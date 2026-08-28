"""Scholarship discovery and audit.

The coverage table is read structurally where a page provides one, because
that table is the only thing entitled to produce FULL_RIDE_CONFIRMED. Prose is
used for eligibility, mode, deadlines and renewal, and every extracted value
keeps the sentence it came from.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.adapters.applicability import (
    assess_degree_applicability,
    assess_international_eligibility,
)
from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.extraction import (
    ClaimBuilder,
    html_title,
    html_to_text,
    is_official_domain,
    parse_date_string,
    parse_money,
    parse_timezone,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageType, classify_page
from app.domain.enums import (
    ApplicationMode,
    ClaimType,
    CostCategory,
    ScholarshipType,
    SourceSpecificity,
)
from app.schemas.money import Money
from app.schemas.result import Coverage, CoverageBreakdown, Scholarship

_COVERAGE_LABELS = {
    "tuition": CostCategory.TUITION,
    "mandatory fees": CostCategory.MANDATORY_FEES,
    "fees": CostCategory.MANDATORY_FEES,
    "housing": CostCategory.HOUSING,
    "accommodation": CostCategory.HOUSING,
    "residence": CostCategory.HOUSING,
    "meal plan": CostCategory.MEALS,
    "meals": CostCategory.MEALS,
    "board": CostCategory.MEALS,
    "living stipend": CostCategory.PERSONAL,
    "stipend": CostCategory.PERSONAL,
    "personal": CostCategory.PERSONAL,
    "travel": CostCategory.TRAVEL,
    "airfare": CostCategory.TRAVEL,
    "health insurance": CostCategory.HEALTH_INSURANCE,
    "books": CostCategory.BOOKS,
}
_COVERAGE_STATES: dict[str, Coverage] = {
    "covered": "yes",
    "fully covered": "yes",
    "included": "yes",
    "not covered": "no",
    "excluded": "no",
    "partially covered": "partial",
    "partial": "partial",
}
_TYPE_HINTS = (
    ("need", ScholarshipType.NEED_BASED),
    ("financial aid", ScholarshipType.NEED_BASED),
    ("automatic", ScholarshipType.AUTOMATIC),
    ("honors", ScholarshipType.HONORS),
    ("department", ScholarshipType.DEPARTMENTAL),
    ("faculty", ScholarshipType.DEPARTMENTAL),
    ("government", ScholarshipType.GOVERNMENT),
    ("mext", ScholarshipType.GOVERNMENT),
    ("community", ScholarshipType.GOVERNMENT),
    ("merit", ScholarshipType.MERIT),
    ("excellence", ScholarshipType.COMPETITIVE),
    ("talent", ScholarshipType.COMPETITIVE),
)


class WebScholarshipAdapter:
    name = "web-scholarships"

    def __init__(self, fetcher: Fetcher, academic_year: str) -> None:
        self.fetcher = fetcher
        self.academic_year = academic_year

    async def find(
        self, candidate: Candidate, program: CandidateProgram, profile
    ) -> tuple[list[Scholarship], AdapterResult]:
        out = AdapterResult()
        if not candidate.scholarships_url:
            out.errors.append(
                f"No official scholarship page is known for {candidate.name}; funding is reported "
                "as unknown rather than assumed absent."
            )
            return [], out

        index = await self.fetcher.get(candidate.scholarships_url)
        out.pages_checked += 1
        if not index.ok:
            out.pages_failed += 1
            out.errors.append(f"{candidate.scholarships_url}: {index.outcome.value} — {index.error}")
            out.retry_urls.append(candidate.scholarships_url)
            return [], out

        links = _award_links(index.text, candidate.scholarships_url)
        if not links:
            out.errors.append(
                f"{candidate.scholarships_url}: no individual award pages were linked, so no award "
                "can be verified in detail."
            )

        scholarships: list[Scholarship] = []
        for i, url in enumerate(links):
            page = await self.fetcher.get(url)
            out.pages_checked += 1
            if not page.ok:
                out.pages_failed += 1
                out.errors.append(f"{url}: {page.outcome.value} — {page.error}")
                out.retry_urls.append(url)
                continue

            classification = classify_page(url=url, html=page.text)
            out.page_types.append((url, classification.page_type.value))
            if classification.page_type is not PageType.SCHOLARSHIP_AWARD:
                # An index, an FAQ or a navigation page is not an award. This is
                # what turned "Scholarships", "Practical matters" and "Prizes
                # and awards" into three separate scholarships.
                out.errors.append(
                    f"{url}: classified as {classification.page_type.value}, not an award page; "
                    "no scholarship recorded."
                )
                continue

            sch, claims = self._parse_award(
                candidate, program, url, page.text, page.fetched_at, classification, index=i
            )
            scholarships.append(sch)
            out.claims.extend(claims)
        return scholarships, out

    def _parse_award(
        self, candidate: Candidate, program: CandidateProgram, url: str,
        html: str, accessed_at: datetime, classification, index: int,
    ) -> tuple[Scholarship, list]:
        soup = BeautifulSoup(html, "lxml")
        text = html_to_text(html)
        low = text.lower()
        title = html_title(html)
        name = classification.subject or (
            soup.find("h1").get_text(strip=True) if soup.find("h1") else title
        ).split(" - ")[0]

        # Every claim from this page is about this one award; the subject key
        # keeps a second award at the same university from looking like a
        # contradiction of the first.
        builder = ClaimBuilder(
            source_url=url,
            page_title=title,
            specificity=SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR,
            program=program.name,
            academic_year=self.academic_year,
            official_domain=url.startswith("fixture://") or is_official_domain(url, [candidate.domain]),
            extraction_method="fixture" if url.startswith("fixture://") else "html_rule",
            accessed_at=accessed_at or datetime.now(UTC),
        )
        _plain_add = builder.add

        def add(*args, **kwargs):
            kwargs.setdefault("subject_key", name)
            return _plain_add(*args, **kwargs)

        builder.add = add  # type: ignore[method-assign]
        builder.add(ClaimType.SCHOLARSHIP_EXISTS, name, f"Award page: {title}", confidence=0.95)

        sch = Scholarship(
            id=f"{candidate.name}::{name}"[:200],
            name=name,
            scholarship_type=_infer_type(name, low),
            source_urls=[url],
            last_verified=accessed_at,
        )

        # --- value ------------------------------------------------------
        pct = re.search(r"covers?\s+(\d{1,3})\s*%\s*(?:of\s+)?(?:the\s+)?tuition", low)
        amount_line = _line_with(text, "the award is worth")
        if pct:
            sch.amount_is_percentage_of_tuition = float(pct.group(1))
            builder.add(ClaimType.SCHOLARSHIP_AMOUNT, {"percent_of_tuition": float(pct.group(1))},
                        _excerpt(text, pct.start()))
        elif amount_line:
            amount = parse_money(amount_line)
            if amount:
                year_m = re.search(r"\b(20\d{2}/\d{2})\b", amount_line)
                sch.amount = Money(
                    amount=amount[0], currency=amount[1],
                    academic_year=year_m.group(1) if year_m else self.academic_year,
                    source_url=url,
                )
                builder.add(
                    ClaimType.SCHOLARSHIP_AMOUNT,
                    {"amount": amount[0], "currency": amount[1],
                     "academic_year": sch.amount.academic_year},
                    amount_line,
                )
        elif "determined individually" in low or "depends on an assessment" in low:
            builder.add(ClaimType.SCHOLARSHIP_AMOUNT, None,
                        _line_with(text, "determined individually") or _line_with(text, "assessment"),
                        confidence=0.9,
                        notes="Award size is not published; it cannot be entered into the gap arithmetic.")

        # --- coverage table (the only route to FULL_RIDE_CONFIRMED) -----
        sch.coverage = _coverage_from_tables(soup)
        if sch.coverage:
            builder.add(
                ClaimType.SCHOLARSHIP_COVERAGE,
                {c.category.value: c.covered for c in sch.coverage},
                "Coverage table: "
                + "; ".join(f"{c.category.value}={c.covered}" for c in sch.coverage),
                confidence=0.9,
                section="What the award covers",
            )
            for c in sch.coverage:
                c.claim_ids.append(url)

        # --- eligibility -------------------------------------------------
        # This award page exists and names an award; that alone is the only
        # thing "opportunity_exists" asserts.
        sch.opportunity_exists = True

        cit = re.search(r"open only to citizens of ([^.]+)\.", text, re.IGNORECASE)
        if cit:
            sch.citizenship_restrictions = [
                p.strip() for p in re.split(r",| and ", cit.group(1)) if p.strip()
            ]
            builder.add(ClaimType.SCHOLARSHIP_CITIZENSHIP_RESTRICTION, sch.citizenship_restrictions,
                        _excerpt(text, cit.start()), confidence=0.9)

        # A restriction list is not itself an answer about international
        # eligibility - the applicant may hold one of the listed citizenships.
        international = assess_international_eligibility(text)
        sch.international_eligible = international.verdict
        if international.verdict != "unknown":
            builder.add(
                ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE,
                international.verdict == "yes",
                international.evidence,
                confidence=0.85,
                notes=international.reason,
            )
        elif sch.citizenship_restrictions:
            sch.international_eligible = "unknown"

        # --- degree applicability -----------------------------------------
        applicability = assess_degree_applicability(text, str(program.degree))
        sch.degree_applicability = applicability.verdict
        sch.degree_applicability_reason = applicability.reason
        sch.applies_to_degrees = list(applicability.mentioned_degrees)
        if applicability.verdict != "unknown":
            builder.add(
                ClaimType.SCHOLARSHIP_PROGRAM_RESTRICTION,
                {"degree": str(program.degree), "applies": applicability.verdict},
                applicability.evidence or applicability.reason,
                confidence=0.85,
                notes=applicability.reason,
            )

        # --- application mode ------------------------------------------
        if "nominated by the department" in low or "direct applications are not accepted" in low:
            sch.application_mode = ApplicationMode.NOMINATION
        elif "no separate application is required" in low or "considered automatically" in low:
            sch.application_mode = ApplicationMode.AUTOMATIC
        elif "separate scholarship application" in low or "must be submitted in addition" in low:
            sch.application_mode = ApplicationMode.SEPARATE
        if sch.application_mode != ApplicationMode.UNKNOWN:
            builder.add(ClaimType.SCHOLARSHIP_APPLICATION_MODE, sch.application_mode.value,
                        _line_with(text, "how to apply") or _line_with(text, "application"))
        sch.requires_extra_essays = "additional essays" in low or "statement of motivation" in low

        # --- deadline ----------------------------------------------------
        dl_line = _line_with(text, "scholarship deadline") or _line_with(text, "deadline is")
        if dl_line:
            match = re.search(r"deadline is ([^.]+?)\.", dl_line + ".", re.IGNORECASE)
            deadline = parse_date_string(match.group(1)) if match else None
            if match and deadline:
                sch.deadline = deadline
                sch.deadline_raw = match.group(1).strip()
                sch.deadline_timezone = parse_timezone(dl_line)
                builder.add(ClaimType.SCHOLARSHIP_DEADLINE, deadline.isoformat(), dl_line,
                            notes=f"timezone: {sch.deadline_timezone or 'not stated on page'}")

        # --- renewal ------------------------------------------------------
        if "not renewable" in low or "one-time award" in low:
            sch.renewable = False
            builder.add(ClaimType.SCHOLARSHIP_RENEWABLE, False, _line_with(text, "renewable"))
        elif "renewable" in low:
            sch.renewable = True
            dur = re.search(r"up to (\d+) years", low)
            if dur:
                sch.duration_years = float(dur.group(1))
                builder.add(ClaimType.SCHOLARSHIP_DURATION_YEARS, float(dur.group(1)),
                            _excerpt(text, dur.start()))
            builder.add(ClaimType.SCHOLARSHIP_RENEWABLE, True, _line_with(text, "renewable"))
            for phrase in ("maintain", "remain in the top", "complete at least"):
                line = _line_with(text, phrase)
                if line:
                    sch.renewal_requirements.append(line.strip())
                    builder.add(ClaimType.SCHOLARSHIP_RENEWAL_REQUIREMENT, line.strip(), line)
                    break

        # --- stacking and count ------------------------------------------
        if "may not be combined" in low:
            sch.stackable = "no"
        elif "may be held together with other" in low:
            sch.stackable = "yes"
        if sch.stackable != "unknown":
            builder.add(ClaimType.SCHOLARSHIP_STACKABLE, sch.stackable, _line_with(text, "combined")
                        or _line_with(text, "held together"))

        cnt = re.search(r"(\d+)\s+awards? are offered", low)
        if cnt:
            sch.published_count = int(cnt.group(1))
            builder.add(ClaimType.SCHOLARSHIP_COUNT, int(cnt.group(1)), _excerpt(text, cnt.start()))

        score = re.search(r"an?\s+(ielts|toefl|sat)\s+score of at least\s+(\d+(?:\.\d+)?)", low)
        if score:
            sch.min_test_scores[score.group(1)] = float(score.group(2))
            builder.add(ClaimType.SCHOLARSHIP_MIN_TEST_SCORE,
                        {score.group(1): float(score.group(2))}, _excerpt(text, score.start()))

        self._derive_availability(sch)
        sch.claim_ids = [c.source_url for c in builder.claims]
        return sch, builder.claims

    @staticmethod
    def _derive_availability(sch: Scholarship) -> None:
        """Roll the separate states up, conservatively.

        A missing deadline used to read as "available". It now reads as
        unknown, because not finding a date is not the same as there being no
        date.
        """
        from datetime import date as _date

        sch.deadline_known = sch.deadline is not None
        sch.deadline_passed = bool(sch.deadline and sch.deadline < _date.today())

        if sch.deadline_known:
            sch.application_window_open = "no" if sch.deadline_passed else "yes"
        else:
            sch.application_window_open = "unknown"

        if sch.degree_applicability == "no" or sch.international_eligible == "no":
            sch.applicant_eligible = "no"
        elif sch.degree_applicability == "yes" and sch.international_eligible == "yes":
            sch.applicant_eligible = "yes"
        else:
            sch.applicant_eligible = "unknown"

        if sch.applicant_eligible == "no" or sch.application_window_open == "no":
            sch.available_this_intake = "no"
        elif sch.applicant_eligible == "yes" and sch.application_window_open == "yes":
            sch.available_this_intake = "yes"
        else:
            sch.available_this_intake = "unknown"


#: A link worth following from a funding index page.
_AWARD_HINTS = (
    "scholarship", "grant", "award", "bursary", "fellowship", "stipend",
    "financial aid", "funding", "beurs", "stipendium",
)
#: Site furniture that appears on every page and is never an award.
_NAV_NOISE = (
    "skip to", "main content", "navigation", "search", "menu", "cookie",
    "privacy", "contact", "login", "sitemap", "back to top", "share",
)


def _award_links(html: str, base: str) -> list[str]:
    """Links from a funding index page that plausibly describe one award.

    Real index pages are mostly site furniture. Following every anchor turned
    "Menu główne" and "Skip to main content" into scholarships, so a link now
    has to look like an award in its text or its path to be followed.
    """
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    out: list[str] = []
    base_host = urlparse(base).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        if href.startswith("fixture://"):
            url = href
        elif base.startswith("fixture://"):
            # urljoin does not understand a custom scheme; resolve by hand.
            url = f"{base.rsplit('/', 1)[0]}/{href.lstrip('./')}"
        else:
            url = urljoin(base, href)
        # A fragment is the same page, not another award.
        url = url.split("#")[0].rstrip("/")

        if not url or url in seen or url == base.rstrip("/"):
            continue
        # Share buttons carry the page's own URL in a query string, so a
        # "scholarships" link can point at facebook.com. An award page is on
        # the institution's own domain.
        if base_host and urlparse(url).netloc != base_host:
            continue

        label = " ".join(a.get_text(" ", strip=True).split()).lower()
        if any(noise in label for noise in _NAV_NOISE):
            continue
        haystack = f"{label} {url.lower()}"
        if not any(hint in haystack for hint in _AWARD_HINTS):
            continue

        seen.add(url)
        out.append(url)
    return out[:12]


def _coverage_from_tables(soup: BeautifulSoup) -> list[CoverageBreakdown]:
    """Read a two-column 'cost / status' table into structured coverage."""
    out: list[CoverageBreakdown] = []
    seen: set[CostCategory] = set()
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c.get_text(strip=True).lower() for c in row.find_all(["td", "th"])]
            if len(cells) != 2:
                continue
            category = next(
                (cat for label, cat in _COVERAGE_LABELS.items() if label in cells[0]), None
            )
            state = _COVERAGE_STATES.get(cells[1])
            if category is None or state is None or category in seen:
                continue
            seen.add(category)
            out.append(CoverageBreakdown(category=category, covered=state))
    return out


def _infer_type(name: str, low_text: str) -> ScholarshipType:
    hay = f"{name.lower()} {low_text[:1200]}"
    for hint, kind in _TYPE_HINTS:
        if hint in hay:
            return kind
    return ScholarshipType.UNKNOWN


def _line_with(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle.lower() in line.lower():
            return line.strip()[:300]
    return ""


def _excerpt(text: str, at: int, radius: int = 150) -> str:
    return text[max(0, at - radius): at + radius].replace("\n", " ").strip()

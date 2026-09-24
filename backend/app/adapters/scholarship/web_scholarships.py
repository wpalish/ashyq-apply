"""Scholarship discovery and audit.

The coverage table is read structurally where a page provides one, because
that table is the only thing entitled to produce FULL_RIDE_CONFIRMED. Prose is
used for eligibility, mode, deadlines and renewal, and every extracted value
keeps the sentence it came from.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.adapters.applicability import (
    assess_degree_applicability,
    assess_international_eligibility,
)
from app.adapters.base import AdapterResult, Candidate, CandidateProgram, PageOutcome
from app.adapters.extraction import (
    ClaimBuilder,
    html_title,
    is_official_domain,
    parse_date_string,
    parse_money,
    parse_timezone,
    readable_text,
)
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import PageType, classify_page
from app.adapters.scope_reader import read_scope
from app.domain.enums import (
    ApplicationMode,
    ClaimType,
    CostCategory,
    ScholarshipType,
    SourceSpecificity,
)
from app.domain.funding import roll_up_availability
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


#: A page saying the award is not on offer. `award_current_for_intake` and
#: `currently_available` were dead fields — declared, never set, and ignored by
#: the roll-up — so an award a page calls discontinued could still be reported
#: as available for the intake.
_AWARD_WITHDRAWN = re.compile(
    r"\b(discontinued|withdrawn|no longer (?:offered|awarded|available)|suspended"
    r"|not (?:being )?(?:offered|awarded)|paused|on hold)\b",
    re.IGNORECASE,
)
#: There is deliberately **no** positive counterpart. I wrote one — "is/are
#: offered", "applications are open" — and the demo caught it reading Delft's
#: "30 awards are offered each year" as a statement about *this* cycle. A
#: sentence about how many awards exist is not evidence that the scheme is
#: running now, and `available_this_intake` needs only `!= no` from this
#: dimension, so the positive branch bought nothing and could be wrong.


#: "You must hold an offer" in the shapes award pages actually write it.
_OFFER_REQUIRED = re.compile(
    r"(must|need to|required to)\s+(hold|have|have received|have been given)\s+an?\s+"
    r"(offer|admission offer|letter of (admission|offer))"
    r"|only\s+(admitted|offer[- ]holding)\s+(students|applicants)"
    r"|open only to (admitted|offer[- ]holding)",
    re.IGNORECASE,
)
#: And the explicit denial, which is just as decisive and much rarer.
_OFFER_NOT_REQUIRED = re.compile(
    r"(no|without an?)\s+(admission\s+)?offer\s+(is\s+)?(required|needed)"
    r"|you do not need an? (admission )?offer"
    r"|apply before (you receive|receiving) an offer",
    re.IGNORECASE,
)
_NEED_BASED = re.compile(
    r"\bneed[- ]based\b|\bdemonstrated financial need\b|\bmeans[- ]tested\b"
    r"|awarded on the basis of financial need",
    re.IGNORECASE,
)
#: Only an explicit "merit only" denial. A page that says "merit-based" and
#: nothing else has not said need is irrelevant — many awards are both.
_MERIT_ONLY = re.compile(
    r"regardless of (financial need|income)"
    r"|financial need is not (considered|taken into account)"
    r"|no (proof|evidence) of financial need",
    re.IGNORECASE,
)


class WebScholarshipAdapter:
    name = "web-scholarships"

    def __init__(self, fetcher: Fetcher, academic_year: str) -> None:
        self.fetcher = fetcher
        self.academic_year = academic_year
        #: Pages this adapter has already read, for its own lifetime — one
        #: run. The funding stage calls ``find`` once per programme, so a
        #: university with two programmes used to read its scholarship index
        #: and every award page twice. Pages are memoised and claims are not:
        #: a claim carries the programme it was built for, so the second
        #: programme re-parses the same page rather than reusing its claims.
        self._pages: dict[str, FetchResult] = {}
        #: Which university ``_pages`` belongs to. The memo exists to stop the
        #: second programme re-reading the first one's pages, and a university
        #: is as far as that goes — holding every university's HTML for the
        #: whole run would be tens of megabytes of dead weight for no gain.
        self._pages_for: str | None = None

    def _memo_for(self, candidate: Candidate) -> None:
        """Point the page memo at this university, dropping the last one's."""
        key = f"{candidate.name}::{candidate.country}"
        if key != self._pages_for:
            self._pages = {}
            self._pages_for = key

    async def _read(self, url: str) -> FetchResult:
        """Fetch a page once per run, however many programmes ask for it."""
        cached = self._pages.get(_page_key(url))
        if cached is not None:
            return cached
        page = await self.fetcher.get(url)
        if page.ok:
            self._pages[_page_key(url)] = page
        return page

    async def find(
        self, candidate: Candidate, program: CandidateProgram, profile
    ) -> tuple[list[Scholarship], AdapterResult]:
        out = AdapterResult()
        self._memo_for(candidate)
        primary = candidate.scholarships_url or ""
        if not primary and not program.url:
            out.errors.append(
                f"No official scholarship page is known for {candidate.name}; funding is reported "
                "as unknown rather than assumed absent."
            )
            return [], out
        if not primary:
            # The one other candidate generator already in hand. It is read as
            # an index only: a programme page is never an award page, and the
            # classifier still has to say so before anything is recorded.
            primary = program.url or ""
            out.errors.append(
                f"No official scholarship page is known for {candidate.name}; the programme page is "
                "read as a funding index instead, and awards are recorded only from award pages."
            )

        scholarships: list[Scholarship] = []
        seen_pages: set[str] = set()
        seen_translations: set[str] = set()
        queue: list[tuple[str, int]] = [(primary, 0)]
        indexes_read = 0
        linked_an_award = False
        fallback_used = primary == program.url

        while queue:
            url, depth = queue.pop(0)
            key = _page_key(url)
            if key in seen_pages:
                continue
            seen_pages.add(key)
            # The same award page in another language adds nothing an
            # English-reading applicant can act on, and costs a read each.
            # Run 25: HKU read its scholarship list three times (en, zh-hant,
            # zh-hans) and ran out of clock before the awards.
            translation = _without_locale(key)
            if depth > 0 and translation != key and translation in seen_translations:
                continue
            seen_translations.add(translation)

            was_read_before = _page_key(url) in self._pages
            page = await self._read(url)
            if not was_read_before:
                out.pages_checked += 1
            if not page.ok:
                out.pages_failed += 1
                out.errors.append(f"{url}: {page.outcome.value} — {page.error}")
                out.retry_urls.append(url)
                out.page_outcomes.append(
                    PageOutcome(
                        url=url,
                        category="fetch-failed",
                        detail=f"{page.outcome.value} — {page.error}",
                    )
                )
            else:
                classification = classify_page(url=url, html=page.text)
                page_type = classification.page_type.value
                if depth > 0:
                    out.page_types.append((url, classification.page_type.value))

                is_index = classification.page_type is PageType.SCHOLARSHIP_INDEX
                if depth == 0 or (is_index and indexes_read < _MAX_INDEX_PAGES):
                    # An index is discovery, never award proof: nothing is
                    # recorded from the page itself, only from what it links.
                    indexes_read += 1
                    if depth > 0:
                        out.errors.append(
                            f"{url}: classified as {classification.page_type.value}; read as a "
                            "funding index, and the awards it links are followed."
                        )
                    links = [
                        link
                        for link in _award_links(page.text, url)
                        if _page_key(link) not in seen_pages
                    ]
                    if _is_international(profile, candidate):
                        # Awards a university reserves for its own citizens are
                        # not read for someone who is not one. Run 36: UBC spent
                        # its last 30 s on eight Canadian-students award pages.
                        for link in [x for x in links if _DOMESTIC_ONLY.search(x)]:
                            links.remove(link)
                            out.page_outcomes.append(
                                PageOutcome(
                                    url=link,
                                    category="classifier-rejected",
                                    detail="for domestic students only; not read for an "
                                    "international applicant",
                                )
                            )
                    if links:
                        linked_an_award = True
                    elif url == primary:
                        out.errors.append(
                            f"{url}: no individual award pages were linked, so no award "
                            "can be verified in detail."
                        )
                    out.page_outcomes.append(
                        PageOutcome(
                            url=url,
                            category="fetched-ok",
                            page_type=page_type,
                            detail=f"read as a funding index; {len(links)} award links followed",
                        )
                    )
                    room = _MAX_AWARD_PAGES - len(queue) - len(scholarships)
                    queue.extend((link, depth + 1) for link in links[: max(room, 0)])
                elif is_index:
                    # An index this deep is a site map, not a funding route.
                    out.errors.append(
                        f"{url}: classified as {classification.page_type.value}; not followed, "
                        f"because {_MAX_INDEX_PAGES} index pages have already been read."
                    )
                    out.page_outcomes.append(
                        PageOutcome(
                            url=url,
                            category="classifier-rejected",
                            page_type=page_type,
                            detail="index page beyond the index budget; not followed",
                        )
                    )
                elif classification.page_type is PageType.SCHOLARSHIP_AWARD:
                    sch, claims = self._parse_award(
                        candidate,
                        program,
                        url,
                        page.text,
                        page.fetched_at,
                        classification,
                        index=len(scholarships),
                    )
                    scholarships.append(sch)
                    out.claims.extend(claims)
                    out.page_outcomes.append(
                        PageOutcome(
                            url=url,
                            category="fetched-ok" if claims else "no-pattern-match",
                            page_type=page_type,
                            detail=f"award page; {len(claims)} claims read",
                        )
                    )
                else:
                    # An FAQ or a navigation page is not an award. This is what
                    # turned "Scholarships", "Practical matters" and "Prizes
                    # and awards" into three separate scholarships.
                    out.errors.append(
                        f"{url}: classified as {classification.page_type.value}, not an award page; "
                        "no scholarship recorded."
                    )
                    out.page_outcomes.append(
                        PageOutcome(
                            url=url,
                            category="classifier-rejected",
                            page_type=page_type,
                            detail="not an award page; no scholarship recorded",
                        )
                    )

            if (
                not queue
                and not linked_an_award
                and not fallback_used
                and program.url
                and _page_key(program.url) not in seen_pages
            ):
                # The index existed and named no award. The programme page is
                # the one other generator already in hand, so it is worth a
                # fetch here and nowhere else.
                fallback_used = True
                queue.append((program.url, 0))

        return scholarships, out

    def _parse_award(
        self,
        candidate: Candidate,
        program: CandidateProgram,
        url: str,
        html: str,
        accessed_at: datetime,
        classification,
        index: int,
    ) -> tuple[Scholarship, list]:
        soup = parse_html(html)
        text = readable_text(html)
        low = text.lower()
        title = html_title(html)
        name = (
            classification.subject
            or (soup.find("h1").get_text(strip=True) if soup.find("h1") else title).split(" - ")[0]
        )

        # Every claim from this page is about this one award; the subject key
        # keeps a second award at the same university from looking like a
        # contradiction of the first.
        builder = ClaimBuilder(
            source_url=url,
            page_title=title,
            specificity=SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR,
            program=program.name,
            academic_year=self.academic_year,
            official_domain=url.startswith("fixture://")
            or is_official_domain(url, [candidate.domain]),
            extraction_method="fixture" if url.startswith("fixture://") else "html_rule",
            accessed_at=accessed_at or datetime.now(UTC),
            # Eligibility prose names a population far more often than
            # requirements prose does, and an award claimed for the wrong one
            # is the most expensive wrong answer this product can give.
            scope=read_scope(text, title=title),
        )
        _plain_add = builder.add

        def add(*args, **kwargs):
            kwargs.setdefault("subject_key", name)
            return _plain_add(*args, **kwargs)

        builder.add = add  # type: ignore[method-assign]
        # The excerpt must be text from the page. "Award page: <title>" was a
        # sentence we wrote, shown in the evidence panel as though quoted.
        builder.add(
            ClaimType.SCHOLARSHIP_EXISTS,
            name,
            _first_sentence_with(text, name) or name,
            confidence=0.95,
            notes=f"page classified as {classification.page_type.value}",
        )

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
            builder.add(
                ClaimType.SCHOLARSHIP_AMOUNT,
                {"percent_of_tuition": float(pct.group(1))},
                _excerpt(text, pct.start()),
            )
        elif amount_line:
            amount = parse_money(amount_line)
            if amount:
                year_m = re.search(r"\b(20\d{2}/\d{2})\b", amount_line)
                sch.amount = Money(
                    amount=amount[0],
                    currency=amount[1],
                    academic_year=year_m.group(1) if year_m else self.academic_year,
                    source_url=url,
                )
                builder.add(
                    ClaimType.SCHOLARSHIP_AMOUNT,
                    {
                        "amount": amount[0],
                        "currency": amount[1],
                        "academic_year": sch.amount.academic_year,
                    },
                    amount_line,
                )
        elif "determined individually" in low or "depends on an assessment" in low:
            builder.add(
                ClaimType.SCHOLARSHIP_AMOUNT,
                None,
                _line_with(text, "determined individually") or _line_with(text, "assessment"),
                confidence=0.9,
                notes="Award size is not published; it cannot be entered into the gap arithmetic.",
            )

        # --- coverage table (the only route to FULL_RIDE_CONFIRMED) -----
        sch.coverage, coverage_quote = _coverage_from_tables(soup)
        if sch.coverage:
            builder.add(
                ClaimType.SCHOLARSHIP_COVERAGE,
                {c.category.value: c.covered for c in sch.coverage},
                # The table's own text, not a summary of it.
                coverage_quote,
                confidence=0.9,
                section="What the award covers",
                notes="; ".join(f"{c.category.value}={c.covered}" for c in sch.coverage),
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
            builder.add(
                ClaimType.SCHOLARSHIP_CITIZENSHIP_RESTRICTION,
                sch.citizenship_restrictions,
                _excerpt(text, cit.start()),
                confidence=0.9,
            )

        faculty = _restricted_to(text, _FACULTY_RESTRICTION)
        if faculty:
            sch.faculty_restrictions = [faculty.group("subject").strip()]
            builder.add(
                ClaimType.SCHOLARSHIP_PROGRAM_RESTRICTION,
                {"faculty": sch.faculty_restrictions[0]},
                _excerpt(text, faculty.start()),
                confidence=0.85,
            )

        programme = _restricted_to(text, _PROGRAMME_RESTRICTION)
        if programme:
            sch.program_restrictions = [programme.group("subject").strip()]
            builder.add(
                ClaimType.SCHOLARSHIP_PROGRAM_RESTRICTION,
                {"programme": sch.program_restrictions[0]},
                _excerpt(text, programme.start()),
                confidence=0.85,
            )

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
            # Only real page text goes in the excerpt; the rationale is a note.
            builder.add(
                ClaimType.SCHOLARSHIP_PROGRAM_RESTRICTION,
                {"degree": str(program.degree), "applies": applicability.verdict},
                applicability.evidence,
                confidence=0.85 if applicability.evidence else 0.6,
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
            builder.add(
                ClaimType.SCHOLARSHIP_APPLICATION_MODE,
                sch.application_mode.value,
                _line_with(text, "how to apply") or _line_with(text, "application"),
            )
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
                builder.add(
                    ClaimType.SCHOLARSHIP_DEADLINE,
                    deadline.isoformat(),
                    dl_line,
                    notes=f"timezone: {sch.deadline_timezone or 'not stated on page'}",
                )

        # --- renewal ------------------------------------------------------
        if "not renewable" in low or "one-time award" in low:
            sch.renewable = False
            builder.add(ClaimType.SCHOLARSHIP_RENEWABLE, False, _line_with(text, "renewable"))
        elif "renewable" in low:
            sch.renewable = True
            dur = re.search(r"up to (\d+) years", low)
            if dur:
                sch.duration_years = float(dur.group(1))
                builder.add(
                    ClaimType.SCHOLARSHIP_DURATION_YEARS,
                    float(dur.group(1)),
                    _excerpt(text, dur.start()),
                )
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
            builder.add(
                ClaimType.SCHOLARSHIP_STACKABLE,
                sch.stackable,
                _line_with(text, "combined") or _line_with(text, "held together"),
            )

        # --- offer required, and need-based ------------------------------
        # Both are decisions the guide lists separately, and both are refused
        # unless the page says so outright: an applicant who assumes an offer
        # is needed applies too late, and one who assumes it is not may never
        # apply at all.
        if _OFFER_REQUIRED.search(low):
            sch.offer_required = "yes"
        elif _OFFER_NOT_REQUIRED.search(low):
            sch.offer_required = "no"
        if sch.offer_required != "unknown":
            builder.add(
                ClaimType.SCHOLARSHIP_OFFER_REQUIRED,
                sch.offer_required,
                _line_with(text, "offer") or _line_with(text, "admitted"),
            )

        if _NEED_BASED.search(low):
            sch.financial_need_required = "yes"
        elif _MERIT_ONLY.search(low):
            sch.financial_need_required = "no"
        if sch.financial_need_required != "unknown":
            builder.add(
                ClaimType.SCHOLARSHIP_NEED_BASED,
                sch.financial_need_required,
                _line_with(text, "need") or _line_with(text, "merit"),
            )

        cnt = re.search(r"(\d+)\s+awards? are offered", low)
        if cnt:
            sch.published_count = int(cnt.group(1))
            builder.add(ClaimType.SCHOLARSHIP_COUNT, int(cnt.group(1)), _excerpt(text, cnt.start()))

        score = re.search(r"an?\s+(ielts|toefl|sat)\s+score of at least\s+(\d+(?:\.\d+)?)", low)
        if score:
            sch.min_test_scores[score.group(1)] = float(score.group(2))
            builder.add(
                ClaimType.SCHOLARSHIP_MIN_TEST_SCORE,
                {score.group(1): float(score.group(2))},
                _excerpt(text, score.start()),
            )

        # Is the award on offer at all? Read here, where the page and the
        # builder are, and before the roll-up that consumes it: a withdrawn
        # award needs no eligibility assessment.
        withdrawn = _line_matching(text, _AWARD_WITHDRAWN)
        if withdrawn:
            sch.currently_available = "no"
            sch.award_current_for_intake = "no"
            builder.add(ClaimType.SCHOLARSHIP_EXISTS, False, withdrawn, confidence=0.7)

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
        elif (
            sch.degree_applicability == "yes"
            and sch.international_eligible == "yes"
            # A faculty or programme restriction the page states but does not
            # settle for this programme is an open question, and an open
            # question is never a yes.
            and not sch.faculty_restrictions
            and not sch.program_restrictions
        ):
            sch.applicant_eligible = "yes"
        else:
            sch.applicant_eligible = "unknown"

        sch.available_this_intake = roll_up_availability(
            opportunity_exists=sch.opportunity_exists,
            applicant_eligible=sch.applicant_eligible,
            application_window_open=sch.application_window_open,
            award_current_for_intake=sch.award_current_for_intake,
        )


#: A link worth following from a funding index page.
#: How many award pages one candidate may cost. Unchanged from when a single
#: index supplied them all; the walk below shares this budget rather than
#: giving each index its own.
_MAX_AWARD_PAGES = 12
#: Including the first one. An index behind an index behind an index is a
#: site map, not a funding route.
_MAX_INDEX_PAGES = 3

_AWARD_HINTS = (
    "scholarship",
    "grant",
    "award",
    "bursary",
    "fellowship",
    "stipend",
    "financial aid",
    "funding",
    "beurs",
    "stipendium",
)
#: Site furniture that appears on every page and is never an award.
_NAV_NOISE = (
    "skip to",
    "main content",
    "navigation",
    "search",
    "menu",
    "cookie",
    "privacy",
    "contact",
    "login",
    "sitemap",
    "back to top",
    "share",
)


#: "open to students in the Faculty of Engineering" and its neighbours. The
#: subject is captured as the page wrote it: this is evidence, not a lookup,
#: and a faculty name normalised by us is no longer the page's statement.
_FACULTY_RESTRICTION = re.compile(
    r"\b(?:open (?:only )?to|restricted to|available (?:only )?to|limited to)\b"
    r"[^.]{0,60}?\b(?:students?|applicants?)?[^.]{0,20}?"
    r"\b(?:in|of|from|within|enrolled in)\b\s+"
    r"(?P<subject>(?:the\s+)?(?:faculty|school|college|department)\s+of\s+[A-Z][^.,;]{2,60})",
    re.IGNORECASE,
)
#: The same shape, for a named programme rather than a faculty.
_PROGRAMME_RESTRICTION = re.compile(
    r"\b(?:open (?:only )?to|restricted to|available (?:only )?to|limited to)\b"
    r"[^.]{0,60}?\b(?:students?|applicants?)?[^.]{0,20}?"
    r"\b(?:in|of|on|enrolled (?:in|on))\b\s+"
    r"(?P<subject>(?:the\s+)?(?:B\.?Sc|B\.?A|M\.?Sc|M\.?A|Bachelor|Master)[^.,;]{2,70}"
    r"\s+(?:programme|program|degree|course))",
    re.IGNORECASE,
)


def _restricted_to(text: str, pattern: re.Pattern[str]) -> re.Match[str] | None:
    """The page's own restriction sentence, or nothing.

    Deliberately narrow. A restriction we invent excludes a real applicant
    from real money, and a restriction we miss leaves an open question that
    the applicant is told to ask — the two failures are not symmetrical.
    """
    return pattern.search(" ".join((text or "").split()))


#: A path that says an award or list is for the university's own citizens.
_DOMESTIC_ONLY = re.compile(r"/[\w-]*\b(?:domestic|canadian|home)-students?\b", re.IGNORECASE)


def _is_international(profile, candidate) -> bool:
    """Whether the applicant plainly holds no citizenship of the university's country.

    Only a clear "no" from :func:`match_citizenship` counts; an unresolvable
    pair (a code, an unknown spelling) keeps every page, so nothing an
    applicant might qualify for is skipped on a guess.
    """
    from app.domain.citizenship import CitizenshipMatch, match_citizenship

    context = getattr(profile, "context", None)
    country = getattr(candidate, "country", "") or ""
    if context is None or not country:
        return False
    held = [getattr(context, "citizenship", None), getattr(context, "second_citizenship", None)]
    if any(h and len(h.strip()) <= 3 for h in held):
        # An ISO code ("CA") is not a name the matcher can compare with
        # "Canada"; a Canadian written that way must not lose Canadian awards.
        return False
    verdict, _ = match_citizenship([country], held)
    return verdict is CitizenshipMatch.NOT_APPLICABLE


def _award_links(html: str, base: str) -> list[str]:
    """Links from a funding index page that plausibly describe one award.

    Real index pages are mostly site furniture. Following every anchor turned
    "Menu główne" and "Skip to main content" into scholarships, so a link now
    has to look like an award in its text or its path to be followed.
    """
    soup = parse_html(html)
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
    return out


_LOCALE_SEGMENT = re.compile(
    r"^(?:zh(?:-han[st]|-cn|-tw|-hk)?|ko|ja|fr|de|es|it|nl|fi|sv|pl|pt|ru|ar|tr|vi|th|id|ms)$",
    re.IGNORECASE,
)


def _without_locale(key: str) -> str:
    """``/zh-hant/fees/x`` and ``/fees/x`` are one page in two languages."""
    parts = urlsplit(key)
    segments = parts.path.split("/")
    if len(segments) > 2 and _LOCALE_SEGMENT.match(segments[1]):
        path = "/" + "/".join(segments[2:])
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))
    return key


def _page_key(url: str) -> str:
    """One page, one identity — a fragment and a trailing slash are neither."""
    return url.split("#")[0].rstrip("/")


def _coverage_from_tables(soup: BeautifulSoup) -> tuple[list[CoverageBreakdown], str]:
    """Read a two-column 'cost / status' table into structured coverage.

    Returns the coverage and the table's own text, so the claim can quote what
    it read rather than a summary of it.
    """
    out: list[CoverageBreakdown] = []
    seen: set[CostCategory] = set()
    quoted = ""
    for table in soup.find_all("table"):
        if not quoted:
            quoted = " ".join(table.get_text(" ", strip=True).split())[:400]
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
    return out, quoted


def _infer_type(name: str, low_text: str) -> ScholarshipType:
    hay = f"{name.lower()} {low_text[:1200]}"
    for hint, kind in _TYPE_HINTS:
        if hint in hay:
            return kind
    return ScholarshipType.UNKNOWN


def _first_sentence_with(text: str, needle: str) -> str:
    """A verbatim sentence from the page containing `needle`, or empty."""
    if not needle:
        return ""
    flat = " ".join(text.split())
    index = flat.lower().find(needle.lower())
    if index < 0:
        return ""
    start = max(0, flat.rfind(".", 0, index) + 1)
    end = flat.find(".", index + len(needle))
    end = len(flat) if end < 0 else end + 1
    return flat[start:end].strip()[:400]


def _line_matching(text: str, pattern: re.Pattern[str]) -> str:
    """The first line a pattern matches, as the evidence for a claim.

    Sibling of ``_line_with``: a claim must quote the page, and a regex-shaped
    question needs a regex-shaped lookup rather than a second substring.
    """
    for line in text.splitlines():
        if pattern.search(line):
            return line.strip()[:300]
    return ""


def _line_with(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle.lower() in line.lower():
            return line.strip()[:300]
    return ""


def _excerpt(text: str, at: int, radius: int = 150) -> str:
    return text[max(0, at - radius) : at + radius].replace("\n", " ").strip()

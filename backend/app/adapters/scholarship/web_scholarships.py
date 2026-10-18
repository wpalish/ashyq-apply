"""Scholarship discovery and audit.

The coverage table is read structurally where a page provides one, because
that table is the only thing entitled to produce FULL_RIDE_CONFIRMED. Prose is
used for eligibility, mode, deadlines and renewal, and every extracted value
keeps the sentence it came from.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import UTC, date, datetime
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.adapters.applicability import (
    Applicability,
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
    verification_domains,
)
from app.adapters.fetching import Fetcher, FetchResult, reading_as
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import PageType, classify_page, main_content
from app.adapters.scholarship.conditional_benefits import read_conditional_policy
from app.adapters.scope_reader import read_scope
from app.domain.enums import (
    ApplicationMode,
    ClaimType,
    CostCategory,
    ScholarshipType,
    SourceSpecificity,
)
from app.domain.funding import roll_up_availability
from app.schemas.claim import MAX_EXCERPT_CHARS
from app.schemas.money import Money
from app.schemas.result import Coverage, CoverageBreakdown, Scholarship

#: One official-award query after an empty walk for a confirmed programme.
SEARCH_FUNDING_FALLBACK = True
#: Measured separately: generic scholarship queries can return only indices.
TARGET_AWARD_SEARCH = True
#: AR-1 (structural analysis 2026-10-18, change 3): scholarship discovery as
#: its own route — official funding links on the confirmed programme page or
#: the admissions hub first, an index budget spent by shape, an award query
#: naming the institution with a shape filter on its results, and existence
#: and international applicability read from eligibility sentences only.
#: Off: nothing changes.
AWARD_ROUTE = False
#: Plan rule SL-1 (read budget analysis 2026-10-18 §2, §4 step 1.4-1.5), off
#: until a paired run passes. For a bachelor request Imperial's funding walk
#: read societal-engagement "funding" pages x4, then PhD studentships and an
#: ADA Lovelace PhD award until the 115 s kill; Chula read a research-office
#: funding page and an "awards and honours" news list. None can answer either
#: scholarship question for an undergraduate. On, for a bachelor request: a
#: funding page (index, award or search lead) whose URL names another level
#: (PhD, doctoral, postgraduate, master's, MSc, MBA, studentship, research
#: degree) and not the bachelor's own words, or that names funding, grants or
#: awards outside any study, admissions, fees or scholarships path, is not
#: read; the confirmed programme page and the admissions page are never
#: refused. The verify stage's deadline and route links get the URL
#: degree-level guard that HL-1 gives them (``names_other_degree_level``),
#: so Imperial's postgraduate-taught deadlines page is not read for a
#: bachelor. The benchmark harness flips it per capture
#: (``--scholarship-level-scope``).
SCHOLARSHIP_LEVEL_SCOPE = True

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

    def __init__(self, fetcher: Fetcher, academic_year: str, today: date | None = None) -> None:
        self.fetcher = fetcher
        self.academic_year = academic_year
        #: The run's assessment day, in UTC. "Has this deadline passed?" is
        #: asked of the run, not of whenever and wherever the adapter happens
        #: to execute: the runner passes the same day ``_stage_assess`` judges
        #: by, so an award's window and its deadline check cannot disagree.
        self.today = today if today is not None else datetime.now(UTC).date()
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
        self._award_searches: dict[str, tuple[str, ...]] = {}

    def _memo_for(self, candidate: Candidate) -> None:
        """Point the page memo at this university, dropping the last one's."""
        key = f"{candidate.name}::{candidate.country}"
        if key != self._pages_for:
            self._pages = {}
            self._award_searches = {}
            self._pages_for = key

    async def _read(self, url: str, kind: str = "core") -> FetchResult:
        """Fetch a page once per run, however many programmes ask for it.

        ``kind`` is what the RL-1 read ledger charges the read as.
        """
        cached = self._pages.get(_page_key(url))
        if cached is not None:
            return cached
        with reading_as(kind):
            page = await self.fetcher.get(url)
        if page.ok:
            self._pages[_page_key(url)] = page
        return page

    async def _search_awards(
        self, candidate: Candidate, program: CandidateProgram, out: AdapterResult
    ) -> tuple[str, ...]:
        """One bounded public-policy query when an index exposes no usable awards.

        No applicant attributes enter the query. Search summaries cannot become
        evidence; the ordinary queue fetches and classifies every returned URL.
        """
        from app.adapters.discovery.live_discovery import (
            canonical_url,
            names_other_degree_level,
            registrable_domain,
            same_institution,
        )
        from app.adapters.search import get_search_provider
        from app.adapters.search.base import SearchError, search_failure_diagnostic
        from app.adapters.search.intent import DiscoveryIntent, queries_for

        # The scholarship query contains the degree, but no programme field.
        # Programmes at the same level therefore share its discovery results;
        # fetched awards are still re-parsed with each programme's own scope.
        key = str(program.degree)
        if key in self._award_searches:
            return self._award_searches[key]
        self._award_searches[key] = ()
        from app.adapters.search import intent as intent_module

        if intent_module.SHARED_QUERY_BUDGET:
            if candidate.search_queries_used >= intent_module.DEFAULT_QUERY_BUDGET:
                out.errors.append(
                    "Official scholarship search not run: earlier stages used the "
                    f"{intent_module.DEFAULT_QUERY_BUDGET}-query budget"
                )
                return ()
            candidate.search_queries_used += 1
        provider_name = "configured search provider"
        try:
            intent = DiscoveryIntent(
                institution=candidate.name,
                domain=registrable_domain(candidate.domain) or candidate.domain,
                degree=program.degree,
                field=program.field or "degree programme",
                population_marker="international",
            )
            provider = get_search_provider()
            provider_name = provider.name
            family = "award_policy" if TARGET_AWARD_SEARCH else "scholarships"
            if AWARD_ROUTE:
                family = "award_route"
                query_text = _award_route_query(candidate.name, str(program.degree))
            else:
                query_text = queries_for(intent, families=(family,), budget=1)[0].text
            response = await provider.search(
                query=query_text, domains=[intent.domain], max_results=5
            )
        except (SearchError, ValueError) as exc:
            out.errors.append(
                f"Official scholarship search: {search_failure_diagnostic(provider_name, exc)}"
            )
            return ()
        urls: list[str] = []
        for found in response.results:
            url = canonical_url(found.url)
            if urlparse(url).scheme not in ("http", "https"):
                continue
            if not any(same_institution(url, d) for d in candidate.official_domains):
                continue
            if names_other_degree_level(url, str(program.degree)) or url in urls:
                continue
            if AWARD_ROUTE:
                refused = _off_award_shape(url, candidate)
                if refused:
                    out.page_outcomes.append(
                        PageOutcome(
                            url=url,
                            category="classifier-rejected",
                            detail=f"award search result not read: {refused}",
                        )
                    )
                    continue
            urls.append(url)
        self._award_searches[key] = tuple(urls[:3])
        out.errors.append(
            f"Official scholarship search ({family}) supplied {len(urls[:3])} leads; "
            "facts require fetched award pages"
        )
        return self._award_searches[key]

    async def _route_entries(
        self,
        candidate: Candidate,
        program: CandidateProgram,
        out: AdapterResult,
        *,
        allow_search: bool,
    ) -> list[str]:
        """AR-1: official funding links on the confirmed programme page, else the hub.

        The programme page counts only once it is confirmed (``allow_search``
        is tied to a ``PROGRAM_EXISTS`` claim); the admissions hub is the
        institution's own and is read only when the programme page offers no
        funding link.
        """
        sources = []
        if allow_search and program.url:
            sources.append(("programme page", program.url))
        if candidate.admissions_url and candidate.admissions_url != program.url:
            sources.append(("admissions hub", candidate.admissions_url))
        for label, source in sources:
            if not is_official_domain(source, candidate.official_domains):
                continue
            was_read_before = _page_key(source) in self._pages
            page = await self._read(source)
            if not was_read_before:
                out.pages_checked += 1
            if not page.ok:
                out.errors.append(
                    f"{source}: {label} not read for funding links — {page.outcome.value}"
                )
                continue
            links = _funding_route_links(page.text, source, candidate, str(program.degree))
            if links:
                out.errors.append(
                    f"{source}: the {label} links {len(links)} official funding pages; "
                    "they are read before any other scholarship route."
                )
                return links
        return []

    @staticmethod
    def _route_filter(
        links: list[str], candidate: Candidate, program: CandidateProgram, out: AdapterResult
    ) -> list[str]:
        """AR-1: an index's award links without other levels and off-shape pages."""
        kept: list[str] = []
        for link in links:
            refused = _off_award_shape(link, candidate) or (
                "names another degree level"
                if _names_other_level(_url_words(link), str(program.degree))
                else ""
            )
            if refused:
                out.page_outcomes.append(
                    PageOutcome(url=link, category="classifier-rejected", detail=refused)
                )
                continue
            kept.append(link)
        return kept

    async def find(
        self, candidate: Candidate, program: CandidateProgram, profile, *, allow_search: bool = True
    ) -> tuple[list[Scholarship], AdapterResult]:
        out = AdapterResult()
        self._memo_for(candidate)
        primary = candidate.scholarships_url or ""
        # AR-1: the official funding links on the programme page or the
        # admissions hub are read before any other index or search path.
        route_entries = (
            await self._route_entries(candidate, program, out, allow_search=allow_search)
            if AWARD_ROUTE
            else []
        )
        route_keys = {_page_key(u) for u in route_entries}
        if not primary and not program.url and not route_entries:
            out.errors.append(
                f"No official scholarship page is known for {candidate.name}; funding is reported "
                "as unknown rather than assumed absent."
            )
            return [], out
        if not primary and program.url:
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
        queue: list[tuple[str, int]] = [(u, 1) for u in route_entries]
        if primary:
            queue.append((primary, 0))
        indexes_read = 0
        unproductive_indexes = 0
        linked_an_award = False
        fallback_used = primary == program.url
        search_used = False
        #: RL-1: whether the one core read of an award page was spent.
        core_award_read = False

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

            # SL-1: a funding page for another level, or outside every study
            # path, is not read; the programme and admissions pages always are.
            refused = (
                _level_scope_refusal(url, str(program.degree))
                if SCHOLARSHIP_LEVEL_SCOPE
                and key not in {_page_key(u) for u in (program.url, candidate.admissions_url) if u}
                else ""
            )
            page: FetchResult | None = None
            if refused:
                out.page_outcomes.append(
                    PageOutcome(
                        url=url, category="classifier-rejected", detail=f"SL-1: not read; {refused}"
                    )
                )
            else:
                was_read_before = _page_key(url) in self._pages
                # RL-1: the index the walk starts from answers "a scholarship
                # exists" and the first page it leads to "open to an
                # international applicant"; every later page is an award page.
                kind = "core" if depth == 0 or not core_award_read else "award"
                core_award_read = core_award_read or depth > 0
                page = await self._read(url, kind)
                if not was_read_before:
                    out.pages_checked += 1
            if page is None:
                pass
            elif not page.ok:
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

                # A page that links several awards filed beneath its own path is
                # a list of awards whatever the classifier calls it. Run 60: NTU's
                # /scholarships/freshmen holds the Nanyang Scholarship link and was
                # rejected as "not an award page".
                is_index = classification.page_type is PageType.SCHOLARSHIP_INDEX or (
                    depth > 0
                    and classification.page_type is not PageType.SCHOLARSHIP_AWARD
                    and _lists_awards_below(page.text, url)
                )
                if AWARD_ROUTE and key in route_keys:
                    # An official "Scholarships" link from the programme page
                    # is a funding route whatever the classifier calls it,
                    # unless it is one award: then it is read as that award.
                    is_index = classification.page_type is not PageType.SCHOLARSHIP_AWARD
                index_room = indexes_read < _MAX_INDEX_PAGES or (
                    # AR-1: up to five index reads while every one so far has
                    # yielded new award links.
                    AWARD_ROUTE
                    and indexes_read < _ROUTE_MAX_INDEX_PAGES
                    and unproductive_indexes == 0
                )
                out_of_scope = (
                    _award_out_of_scope(page.text, url, program)
                    if AWARD_ROUTE
                    and not is_index
                    and classification.page_type is PageType.SCHOLARSHIP_AWARD
                    else ""
                )
                if depth == 0 or (is_index and index_room):
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
                    if AWARD_ROUTE:
                        links = self._route_filter(links, candidate, program, out)
                        if not links:
                            unproductive_indexes += 1
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
                    # Every index shares one award budget, ranked together: NTU's
                    # bursaries index was read first and its 21 links took all
                    # twelve slots, so the scholarships index's Nanyang link was
                    # never read (run 57). Awards named as scholarships go first.
                    pending = [q for q in queue if q[1] > 0]
                    kept = [q for q in queue if q[1] == 0]
                    known = {_page_key(q[0]) for q in pending}
                    pending += [(link, depth + 1) for link in links if _page_key(link) not in known]
                    room = max(_MAX_AWARD_PAGES - len(scholarships), 0)
                    if AWARD_ROUTE:
                        # Programme-page routes first, then sub-indexes and
                        # awards shaped like this request.
                        pending.sort(key=lambda q: _route_priority(q[0], route_keys))
                        head = [q for q in pending if _page_key(q[0]) in route_keys]
                        rest = [q for q in pending if _page_key(q[0]) not in route_keys]
                        queue[:] = head + kept + rest[: max(room - len(head), 0)]
                    else:
                        pending.sort(key=lambda q: _award_priority(q[0]))
                        queue[:] = kept + pending[:room]
                    queued = sum(1 for link in links if any(q[0] == link for q in queue))
                    out.page_outcomes.append(
                        PageOutcome(
                            url=url,
                            category="fetched-ok",
                            page_type=page_type,
                            detail=(
                                f"read as a funding index; {len(links)} award links, "
                                f"{queued} queued within the award budget"
                            ),
                        )
                    )
                elif is_index:
                    # An index this deep is a site map, not a funding route.
                    out.errors.append(
                        f"{url}: classified as {classification.page_type.value}; not followed, "
                        f"because {indexes_read if AWARD_ROUTE else _MAX_INDEX_PAGES} index "
                        "pages have already been read."
                    )
                    out.page_outcomes.append(
                        PageOutcome(
                            url=url,
                            category="classifier-rejected",
                            page_type=page_type,
                            detail="index page beyond the index budget; not followed",
                        )
                    )
                elif out_of_scope:
                    # AR-1: an award for another degree level or faculty
                    # claims nothing for this programme.
                    out.errors.append(
                        f"{url}: award page out of scope ({out_of_scope}); no claims."
                    )
                    out.page_outcomes.append(
                        PageOutcome(
                            url=url,
                            category="classifier-rejected",
                            page_type=page_type,
                            detail=f"award out of scope: {out_of_scope}",
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
                            detail=(
                                "not an award page; no scholarship recorded "
                                f"({_award_link_summary(page.text, url)})"
                            ),
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

            if (
                SEARCH_FUNDING_FALLBACK
                and allow_search
                and not queue
                and not scholarships
                and not search_used
            ):
                search_used = True
                leads = await self._search_awards(candidate, program, out)
                queue.extend((u, 1) for u in leads if _page_key(u) not in seen_pages)
                if AWARD_ROUTE:
                    # Search results are read as indexes or awards in their own
                    # right, like a programme-page funding link.
                    route_keys |= {_page_key(u) for u in leads}

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

        award_scope = read_scope(text, title=title)
        if re.search(r"\bopen to all nationalities\b", text, re.I):
            # A statement covering every nationality must not acquire a
            # narrower audience merely because a later benefit/bond paragraph
            # mentions international students. Eligibility is read separately.
            award_scope = replace(award_scope, population=None)

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
            or is_official_domain(url, candidate.official_domains),
            extraction_method="fixture" if url.startswith("fixture://") else "html_rule",
            accessed_at=accessed_at or datetime.now(UTC),
            # Eligibility prose names a population far more often than
            # requirements prose does, and an award claimed for the wrong one
            # is the most expensive wrong answer this product can give.
            scope=award_scope,
            # The verifier's context (adversarial review, 2026-09-25): without
            # it the verbatim and domain checks were skipped.
            page_text=text,
            allowed_domains=verification_domains(url, candidate.domain, candidate.extra_domains),
        )
        _plain_add = builder.add

        def add(*args, **kwargs):
            kwargs.setdefault("subject_key", name)
            return _plain_add(*args, **kwargs)

        builder.add = add  # type: ignore[method-assign]
        # AR-1: existence and international applicability are read from the
        # award's own eligibility sentences, never from navigation or prose.
        eligibility = _eligibility_sentences(main_content(parse_html(html))) if AWARD_ROUTE else []
        if AWARD_ROUTE:
            if eligibility:
                builder.add(
                    ClaimType.SCHOLARSHIP_EXISTS,
                    name,
                    next((s for s in eligibility if name.lower() in s.lower()), eligibility[0]),
                    confidence=0.95,
                    notes=(
                        f"page classified as {classification.page_type.value}; "
                        "read from the award's eligibility sentence"
                    ),
                )
        else:
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

        # --- living allowance and duration in words ----------------------
        living = _living_allowance(text)
        if living is not None:
            value, quote = living
            builder.add(ClaimType.SCHOLARSHIP_LIVING_ALLOWANCE, value, quote)
        normal = _NORMAL_DURATION.search(text)
        if normal:
            builder.add(
                ClaimType.SCHOLARSHIP_DURATION,
                "normal_programme_duration",
                _excerpt(text, normal.start()),
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

        # Keep conditional scheme evidence without turning it into aid the
        # applicant can count on. Only the existing table route sets coverage.
        if not sch.coverage:
            policy = read_conditional_policy(html, builder.claims)
            if policy is not None:
                builder.add(
                    ClaimType.SCHOLARSHIP_COVERAGE,
                    policy.value,
                    policy.quote,
                    section="Benefits of award",
                    notes=(
                        "These conditional benefits are stated by the scheme. Applicant eligibility "
                        "and other award terms must be checked separately before counting them as aid."
                    ),
                )

        # --- eligibility -------------------------------------------------
        # This award page exists and names an award; that alone is the only
        # thing "opportunity_exists" asserts.
        sch.opportunity_exists = True

        cit = re.search(r"open only to citizens of ([^.]+)\.", text, re.IGNORECASE)
        open_to_all = _ALL_NATIONALITIES.search(text)
        if open_to_all and not cit:
            # The page's own statement that no citizenship is excluded.
            builder.add(
                ClaimType.SCHOLARSHIP_CITIZENSHIP_RESTRICTION,
                "all",
                _excerpt(text, open_to_all.start()),
                confidence=0.9,
            )
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
        international = (
            _route_international(eligibility)
            if AWARD_ROUTE
            else assess_international_eligibility(text)
        )
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
        # Global navigation names other degree levels; only the award's own
        # content can establish applicability (Groningen live capture).
        award_content = main_content(parse_html(html))
        award_text = readable_text(str(award_content))
        policy_statements = _award_policy_statements(award_content)
        applicability = assess_degree_applicability(award_text, str(program.degree))
        sch.degree_applicability = applicability.verdict
        sch.degree_applicability_reason = applicability.reason
        sch.applies_to_degrees = list(applicability.mentioned_degrees)
        study_mode = _study_mode_restriction(award_text)
        if study_mode:
            # The current programme/profile has no confirmed study mode.
            # Keep this as an unresolved programme condition; level yes alone
            # is insufficient to call the applicant eligible.
            sch.program_restrictions.append(study_mode)
        if applicability.verdict != "unknown":
            evidence = applicability.evidence
            reason = applicability.reason
            if study_mode:
                reason += "; study mode must be confirmed: " + study_mode
                if (
                    applicability.verdict == "yes"
                    and str(program.degree)
                    in assess_degree_applicability(
                        study_mode, str(program.degree)
                    ).mentioned_degrees
                ):
                    evidence = study_mode
            # Only real page text goes in the excerpt; the rationale is a note.
            builder.add(
                ClaimType.SCHOLARSHIP_PROGRAM_RESTRICTION,
                {"degree": str(program.degree), "applies": applicability.verdict},
                evidence,
                confidence=0.85 if evidence else 0.6,
                notes=reason,
            )

        # --- application mode ------------------------------------------
        application_order = _admission_application_first(policy_statements)
        if "nominated by the department" in low or "direct applications are not accepted" in low:
            sch.application_mode = ApplicationMode.NOMINATION
        elif "no separate application is required" in low or "considered automatically" in low:
            sch.application_mode = ApplicationMode.AUTOMATIC
        elif (
            "separate scholarship application" in low
            or "must be submitted in addition" in low
            or application_order
        ):
            sch.application_mode = ApplicationMode.SEPARATE
        if sch.application_mode != ApplicationMode.UNKNOWN:
            ordered_separate = bool(
                application_order and sch.application_mode is ApplicationMode.SEPARATE
            )
            builder.add(
                ClaimType.SCHOLARSHIP_APPLICATION_MODE,
                sch.application_mode.value,
                application_order
                if ordered_separate
                else _line_with(text, "how to apply") or _line_with(text, "application"),
                notes=(
                    "The admission application must be submitted before the scholarship application."
                    if ordered_separate
                    else ""
                ),
            )
        sch.requires_extra_essays = _required_extra_essay(policy_statements)

        grant_bond = _tuition_grant_bond(policy_statements, name)
        if grant_bond:
            value, quote = grant_bond
            builder.add(
                ClaimType.SCHOLARSHIP_BOND,
                value,
                quote,
                population="Singapore PRs and international students",
                notes=(
                    "The scholarship has no separate award bond; the stated three-year obligation "
                    "belongs to the MOE Tuition Grant Scheme for Singapore PRs and international "
                    "students."
                ),
            )

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
        # A retention condition stated with its scale and review period is a
        # renewal requirement whether or not the page says "renewable".
        retention = _renewal_condition(text)
        if retention is not None:
            value, quote = retention
            sch.renewal_requirements.append(quote)
            builder.add(ClaimType.SCHOLARSHIP_RENEWAL_REQUIREMENT, value, quote)
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
                if retention is not None:
                    break
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
        withdrawn = _withdrawn_award_quote(text)
        if withdrawn:
            sch.currently_available = "no"
            sch.award_current_for_intake = "no"
            builder.add(ClaimType.SCHOLARSHIP_EXISTS, False, withdrawn, confidence=0.7)

        self._derive_availability(sch, self.today)
        sch.claim_ids = [c.source_url for c in builder.claims]
        return sch, builder.claims

    @staticmethod
    def _derive_availability(sch: Scholarship, today: date | None = None) -> None:
        """Roll the separate states up, conservatively.

        A missing deadline used to read as "available". It now reads as
        unknown, because not finding a date is not the same as there being no
        date.

        ``today`` is the run's assessment day (UTC). It used to be the server's
        local ``date.today()``, read here behind a function-local import: a
        different clock and time zone from the one the runner assesses with,
        and one nothing could pin, so a stored result changed when the
        calendar crossed an award's deadline.
        """
        today = today if today is not None else datetime.now(UTC).date()

        sch.deadline_known = sch.deadline is not None
        sch.deadline_passed = bool(sch.deadline and sch.deadline < today)

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


def _study_mode_restriction(text: str) -> str:
    """Retain an explicit awardee programme-mode condition in its own words."""
    flat = " ".join(text.split())
    requirement = re.compile(
        r"\b(?:successful\s+awardees?|scholarship\s+holders?|recipients?|applicants?)\s+"
        r"(?:must|should|(?:are|is)\s+required\s+to)\s+"
        r"(?:read|pursue|be\s+enrolled\s+in)\s+"
        r"(?:an?\s+)?full[- ]time\s+"
        r"(?:undergraduate|bachelor['’]?s?|master['’]?s?|postgraduate|doctoral)\s+"
        r"(?:degree\s+)?(?:programmes?|programs?|degrees?|courses?)\b",
        re.I,
    )
    for sentence in re.split(r"(?<=[.!?])\s+", flat):
        if len(sentence) > 300 or re.search(r"\b(?:if|when|unless)\b", sentence, re.I):
            continue
        match = requirement.search(sentence)
        if match and not re.search(
            r"\b(?:not\s+(?:required|necessary|obligatory)|no\s+requirement)\s+"
            r"(?:(?:that|for)\s+)?$",
            sentence[: match.start()],
            re.I,
        ):
            return sentence
    return ""


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


#: "for the normal duration of the programme", "normal candidature",
#: "the minimum duration of the course" — a duration stated as the
#: programme's own length rather than a number of years.
_NORMAL_DURATION = re.compile(
    r"\b(?:normal|standard|minimum)\s+(?:(?:programme|program|course|degree)\s+)?"
    r"(?:candidature|duration|length|period)"
    r"(?:\s+of\s+(?:the|their|your|his|her)?\s*(?:programme|program|course|study|studies|degree))?",
    re.IGNORECASE,
)
_LIVING_LINE = re.compile(
    r"[^.\n]*\b(?:living|maintenance|subsistence)\s+(?:allowance|stipend|subsidy)[^.\n]*",
    re.IGNORECASE,
)
_PER_YEAR = re.compile(
    r"\b(?:per|a|each)\s+(?:academic\s+)?(?:year|annum)\b|\bannual(?:ly)?\b", re.I
)
_PER_MONTH = re.compile(r"\b(?:per|a|each)\s+month\b|\bmonthly\b", re.I)

_ADMISSION_APPLICATION_FIRST = re.compile(
    r"^applicants\s+(?:are required to|must)\s+submit their application for admission\s+"
    r"before submitting their application for scholarship\b",
    re.I,
)
_EXTRA_ESSAY = re.compile(
    r"\b(?:personal essay|additional essays?|statement of motivation)\b", re.I
)
_ESSAY_REQUIRED = re.compile(r"\b(?:requires?|required|must|compulsory|mandatory)\b", re.I)
_OPTIONAL_POLICY = re.compile(
    r"\b(?:optional|voluntary|may|might|could)\b"
    r"|\b(?:not|never)\s+(?:required|compulsory|mandatory)\b"
    r"|\b(?:do|does)\s+not\s+(?:require|need|submit)\b"
    r"|\bno\s+requirement\b",
    re.I,
)
_TUITION_GRANT_BOND = re.compile(
    r"^no bond is attached to (?P<award>.+?) apart from the (?:three|3)[- ]year bond "
    r"applicable to all Singapore PRs and international students under the "
    r"MOE Tuition Grant Scheme\b",
    re.I,
)


def _award_policy_statements(content: BeautifulSoup) -> list[str]:
    """Complete sentences from the award's own paragraphs and list items.

    A wrapped clause belongs to its HTML block. A complete statement above
    the evidence cap is omitted, rather than losing an exception to clipping.
    """
    out: list[str] = []
    for block in content.find_all(["p", "li"]):
        text = " ".join(block.get_text(" ", strip=True).split())
        for statement in re.split(r"(?<=[.!?])\s+", text):
            if statement and len(statement) <= MAX_EXCERPT_CHARS and statement not in out:
                out.append(statement)
    return out


def _admission_application_first(statements: list[str]) -> str:
    """Two submitted applications establish order, not an admission offer."""
    for statement in statements:
        if (
            _ADMISSION_APPLICATION_FIRST.search(statement)
            and not _OPTIONAL_POLICY.search(statement)
            and not re.search(r"\b(?:if|when|unless)\b", statement, re.I)
        ):
            return statement
    return ""


def _required_extra_essay(statements: list[str]) -> bool:
    for statement in statements:
        if (
            _EXTRA_ESSAY.search(statement)
            and _ESSAY_REQUIRED.search(statement)
            and not _OPTIONAL_POLICY.search(statement)
            and not re.search(r"\b(?:if|when|unless)\b", statement, re.I)
            and not re.search(r"\b(?:must|shall|should)\s+not\b", statement, re.I)
            and not re.search(
                r"\bno\s+(?:(?:required|compulsory|mandatory)\s+)?"
                r"(?:personal essay|additional essays?|statement of motivation)\b",
                statement,
                re.I,
            )
        ):
            return True
    return False


def _tuition_grant_bond(statements: list[str], name: str) -> tuple[dict[str, object], str] | None:
    """Keep the grant exception when the award itself has no service bond."""
    for statement in statements:
        match = _TUITION_GRANT_BOND.search(statement)
        if (
            match
            and match.group("award").casefold() in (name.casefold(), "the " + name.casefold())
            and not _OPTIONAL_POLICY.search(statement)
        ):
            return {
                "years": 3,
                "basis": "MOE_Tuition_Grant",
                "population": ["Singapore_PR", "international"],
            }, statement
    return None


_ALL_NATIONALITIES = re.compile(
    r"\bopen to (?:applicants of |students of )?all nationalities\b", re.I
)
_RETENTION_GPA = re.compile(
    r"(?:minimum|at least)\s+(?:a\s+)?(?:cumulative\s+)?(?:grade point average|c?gpa)"
    r"(?:\s*\((?:c?gpa)\))?\s+of\s+(\d+(?:\.\d+)?)\s+(?:over|out of)\s+(\d+(?:\.\d+)?)",
    re.I,
)
_REVIEW_PERIOD = (
    (re.compile(r"reviewed\s+(?:every|each)\s+semester", re.I), "each_semester"),
    (
        re.compile(r"reviewed\s+(?:every|each)\s+(?:academic\s+)?year|reviewed\s+annually", re.I),
        "each_year",
    ),
)


def _renewal_condition(text: str) -> tuple[dict[str, object], str] | None:
    """A minimum grade to keep the award, on its stated scale, or nothing.

    The scale must be on the page ("3.5 over 5.0"): a bare 3.5 means nothing
    to an applicant whose grades are on another scale. The review period is
    added only when the page states it.
    """
    match = _RETENTION_GPA.search(text)
    if match is None:
        return None
    value: dict[str, object] = {
        "cgpa_gte": float(match.group(1)),
        "scale": float(match.group(2)),
    }
    quote = _excerpt(text, match.start())
    for pattern, period in _REVIEW_PERIOD:
        review = pattern.search(text)
        if review is not None:
            value["review"] = period
            break
    return value, quote


def _living_allowance(text: str) -> tuple[dict[str, object], str] | None:
    """A living allowance with its amount, currency and period, or nothing.

    All three must be on the page's own line: an amount without a period is
    not an allowance anyone can plan with, so none is invented.
    """
    for match in _LIVING_LINE.finditer(text):
        line = match.group(0).strip()
        money = parse_money(line)
        if not money:
            continue
        if _PER_MONTH.search(line):
            period = "month"
        elif _PER_YEAR.search(line):
            period = "academic_year"
        else:
            continue
        amount, currency = money
        # S$6,500 is a whole amount; 6500.0 would not equal the page's figure
        # anywhere a value is compared as written.
        if float(amount).is_integer():
            amount = int(amount)
        return {"currency": currency, "amount": amount, "period": period}, line
    return None


#: Pages about an award rather than one award, or awards for someone else:
#: FAQs, graduate study, enrolled students, exchanges and teaching prizes.
#: Run 59: NTU's twelve award slots went to these, Nanyang Scholarship unread.
_OFF_TARGET_AWARD = re.compile(
    r"faqs?\b|/(post)?graduate/|(?<!under)graduate-|current-students?|student-exchanges?|"
    r"inbound|teaching|/education/|diploma|staff|innovat|research|fellow|seed-?fund|"
    r"grants-funding|accolade|life-at",
    re.I,
)


#: How many award links under a page's own path make it a list of awards.
_CHILD_AWARDS_FOR_INDEX = 3


def _lists_awards_below(html: str, url: str) -> bool:
    """True when the page links at least three awards filed beneath its own path."""
    own = re.sub(r"(/index)?\.html?$", "", urlparse(url).path.rstrip("/").lower()) + "/"
    below = [
        link for link in _award_links(html, url) if urlparse(link).path.lower().startswith(own)
    ]
    return len(below) >= _CHILD_AWARDS_FOR_INDEX


def _award_link_summary(html: str, url: str) -> str:
    """How many award links a rejected page carries, and a few of them.

    Run 61: NTU's /scholarships/freshmen stayed rejected and nothing said what
    it linked, so the next fix would have been a guess.
    """
    links = _award_links(html, url)
    own = re.sub(r"(/index)?\.html?$", "", urlparse(url).path.rstrip("/").lower()) + "/"
    below = sum(1 for link in links if urlparse(link).path.lower().startswith(own))
    sample = ", ".join(urlparse(link).path for link in links[:4])
    return f"{len(links)} award links, {below} below it: {sample}"


def _award_priority(url: str) -> tuple[int, int]:
    """Lower reads first: a named scholarship, then awards, then need-based aid;
    within each, a page for an incoming applicant before one for someone else."""
    path = urlparse(url).path.lower()
    off_target = 1 if _OFF_TARGET_AWARD.search(path) else 0
    if "scholarship" in path:
        return (off_target, 0)
    if re.search(r"bursar|financial-?aid|loan|hardship", path):
        return (off_target, 2)
    return (off_target, 1)


def _award_links(html: str, base: str) -> list[str]:
    """Links from a funding index page that plausibly describe one award.

    Real index pages are mostly site furniture. Following every anchor turned
    "Menu główne" and "Skip to main content" into scholarships, so a link now
    has to look like an award in its text or its path to be followed.
    """
    soup = parse_html(html)
    if SEARCH_FUNDING_FALLBACK:
        soup = main_content(soup)
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


#: AR-1: how many index reads the walk may spend when each one is productive.
_ROUTE_MAX_INDEX_PAGES = 5
#: AR-1: how many official funding links one programme page may supply.
_ROUTE_MAX_ENTRY_LINKS = 3
#: A link naming funding in its text or its path.
_FUNDING_LINK = re.compile(
    r"scholarship|\bfunding\b|\bawards?\b|financial[- ]?aid|bursar(?:y|ies)", re.I
)
#: An index or award shaped like an international undergraduate request.
_REQUEST_SHAPE = re.compile(
    r"international|overseas|undergrad|bachelor|entrance|first[- ]year|freshm|incoming", re.I
)
_LEVEL_WORDS = {
    "foundation": r"\bfoundation (?:year|programme|program)\b",
    "bachelor": r"\b(?:undergraduates?|bachelor'?s?|freshm[ae]n|first[- ]year)\b",
    "master": r"\b(?:master'?s?|postgraduates?|graduate|taught postgraduate|mba)\b",
    "phd": r"\b(?:ph\.?d|doctoral|doctorate|research degrees?)\b",
}
#: Mail-tracking redirectors on the institution's own domain
#: (``massmailer.univie.ac.at``) are not pages about an award.
_MAIL_TRACKING_HOST = re.compile(
    r"^(?:[\w-]+\.)*?(?:(?:mass)?mail(?:er|ing|chimp)?\d*|newsletter|list-manage|click"
    r"|track(?:ing)?|links?|email)\.",
    re.I,
)
_MAIL_TRACKING_PATH = re.compile(r"/(?:track|click|redirect|r)/|[?&](?:utm_|mc_eid|mc_cid)", re.I)
_NEWS_PATH = re.compile(
    r"/(?:news|posts?|blogs?|stories|story|events?|press|newsroom|articles?|media-releases?)"
    r"(?:/|$|-)",
    re.I,
)
_COUNTRY_PATH = re.compile(r"/(?:countr(?:y|ies)|your-country|nationalit(?:y|ies))(?:/|$)", re.I)
#: The host labels of faculty sites; their funding pages are for that faculty.
_FACULTY_HOSTS = frozenset(
    {"arts", "law", "medicine", "med", "music", "nursing", "dentistry", "pharmacy", "business"}
)


def _url_words(url: str) -> str:
    parts = urlparse(url)
    return re.sub(r"[/_.\-]+", " ", f"{parts.path} {parts.query}").lower()


def _names_other_level(text: str, degree: str) -> bool:
    """Whether text names another degree level and never the requested one."""
    own = _LEVEL_WORDS.get(degree)
    if own and re.search(own, text, re.I):
        return False
    return any(
        re.search(pattern, text, re.I) for level, pattern in _LEVEL_WORDS.items() if level != degree
    )


#: SL-1: URL words naming a level above a bachelor's, a studentship included.
_ABOVE_BACHELOR = re.compile(
    r"\b(?:ph\.?d|doctoral|doctorate|postgrad\w*|pgt|pgr|master'?s?|msc|mres|mphil|mba"
    r"|studentships?|research degrees?)\b",
    re.I,
)
#: SL-1: URL words naming funding that is not, by itself, a study path.
_FUNDING_WORDS = re.compile(r"\b(?:funding|funds?|grants?|awards?|honours|prizes?)\b", re.I)
#: SL-1: URL words of a study, admissions, fees or scholarships path.
_STUDY_PATH_WORDS = re.compile(
    r"\b(?:study|studies|studying|admissions?|admit|apply|applying|applicants?|undergrad\w*"
    r"|bachelors?|prospective|future students?|students?|fees?|tuition|scholarships?"
    r"|bursar(?:y|ies)|financial aid|financial support|freshm[ae]n|entrance|international)\b",
    re.I,
)


def _level_scope_refusal(url: str, degree: str) -> str:
    """SL-1: why a funding page is not read for a bachelor request, or empty."""
    if degree != "bachelor":
        return ""
    words = _url_words(url)
    if _ABOVE_BACHELOR.search(words) and not re.search(_LEVEL_WORDS["bachelor"], words, re.I):
        return "the URL names another degree level than bachelor"
    if _FUNDING_WORDS.search(words) and not _STUDY_PATH_WORDS.search(words):
        return "a funding page outside every study, admissions or scholarships path"
    return ""


def _off_award_shape(url: str, candidate: Candidate) -> str:
    """Why a URL is not a page about an award, or empty (AR-1 shape filter)."""
    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    path = parts.path.lower()
    if _MAIL_TRACKING_HOST.match(host) or _MAIL_TRACKING_PATH.search(f"{path}?{parts.query}"):
        return "a mail-tracking link"
    if _NEWS_PATH.search(path):
        return "a news item or post"
    if _COUNTRY_PATH.search(path):
        return "a country page"
    if path.endswith(".pdf") and not (
        is_official_domain(url, candidate.official_domains) and "scholarship" in path
    ):
        return "a PDF outside the official scholarships path"
    return ""


def _funding_route_links(html: str, base: str, candidate: Candidate, degree: str) -> list[str]:
    """Official funding links on a programme page or hub, best shaped first (AR-1)."""
    from app.adapters.discovery.live_discovery import names_other_degree_level, same_institution

    found: list[tuple[int, int, str]] = []
    seen: set[str] = {_page_key(base)}
    for content in (main_content(parse_html(html)), parse_html(html)):
        for order, a in enumerate(content.find_all("a", href=True)):
            href = a["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            url = _page_key(urljoin(base, href))
            if url in seen or urlparse(url).scheme not in ("http", "https"):
                continue
            if not any(same_institution(url, d) for d in candidate.official_domains if d):
                continue
            label = " ".join(a.get_text(" ", strip=True).split())
            words = f"{label.lower()} {_url_words(url)}"
            if not _FUNDING_LINK.search(words):
                continue
            seen.add(url)
            if (
                _off_award_shape(url, candidate)
                or _DOMESTIC_ONLY.search(url)
                or names_other_degree_level(url, degree)
                or _names_other_level(words, degree)
            ):
                continue
            found.append((0 if _REQUEST_SHAPE.search(words) else 1, order, url))
        if found:
            break
    found.sort()
    return [url for _, _, url in found[:_ROUTE_MAX_ENTRY_LINKS]]


def _route_priority(url: str, route_keys: set[str]) -> tuple[int, int, int, int]:
    """Programme-page routes, then request-shaped sub-indexes, then the rest (AR-1)."""
    off_target, kind = _award_priority(url)
    shaped = 0 if _REQUEST_SHAPE.search(_url_words(url)) else 1
    return (0 if _page_key(url) in route_keys else 1, off_target, shaped, kind)


def _award_route_query(institution: str, degree: str) -> str:
    """The AR-1 award query: the institution and the population, no applicant data."""
    level = {
        "foundation": "foundation",
        "bachelor": "undergraduate",
        "master": "postgraduate",
        "phd": "doctoral",
    }.get(degree, "undergraduate")
    return f"{institution} scholarships international {level} students"


_GENERIC_SUBJECT_WORDS = frozenset(
    {"bachelor", "master", "degree", "programme", "program", "studies", "honours"}
)


def _award_out_of_scope(html: str, url: str, program: CandidateProgram) -> str:
    """Why an award page claims nothing for this programme, or empty (AR-1)."""
    award_text = readable_text(str(main_content(parse_html(html))))
    if assess_degree_applicability(award_text, str(program.degree)).verdict == "no":
        return "the award is for another degree level"
    subject_words = (
        set(re.findall(r"[a-z]{4,}", f"{program.name} {program.field}".lower()))
        - _GENERIC_SUBJECT_WORDS
    )
    host_label = (urlparse(url).hostname or "").lower().split(".")[0]
    if host_label in _FACULTY_HOSTS and subject_words and host_label not in subject_words:
        return f"a funding page of the {host_label} faculty site"
    faculty = _restricted_to(award_text, _FACULTY_RESTRICTION)
    if faculty and subject_words:
        named = set(re.findall(r"[a-z]{4,}", faculty.group("subject").lower()))
        if not named & subject_words:
            return f"restricted to {faculty.group('subject').strip()}"
    return ""


#: Sentences that state who may hold an award.
_ELIGIBILITY_CUE = re.compile(
    r"\beligib|\bopen to\b|\bavailable (?:to|for)\b|\bwho can apply\b|\bapplicants? must\b"
    r"|\bcandidates? must\b|\bstudents? must\b|\bawarded to\b|\brestricted to\b"
    r"|\blimited to\b|\bmay apply\b|\bcan apply\b|\bcriteria\b",
    re.I,
)
_DOMESTIC_SENTENCE = re.compile(
    r"\b(?:domestic|home|local)(?:[- ]fee)? (?:students?|applicants?)\b"
    r"|\bpermanent residents?\b|\bhome fee status\b",
    re.I,
)
_INTERNATIONAL_WORD = re.compile(r"\binternational\b|\boverseas\b|\bnon-?(?:eu|eea)\b", re.I)
#: A named population: "students from Belarus", "citizens of Kazakhstan".
_POPULATION_RESTRICTION = re.compile(
    r"\b(?:students?|applicants?|candidates?|citizens?|nationals?)\s+(?:from|of)\s+(?:the\s+)?"
    r"(?!(?:All|Any|Outside|Abroad|Overseas|Other|University|Faculty|School|College|Department"
    r"|Institute)\b)[A-Z][a-z]+"
    r"|\b(?:from|of)\s+(?:developing|low[- ]income|eligible|selected|partner|specific|"
    r"listed)\s+countries\b|\bcitizenship of\b",
)


def _eligibility_sentences(content: BeautifulSoup) -> list[str]:
    """The award's own sentences that say who may hold it (AR-1)."""
    return [s for s in _award_policy_statements(content) if _ELIGIBILITY_CUE.search(s)]


def _route_international(sentences: list[str]) -> Applicability:
    """International applicability from eligibility sentences only (AR-1).

    A domestic-only sentence ("home students", "permanent residents") is a no;
    a sentence naming one population ("students from Belarus") can never make
    the award open to international applicants in general.
    """
    for sentence in sentences:
        if _DOMESTIC_SENTENCE.search(sentence) and not _INTERNATIONAL_WORD.search(sentence):
            return Applicability("no", "the award is for domestic students only", sentence)
    verdict = assess_international_eligibility(" ".join(sentences))
    if verdict.verdict == "yes" and any(_POPULATION_RESTRICTION.search(s) for s in sentences):
        return Applicability(
            "unknown",
            "the award is restricted to a named population, not to international "
            "applicants in general",
        )
    return verdict


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


def _withdrawn_award_quote(text: str) -> str:
    """Read scheme closure without treating a holder's revocation as closure.

    Evaluate each statement independently: a retention condition cannot hide
    a later actual cancellation on the same page. A wrapped if/when/unless
    clause belongs to the preceding statement, rather than a different award.
    """
    statements = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
    for index, statement in enumerate(statements):
        context = statement
        if (
            not statement.endswith((".", "!", "?"))
            and index + 1 < len(statements)
            and re.match(r"^(?:if|when|unless)\b", statements[index + 1], re.I)
        ):
            context += " " + statements[index + 1]
        for match in _AWARD_WITHDRAWN.finditer(statement):
            prefix = statement[: match.start()]
            denied = re.search(
                r"\b(?:not|never)\s+(?:(?:been|ever|previously|actually|formally|yet)\s+){0,3}$",
                prefix,
                re.I,
            )
            if denied:
                continue
            if match.group().lower() == "withdrawn":
                # Possible or conditional holder withdrawal does not say
                # that the entire scholarship scheme has closed.
                possible = re.search(r"\b(?:may|might|can|could|would)\b.{0,120}$", prefix, re.I)
                conditional = re.search(r"\b(?:if|when|unless)\b", context, re.I)
                individual = re.search(
                    r"\b(?:your|his|her|their)\s+(?:scholarship|award|offer)\b"
                    r"|\b(?:scholarship|award|admission)\s+offer\b",
                    prefix,
                    re.I,
                ) or re.search(
                    r"\bfrom\s+(?:(?:an?|the)\s+)?(?:holder|recipient|student|scholar)\b",
                    statement[match.end() :],
                    re.I,
                )
                if possible or conditional or individual:
                    continue
            # Keep the complete decisive statement in the existing quote cap.
            # Truncating away its predicate would manufacture closure evidence.
            if len(statement) <= 300:
                return statement
    return ""


def _line_with(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle.lower() in line.lower():
            return line.strip()[:300]
    return ""


def _excerpt(text: str, at: int, radius: int = 150) -> str:
    return text[max(0, at - radius) : at + radius].replace("\n", " ").strip()

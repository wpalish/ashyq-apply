"""Admission requirements from official pages.

Two guards separate this from the version that produced live false positives:

* the page is classified first, and each extractor runs only on page classes
  that could actually answer its question;
* a positive claim needs positive evidence. The absence of "applications are
  closed" is not evidence that an intake is open.

URL-scheme agnostic on purpose: the same adapter reads a bundled ``fixture://``
page and a live university page, so demo mode rehearses the real path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.adapters.base import AdapterResult, Candidate, CandidateProgram, PageOutcome
from app.adapters.discovery.live_discovery import matches_field_text
from app.adapters.document_ir import build_document_ir
from app.adapters.extraction import (
    ClaimBuilder,
    excerpt_around,
    extract_admission_route,
    extract_costs,
    extract_programme_faculty,
    extract_requirements,
    for_matching,
    html_title,
    is_official_domain,
    pdf_to_text,
    readable_text,
    verification_domains,
)
from app.adapters.fetching import Fetcher, same_source_site
from app.adapters.matching import degree_matches, program_matches
from app.adapters.page_classifier import (
    PageType,
    classify_page,
    degree_level_of,
    full_degree_titles,
)
from app.adapters.requirements.section_scope import full_degree_sections
from app.adapters.scope_reader import read_scope
from app.adapters.search.ontology import titles_name_same_programme
from app.adapters.structured_extraction import extract_table_requirements
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.enums import ClaimType, FetchOutcome, SourceSpecificity
from app.domain.programme_identity import Verdict
from app.schemas.claim import MAX_EXCERPT_CHARS

#: An intake is open only when a page says so. Each pattern must capture the
#: sentence it matched, which becomes the claim's excerpt.
_INTAKE_OPEN_EVIDENCE: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "application window",
        re.compile(
            r"[^.]*\bapplications?\b[^.]{0,80}\b(?:open|opens|opened|will open)\b[^.]{0,80}\.", re.I
        ),
    ),
    (
        "currently accepting",
        re.compile(
            r"[^.]*\b(?:now accepting|currently accepting|accepting applications|applications are open)\b[^.]{0,80}\.",
            re.I,
        ),
    ),
    (
        "apply now for cycle",
        re.compile(r"[^.]*\bapply (?:now|online|here)\b[^.]{0,80}\b(20\d{2})\b[^.]{0,60}\.", re.I),
    ),
)
_INTAKE_CLOSED_EVIDENCE = re.compile(
    r"[^.]*\b(?:applications? (?:are |is )?closed|no longer accepting|admissions? (?:are |is )?closed"
    r"|intake (?:is )?closed|not accepting applications)\b[^.]{0,80}\.",
    re.I,
)
#: A sentence that settles whether the English test can be skipped. Broad on
#: purpose about *how* it is phrased and narrow about *what* it is about: the
#: `_MENTIONS_ENGLISH` check below is what keeps a fee waiver out.
_ENGLISH_WAIVER = re.compile(
    r"[^.]*\b(exempt(?:ed|ions?)?|waive(?:d|s|r|rs)?|not required to (?:submit|provide|take)"
    r"|do(?:es)? not need to (?:submit|provide|take))\b[^.]*\.",
    re.IGNORECASE,
)
#: The denial, which must be its own pattern. Reusing the fee-waiver negation
#: read "you do not need to submit IELTS if..." — a waiver in plain words — as
#: a refusal of one, which is the most expensive way to be wrong here.
_NO_ENGLISH_WAIVER = re.compile(
    r"\bno\s+(?:waivers?|exemptions?)\b"
    r"|\b(?:waivers?|exemptions?)\s+(?:are|is)\s+not\s+(?:granted|available|possible|offered)"
    r"|\bcannot\s+be\s+waived\b"
    r"|\bis\s+required\s+of\s+all\s+applicants\b",
    re.IGNORECASE,
)
_MENTIONS_ENGLISH = re.compile(
    r"\b(english|ielts|toefl|duolingo|pte|language (?:test|requirement|proficiency))\b",
    re.IGNORECASE,
)


#: A "fee waiver" line only yields a claim when the page actually settles the
#: question. Negation is positive evidence of absence and is claimed as False;
#: a line that merely mentions waivers settles nothing — unknown stays
#: unknown, never a confident True.
_WAIVER_NEGATION = re.compile(
    r"\b(no|not|never|neither|nor|without|cannot|can'?t|won'?t|isn'?t|aren'?t"
    r"|doesn'?t|don'?t|unavailable)\b",
    re.IGNORECASE,
)
_WAIVER_OFFERED = re.compile(r"\b(available|offered|granted|waive[ds]?|waiving)\b", re.IGNORECASE)


#: Experiment ER-08 (expert trace 2026-10-04), on since the 10-case paired run
#: 37279746829 (owner approved 2026-10-05); False turns it off.
#: After a programme page is known, one public query per topic finds the
#: official page that publishes it. Groningen, NTU and HKU each answered the
#: English, fee and deadline questions on pages this adapter never opened,
#: and each was the top same-institution result of one query.
TOPIC_SEARCH = True
#: Topic name to the public query; only the institution name is filled in.
#: Plan rule TS-2: a failed topic query no longer ends topic search for the
#: institution; the next topic is still asked (NTU, run claude-sr1-paired-1:
#: two of four repetitions lost all three topics to one failed query).
TOPIC_SEARCH_CONTINUE = False
_TOPIC_QUERIES = (
    ("english", "{name} undergraduate English language requirements international applicants"),
    ("fees", "{name} undergraduate tuition fees international students"),
    ("deadline", "{name} undergraduate application deadline international students"),
)


@dataclass(frozen=True)
class _Target:
    url: str
    specificity: SourceSpecificity
    #: Reached by following an English-requirement link from an official page.
    language_follow: bool = False
    #: Found by experiment ER-08 for this topic.
    topic: str | None = None
    #: Reached by following a route or deadline link (plan rule RL-1).
    route_follow: bool = False


#: Language-requirement pages followed per programme, beyond the two targets.
_MAX_LANGUAGE_FOLLOWS = 2
_LANGUAGE_LINK = re.compile(
    r"english[\s-]+(language|proficiency|competency|requirement)|language[\s-]+"
    r"(requirement|proficiency|competency|admission)|\bielts\b",
    re.I,
)


def _language_links(html: str, base: str, domain: str | None) -> list[str]:
    """Official links on a page whose text or URL names an English requirement."""
    if not domain:
        return []
    out: list[str] = []
    for link in build_document_ir(html, base).links:
        url = link.url.split("#")[0]
        if not url.startswith(("https://", "http://", "fixture://")):
            continue
        if not (url.startswith("fixture://") or is_official_domain(url, [domain])):
            continue
        named = _LANGUAGE_LINK.search(link.text) or _LANGUAGE_LINK.search(url.replace("/", " "))
        if named and url not in out and url.rstrip("/") != base.rstrip("/"):
            out.append(url)
    return out


#: Plan rule RL-1 (control run claude-control-twopass-1, 2026-10-06): the
#: deadline and the English minimum often sit two or three official links below
#: the admissions hub the adapter reads (Delft: hub -> "BSc - International
#: diploma" -> "Admission Requirements" / "Dates & Deadlines"; UBC: hub ->
#: "Dates and deadlines"). On since paired run 37545452839 (2 stable gains,
#: 0 losses; owner delegation 2026-10-06). False turns it off.
ROUTE_LEADS = True
#: Route and deadline pages followed per programme, beyond every other target.
_MAX_ROUTE_FOLLOWS = 4
_DEADLINE_LEAD = re.compile(
    r"\bdates?\s*(?:&|and)\s*deadlines?\b|\bapplication\s+deadlines?\b|\bkey\s+dates\b", re.I
)
#: The undergraduate route for an applicant with a foreign school diploma.
_ROUTE_LEAD = re.compile(
    r"\binternational\s+(?:diploma|high\s+schools?|secondary|qualifications?)\b"
    r"|\bnon[\s-]dutch\b|\bforeign\s+(?:diploma|qualifications?)\b",
    re.I,
)
#: A bare "Admission requirements" link, followed only from a page that is
#: already on the international route, so a domestic route is never read.
_REQUIREMENTS_LEAD = re.compile(r"^\s*(?:admission|entry)\s+requirements\s*$", re.I)
_ON_ROUTE = re.compile(r"international|non-dutch|foreign", re.I)
_GRADUATE_LEAD = re.compile(r"\b(?:msc|master'?s?|phd|doctoral|postgraduate|graduate)\b", re.I)


def _route_links(
    html: str, base: str, domain: str | None, *, deadline: bool, requirements: bool
) -> list[tuple[str, bool]]:
    """Same-site links to the deadline or the foreign-diploma route (RL-1).

    Each item is ``(url, is_requirements_page)``. Link text decides; a link
    that names a graduate route is never followed.
    """
    if not domain:
        return []
    on_route = bool(_ON_ROUTE.search(base))
    out: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for link in build_document_ir(html, base).links:
        url = link.url.split("#")[0]
        text = " ".join(link.text.split())
        if not url.startswith(("https://", "http://", "fixture://")) or url in seen:
            continue
        if not (url.startswith("fixture://") or is_official_domain(url, [domain])):
            continue
        if url.rstrip("/") == base.rstrip("/") or _GRADUATE_LEAD.search(text):
            continue
        if (deadline and _DEADLINE_LEAD.search(text)) or (
            requirements and _ROUTE_LEAD.search(text)
        ):
            out.append((url, False))
        elif requirements and on_route and _REQUIREMENTS_LEAD.search(text):
            out.append((url, True))
        else:
            continue
        seen.add(url)
    return out


class WebRequirementsAdapter:
    name = "web-requirements"

    def __init__(self, fetcher: Fetcher, academic_year: str) -> None:
        self.fetcher = fetcher
        self.academic_year = academic_year
        #: Topic pages found per institution: programmes of one university
        #: share them, so each query is sent once per run.
        self._topic_pages: dict[str, tuple[tuple[str, str], ...]] = {}

    async def verify(
        self, candidate: Candidate, program: CandidateProgram, intake: str
    ) -> AdapterResult:
        out = AdapterResult()

        # Two sources on purpose: the programme page and the general admissions
        # page. When they disagree the conflict detector has something to find.
        targets = [
            _Target(program.url, SourceSpecificity.PROGRAM_INTAKE) if program.url else None,
            _Target(candidate.admissions_url, SourceSpecificity.UNIVERSITY_ADMISSIONS)
            if candidate.admissions_url
            else None,
        ]
        queue = [t for t in targets if t]
        visited = {t.url for t in queue}
        if TOPIC_SEARCH and program.url:
            for topic, url in await self._find_topic_pages(candidate, program, out):
                if url not in visited:
                    visited.add(url)
                    queue.append(_Target(url, SourceSpecificity.UNIVERSITY_ADMISSIONS, topic=topic))
        followed = 0
        routed = 0
        while queue:
            target = queue.pop(0)
            res = await self.fetcher.get(target.url)
            out.pages_checked += 1
            if not res.ok:
                out.pages_failed += 1
                out.errors.append(f"{target.url}: {res.outcome.value} — {res.error}")
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="fetch-failed",
                        detail=f"{res.outcome.value} — {res.error}",
                    )
                )
                if res.outcome in (
                    FetchOutcome.TIMEOUT,
                    FetchOutcome.NETWORK_UNAVAILABLE,
                    FetchOutcome.HTTP_ERROR,
                ):
                    out.retry_urls.append(target.url)
                continue
            if not same_source_site(target.url, res.final_url or target.url):
                out.pages_failed += 1
                out.errors.append(
                    f"{target.url}: redirected off the source site; no requirements verified"
                )
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="fetch-failed",
                        detail="redirected off the source site",
                    )
                )
                continue

            text = pdf_to_text(res.content) if res.is_pdf else readable_text(res.text)
            if not text.strip():
                out.pages_failed += 1
                out.errors.append(
                    f"{target.url}: page fetched but no readable text could be extracted"
                )
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="unreadable",
                        detail="page fetched but no readable text could be extracted",
                    )
                )
                continue

            page_url = res.final_url or target.url
            page = classify_page(url=page_url, html="" if res.is_pdf else res.text, text=text)
            out.page_types.append((target.url, page.page_type.value))

            if (
                target.url == program.url
                and page.accepts("program_exists")
                and page.degree_level
                and program.degree
                and str(page.degree_level) != str(program.degree)
            ):
                out.errors.append(
                    f"{target.url}: final page {page_url} names {page.degree_level}; "
                    f"cannot verify the requested {program.degree} programme"
                )
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="classifier-rejected",
                        page_type=page.page_type.value,
                        readable_chars=len(text),
                        detail="final page names a different degree level",
                    )
                )
                continue

            page_title = html_title(res.text) if not res.is_pdf else page_url.rsplit("/", 1)[-1]
            builder = ClaimBuilder(
                source_url=page_url,
                page_title=page_title,
                specificity=(
                    SourceSpecificity.PROGRAM_INTAKE
                    if page.page_type is PageType.INTAKE_SPECIFIC_PROGRAM
                    else target.specificity
                ),
                program=program.name,
                intake=intake,
                academic_year=page.academic_year or self.academic_year,
                official_domain=page_url.startswith("fixture://")
                or is_official_domain(page_url, [candidate.domain]),
                extraction_method="fixture" if target.url.startswith("fixture://") else "html_rule",
                accessed_at=res.fetched_at,
                # Read from the page's own words only. The programme, intake
                # and year above are what we asked for; this is what the page
                # answered, and recording the second as if it were the first
                # is the whole of the wrong-scope failure.
                scope=read_scope(text, title=page_title),
                # The verifier's context: without it the verbatim, domain and
                # page-type checks were silently skipped for every requirement
                # claim (found in the owner's adversarial review, 2026-09-25).
                page_text=text,
                page_type=page.page_type.value,
                allowed_domains=verification_domains(page_url, candidate.domain),
            )
            # TY-1: the year the applicant asked for, kept apart from the year
            # the page states first, so a fee table picks the applicant's row.
            builder.requested_academic_year = self.academic_year
            # A shared language page can publish different rules for exchange
            # and full-degree applicants. Keep the original verifier context,
            # but neither table nor prose requirements may use exchange rules.
            sections = full_degree_sections(res.text, text) if not res.is_pdf else None
            requirement_html = sections.html if sections else res.text
            requirement_prose = sections.prose if sections else (text,)

            if not page.accepts("requirements"):
                # A catalogue listing confirms existence by the T29 contract
                # (the university's own list); the verifier's page-type table
                # admits existence only on programme pages, so that one check
                # is lifted here while verbatim and domain still apply.
                builder.page_type = None
                if page.page_type in _LISTING_PAGE_TYPES and self._claim_listed_programme(
                    program, builder, text
                ):
                    # The page that confirms the programme may state its faculty
                    # in a labelled field; one value only (HKU, 2026-09-28).
                    if not res.is_pdf:
                        extract_programme_faculty(text, builder)
                    out.claims.extend(builder.claims)
                    out.page_outcomes.append(
                        PageOutcome(
                            url=target.url,
                            category="fetched-ok",
                            page_type=page.page_type.value,
                            readable_chars=len(text),
                            detail="listing page: only the programme's existence was read",
                        )
                    )
                    continue
                if target.language_follow and not res.is_pdf:
                    # The classifier's page type is a routing hint, not a permission
                    # (both reviews, 2026-09-25): a page reached through an official
                    # "English language requirements" link may state IELTS in a table
                    # whatever type it reads as. Only the structural IELTS reader runs;
                    # verbatim and domain checks still apply to what it reads.
                    tabled = extract_table_requirements(
                        build_document_ir(requirement_html, page_url), builder
                    )
                    if tabled:
                        out.claims.extend(builder.claims)
                        out.page_outcomes.append(
                            PageOutcome(
                                url=target.url,
                                category="fetched-ok",
                                page_type=page.page_type.value,
                                readable_chars=len(text),
                                detail=f"language page: {len(tabled)} claims read from its tables",
                            )
                        )
                        continue
                # An admission-route statement names admission itself ("admitted
                # without a declared major"), so it is read from any official page;
                # verbatim and domain checks still apply (KAIST's department page
                # classifies as unknown and states the route, 2026-09-27 trace).
                builder.page_type = None
                if not res.is_pdf and extract_admission_route(text, builder):
                    out.claims.extend(builder.claims)
                    out.page_outcomes.append(
                        PageOutcome(
                            url=target.url,
                            category="fetched-ok",
                            page_type=page.page_type.value,
                            readable_chars=len(text),
                            detail="only the undergraduate admission route was read",
                        )
                    )
                    continue
                out.errors.append(
                    f"{target.url}: classified as {page.page_type.value}; no requirement can be "
                    "read from this kind of page."
                )
                out.page_outcomes.append(
                    PageOutcome(
                        url=target.url,
                        category="classifier-rejected",
                        page_type=page.page_type.value,
                        readable_chars=len(text),
                        detail=(
                            f"classified as {page.page_type.value}; no requirement can be "
                            "read from this kind of page. "
                            # What the classifier saw, so a wrong call can be
                            # diagnosed from a capture without the page itself.
                            f"title={page.title[:80]!r} signals={'; '.join(page.signals[:3])!r} "
                            f"chars={len(text)} degrees={full_degree_titles(text)[:3]!r}"
                        ),
                    )
                )
                continue

            self._claim_program_exists(page, program, builder, out, text, identity_text=page_title)
            if page.accepts("program_exists") and not res.is_pdf:
                extract_programme_faculty(text, builder)
            if page.accepts("requirements"):
                # Structure first: a table row states the test, the column and the
                # value together (V2-30C). A prose claim of a type the table
                # already answered is dropped, so one page never states two
                # IELTS minimums from two readings of itself.
                tabled = (
                    extract_table_requirements(
                        build_document_ir(requirement_html, page_url), builder
                    )
                    if not res.is_pdf
                    else []
                )
                answered = {c.claim_type for c in tabled}
                for prose in requirement_prose:
                    before = len(builder.claims)
                    extract_requirements(prose, builder)
                    builder.claims[before:] = [
                        c for c in builder.claims[before:] if c.claim_type not in answered
                    ]
                    answered.update(c.claim_type for c in builder.claims[before:])
            self._claim_intake_state(page, text, intake, builder, out)
            for prose in requirement_prose:
                self._claim_english_test_types(prose, builder)
                self._claim_english_waiver(prose, builder)
            self._claim_fees(text, builder)
            if (
                TOPIC_SEARCH
                and page.accepts("costs")
                and (target.topic is not None or target.url == program.url)
            ):
                # A programme page or a fee page states the tuition table
                # (Groningen: non-EU/EEA per academic year on the programme
                # page), which the university-level cost adapter never reads.
                extract_costs(text, builder)

            out.claims.extend(builder.claims)
            out.page_outcomes.append(
                PageOutcome(
                    url=target.url,
                    category="fetched-ok" if builder.claims else "no-pattern-match",
                    page_type=page.page_type.value,
                    readable_chars=len(text),
                    detail=(
                        f"{len(builder.claims)} claims read from this page"
                        if builder.claims
                        else "page was read and accepted, but no requirement pattern "
                        "matched; nothing on it is claimed"
                    ),
                )
            )
            # The English requirement often lives on its own page that the
            # programme or admissions page links to (UBC's English Language
            # Admission Standard, Groningen's faculty language page). When no
            # IELTS minimum has been read yet, follow at most
            # _MAX_LANGUAGE_FOLLOWS such official links, once.
            if (
                followed < _MAX_LANGUAGE_FOLLOWS
                and not res.is_pdf
                and not any(c.claim_type is ClaimType.IELTS_MIN_OVERALL for c in out.claims)
            ):
                for url in _language_links(res.text, page_url, candidate.domain):
                    if url in visited or followed >= _MAX_LANGUAGE_FOLLOWS:
                        continue
                    visited.add(url)
                    followed += 1
                    queue.append(
                        _Target(url, SourceSpecificity.UNIVERSITY_ADMISSIONS, language_follow=True)
                    )
            if ROUTE_LEADS and routed < _MAX_ROUTE_FOLLOWS and not res.is_pdf:
                have = {c.claim_type for c in out.claims}
                want_deadline = ClaimType.ADMISSION_DEADLINE not in have
                want_english = ClaimType.IELTS_MIN_OVERALL not in have
                for url, is_requirements in _route_links(
                    res.text,
                    page_url,
                    candidate.domain,
                    deadline=want_deadline,
                    requirements=want_english,
                ):
                    if url in visited or routed >= _MAX_ROUTE_FOLLOWS:
                        continue
                    visited.add(url)
                    routed += 1
                    queue.append(
                        _Target(
                            url,
                            SourceSpecificity.UNIVERSITY_ADMISSIONS,
                            language_follow=is_requirements,
                            route_follow=True,
                        )
                    )

        if not out.claims and out.pages_checked == 0:
            out.errors.append(
                f"No official page is known for {program.name} at {candidate.name}; "
                "requirements cannot be verified."
            )
        return out

    async def _find_topic_pages(
        self, candidate: Candidate, program: CandidateProgram, out: AdapterResult
    ) -> tuple[tuple[str, str], ...]:
        """One official page per topic, from one public query each, or nothing.

        Only the institution's name enters a query. A result counts only on the
        institution's own domain, outside excluded paths and not naming another
        degree level. A provider failure (a 429 included) ends the search for
        this institution; nothing is retried.
        """
        from app.adapters.discovery.live_discovery import (
            is_excluded_path,
            names_other_degree_level,
            registrable_domain,
            same_institution,
        )
        from app.adapters.search import SearchError, get_search_provider
        from app.adapters.search import intent as intent_module
        from app.adapters.search.base import search_failure_diagnostic
        from app.adapters.search.intent import DEFAULT_QUERY_BUDGET

        key = candidate.domain or candidate.name
        if key in self._topic_pages:
            return self._topic_pages[key]
        self._topic_pages[key] = ()
        if not candidate.domain:
            return ()
        # One institution gets DEFAULT_QUERY_BUDGET queries in all; topic
        # search spends only what discovery left (English first).
        remaining = DEFAULT_QUERY_BUDGET - candidate.search_queries_used
        if intent_module.SHARED_QUERY_BUDGET:
            remaining -= intent_module.SCHOLARSHIP_QUERY_RESERVE
        if remaining <= 0:
            out.errors.append(
                f"Topic search not run: discovery used the {DEFAULT_QUERY_BUDGET}-query budget"
            )
            return ()
        try:
            provider = get_search_provider()
        except SearchError:
            return ()
        found: list[tuple[str, str]] = []
        for topic, template in _TOPIC_QUERIES[:remaining]:
            if intent_module.SHARED_QUERY_BUDGET:
                candidate.search_queries_used += 1
            try:
                response = await provider.search(
                    query=template.format(name=candidate.name),
                    domains=[registrable_domain(candidate.domain) or candidate.domain],
                    max_results=5,
                )
            except SearchError as exc:
                out.errors.append(
                    f"Topic search ({topic}): {search_failure_diagnostic(provider.name, exc)}"
                )
                # TS-2: one failed topic need not cost the others; a 429 still
                # stops, as it does in discovery.
                if TOPIC_SEARCH_CONTINUE and getattr(exc, "http_status", None) != 429:
                    continue
                break
            taken = {u for _, u in found}
            for result in response.results:
                url = result.url
                if (
                    same_institution(url, candidate.domain)
                    and not is_excluded_path(url)
                    and not names_other_degree_level(url, str(program.degree))
                    and url not in taken
                ):
                    found.append((topic, url))
                    break
        self._topic_pages[key] = tuple(found)
        return self._topic_pages[key]

    # --- individual claims ------------------------------------------------

    def _claim_program_exists(
        self, page, program, builder, out, text: str, *, identity_text: str | None = None
    ) -> None:
        """Only a programme page whose own subject matches may confirm existence."""
        if not page.accepts("program_exists"):
            if page.page_type in _LISTING_PAGE_TYPES and self._claim_listed_programme(
                program, builder, text
            ):
                return
            out.errors.append(
                f"{builder.meta['source_url']}: {page.page_type.value} pages cannot confirm that "
                f"{program.name!r} exists."
            )
            return

        matched, why = program_matches(
            requested_name=program.name,
            requested_field=program.field,
            page_subject=page.subject,
            requested_degree=program.degree,
            page_degree=page.degree_level,
        )
        if (
            matched
            and program.field
            and _named_after_its_url(program)
            and not matches_field_text(page.subject or "", [program.field])
        ):
            # The requested name can be discovery's placeholder from a URL slug,
            # so it matches the page it came from. The applicant's field is the
            # check that cannot: HKU's "Computing and Data Science", reached by
            # search, confirmed itself for a computer science applicant (run 51).
            matched, why = (
                False,
                (
                    f"page subject {page.subject!r} does not name the requested field "
                    f"{program.field!r}"
                ),
            )
        if matched and _COURSE_LIST.search(page.subject or ""):
            # A calendar section lists courses, not a programme one can apply
            # to: Toronto's "Computer Science Topic Courses" (run 52).
            matched, why = False, f"page subject {page.subject!r} names courses, not a programme"
        if not matched:
            out.errors.append(
                f"{builder.meta['source_url']}: not confirming {program.name!r} — {why}"
            )
            return

        excerpt = _first_sentence_containing(text, page.subject) or page.subject or ""
        language = page.language_of_instruction
        identity_only = (
            not is_verbatim_excerpt(excerpt, text)
            and bool(identity_text)
            and is_verbatim_excerpt(page.subject or "", identity_text or "")
        )
        if identity_only:
            # This is the actual fetched title (or h1 fallback), outside the
            # selected article. It proves identity only; never join it to body
            # text to manufacture language or requirement evidence.
            excerpt = identity_text or ""
            language = None
        if not identity_only and page.language_evidence is not None:
            proof = _complete_language_excerpt(text, page.language_evidence)
            if proof:
                excerpt = proof
            else:
                language = None
        reading_context = builder.page_text
        try:
            if identity_only:
                builder.page_text = identity_text
            claim = builder.add(
                ClaimType.PROGRAM_EXISTS,
                {
                    "program": page.subject,
                    "degree": page.degree_level,
                    "language": language,
                    "matched_because": why,
                },
                excerpt,
                confidence=0.9,
                section="Programme identity",
                # The programme's own title states its degree; a stray "master's"
                # elsewhere on the page must not re-scope it (run 76, HKU).
                degree=str(page.degree_level) if page.degree_level else None,
            )
        finally:
            builder.page_text = reading_context
        if claim is None and builder.rejected:
            out.errors.append(
                f"{builder.meta['source_url']}: programme identity rejected: "
                f"{builder.rejected[-1][2].value}"
            )

    @staticmethod
    def _claim_listed_programme(program, builder, text: str) -> bool:
        """Confirm existence from a listing page, or do nothing.

        Owner decision 2026-09-23: a school or listing page may confirm
        **existence only**, and only by naming the requested programme by a
        full degree title the ontology's strong aliases equate with it. HKU's
        certified source is exactly such a page. Nothing else is read from it.
        """
        listed = _listed_programme(text, program)
        if listed is None:
            return False
        title, degree = listed
        builder.add(
            ClaimType.PROGRAM_EXISTS,
            {
                "program": title,
                "degree": degree,
                "language": None,
                "matched_because": "named by its full degree title on a listing page",
            },
            _first_sentence_containing(text, title, max_characters=300) or title,
            confidence=0.7,
            section="Programme identity",
            degree=str(degree) if degree else None,
        )
        return True

    def _claim_intake_state(self, page, text: str, intake: str, builder, out) -> None:
        """Open, closed, or no claim at all. Silence is never 'open'."""
        if not page.accepts("intake"):
            return
        flat = for_matching(text)

        closed = _INTAKE_CLOSED_EVIDENCE.search(flat)
        if closed:
            builder.add(
                ClaimType.INTAKE_OPEN,
                False,
                closed.group(0).strip()[:400],
                confidence=0.85,
                section="Key dates",
            )
            return

        for label, pattern in _INTAKE_OPEN_EVIDENCE:
            match = pattern.search(flat)
            if not match:
                continue
            sentence = match.group(0).strip()
            year = _target_year(intake)
            # The evidence has to be about the cycle being researched.
            years = {int(y) for y in re.findall(r"\b(20\d{2})\b", sentence)}
            if year and years and year not in years and (year - 1) not in years:
                out.errors.append(
                    f"{builder.meta['source_url']}: found an application window for "
                    f"{sorted(years)}, not {year}; intake status left unknown."
                )
                continue
            builder.add(
                ClaimType.INTAKE_OPEN,
                True,
                sentence[:400],
                confidence=0.8,
                section="Key dates",
                notes=f"positive evidence: {label}",
            )
            return

        out.errors.append(
            f"{builder.meta['source_url']}: no statement about the application window for "
            f"{intake}; intake status is unknown, not open."
        )

    def _claim_english_waiver(self, text: str, builder) -> None:
        """The published conditions under which no English test is required.

        Recorded as the page's own sentence, not as a boolean: "a waiver
        exists" is useless to an applicant who cannot tell whether it covers
        them, and the conditions are the whole content of the fact. A
        Kazakhstani applicant from an English-medium school lives or dies by
        this sentence, and until now the pipeline read only *fee* waivers and
        dropped it.

        The sentence must be about the language requirement: a fee waiver
        beside it is a different fact, and matching "waiver" alone would claim
        an English exemption from a page offering to waive an application fee.
        """
        flat = for_matching(text)
        for match in _ENGLISH_WAIVER.finditer(flat):
            sentence = match.group(0).strip()
            if not _MENTIONS_ENGLISH.search(sentence):
                continue
            if _NO_ENGLISH_WAIVER.search(sentence):
                # "No waivers are granted" settles it the other way, and
                # claiming a waiver here would be the worse error.
                builder.add(ClaimType.ENGLISH_TEST_WAIVER, "", sentence, confidence=0.7)
                return
            builder.add(ClaimType.ENGLISH_TEST_WAIVER, sentence, sentence, confidence=0.75)
            return

    def _claim_english_test_types(self, text: str, builder) -> None:
        flat = for_matching(text)
        match = re.search(
            r"[^.]*\bIELTS\b[^.]{0,120}?\b(Academic|General Training)\b[^.]{0,120}\.", flat, re.I
        )
        if not match:
            return
        sentence = match.group(0).strip()
        low = sentence.lower()
        accepted: list[str] = []
        if "academic" in low:
            accepted.append("academic")
        if "ukvi" in low:
            accepted.append("ukvi_academic")
        if re.search(r"general training is not accepted|not accept[^.]{0,30}general training", low):
            accepted = [a for a in accepted if a != "general_training"]
        elif "general training" in low and "not" not in low:
            accepted.append("general_training")
        if accepted:
            builder.add(
                ClaimType.IELTS_ACCEPTED_TYPES,
                accepted,
                sentence[:400],
                section="English language requirements",
            )

    def _claim_fees(self, text: str, builder) -> None:
        fee_line = _line_containing(text, "application fee")
        if fee_line:
            fee = _fee(fee_line)
            if fee is not None:
                builder.add(ClaimType.APPLICATION_FEE, fee, fee_line, confidence=0.7)
        waiver_line = _line_containing(text, "fee waiver")
        if not waiver_line:
            return
        if _WAIVER_NEGATION.search(waiver_line):
            # "Fee waivers are not available" — claiming True here was the
            # opposite of the page. Explicit negation is claimed as False.
            builder.add(ClaimType.FEE_WAIVER_AVAILABLE, False, waiver_line, confidence=0.7)
        elif _WAIVER_OFFERED.search(waiver_line):
            builder.add(ClaimType.FEE_WAIVER_AVAILABLE, True, waiver_line, confidence=0.7)
        # Anything else (e.g. "questions about fee waivers ...") neither
        # affirms nor negates: no claim at all.


# --- helpers ---------------------------------------------------------------


#: A subject that names a list of courses rather than a programme.
_COURSE_LIST = re.compile(r"\bcourses?\b(?!\s+of\s+study)", re.IGNORECASE)


def _named_after_its_url(program: CandidateProgram) -> bool:
    """Whether the requested name is only discovery's placeholder from the URL.

    Such a name matches the page it came from by construction, so it cannot
    say the page is the applicant's programme. A name from a catalogue or a
    registry is the university's own and is trusted as before.
    """
    if not program.url:
        return False
    slug = program.url.rstrip("/").rsplit("/", 1)[-1]
    slug_words = [w for w in re.split(r"[-_]+", slug.lower().replace(".html", "")) if w]
    name_words = [w for w in re.split(r"[^a-z0-9]+", program.name.lower()) if w]
    return bool(slug_words) and slug_words == name_words


def _target_year(intake: str) -> int | None:
    match = re.search(r"\b(20\d{2})\b", intake or "")
    return int(match.group(1)) if match else None


#: Pages that list programmes rather than describe one. Only these may name a
#: programme into existence, and only by its full degree title.
_LISTING_PAGE_TYPES = frozenset({PageType.PROGRAM_CATALOG, PageType.UNKNOWN})


def _listed_programme(text: str, program) -> tuple[str, str | None] | None:
    """The first full degree title on a listing page that names the requested
    programme, and its degree — or ``None``.

    Strict on both counts: the ontology must say YES (a strong alias, never a
    related field), and a stated degree level must be the requested one.
    """
    for title in full_degree_titles(text):
        # Against the requested field as well as the candidate's name: the
        # name can be what a faculty page calls itself. Run 35: HKU's page,
        # named "Computing and Data Science", listed "Bachelor of Engineering
        # in Computer Science" for a request for computer science.
        wanted = [n for n in (program.name, getattr(program, "field", "")) if n]
        if not any(titles_name_same_programme(title, n) is Verdict.YES for n in wanted):
            continue
        degree = degree_level_of(title)
        if degree_matches(program.degree, degree) is False:
            continue
        return title, degree
    return None


def _complete_language_excerpt(text: str, evidence: str) -> str:
    """Locate the whole main-content proof in the reader's original text."""
    if not evidence:
        return ""
    pattern = re.compile(r"\s+".join(re.escape(word) for word in evidence.split()), re.I)
    match = pattern.search(text)
    if match is None or match.end() - match.start() > MAX_EXCERPT_CHARS:
        return ""
    return match.group()


def _first_sentence_containing(
    text: str, needle: str | None, *, max_characters: int | None = None
) -> str:
    """A real quote from the page, or empty. Never a sentence we wrote."""
    if not needle:
        return ""
    flat = for_matching(text)
    index = flat.lower().find(needle.lower())
    if index < 0:
        return ""
    if max_characters is None:
        return excerpt_around(flat, index, index + len(needle))
    # Keep the full programme title within the owner's 300-character support
    # window; unrelated surrounding prose otherwise obscures listing evidence.
    radius = max(0, (max_characters - len(needle)) // 2)
    return excerpt_around(flat, index, index + len(needle), radius=radius)


def _fee(line: str) -> dict[str, object] | None:
    """The application fee, or None.

    Returning the raw sentence when no amount parses would put a fragment like
    "Among this year's applicants, thre" into the results as a fee. A fee we
    cannot read is simply not a claim.
    """
    from app.adapters.extraction import parse_money

    parsed = parse_money(line)
    return {"amount": parsed[0], "currency": parsed[1]} if parsed else None


def _line_containing(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line.lower():
            return line.strip()[:300]
    return ""

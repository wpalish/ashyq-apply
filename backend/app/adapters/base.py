"""Adapter contracts.

Selectors, URL patterns and site quirks live inside adapters. The pipeline
above them only ever sees ``Candidate`` objects and ``Claim`` lists, so adding
a source never means touching business logic or the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.domain.enums import DegreeLevel
from app.schemas.claim import Claim
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import CostBreakdown, DocumentChecklist, RankingEntry, Scholarship


@dataclass
class CandidateProgram:
    name: str
    field: str
    degree: DegreeLevel
    url: str | None = None


@dataclass(frozen=True)
class RequirementsLead:
    """SP-2: a page discovery read and refused as a process sub-page of a programme.

    Not the programme page, but its admissions process page, so a lead for the
    requirements and deadline questions. ``names_programme``: the page's ``h1``
    names the requested level and subject, so its claims may take the
    programme's scope; otherwise the page keeps its own read scope.
    """

    url: str
    names_programme: bool = False


@dataclass
class Candidate:
    """A university found during discovery, before anything is verified."""

    name: str
    country: str
    city: str
    domain: str = ""
    programs: list[CandidateProgram] = field(default_factory=list)
    rankings: list[RankingEntry] = field(default_factory=list)
    admissions_url: str | None = None
    costs_url: str | None = None
    scholarships_url: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    discovery_source: str = ""
    notes: str = ""
    #: Provider queries discovery already spent on this institution.
    search_queries_used: int = 0
    #: DI-1 (``ADMISSIONS_HOST_FROM_HOMEPAGE``): registrable domains, beyond
    #: ``domain``, that this institution's own homepage names as its admissions
    #: site. At most one; empty unless the rule is on and found one. Every
    #: official-domain reader takes ``official_domains`` rather than ``domain``.
    extra_domains: list[str] = field(default_factory=list)
    #: QR-1 (``QUESTION_ROUTED_EVIDENCE``): official pages the requirements
    #: adapter reached for the fees question (a "Fees" link on the programme or
    #: admissions page, or the fees topic query), at most two. The cost adapter
    #: reads them after ``costs_url`` when that page states no tuition. Empty
    #: unless the rule is on.
    question_fee_urls: list[str] = field(default_factory=list)
    #: SP-2 (``live_discovery.SUBPAGE_REQUIREMENTS_LEAD``): a process sub-page
    #: SP-1 refused, at most one, for the requirements adapter to read after
    #: QR-1's question links. Empty unless the rule is on and found one.
    requirements_leads: list[RequirementsLead] = field(default_factory=list)

    @property
    def official_domains(self) -> tuple[str, ...]:
        """The institution's own domain first, then any DI-1 admissions domain.

        With no extra domain this is exactly ``(domain,)`` — the one-element
        list every reader passed before — so a run without DI-1 is unchanged.
        """
        return (self.domain, *self.extra_domains)

    @property
    def verifiable(self) -> bool:
        """Whether any official page is known for this candidate."""
        return bool(self.admissions_url or self.costs_url or any(p.url for p in self.programs))


@dataclass(frozen=True)
class PageOutcome:
    """How one page's reading ended, in the run's own vocabulary.

    The categories are the frozen T18 acceptance vocabulary: a report built
    from a run must be able to separate fetch-failed / unreadable /
    classifier-rejected / no-pattern-match instead of reporting "35 pages,
    0 claims, 0 failed" — a fetch-level fact that cannot explain itself.
    ``page_type`` is the classifier's answer for pages that were read.
    """

    url: str
    category: str
    page_type: str = ""
    detail: str = ""
    readable_chars: int = 0
    #: ES-2 (measurement only, funding stage): the page's ``<html lang>``
    #: primary subtag (``""`` when it declares none) and the classifier's
    #: ``funding_category`` (``"not_funding"`` outside the funding branch).
    #: ``None`` where not recorded. The runner's outcome line never prints
    #: them; only the evaluation capture reads them.
    html_lang: str | None = None
    classifier_signal: str | None = None


@dataclass
class AdapterResult:
    """What an adapter produced plus what went wrong doing it."""

    claims: list[Claim] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pages_checked: int = 0
    pages_failed: int = 0
    retry_urls: list[str] = field(default_factory=list)
    #: (url, page_type) for every page read, so a run can show *why* a page
    #: produced nothing rather than only that it did.
    page_types: list[tuple[str, str]] = field(default_factory=list)
    #: One outcome per page touched, for the run's persisted diagnostics.
    page_outcomes: list[PageOutcome] = field(default_factory=list)


@runtime_checkable
class DiscoveryAdapter(Protocol):
    name: str

    async def discover(self, profile: ApplicantProfileIn, limit: int) -> list[Candidate]: ...


@runtime_checkable
class RequirementsAdapter(Protocol):
    name: str

    async def verify(
        self, candidate: Candidate, program: CandidateProgram, intake: str
    ) -> AdapterResult: ...


@runtime_checkable
class ScholarshipAdapter(Protocol):
    name: str

    async def find(
        self, candidate: Candidate, program: CandidateProgram, profile: ApplicantProfileIn
    ) -> tuple[list[Scholarship], AdapterResult]: ...


@runtime_checkable
class CostAdapter(Protocol):
    name: str

    async def fetch(self, candidate: Candidate) -> tuple[CostBreakdown, AdapterResult]: ...


@runtime_checkable
class DocumentsAdapter(Protocol):
    name: str

    async def collect(
        self, candidate: Candidate, program: CandidateProgram, scholarships: list[Scholarship]
    ) -> tuple[DocumentChecklist, AdapterResult]: ...


@runtime_checkable
class GovernmentAdapter(Protocol):
    name: str

    async def post_study_work(self, country: str) -> AdapterResult: ...

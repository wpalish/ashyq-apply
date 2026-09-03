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

    @property
    def verifiable(self) -> bool:
        """Whether any official page is known for this candidate."""
        return bool(self.admissions_url or self.costs_url or any(p.url for p in self.programs))


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

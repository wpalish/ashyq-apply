"""Phase 3 §9: "store source and scope for each required document."

A checklist read off a general admissions page and one read off the
programme's own page used to be indistinguishable on the record - the adapter
computed the page's scope for its claims and dropped it for the documents.
"""

from __future__ import annotations

import pytest

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.documents.web_documents import WebDocumentsAdapter
from app.adapters.fetching import Fetcher
from app.domain.enums import DegreeLevel, DocumentOwner, DocumentPurpose
from app.schemas.result import DocumentItem


def _candidate() -> Candidate:
    return Candidate(
        name="University of Toronto",
        country="Canada",
        city="Toronto",
        domain="utoronto.ca",
    )


def _program() -> CandidateProgram:
    return CandidateProgram(
        name="BS CS",
        field="cs",
        degree=DegreeLevel.BACHELOR,
        url="fixture://u-toronto/program-0.html",
    )


class TestADocumentCarriesThePageScope:
    @pytest.mark.asyncio
    async def test_documents_read_from_a_page_carry_what_it_said_it_covered(
        self, settings, corpus_dir
    ):
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as fetcher:
            checklist, _ = await WebDocumentsAdapter(fetcher, "2026/27").collect(
                _candidate(), _program(), []
            )

        documents = checklist.admission_documents + checklist.applicant_actions
        assert documents, "the fixture is expected to yield documents"
        assert all(d.scope is not None for d in documents)
        # The page states the intake it is about; every row read from it says so.
        assert {d.scope.intake for d in documents if d.scope} == {"Fall 2027"}
        assert {d.scope.academic_year for d in documents if d.scope} == {"2026/27"}

    @pytest.mark.asyncio
    async def test_a_page_that_names_no_population_invents_none(self, settings, corpus_dir):
        async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as fetcher:
            checklist, _ = await WebDocumentsAdapter(fetcher, "2026/27").collect(
                _candidate(), _program(), []
            )

        for document in checklist.admission_documents:
            assert document.scope is not None
            # The reader refuses these dimensions in writing, by design: a
            # document page naming a programme is not evidence that the
            # requirement is programme-specific.
            assert document.scope.programme is None
            assert document.scope.university is None
            # And it did not invent a population the page never named.
            assert document.scope.population is None


class TestTheFieldIsAbsentUntilSomebodyRecordsOne:
    def test_an_unrecorded_scope_is_left_out_of_the_payload(self):
        """``None`` means nobody looked, and that is not a finding."""
        item = DocumentItem(
            name="CV", purpose=DocumentPurpose.ADMISSION, owner=DocumentOwner.APPLICANT
        )
        assert "scope" not in item.model_dump()
        assert "scope" not in item.model_dump_json()

    def test_a_recorded_scope_survives_a_round_trip(self):
        from app.domain.claim_scope import ClaimScope

        item = DocumentItem(
            name="CV",
            purpose=DocumentPurpose.ADMISSION,
            owner=DocumentOwner.APPLICANT,
            scope=ClaimScope(population="international students"),
        )
        back = DocumentItem.model_validate_json(item.model_dump_json())
        assert back.scope is not None
        assert back.scope.population == "international students"


def test_the_adapter_result_type_is_unchanged():
    """A guard: this step records, it does not act."""
    assert "scope" not in AdapterResult.__dataclass_fields__

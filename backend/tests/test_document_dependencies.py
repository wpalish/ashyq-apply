"""Phase 3 §9 — a document that waits for another document.

`DocumentItem.depends_on` was declared on the schema and populated by nothing.
The guide's own example is the one that can now be recorded honestly: an
admission offer letter before a scholarship submission, when the award page
says an offer is required.
"""

from __future__ import annotations

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.documents.web_documents import _OFFER_LETTER, WebDocumentsAdapter
from app.adapters.fetching import Fetcher
from app.schemas.result import Scholarship


def _award(**over) -> Scholarship:
    return Scholarship.model_validate(
        {
            "id": "sch-1",
            "name": "Example Award",
            "source_urls": ["fixture://nus/scholarship-0.html"],
            **over,
        }
    )


async def _collect(settings, corpus_dir, award: Scholarship):
    candidate = Candidate(
        name="University of Toronto",
        country="Canada",
        city="Toronto",
        domain="utoronto.ca",
    )
    program = CandidateProgram(
        name="BS CS", field="cs", degree="bachelor", url="fixture://u-toronto/program-0.html"
    )
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=corpus_dir) as fetcher:
        checklist, _ = await WebDocumentsAdapter(fetcher, "2026/27").collect(
            candidate, program, [award]
        )
    return checklist


@pytest.mark.asyncio
async def test_a_scholarship_document_waits_for_the_offer_when_the_award_says_so(
    settings, corpus_dir
):
    checklist = await _collect(settings, corpus_dir, _award(offer_required="yes"))
    assert checklist.scholarship_documents, "the fixture award page yields documents"
    assert all(d.depends_on == [_OFFER_LETTER] for d in checklist.scholarship_documents)


@pytest.mark.asyncio
async def test_nothing_waits_when_the_award_page_never_mentioned_an_offer(settings, corpus_dir):
    """Unknown is the common answer, and a guess about someone's paperwork
    order is worse than an empty field."""
    checklist = await _collect(settings, corpus_dir, _award())
    assert checklist.scholarship_documents
    assert all(d.depends_on == [] for d in checklist.scholarship_documents)


@pytest.mark.asyncio
async def test_an_award_that_needs_no_offer_creates_no_dependency(settings, corpus_dir):
    checklist = await _collect(settings, corpus_dir, _award(offer_required="no"))
    assert all(d.depends_on == [] for d in checklist.scholarship_documents)

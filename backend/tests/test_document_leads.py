"""DOC-3: the documents stage finds the institution's application-documents page."""

from __future__ import annotations

from typing import Any

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.documents import web_documents
from app.adapters.documents.web_documents import WebDocumentsAdapter
from app.adapters.fetching import FetchResult
from app.domain.enums import DegreeLevel, FetchOutcome

ROOT = "https://www.rug.nl"
PROGRAMME = f"{ROOT}/bachelors/computing-science"
ROUTE = f"{ROOT}/admission/bachelor-non-dutch-qualification"
DOCUMENTS = f"{ROOT}/admission/bachelor-application-documents"
PAGES = {
    PROGRAMME: (
        "<h1>Computing Science</h1><p>A three-year programme.</p>"
        f'<a href="{ROUTE}">International diploma</a>'
        '<a href="https://elsewhere.example/application-documents">Application documents</a>'
    ),
    ROUTE: (
        "<h1>Bachelor with a non-Dutch diploma</h1>"
        f'<a href="{DOCUMENTS}">Bachelor\'s application documents</a>'
    ),
    DOCUMENTS: (
        "<h1>Bachelor's application documents</h1><h2>Required documents</h2><ul>"
        "<li>You must upload a copy of your valid passport.</li>"
        "<li>You must upload a CV.</li></ul>"
    ),
}


class _Fetcher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        self.calls.append(url)
        if url not in PAGES:
            return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, status_code=404)
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            text=f"<html><body>{PAGES[url]}</body></html>",
            content_type="text/html",
            final_url=url,
        )


async def _collect(fetcher: _Fetcher):
    candidate = Candidate(name="University of Groningen", country="NL", city="", domain="rug.nl")
    program = CandidateProgram(
        name="Computing Science", field="cs", degree=DegreeLevel.BACHELOR, url=PROGRAMME
    )
    checklist, _ = await WebDocumentsAdapter(fetcher, "2027/28").collect(  # type: ignore[arg-type]
        candidate, program, []
    )
    return checklist


@pytest.mark.asyncio
async def test_off_by_default_only_the_programme_page_is_read() -> None:
    fetcher = _Fetcher()
    checklist = await _collect(fetcher)
    assert web_documents.DOCUMENT_LEADS is False
    assert fetcher.calls == [PROGRAMME]
    assert checklist.admission_documents == []


@pytest.mark.asyncio
async def test_the_documents_page_two_links_away_is_read(monkeypatch) -> None:
    monkeypatch.setattr(web_documents, "DOCUMENT_LEADS", True)
    fetcher = _Fetcher()
    checklist = await _collect(fetcher)
    assert DOCUMENTS in fetcher.calls
    # The off-site "Application documents" link is never followed.
    assert not any("elsewhere.example" in url for url in fetcher.calls)
    assert {d.source_url for d in checklist.admission_documents} == {DOCUMENTS}
    assert len(checklist.admission_documents) >= 1

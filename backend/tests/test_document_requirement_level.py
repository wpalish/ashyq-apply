"""Whether a document is required, conditional, or simply not stated.

Every extracted document was marked `required=True`, because that is the
field's default and the extractor never set it. A page listing "a portfolio, if
applicable" or "one of: IELTS, TOEFL or Duolingo" therefore told the applicant
they must produce all of them.

That is the same rule the rest of the product follows: an unknown is not a yes.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.documents.web_documents import requirement_level_of
from app.domain.enums import DegreeLevel


class TestWordingDecidesTheLevel:
    @pytest.mark.parametrize("line", [
        "Required documents: a certified copy of your diploma.",
        "You must submit a motivation letter.",
        "All applicants are required to provide a transcript.",
        "A passport copy is mandatory.",
    ])
    def test_required_wording_is_required(self, line):
        assert requirement_level_of(line) == "required"

    @pytest.mark.parametrize("line", [
        "A portfolio, if applicable.",
        "Reference letters may be requested.",
        "A CV is optional for this programme.",
        "Where relevant, submit proof of name change.",
        "Applicants from outside the EU should also provide a residence permit.",
        "One of: IELTS, TOEFL or Duolingo.",
        "A recommendation letter is recommended but not required.",
    ])
    def test_conditional_or_optional_wording_is_conditional(self, line):
        assert requirement_level_of(line) == "conditional"

    @pytest.mark.parametrize("line", [
        "Transcript",
        "Motivation letter - upload as PDF, max 2 pages.",
        "Diploma",
    ])
    def test_wording_that_says_nothing_stays_unknown(self, line):
        """A bare list item does not say whether it is compulsory."""
        assert requirement_level_of(line) == "unknown"


class TestTheExtractorUsesIt:
    @staticmethod
    async def extract(html: str):
        import tempfile
        from pathlib import Path

        from app.adapters.base import Candidate, CandidateProgram
        from app.adapters.documents.web_documents import WebDocumentsAdapter
        from app.adapters.fetching import Fetcher, FetchResult
        from app.domain.enums import FetchOutcome

        async with Fetcher(Path(tempfile.mkdtemp()), offline=True) as fetcher:
            async def fake_get(url: str, *, use_cache: bool = True) -> FetchResult:
                raw = html.encode()
                return FetchResult(
                    url=url, outcome=FetchOutcome.OK, status_code=200, content=raw,
                    text=html, content_type="text/html",
                    fetched_at=datetime.now(UTC), final_url=url,
                )

            fetcher.get = fake_get  # type: ignore[method-assign]
            candidate = Candidate(
                name="U", country="X", city="Y",
                admissions_url="https://uni.edu/documents", domain="uni.edu",
            )
            program = CandidateProgram(
                name="BSc Computer Science", field="computer science", degree=DegreeLevel.BACHELOR,
                url="https://uni.edu/programmes/cs",
            )
            return await WebDocumentsAdapter(fetcher, "2026/27").collect(candidate, program, [])

    @pytest.mark.asyncio
    async def test_a_conditional_document_is_not_asserted_as_required(self):
        html = (
            "<html><head><title>Required documents</title></head><body><main>"
            "<h1>Required documents</h1>"
            "<p>You must submit a transcript of records.</p>"
            "<p>A portfolio, if applicable.</p>"
            "</main></body></html>"
        )
        checklist, _ = await self.extract(html)
        every = [*checklist.admission_documents, *checklist.scholarship_documents]
        by_name = {i.name.lower(): i for i in every}
        portfolio = next((v for k, v in by_name.items() if "portfolio" in k), None)
        if portfolio is not None:
            assert portfolio.requirement_level != "required", (
                "a document the page marked 'if applicable' was asserted as required"
            )

    @pytest.mark.asyncio
    async def test_nothing_defaults_to_required(self):
        """The defect in one line: the field's default must not be an assertion."""
        from app.domain.enums import DocumentOwner, DocumentPurpose
        from app.schemas.result import DocumentItem

        item = DocumentItem(name="X", purpose=DocumentPurpose.ADMISSION,
                            owner=DocumentOwner.APPLICANT)
        assert item.requirement_level == "unknown"

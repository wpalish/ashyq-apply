"""PD-1 (PDF map ticket 04): the stages read a PDF as pages, by its own title.

Synthetic PDFs built with pypdf's writer (the ticket-03 helper); a fake
fetcher hands them to the real stage adapters. No network.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("pypdf", reason="pypdf cannot be imported in this environment")

from app.adapters import pdf_evidence
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.fetching import FetchResult
from app.adapters.pdf_document import read_pdf
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.domain.enums import ClaimType, DegreeLevel, FetchOutcome
from tests.test_pdf_document import build_pdf

DOMAIN = "example.edu"
FEE_URL = "https://www.example.edu/files/fees-2026.pdf"
AWARD_URL = "https://www.example.edu/scholarships/global-excellence.pdf"
REQ_URL = "https://www.example.edu/admissions/entry-requirements.pdf"


class FakeFetcher:
    def __init__(self, pages: dict[str, bytes]) -> None:
        self.pages = pages
        self.requested: list[str] = []

    async def get(self, url: str, **_: object) -> FetchResult:
        self.requested.append(url)
        if url not in self.pages:
            return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, error="404")
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            content=self.pages[url],
            text=self.pages[url].decode("latin-1"),
            content_type="application/pdf",
            final_url=url,
            fetched_at=datetime(2026, 10, 18, tzinfo=UTC),
        )


@pytest.fixture
def readers_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_evidence, "PDF_EVIDENCE_READERS", True)


def _candidate(**kwargs: object) -> Candidate:
    return Candidate(
        name="Example University",
        country="Netherlands",
        city="Exampletown",
        domain=DOMAIN,
        **kwargs,  # type: ignore[arg-type]
    )


PROGRAM = CandidateProgram(
    name="MSc Computer Science",
    field="Computer Science",
    degree=DegreeLevel.MASTER,
    url="https://www.example.edu/programmes/msc-computer-science",
)

FEE_PAGES = [
    ["Tuition and fees 2026/27", "This schedule lists the fees set by the Board."],
    [
        "Fees for international students",
        "International students pay the institutional fee.",
        "Tuition fee: EUR 18,000 per year",
    ],
]


async def _costs(pages: dict[str, bytes]) -> tuple[object, object]:
    fetcher = FakeFetcher(pages)
    adapter = WebCostAdapter(fetcher, "2026/27")  # type: ignore[arg-type]
    return await adapter.fetch(_candidate(costs_url=FEE_URL, programs=[PROGRAM]))


@pytest.mark.asyncio
async def test_a_fee_pdf_claims_tuition_from_its_page_with_that_pages_population(
    readers_on: None,
) -> None:
    _, out = await _costs({FEE_URL: build_pdf(FEE_PAGES)})
    tuition = [c for c in out.claims if c.claim_type is ClaimType.TUITION]  # type: ignore[attr-defined]
    assert tuition, out.page_outcomes  # type: ignore[attr-defined]
    claim = tuition[0]
    assert claim.relevant_section == "p. 2"
    assert claim.normalized_value["amount"] == 18000
    assert claim.scope is not None and claim.scope.population == "international"
    assert claim.page_title == "Tuition and fees 2026/27"
    assert claim.extraction_method == "pdf_rule"


@pytest.mark.asyncio
async def test_two_programmes_rows_naming_neither_confirmed_programme_are_not_claimed(
    readers_on: None,
) -> None:
    pages = [
        ["Tuition and fees 2026/27", "This schedule lists the fees set by the Board."],
        [
            "Tuition fee MSc Chemistry: EUR 20,000 per year",
            "Tuition fee MSc Physics: EUR 22,000 per year",
        ],
    ]
    _, out = await _costs({FEE_URL: build_pdf(pages)})
    assert not [c for c in out.claims if c.claim_type is ClaimType.TUITION]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_an_image_only_pdf_is_a_fetch_failure_without_a_claim(readers_on: None) -> None:
    _, out = await _costs({FEE_URL: build_pdf([None, None])})
    assert not out.claims  # type: ignore[attr-defined]
    outcome = out.page_outcomes[-1]  # type: ignore[attr-defined]
    assert (outcome.category, outcome.detail) == ("fetch-failed", "PDF without a text layer")


@pytest.mark.asyncio
async def test_flag_off_keeps_the_old_pdf_path() -> None:
    assert pdf_evidence.PDF_EVIDENCE_READERS is False
    _, out = await _costs({FEE_URL: build_pdf(FEE_PAGES)})
    for claim in out.claims:  # type: ignore[attr-defined]
        assert claim.relevant_section == ""
        assert claim.page_title == "Fee schedule (PDF)"


AWARD_PAGES = [
    [
        "Global Excellence Scholarship",
        "",
        "The Global Excellence Scholarship is open to international students "
        "admitted to a master's programme.",
        "The award covers EUR 10,000 of the tuition fee.",
    ]
]


@pytest.mark.asyncio
async def test_an_award_pdf_is_read_as_its_award_with_a_page_number(readers_on: None) -> None:
    fetcher = FakeFetcher({AWARD_URL: build_pdf(AWARD_PAGES)})
    adapter = WebScholarshipAdapter(fetcher, "2026/27")  # type: ignore[arg-type]
    _, out = await adapter.find(
        _candidate(scholarships_url=AWARD_URL, programs=[PROGRAM]),
        PROGRAM,
        None,
        allow_search=False,
    )
    types = {c.claim_type for c in out.claims}
    assert ClaimType.SCHOLARSHIP_EXISTS in types, out.page_outcomes
    assert ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE in types, out.claims
    assert all(c.relevant_section == "p. 1" for c in out.claims if c.source_url == AWARD_URL)


REQ_PAGES = [
    ["Entry requirements", "These rules apply to every master's programme."],
    [
        "English language requirements",
        "Applicants must have an IELTS overall band score of 6.5 or higher.",
    ],
]


@pytest.mark.asyncio
async def test_a_requirements_pdf_classifies_by_its_title_and_claims_with_a_page(
    readers_on: None,
) -> None:
    program = CandidateProgram(
        name=PROGRAM.name, field=PROGRAM.field, degree=PROGRAM.degree, url=REQ_URL
    )
    fetcher = FakeFetcher({REQ_URL: build_pdf(REQ_PAGES)})
    adapter = WebRequirementsAdapter(fetcher, "2026/27")  # type: ignore[arg-type]
    out = await adapter.verify(_candidate(programs=[program]), program, "fall 2026")
    types = dict(out.page_types)
    assert types[REQ_URL] != "unknown"
    ielts = [c for c in out.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
    assert ielts, out.page_outcomes
    assert ielts[0].relevant_section == "p. 2", ielts[0].original_text_excerpt
    assert ielts[0].page_title == "Entry requirements"


def test_classification_uses_the_pdf_title_and_headings() -> None:
    doc = read_pdf(build_pdf(FEE_PAGES), FEE_URL)
    pdf = pdf_evidence.PdfRead(
        doc=doc, text=pdf_evidence.paged_text(doc), html=pdf_evidence.pdf_html(doc)
    )
    assert "<title>Tuition and fees 2026/27</title>" in pdf.html
    assert "p. 1" not in pdf.html  # page labels are provenance, not headings
    assert pdf_evidence.classify_pdf(pdf, FEE_URL).page_type.value == "costs"


def test_the_module_imports_no_network_layer() -> None:
    source = Path(pdf_evidence.__file__).read_text()
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not {m for m in imported if "fetching" in m or m in {"httpx", "socket", "requests"}}


@pytest.mark.asyncio
async def test_the_row_naming_the_confirmed_programme_is_the_one_claimed(readers_on: None) -> None:
    pages = [
        [
            "Tuition fee MSc Chemistry: EUR 20,000 per year",
            "Tuition fee MSc Computer Science: EUR 19,000 per year",
        ],
    ]
    _, out = await _costs({FEE_URL: build_pdf(pages)})
    amounts = {
        c.normalized_value["amount"]
        for c in out.claims  # type: ignore[attr-defined]
        if c.claim_type is ClaimType.TUITION
    }
    assert amounts <= {19000}

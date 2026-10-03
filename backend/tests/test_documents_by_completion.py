"""A document's form by completion state, read from one line (Groningen, 2026-09-28)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.document_ir import build_document_ir
from app.adapters.documents.web_documents import _completion_forms, read_documents
from app.adapters.extraction import ClaimBuilder, html_to_text
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimType, DocumentPurpose

GRONINGEN = (
    "Transcript Scan(s) of your academic record (i.e. final grade list/report card) and/or "
    "if not yet completed: school-issued list of your courses still to be completed "
    "(if applicable, including level/credits/units)"
)


def read(text: str):
    builder = ClaimBuilder(
        source_url="https://www.rug.nl/x",
        page_title="x",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 9, 28, tzinfo=UTC),
    )
    _completion_forms(text, builder)
    return [c.normalized_value for c in builder.claims]


def test_both_forms_of_the_transcript_are_read():
    assert read(GRONINGEN) == [
        {"document": "Full academic transcript", "status": "completed", "form": "academic_record"},
        {
            "document": "Full academic transcript",
            "status": "not_completed",
            "form": "school_course_list",
        },
    ]


def test_a_diploma_or_an_enrolment_statement():
    values = read(
        "Diploma Certified copy of your diploma or if not yet completed: "
        "a statement of enrolment from your school"
    )
    assert [v["form"] for v in values] == ["diploma", "school_enrolment_statement"]


def test_an_unrecognised_form_reads_nothing():
    assert read("Transcript Your grades, or if not yet completed: whatever you have") == []


def test_no_completion_clause_reads_nothing():
    assert read("Transcript Scan(s) of your academic record") == []


BODY = GRONINGEN.removeprefix("Transcript ")


def _read_html(html: str):
    scope = ClaimScope(population="transfer")
    text = html_to_text(html)
    builder = ClaimBuilder(
        source_url="https://u.edu/documents",
        official_domain=True,
        page_text=text,
        scope=scope,
    )
    read_documents(
        text,
        "https://u.edu/documents",
        DocumentPurpose.ADMISSION,
        scope,
        builder,
        document=build_document_ir(html, "https://u.edu/documents"),
    )
    assert builder.meta["scope"] is scope
    return [c for c in builder.claims if c.claim_type is ClaimType.DOCUMENT_BY_COMPLETION]


@pytest.mark.parametrize(
    "html",
    [
        f"<table><tr><th>Transcript</th><td>{BODY}</td></tr></table>",
        f"<h3>Transcript</h3><p>{BODY}</p>",
        f"<dl><dt>Transcript</dt><dd>{BODY}</dd></dl>",
        f"<p>{GRONINGEN}</p>",
    ],
    ids=["row-header", "heading", "definition-list", "one-paragraph"],
)
def test_explicit_document_structure_preserves_both_forms_without_duplicates(html):
    claims = _read_html(html)
    assert [c.normalized_value for c in claims] == read(GRONINGEN)
    assert all(c.original_text_excerpt in {BODY, GRONINGEN} for c in claims)
    assert all(c.scope.population is None for c in claims)


@pytest.mark.parametrize(
    "html",
    [
        "<table><tr><th>Transcript</th><td>Scan of your academic record</td>"
        "<td>if not yet completed: school-issued list of your courses</td></tr></table>",
        "<h3>Transcript</h3><p>Scan of your academic record</p>"
        "<p>if not yet completed: school-issued list of your courses</p>",
        f"<table><tr><th>Transcript</th><th>Diploma</th><td>{BODY}</td></tr></table>",
        f"<table><caption>Transcript</caption><tr><td>{BODY}</td></tr></table>",
        f"<h3>Diploma</h3><p>{GRONINGEN}</p>",
    ],
    ids=["split-cells", "split-paragraphs", "ambiguous-label", "caption-only", "wrong-label"],
)
def test_structural_reader_abstains_when_the_document_or_both_forms_are_unproved(html):
    assert _read_html(html) == []


def test_each_document_block_keeps_its_own_applicant_population():
    html = (
        f"<h2>International students</h2><h3>Transcript</h3><p>{BODY}</p>"
        "<h2>Domestic students</h2><h3>Diploma</h3>"
        "<p>Certified copy of your diploma or if not yet completed: "
        "a statement of enrolment from your school</p>"
    )
    claims = _read_html(html)
    assert [(c.normalized_value["form"], c.scope.population) for c in claims] == [
        ("academic_record", "international"),
        ("school_course_list", "international"),
        ("diploma", "domestic"),
        ("school_enrolment_statement", "domestic"),
    ]


def test_a_completion_form_is_not_claimed_after_its_evidence_would_be_clipped():
    from app.schemas.claim import MAX_EXCERPT_CHARS

    html = (
        "<h3>Transcript</h3><p>Scan of your academic record "
        + "context " * MAX_EXCERPT_CHARS
        + "if not yet completed: school-issued list of your courses</p>"
    )
    assert _read_html(html) == []


def test_actual_diploma_cell_keeps_secondary_and_higher_education_separate():
    html = (Path(__file__).parent / "fixtures/live_shapes/groningen_diploma_row.html").read_text()
    claims = _read_html(html)
    assert [(c.normalized_value["status"], c.normalized_value["form"]) for c in claims] == [
        ("completed", "diploma"),
        ("not_completed", "school_enrolment_statement"),
    ]
    for claim in claims:
        assert "from your school" in claim.original_text_excerpt
        assert "Higher education" not in claim.original_text_excerpt
        assert "educational institution" not in claim.original_text_excerpt
        assert "expected date of graduation" in claim.original_text_excerpt


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("<strong>Diploma</strong>", "<strong>Transcript</strong>"),
        ("Secondary education", "Secondary education (if applicable)"),
        ("or<br/>if not yet completed:", "or<br/>if requested:"),
        ("Statement of enrolment", "Alternative documents"),
        ("Statement of enrolment", "Statement of enrolment if requested"),
        ("Statement of enrolment", "Statement of enrolment (not required)"),
        ("Higher education (if applicable)", "Unrelated information"),
        ("expected date of graduation", "expected date of graduation " + "context " * 500),
    ],
    ids=[
        "wrong-document",
        "conditional-group",
        "different-condition",
        "unknown-form",
        "extra-condition",
        "not-required",
        "no-group-boundary",
        "oversized-group",
    ],
)
def test_compound_cell_requires_a_complete_unambiguous_secondary_group(old, new):
    html = (Path(__file__).parent / "fixtures/live_shapes/groningen_diploma_row.html").read_text()
    assert old in html
    assert _read_html(html.replace(old, new)) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("structured", [True, False], ids=["html-table", "plain-text"])
async def test_document_adapter_and_direct_source_oracle_share_reading(tmp_path, structured):
    from app.adapters.base import Candidate, CandidateProgram
    from app.adapters.documents.web_documents import WebDocumentsAdapter
    from app.adapters.fetching import Fetcher
    from app.domain.enums import DegreeLevel
    from evaluation.research.oracle import _document_claims

    html = (
        f"<table><tr><th>Transcript</th><td>{BODY}</td></tr></table>" if structured else GRONINGEN
    )
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "documents.html").write_text(html)
    url = "fixture://documents.html"
    program = CandidateProgram("BSc Computing", "computing", DegreeLevel.BACHELOR, url)
    candidate = Candidate("University", "Country", "City", domain="u.edu")
    async with Fetcher(tmp_path / "cache", offline=True, corpus_dir=corpus) as fetcher:
        _, report = await WebDocumentsAdapter(fetcher, "2026/27").collect(candidate, program, [])
    values = [
        c.normalized_value
        for c in report.claims
        if c.claim_type is ClaimType.DOCUMENT_BY_COMPLETION
    ]
    assert values == read(GRONINGEN)
    assert report.pages_checked == 1 and report.pages_failed == 0
    gated, ungated = _document_claims(url, html, datetime(2026, 9, 28, tzinfo=UTC))
    assert gated == ungated
    assert [value for key, value in gated if key == "unmapped.document_by_completion"] == values

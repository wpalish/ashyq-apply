"""Programme and campus context cannot leak across a supplemental-document table."""

from datetime import UTC, datetime

import pytest

from app.adapters.document_ir import build_document_ir
from app.adapters.documents.web_documents import read_documents
from app.adapters.extraction import ClaimBuilder, html_to_text
from app.adapters.scope_reader import read_scope
from app.domain.enums import ClaimStatus, DocumentPurpose, SourceSpecificity
from evaluation.research.mapping import evidence_scope

URL = "https://uni.edu/program/computer-science"
ROW = "<table><tr><td>Supplemental Application</td><td>Required</td></tr></table>"
PICKER = """<div><h2><button aria-expanded="false" aria-controls="">Change School System</button></h2>
<section aria-hidden="true"><h2 class="u-visually--hidden">Academic Requirements Picker</h2>
<h2 class="u-visually--hidden">Display Academic Requirements</h2><form>IB Diploma</form></section></div>"""


def read(body, requested="Computer Science (St. George)"):
    html = f"<h1>Computer Science</h1>{body}"
    text = html_to_text(html)
    scope = read_scope(text)
    builder = ClaimBuilder(
        source_url=URL,
        program=requested,
        scope=scope,
        page_text=text,
        official_domain=True,
        specificity=SourceSpecificity.PROGRAM,
        accessed_at=datetime(2026, 10, 3, tzinfo=UTC),
    )
    doc = build_document_ir(html, URL)
    items = read_documents(text, URL, DocumentPurpose.ADMISSION, scope, builder, document=doc)
    assert builder.meta["scope"] == scope
    assert not builder.rejected
    return items, builder.claims, doc


def test_form_picker_does_not_erase_campus_and_qualification_context():
    items, claims, doc = read(
        "<h2>St. George campus</h2><h3>Ontario Requirements</h3>"
        "<p>Ontario Secondary School Diploma (OSSD) with six subjects.</p>" + PICKER + ROW
    )
    assert doc.blocks[-1].section_path == (
        "Computer Science",
        "St. George campus",
        "Ontario Requirements",
    )
    assert len(items) == len(claims) == 1
    claim = claims[0]
    assert claim.normalized_value == "Supplemental Application"
    assert claim.scope.programme == "Computer Science (St. George)"
    assert claim.scope.qualification == "Ontario Secondary School Diploma (OSSD)"
    assert claim.scope.degree is None
    assert claim.status is ClaimStatus.NEEDS_OFFICIAL_CLARIFICATION
    assert "OSSD" in items[0].name
    assert "degree level is not stated" in items[0].format_notes
    assert "Ontario Secondary School Diploma" in claim.relevant_section
    assert claim.original_text_excerpt == "Supplemental Application Required"


def test_explicit_degree_is_read_from_source_heading():
    items, claims, _ = read(
        "<h2>St. George campus</h2><h3>Bachelor admission requirements</h3>" + ROW
    )
    assert len(items) == len(claims) == 1
    assert claims[0].scope.degree == "bachelor"
    assert claims[0].status is ClaimStatus.VERIFIED_CURRENT


@pytest.mark.parametrize(
    "requested, expected",
    [
        ("Computer Science", 0),
        ("Computer Science (St. George)", 1),
        ("Computer Science (Mississauga)", 1),
        ("Computer Science (Scarborough)", 0),
        ("Mathematics (St. George)", 0),
    ],
)
def test_mixed_campus_page_requires_an_explicit_campus_choice(requested, expected):
    items, claims, _ = read(
        "<h2>Mississauga campus</h2>" + ROW + "<h2>St. George campus</h2>" + ROW, requested
    )
    assert len(items) == len(claims) == expected
    if expected:
        assert claims[0].scope.programme == requested


@pytest.mark.parametrize(
    "table",
    [
        ROW.replace("Required", "Not required"),
        ROW.replace("Required", "Required if invited"),
        ROW.replace("Required", "Optional"),
        "<table><tr><td>Supplemental Application</td><td>Optional</td></tr><tr><td>Essay</td><td>Required</td></tr></table>",
        "<p>Supplemental Application</p><p>Required</p>",
        "<table><tr><th>Degree</th><th>Required</th></tr><tr><td>Supplemental Application</td><td>Required</td></tr></table>",
    ],
)
def test_condition_or_another_row_cannot_establish_requirement(table):
    items, claims, _ = read("<h2>St. George campus</h2>" + table)
    assert items == claims == []


def test_real_accordion_heading_with_a_target_remains_evidence_context():
    _, _, doc = read(
        '<h2><button aria-expanded="false" aria-controls="requirements">Bachelor requirements</button></h2>'
        '<section id="requirements">' + ROW + "</section>"
    )
    assert "Bachelor requirements" in doc.blocks[-1].section_path


def test_mapping_preserves_published_qualification_without_using_request_scope():
    scope = evidence_scope(
        {"scope": {"degree": None, "qualification": "Ontario Secondary School Diploma (OSSD)"}},
        university="Example University",
        programme="Computer Science",
        degree=None,
    )
    assert scope.qualification == "Ontario Secondary School Diploma (OSSD)"
    assert scope.degree is None


@pytest.mark.parametrize(
    "heading",
    [
        '<h2 class="sr-only">Bachelor requirements</h2>',
        '<h2><button aria-expanded="false" aria-controls="">Bachelor requirements</button></h2>',
    ],
)
def test_accessible_or_control_heading_outside_form_is_not_discarded(heading):
    _, _, doc = read(heading + ROW)
    assert "Bachelor requirements" in doc.blocks[-1].section_path


def test_accessible_heading_with_evidence_and_an_unrelated_form_is_preserved():
    _, _, doc = read(
        '<div><h2 class="sr-only">Bachelor requirements</h2>'
        "<p>Applicants must submit their diploma.</p><form>Search</form>" + ROW + "</div>"
    )
    assert "Bachelor requirements" in doc.blocks[-1].section_path

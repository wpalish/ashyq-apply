"""Mixed audience pages must not turn exchange rules into degree requirements."""

from __future__ import annotations

import pytest

from app.adapters.document_ir import build_document_ir
from app.adapters.extraction import readable_text
from app.adapters.requirements.section_scope import full_degree_sections
from app.domain.enums import ClaimType
from tests.test_requirements_language_follow import _run, _site

DEGREE = "<h3>Bachelor programmes</h3><div>IELTS overall 6.5, no band below 6.0.</div>"
EXCHANGE = """<h3>Exchange programs</h3><section><h4>English language</h4>
<p>IELTS overall 5.5, no band below 5.0. TOEFL iBT 70.</p>
<p>Exchange students are exempt from the English language test.</p></section>"""
TABLE = """<table><tr><th>Test</th><th>Overall</th><th>Reading</th><th>Writing</th></tr>
<tr><td>IELTS Academic</td><td>5.5</td><td>5.0</td><td>5.0</td></tr></table>"""


def _page(body: str, title: str = "Admission requirements") -> str:
    return f"<html><head><title>{title}</title></head><body><h1>{title}</h1>{body}</body></html>"


@pytest.mark.parametrize(
    "heading",
    [
        "Exchange programs (visiting year)",
        "Exchange students",
        "Student exchange",
        "Visiting students",
        "Non-degree admissions",
        "Nondegree programmes",
        "Non-degree programmes and visiting students",
        "Exchange students (except visiting students)",
        "Undergraduate exchange and visiting students",
        "Exchange students (bachelor and master level)",
        "Exchange programmes for bachelor and master students",
    ],
)
def test_explicit_non_degree_scope_ends_at_peer_heading(heading):
    html = _page(f"<h2>{heading}</h2><p>IELTS overall 5.5.</p><h2>Degree study</h2>{DEGREE}")
    view = full_degree_sections(html, readable_text(html))
    assert view.excluded_sections == 1
    assert "5.5" not in view.html
    assert "6.5" in view.html


@pytest.mark.parametrize("body", [EXCHANGE + DEGREE, DEGREE + EXCHANGE])
@pytest.mark.asyncio
async def test_adapter_keeps_degree_prose_and_discards_exchange_bands_and_waiver(
    settings, tmp_path, body
):
    result = await _run(settings, _site(tmp_path, _page(body)))
    values = {c.claim_type: c.normalized_value for c in result.claims}
    assert values[ClaimType.IELTS_MIN_OVERALL] == 6.5
    assert values[ClaimType.IELTS_MIN_SUBSCORE] == 6.0
    assert ClaimType.TOEFL_MIN_TOTAL not in values
    assert ClaimType.ENGLISH_TEST_WAIVER not in values
    assert all("5.5" not in c.original_text_excerpt for c in result.claims)


@pytest.mark.parametrize("title", ["Admission requirements", "Campus museum"])
@pytest.mark.asyncio
async def test_exchange_table_does_not_override_degree_prose_on_either_table_route(
    settings, tmp_path, title
):
    degree_table = TABLE.replace("5.5", "6.5").replace("5.0", "6.0")
    body = f"<h3>Exchange programs</h3>{TABLE}<h3>Bachelor programmes</h3>{degree_table}"
    result = await _run(settings, _site(tmp_path, _page(body, title)))
    values = {c.claim_type: c.normalized_value for c in result.claims}
    assert values[ClaimType.IELTS_MIN_OVERALL] == 6.5
    assert values[ClaimType.IELTS_MIN_SUBSCORE] == {"reading": 6.0, "writing": 6.0}


@pytest.mark.parametrize("container", ["aside", "nav", "header", "footer"])
@pytest.mark.asyncio
async def test_sidebar_heading_cannot_delete_degree_content(settings, tmp_path, container):
    html = _page(f"<{container}>{EXCHANGE}</{container}><div>IELTS overall 6.5.</div>")
    result = await _run(settings, _site(tmp_path, html))
    assert [
        c.normalized_value for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL
    ] == [6.5]


def test_nested_containers_preserve_later_heading_and_table_structure():
    html = _page(f"<h2>Exchange programs</h2><div>{TABLE}<h2>Bachelor programmes</h2>{TABLE}</div>")
    view = full_degree_sections(html, readable_text(html))
    cells = build_document_ir(view.html, "fixture://page").blocks
    assert len([b for b in cells if b.kind == "table_cell" and b.text == "5.5"]) == 1


@pytest.mark.parametrize(
    "heading",
    [
        "Bachelor and exchange programs",
        "Degree programmes / exchange programs",
        "Undergraduate and exchange admissions",
        "Degree and non-degree students",
        "First-year and exchange students",
        "Degree-seeking or exchange students",
        "Undergraduate, exchange students",
        "Requirements excluding exchange students",
        "Not for visiting students",
        "Bachelor applicants (not exchange students)",
        "Requirements do not apply to exchange students",
        "Non-degree students excluded from this requirement",
        "Exchange rates",
        "Visiting our campus",
    ],
)
def test_joint_negated_and_unrelated_headings_keep_original_fast_path(heading):
    html = _page(f"<h2>{heading}</h2><div>IELTS overall 6.5.</div>")
    text = readable_text(html)
    view = full_degree_sections(html, text)
    assert view.html == html
    assert view.prose == (text,)
    assert view.excluded_sections == 0


@pytest.mark.parametrize("container", ["table", "td"])
def test_heading_inside_table_cannot_scope_later_page_content(container):
    local = f"<{container}><h3>Exchange programs</h3><p>IELTS overall 5.5.</p></{container}>"
    html = _page(local + "<p>IELTS overall 6.5.</p>")
    view = full_degree_sections(html, readable_text(html))
    assert "5.5" not in view.html
    assert "6.5" in view.html


@pytest.mark.asyncio
async def test_no_prose_requirement_can_bridge_a_removed_section(settings, tmp_path):
    body = "<p>IELTS overall</p>" + EXCHANGE + "<h3>Other requirements</h3><div>6.5.</div>"
    result = await _run(settings, _site(tmp_path, _page(body)))
    assert not any(c.claim_type is ClaimType.IELTS_MIN_OVERALL for c in result.claims)


@pytest.mark.asyncio
async def test_only_exchange_requirements_remain_unknown(settings, tmp_path):
    result = await _run(settings, _site(tmp_path, _page(EXCHANGE + TABLE)))
    assert not any(
        c.claim_type
        in {
            ClaimType.IELTS_MIN_OVERALL,
            ClaimType.IELTS_MIN_SUBSCORE,
            ClaimType.TOEFL_MIN_TOTAL,
            ClaimType.ENGLISH_TEST_WAIVER,
        }
        for c in result.claims
    )

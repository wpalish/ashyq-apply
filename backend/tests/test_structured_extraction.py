"""IELTS from table structure (V2-30C), on the shapes the reviews quoted."""

from __future__ import annotations

from app.adapters.document_ir import build_document_ir
from app.adapters.extraction import ClaimBuilder, html_to_text
from app.adapters.structured_extraction import extract_table_requirements
from app.domain.enums import ClaimType
from tests.test_document_ir import GRONINGEN, UBC


def _run(html: str):
    builder = ClaimBuilder(
        source_url="https://u.edu/x", official_domain=True, page_text=html_to_text(html)
    )
    claims = extract_table_requirements(build_document_ir(html, "https://u.edu/x"), builder)
    return {c.claim_type: c for c in claims}, builder


def test_ubc_row_gives_overall_and_part_floor_from_one_cell():
    claims, _ = _run(UBC)
    assert claims[ClaimType.IELTS_MIN_OVERALL].normalized_value == 6.5
    assert claims[ClaimType.IELTS_MIN_SUBSCORE].normalized_value == 6.0
    assert (
        claims[ClaimType.IELTS_MIN_OVERALL].original_text_excerpt
        == "6.5, with no part less than 6.0"
    )


def test_groningen_columns_give_overall_and_a_per_section_map():
    claims, _ = _run(GRONINGEN)
    assert claims[ClaimType.IELTS_MIN_OVERALL].normalized_value == 6.5
    assert claims[ClaimType.IELTS_MIN_SUBSCORE].normalized_value == {
        "reading": 6.0,
        "writing": 6.0,
    }


def test_a_toefl_row_is_never_read_as_ielts():
    html = """<table><tr><th>Test</th><th>Overall</th></tr>
    <tr><td>TOEFL iBT</td><td>6.5</td></tr></table>"""
    claims, _ = _run(html)
    assert claims == {}


def test_a_column_that_names_nothing_is_not_guessed():
    html = """<table><tr><th>Test</th><th>2027</th></tr>
    <tr><td>IELTS</td><td>6.5</td></tr></table>"""
    assert _run(html)[0] == {}


def test_a_floor_above_the_overall_is_not_read():
    html = """<table><tr><th>Test</th><th>Minimum</th></tr>
    <tr><td>IELTS</td><td>6.0, with no part less than 6.5</td></tr></table>"""
    assert _run(html)[0] == {}


def test_every_excerpt_passes_the_verbatim_check():
    for html in (UBC, GRONINGEN):
        claims, builder = _run(html)
        assert claims and not builder.rejected


def test_a_population_named_elsewhere_on_the_page_is_not_the_tables():
    """Run 75: UBC's IELTS row was filed as 'transfer' from another section."""
    from app.adapters.scope_reader import read_scope

    html = UBC.replace(
        "<h1>English language competency</h1>",
        "<h1>English language competency</h1><h2>Transfer students</h2>"
        "<p>Transfer students from another university apply separately.</p>",
    )
    builder = ClaimBuilder(
        source_url="https://u.edu/x",
        official_domain=True,
        page_text=html_to_text(html),
        scope=read_scope(html_to_text(html)),
    )
    page_population = builder.meta["scope"].population
    claims = extract_table_requirements(build_document_ir(html, "https://u.edu/x"), builder)
    assert page_population == "transfer"
    assert claims
    assert all(c.scope.population is None for c in claims)
    # The builder's page scope is restored for whatever reads the page next.
    assert builder.meta["scope"].population == page_population

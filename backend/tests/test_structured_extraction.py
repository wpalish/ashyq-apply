"""IELTS from table structure (V2-30C), on the shapes the reviews quoted."""

from __future__ import annotations

import pytest

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


@pytest.mark.parametrize(
    "html",
    [
        """<h2>International students</h2><table>
        <tr><th>Test</th><th>Overall</th><th>Reading</th></tr>
        <tr><td>IELTS</td><td>6.5</td><td>6.0</td></tr></table>
        <h2>Domestic students</h2><table>
        <tr><th>Test</th><th>Overall</th><th>Writing</th></tr>
        <tr><td>IELTS</td><td>7.0</td><td>7.0</td></tr></table>""",
        """<table><tr><th>Test</th><th>Applicants</th><th>Overall</th>
        <th>Reading</th><th>Writing</th></tr>
        <tr><th>IELTS</th><th>International students</th><td>6.5</td>
        <td>6.0</td><td>Not stated</td></tr>
        <tr><th>IELTS</th><th>Domestic students</th><td>7.0</td>
        <td>Not stated</td><td>7.0</td></tr></table>""",
    ],
    ids=["separate-tables", "separate-rows"],
)
def test_independent_applicant_requirements_are_not_combined(html):
    from app.domain.claim_scope import ClaimScope
    from app.domain.enums import ClaimStatus, SourceSpecificity

    page_scope = ClaimScope()
    builder = ClaimBuilder(
        source_url="https://u.edu/requirements",
        official_domain=True,
        specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
        page_text=html_to_text(html),
        scope=page_scope,
    )
    claims = extract_table_requirements(build_document_ir(html, "https://u.edu/x"), builder)
    assert [(c.claim_type, c.normalized_value, c.scope.population) for c in claims] == [
        (ClaimType.IELTS_MIN_OVERALL, 6.5, "international"),
        (ClaimType.IELTS_MIN_SUBSCORE, {"reading": 6.0}, "international"),
        (ClaimType.IELTS_MIN_OVERALL, 7.0, "domestic"),
        (ClaimType.IELTS_MIN_SUBSCORE, {"writing": 7.0}, "domestic"),
    ]
    assert all(c.status is ClaimStatus.VERIFIED_CURRENT for c in claims)
    assert not builder.rejected
    assert builder.meta["scope"] is page_scope


def test_each_applicant_row_keeps_its_compound_overall_and_floor():
    from app.domain.claim_scope import ClaimScope

    html = """<table><tr><th>Test</th><th>Applicants</th><th>Minimum</th></tr>
    <tr><th>IELTS</th><th>International students</th>
    <td>6.5, with no part less than 6.0</td></tr>
    <tr><th>IELTS</th><th>Domestic students</th>
    <td>7.0, with no part less than 6.5</td></tr></table>"""
    builder = ClaimBuilder(
        source_url="https://u.edu/requirements",
        official_domain=True,
        page_text=html_to_text(html),
        scope=ClaimScope(),
    )
    claims = extract_table_requirements(build_document_ir(html, "https://u.edu/x"), builder)
    assert [(c.claim_type, c.normalized_value, c.scope.population) for c in claims] == [
        (ClaimType.IELTS_MIN_OVERALL, 6.5, "international"),
        (ClaimType.IELTS_MIN_SUBSCORE, 6.0, "international"),
        (ClaimType.IELTS_MIN_OVERALL, 7.0, "domestic"),
        (ClaimType.IELTS_MIN_SUBSCORE, 6.5, "domestic"),
    ]


def test_subscore_evidence_contains_every_band_in_the_map():
    html = """<table><tr><th>Test</th><th>Reading</th><th>Writing</th></tr>
    <tr><td>IELTS</td><td>6.0</td><td>7.0</td></tr></table>"""
    claims, builder = _run(html)
    claim = claims[ClaimType.IELTS_MIN_SUBSCORE]
    assert claim.normalized_value == {"reading": 6.0, "writing": 7.0}
    assert claim.original_text_excerpt == "6.0 7.0"
    assert not builder.rejected


def test_a_map_is_not_claimed_when_quote_clipping_would_remove_a_band():
    from app.schemas.claim import MAX_EXCERPT_CHARS

    html = f"""<table><tr><th>Test</th><th>Overall</th><th>Reading</th>
    <th>Details</th><th>Writing</th></tr><tr><td>IELTS</td><td>6.5</td>
    <td>6.0</td><td>{"context " * MAX_EXCERPT_CHARS}</td><td>7.0</td></tr></table>"""
    claims, _ = _run(html)
    assert set(claims) == {ClaimType.IELTS_MIN_OVERALL}
    assert claims[ClaimType.IELTS_MIN_OVERALL].normalized_value == 6.5

"""DocumentIR keeps what the markup relates (V2-30B).

The shapes are the ones both reviews quoted from real pages: UBC's English
table puts IELTS in one row with its overall and per-part minimum; Groningen's
language table has one column per section.
"""

from __future__ import annotations

import pytest

from app.adapters.document_ir import build_document_ir

UBC = """<html><head><title>English language competency</title></head><body>
<nav><a href="/menu">Menu</a></nav>
<h1>English language competency</h1>
<h2>Tests that satisfy the English Language Admission Standard</h2>
<table><caption>Accepted tests</caption>
<thead><tr><th>Test</th><th>Name</th><th>Minimum score</th></tr></thead>
<tbody>
<tr><th scope="row">IELTS</th><td>International English Language Testing System (Academic)</td>
<td>6.5, with no part less than 6.0</td></tr>
<tr><th scope="row">PTE</th><td>Pearson Test of English (Academic)</td><td>Overall: 65</td></tr>
</tbody></table>
<p>See <a href="/applying-ubc/requirements">general requirements</a>.</p>
</body></html>"""

GRONINGEN = """<html><body><h2>Language requirements</h2>
<table>
<tr><th>Test</th><th>Overall</th><th>Reading</th><th>Writing</th></tr>
<tr><td>IELTS Academic</td><td>6.5</td><td>6.0</td><td>6.0</td></tr>
<tr><td>TOEFL iBT</td><td>90</td><td>21</td><td>21</td></tr>
</table></body></html>"""


def _cell(doc, text):
    return next(b for b in doc.blocks if b.kind == "table_cell" and b.text == text)


def test_a_ubc_style_row_keeps_its_test_and_its_column():
    doc = build_document_ir(UBC, "https://you.ubc.ca/applying-ubc/requirements/elc/")
    value = _cell(doc, "6.5, with no part less than 6.0")
    assert value.row_headers == ("IELTS",)
    assert value.column_headers == ("Minimum score",)
    assert value.caption == "Accepted tests"
    assert value.section_path == (
        "English language competency",
        "Tests that satisfy the English Language Admission Standard",
    )
    # A row header is context, never a value of its own.
    assert not [b for b in doc.blocks if b.kind == "table_cell" and b.text == "IELTS"]


def test_a_groningen_style_table_ties_each_band_to_its_section_and_test():
    doc = build_document_ir(GRONINGEN, "https://www.rug.nl/fse/language")
    overall = next(b for b in doc.blocks if b.kind == "table_cell" and b.col == 1 and b.row == 1)
    assert (overall.text, overall.row_headers, overall.column_headers) == (
        "6.5",
        ("IELTS Academic",),
        ("Overall",),
    )
    writing = next(b for b in doc.blocks if b.kind == "table_cell" and b.col == 3 and b.row == 2)
    assert (writing.text, writing.row_headers, writing.column_headers) == (
        "21",
        ("TOEFL iBT",),
        ("Writing",),
    )


def test_spans_are_expanded_so_a_merged_header_covers_every_column():
    html = """<table>
    <tr><th rowspan="2">Test</th><th colspan="2">Minimum</th></tr>
    <tr><th>Overall</th><th>Each part</th></tr>
    <tr><td>IELTS</td><td>6.5</td><td>6.0</td></tr></table>"""
    doc = build_document_ir(html, "https://u.edu/x")
    each = _cell(doc, "6.0")
    assert each.column_headers == ("Minimum", "Each part")
    assert each.row_headers == ("IELTS",)


def test_explicit_headers_attributes_win():
    html = """<table><tr><th id="t">Test</th><th id="o">Overall</th></tr>
    <tr><td>IELTS</td><td headers="o">6.5</td></tr></table>"""
    assert _cell(build_document_ir(html, "https://u.edu/x"), "6.5").column_headers == ("Overall",)


def test_definition_lists_become_key_value_blocks():
    doc = build_document_ir(
        "<dl><dt>Application deadline</dt><dd>15 January 2027</dd></dl>", "https://u.edu/x"
    )
    kv = [b for b in doc.blocks if b.kind == "key_value"]
    assert [(b.label, b.text) for b in kv] == [("Application deadline", "15 January 2027")]


def test_links_are_absolute_and_carry_their_section():
    doc = build_document_ir(UBC, "https://you.ubc.ca/applying-ubc/requirements/elc/")
    link = next(lk for lk in doc.links if lk.text == "general requirements")
    assert link.url == "https://you.ubc.ca/applying-ubc/requirements"
    assert link.section_path[-1] == ("Tests that satisfy the English Language Admission Standard")


def test_block_text_is_verbatim_from_the_page():
    """A claim built from a block must still pass the verbatim check."""
    from app.adapters.extraction import html_to_text

    doc = build_document_ir(UBC, "https://you.ubc.ca/x")
    page = " ".join(html_to_text(UBC).split())
    for block in doc.blocks:
        assert block.text in page, block


def test_rubbish_does_not_raise():
    assert build_document_ir("", "https://u.edu/x").blocks == []
    assert build_document_ir("<table><tr><td colspan='x'>a", "https://u.edu/x").blocks


# Prospective synthetic regressions; no original university artifacts are read.
def test_explicit_adjacent_year_label_keeps_literal_text_and_exact_dom_provenance():
    html = """<main><div><div><h1>Qualification requirements</h1>
    <div class="visual-subtitle">Academic year 2030/2031</div></div>
    <div><p>Foundation years are not considered.</p></div></div></main>"""
    doc = build_document_ir(html, "https://example.edu/qualifications")
    note = next(b for b in doc.blocks if b.kind == "paragraph")
    assert note.id == "b1"  # The added context creates no new quote block.
    assert note.text == "Foundation years are not considered."
    assert note.section_path == ("Qualification requirements",)
    (label,) = note.section_year_labels
    assert label.text == "Academic year 2030/2031"
    assert label.section_path == note.section_path
    assert label.heading_dom_path == "/html[1]/body[1]/main[1]/div[1]/div[1]/h1[1]"
    assert label.dom_path == "/html[1]/body[1]/main[1]/div[1]/div[1]/div[1]"
    assert not note.row_year_cells


@pytest.mark.parametrize("wrapper", ["nav", "aside", "footer", "header", "form"])
def test_year_labels_in_navigation_or_controls_do_not_become_section_scope(wrapper):
    html = f"""<{wrapper}><h1>Menu</h1><div>Academic year 2030/2031</div></{wrapper}>
    <main><h1>Qualifications</h1><p>Foundation years are not considered.</p></main>"""
    doc = build_document_ir(html, "https://example.edu/x")
    assert not next(
        b for b in doc.blocks if b.text == "Foundation years are not considered."
    ).section_year_labels


@pytest.mark.parametrize(
    "label",
    [
        '<div role="navigation">Academic year 2030/2031</div>',
        "<div hidden>Academic year 2030/2031</div>",
        '<div aria-hidden="true">Academic year 2030/2031</div>',
        '<div><a href="/old">Academic year 2030/2031</a></div>',
        "<p>Other unrelated content.</p><div>Academic year 2030/2031</div>",
        "<div>Applications for fall 2030</div>",
    ],
)
def test_only_adjacent_explicit_academic_year_labels_are_kept(label):
    doc = build_document_ir(
        f"<h1>Qualifications</h1>{label}<p>Policy.</p>", "https://example.edu/x"
    )
    assert not next(b for b in doc.blocks if b.text == "Policy.").section_year_labels


def test_section_year_labels_stay_separate_between_heading_scopes():
    html = """<h1>Campus A</h1><div>Academic year 2030/2031</div><p>Policy A.</p>
    <h1>Campus B</h1><div>Academic year 2031/2032</div><p>Policy B.</p>"""
    doc = build_document_ir(html, "https://example.edu/x")
    a = next(b for b in doc.blocks if b.text == "Policy A.")
    b = next(b for b in doc.blocks if b.text == "Policy B.")
    assert a.section_year_labels[0].text == "Academic year 2030/2031"
    assert b.section_year_labels[0].text == "Academic year 2031/2032"
    assert a.section_year_labels[0].section_path == ("Campus A",)
    assert b.section_year_labels[0].section_path == ("Campus B",)


def test_footer_does_not_inherit_a_content_year_label():
    doc = build_document_ir(
        "<main><h1>Fees</h1><div>Academic year 2030/2031</div><p>Content.</p></main>"
        "<footer><p>Footer note.</p></footer>",
        "https://example.edu/x",
    )
    assert not next(b for b in doc.blocks if b.text == "Footer note.").section_year_labels


def test_year_cells_keep_same_row_and_original_blank_or_merged_coordinates():
    doc = build_document_ir(
        """<table><tr><th>Applicant</th><th>Year</th><th>Fee</th></tr>
    <tr><td>International</td><td>2030-2031</td><td>EUR 19800</td></tr>
    <tr><td>Domestic</td><td></td><td>EUR 19800</td></tr></table>""",
        "https://example.edu/x",
    )
    fees = [b for b in doc.blocks if b.text == "EUR 19800"]
    (year,) = fees[0].row_year_cells
    assert (year.table_id, year.row, year.col, year.rowspan, year.colspan) == (0, 1, 1, 1, 1)
    assert year.dom_path == "/html[1]/body[1]/table[1]/tr[2]/td[2]"
    assert year.text == "2030-2031" and year.column_headers == ("Year",)
    (blank,) = fees[1].row_year_cells
    assert blank.text == "" and blank.row == 2
    assert fees[0].row_headers == ("International",)  # Year is not a row header.


@pytest.mark.parametrize("container", ["main", "article", "section"])
def test_year_label_does_not_exit_into_a_distinct_unheaded_semantic_container(container):
    html = f"""<{container}><h2>Qualifications</h2>
    <div>Academic year 2030/2031</div><p>First policy.</p></{container}>
    <{container}><p>Unheaded sibling policy.</p></{container}>"""
    doc = build_document_ir(html, "https://example.edu/x")
    first = next(b for b in doc.blocks if b.text == "First policy.")
    sibling = next(b for b in doc.blocks if b.text == "Unheaded sibling policy.")
    assert first.section_year_labels
    assert not sibling.section_year_labels
    assert first.semantic_container_dom_path != sibling.semantic_container_dom_path
    assert first.section_year_labels[0].container_dom_path == first.semantic_container_dom_path


def test_same_heading_text_in_different_sections_keeps_distinct_dom_origin():
    html = """<main><section><h2>Qualifications</h2><div>Academic year 2030/2031</div>
    <p>First policy.</p></section><section><h2>Qualifications</h2>
    <div>Academic year 2031/2032</div><p>Second policy.</p></section></main>"""
    doc = build_document_ir(html, "https://example.edu/x")
    first = next(b for b in doc.blocks if b.text == "First policy.")
    second = next(b for b in doc.blocks if b.text == "Second policy.")
    assert first.section_path == second.section_path == ("Qualifications",)
    assert first.section_year_labels[0].container_dom_path.endswith("/section[1]")
    assert second.section_year_labels[0].container_dom_path.endswith("/section[2]")
    assert second.section_year_labels[0].text == "Academic year 2031/2032"


def test_nested_div_heading_wrapper_and_body_share_only_the_same_explicit_container():
    html = """<main><div><div><h2>Qualifications</h2><div>Academic year 2030/2031</div></div>
    <div><p>Same content policy.</p></div></div></main>"""
    doc = build_document_ir(html, "https://example.edu/x")
    note = next(b for b in doc.blocks if b.text == "Same content policy.")
    (label,) = note.section_year_labels
    assert (
        label.container_dom_path == note.semantic_container_dom_path == "/html[1]/body[1]/main[1]"
    )
    assert note.id == "b1"


@pytest.mark.parametrize(
    "label",
    [
        "<div><span hidden>Academic year 2030/2031</span></div>",
        '<div><span aria-hidden="true">Academic year 2030/2031</span></div>',
        '<div><span style="display: none">Academic year 2030/2031</span></div>',
        '<div><span class="sr-only">Academic year 2030/2031</span></div>',
        "<div><nav>Academic year 2030/2031</nav></div>",
        "<div><footer>Academic year 2030/2031</footer></div>",
        '<div><span role="navigation">Academic year 2030/2031</span></div>',
        "<div><button>Academic year 2030/2031</button></div>",
        "<div><form>Academic year 2030/2031</form></div>",
    ],
)
def test_year_label_checks_hidden_navigation_and_control_descendants(label):
    doc = build_document_ir(
        f"<main><h1>Qualifications</h1>{label}<p>Policy.</p></main>", "https://example.edu/x"
    )
    assert not next(b for b in doc.blocks if b.text == "Policy.").section_year_labels


@pytest.mark.parametrize(
    "year_cell,year_header,reason",
    [
        ("<td hidden>2030/2031</td>", "<th>Year</th>", "non_content_year_cell"),
        (
            '<td><span aria-hidden="true">2030/2031</span></td>',
            "<th>Year</th>",
            "non_content_year_cell",
        ),
        ("<td>2030/2031</td>", "<th hidden>Year</th>", "non_content_year_header"),
        ("<td>2030/2031</td>", "<th><span hidden>Year</span></th>", "non_content_year_header"),
        ("<td>2030/2031</td>", "<th><nav>Year</nav></th>", "non_content_year_header"),
    ],
)
def test_hidden_or_navigation_year_sources_remain_explicitly_unusable(
    year_cell, year_header, reason
):
    html = (
        f"<table><tr>{year_header}<th>Fee</th></tr><tr>{year_cell}<td>EUR 19800</td></tr></table>"
    )
    fee = _cell(build_document_ir(html, "https://example.edu/x"), "EUR 19800")
    (year,) = fee.row_year_cells
    assert year.blocked_reason == reason
    assert year.dom_path.endswith("/tr[2]/td[1]")
    assert year.header_dom_paths == ("/html[1]/body[1]/table[1]/tr[1]/th[1]",)


@pytest.mark.parametrize(
    "headers", ['headers="a"', 'headers="missing"', 'headers=""', 'headers="y y"']
)
def test_explicit_non_year_or_unresolved_headers_never_fall_back_to_position(headers):
    html = f"""<table><tr><th id="a">Applicant</th><th id="y">Year</th><th>Fee</th></tr>
    <tr><td>International</td><td {headers}>2030/2031</td><td>EUR 19800</td></tr></table>"""
    (year,) = _cell(build_document_ir(html, "https://example.edu/x"), "EUR 19800").row_year_cells
    assert year.header_origin == "explicit"
    assert year.blocked_reason is not None
    assert year.column_headers != ("Year",) or headers == 'headers="y y"'


def test_valid_explicit_year_header_list_has_exact_header_provenance():
    html = """<table><tr><th id="y">Year</th><th>Fee</th></tr>
    <tr><td headers="y">2030/2031</td><td>EUR 19800</td></tr></table>"""
    (year,) = _cell(build_document_ir(html, "https://example.edu/x"), "EUR 19800").row_year_cells
    assert year.header_origin == "explicit"
    assert year.column_headers == ("Year",) and year.blocked_reason is None
    assert year.header_dom_paths == ("/html[1]/body[1]/table[1]/tr[1]/th[1]",)


def test_year_row_header_has_original_header_proof_without_inventing_a_value_block():
    html = """<table><tr><th>Year</th><th>Fee</th></tr>
    <tr><th scope="row">2030/2031</th><td>EUR 19800</td></tr></table>"""
    doc = build_document_ir(html, "https://example.edu/x")
    fee = _cell(doc, "EUR 19800")
    (year,) = fee.row_year_cells
    assert (
        year.source_kind == "row_header" and year.source_tag == "th" and year.source_scope == "row"
    )
    assert year.block_id is None and year.blocked_reason is None
    assert year.dom_path == "/html[1]/body[1]/table[1]/tr[2]/th[1]"
    assert fee.row_headers == ("2030/2031",)
    assert not any(b.text == "2030/2031" for b in doc.blocks)


def test_dropped_control_cannot_erase_original_year_header_classification():
    doc = build_document_ir(
        "<table><tr><th><form>Year</form></th><th>Fee</th></tr>"
        "<tr><td>2030/2031</td><td>EUR 19800</td></tr></table>",
        "https://example.edu/x",
    )
    (year,) = _cell(doc, "EUR 19800").row_year_cells
    assert year.column_headers == ("Year",)
    assert year.blocked_reason == "non_content_year_header"
    assert year.header_dom_paths == ("/html[1]/body[1]/table[1]/tr[1]/th[1]",)

"""DocumentIR keeps what the markup relates (V2-30B).

The shapes are the ones both reviews quoted from real pages: UBC's English
table puts IELTS in one row with its overall and per-part minimum; Groningen's
language table has one column per section.
"""

from __future__ import annotations

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

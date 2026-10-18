"""PDF map ticket 03: a PDF read page by page, with a title and a DocumentIR.

Fixtures are the bundled synthetic Groningen fee PDF and PDFs built here with
pypdf's writer. No network, nothing copied from a university.
"""

from __future__ import annotations

import ast
import io
from collections.abc import Sequence
from pathlib import Path

import pytest

pypdf = pytest.importorskip("pypdf", reason="pypdf cannot be imported in this environment")

from pypdf import PdfWriter  # noqa: E402
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject  # noqa: E402

from app.adapters import pdf_document  # noqa: E402
from app.adapters.extraction import pdf_to_text  # noqa: E402
from app.adapters.pdf_document import (  # noqa: E402
    MAX_PDF_PAGES,
    build_pdf_ir,
    page_of,
    pdf_text,
    read_pdf,
)
from app.domain.claim_verifier import normalize_text  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "app/corpus/pages/u-groningen/fees.pdf"
URL = "https://www.example.edu/files/fees-2026.pdf"


def _escape(line: str) -> str:
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(pages: Sequence[Sequence[str] | None], *, title: str | None = None) -> bytes:
    """One page per entry: a list of text lines, or ``None`` for a page with a
    filled rectangle and no text (what a scan looks like to a text extractor)."""
    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    for lines in pages:
        page = writer.add_blank_page(width=600, height=400)
        stream = DecodedStreamObject()
        if lines is None:
            stream.set_data(b"0.5 g 20 20 500 300 re f")
        else:
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
            )
            ops = ["BT /F1 10 Tf 14 TL 20 370 Td"]
            ops += [f"({_escape(line)}) Tj T*" for line in lines]
            ops.append("ET")
            stream.set_data("\n".join(ops).encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    if title is not None:
        writer.add_metadata({"/Title": title})
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


THREE_PAGES = [
    ["Admissions and fees regulation", "Applications open in October."],
    ["2. TUITION FEES", "Tuition fee: EUR 18,000 per year", "Applications open in October."],
    ["3. Scholarships", "Merit awards are reviewed in spring."],
]


@pytest.fixture(scope="module")
def three_page_pdf() -> bytes:
    return build_pdf(THREE_PAGES)


def test_the_bundled_fee_pdf_reads_as_one_readable_page() -> None:
    doc = read_pdf(FIXTURE.read_bytes(), "https://www.rug.nl/education/fees.pdf")
    assert doc.status == "readable"
    assert doc.total_pages == 1 and not doc.truncated
    assert [p.number for p in doc.pages] == [1]
    assert doc.pages[0].has_text
    assert doc.title == "University of Groningen - Statement of Tuition and Fees"
    assert page_of(doc, "Tuition fee [non-EEA students]: EUR 16,500 per year") == 1
    assert doc.parse_ms >= 0


def test_page_numbers_are_one_based_and_stable_across_reads(three_page_pdf: bytes) -> None:
    first = read_pdf(three_page_pdf, URL)
    second = read_pdf(three_page_pdf, URL)
    assert first.status == "readable"
    assert [p.number for p in first.pages] == [1, 2, 3]
    assert first.pages == second.pages
    assert first.total_pages == 3 and not first.truncated


def test_page_of_names_the_single_page_or_none(three_page_pdf: bytes) -> None:
    doc = read_pdf(three_page_pdf, URL)
    assert page_of(doc, "Tuition fee: EUR 18,000 per year") == 2
    assert page_of(doc, "Tuition  fee:\nEUR 18,000") == 2  # whitespace normalised
    assert page_of(doc, "Merit awards are reviewed") == 3
    assert page_of(doc, "Applications open in October.") is None  # on pages 1 and 2
    assert page_of(doc, "Housing is guaranteed") is None
    assert page_of(doc, "   ") is None


def test_title_prefers_metadata_then_first_line_then_file_name(three_page_pdf: bytes) -> None:
    assert read_pdf(three_page_pdf, URL).title == "Admissions and fees regulation"
    with_meta = build_pdf(THREE_PAGES, title="  Fee   Regulation 2026 ")
    assert read_pdf(with_meta, URL).title == "Fee Regulation 2026"
    scanned = build_pdf([None])
    assert read_pdf(scanned, "https://x.edu/docs/Fee%20Scan.pdf").title == "Fee Scan.pdf"
    long_first_line = build_pdf([["x" * 130, "short"]])
    assert read_pdf(long_first_line, URL).title == "fees-2026.pdf"


def test_an_image_only_pdf_has_no_text_layer() -> None:
    doc = read_pdf(build_pdf([None, None]), URL)
    assert doc.status == "no_text_layer"
    assert [p.has_text for p in doc.pages] == [False, False]
    assert pdf_text(doc) == ""
    assert build_pdf_ir(doc).blocks[0].text == "p. 1"


def test_a_mixed_pdf_with_one_text_page_is_readable() -> None:
    doc = read_pdf(build_pdf([None, ["Fee schedule"]]), URL)
    assert doc.status == "readable"
    assert [p.has_text for p in doc.pages] == [False, True]
    assert doc.title == "fees-2026.pdf"  # the first page has no line to name it


@pytest.mark.parametrize(
    "content",
    [b"", b"not a pdf at all", b"%PDF-1.7\n1 0 obj << /Type /Catalog", FIXTURE.read_bytes()[:200]],
)
def test_malformed_bytes_never_raise(content: bytes) -> None:
    doc = read_pdf(content, URL)
    assert doc.status == "malformed"
    assert doc.pages == []
    assert doc.title == "fees-2026.pdf"
    assert pdf_text(doc) == ""
    assert build_pdf_ir(doc).blocks == []
    assert page_of(doc, "anything") is None


def test_forty_five_pages_read_forty_and_say_truncated() -> None:
    body = build_pdf([[f"Page marker {n:02d}"] for n in range(1, 46)])
    doc = read_pdf(body, URL)
    assert MAX_PDF_PAGES == 40
    assert doc.total_pages == 45
    assert len(doc.pages) == 40 and doc.pages[-1].number == 40
    assert doc.truncated is True
    assert page_of(doc, "Page marker 40") == 40
    assert page_of(doc, "Page marker 41") is None
    assert normalize_text(pdf_text(doc)) == normalize_text(pdf_to_text(body, max_pages=40))


def test_the_time_cap_stops_at_the_pages_done(
    monkeypatch: pytest.MonkeyPatch, three_page_pdf: bytes
) -> None:
    ticks = iter([0.0, 0.1, 0.2, 5.0, 5.0, 5.0])
    monkeypatch.setattr(pdf_document, "_clock", lambda: next(ticks))
    doc = read_pdf(three_page_pdf, URL, time_cap_s=3.0)
    assert [p.number for p in doc.pages] == [1, 2]
    assert doc.status == "readable"
    assert doc.truncated is True
    assert doc.total_pages == 3


def test_the_time_cap_with_no_page_done_is_too_slow(
    monkeypatch: pytest.MonkeyPatch, three_page_pdf: bytes
) -> None:
    ticks = iter([0.0, 10.0, 10.0])
    monkeypatch.setattr(pdf_document, "_clock", lambda: next(ticks))
    doc = read_pdf(three_page_pdf, URL, time_cap_s=3.0)
    assert doc.status == "too_slow"
    assert doc.pages == [] and doc.truncated is True
    assert doc.parse_ms == 10_000


def test_a_page_that_fails_to_extract_reads_as_empty(
    monkeypatch: pytest.MonkeyPatch, three_page_pdf: bytes
) -> None:
    from pypdf import PageObject

    original = PageObject.extract_text
    calls = {"n": 0}

    def flaky(self: PageObject, *args: object, **kwargs: object) -> str:
        calls["n"] += 1
        if calls["n"] == 2:
            raise ValueError("broken content stream")
        return original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(PageObject, "extract_text", flaky)
    doc = read_pdf(three_page_pdf, URL)
    assert [p.has_text for p in doc.pages] == [True, False, True]
    assert doc.status == "readable"


def test_ir_carries_the_page_and_the_numbered_heading(three_page_pdf: bytes) -> None:
    ir = build_pdf_ir(read_pdf(three_page_pdf, URL))
    assert ir.url == URL and ir.title == "Admissions and fees regulation"
    by_text = {block.text: block for block in ir.blocks}
    (fee,) = [b for b in ir.blocks if "EUR 18,000" in b.text]
    assert fee.text == "Tuition fee: EUR 18,000 per year Applications open in October."
    assert fee.kind == "paragraph"
    assert fee.section_path == ("p. 2", "2. TUITION FEES")
    assert by_text["2. TUITION FEES"].kind == "heading"
    assert by_text["Merit awards are reviewed in spring."].section_path == (
        "p. 3",
        "3. Scholarships",
    )
    page_headings = [b.text for b in ir.blocks if b.kind == "heading" and b.text.startswith("p. ")]
    assert page_headings == ["p. 1", "p. 2", "p. 3"]
    assert len({b.id for b in ir.blocks}) == len(ir.blocks)


def test_ir_splits_paragraphs_on_blank_lines_and_finds_short_headings() -> None:
    doc = pdf_document.PdfDocument(
        url=URL,
        title="t",
        pages=[
            pdf_document.PdfPage(
                number=1,
                text=(
                    "Who may apply\n\n"
                    "Applicants hold a secondary\ncertificate.\n\n"
                    "Fees are listed below.\n\n"
                    "§ 3 Payment\nPayment is due in August.\n"
                    "ART. 4 REFUNDS\nNo refunds after enrolment."
                ),
                has_text=True,
            )
        ],
        total_pages=1,
        status="readable",
    )
    blocks = [(b.kind, b.text, b.section_path) for b in build_pdf_ir(doc).blocks]
    assert blocks == [
        ("heading", "p. 1", ("p. 1",)),
        ("heading", "Who may apply", ("p. 1", "Who may apply")),
        ("paragraph", "Applicants hold a secondary certificate.", ("p. 1", "Who may apply")),
        ("paragraph", "Fees are listed below.", ("p. 1", "Who may apply")),
        ("heading", "§ 3 Payment", ("p. 1", "§ 3 Payment")),
        ("paragraph", "Payment is due in August.", ("p. 1", "§ 3 Payment")),
        ("heading", "ART. 4 REFUNDS", ("p. 1", "ART. 4 REFUNDS")),
        ("paragraph", "No refunds after enrolment.", ("p. 1", "ART. 4 REFUNDS")),
    ]


def test_a_paragraph_before_any_heading_carries_only_the_page() -> None:
    doc = pdf_document.PdfDocument(
        url=URL,
        title="t",
        pages=[pdf_document.PdfPage(number=7, text="plain text line", has_text=True)],
        total_pages=7,
        status="readable",
    )
    (page, para) = build_pdf_ir(doc).blocks
    assert page.text == "p. 7"
    assert (para.kind, para.section_path) == ("paragraph", ("p. 7",))


def test_pdf_text_matches_pdf_to_text_after_whitespace_normalisation(
    three_page_pdf: bytes,
) -> None:
    for body in (three_page_pdf, FIXTURE.read_bytes()):
        doc = read_pdf(body, URL)
        assert normalize_text(pdf_text(doc)) == normalize_text(pdf_to_text(body, max_pages=40))


def test_the_module_does_no_io_and_never_imports_the_fetcher() -> None:
    source = Path(pdf_document.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(name.startswith("app.adapters.fetching") for name in imported)
    assert not imported & {"httpx", "requests", "socket", "urllib.request", "aiohttp", "os"}
    assert "open(" not in source


def test_unreadable_metadata_falls_back_to_the_first_line(
    monkeypatch: pytest.MonkeyPatch, three_page_pdf: bytes
) -> None:
    from pypdf import PdfReader

    def broken(self: PdfReader) -> None:
        raise ValueError("bad /Info")

    monkeypatch.setattr(PdfReader, "metadata", property(broken))
    assert read_pdf(three_page_pdf, URL).title == "Admissions and fees regulation"


def test_an_overlong_capitalised_line_is_not_a_heading() -> None:
    line = "A" * 130
    doc = pdf_document.PdfDocument(
        url=URL,
        title="t",
        pages=[pdf_document.PdfPage(number=1, text=line, has_text=True)],
        total_pages=1,
        status="readable",
    )
    assert [b.kind for b in build_pdf_ir(doc).blocks] == ["heading", "paragraph"]

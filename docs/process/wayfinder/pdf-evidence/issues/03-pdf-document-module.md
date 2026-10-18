# `app/adapters/pdf_document.py`: per-page text with provenance, a title, and a DocumentIR the readers already consume

Type: task
Status: open
Blocked by: —
Map: ../map.md · AFK task, starts now. New module only; no flag (a library with no caller changes no behaviour);
disjoint from every file a worker holds.

## Goal

Turn `FetchResult.content` of a PDF into something the existing stack can classify, read and verify **with a page
number**. Today `extraction.pdf_to_text(data, max_pages=40)` returns one string: no page boundaries, no title, no
headings, so `classify_page(url, html="", text)` reads `unknown` and `page_type_admits` rejects every claim; the funding
stage does not call it at all. The evaluation side already has the per-page shape (`expert/controller.py` L858–890)
— port it into production as a pure module.

## Shape (proposal; the worker may rename, not widen)

```python
@dataclass(frozen=True, slots=True)
class PdfPage:
    number: int            # 1-based
    text: str              # pypdf extract_text(), whitespace-normalised like readable_text
    has_text: bool

@dataclass(slots=True)
class PdfDocument:
    url: str
    title: str             # metadata /Title, else the first page's first non-empty line ≤ 120 chars, else the file name
    pages: list[PdfPage]   # first MAX_PDF_PAGES (40) only
    total_pages: int
    truncated: bool        # total_pages > MAX_PDF_PAGES
    parse_ms: int
    status: Literal["readable", "no_text_layer", "malformed", "too_slow"]

def read_pdf(content: bytes, url: str, *, max_pages: int = 40, time_cap_s: float = 3.0) -> PdfDocument
def pdf_text(doc: PdfDocument) -> str                    # pages joined with "\n\n", for ClaimBuilder(page_text=…)
def build_pdf_ir(doc: PdfDocument) -> DocumentIR         # one "heading" block per page ("p. N"), paragraphs per blank-line
                                                         # run, section_path=("p. N", <ALL-CAPS or numbered line above>)
def page_of(doc: PdfDocument, excerpt: str) -> int | None  # the single page whose text contains the normalised excerpt
```

- `read_pdf` runs pypdf on a worker thread (`asyncio.to_thread` at the call site is the caller's job; the function is
  sync and never raises); malformed → `status="malformed"`, empty text on every page → `"no_text_layer"`; over
  `time_cap_s` → stop at the pages done, `status="too_slow"` if none.
- `build_pdf_ir` emits `EvidenceBlock(kind="heading", text="p. N")` then `paragraph` blocks; a line that is ALL CAPS,
  numbered (`1.`, `§ 3`, `Art. 4`, `2.1`) or ≤ 80 chars followed by a blank line becomes a heading of its own and
  enters `section_path`. No table reconstruction here (ticket 08 decides).
- `extraction.pdf_to_text` stays as it is (callers unchanged); the module uses the same `max_pages`.
- Claims built from a PDF get `relevant_section = f"p. {page_of(doc, excerpt)}"` — the wiring is ticket 04's.

## Files

New: `backend/app/adapters/pdf_document.py`, `backend/tests/test_pdf_document.py`. Fixtures: the bundled
`backend/app/corpus/pages/u-groningen/fees.pdf` (text, 1 page), two synthetic PDFs built in the test with pypdf's
writer (a 3-page text PDF with a numbered heading and a fee line on page 2; an image-only page), a truncated byte
string (malformed), a 45-page PDF for the cap. No network, no fixtures copied from any university.

## Done when

- Tests: page numbers 1-based and stable across two reads; `page_of` returns the page for a quote that occurs once
  and `None` when it occurs on two pages or on none; `no_text_layer` for the image-only PDF; `malformed` never
  raises; 45 pages → 40 read, `truncated=True`; the IR's `section_path` carries `("p. 2", "2. TUITION FEES")` for the
  synthetic file; `pdf_text` equals `pdf_to_text` on the same bytes after whitespace normalisation (so the verifier
  sees the same text either way).
- Gates green (`ruff`, `mypy`, coverage ≥ 92 %); `seed_demo.py` order unchanged (nothing calls the module yet).
- HANDOFF §8 line: module path and the four public names.
- Offline guard: the module imports nothing from `app.adapters.fetching` and performs no I/O.

## Evidence

`expert/controller.py` L858–890 and `expert/models.py` L523–530 (per-page extraction and per-page quote check,
evaluation side); `test_expert_pdf_view.py` L76–205 (behaviours already specified there); `document_ir.py`
`EvidenceBlock` / `DocumentIR` (L43–86); `extraction.pdf_to_text` (L77–88).

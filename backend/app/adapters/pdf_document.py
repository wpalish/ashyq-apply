"""A PDF as pages with provenance, a title and a DocumentIR (PDF map, ticket 03).

``extraction.pdf_to_text`` returns one string: no page boundaries, no title,
no headings. A claim built from it can carry a verbatim quote but no page
number, and the classifier sees a page with neither title nor headings. This
module keeps what the PDF itself states:

* each page's text, 1-based, with whether it has a text layer at all;
* a title (metadata ``/Title``, else the first page's first line, else the
  file name);
* a ``DocumentIR`` with one ``"p. N"`` heading per page, so every block's
  ``section_path`` starts with the page it came from.

It is a library: it performs no I/O, imports nothing from the fetching layer
and changes no pipeline behaviour until a stage calls it. ``read_pdf`` is
synchronous and never raises; a caller on the event loop runs it with
``asyncio.to_thread``. Scanned PDFs are not OCR'd: a document whose every
page lacks a text layer is ``no_text_layer``.
"""

from __future__ import annotations

import io
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal
from urllib.parse import unquote, urlparse

from app.adapters.document_ir import BlockKind, DocumentIR, EvidenceBlock
from app.domain.claim_verifier import normalize_text

if TYPE_CHECKING:
    from pypdf import PdfReader

#: The same page cap as ``extraction.pdf_to_text(max_pages=40)``.
MAX_PDF_PAGES = 40
#: Wall-clock cap on parsing one PDF. It is checked between pages: one page's
#: extraction is never interrupted, so a single pathological page can overrun.
PDF_TIME_CAP_S = 3.0
TITLE_MAX_CHARS = 120
#: A line of at most this many characters standing alone before a blank line
#: is a heading.
SHORT_HEADING_CHARS = 80

PdfStatus = Literal["readable", "no_text_layer", "malformed", "too_slow"]

_WS = re.compile(r"[ \t ]+")
_BLANKS = re.compile(r"\n{3,}")
_NUMBERED = re.compile(
    r"^(?:\d{1,2}(?:\.\d{1,2})*\.\s+\S"  # "1. Fees", "2.1. Scope"
    r"|\d{1,2}(?:\.\d{1,2})+\s+\S"  # "2.1 Scope"
    r"|§\s*\d+"  # "§ 3"
    r"|Art\.\s*\d+)"  # "Art. 4"
)
_SENTENCE_END = (".", ",", ";")

# Patched by tests; production always reads the monotonic clock.
_clock = time.monotonic


@dataclass(frozen=True, slots=True)
class PdfPage:
    number: int
    """1-based, as a reader of the PDF would cite it."""
    text: str
    """``extract_text()``, whitespace runs collapsed, blank-line runs kept as one."""
    has_text: bool


@dataclass(slots=True)
class PdfDocument:
    url: str
    title: str
    pages: list[PdfPage] = field(default_factory=list)
    """The pages read: at most ``max_pages``, fewer when the time cap stopped the parse."""
    total_pages: int = 0
    truncated: bool = False
    """True when fewer pages were read than the document has (page or time cap)."""
    parse_ms: int = 0
    status: PdfStatus = "malformed"


def open_reader(content: bytes) -> PdfReader | None:
    """A ``PdfReader`` ready to read, or ``None`` for a PDF that needs a password.

    Official guides are often encrypted with an empty user password: any viewer
    opens them without asking, but the text is AES- or RC4-encrypted and pypdf
    needs ``cryptography`` to decrypt AES. Such a PDF is unlocked with ``""``.
    A PDF whose user password is not empty is refused, not guessed at.
    Malformed bytes raise; every caller already turns that into a fixed result.
    """
    from pypdf import PasswordType, PdfReader

    reader = PdfReader(io.BytesIO(content))
    if reader.is_encrypted and reader.decrypt("") == PasswordType.NOT_DECRYPTED:
        return None
    return reader


def _normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_WS.sub(" ", line).strip() for line in text.split("\n")]
    return _BLANKS.sub("\n\n", "\n".join(lines)).strip()


def _file_name(url: str) -> str:
    name = unquote(urlparse(url).path.rstrip("/").rsplit("/", 1)[-1])
    return name or url


def _title(metadata_title: str, pages: list[PdfPage], url: str) -> str:
    title = _WS.sub(" ", metadata_title).strip()
    if title:
        return title[:TITLE_MAX_CHARS]
    if pages:
        for line in pages[0].text.split("\n"):
            if line:
                if len(line) <= TITLE_MAX_CHARS:
                    return line
                break
    return _file_name(url)


def read_pdf(
    content: bytes,
    url: str,
    *,
    max_pages: int = MAX_PDF_PAGES,
    time_cap_s: float = PDF_TIME_CAP_S,
) -> PdfDocument:
    """Parse ``content`` page by page. Never raises; failure is a ``status``."""
    started = _clock()

    def elapsed_ms() -> int:
        return int((_clock() - started) * 1000)

    try:
        import pypdf  # noqa: F401
    except ImportError:  # pragma: no cover - pypdf is a hard requirement
        return PdfDocument(url=url, title=_file_name(url), status="malformed")

    metadata_title = ""
    pages: list[PdfPage] = []
    total = 0
    try:
        reader = open_reader(content)
        if reader is None:
            # Needs a password nobody gave us: nothing can be read from it.
            return PdfDocument(
                url=url, title=_file_name(url), parse_ms=elapsed_ms(), status="malformed"
            )
        total = len(reader.pages)
        try:
            meta = reader.metadata
            raw = meta.title if meta is not None else None
            metadata_title = raw if isinstance(raw, str) else ""
        except Exception:
            metadata_title = ""
        for index in range(min(total, max(max_pages, 0))):
            if _clock() - started > time_cap_s:
                break
            try:
                raw_text = reader.pages[index].extract_text() or ""
            except Exception:
                # One broken page does not lose the others; it reads as empty.
                raw_text = ""
            text = _normalise(raw_text)
            pages.append(PdfPage(number=index + 1, text=text, has_text=bool(text)))
    except Exception:
        # PDF bytes are untrusted: a fixed status, never the exception text.
        # Page failures are caught per page above, so nothing was read here.
        return PdfDocument(
            url=url,
            title=_file_name(url),
            total_pages=total,
            parse_ms=elapsed_ms(),
            status="malformed",
        )

    status: PdfStatus
    if not pages:
        status = "too_slow" if total else "malformed"
    elif any(page.has_text for page in pages):
        status = "readable"
    else:
        status = "no_text_layer"
    return PdfDocument(
        url=url,
        title=_title(metadata_title, pages, url),
        pages=pages,
        total_pages=total,
        truncated=len(pages) < total,
        parse_ms=elapsed_ms(),
        status=status,
    )


def pdf_text(doc: PdfDocument) -> str:
    """The pages joined by a blank line: the ``page_text`` a ClaimBuilder verifies against."""
    return "\n\n".join(page.text for page in doc.pages if page.text)


def _is_heading(line: str, *, alone_before_blank: bool) -> bool:
    if len(line) > TITLE_MAX_CHARS:
        return False
    letters = [c for c in line if c.isalpha()]
    if len(letters) >= 3 and all(c.isupper() for c in letters):
        return True
    if _NUMBERED.match(line):
        return True
    return (
        alone_before_blank
        and len(line) <= SHORT_HEADING_CHARS
        and not line.endswith(_SENTENCE_END)
        and any(c.isalpha() for c in line)
    )


def build_pdf_ir(doc: PdfDocument) -> DocumentIR:
    """One ``"p. N"`` heading per page, then its paragraphs and headings.

    A paragraph is a run of lines between blank lines. A line that is ALL
    CAPS, numbered (``1.``, ``2.1``, ``§ 3``, ``Art. 4``), or a short line
    alone in its run before a blank line is a heading of its own and becomes
    the second element of ``section_path`` for what follows on that page.
    Tables are not reconstructed (ticket 08).
    """
    ir = DocumentIR(url=doc.url, title=doc.title)

    def add(kind: BlockKind, text: str, path: tuple[str, ...]) -> None:
        ir.blocks.append(
            EvidenceBlock(id=f"b{len(ir.blocks)}", kind=kind, text=text, section_path=path)
        )

    for page in doc.pages:
        page_label = f"p. {page.number}"
        add("heading", page_label, (page_label,))
        heading: str | None = None
        runs = [run.split("\n") for run in page.text.split("\n\n") if run.strip()]
        for run_index, run in enumerate(runs):
            alone = len(run) == 1 and run_index < len(runs) - 1
            buffer: list[str] = []
            for line in [*run, None]:
                is_heading = line is not None and _is_heading(line, alone_before_blank=alone)
                if (line is None or is_heading) and buffer:
                    path = (page_label, heading) if heading else (page_label,)
                    add("paragraph", " ".join(buffer), path)
                    buffer = []
                if line is None:
                    break
                if is_heading:
                    heading = line
                    add("heading", line, (page_label, line))
                elif line:
                    buffer.append(line)
    return ir


def page_of(doc: PdfDocument, excerpt: str) -> int | None:
    """The one page whose text contains ``excerpt`` (both sides normalised).

    ``None`` when the excerpt is empty, on no page, or on more than one page:
    a page number is provenance only when it is unambiguous.
    """
    needle = normalize_text(excerpt)
    if not needle:
        return None
    hits = [page.number for page in doc.pages if needle in normalize_text(page.text)]
    return hits[0] if len(hits) == 1 else None

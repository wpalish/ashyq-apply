"""PD-1: a fetched PDF read by the stages as pages, by its own title (PDF map, ticket 04).

Without this module a stage that meets a PDF either parses its bytes as HTML
(the funding stage) or extracts one string and classifies it with neither
title nor headings, so the page is ``unknown`` and the verifier admits
nothing from it. Behind ``PDF_EVIDENCE_READERS`` a stage asks ``open_pdf``
for the PDF's pages (``pdf_document``) and gets:

* ``text`` — the pages joined with a gap no excerpt window crosses, the
  ``page_text`` the readers and the verifier see;
* ``html`` — the same words as a minimal HTML page whose ``<title>`` is the
  PDF's title and whose ``<h2>`` are the PDF's own headings, so the existing
  classifier signals and the HTML readers fire on what the PDF states; no
  new classifier word is added;
* ``claim_builder`` — a ``ClaimBuilder`` that stamps every claim whose
  excerpt sits on one page with ``relevant_section = "p. N"`` and scopes it
  by that page's words (a 40-page prospectus states many degrees and
  populations; a page that names one scopes its own claims).

The readers themselves are the stages' existing deterministic ones. This
module imports no network module and performs no I/O; parsing is the same
synchronous work ``extraction.pdf_to_text`` did before it.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from html import escape
from typing import Any, Protocol, TypeVar

from app.adapters.base import PageOutcome
from app.adapters.extraction import EXCERPT_RADIUS, ClaimBuilder
from app.adapters.page_classifier import PageClassification, classify_page
from app.adapters.pdf_document import PdfDocument, build_pdf_ir, page_of, read_pdf
from app.adapters.scope_reader import read_scope
from app.domain.claim_scope import SCOPE_DIMENSIONS, ClaimScope
from app.domain.enums import ClaimType
from app.schemas.claim import Claim

#: PD-1. Off: every stage keeps its pre-PD-1 PDF path, byte for byte.
PDF_EVIDENCE_READERS = False

#: First-page headings that join the title as the classifier's "head".
HEAD_HEADINGS = 3


class _Fetched(Protocol):
    """The part of a ``FetchResult`` read here (no import of the fetching layer)."""

    url: str
    final_url: str
    content: bytes

    @property
    def is_pdf(self) -> bool: ...


_FetchedT = TypeVar("_FetchedT", bound=_Fetched)


@dataclass(frozen=True, slots=True)
class PdfRead:
    doc: PdfDocument
    text: str
    html: str

    @property
    def title(self) -> str:
        return self.doc.title


def pdf_html(doc: PdfDocument) -> str:
    """The PDF's words as an HTML page: its title, its headings, its paragraphs.

    Page labels (``"p. N"``) are not headings here: they are provenance, kept
    on the claim, never a section or an award name.
    """
    ir = build_pdf_ir(doc)
    title = escape(doc.title)
    parts = [f"<html><head><title>{title}</title></head><body><main><h1>{title}</h1>"]
    for block in ir.blocks:
        if block.kind == "heading":
            if len(block.section_path) == 1:
                continue  # the page label
            parts.append(f"<h2>{escape(block.text)}</h2>")
        else:
            parts.append(f"<p>{escape(block.text)}</p>")
    parts.append("</main></body></html>")
    return "".join(parts)


def open_pdf(res: _Fetched) -> PdfRead | None:
    """The PDF behind ``res`` read as pages, or None (flag off, or not a PDF)."""
    if not PDF_EVIDENCE_READERS or not res.is_pdf:
        return None
    doc = read_pdf(res.content, res.final_url or res.url)
    return PdfRead(doc=doc, text=paged_text(doc), html=pdf_html(doc))


#: Between two pages of ``paged_text``: wider than an excerpt window reaches,
#: so a reader's excerpt (``extraction.excerpt_around``) never spans a page
#: boundary and every claim can name the one page it was read on.
PAGE_GAP = "\n" * (2 * EXCERPT_RADIUS + 2)


def paged_text(doc: PdfDocument) -> str:
    """The pages in order, each read on its own by the stage's whole-text readers.

    The same words as ``pdf_text``; only the blank space between pages is
    wider. Whitespace is normalised by the verifier, so an excerpt checks
    against either.
    """
    return PAGE_GAP.join(page.text for page in doc.pages if page.text)


def classify_pdf(pdf: PdfRead, url: str) -> PageClassification:
    """The PDF classified by its own title and first headings, then its text."""
    return classify_page(url=url, html=pdf.html, text=pdf.text)


def pdf_page_outcome(pdf: PdfRead, url: str) -> PageOutcome | None:
    """The outcome of a PDF that cannot be read; None when it can."""
    status = pdf.doc.status
    if status == "readable":
        return None
    if status == "no_text_layer":
        return PageOutcome(url=url, category="fetch-failed", detail="PDF without a text layer")
    detail = "PDF unparseable" if status == "malformed" else "PDF parse exceeded its time cap"
    return PageOutcome(url=url, category="unreadable", detail=detail)


def pdf_read_detail(pdf: PdfRead) -> str:
    doc = pdf.doc
    return f"PDF, {len(doc.pages)} pages" + (" (truncated)" if doc.truncated else "")


class PdfClaimBuilder(ClaimBuilder):
    """A ``ClaimBuilder`` that knows which page of the PDF each excerpt is on."""

    def __init__(self, *, pdf: PdfDocument, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.pdf = pdf

    def add(
        self, claim_type: ClaimType, value: object, excerpt: str, **kwargs: Any
    ) -> Claim | None:
        number = page_of(self.pdf, excerpt)
        if number is None:
            return super().add(claim_type, value, excerpt, **kwargs)
        # The page is the provenance a reader of the PDF can check (ticket 07);
        # a reader's own section name for an HTML page does not locate it.
        kwargs["section"] = f"p. {number}"
        page = self.pdf.pages[number - 1]
        stage_scope = self.meta["scope"]
        self.meta["scope"] = page_scope(stage_scope, page.text, self.pdf.title)  # type: ignore[arg-type]
        try:
            return super().add(claim_type, value, excerpt, **kwargs)
        finally:
            self.meta["scope"] = stage_scope


def page_scope(stage_scope: ClaimScope | None, page_text: str, title: str) -> ClaimScope:
    """The stage's scope with every dimension the page itself states replaced."""
    own = read_scope(page_text, title=title)
    stated = {name: getattr(own, name) for name in SCOPE_DIMENSIONS if getattr(own, name)}
    return replace(stage_scope or ClaimScope(), **stated)


def read_pages(
    pdf: PdfRead | None,
    text: str,
    reader: Callable[[str], list[Claim]],
    *,
    programmes: Sequence[str] = (),
) -> list[Claim]:
    """``reader`` over each page of the PDF in turn, or over ``text`` for any other page.

    A reader that looks for the first label on a page must not take a
    cover page's "Tuition and fees 2026/27" as the label of a figure on
    page 2; each page is read as the page it is. With ``programmes`` (the
    programme asked for), a page's tuition figures pass ``programme_rows``.
    """
    if pdf is None:
        return reader(text)
    claims: list[Claim] = []
    for page in pdf.doc.pages:
        if page.text:
            claims += programme_rows(page.text, reader(page.text), programmes)
    return claims


#: A fee-schedule row that names a programme: a degree word and a capitalised name.
_PROGRAMME_ROW = re.compile(
    r"\b(?:MSc|BSc|MA|BA|MBA|LLM|MEng|BEng|MPhil|PhD|Master(?:'s)? of|Bachelor(?:'s)? of)"
    r"\s+[A-Z]"
)
_AMOUNT = re.compile(r"\d[\d,.' ]*\d|\d")


def _amounts(line: str) -> set[int]:
    found = set()
    for raw in _AMOUNT.findall(line):
        digits = re.sub(r"[,.' ](?=\d{3}\b)", "", raw.strip())
        try:
            found.add(int(float(digits.replace(",", "").replace("'", "").replace(" ", ""))))
        except ValueError:
            continue
    return found


def programme_rows(page_text: str, claims: list[Claim], programmes: Sequence[str]) -> list[Claim]:
    """A page of several programmes' fee rows lends no row to another programme.

    When two or more lines of the page name a programme beside a figure, a
    tuition claim is kept only when its amount is on a line that names the
    programme asked for; with no such line every tuition claim of the page
    is dropped (ticket 08's rule in its simplest form). A page with at most
    one programme row is left to the readers.
    """
    if not programmes:
        return claims
    rows = [
        line
        for line in page_text.split("\n")
        if _PROGRAMME_ROW.search(line) and any(c.isdigit() for c in line)
    ]
    if len(rows) < 2:
        return claims
    wanted = [p.casefold() for p in programmes if p]
    own = set().union(*(_amounts(row) for row in rows if any(p in row.casefold() for p in wanted)))
    return [
        claim
        for claim in claims
        if claim.claim_type is not ClaimType.TUITION
        or (
            isinstance(claim.normalized_value, dict)
            and int(claim.normalized_value.get("amount") or -1) in own
        )
    ]


def claim_builder(pdf: PdfRead | None) -> Callable[..., ClaimBuilder]:
    """The builder a stage constructs: page-aware for a PDF, the plain one otherwise."""
    if pdf is None:
        return ClaimBuilder
    doc = pdf.doc

    def build(**kwargs: Any) -> ClaimBuilder:
        return PdfClaimBuilder(pdf=doc, **kwargs)

    return build


def stamp_pages(claims: Sequence[Claim], docs: dict[str, PdfDocument]) -> None:
    """Give every claim read from one of ``docs`` (by URL) its page, when unambiguous."""
    for claim in claims:
        doc = docs.get(claim.source_url)
        if doc is None or claim.relevant_section:
            continue
        number = page_of(doc, claim.original_text_excerpt)
        if number is not None:
            claim.relevant_section = f"p. {number}"


def read_as_html(res: _FetchedT, docs: dict[str, PdfDocument]) -> _FetchedT:
    """The funding stage's hook: a PDF becomes its HTML rendering, its pages kept in ``docs``.

    The stage reads ``res.text`` as HTML everywhere (classifier, award
    sections, award pages); before PD-1 that was the PDF's bytes decoded.
    """
    pdf = open_pdf(res)
    if pdf is None:
        return res
    docs[res.url] = pdf.doc
    if res.final_url:
        docs[res.final_url] = pdf.doc
    return dataclasses.replace(res, text=pdf.html)  # type: ignore[type-var]

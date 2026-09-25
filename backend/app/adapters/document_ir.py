"""A page as structured evidence blocks, not one flat string (V2-30B).

Both reviews of 2026-09-25 found the same loss: ``readable_text`` flattens a
page before any extractor sees it, so "IELTS Academic | Overall | 6.5" in a
table reaches the regexes as three unrelated words on three lines. This module
keeps the relationships a page states in markup:

* a heading and the blocks under it (``section_path``);
* a table cell and its row and column headers, with ``rowspan``/``colspan``
  expanded and explicit ``headers=""`` references honoured first;
* a ``<dt>`` and its ``<dd>``;
* a link and the section it sits in.

Every block keeps its text exactly as the page renders it (whitespace
collapsed, nothing else), so a claim built from a block can still be checked
verbatim against the page. Nothing here decides what a value means; that is
the extractors' job, and they may only use what a block records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urljoin

from bs4 import Tag

from app.adapters.html_parse import parse_html

BlockKind = Literal["heading", "paragraph", "list_item", "key_value", "table_cell"]

_WS = re.compile(r"\s+")
_HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
_DROP = ("script", "style", "noscript", "svg", "template", "form")


def _text(tag: Tag) -> str:
    return _WS.sub(" ", tag.get_text(" ", strip=True)).strip()


@dataclass(frozen=True, slots=True)
class EvidenceBlock:
    """One piece of a page with the context the markup gave it."""

    id: str
    kind: BlockKind
    #: The block's own text as rendered, whitespace collapsed.
    text: str
    #: Headings above the block, outermost first.
    section_path: tuple[str, ...] = ()
    #: For a table cell: its table's index on the page, row and column.
    table_id: int | None = None
    row: int | None = None
    col: int | None = None
    row_headers: tuple[str, ...] = ()
    column_headers: tuple[str, ...] = ()
    caption: str = ""
    #: For a key-value block: the label (``<dt>``) the value (``text``) answers.
    label: str = ""


@dataclass(frozen=True, slots=True)
class EvidenceLink:
    url: str
    text: str
    section_path: tuple[str, ...] = ()


@dataclass(slots=True)
class DocumentIR:
    url: str
    title: str = ""
    blocks: list[EvidenceBlock] = field(default_factory=list)
    links: list[EvidenceLink] = field(default_factory=list)

    def table_cells(self, table_id: int) -> list[EvidenceBlock]:
        return [b for b in self.blocks if b.kind == "table_cell" and b.table_id == table_id]


@dataclass(slots=True)
class _Cell:
    tag: Tag
    text: str
    is_header: bool
    origin: tuple[int, int]


def _grid(table: Tag) -> list[list[_Cell | None]]:
    """The table as a rectangular grid, spans expanded to every slot they cover."""
    rows = [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]
    grid: list[list[_Cell | None]] = []
    for r, tr in enumerate(rows):
        while len(grid) <= r:
            grid.append([])
        c = 0
        for cell in tr.find_all(["td", "th"], recursive=False):
            while c < len(grid[r]) and grid[r][c] is not None:
                c += 1
            rowspan = _span(cell.get("rowspan"))
            colspan = _span(cell.get("colspan"))
            entry = _Cell(cell, _text(cell), cell.name == "th", (r, c))
            for dr in range(rowspan):
                while len(grid) <= r + dr:
                    grid.append([])
                target = grid[r + dr]
                while len(target) < c + colspan:
                    target.append(None)
                for dc in range(colspan):
                    target[c + dc] = entry
            c += colspan
    width = max((len(row) for row in grid), default=0)
    for row in grid:
        row.extend([None] * (width - len(row)))
    return grid


def _span(value: object) -> int:
    try:
        return max(1, min(int(str(value)), 50))
    except (TypeError, ValueError):
        return 1


def _header_rows(grid: list[list[_Cell | None]]) -> int:
    """Leading rows made only of header cells (a ``<thead>`` or ``<th>`` row)."""
    count = 0
    for row in grid:
        cells = [c for c in row if c is not None]
        if cells and all(c.is_header or c.tag.find_parent("thead") for c in cells):
            count += 1
        else:
            break
    return count


def _unique(values: list[str]) -> tuple[str, ...]:
    out: list[str] = []
    for v in values:
        if v and v not in out:
            out.append(v)
    return tuple(out)


def _table_blocks(
    table: Tag, table_id: int, section: tuple[str, ...], start: int
) -> list[EvidenceBlock]:
    caption_tag = table.find("caption")
    caption = _text(caption_tag) if caption_tag else ""
    grid = _grid(table)
    head = _header_rows(grid)
    by_id = {th["id"]: _text(th) for th in table.find_all(["th", "td"]) if th.get("id")}
    blocks: list[EvidenceBlock] = []
    seen: set[tuple[int, int]] = set()
    for r, row in enumerate(grid):
        if r < head:
            continue
        for c, cell in enumerate(row):
            if cell is None or cell.origin in seen or cell.origin != (r, c):
                continue
            seen.add(cell.origin)
            if cell.is_header and cell.tag.get("scope") != "col":
                # A row header is context, not a value.
                continue
            explicit = [by_id[h] for h in str(cell.tag.get("headers", "")).split() if h in by_id]
            if explicit:
                column_headers: tuple[str, ...] = tuple(explicit)
                row_headers: tuple[str, ...] = ()
            else:
                column_headers = _unique(
                    [
                        grid[h][c].text  # type: ignore[union-attr]
                        for h in range(head)
                        if grid[h][c] is not None
                    ]
                )
                row_headers = _unique(
                    [
                        x.text
                        for x in row[:c]
                        if x is not None and (x.is_header or x.tag.get("scope") == "row")
                    ]
                )
                if not row_headers and c > 0 and row[0] is not None and row[0] is not cell:
                    # The common unmarked layout: the first column names the row.
                    row_headers = (row[0].text,)
            if not cell.text:
                continue
            blocks.append(
                EvidenceBlock(
                    id=f"b{start + len(blocks)}",
                    kind="table_cell",
                    text=cell.text,
                    section_path=section,
                    table_id=table_id,
                    row=r,
                    col=c,
                    row_headers=row_headers,
                    column_headers=column_headers,
                    caption=caption,
                )
            )
    return blocks


def build_document_ir(html: str, url: str) -> DocumentIR:
    """Parse ``html`` into ordered evidence blocks and links. Never raises."""
    soup = parse_html(html)
    title_tag = soup.find("title")
    doc = DocumentIR(url=url, title=_text(title_tag) if title_tag else "")
    for tag in soup(_DROP):
        tag.decompose()
    body = soup.body or soup
    section: list[tuple[int, str]] = []
    tables = 0

    def path() -> tuple[str, ...]:
        return tuple(text for _level, text in section)

    def add(kind: BlockKind, text: str, **extra: object) -> None:
        if text:
            doc.blocks.append(
                EvidenceBlock(
                    id=f"b{len(doc.blocks)}",
                    kind=kind,
                    text=text,
                    section_path=path(),
                    **extra,  # type: ignore[arg-type]
                )
            )

    for node in body.find_all(True):
        if not isinstance(node, Tag):
            continue
        name = node.name
        if name in _HEADINGS:
            level = int(name[1])
            while section and section[-1][0] >= level:
                section.pop()
            text = _text(node)
            if text:
                section.append((level, text))
                add("heading", text)
        elif name == "table" and not node.find_parent("table"):
            doc.blocks.extend(_table_blocks(node, tables, path(), len(doc.blocks)))
            tables += 1
        elif name == "dt":
            dd = node.find_next_sibling("dd")
            if dd is not None:
                add("key_value", _text(dd), label=_text(node))
        elif name == "li" and not node.find_parent("table") and not node.find(["ul", "ol"]):
            add("list_item", _text(node))
        elif name == "p" and not node.find_parent(["table", "li", "dd"]):
            add("paragraph", _text(node))
        elif name == "a" and node.get("href"):
            href = str(node["href"]).strip()
            if href and not href.startswith(("#", "mailto:", "tel:", "javascript:")):
                doc.links.append(EvidenceLink(urljoin(url, href), _text(node), path()))
    return doc

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
from dataclasses import dataclass, field, replace
from typing import Literal
from urllib.parse import urljoin

from bs4 import Tag

from app.adapters.html_parse import parse_html

BlockKind = Literal["heading", "paragraph", "list_item", "key_value", "table_cell"]

_WS = re.compile(r"\s+")
_HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
_DROP = ("script", "style", "noscript", "svg", "template", "form")
_YEAR_LABEL = re.compile(
    r"Academic\s+year\s*:?\s*20\d{2}(?:\s*[/–—-]\s*(?:20\d{2}|\d{2}))?", re.IGNORECASE
)
_YEAR_HEADER = re.compile(r"(?:Academic\s+)?Year", re.IGNORECASE)


def _text(tag: Tag) -> str:
    return _WS.sub(" ", tag.get_text(" ", strip=True)).strip()


def _dom_path(node: Tag) -> str:
    """An exact tag path in the parsed original source, independent of block IDs."""
    parts: list[str] = []
    while isinstance(node, Tag) and node.name != "[document]":
        ordinal = 1 + sum(
            isinstance(sibling, Tag) and sibling.name == node.name
            for sibling in node.previous_siblings
        )
        parts.append(f"{node.name}[{ordinal}]")
        node = node.parent  # type: ignore[assignment]
    return "/" + "/".join(reversed(parts))


def _dom_paths(root: Tag) -> dict[int, str]:
    """Assign original paths in one traversal, without rescanning prior siblings."""
    paths = {id(root): ""}
    for parent in (root, *root.find_all(True)):
        counts: dict[str, int] = {}
        for child in parent.children:
            if not isinstance(child, Tag):
                continue
            counts[child.name] = counts.get(child.name, 0) + 1
            paths[id(child)] = f"{paths[id(parent)]}/{child.name}[{counts[child.name]}]"
    return paths


def _semantic_container_path(node: Tag, dom_paths: dict[int, str]) -> str:
    for parent in (node, *node.parents):
        if isinstance(parent, Tag) and parent.name in {"main", "article", "section", "body"}:
            return dom_paths[id(parent)]
    return "/"


@dataclass(frozen=True, slots=True)
class SectionYearLabel:
    """Literal year label directly adjacent to one content heading."""

    text: str
    dom_path: str
    heading_dom_path: str
    section_path: tuple[str, ...] = ()
    container_dom_path: str = ""


@dataclass(frozen=True, slots=True)
class RowYearCell:
    """A Year column cell, including blanks and ambiguous merged cells."""

    text: str
    dom_path: str
    table_id: int
    row: int
    col: int
    rowspan: int
    colspan: int
    column_headers: tuple[str, ...]
    block_id: str | None = None
    source_kind: Literal["value", "row_header"] = "value"
    source_tag: str = "td"
    source_scope: str = ""
    header_origin: Literal["positional", "explicit"] = "positional"
    header_dom_paths: tuple[str, ...] = ()
    blocked_reason: str | None = None


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
    #: Dedicated year provenance; never included in programme/applicant scope text.
    section_year_labels: tuple[SectionYearLabel, ...] = ()
    row_year_cells: tuple[RowYearCell, ...] = ()
    semantic_container_dom_path: str = ""


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


def _header_tokens(value: object) -> tuple[str, ...]:
    # BeautifulSoup represents headers as AttributeValueList, not always a string.
    if isinstance(value, str):
        return tuple(value.split())
    if isinstance(value, list | tuple) and all(isinstance(part, str) for part in value):
        return tuple(token for part in value for token in part.split())
    return ()


def _year_columns(
    grid: list[list[_Cell | None]],
    head: int,
    table_id: int,
    dom_paths: dict[int, str],
    original_visibility: dict[int, bool],
    original_texts: dict[int, str],
) -> dict[int, tuple[RowYearCell, ...]]:
    """Record exact Year provenance; an explicit headers attribute is authoritative."""
    result: dict[int, tuple[RowYearCell, ...]] = {}
    origins = {cell.origin: cell for row in grid for cell in row if cell is not None}
    by_id: dict[str, list[_Cell]] = {}
    for origin_cell in origins.values():
        if origin_cell.tag.get("id"):
            by_id.setdefault(str(origin_cell.tag["id"]), []).append(origin_cell)
    for r, row in enumerate(grid):
        if r < head:
            continue
        refs: list[RowYearCell] = []
        seen: set[tuple[int, int]] = set()
        for c, cell in enumerate(row):
            if cell is None or cell.origin in seen:
                continue
            seen.add(cell.origin)
            positional: dict[tuple[int, int], _Cell] = {}
            for h in range(head):
                header = grid[h][c]
                if header is not None:
                    positional[header.origin] = header
            positional_year = any(
                _YEAR_HEADER.fullmatch(original_texts[id(header.tag)])
                for header in positional.values()
            )
            explicit = cell.tag.has_attr("headers")
            blocked: str | None = None
            if explicit:
                tokens = _header_tokens(cell.tag.get("headers"))
                header_cells = [
                    by_id[token][0] for token in tokens if len(by_id.get(token, [])) == 1
                ]
                if not tokens:
                    blocked = "empty_explicit_headers"
                elif len(set(tokens)) != len(tokens):
                    blocked = "duplicate_header_reference"
                elif len(header_cells) != len(tokens):
                    blocked = "unresolved_or_duplicate_header_id"
                elif not any(
                    _YEAR_HEADER.fullmatch(original_texts[id(header.tag)])
                    for header in header_cells
                ):
                    blocked = "explicit_headers_are_not_year"
                # Invalid explicit references must never fall back to a positional Year.
                if (
                    blocked
                    and not positional_year
                    and not any(
                        _YEAR_HEADER.fullmatch(original_texts[id(header.tag)])
                        for header in header_cells
                    )
                ):
                    continue
            else:
                header_cells = list(positional.values())
                if not positional_year:
                    continue
            if blocked is None and any(
                not original_visibility[id(header.tag)] for header in header_cells
            ):
                blocked = "non_content_year_header"
            if blocked is None and not original_visibility[id(cell.tag)]:
                blocked = "non_content_year_cell"
            scope = str(cell.tag.get("scope", "")).casefold()
            refs.append(
                RowYearCell(
                    text=original_texts[id(cell.tag)],
                    dom_path=dom_paths[id(cell.tag)],
                    table_id=table_id,
                    row=cell.origin[0],
                    col=cell.origin[1],
                    rowspan=_span(cell.tag.get("rowspan")),
                    colspan=_span(cell.tag.get("colspan")),
                    column_headers=_unique(
                        [original_texts[id(header.tag)] for header in header_cells]
                    ),
                    source_kind="row_header" if cell.is_header and scope != "col" else "value",
                    source_tag=cell.tag.name,
                    source_scope=scope,
                    header_origin="explicit" if explicit else "positional",
                    header_dom_paths=tuple(dom_paths[id(header.tag)] for header in header_cells),
                    blocked_reason=blocked,
                )
            )
        result[r] = tuple(refs)
    return result


def _table_blocks(
    table: Tag,
    table_id: int,
    section: tuple[str, ...],
    start: int,
    *,
    section_year_labels: tuple[SectionYearLabel, ...] = (),
    dom_paths: dict[int, str] | None = None,
    original_visibility: dict[int, bool] | None = None,
    original_texts: dict[int, str] | None = None,
    semantic_container_dom_path: str = "",
) -> list[EvidenceBlock]:
    caption_tag = table.find("caption")
    caption = _text(caption_tag) if caption_tag else ""
    grid = _grid(table)
    head = _header_rows(grid)
    cell_paths = (
        dom_paths
        if dom_paths is not None
        else {id(cell.tag): _dom_path(cell.tag) for row in grid for cell in row if cell is not None}
    )
    visibility = (
        original_visibility
        if original_visibility is not None
        else {
            id(cell.tag): _year_content_visible(cell.tag)
            for row in grid
            for cell in row
            if cell is not None
        }
    )
    texts = (
        original_texts
        if original_texts is not None
        else {id(cell.tag): cell.text for row in grid for cell in row if cell is not None}
    )
    year_columns = _year_columns(grid, head, table_id, cell_paths, visibility, texts)
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
                    section_year_labels=section_year_labels,
                    row_year_cells=year_columns.get(r, ()),
                    semantic_container_dom_path=semantic_container_dom_path,
                )
            )
    cell_ids = {(block.row, block.col): block.id for block in blocks}
    return [
        replace(
            block,
            row_year_cells=tuple(
                replace(cell, block_id=cell_ids.get((cell.row, cell.col)))
                for cell in block.row_year_cells
            ),
        )
        for block in blocks
    ]


#: Part of plan rule DOC-2 (documents/web_documents.py): a screen-reader label
#: of a form picker is not a heading for the evidence after it.
FORM_LABEL_HEADINGS = False


def _form_only_container(node: Tag) -> bool:
    if not node.find("form"):
        return False
    return not any(
        text.strip()
        and not text.find_parent((*_HEADINGS, "form", "button", "script", "style", "svg"))
        for text in node.find_all(string=True)
    )


def _non_content_year_location(node: Tag) -> bool:
    for parent in (node, *node.parents):
        if not isinstance(parent, Tag):
            continue
        style = str(parent.get("style", ""))
        classes = set(parent.get("class", []))
        if (
            parent.name in {"nav", "aside", "footer", "header", "form"}
            or str(parent.get("role", "")).casefold() in {"navigation", "complementary", "banner"}
            or parent.has_attr("hidden")
            or str(parent.get("aria-hidden", "")).casefold() == "true"
            or classes & {"u-visually--hidden", "visually-hidden", "sr-only"}
            or re.search(
                r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden)\s*(?:!important)?\s*(?:;|$)",
                style,
                re.IGNORECASE,
            )
        ):
            return True
    return False


def _year_content_visible(node: Tag, *, label: bool = False) -> bool:
    forbidden = {"button", "input", "select", "textarea", "option", *_DROP}
    if label:
        forbidden.add("a")
    return not any(
        child.name in forbidden or _non_content_year_location(child)
        for child in (node, *node.find_all(True))
    )


def _heading_year_labels(heading: Tag, dom_paths: dict[int, str]) -> tuple[SectionYearLabel, ...]:
    if not _year_content_visible(heading, label=True):
        return ()
    labels: list[SectionYearLabel] = []
    for sibling in heading.next_siblings:
        if not isinstance(sibling, Tag):
            if str(sibling).strip():
                break
            continue
        text = _text(sibling)
        if sibling.name not in {"div", "p", "span"} or not _YEAR_LABEL.fullmatch(text):
            break
        if not _year_content_visible(sibling, label=True):
            break
        labels.append(
            SectionYearLabel(
                text=text,
                dom_path=dom_paths[id(sibling)],
                heading_dom_path=dom_paths[id(heading)],
                container_dom_path=_semantic_container_path(heading, dom_paths),
            )
        )
    return tuple(labels)


def build_document_ir(html: str, url: str) -> DocumentIR:
    """Parse ``html`` into ordered evidence blocks and links. Never raises."""
    soup = parse_html(html)
    title_tag = soup.find("title")
    doc = DocumentIR(url=url, title=_text(title_tag) if title_tag else "")
    # Capture form relationships before forms themselves are removed. Hidden
    # headings outside a form picker can be genuine accessible evidence headings.
    form_headings: set[int] = set()
    for heading in soup.find_all(_HEADINGS):
        classes = set(heading.get("class", []))
        hidden_form_label = bool(
            classes & {"u-visually--hidden", "visually-hidden", "sr-only"}
            and heading.parent
            and _form_only_container(heading.parent)
        )
        buttons = heading.find_all("button")
        control_only = bool(
            buttons
            and _text(heading) == " ".join(_text(button) for button in buttons)
            and all(
                button.has_attr("aria-expanded") and not button.get("aria-controls")
                for button in buttons
            )
            and any(_form_only_container(parent) for parent in list(heading.parents)[:3])
        )
        if hidden_form_label or control_only:
            form_headings.add(id(heading))
    # Compute coordinates before dropped source tags could change ancestry.
    dom_paths = _dom_paths(soup)
    heading_year_labels = {
        id(heading): _heading_year_labels(heading, dom_paths)
        for heading in soup.find_all(_HEADINGS)
    }
    # Visibility is bound before forms/scripts are dropped from the parsed tree.
    original_visibility = {
        id(cell): _year_content_visible(cell) for cell in soup.find_all(["td", "th"])
    }
    original_texts = {id(cell): _text(cell) for cell in soup.find_all(["td", "th"])}
    for tag in soup(_DROP):
        tag.decompose()
    body = soup.body or soup
    section: list[tuple[int, str, tuple[SectionYearLabel, ...]]] = []
    tables = 0

    def path() -> tuple[str, ...]:
        return tuple(text for _level, text, _labels in section)

    def year_labels(node: Tag) -> tuple[SectionYearLabel, ...]:
        if _non_content_year_location(node):
            return ()
        container = _semantic_container_path(node, dom_paths)
        return next(
            (
                labels
                for _level, _text, labels in reversed(section)
                if labels and all(label.container_dom_path == container for label in labels)
            ),
            (),
        )

    def add(kind: BlockKind, text: str, node: Tag, **extra: object) -> None:
        if text:
            doc.blocks.append(
                EvidenceBlock(
                    id=f"b{len(doc.blocks)}",
                    kind=kind,
                    text=text,
                    section_path=path(),
                    section_year_labels=year_labels(node),
                    semantic_container_dom_path=_semantic_container_path(node, dom_paths),
                    **extra,  # type: ignore[arg-type]
                )
            )

    for node in body.find_all(True):
        if not isinstance(node, Tag):
            continue
        name = node.name
        if name in _HEADINGS:
            # Screen-reader labels for a form are not headings for the
            # surrounding admissions evidence. In particular, a hidden picker
            # must not replace the campus/qualification heading of the next table.
            if FORM_LABEL_HEADINGS and id(node) in form_headings:
                continue
            level = int(name[1])
            while section and section[-1][0] >= level:
                section.pop()
            text = _text(node)
            if text:
                section.append((level, text, ()))
                labels = tuple(
                    replace(label, section_path=path()) for label in heading_year_labels[id(node)]
                )
                section[-1] = (level, text, labels)
                add("heading", text, node)
        elif name == "table" and not node.find_parent("table"):
            doc.blocks.extend(
                _table_blocks(
                    node,
                    tables,
                    path(),
                    len(doc.blocks),
                    section_year_labels=year_labels(node),
                    dom_paths=dom_paths,
                    original_visibility=original_visibility,
                    original_texts=original_texts,
                    semantic_container_dom_path=_semantic_container_path(node, dom_paths),
                )
            )
            tables += 1
        elif name == "dt":
            dd = node.find_next_sibling("dd")
            if dd is not None:
                add("key_value", _text(dd), node, label=_text(node))
        elif name == "li" and not node.find_parent("table") and not node.find(["ul", "ol"]):
            add("list_item", _text(node), node)
        elif name == "p" and not node.find_parent(["table", "li", "dd"]):
            add("paragraph", _text(node), node)
        elif name == "a" and node.get("href"):
            href = str(node["href"]).strip()
            if href and not href.startswith(("#", "mailto:", "tel:", "javascript:")):
                doc.links.append(EvidenceLink(urljoin(url, href), _text(node), path()))
    return doc

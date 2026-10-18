"""Published cost rows/options, retained without selecting an applicant's tariff."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.adapters.document_ir import DocumentIR, EvidenceBlock
from app.adapters.extraction import (
    _MONEY,
    ClaimBuilder,
    _year_key,
    extract_costs,
    fee_status_population,
    parse_money,
)
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import main_content
from app.adapters.scope_reader import read_scope
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimType
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim

_TUITION_HEADING = re.compile(
    r"^Annual tuition fees? for (?P<population>.+?)\s+(?:in\s+)?"
    r"(?P<start>20\d{2})\s*/\s*(?P<end>20\d{2}|\d{2})\s+academic year$",
    re.I,
)
_HOUSING_OPTION = re.compile(
    r"^(?P<option>(?:on|off)[ -]campus housing|residential halls(?: and colleges)?"
    r"|student accommodation)\s*:?[ \t]*",
    re.I,
)
_ANNUAL_PERIOD = re.compile(r"^\s*(?:per\s+(?:academic\s+)?year|annually)\b", re.I)
_NONANNUAL_PERIOD = re.compile(r"\b(?:per\s+(?:month|semester|term)|monthly)\b", re.I)


@dataclass
class StructuredCosts:
    claims: list[Claim] = field(default_factory=list)
    handled_types: set[ClaimType] = field(default_factory=set)


def _complete_quote(value: str, page_text: str | None) -> str:
    """Only the whole local proof, never a clipped or joined quotation."""
    if not value or not page_text or len(value) > MAX_EXCERPT_CHARS:
        return ""
    pattern = re.compile(r"\s+".join(re.escape(word) for word in value.split()))
    match = pattern.search(page_text)
    if match is None:
        return ""
    quote = match.group()
    return quote if len(quote) <= MAX_EXCERPT_CHARS else ""


def _money_value(value: str, *, annual: bool) -> dict[str, float | str] | None:
    """A point or an explicit same-currency range with its upper amount."""
    matches = list(_MONEY.finditer(value))
    if not 1 <= len(matches) <= 2:
        return None
    values = [parse_money(match.group()) for match in matches]
    if any(parsed is None or parsed[0] <= 0 for parsed in values):
        return None
    if annual and not _ANNUAL_PERIOD.match(value[matches[-1].end() :]):
        return None
    if len(matches) == 1:
        parsed = values[0]
        assert parsed is not None
        return {"amount": parsed[0], "currency": parsed[1]}
    if not re.fullmatch(r"\s*(?:to|[–-])\s*", value[matches[0].end() : matches[1].start()]):
        return None
    low, high = values
    assert low is not None and high is not None
    if low[1] != high[1] or low[0] > high[0]:
        return None
    return {
        "amount": high[0],
        "currency": high[1],
        "range_low": low[0],
        "range_high": high[0],
    }


def _row_quote(row: list[EvidenceBlock]) -> str:
    labels = tuple(dict.fromkeys(label for block in row for label in block.row_headers))
    body = " ".join(block.text for block in row)
    prefix = " ".join(labels)
    return body if not prefix or body.startswith(prefix) else f"{prefix} {body}"


def extract_structured_costs(
    document: DocumentIR, builder: ClaimBuilder, *, html: str
) -> StructuredCosts:
    """Read qualified annual fee rows and complete named housing options.

    Every returned claim is source evidence. No returned tariff/option is an
    applicant-specific arithmetic input: this seam has no confirmed fee
    status, faculty match or housing selection. The caller excludes handled
    categories from the legacy point-price fallback as well.
    """
    out = StructuredCosts()
    original_scope = builder.meta.get("scope")
    original_year = builder.meta.get("academic_year")
    rows: dict[tuple[int, int], list[EvidenceBlock]] = {}
    for block in document.blocks:
        if block.kind == "table_cell" and block.table_id is not None and block.row is not None:
            rows.setdefault((block.table_id, block.row), []).append(block)
    try:
        for row in rows.values():
            heading = next(
                (
                    part
                    for part in reversed(row[0].section_path)
                    if _TUITION_HEADING.fullmatch(part)
                ),
                "",
            )
            if not heading:
                continue
            out.handled_types.add(ClaimType.TUITION)
            match = _TUITION_HEADING.fullmatch(heading)
            assert match is not None
            labels = tuple(dict.fromkeys(label for block in row for label in block.row_headers))
            if len(labels) != 1:
                continue
            label = labels[0]
            proof = _row_quote(row)
            quote = _complete_quote(proof, builder.page_text)
            money = _money_value(proof, annual=False)
            if not quote or money is None or _NONANNUAL_PERIOD.search(proof):
                continue
            year = f"{match.group('start')}/{match.group('end')[-2:]}"
            population = match.group("population")
            group = re.sub(r"^for\s+", "", label, flags=re.I)
            faculty = (
                group
                if re.search(r"\b(?:faculties|faculty|schools?|colleges?)\b", group, re.I)
                else None
            )
            programme = (
                group if re.search(r"\b(?:bachelor|master|MBBS|BDS)\b", group, re.I) else None
            )
            builder.meta["scope"] = ClaimScope(
                population=population,
                faculty=faculty,
                programme=programme,
                academic_year=year,
            )
            builder.meta["academic_year"] = year
            claim = builder.add(
                ClaimType.TUITION,
                money,
                quote,
                subject_key=f"{population} / {group}",
                section=" / ".join(row[0].section_path),
                notes="Published tariff retained; applicant fee status and faculty/programme applicability are unconfirmed.",
            )
            if claim is not None:
                out.claims.append(claim)

        seen: set[tuple[str, str]] = set()
        content = main_content(parse_html(html))
        section_path: list[tuple[int, str]] = []
        for node in content.find_all(True):
            if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                level = int(node.name[1])
                while section_path and section_path[-1][0] >= level:
                    section_path.pop()
                heading_text = " ".join(node.get_text(" ", strip=True).split())
                if heading_text:
                    section_path.append((level, heading_text))
                continue
            if node.name not in {"div", "li", "dd", "p", "section"}:
                continue
            proof = " ".join(node.get_text(" ", strip=True).split())
            match = _HOUSING_OPTION.match(proof)
            if match is None or not _MONEY.match(proof[match.end() :]):
                continue
            out.handled_types.add(ClaimType.HOUSING_COST)
            context = " / ".join(heading for _level, heading in section_path)
            key = (proof, context)
            if key in seen:
                continue
            seen.add(key)
            money = _money_value(proof[match.end() :], annual=True)
            quote = _complete_quote(proof, builder.page_text)
            if money is None or not quote:
                continue
            option = match.group("option")
            # A remote page heading's date is not this option's fee year.
            nearest_heading = section_path[-1][1] if section_path else ""
            option_year = read_scope(nearest_heading).academic_year
            builder.meta["scope"] = ClaimScope(academic_year=option_year)
            builder.meta["academic_year"] = option_year
            claim = builder.add(
                ClaimType.HOUSING_COST,
                money,
                quote,
                subject_key=option,
                section=context or "Housing option",
                notes="Published housing option retained; no applicant option or full-year accommodation selected.",
            )
            if claim is not None:
                out.claims.append(claim)
    finally:
        builder.meta["scope"] = original_scope
        builder.meta["academic_year"] = original_year
    return out


#: FE-2: the column of a per-course fee table that names the course.
_COURSE_COLUMN = re.compile(r"^(?:course|programme|program|degree)(?:\s+(?:name|title))?$", re.I)
#: A fee column for later years, or priced per term, is not a first-year
#: annual fee: "Years 2+" beside "Year 1" is the continuing students' rate.
_NOT_FIRST_YEAR = re.compile(
    r"\byears?\s*(?:[2-9]|two|three|four)\b|\bsubsequent\b|\bcontinuing\b|\blater\s+years?\b"
    r"|\bper\s+(?:month|semester|term|credit|module)\b",
    re.I,
)
_FEE_WORD = re.compile(r"\b(?:fees?|tuition)\b", re.I)
_YEAR_COLUMN = re.compile(r"^(?:academic\s+)?year$|^academic\s+year\b", re.I)
#: What a course cell may carry beside the course's name: a parenthetical
#: note ("(Year 5 is postgraduate)") and the degree's letters.
_COURSE_NOTE = re.compile(r"\([^)]*\)|\b(?:B\.?A|B\.?Sc|BEng|B\.?E|Hons|Honours)\b\.?", re.I)


_DEGREE_PREFIX = re.compile(r"^\s*bachelor\s+of\s+(?:science|arts|engineering)\s+(?:in\s+)?", re.I)


def _course_key(name: str) -> str:
    """A course's name for comparison: no note, no degree letters, no case."""
    plain = _DEGREE_PREFIX.sub("", _COURSE_NOTE.sub(" ", name))
    return " ".join(re.sub(r"[^\w&]+", " ", plain).casefold().split())


def _international_column(header: str) -> str | None:
    """The population a fee column's header names, when it is the
    international (Overseas, International, non-EU) first-year fee."""
    if not _FEE_WORD.search(header) or _NOT_FIRST_YEAR.search(header):
        return None
    match = re.search(r"\b(overseas|international|non[-\s]?EU(?:\s*/\s*EEA)?)\b", header, re.I)
    population = fee_status_population(match.group(1)) if match else None
    return population if population in {"international", "non-EU/EEA"} else None


def extract_programme_fee_rows(document: DocumentIR, builder: ClaimBuilder) -> list[Claim]:
    """FE-2: the requested programme's row of a per-course fee table.

    Trinity's ``courses/undergraduate/fees/`` lists every course for several
    academic years, with the non-EU first-year fee in its own column: "2027/28
    | School of Computer Science & Statistics | Computer Science (Year 5 is
    postgraduate) | … | €30,450.00". The row is read only when exactly one row
    of the requested year names the requested programme (its course cell, less
    a parenthetical note and degree letters, *is* the programme's name or
    field: "Computer Science and Geography" is another course), and exactly
    one column is an international fee; otherwise the table is left alone.
    """
    requested = {_course_key(p) for p in builder.requested_programmes if _course_key(p)}
    want = _year_key(
        str(builder.requested_academic_year or builder.meta.get("academic_year") or "")
    )
    if not requested:
        return []
    tables: dict[int, dict[int, list[EvidenceBlock]]] = {}
    for block in document.blocks:
        if block.kind == "table_cell" and block.table_id is not None and block.row is not None:
            tables.setdefault(block.table_id, {}).setdefault(block.row, []).append(block)
    claims: list[Claim] = []
    for rows in tables.values():
        headers: dict[int, str] = {}
        for row in rows.values():
            for block in row:
                if block.col is not None and block.column_headers:
                    headers.setdefault(block.col, block.column_headers[-1])
        course_cols = [c for c, h in headers.items() if _COURSE_COLUMN.match(h.strip())]
        fee_cols = {c: p for c, h in headers.items() if (p := _international_column(h))}
        if len(fee_cols) > 1:
            fee_cols = {c: p for c, p in fee_cols.items() if "total" in headers[c].lower()}
        year_cols = [c for c, h in headers.items() if _YEAR_COLUMN.match(h.strip())]
        if len(course_cols) != 1 or len(fee_cols) != 1:
            continue
        (fee_col, population), course_col = next(iter(fee_cols.items())), course_cols[0]
        matches = []
        for row in rows.values():
            cells = {b.col: b for b in row if b.col is not None}
            course, fee = cells.get(course_col), cells.get(fee_col)
            if course is None or fee is None or _course_key(course.text) not in requested:
                continue
            stated = next(
                (
                    key
                    for key in (
                        *(_year_key(cells[c].text) for c in year_cols if c in cells),
                        *(_year_key(h) for h in row[0].row_headers),
                    )
                    if key
                ),
                None,
            )
            if want is not None and stated is not None and stated != want:
                continue
            if year_cols and stated is None:
                continue
            matches.append((row, fee, stated))
        if len(matches) != 1:
            continue
        row, fee, stated = matches[0]
        money = _money_value(fee.text, annual=False)
        quote = _complete_quote(_row_quote(row), builder.page_text)
        if money is None or "range_low" in money or not quote:
            continue
        # A heading names its table the way a title names its page: a bare
        # "Undergraduate Fees" is the bachelor's level.
        level = read_scope("", title=" / ".join(row[0].section_path)).degree
        if builder.requested_degree and level and level != builder.requested_degree:
            continue
        claim = builder.add(
            ClaimType.TUITION,
            money,
            quote,
            section=" / ".join(row[0].section_path) or "Fees and costs",
            subject_key=population,
            population=population,
            degree=level,
            academic_year=stated,
            notes=f"Per-course fee table, column {headers[fee_col]!r}.",
        )
        if claim is not None:
            claims.append(claim)
    return claims


def extract_unhandled_costs(
    text: str, builder: ClaimBuilder, handled: set[ClaimType]
) -> list[Claim]:
    """Legacy source rules only emit categories not handled structurally."""
    if not handled:
        return extract_costs(text, builder)
    original_add = builder.add

    def add_unhandled(
        claim_type: ClaimType, value: object, excerpt: str, **kwargs: Any
    ) -> Claim | None:
        if claim_type in handled:
            return None
        return original_add(claim_type, value, excerpt, **kwargs)

    builder.add = add_unhandled  # type: ignore[method-assign]
    try:
        return extract_costs(text, builder)
    finally:
        builder.add = original_add  # type: ignore[method-assign]

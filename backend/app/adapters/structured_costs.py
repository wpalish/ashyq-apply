"""Published cost rows/options, retained without selecting an applicant's tariff."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.adapters.document_ir import DocumentIR, EvidenceBlock
from app.adapters.extraction import _MONEY, ClaimBuilder, extract_costs, parse_money
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

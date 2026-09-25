"""Requirements read from a page's structure, before the prose regexes (V2-30C).

The prose extractor looks for "IELTS ... overall ... 6.5" within a sentence.
Real pages publish the same requirement as a table row (UBC: "IELTS |
International English Language Testing System (Academic) | 6.5, with no part
less than 6.0") or one column per section (Groningen: "IELTS Academic | 6.5 |
6.0 | 6.0"). Once flattened, the test name, the column meaning and the number
are three unrelated lines. Here they are read from DocumentIR, where the
markup still relates them.

The rules are strict on purpose: a value is read only when its own cell holds
it, and the cell's headers (row, column or caption) name IELTS. A column that
names no section and no "overall" is not guessed. The quote is the cell's
text, verbatim; the headers that give it meaning go in ``section``.
"""

from __future__ import annotations

import re
from dataclasses import replace

from app.adapters.document_ir import DocumentIR, EvidenceBlock
from app.adapters.extraction import ClaimBuilder
from app.adapters.scope_reader import read_scope
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimType
from app.schemas.claim import Claim

_IELTS = re.compile(r"\bIELTS\b|International English Language Testing System", re.I)
_SECTIONS = ("listening", "reading", "writing", "speaking")
_OVERALL = re.compile(r"\b(overall|total|minimum score|minimum|score|band)\b", re.I)
#: A band on its own: "6.5", "6", "6.5 overall".
_BAND = re.compile(r"^\s*(\d(?:\.\d)?)\s*(?:overall)?\s*$", re.I)
#: "6.5, with no part less than 6.0" — an overall band and a per-part floor.
_BAND_WITH_FLOOR = re.compile(
    r"^\s*(\d(?:\.\d)?)\s*(?:overall)?\s*[,;(]?\s*(?:with\s+)?no\s+"
    r"(?:individual\s+)?(?:part|band|section|component|sub-?score)s?\s+"
    r"(?:less\s+than|below|lower\s+than)\s+(\d(?:\.\d)?)",
    re.I,
)


def _band(raw: str) -> float | None:
    value = float(raw)
    return value if 4.0 <= value <= 9.0 and (value * 2).is_integer() else None


def _context(block: EvidenceBlock) -> str:
    return " | ".join([*block.row_headers, *block.column_headers, block.caption])


def _section(block: EvidenceBlock) -> str:
    return " / ".join([*block.section_path[-1:], *block.row_headers, *block.column_headers]).strip(
        " /"
    )


def extract_table_requirements(doc: DocumentIR, builder: ClaimBuilder) -> list[Claim]:
    """IELTS overall and per-section minimums from table cells, one table at a time.

    A table claim's population is what the table's own context states (its
    section heading, caption, row), never a population named elsewhere on the
    page: run 75 filed UBC's IELTS row as "transfer" because the page mentions
    transfer students in another section.
    """
    page_scope = builder.meta.get("scope")
    try:
        return _extract(doc, builder, page_scope)
    finally:
        builder.meta["scope"] = page_scope


def _scope_for(block: EvidenceBlock, page_scope: object) -> object:
    if not isinstance(page_scope, ClaimScope):
        return page_scope
    local = read_scope(" ".join([*block.section_path, block.caption, *block.row_headers]))
    return replace(page_scope, population=local.population)


def _extract(doc: DocumentIR, builder: ClaimBuilder, page_scope: object) -> list[Claim]:
    found: list[Claim] = []
    overall_done = False
    bands: dict[str, float] = {}
    band_block: EvidenceBlock | None = None
    for block in doc.blocks:
        if block.kind != "table_cell" or not _IELTS.search(" ".join(block.row_headers)):
            # The row must be the IELTS row: a caption naming IELTS over a table
            # of several tests does not make every number an IELTS band.
            continue
        headers = " ".join(block.column_headers).lower()
        floor = _BAND_WITH_FLOOR.match(block.text)
        if floor and not overall_done:
            overall, part = _band(floor.group(1)), _band(floor.group(2))
            if overall is not None and part is not None and part <= overall:
                builder.meta["scope"] = _scope_for(block, page_scope)
                for claim_type, value in (
                    (ClaimType.IELTS_MIN_OVERALL, overall),
                    (ClaimType.IELTS_MIN_SUBSCORE, part),
                ):
                    claim = builder.add(claim_type, value, block.text, section=_section(block))
                    if claim is not None:
                        found.append(claim)
                overall_done = True
            continue
        single = _BAND.match(block.text)
        if not single:
            continue
        band = _band(single.group(1))
        if band is None:
            continue
        named = [s for s in _SECTIONS if re.search(rf"\b{s}\b", headers)]
        if len(named) == 1:
            bands.setdefault(named[0], band)
            band_block = band_block or block
        elif not named and _OVERALL.search(headers) and not overall_done:
            builder.meta["scope"] = _scope_for(block, page_scope)
            claim = builder.add(
                ClaimType.IELTS_MIN_OVERALL, band, block.text, section=_section(block)
            )
            if claim is not None:
                found.append(claim)
            overall_done = True
    if bands and band_block is not None:
        # Sections named one by one, as the prose extractor records them: a map.
        builder.meta["scope"] = _scope_for(band_block, page_scope)
        claim = builder.add(
            ClaimType.IELTS_MIN_SUBSCORE,
            dict(sorted(bands.items())),
            band_block.text,
            section=_section(band_block) + " (per section: " + ", ".join(sorted(bands)) + ")",
        )
        if claim is not None:
            found.append(claim)
    return found

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
from collections.abc import Callable
from dataclasses import dataclass, replace

from app.adapters import extraction
from app.adapters.document_ir import DocumentIR, EvidenceBlock
from app.adapters.extraction import ClaimBuilder, EnglishHint, faculty_key
from app.adapters.scope_reader import read_scope
from app.domain.claim_scope import ClaimScope
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.enums import ClaimType
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim

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
        claims = _extract(doc, builder, page_scope)
        if extraction.ENGLISH_READERS_V2:
            answered = {c.claim_type for c in claims}
            claims += _extract_v2(doc, builder, page_scope, answered)
        return claims
    finally:
        builder.meta["scope"] = page_scope


def _scope_for(block: EvidenceBlock, page_scope: object) -> object:
    if not isinstance(page_scope, ClaimScope):
        return page_scope
    local = read_scope(" ".join([*block.section_path, block.caption, *block.row_headers]))
    return replace(page_scope, population=local.population)


def _extract(doc: DocumentIR, builder: ClaimBuilder, page_scope: object) -> list[Claim]:
    rows: dict[tuple[int, int], list[EvidenceBlock]] = {}
    for block in doc.blocks:
        if block.kind != "table_cell" or not _IELTS.search(" ".join(block.row_headers)):
            # A caption mentioning IELTS does not make every test row IELTS.
            continue
        if block.table_id is None or block.row is None:
            continue
        rows.setdefault((block.table_id, block.row), []).append(block)
    return [claim for row in rows.values() for claim in _extract_row(row, builder, page_scope)]


def _extract_row(
    row: list[EvidenceBlock], builder: ClaimBuilder, page_scope: object
) -> list[Claim]:
    """One published requirement; cells from another row cannot complete it."""
    found: list[Claim] = []
    overall_done = False
    bands: dict[str, float] = {}
    band_block: EvidenceBlock | None = None
    for block in row:
        headers = " ".join(block.column_headers).lower()
        floor = _BAND_WITH_FLOOR.match(block.text)
        pair = (
            (floor.group(1), floor.group(2))
            if floor
            else (_ielts_floor_v2(block.text) if extraction.ENGLISH_READERS_V2 else None)
        )
        if pair and not overall_done:
            overall, part = _band(pair[0]), _band(pair[1])
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
        row_excerpt = " ".join(block.text for block in row)
        if len(row_excerpt) > MAX_EXCERPT_CHARS:
            # Claim clips long quotes. Abstain before a later band can disappear
            # from stored evidence while remaining in the claimed map.
            return found
        # Sections named one by one, as the prose extractor records them: a map.
        builder.meta["scope"] = _scope_for(band_block, page_scope)
        claim = builder.add(
            ClaimType.IELTS_MIN_SUBSCORE,
            dict(sorted(bands.items())),
            # Keep every cell in source order, including intervening text. A
            # quote of the first band alone cannot support the remaining bands.
            # ClaimBuilder checks the contiguous row against the page text.
            row_excerpt,
            section=_section(band_block) + " (per section: " + ", ".join(sorted(bands)) + ")",
        )
        if claim is not None:
            found.append(claim)
    return found


# --- plan change EN-2 (``extraction.ENGLISH_READERS_V2``) ----------------------
#
# The tables the reader above cannot attribute: the test is a column header
# (TCD: a first row of <td>s naming "IELTS Academic", "TOEFL iBT (Before January
# 2026)", ...) or the table's own label (UNSW's "IELTS ..." accordion, Imperial's
# "IELTS – Academic" tab), and the rows are entry bands or faculties. A table
# like that states several requirements for one test; the programme's row is
# picked by what its programme page says (EnglishHint) and, when the rows still
# disagree, nothing is claimed — never the first, the highest or the lowest.

_TEST_NAMES: tuple[tuple[ClaimType, re.Pattern[str]], ...] = (
    (ClaimType.IELTS_MIN_OVERALL, _IELTS),
    (
        ClaimType.TOEFL_MIN_TOTAL,
        re.compile(r"\bTOEFL\b|Test of English as a Foreign Language", re.I),
    ),
    (ClaimType.DUOLINGO_MIN, re.compile(r"\bDuolingo\b", re.I)),
)
#: A label naming one of these is another test's (or two tests') table.
_OTHER_TEST_NAME = re.compile(
    r"\b(?:PTE|Pearson|Cambridge|LanguageCert|OET|Occupational English|Michigan|CAEL"
    r"|CELPIP|Oxford Test|MUET|ISE)\b",
    re.I,
)
#: EN-2b: "tests equivalent to IELTS", "alternatives to IELTS", "in place of
#: IELTS": the test named is the yardstick, the rows are other tests.
_EQUIVALENT_TO = re.compile(
    r"\b(?:equivalents?|alternatives?)\s+to\b|\bin\s+(?:lieu|place)\s+of\b|\binstead\s+of\b",
    re.I,
)
#: The number a cell starts with, and the word that makes it the overall one.
_CELL_LEAD = re.compile(r"^\s*(\d{1,3}(?:\.\d)?)(?!\d)\s*(overall|total)?\b\s*[,;]?\s*", re.I)
#: A per-part floor stated after the overall number, the whole rest of the cell.
_CELL_FLOORS: tuple[re.Pattern[str], ...] = (
    # UNSW "(min 6.0 in each subtest)", Imperial "(minimum 6.0 in all elements)"
    re.compile(
        r"\(?\s*(?:with\s+)?(?:a\s+)?min(?:imum|\.)?\s*(?:of\s+)?(\d{1,3}(?:\.\d)?)\s+in\s+"
        r"(?:each|all|every)(?:\s+[\w-]+){1,2}\s*\)?",
        re.I,
    ),
    # TCD "6.0 in each band", "21 in each section", "100 in each subscore"
    re.compile(
        r"(?:with\s+)?(\d{1,3}(?:\.\d)?)\s+in\s+(?:each|all|every)\s+(?:band|section|subtest"
        r"|sub-?score|element|component|skill|module|part)s?",
        re.I,
    ),
    # UBC "with no part less than 6.0"
    re.compile(
        r"\(?\s*(?:with\s+)?no\s+(?:individual\s+)?(?:part|band|section|component|sub-?score"
        r"|element|skill)s?\s+(?:less\s+than|below|lower\s+than)\s+(\d{1,3}(?:\.\d)?)\s*\)?",
        re.I,
    ),
    # Imperial "with no less than 105 in any integrated subscore"
    re.compile(
        r"\(?\s*(?:with\s+)?no\s+(?:less|lower)\s+than\s+(\d{1,3}(?:\.\d)?)\s+in\s+"
        r"(?:any|each|all)(?:\s+[\w-]+){1,3}\s*\)?",
        re.I,
    ),
)
#: Sections named one by one, "(min. 23 in writing, 22 in reading, listening
#: and speaking)": a statement about the parts, not a single floor.
_CELL_SECTIONS = re.compile(r"\(\s*min(?:imum|\.)?\s+\d[^()]*\)", re.I)
_CELL_END = re.compile(r"[\s.;]*")
_VALUE_LIKE = re.compile(r"^\s*\d")
#: A cell that states a requirement: it starts with the score, or says "overall"
#: / "minimum" / "not accepted". A description ("Test of English as a Foreign
#: Language") or a footnote ("*Test scores are only considered valid if taken
#: within 2 years ...") states none.
_REQUIREMENT_CELL = re.compile(
    r"^\s*\d|\b(?:overall|minimum|at\s+least)\b|\bmin\.|\bnot\s+(?:accepted|applicable)\b"
    r"|^\s*n/?a\s*$",
    re.I,
)
_STATES_OVERALL = re.compile(r"\b(?:overall|total)\b", re.I)
_FOOTNOTE = re.compile(r"^\s*(?:[*†‡]|note\b|please\b)", re.I)
_UNDERGRADUATE = re.compile(r"\b(?:undergraduate|bachelor'?s?|UG)\b", re.I)
_POSTGRADUATE = re.compile(
    r"\b(?:postgraduate|graduate|master'?s?|PG|research|doctoral|PhD)\b", re.I
)

_Reading = tuple[float, float | None]


@dataclass(frozen=True, slots=True)
class _Candidate:
    """One cell that states a minimum for one test, with the labels of its row."""

    block: EvidenceBlock
    #: (overall, per-part floor) as read; None when the cell could not be read.
    reading: _Reading | None
    row_label: str
    column_label: str

    @property
    def labels(self) -> str:
        return f"{self.row_label} | {self.column_label}"


def _ielts_floor_v2(text: str) -> tuple[str, str] | None:
    """EN-2 (b): "6.5 overall (min 6.0 in each subtest)" as (overall, floor)."""
    status, reading = _read_cell(ClaimType.IELTS_MIN_OVERALL, text, "")
    if status != "ok" or reading is None or reading[1] is None:
        return None
    return str(reading[0]), str(reading[1])


def _read_cell(test: ClaimType, text: str, headers: str) -> tuple[str, _Reading | None]:
    """("ok", reading), ("other", None) for TOEFL's banded 1-6 scale, or ("unread", None)."""
    lead = _CELL_LEAD.match(text)
    if lead is None:
        return "unread", None
    raw, word = lead.group(1), lead.group(2)
    rest = text[lead.end() :]
    floor: str | None = None
    stated = False
    if not _CELL_END.fullmatch(rest):
        for pattern in _CELL_FLOORS:
            m = pattern.match(rest)
            if m and _CELL_END.fullmatch(rest, m.end()):
                floor, stated = m.group(1), True
                break
        else:
            m = _CELL_SECTIONS.match(rest)
            if not (m and _CELL_END.fullmatch(rest, m.end())):
                return "unread", None
            stated = True
    if not (word or stated or _OVERALL.search(headers)):
        # A bare number under a header that does not say "overall" is not guessed.
        return "unread", None
    if test is ClaimType.IELTS_MIN_OVERALL:
        overall, part = _band(raw), (_band(floor) if floor else None)
        if overall is None or (floor and (part is None or part > overall)):
            return "unread", None
        return "ok", (overall, part)
    if "." in raw or float(raw) <= 9:
        # TOEFL iBT's 1-6 bands (from January 2026): not a 0-120 total.
        return "other", None
    low, high = (40, 120) if test is ClaimType.TOEFL_MIN_TOTAL else (60, 160)
    if not low <= int(raw) <= high:
        return "unread", None
    return "ok", (float(raw), None)


def _names_a_test(label: str) -> bool:
    return bool(_OTHER_TEST_NAME.search(label) or any(p.search(label) for _, p in _TEST_NAMES))


def _test_of(*sources: str) -> ClaimType | None:
    """The one test the first label that names any test names, else None.

    A label that names a test as the yardstick of others ("Approved English
    proficiency tests equivalent to IELTS (Academic)") names no test of its
    rows: it stops the search and attributes nothing.
    """
    for source in sources:
        ours = {test for test, pattern in _TEST_NAMES if pattern.search(source)}
        other = _OTHER_TEST_NAME.search(source)
        if ours or other:
            if _EQUIVALENT_TO.search(source):
                return None
            return ours.pop() if len(ours) == 1 and not other else None
    return None


def _first_row_headers(cells: list[EvidenceBlock]) -> dict[int, str]:
    """TCD: a header row written as <td>s that name tests, as {column: text}."""
    if any(c.column_headers for c in cells):
        return {}
    first = min(c.row for c in cells if c.row is not None)
    row = [c for c in cells if c.row == first and c.col is not None]
    if len(row) < 2 or any(_CELL_LEAD.match(c.text) for c in row):
        return {}
    if not any(pattern.search(c.text) for c in row for _, pattern in _TEST_NAMES):
        return {}
    return {c.col: c.text for c in row if c.col is not None}


def _narrow(cands: list[_Candidate], keep: Callable[[_Candidate], bool]) -> list[_Candidate]:
    """The candidates a hint names; all of them when it names none."""
    kept = [c for c in cands if keep(c)]
    return kept or cands


def _pick(cands: list[_Candidate], hint: EnglishHint | None) -> _Candidate | None:
    """The programme's row, or None when the rows left still disagree."""
    if hint is not None:
        if hint.degree:
            level = _POSTGRADUATE if hint.degree in ("master", "phd") else _UNDERGRADUATE
            cands = _narrow(cands, lambda c: bool(level.search(c.column_label + " " + c.row_label)))
        if hint.units:
            units = hint.units
            cands = _narrow(
                cands,
                lambda c: any(
                    faculty_key(label) in units for label in (c.row_label, c.column_label) if label
                ),
            )
        if hint.band:
            band = re.compile(rf"\bband\s+{re.escape(hint.band)}\b", re.I)
            cands = _narrow(cands, lambda c: bool(band.search(c.labels)))
        if hint.level:
            word = re.compile(rf"\b{re.escape(hint.level)}\b", re.I)
            cands = _narrow(cands, lambda c: bool(word.search(c.labels)))
    readings = {c.reading for c in cands}
    if len(readings) != 1 or None in readings:
        return None
    return cands[0]


def _row_quote(chosen: _Candidate, cells: list[EvidenceBlock], page_text: str | None) -> str:
    """The row from its label to the chosen cell, when the page has it verbatim."""
    block = chosen.block
    row = sorted(
        (c for c in cells if c.row == block.row and (c.col or 0) <= (block.col or 0)),
        key=lambda c: c.col or 0,
    )
    parts = [c.text for c in row]
    if chosen.row_label and block.row_headers and (not row or row[0].text != chosen.row_label):
        parts.insert(0, chosen.row_label)
    quote = " ".join(parts)
    if (
        page_text
        and len(quote) <= MAX_EXCERPT_CHARS
        and is_verbatim_excerpt(quote.casefold(), page_text.casefold())
    ):
        return quote
    return block.text


def _extract_v2(
    doc: DocumentIR, builder: ClaimBuilder, page_scope: object, answered: set[ClaimType]
) -> list[Claim]:
    tables: dict[int, list[EvidenceBlock]] = {}
    for block in doc.blocks:
        if block.kind == "table_cell" and block.table_id is not None and block.row is not None:
            tables.setdefault(block.table_id, []).append(block)
    found: dict[ClaimType, list[_Candidate]] = {}
    for cells in tables.values():
        synthetic = _first_row_headers(cells)
        first = min(c.row for c in cells if c.row is not None)
        # EN-2b: a table whose rows are named by test (Auckland's "Cambridge",
        # "PTE", "LanguageCert", ... under "tests equivalent to IELTS") is a
        # table of tests. A row there that names no known test is an unknown
        # test ("AEMG ... Final Exam"), not the test of the table's heading.
        rows_are_tests = any(
            _names_a_test(h) for c in cells for h in c.row_headers if not _VALUE_LIKE.match(h)
        )
        for block in cells:
            if synthetic and block.row == first:
                continue
            if _IELTS.search(" ".join(block.row_headers)):
                continue  # an IELTS row: the reader above reads it
            columns = block.column_headers or (
                (synthetic[block.col],) if block.col in synthetic else ()
            )
            row_label = " ".join(h for h in block.row_headers if not _VALUE_LIKE.match(h))
            column_label = " ".join(columns)
            heading = block.section_path[-1] if block.section_path else ""
            labels = (row_label, column_label)
            test = (
                _test_of(*labels)
                if rows_are_tests
                else _test_of(*labels, block.table_label, heading)
            )
            if test is None or test in answered:
                continue
            if _FOOTNOTE.match(block.text) or not _REQUIREMENT_CELL.search(block.text):
                continue
            status, reading = _read_cell(test, block.text, column_label)
            if status == "other":
                continue
            found.setdefault(test, []).append(_Candidate(block, reading, row_label, column_label))
    claims: list[Claim] = []
    for test, cands in found.items():
        chosen = _pick(cands, builder.english_hint)
        if chosen is None or chosen.reading is None:
            if not any(c.reading or _STATES_OVERALL.search(c.block.text) for c in cands):
                # Nothing in the table reads as a score for this test (a table
                # of test dates under an "IELTS" heading): it answers nothing
                # and silences nothing.
                continue
            builder.english_abstained.add(test)
            if test is ClaimType.IELTS_MIN_OVERALL:
                builder.english_abstained.add(ClaimType.IELTS_MIN_SUBSCORE)
            continue
        block = chosen.block
        overall, floor = chosen.reading
        quote = _row_quote(chosen, tables[block.table_id or 0], builder.page_text)
        heading = block.table_label or (block.section_path[-1] if block.section_path else "")
        section = " / ".join(x for x in (heading, chosen.row_label, chosen.column_label) if x)
        builder.meta["scope"] = _scope_for(block, page_scope)
        values: list[tuple[ClaimType, object]]
        if test is ClaimType.IELTS_MIN_OVERALL:
            values = [(test, overall)]
            if floor is not None:
                values.append((ClaimType.IELTS_MIN_SUBSCORE, floor))
            else:
                # The row states no floor; a floor read elsewhere on the page
                # would belong to another row.
                builder.english_abstained.add(ClaimType.IELTS_MIN_SUBSCORE)
        else:
            values = [(test, int(overall))]
        for claim_type, value in values:
            claim = builder.add(claim_type, value, quote, section=section)
            if claim is not None:
                claims.append(claim)
    return claims

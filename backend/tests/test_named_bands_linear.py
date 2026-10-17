"""EX-1: the per-section IELTS reading is linear in the page, and reads the same.

Masaryk lost all eight repetitions to ``_named_bands``: its sentence pattern,
``(?:[^.\\n]|\\.(?=\\d))*\\bIELTS\\b(?:[^.\\n]|\\.(?=\\d))*``, re-scanned every
period-free line from each of its positions — 15 s on a 31k-character page, in
synchronous code the child's own deadline could not interrupt. The rewrite
finds "IELTS" first and widens each hit to its sentence. The old pattern is
kept here as the oracle: the spans and bands must not move.
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime

import pytest

from app.adapters.extraction import (
    _IELTS_NAMED_BAND,
    _OTHER_TEST,
    ClaimBuilder,
    _named_bands,
    for_matching,
)
from app.adapters.requirements.web_requirements import extract_requirements

_OLD_IELTS_SENTENCE = re.compile(
    r"(?:[^.\n]|\.(?=\d))*\bIELTS\b(?:[^.\n]|\.(?=\d))*",
    re.IGNORECASE,
)


def _old_named_bands(text: str) -> tuple[int, int, dict[str, float]] | None:
    """The implementation before EX-1, verbatim apart from the name."""
    for sentence in _OLD_IELTS_SENTENCE.finditer(text):
        body = sentence.group(0)
        named = re.search(r"\bIELTS\b", body, re.IGNORECASE)
        other = _OTHER_TEST.search(body, named.end()) if named else None
        if other:
            body = body[: other.start()]
        bands = {
            match.group(1).lower(): float(match.group(2))
            for match in _IELTS_NAMED_BAND.finditer(body)
            if 4.0 <= float(match.group(2)) <= 9.0
        }
        if bands:
            return sentence.start(), sentence.end(), bands
    return None


#: A Masaryk-shaped page: one very long line with no full stop and no IELTS,
#: then the English requirement on a line of its own.
_LONG_LINE = (
    "Applicants from abroad may submit a language certificate with section scores " * 520
)[:40_000]
_LONG_PAGE = _LONG_LINE + "\nIELTS 6.5 overall with Writing 6.0 and Speaking 6.0."

_REPRESENTATIVE = [
    "IELTS: Overall 6, Writing 6,speaking 6",
    "IELTS Academic: overall 7.0, with Writing 6.5 and Reading 6.0.",
    "IELTS overall 7.0, Writing 6.5.",
    "IELTS overall 6.5, no band less than 6.0.",
    "IELTS overall 6.5. Writing competitions are held in June 7.",
    "Writing 6 is the room number. Applicants need a good essay.",
    "IELTS overall 6.5, Writing 12.",
    # A PTE table run on into the IELTS one with no full stop between.
    "IELTS 6.5 (Writing 6.0) PTE Academic 60, Reading: 60, Writing 59",
    # The first IELTS sentence names no band; the second one does.
    "We accept IELTS. Our ielts minimum is Listening 6.0, Reading 6.5\nnext line",
    # IELTS inside a longer word is not the test.
    "IELTSX Writing 6.5. Then IELTS with Speaking 7.0.",
    # Two IELTS mentions in one sentence, a decimal point at the very end.
    "IELTS or IELTS Indicator: Writing 6.0 and Reading 6.5 or 7.",
    "",
    "no test named here at all",
    _LONG_PAGE,
    _LONG_LINE + " IELTS Writing 6.5",
]


@pytest.mark.parametrize("text", _REPRESENTATIVE, ids=range(len(_REPRESENTATIVE)))
def test_reads_exactly_what_the_old_pattern_read(text: str) -> None:
    if len(text) > 10_000 and "\n" in text:
        # The old pattern takes ~40 s on this one; the oracle for it is spelled
        # out instead of recomputed.
        start = len(_LONG_LINE) + 1
        assert _named_bands(text) == (start, len(text) - 1, {"writing": 6.0, "speaking": 6.0})
        return
    assert _named_bands(text) == _old_named_bands(text)


def test_a_forty_thousand_character_page_reads_in_well_under_a_second() -> None:
    started = time.perf_counter()
    found = _named_bands(_LONG_PAGE)
    elapsed = time.perf_counter() - started
    assert found is not None and found[2] == {"writing": 6.0, "speaking": 6.0}
    assert elapsed < 2.0, f"_named_bands took {elapsed:.2f} s on a 40k page"


def test_the_whole_requirements_extraction_is_bounded_on_that_page() -> None:
    builder = ClaimBuilder(source_url="fixture://page", accessed_at=datetime.now(UTC))
    started = time.perf_counter()
    extract_requirements(for_matching(_LONG_PAGE), builder)
    elapsed = time.perf_counter() - started
    got = {c.claim_type.value: c.normalized_value for c in builder.claims}
    assert got["ielts_min_subscore"] == {"writing": 6.0, "speaking": 6.0}
    assert elapsed < 2.0, f"extract_requirements took {elapsed:.2f} s on a 40k page"

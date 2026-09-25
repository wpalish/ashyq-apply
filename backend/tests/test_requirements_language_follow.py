"""The English requirement on its own page is followed from the programme page (V2-31 seed).

UBC's programme page sends the reader to the English Language Admission
Standard; the IELTS row lives there, in a table.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.domain.enums import ClaimType, DegreeLevel
from tests.test_document_ir import UBC

PROGRAMME = """<html><head><title>Computer Science (BSc) - UBC</title></head><body>
<h1>Computer Science (BSc)</h1>
<p>Bachelor of Science in Computer Science. Program requirements: see the
<a href="fixture://ubc/english.html">English language requirements</a> and
<a href="fixture://ubc/museum.html">our museum</a>.</p>
</body></html>"""


def _site(tmp_path: Path, english: str = UBC) -> Path:
    root = tmp_path / "site"
    (root / "ubc").mkdir(parents=True)
    (root / "ubc" / "programme.html").write_text(PROGRAMME, encoding="utf-8")
    (root / "ubc" / "english.html").write_text(english, encoding="utf-8")
    (root / "ubc" / "museum.html").write_text("<p>IELTS 9.0 overall</p>", encoding="utf-8")
    return root


async def _run(settings, root: Path):
    candidate = Candidate(name="UBC", country="Canada", city="Vancouver", domain="ubc.ca")
    program = CandidateProgram(
        name="Computer Science (BSc)",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url="fixture://ubc/programme.html",
    )
    async with Fetcher(settings.cache_dir, offline=True, corpus_dir=root) as f:
        return await WebRequirementsAdapter(f, "2027/28").verify(candidate, program, "fall 2027")


@pytest.mark.asyncio
async def test_the_linked_language_page_is_read_and_its_table_gives_ielts(settings, tmp_path):
    result = await _run(settings, _site(tmp_path))
    by_type = {c.claim_type: c for c in result.claims}
    assert by_type[ClaimType.IELTS_MIN_OVERALL].normalized_value == 6.5
    assert by_type[ClaimType.IELTS_MIN_OVERALL].source_url == "fixture://ubc/english.html"
    assert by_type[ClaimType.IELTS_MIN_SUBSCORE].normalized_value == 6.0
    # The museum link names no English requirement and is not read.
    assert "fixture://ubc/museum.html" not in {o.url for o in result.page_outcomes}


@pytest.mark.asyncio
async def test_nothing_is_followed_once_ielts_is_known(settings, tmp_path):
    root = _site(tmp_path)
    (root / "ubc" / "programme.html").write_text(
        PROGRAMME.replace(
            "Program requirements:", "IELTS overall band of 7.0. Program requirements:"
        ),
        encoding="utf-8",
    )
    result = await _run(settings, root)
    assert "fixture://ubc/english.html" not in {o.url for o in result.page_outcomes}

"""A programme page confirms existence only for the applicant's own field (run 51, HKU).

Search brought HKU's "Computing and Data Science" page; discovery named the
lead after its URL slug, so the requested name matched the page it came from
and existence was confirmed for a computer science applicant.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.adapters.fetching import Fetcher
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from tests.test_live_extraction import _candidate, _program, _serve

_URL = "https://www.qa-fixture.example/undergraduate/computing-and-data-science"


def _page(title: str) -> str:
    return (
        f"<html><head><title>{title} | QA Fixture University</title></head><body><main>"
        f"<h1>Bachelor of Science in {title}</h1>"
        f"<p>The Bachelor of Science in {title} is a four-year undergraduate programme. "
        "Applicants need IELTS overall 6.5. The application deadline is 1 May 2027.</p>"
        "</main></body></html>"
    )


async def _exists(monkeypatch, tmp_path, title: str, name: str):
    async with Fetcher(tmp_path / "cache", delay_seconds=0.0, offline=True) as fetcher:
        _serve(monkeypatch, fetcher, {_URL: _page(title)})
        program = replace(_program(_URL), name=name)
        result = await WebRequirementsAdapter(fetcher, "2026/27").verify(
            _candidate(), program, "fall 2027"
        )
    return [c for c in result.claims if c.claim_type.value == "program_exists"]


@pytest.mark.asyncio
async def test_a_slug_named_lead_does_not_confirm_another_field(monkeypatch, tmp_path):
    claims = await _exists(
        monkeypatch, tmp_path, "Computing and Data Science", "Computing And Data Science"
    )
    assert claims == []


@pytest.mark.asyncio
async def test_the_applicants_field_still_confirms(monkeypatch, tmp_path):
    claims = await _exists(monkeypatch, tmp_path, "Computer Science", "Computer Science")
    assert len(claims) == 1

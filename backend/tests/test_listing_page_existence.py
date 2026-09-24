"""A listing page may confirm a programme exists — nothing more (owner, 2026-09-23).

HKU's certified source for "Bachelor of Engineering in Computer Science" is its
School of Computing and Data Science page, which lists programmes. The adapter's
rule was that only a programme's own page may confirm existence, so the fact was
unreachable. It now may, strictly: a full degree title that the ontology's strong
aliases equate with the request, at the requested degree level, and existence only.
"""

from __future__ import annotations

import pytest

from app.adapters.fetching import Fetcher
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from tests.test_live_extraction import _candidate, _program, _serve

_URL = "https://admissions.qa-fixture.example/programmes/computing-and-data-science"


def _school(body: str) -> str:
    links = "".join(f'<li><a href="/programmes/p{i}">Programme {i}</a></li>' for i in range(6))
    return (
        "<html><head><title>Computing and Data Science | Admissions</title></head><body><main>"
        f"<h1>Computing and Data Science</h1><p>{body}</p><ul>{links}</ul></main></body></html>"
    )


async def _existence(monkeypatch, tmp_path, html: str):
    async with Fetcher(tmp_path / "cache", delay_seconds=0.0, offline=True) as fetcher:
        _serve(monkeypatch, fetcher, {_URL: html})
        result = await WebRequirementsAdapter(fetcher, "2026/27").verify(
            _candidate(), _program(_URL), "fall 2027"
        )
    return [c for c in result.claims if c.claim_type.value == "program_exists"], result


@pytest.mark.asyncio
async def test_a_full_degree_title_on_a_listing_page_confirms_existence(monkeypatch, tmp_path):
    claims, _ = await _existence(
        monkeypatch,
        tmp_path,
        _school(
            "The Bachelor of Engineering in Computer Science covers algorithms and data "
            "structures. IELTS overall 6.5 is required."
        ),
    )
    assert len(claims) == 1
    assert claims[0].normalized_value["program"] == "Bachelor of Engineering in Computer Science"
    assert claims[0].normalized_value["degree"] == "bachelor"


@pytest.mark.asyncio
async def test_a_related_field_is_not_the_requested_programme(monkeypatch, tmp_path):
    claims, _ = await _existence(
        monkeypatch,
        tmp_path,
        _school("The Bachelor of Science in Data Science covers statistics and machine learning."),
    )
    assert claims == []


@pytest.mark.asyncio
async def test_a_listing_page_yields_existence_and_nothing_else(monkeypatch, tmp_path):
    _, result = await _existence(
        monkeypatch,
        tmp_path,
        _school(
            "The Bachelor of Engineering in Computer Science covers algorithms. "
            "Applicants need IELTS overall 6.5."
        ),
    )
    assert {c.claim_type.value for c in result.claims} <= {"program_exists"}


@pytest.mark.asyncio
async def test_the_requested_field_counts_when_the_name_is_the_faculty_s(monkeypatch, tmp_path):
    """Run 35: the candidate carried the page's own name, 'Computing and Data
    Science', while the applicant asked for computer science."""
    from dataclasses import replace

    from app.adapters.base import CandidateProgram
    from app.domain.enums import DegreeLevel

    program = CandidateProgram(
        name="Computing and Data Science",
        field="computer science",
        degree=DegreeLevel.BACHELOR,
        url=_URL,
    )
    html = _school("The Bachelor of Engineering in Computer Science covers algorithms.")
    async with Fetcher(tmp_path / "cache", delay_seconds=0.0, offline=True) as fetcher:
        _serve(monkeypatch, fetcher, {_URL: html})
        result = await WebRequirementsAdapter(fetcher, "2026/27").verify(
            _candidate(), replace(program), "fall 2027"
        )
    claims = [c for c in result.claims if c.claim_type.value == "program_exists"]
    assert [c.normalized_value["program"] for c in claims] == [
        "Bachelor of Engineering in Computer Science"
    ]

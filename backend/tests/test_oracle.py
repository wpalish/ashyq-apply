"""EXTRA-10: read each certified fact from its own source page.

`claim_recall` has said 0/62 for four runs without ever distinguishing "we
never reached the page" from "we reached it and could not read it". Fetching
the labelled URL directly removes discovery from the question by construction,
so the verdict that comes back is about readability alone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.fetching import Fetcher
from evaluation.research.oracle import (
    FETCH_FAILED,
    RECOVERED,
    TEXT_MISSING,
    TIMED_OUT,
    VALUE_MISSING,
    Target,
    bounded_probe,
    excerpt_is_present,
    probe,
    summarise,
    targets,
)
from evaluation.research.schema import Dataset

_PLAIN = """<html><head><title>BSc Computer Science</title></head><body><main>
<h1>BSc Computer Science</h1>
<p>This bachelor's degree programme in computer science is taught in English.</p>
<p>Applicants need an IELTS Academic overall band score of 6.5.</p>
</main></body></html>"""

_AS_A_TABLE = """<html><head><title>BSc Computer Science</title></head><body><main>
<h1>BSc Computer Science</h1>
<p>This bachelor's degree programme in computer science is taught in English.</p>
<table>
<tr><th>Test</th><th>Overall</th><th>Reading</th><th>Listening</th><th>Speaking</th><th>Writing</th></tr>
<tr><td>IELTS (Academic)</td><td>6.5</td><td>6.5</td><td>6.5</td><td>6.5</td><td>6.5</td></tr>
</table>
</main></body></html>"""

_SILENT = """<html><head><title>BSc Computer Science</title></head><body><main>
<h1>BSc Computer Science</h1>
<p>This bachelor's degree programme in computer science lasts three years.</p>
</main></body></html>"""


def _dataset(url: str, excerpt: str) -> Dataset:
    return Dataset.model_validate(
        {
            "schema_version": "1",
            "version": "test",
            "split": "development",
            "cases": [
                {
                    "id": "example",
                    "dataset_version": "test",
                    "university": "Example University",
                    "domain": "uni.edu",
                    "country": "Testland",
                    "site_types": [],
                    "request": {
                        "university": "Example University",
                        "degree": "bachelor",
                        "field": "computer science",
                        "intake": "fall 2027",
                    },
                    "programme_urls": [],
                    "programme_status": "unknown",
                    "programme_evidence": [],
                    "labels": [
                        {
                            "key": "ielts.overall",
                            "status": "known",
                            "value": 6.5,
                            "critical": True,
                            "evidence": [
                                {
                                    "url": url,
                                    "excerpt": excerpt,
                                    "scope": {
                                        "university": "Example University",
                                        "programme": None,
                                        "degree": "bachelor",
                                        "field": "computer science",
                                        "intake": "fall 2027",
                                        "population": None,
                                        "qualification": None,
                                        "academic_year": None,
                                    },
                                    "accessed_on": "2026-09-20",
                                    "source_type": "official",
                                }
                            ],
                        }
                    ],
                    "review": {
                        "status": "human_verified",
                        "prepared_by": "test",
                        "reviewer": "test",
                        "verified_on": "2026-09-21",
                        "notes": "test fixture",
                    },
                }
            ],
        }
    )


async def _probe_one(tmp_path: Path, pages: dict[str, str], url: str, excerpt: str):
    corpus = tmp_path / "corpus"
    for rel, html in pages.items():
        path = corpus / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
    target = Target("example", "ielts.overall", 6.5, url, excerpt)
    async with Fetcher(tmp_path / "cache", offline=True, corpus_dir=corpus) as fetcher:
        return await probe(target, fetcher)


class TestTheFourVerdicts:
    @pytest.mark.asyncio
    async def test_a_plainly_stated_requirement_is_recovered(self, tmp_path):
        found = await _probe_one(
            tmp_path,
            {"uni/cs.html": _PLAIN},
            "fixture://uni/cs.html",
            "IELTS Academic overall band score of 6.5",
        )
        assert found.verdict == RECOVERED

    @pytest.mark.asyncio
    async def test_a_requirement_in_a_table_is_value_missing(self, tmp_path):
        """The words reach us and no pattern fires — that is the patterns, and
        it is the failure a table produces."""
        found = await _probe_one(
            tmp_path,
            {"uni/cs.html": _AS_A_TABLE},
            "fixture://uni/cs.html",
            "IELTS (Academic) 6.5",
        )
        assert found.verdict == VALUE_MISSING
        assert "quoted words are in our text" in found.detail

    @pytest.mark.asyncio
    async def test_a_page_that_never_says_it_is_text_missing(self, tmp_path):
        """Either the content never reached us, or the reviewer read a
        different page. Both are a different problem from the patterns."""
        found = await _probe_one(
            tmp_path,
            {"uni/cs.html": _SILENT},
            "fixture://uni/cs.html",
            "IELTS Academic overall band score of 6.5",
        )
        assert found.verdict == TEXT_MISSING

    @pytest.mark.asyncio
    async def test_an_unreadable_page_says_so_rather_than_blaming_extraction(self, tmp_path):
        found = await _probe_one(tmp_path, {}, "fixture://uni/gone.html", "anything")
        assert found.verdict == FETCH_FAILED


class TestComparingTheReviewersWords:
    def test_table_cells_joined_with_spaces_still_count_as_present(self):
        """The certified corpus says so in its own notes: "Table cells joined
        with spaces for review"."""
        assert excerpt_is_present(
            "non-EU/EEA students 01 May 2027",
            "Deadlines\nnon-EU/EEA students\n01 May 2027\n01 September 2027",
        )

    def test_punctuation_and_case_do_not_decide(self):
        assert excerpt_is_present("IELTS Academic: 6.5!", "ielts academic 6 5")

    def test_absent_words_are_absent(self):
        assert not excerpt_is_present("IELTS 6.5", "The programme lasts three years.")

    def test_an_empty_excerpt_is_never_present(self):
        """A label with no quoted words proves nothing either way."""
        assert not excerpt_is_present("", "anything at all")

    def test_the_words_must_be_in_order(self):
        assert not excerpt_is_present("6.5 IELTS overall", "IELTS overall 6.5")


class TestReadingTheCorpus:
    def test_every_target_names_a_page_and_a_fact(self):
        dataset = _dataset("https://uni.edu/cs", "IELTS 6.5")
        found = targets(dataset)
        assert [(t.case_id, t.key, t.url) for t in found] == [
            ("example", "ielts.overall", "https://uni.edu/cs")
        ]

    def test_a_label_with_no_evidence_is_not_a_target(self):
        """Most certified labels are UNKNOWN by design; they name no page."""
        dataset = _dataset("https://uni.edu/cs", "IELTS 6.5")
        dataset.cases[0].labels[0].evidence = []
        assert targets(dataset) == []

    def test_the_summary_counts_every_verdict(self):
        from evaluation.research.oracle import Finding

        text = summarise(
            [
                Finding("a", "ielts.overall", "u", RECOVERED),
                Finding("b", "deadline", "u", VALUE_MISSING),
                Finding("c", "tuition", "u", TEXT_MISSING),
            ]
        )
        assert "3 certified facts" in text
        assert f"{RECOVERED:14} 1" in text
        assert f"{VALUE_MISSING:14} 1" in text


class _HangingFetcher:
    async def get(self, url):
        import asyncio

        await asyncio.sleep(3600)


@pytest.mark.asyncio
async def test_a_hung_page_times_out_instead_of_stalling_the_run():
    target = Target("example", "ielts.overall", 6.5, "https://example.edu/x", "IELTS 6.5")
    finding = await bounded_probe(target, _HangingFetcher(), seconds=0.05)
    assert finding.verdict == TIMED_OUT

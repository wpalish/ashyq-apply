"""V2-10b — the retrieval probe's logic, driven by the fake provider.

The probe itself calls a paid API; these tests never do. What is pinned here
is the arithmetic and the opt-in guard, so a measurement nobody can rerun
cannot quietly become the number everyone quotes.
"""

from __future__ import annotations

import json

import pytest

from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import queries_for
from evaluation.research.search_probe import (
    QUERIES_PER_CASE,
    _intake_year,
    _intent,
    main,
    probe_case,
    run,
)

CASE = {
    "id": "nu",
    "university": "Nazarbayev University",
    "domain": "nu.edu.kz",
    "request": {"degree": "bachelor", "field": "computer science", "intake": "fall 2027"},
    "programme_urls": ["https://nu.edu.kz/programmes/bsc-computer-science"],
}


def a_provider(urls):
    corpus = {q.text: list(urls) for q in queries_for(_intent(CASE), budget=99)}
    return FakeSearchProvider(corpus)


class TestTheIntentComesFromTheSignedCase:
    def test_the_intake_year_is_parsed_from_the_requested_scope(self):
        assert _intake_year({"intake": "fall 2027"}) == 2027
        assert _intake_year({"intake": ""}) is None
        assert _intake_year({"intake": "autumn"}) is None

    def test_the_intent_carries_the_cases_own_scope(self):
        intent = _intent(CASE)

        assert intent.domain == "nu.edu.kz"
        assert intent.field == "computer science"
        assert intent.intake_year == 2027


class TestTheMeasurement:
    async def test_a_found_page_records_its_position(self):
        provider = a_provider(
            [
                ("https://nu.edu.kz/news/cs", "News", ""),
                ("https://nu.edu.kz/programmes/bsc-computer-science", "BSc Computer Science", ""),
            ]
        )

        probe = await probe_case(provider, CASE)

        assert probe.correct_position is not None
        assert probe.candidates >= 1

    async def test_a_page_that_never_appears_is_not_reachable(self):
        probe = await probe_case(a_provider([("https://nu.edu.kz/about", "About", "")]), CASE)

        assert probe.correct_position is None

    async def test_urls_are_canonicalised_before_comparison(self):
        """A tracking parameter must not read as a different page."""
        provider = a_provider(
            [("https://nu.edu.kz/programmes/bsc-computer-science?utm_source=x", "BSc CS", "")]
        )

        probe = await probe_case(provider, CASE)

        assert probe.correct_position == 1

    async def test_the_top_candidate_is_put_through_the_identity_check(self):
        provider = a_provider(
            [("https://nu.edu.kz/programmes/bsc-computer-science", "BSc Computer Science", "")]
        )

        probe = await probe_case(provider, CASE)

        assert probe.top_identity
        assert probe.top_applies_to_intake

    async def test_a_provider_outage_is_reported_as_an_outage(self):
        """Not as a case that found nothing — those want different fixes."""
        probe = await probe_case(FakeSearchProvider({}, fail_with="quota"), CASE)

        assert probe.candidates == 0
        assert probe.failed_queries == probe.queries_run

    async def test_the_run_totals_add_up(self):
        provider = a_provider([("https://nu.edu.kz/programmes/bsc-computer-science", "BSc CS", "")])

        report = await run(provider, {"version": "test", "cases": [CASE, CASE]})

        assert report["scored_cases"] == 2
        assert report["retrieval_ceiling"] == 2
        assert report["correct_at_rank_one"] == 2
        assert report["provider"] == "fake"

    async def test_a_case_with_no_signed_url_is_not_scored(self):
        """Counting it would blame retrieval for a gap in the corpus."""
        report = await run(
            a_provider([]), {"version": "t", "cases": [{**CASE, "programme_urls": []}]}
        )

        assert report["scored_cases"] == 0


class TestItCannotBeRunByAccident:
    def test_it_refuses_without_the_live_flag(self):
        with pytest.raises(SystemExit, match="--live"):
            main(["--dataset", "x.json"])

    def test_it_refuses_without_a_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("UNIMATCH_EXA_API_KEY", raising=False)
        monkeypatch.delenv("EXA_API_KEY", raising=False)

        with pytest.raises(SystemExit, match="UNIMATCH_EXA_API_KEY"):
            main(["--dataset", str(tmp_path / "x.json"), "--live"])

    def test_the_cost_of_a_run_is_stated_in_the_code(self):
        """A reader should be able to price a run before starting one."""
        assert QUERIES_PER_CASE == 6


class TestTheCommittedResult:
    def test_it_matches_the_shape_this_module_produces(self):
        from pathlib import Path

        stored = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "evaluation/research/baseline/search_probe.exa.json"
            ).read_text(encoding="utf-8")
        )

        assert stored["provider"] == "exa"
        assert stored["scored_cases"] == 10
        assert stored["retrieval_ceiling"] == 9
        assert stored["correct_at_rank_one"] == 2
        assert stored["cases_with_no_candidates"] == 0


class TestTheCliWiring:
    def test_it_writes_and_prints_the_report(self, tmp_path, monkeypatch, capsys):
        """Covers the entry point without letting it near the network."""
        import evaluation.research.search_probe as module

        dataset = tmp_path / "d.json"
        dataset.write_text(json.dumps({"version": "test", "cases": [CASE]}), encoding="utf-8")
        out = tmp_path / "out.json"

        monkeypatch.setenv("UNIMATCH_EXA_API_KEY", "not-a-real-key")
        monkeypatch.setattr(
            "app.adapters.search.exa.ExaSearchProvider",
            lambda key: a_provider(
                [("https://nu.edu.kz/programmes/bsc-computer-science", "BSc CS", "")]
            ),
        )

        module.main(["--dataset", str(dataset), "--out", str(out), "--live"])

        written = json.loads(out.read_text(encoding="utf-8"))
        assert written["retrieval_ceiling"] == 1
        assert json.loads(capsys.readouterr().out) == written

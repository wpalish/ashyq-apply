"""V2-14 — what ranking alone could achieve.

The measurement is small; the decision it supports is not. If a reranker's
headroom is zero, then comparing rerankers measures nothing and buying one
buys nothing, so these tests pin the arithmetic rather than trust it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.research.ceiling import CaseCeiling, CeilingReport, compute_ceiling, main

ROOT = Path(__file__).resolve().parents[1] / "evaluation/research"


def a_dataset(*cases) -> dict:
    return {
        "version": "test",
        "cases": [{"id": cid, "programme_urls": list(urls)} for cid, urls in cases],
    }


def a_capture(*observations) -> dict:
    return {
        "observations": [{"case_id": cid, "ranked_urls": list(urls)} for cid, urls in observations]
    }


class TestTheArithmetic:
    def test_a_correct_page_in_the_set_is_reachable_and_its_position_is_recorded(self):
        report = compute_ceiling(
            a_dataset(("x", ["https://a.test/cs"])),
            a_capture(("x", ["https://a.test/news", "https://a.test/cs"])),
        )

        assert report.cases[0].correct_position == 2
        assert report.cases[0].reachable
        assert not report.cases[0].already_first
        assert report.ceiling == 1
        assert report.headroom == 1

    def test_a_page_already_first_leaves_no_headroom(self):
        """A reranker cannot improve on first place, which is the whole finding."""
        report = compute_ceiling(
            a_dataset(("x", ["https://a.test/cs"])), a_capture(("x", ["https://a.test/cs"]))
        )

        assert report.already_correct == 1
        assert report.headroom == 0

    def test_an_absent_page_is_unreachable_by_any_ordering(self):
        report = compute_ceiling(
            a_dataset(("x", ["https://a.test/cs"])), a_capture(("x", ["https://a.test/news"]))
        )

        assert report.cases[0].correct_position is None
        assert report.ceiling == 0

    def test_urls_are_canonicalised_on_both_sides(self):
        """A trailing slash or a tracking parameter must not read as a miss."""
        report = compute_ceiling(
            a_dataset(("x", ["https://a.test/cs/"])),
            a_capture(("x", ["https://a.test/cs?utm_source=mail"])),
        )

        assert report.cases[0].already_first

    def test_the_best_position_is_taken_when_several_correct_pages_appear(self):
        report = compute_ceiling(
            a_dataset(("x", ["https://a.test/one", "https://a.test/two"])),
            a_capture(("x", ["https://a.test/two", "https://a.test/one"])),
        )

        assert report.cases[0].correct_position == 1

    def test_a_case_with_no_signed_answer_is_not_scored_at_all(self):
        """Counting it as a miss would blame retrieval for a gap in the corpus."""
        report = compute_ceiling(a_dataset(("x", [])), a_capture(("x", ["https://a.test/cs"])))

        assert report.scored == 0
        assert report.cases == ()

    def test_empty_candidate_sets_are_counted_separately(self):
        """No candidates and wrong candidates are different failures."""
        report = compute_ceiling(
            a_dataset(("x", ["https://a.test/cs"]), ("y", ["https://b.test/cs"])),
            a_capture(("x", []), ("y", ["https://b.test/news"])),
        )

        assert report.retrieved_nothing == 1
        assert report.scored == 2


class TestTheRealMeasurement:
    def _live(self) -> CeilingReport:
        return compute_ceiling(
            json.loads((ROOT / "data/ground_truth.reviewed.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "baseline/capture.json").read_text(encoding="utf-8")),
        )

    def test_the_committed_result_matches_a_fresh_computation(self):
        stored = json.loads((ROOT / "baseline/ceiling.reviewed.json").read_text(encoding="utf-8"))

        assert self._live().to_dict() == stored

    def test_no_reranker_has_any_headroom_on_the_current_capture(self):
        """The finding this whole step exists to record.

        If this ever fails because headroom rose, that is good news and V2-14
        becomes worth doing. Update RERANKER_CEILING.md rather than the
        assertion.
        """
        report = self._live()

        assert report.scored == 10
        assert report.ceiling == 1
        assert report.already_correct == 1
        assert report.headroom == 0

    def test_the_recall_failure_is_retrieval_not_ranking(self):
        report = self._live()

        assert report.ceiling == report.already_correct
        assert report.retrieved_nothing == 3


class TestTheCli:
    def test_it_writes_the_report_and_prints_it(self, tmp_path, capsys):
        out = tmp_path / "ceiling.json"

        main(
            [
                "--dataset",
                str(ROOT / "data/ground_truth.reviewed.json"),
                "--capture",
                str(ROOT / "baseline/capture.json"),
                "--out",
                str(out),
            ]
        )

        written = json.loads(out.read_text(encoding="utf-8"))
        assert written["headroom_for_any_reranker"] == 0
        assert json.loads(capsys.readouterr().out) == written

    def test_it_requires_both_inputs(self):
        with pytest.raises(SystemExit):
            main(["--dataset", "x.json"])

    def test_a_case_ceiling_reports_reachability_directly(self):
        assert CaseCeiling("x", 3, 2).reachable
        assert not CaseCeiling("x", 3, None).reachable

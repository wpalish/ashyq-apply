"""The evidence generator has to be right about what it observed.

Three defects, each of which made the artifact quietly wrong rather than
loudly broken:

  - `frontend_tests` was `null`. `run()` kept only the last line of output, and
    vitest's last line is "Duration 779ms (...)" — the count is three lines
    above it. A missing number reads as "not measured" when it was measured.
  - The canary provenance was an absolute path into a scratch directory that
    exists on one machine for one session. Nobody else can check it.
  - `container_runtime` was hardcoded to `not_run`. That was true when it was
    written and false the moment CI ran the gate, and an artifact asserting a
    result it never observed is the exact thing this file exists to prevent.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.release_evidence import (
    GENERATED_OUTPUTS,
    canary_summary,
    count_tests,
    portable_path,
)


class TestCountingWhatTheToolPrinted:
    def test_a_pytest_summary_is_read(self):
        assert count_tests("1852 passed, 1 warning in 40.81s") == 1852

    def test_a_vitest_summary_is_read_even_when_it_is_not_the_last_line(self):
        """The defect: vitest ends with a duration, not a count."""
        output = "\n".join(
            [
                " Test Files  7 passed (7)",
                "      Tests  60 passed (60)",
                "   Start at  06:47:52",
                "   Duration  779ms (transform 163ms, setup 467ms)",
            ]
        )
        assert count_tests(output) == 60

    def test_a_failing_run_reports_no_count_rather_than_a_wrong_one(self):
        assert count_tests("3 failed, 1849 passed in 40.81s") is None

    def test_nothing_is_invented_from_empty_output(self):
        assert count_tests("") is None
        assert count_tests("Killed") is None


class TestProvenanceTravels:
    def test_a_path_inside_the_repository_is_recorded_relative(self):
        root = Path(__file__).resolve().parent.parent.parent
        assert portable_path(root / "artifacts" / "x.json") == "artifacts/x.json"

    def test_a_path_outside_the_repository_keeps_only_its_name(self):
        """An absolute scratch path names a directory that exists on one
        machine for one session. Its basename is the part anyone can use."""
        recorded = portable_path(Path("/private/tmp/claude-501/abc/final14/run1/canary.json"))
        assert "/private/tmp" not in recorded
        assert "claude-501" not in recorded
        assert recorded.endswith("canary.json")


class TestThreeRunsMustLookLikeThreeRuns:
    """`portable_path` reduced every run to its basename.

    The canary writes `run1/canary-2026-08-29.json`, `run2/…`, `run3/…` — three
    files with one name. Recording only the basename put three identical rows
    in the artifact, so a document saying "three independent runs at this
    commit gave 8, 8, 8" was indistinguishable, in the evidence, from one file
    counted three times. The claim being *true* is not the point: the artifact
    could not support it either way.
    """

    @staticmethod
    def _write(directory: Path, run: str, rows: list[dict]) -> None:
        import json

        (directory / run).mkdir(parents=True, exist_ok=True)
        (directory / run / "canary-2026-08-29.json").write_text(json.dumps(rows))

    def test_each_run_is_named_by_its_own_path_and_digest(self, tmp_path: Path):
        found = {"program_page_found": True, "claims": 3, "completeness": 0.2}
        self._write(tmp_path, "run1", [found])
        self._write(tmp_path, "run2", [found, found])
        self._write(tmp_path, "run3", [found, found, found])

        summary = canary_summary(tmp_path)
        files = [r["file"] for r in summary["runs"]]

        assert files == [
            "run1/canary-2026-08-29.json",
            "run2/canary-2026-08-29.json",
            "run3/canary-2026-08-29.json",
        ], "the runs are not distinguishable in the record"
        assert len({r["sha256"] for r in summary["runs"]}) == 3
        assert all(len(r["sha256"]) == 64 for r in summary["runs"])
        assert summary["runs_supplied"] == 3
        assert summary["distinct_run_files"] == 3

    def test_the_same_file_three_times_is_reported_as_one(self, tmp_path: Path):
        """The failure mode this exists to expose, made explicit.

        Identical bytes in three places is a legitimate thing to record — it is
        just not three independent runs, and the artifact now says which it is
        rather than leaving a reader to assume.
        """
        same = [{"program_page_found": True, "claims": 1, "completeness": 0.1}]
        for run in ("run1", "run2", "run3"):
            self._write(tmp_path, run, same)

        summary = canary_summary(tmp_path)
        assert summary["runs_supplied"] == 3
        assert summary["distinct_run_files"] == 1


class TestTheTreeStateSaysSomething:
    def test_the_artifact_and_the_rendered_documents_count_as_generated(self):
        """The generator writes these, so their being modified during a run is
        the run, not a source change. Listing them separately is what lets the
        source question be asked at all."""
        assert "artifacts/release-evidence.json" in GENERATED_OUTPUTS
        assert any(p.startswith("docs/evidence/") for p in GENERATED_OUTPUTS)

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

from scripts.release_evidence import count_tests, portable_path


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

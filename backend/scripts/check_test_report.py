#!/usr/bin/env python
"""Fail when a test run contains anything other than passes.

Grepping the source for `@pytest.mark.skip` was the check before this, and it
could not see the thing that actually happened: a *runtime* `pytest.skip()`
inside a passing test. The suite reported "1858 passed, 1 skipped" while the
release report, the checklist and gate 26 all said skips were zero.

A skipped test is a test that did not run. In a release gate that is not a
neutral outcome — it is an unmeasured one — so this reads the machine-readable
report and refuses anything that is not a pass.

    python scripts/check_test_report.py junit.xml [more.xml ...]

Handles pytest and Vitest JUnit XML, and Playwright's JSON report.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

#: Outcomes that mean "this test did not assert anything".
UNRUN = ("skipped", "xfail", "xpass", "pending", "flaky")


def from_junit(path: Path) -> tuple[int, list[str]]:
    """(tests, offending descriptions) from a JUnit XML report."""
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
    total, offenders = 0, []
    for suite in suites:
        for case in suite.findall("testcase"):
            total += 1
            for child in case:
                tag = child.tag.lower()
                if tag in ("skipped", "flaky"):
                    reason = (child.get("message") or child.text or "").strip()
                    name = f"{case.get('classname', '')}::{case.get('name', '')}"
                    offenders.append(f"{tag}: {name} — {reason[:160]}")
    return total, offenders


def from_playwright_json(path: Path) -> tuple[int, list[str]]:
    """(tests, offending descriptions) from Playwright's JSON reporter."""
    report = json.loads(path.read_text())
    total, offenders = 0, []

    def walk(suite: dict) -> None:
        nonlocal total
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                total += 1
                status = test.get("status") or test.get("expectedStatus")
                if status in UNRUN:
                    offenders.append(f"{status}: {spec.get('title', '?')}")
        for child in suite.get("suites", []):
            walk(child)

    for suite in report.get("suites", []):
        walk(suite)
    return total, offenders


def main(paths: list[str]) -> int:
    if not paths:
        print("usage: check_test_report.py REPORT [REPORT ...]", file=sys.stderr)
        return 2

    grand_total, all_offenders = 0, []
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            # A missing report is not a pass. It is the absence of evidence
            # that anything ran at all.
            print(f"FAIL: {path} does not exist; no test report to check")
            return 1
        reader = from_playwright_json if path.suffix == ".json" else from_junit
        total, offenders = reader(path)
        grand_total += total
        all_offenders += [f"{path.name}: {o}" for o in offenders]
        print(f"  {path.name}: {total} tests, {len(offenders)} not run")

    if all_offenders:
        print(f"\nFAIL: {len(all_offenders)} test(s) did not run:")
        for offender in all_offenders:
            print(f"  {offender}")
        print(
            "\nA skipped test in a release gate is an unmeasured one. Either it "
            "should run, or its absence should be a documented, asserted "
            "decision rather than a silent skip."
        )
        return 1

    if grand_total == 0:
        print("FAIL: the reports contain no tests at all")
        return 1

    print(f"\nOK: {grand_total} tests, none skipped, xfailed or flaky")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

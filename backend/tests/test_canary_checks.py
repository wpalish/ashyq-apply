"""The canary's own zero-tolerance checks, tested like product code.

`scripts/canary_discovery.py` decides whether a live run produced a false
positive, and "zero false positives" is a release blocker. That makes the check
itself release-critical, and it had never been tested.

It needed testing. The requirement check asked a plain string for attributes no
string has, so it could not pass: every decided requirement was a false
positive. Nobody saw it because for the first ten institutions every live
requirement came back unknown, and the branch was never reached. The eleventh
institution reached it, and the gate accused the product of something it had
not done.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from app.domain.enums import EligibilityStatus
from app.schemas.result import ProgramResult, RequirementCheck

BACKEND = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def canary():
    """The script, imported as a module rather than run as one."""
    spec = importlib.util.spec_from_file_location(
        "canary_discovery", BACKEND / "scripts" / "canary_discovery.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["canary_discovery"] = module
    spec.loader.exec_module(module)
    return module


def result_with(*checks: RequirementCheck) -> ProgramResult:
    return ProgramResult(
        id="r1",
        run_id="run1",
        university="Charles University",
        university_id="cuni",
        country="Czech Republic",
        city="Prague",
        program="Computer Science",
        degree="bachelor",
        intake="2027 fall",
        requirement_checks=list(checks),
    )


def requirement(status: EligibilityStatus, claim_ids: list[str]) -> RequirementCheck:
    return RequirementCheck(
        requirement="Entrance examination",
        published_value=True,
        status=status,
        explanation="Entrance examination is required.",
        claim_ids=claim_ids,
    )


class TestRequirementProvenance:
    def test_a_decided_requirement_that_names_its_claim_is_not_a_false_positive(self, canary):
        """The case that broke the gate: a real requirement, with a real source."""
        result = result_with(
            requirement(EligibilityStatus.PENDING, ["https://cuni.cz/UKEN-329.html"])
        )
        assert canary.false_positives(result, []) == []

    def test_a_decided_requirement_with_no_claim_at_all_is_still_caught(self, canary):
        """The thing the gate is actually for must keep failing."""
        result = result_with(requirement(EligibilityStatus.PENDING, []))
        flagged = canary.false_positives(result, [])
        assert [f["kind"] for f in flagged] == ["requirement_verdict_without_source"]
        assert "Entrance examination" in flagged[0]["detail"]

    def test_an_unconfirmed_requirement_needs_no_source(self, canary):
        """ "Could not confirm" asserts nothing about the applicant to back up."""
        unconfirmed = requirement(EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION, [])
        assert canary.false_positives(result_with(unconfirmed), []) == []

    def test_the_skip_list_names_statuses_that_exist(self, canary):
        """The old list held "unknown" and "needs_clarification", neither of
        which `EligibilityStatus` has ever defined, so nothing was skipped."""
        decided = {EligibilityStatus.MET, EligibilityStatus.GAP, EligibilityStatus.PENDING}
        for status in decided:
            flagged = canary.false_positives(result_with(requirement(status, [])), [])
            assert flagged, f"{status} asserts something and must name a source"

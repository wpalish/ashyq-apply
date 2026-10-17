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


class TestRecallMetrics:
    def test_program_and_category_recall_publish_separate_fractions(self, canary):
        rows = [
            {
                "program_page_found": True,
                "discovered": {
                    "admissions": ["a"],
                    "costs": ["c"],
                    "scholarships": [],
                },
            },
            {
                "program_page_found": False,
                "discovered": {
                    "admissions": ["a"],
                    "costs": [],
                    "scholarships": ["s"],
                },
            },
        ]

        metrics = canary.recall_metrics(rows)

        assert metrics["program"] == {"numerator": 1, "denominator": 2, "target": 0.7}
        assert metrics["category"] == {"numerator": 4, "denominator": 6, "target": 26 / 30}

    def test_empty_batch_never_divides_by_zero_or_claims_success(self, canary):
        metrics = canary.recall_metrics([])

        assert metrics["program"]["numerator"] == 0
        assert metrics["program"]["denominator"] == 0
        assert metrics["category"]["denominator"] == 0

    def test_batch_filter_is_explicit_and_preserves_registry_order(self, canary):
        registry = [
            {"homepage": "https://a.edu", "name": "A"},
            {"homepage": "https://b.edu", "name": "B"},
            {"homepage": "https://c.edu", "name": "C"},
        ]

        selected = canary.select_registry_entries(registry, ["c.edu", "a.edu"])

        assert [entry["name"] for entry in selected] == ["A", "C"]
        with pytest.raises(SystemExit, match="no institution"):
            canary.select_registry_entries(registry, ["missing.edu"])


class TestExplicitEntries:
    """Rule 0: a seed-only university runs without a curated registry entry."""

    async def test_entries_replace_the_registry_and_run_the_no_seed_path(self, canary, monkeypatch):
        from urllib.parse import urlparse

        from app.adapters.base import Candidate
        from app.adapters.discovery.live_discovery import DiscoveryTrace
        from app.catalogue.discovery import CatalogueDiscoveryAdapter
        from app.catalogue.importer import identity_key, stable_id

        entry = {
            "name": "ETH Zurich",
            "country": "Switzerland",
            "city": "Zurich",
            "homepage": "https://ethz.ch/",
        }
        seen: dict[str, object] = {}

        async def heavy_runner(self):
            seen["university_ids"] = list(self.run.university_ids)
            adapter = self._make_discovery_adapter(self._make_fetcher())
            self._candidates = await adapter.discover(self.profile, self.candidate_limit)

        async def discover_one(self, given, profile):
            seen["entry"] = dict(given)
            trace = DiscoveryTrace(
                institution=given["name"], domain=urlparse(given["homepage"]).netloc
            )
            trace.manual_seeds = {k: v for k, v in (given.get("seeds") or {}).items() if v}
            candidate = Candidate(name=given["name"], country=given["country"], city=given["city"])
            return candidate, trace

        async def identity_gate(self, uni, trace):
            pytest.fail("an explicit entry is the established site identity")

        def no_registry(*args, **kwargs):
            pytest.fail("explicit entries never consult the registry selector")

        monkeypatch.setattr(canary.CanaryRunner, "run_to_decision", heavy_runner)
        monkeypatch.setattr(CatalogueDiscoveryAdapter, "_discover_one", discover_one)
        monkeypatch.setattr(CatalogueDiscoveryAdapter, "_identify_site", identity_gate)
        monkeypatch.setattr(canary, "select_registry_entries", no_registry)

        report = await canary.run_canary(None, False, entries=[entry])

        assert report["run_error"] == ""
        assert seen["university_ids"] == [stable_id(identity_key("ETH Zurich", "Switzerland"))]
        assert seen["entry"] == entry
        assert report["batch"] == ["ETH Zurich"]
        [row] = report["institutions"]
        assert row["domain"] == "ethz.ch"
        assert row["discovery_trace"]["manual_seeds"] == {}

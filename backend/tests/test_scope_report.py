"""V2-27 — a scope failure must name its dimension, not just count itself.

Synthetic throughout: no universities, no network, no corpus.
"""

from __future__ import annotations

from evaluation.research.schema import Capture, Dataset
from evaluation.research.scope_report import scope_mismatches, summarise


def _dataset(expected_scope: dict, value=6.5, key="ielts.overall") -> Dataset:
    return Dataset.model_validate(
        {
            "version": "synthetic-1",
            "split": "development",
            "cases": [
                {
                    "id": "case-1",
                    "dataset_version": "synthetic-1",
                    "university": "Example University",
                    "domain": "example.edu",
                    "country": "Nowhere",
                    "site_types": ["synthetic"],
                    "request": {"university": "Example University"},
                    "programme_status": "known",
                    "programme_urls": ["https://example.edu/programme"],
                    "programme_evidence": [
                        {
                            "url": "https://example.edu/programme",
                            "excerpt": "Computer Science",
                            "scope": {"university": "Example University"},
                            "accessed_on": "2026-09-21",
                            "source_type": "official",
                        }
                    ],
                    "review": {
                        "status": "human_verified",
                        "reviewer": "Test",
                        "verified_on": "2026-09-21",
                        "prepared_by": "synthetic fixture",
                        "notes": "synthetic",
                    },
                    "labels": [
                        {
                            "key": key,
                            "status": "known",
                            "value": value,
                            "evidence": [
                                {
                                    "url": "https://example.edu/entry",
                                    "excerpt": "IELTS overall 6.5",
                                    "scope": expected_scope,
                                    "accessed_on": "2026-09-21",
                                    "source_type": "official",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )


def _capture(recorded_scope: dict | None, value=6.5, key="ielts.overall") -> Capture:
    evidence = (
        None
        if recorded_scope is None
        else {
            "url": "https://example.edu/entry",
            "excerpt": "IELTS overall 6.5",
            "scope": recorded_scope,
            "accessed_on": "2026-09-21",
            "source_type": "official",
        }
    )
    return Capture.model_validate(
        {
            "pipeline_sha": "0" * 40,
            "captured_at": "20260921T000000Z",
            "mode": "live",
            "config": {},
            "observations": [
                {
                    "case_id": "case-1",
                    "predictions": [{"key": key, "value": value, "evidence": evidence}],
                }
            ],
        }
    )


SCOPE = {"university": "Example University", "population": "international"}


def test_a_page_that_did_not_say_is_reported_as_silent() -> None:
    found = scope_mismatches(_dataset(SCOPE), _capture({"university": "Example University"}))
    assert [(m.dimension, m.shape) for m in found] == [("population", "silent")]


def test_a_page_that_said_something_else_is_reported_as_differing() -> None:
    found = scope_mismatches(
        _dataset(SCOPE),
        _capture({"university": "Example University", "population": "domestic"}),
    )
    assert [(m.dimension, m.shape) for m in found] == [("population", "differs")]
    assert found[0].recorded == "domestic"


def test_a_claim_with_no_evidence_at_all_is_our_own_gap() -> None:
    """`unrecorded` is the only shape that is purely our bug."""
    found = scope_mismatches(_dataset(SCOPE), _capture(None))
    assert {m.shape for m in found} == {"unrecorded"}
    assert {m.dimension for m in found} == {"university", "population"}


def test_a_matching_scope_reports_nothing() -> None:
    assert scope_mismatches(_dataset(SCOPE), _capture(dict(SCOPE))) == []
    assert "no scope mismatches" in summarise([])


def test_the_summary_counts_by_shape_and_by_dimension() -> None:
    found = scope_mismatches(
        _dataset(SCOPE),
        _capture({"university": "Other University", "population": "domestic"}),
    )
    text = summarise(found)
    assert "by shape:     differs=2" in text
    assert "population (differs)=1" in text


def test_an_unlabelled_prediction_is_not_judged() -> None:
    """The rate only counts known labels; so does this, or it would explain
    a different population of claims than the number describes."""
    assert scope_mismatches(_dataset(SCOPE), _capture(dict(SCOPE), key="tuition")) == []

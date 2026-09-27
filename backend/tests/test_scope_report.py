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


def test_the_same_programme_under_two_titles_is_still_shown() -> None:
    """The diagnostic kept naming these while the scorer counted them wrong,
    and that evidence is what the owner settled on 2026-09-22: the scorer now
    compares programme identity, so they count as matches.

    They stay in this report because a rename is worth seeing — the report
    says which way it is counted rather than implying the old answer.
    """
    from evaluation.research.scope_report import same_programme_under_another_name

    found = scope_mismatches(
        _dataset({"university": "Example University", "programme": "Computer Science"}),
        _capture(
            {
                "university": "Example University",
                "programme": "Bachelor of Computing (Hons) in Computer Science",
            }
        ),
    )
    assert [m.shape for m in found] == ["differs"], "the strings do differ"
    renamed = same_programme_under_another_name(found)
    assert len(renamed) == 1
    text = summarise(found)
    assert "counts these as matches" in text, "the report must not imply the old answer"


def test_a_different_field_is_not_reported_as_a_rename() -> None:
    from evaluation.research.scope_report import same_programme_under_another_name

    found = scope_mismatches(
        _dataset({"university": "Example University", "programme": "Computer Science"}),
        _capture({"university": "Example University", "programme": "BSc Data Science"}),
    )
    assert same_programme_under_another_name(found) == []


def test_the_json_the_workflow_asks_for_is_actually_writable(tmp_path, monkeypatch) -> None:
    """`--json` crashed the live capture run and hid the numbers behind it.

    `Mismatch` is a slotted dataclass, so `m.__dict__` raises AttributeError.
    The report itself had been printed by then, so the failure looked like the
    diagnostic's — it was the serialisation, one line later. The test drives
    the CLI, because that is the part nothing exercised.
    """
    import json
    import sys

    from evaluation.research.scope_report import main

    dataset = _dataset({"university": "Example University", "programme": "Computer Science"})
    capture = _capture({"university": "Example University", "programme": "BSc Data Science"})
    dataset_path = tmp_path / "dataset.json"
    capture_path = tmp_path / "capture.json"
    out = tmp_path / "scope-mismatches.json"
    dataset_path.write_text(dataset.model_dump_json(), encoding="utf-8")
    capture_path.write_text(capture.model_dump_json(), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scope_report",
            "--dataset",
            str(dataset_path),
            "--capture",
            str(capture_path),
            "--json",
            str(out),
        ],
    )
    main()

    written = json.loads(out.read_text(encoding="utf-8"))
    assert written[0]["dimension"] == "programme"
    assert written[0]["shape"] == "differs"


def test_a_case_only_difference_is_not_reported() -> None:
    """The scorer has compared non-programme scope case-blind since 2026-09-23."""
    wanted = {**SCOPE, "intake": "fall 2027"}
    got = {**SCOPE, "intake": "Fall 2027"}
    assert scope_mismatches(_dataset(wanted), _capture(got)) == []

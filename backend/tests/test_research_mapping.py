"""Synthetic identity and evidence checks: no universities, applicants or network."""

import json
import socket

import pytest
from pydantic import ValidationError

from evaluation.research.identities import IdentityMap
from evaluation.research.map_claims import main, map_predictions


def identities():
    return IdentityMap.model_validate(
        {
            "version": "synthetic-1",
            "bindings": [
                {
                    "kind": "award",
                    "source_url": "https://example.edu/award?year=2027",
                    "subject": "Example Award",
                    "key": "scholarships.example",
                    "notes": "Synthetic",
                },
                {
                    "kind": "document",
                    "source_url": "https://example.edu/award?year=2027",
                    "subject": "Essay",
                    "key": "documents.scholarship.example.essay",
                    "notes": "Synthetic scholarship-specific document",
                },
            ],
        }
    )


def claim(kind, value, **overrides):
    return {
        "claim_type": kind,
        "normalized_value": value,
        "source_url": "https://example.edu/award?year=2027",
        "subject_key": "Example Award",
        "original_text_excerpt": "Synthetic evidence.",
        "accessed_at": "2026-09-20T01:00:00Z",
        "program": "Example Programme",
        "official_domain": True,
        **overrides,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_url": "https://other.edu/award?year=2027"},
        {"source_url": "https://example.edu/award?year=2026"},
        {"source_url": "https://example.edu/Award?year=2027"},
        {"subject_key": "Another Award"},
        {"subject_key": None},
    ],
)
def test_identity_cannot_leak_to_another_award_source_or_year(overrides):
    result = map_predictions(
        [claim("scholarship_international_eligible", True, **overrides)],
        identities(),
        "Example University",
    )
    assert result[0].key == "unmapped.scholarship_international_eligible"


def test_existence_needs_consistent_identity_and_never_infers_applicability():
    result = map_predictions(
        [
            claim("scholarship_exists", "Example Award"),
            claim("scholarship_exists", "Other Award"),
        ],
        identities(),
        "Example University",
    )
    assert [(p.key, p.value) for p in result] == [
        ("scholarships.example.exists", True),
        ("unmapped.scholarship_exists", "Other Award"),
    ]
    assert result[0].evidence.scope.programme == "Example Programme"
    assert result[0].evidence.scope.degree is None
    assert result[0].supported is None


def test_coverage_splits_without_inventing_money_or_living_scope():
    result = map_predictions(
        [
            claim(
                "scholarship_coverage",
                {
                    "tuition": "yes",
                    "housing": "partial",
                    "mandatory_fees": "no",
                    "health_insurance": "unknown",
                    "personal": "yes",
                },
            )
        ],
        identities(),
        "Example University",
    )
    assert {p.key: p.value for p in result} == {
        "scholarships.example.coverage.tuition": "yes",
        "scholarships.example.coverage.housing": "partial",
        "scholarships.example.coverage.fees": "no",
        "scholarships.example.coverage.insurance": None,
        "scholarships.example.coverage.personal": "yes",
    }


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"tuition": True},
        {"tuition": {"fraction": 1}},
        {"invented": "yes"},
        {"tuition": "maybe"},
    ],
)
def test_unrecognized_coverage_retains_the_entire_original_claim(value):
    result = map_predictions([claim("scholarship_coverage", value)], identities(), "Example")
    assert len(result) == 1
    assert result[0].key == "unmapped.scholarship_coverage"
    assert result[0].value == value


def test_documents_are_explicitly_scoped_and_atomic():
    result = map_predictions(
        [
            claim("required_document", "Essay"),
            claim("essay_prompt", {"document": "Essay", "word_limit": 250}),
            claim("required_document", "Transcript"),
        ],
        identities(),
        "Example",
    )
    assert [(p.key, p.value) for p in result] == [
        ("documents.scholarship.example.essay.required", True),
        ("documents.scholarship.example.essay.maximum_words", 250),
        ("unmapped.required_document", "Transcript"),
    ]


@pytest.mark.parametrize("value", [True, -1, 0, "250"])
def test_word_limit_is_not_guessed_from_wrong_json_types(value):
    result = map_predictions(
        [claim("essay_prompt", {"document": "Essay", "word_limit": value})], identities(), "Example"
    )
    assert result[0].key == "unmapped.essay_prompt"


def test_duplicate_canonical_identity_and_wrong_namespace_are_rejected():
    raw = identities().model_dump(mode="json")
    raw["bindings"].append(
        {
            **raw["bindings"][0],
            "source_url": "https://example.edu/award/?year=2027#section",
            "key": "scholarships.other",
        }
    )
    with pytest.raises(ValidationError, match="ambiguous"):
        IdentityMap.model_validate(raw)
    raw = identities().model_dump(mode="json")
    raw["bindings"][1]["key"] = "documents.essay"
    with pytest.raises(ValidationError, match="purpose"):
        IdentityMap.model_validate(raw)


def test_production_verification_is_not_human_adjudication_and_capped_quotes_stay_flagged():
    result = map_predictions(
        [
            claim(
                "scholarship_international_eligible",
                True,
                status="verified",
                confidence=1,
                original_text_excerpt="x" * 600,
            )
        ],
        identities(),
        "Example",
    )
    assert result[0].supported is None
    assert result[0].current is None
    assert result[0].evidence.excerpt_truncated is True
    assert str(result[0].evidence.accessed_on) == "2026-09-20"


def test_cli_is_offline_reproducible_and_keeps_inputs(tmp_path, monkeypatch):
    import sys

    raw = tmp_path / "raw.json"
    bindings = tmp_path / "bindings.json"
    output = tmp_path / "predictions.json"
    raw.write_text(json.dumps({"claims": [claim("scholarship_exists", "Example Award")]}))
    bindings.write_text(identities().model_dump_json())
    original = raw.read_bytes()

    def no_network(*args, **kwargs):
        raise AssertionError("Mapping attempted network")

    monkeypatch.setattr(socket, "socket", no_network)
    argv = [
        "map",
        "--raw",
        str(raw),
        "--bindings",
        str(bindings),
        "--university",
        "Example",
        "--out",
        str(output),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    main()
    first = output.read_bytes()
    main()
    assert output.read_bytes() == first
    report = json.loads(first)
    assert report["raw_claim_count"] == report["prediction_count"] == 1
    assert report["unmapped_prediction_count"] == 0
    monkeypatch.setattr(sys, "argv", argv[:-1] + [str(raw)])
    with pytest.raises(SystemExit):
        main()
    assert raw.read_bytes() == original


def test_replay_preserves_operations_and_other_cases_and_rejects_wrong_join(tmp_path, monkeypatch):
    import sys

    from evaluation.research.schema import Capture, Observation, Telemetry

    raw = tmp_path / "raw.json"
    bindings = tmp_path / "bindings.json"
    parent = tmp_path / "capture.json"
    output = tmp_path / "replay.json"
    raw.write_text(
        json.dumps(
            {
                "canary": {"institutions": [{"institution": "Example"}]},
                "claims": [claim("scholarship_exists", "Example Award")],
            }
        )
    )
    bindings.write_text(identities().model_dump_json())
    capture = Capture(
        pipeline_sha="original",
        captured_at="original-time",
        mode="synthetic",
        config={},
        observations=[
            Observation(case_id="one", telemetry=Telemetry(http_fetches=9)),
            Observation(case_id="two", error="TIMEOUT"),
        ],
    )
    parent.write_text(capture.model_dump_json())
    argv = [
        "map",
        "--raw",
        str(raw),
        "--bindings",
        str(bindings),
        "--university",
        "Example",
        "--capture",
        str(parent),
        "--case-id",
        "one",
        "--out",
        str(output),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    main()
    replay = Capture.model_validate_json(output.read_text())
    assert replay.mode == "replay"
    assert replay.pipeline_sha == capture.pipeline_sha
    assert replay.captured_at == capture.captured_at
    assert replay.observations[0].telemetry == capture.observations[0].telemetry
    assert replay.observations[1] == capture.observations[1]
    assert replay.observations[0].predictions[0].key == "scholarships.example.exists"
    assert Capture.model_validate_json(parent.read_text()) == capture
    argv[argv.index("--university") + 1] = "Other university"
    with pytest.raises(SystemExit):
        main()


def test_mapped_unknown_never_increases_critical_coverage():
    from evaluation.research.metrics import score
    from evaluation.research.schema import Capture, Dataset, Observation

    predictions = map_predictions(
        [claim("scholarship_coverage", {"health_insurance": "unknown"})], identities(), "Example"
    )
    dataset = Dataset.model_validate(
        {
            "version": "synthetic",
            "split": "development",
            "cases": [
                {
                    "id": "example",
                    "dataset_version": "synthetic",
                    "university": "Example",
                    "country": "Example",
                    "domain": "example.edu",
                    "site_types": [],
                    "request": {"university": "Example"},
                    "labels": [
                        {"key": "scholarships.example.coverage.insurance", "status": "unknown"}
                    ],
                    "review": {"prepared_by": "synthetic test", "notes": "Synthetic"},
                }
            ],
        }
    )
    capture = Capture(
        pipeline_sha="test",
        captured_at="test",
        mode="synthetic",
        config={},
        observations=[Observation(case_id="example", predictions=predictions)],
    )
    assert score(dataset, capture, allow_drafts=True)["metrics"]["critical_field_coverage"] == {
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
    }


@pytest.mark.parametrize("value", ["unknown", "UNKNOWN"])
def test_direct_policy_unknown_is_also_unanswered(value):
    result = map_predictions([claim("sat_policy", value)], identities(), "Example")
    assert result[0].key == "sat.policy"
    assert result[0].value is None


# --- V2-22b: the capture records the page, not the question -------------------


def a_raw_claim(**over):
    raw = {
        "claim_type": "ielts_min_overall",
        "normalized_value": 6.5,
        "original_text_excerpt": "IELTS overall 6.5",
        "source_url": "https://example.edu/entry",
        "accessed_at": "2026-09-21T00:00:00+00:00",
        "official_domain": True,
        "program": "Computer Science",
        "intake": "fall 2027",
        "academic_year": "2026/27",
    }
    raw.update(over)
    return raw


def test_a_claim_that_states_its_scope_is_captured_with_the_page_s_words():
    from evaluation.research.mapping import evidence_scope

    scope = evidence_scope(
        a_raw_claim(scope={"intake": "Fall 2026", "population": "international"}),
        university="Example University",
        programme="Computer Science",
        degree="bachelor",
    )
    assert scope.intake == "Fall 2026"
    assert scope.population == "international"


def test_a_dimension_the_page_was_silent_on_is_a_gap_not_the_request():
    """The 5/5 wrong-scope rate is made of this exact substitution."""
    from evaluation.research.mapping import evidence_scope

    scope = evidence_scope(
        a_raw_claim(scope={"population": "international"}),
        university="Example University",
        programme="Computer Science",
        degree="bachelor",
    )
    assert scope.intake is None
    assert scope.academic_year is None


def test_a_claim_written_before_scope_existed_is_captured_exactly_as_before():
    """Frozen captures are full of these; re-scoring one must not change."""
    from evaluation.research.mapping import evidence_scope

    scope = evidence_scope(
        a_raw_claim(),
        university="Example University",
        programme="Computer Science",
        degree="bachelor",
    )
    assert scope.intake == "fall 2027"
    assert scope.academic_year == "2026/27"
    assert scope.population is None

"""Adversarial controls for decision-grade scoring and its denominators."""

from copy import deepcopy

import pytest
from pydantic import HttpUrl

from evaluation.research.decision_metrics import (
    GROUPS,
    DecisionReview,
    prediction_id,
    score_decisions,
)
from evaluation.research.schema import Capture, Dataset, Evidence, Prediction


def fixture_inputs():
    scope = {
        "university": "Example",
        "programme": "Computer Science",
        "degree": "bachelor",
        "population": "international",
        "qualification": "attestat",
        "intake": "fall 2027",
        "field": "computer_science",
    }
    evidence = {
        "url": "https://example.edu/admissions",
        "excerpt": "Applicants require an IELTS score of 6.5.",
        "scope": scope,
        "accessed_on": "2026-10-09",
        "source_type": "official",
    }
    labels = [
        {"key": "ielts.overall", "status": "known", "value": 6.5, "evidence": [evidence]},
        {
            "key": "programme.language",
            "status": "known",
            "value": "English",
            "evidence": [{**evidence, "excerpt": "The programme is taught in English."}],
        },
    ]
    case = {
        "id": "a",
        "dataset_version": "test",
        "university": "Example",
        "domain": "example.edu",
        "country": "Test",
        "site_types": ["html"],
        "request": scope,
        "programme_urls": ["https://example.edu/cs"],
        "programme_status": "known",
        "programme_evidence": [evidence],
        "labels": labels,
        "review": {
            "status": "human_verified",
            "prepared_by": "preparer",
            "reviewer": "reviewer",
            "verified_on": "2026-10-09",
            "notes": "Verified fixture",
        },
    }
    dataset = Dataset.model_validate({"version": "test", "split": "development", "cases": [case]})
    predictions = [
        Prediction(
            key=label["key"],
            value=label["value"],
            evidence=Evidence.model_validate(label["evidence"][0]),
        )
        for label in labels
    ]
    capture = Capture.model_validate(
        {
            "pipeline_sha": "frozen",
            "captured_at": "2026-10-09",
            "mode": "synthetic",
            "config": {},
            "observations": [
                {
                    "case_id": "a",
                    "programme_urls": case["programme_urls"],
                    "predictions": predictions,
                }
            ],
        }
    )
    contracts = {"a": {g: ["ielts.overall"] for g in GROUPS}}
    reviews = {
        prediction_id("a", p): DecisionReview("independent", True, True, True) for p in predictions
    }
    return dataset, capture, contracts, reviews


def run(dataset, capture, contracts, reviews, **kwargs):
    return score_decisions(
        dataset, capture, contracts=contracts, reviews=reviews, bootstrap_samples=100, **kwargs
    )


def test_verified_complete_answers_and_identity_gate():
    result = run(*fixture_inputs())
    assert result["metrics"]["recall"]["value"] == 1
    assert result["metrics"]["precision"]["value"] == 1
    assert result["release_eligible"] is False  # Synthetic evidence cannot certify release.
    assert result["metrics"]["recall"]["interval"]["lower"] is None


def test_high_scoring_live_validation_needs_separate_seal_and_cohort_review():
    dataset, capture, contracts, reviews = fixture_inputs()
    dataset.split = "validation"
    capture.mode = "live"
    result = run(dataset, capture, contracts, reviews)
    assert result["point_thresholds_met"] is True
    assert result["release_eligible"] is False
    assert result["release_review_required"] is True


def test_same_domain_cafeteria_citation_does_not_prove_ielts():
    dataset, capture, contracts, reviews = fixture_inputs()
    p = capture.observations[0].predictions[0]
    p.evidence.excerpt = "Our cafeteria opens at noon."
    reviews[prediction_id("a", p)] = DecisionReview("independent", True, True, True)
    result = run(dataset, capture, contracts, reviews)
    assert result["metrics"]["recall"]["value"] == 0
    assert result["metrics"]["precision"]["denominator"] == 2
    assert result["prediction_failures"]["evidence_not_independently_supported"] == 1


@pytest.mark.parametrize(
    "dimension,value",
    [
        ("population", "transfer"),
        ("intake", "fall 2026"),
        ("qualification", None),
        ("programme", "Mechanical Engineering"),
    ],
)
def test_wrong_or_silent_scope_is_not_removed_from_precision(dimension, value):
    dataset, capture, contracts, reviews = fixture_inputs()
    p = capture.observations[0].predictions[0]
    setattr(p.evidence.scope, dimension, value)
    reviews[prediction_id("a", p)] = DecisionReview("independent", True, True, True)
    result = run(dataset, capture, contracts, reviews)
    assert result["metrics"]["precision"]["numerator"] == 1
    assert result["metrics"]["precision"]["denominator"] == 2
    assert result["metrics"]["recall"]["value"] == 0


def test_unknown_and_unlabelled_predictions_stay_in_precision():
    dataset, capture, contracts, reviews = fixture_inputs()
    dataset.cases[0].labels[0].status = "unknown"
    dataset.cases[0].labels[0].value = None
    capture.observations[0].predictions.append(Prediction(key="novel.policy", value="optional"))
    result = run(dataset, capture, contracts, reviews)
    assert result["metrics"]["precision"]["denominator"] == 3
    assert result["cases"][0]["unadjudicated_predictions"] == 2
    assert result["label_statuses"]["unknown"] == 1
    assert result["gold_complete"] is False


def test_missing_case_and_access_failure_remain_recall_misses():
    dataset, capture, contracts, reviews = fixture_inputs()
    second = deepcopy(dataset.cases[0])
    second.id = "missing"
    second.domain = "second.edu"
    dataset.cases.append(second)
    contracts[second.id] = deepcopy(contracts["a"])
    capture.observations[0].error = "PROVIDER_STOP"
    capture.observations[0].predictions = []
    result = run(dataset, capture, contracts, reviews)
    assert result["metrics"]["recall"]["denominator"] == 12
    assert result["metrics"]["recall"]["numerator"] == 0
    assert result["missing_cases"] == ["missing"]
    assert result["access_failed_cases"] == ["a"]


def test_all_required_components_not_any_key():
    dataset, capture, contracts, reviews = fixture_inputs()
    label = deepcopy(dataset.cases[0].labels[0])
    label.key = "ielts.subscore"
    label.value = 6.0
    dataset.cases[0].labels.append(label)
    contracts["a"]["english"].append("ielts.subscore")
    result = run(dataset, capture, contracts, reviews)
    assert result["metrics"]["recall"]["numerator"] == 5
    assert result["cases"][0]["groups"]["english"]["correct"] is False


def test_contradictory_displayed_values_fail_even_with_one_correct():
    dataset, capture, contracts, reviews = fixture_inputs()
    other = deepcopy(capture.observations[0].predictions[0])
    other.value = 7.0
    capture.observations[0].predictions.append(other)
    result = run(dataset, capture, contracts, reviews)
    assert result["metrics"]["recall"]["value"] == 0
    assert result["prediction_failures"]["contradictory_displayed_values"] == 2


@pytest.mark.parametrize("flag", ["current", "conditions_correct", "conflict_resolved"])
def test_independent_currentness_conditions_and_conflict_checks(flag):
    dataset, capture, contracts, reviews = fixture_inputs()
    args = {
        "reviewer": "independent",
        "current": True,
        "conditions_correct": True,
        "conflict_resolved": True,
    }
    args[flag] = False
    reviews[prediction_id("a", capture.observations[0].predictions[0])] = DecisionReview(**args)
    assert run(dataset, capture, contracts, reviews)["metrics"]["recall"]["value"] == 0


def test_production_self_confidence_does_not_replace_independent_review():
    dataset, capture, contracts, _ = fixture_inputs()
    for p in capture.observations[0].predictions:
        p.supported = True
        p.current = True
        p.conflict_visible = False
    result = run(dataset, capture, contracts, {})
    assert result["metrics"]["precision"]["value"] == 0
    assert result["prediction_failures"]["missing_independent_review"] == 2


def test_alternative_source_requires_explicit_support_review_and_value():
    dataset, capture, contracts, reviews = fixture_inputs()
    p = capture.observations[0].predictions[0]
    p.evidence.url = HttpUrl("https://example.edu/english-policy")
    p.evidence.excerpt = "IELTS 6.5 is required for these applicants."
    p.supported = True
    reviews[prediction_id("a", p)] = DecisionReview("independent", True, True, True, True)
    assert run(dataset, capture, contracts, reviews)["metrics"]["recall"]["value"] == 1
    p.evidence.excerpt = "IELTS is accepted."
    reviews[prediction_id("a", p)] = DecisionReview("independent", True, True, True, True)
    assert run(dataset, capture, contracts, reviews)["metrics"]["recall"]["value"] == 0


def test_identity_and_language_are_separate_required_gate():
    dataset, capture, contracts, reviews = fixture_inputs()
    capture.observations[0].programme_urls = []
    assert run(dataset, capture, contracts, reviews)["metrics"]["recall"]["value"] == 0
    capture.observations[0].programme_urls = dataset.cases[0].programme_urls
    capture.observations[0].predictions = capture.observations[0].predictions[:1]
    assert run(dataset, capture, contracts, reviews)["metrics"]["recall"]["value"] == 0


def test_no_exclusion_of_published_gold_as_not_published():
    dataset, capture, contracts, reviews = fixture_inputs()
    with pytest.raises(ValueError, match="cannot be excluded"):
        run(
            dataset,
            capture,
            contracts,
            reviews,
            question_states={"a": {"english": "explicit_not_published_yet"}},
        )


def test_grouped_subjects_and_cluster_resampling_are_deterministic():
    dataset, capture, contracts, reviews = fixture_inputs()
    second = deepcopy(dataset.cases[0])
    second.id = "b"
    second.domain = "another.edu"
    second.request.field = "business_administration"
    dataset.cases.append(second)
    contracts["b"] = deepcopy(contracts["a"])
    first = run(dataset, capture, contracts, reviews)
    second_result = run(dataset, capture, contracts, reviews)
    assert first == second_result
    assert set(first["subjects"]) == {"computer_science", "business_administration"}
    interval = first["metrics"]["recall"]["interval"]
    assert interval["clusters"] == 2
    assert (interval["lower"], interval["upper"]) == (0, 1)


def test_exact_duplicate_answers_cannot_inflate_metrics():
    dataset, capture, contracts, reviews = fixture_inputs()
    capture.observations[0].predictions.append(deepcopy(capture.observations[0].predictions[0]))
    assert run(dataset, capture, contracts, reviews)["metrics"]["precision"]["denominator"] == 2


def test_contract_and_observation_validation():
    dataset, capture, contracts, reviews = fixture_inputs()
    with pytest.raises(ValueError, match="six decision groups"):
        run(dataset, capture, {}, reviews)
    capture.observations.append(deepcopy(capture.observations[0]))
    with pytest.raises(ValueError, match="Duplicate"):
        run(dataset, capture, contracts, reviews)


def test_citation_variants_cannot_rescue_precision_from_a_wrong_answer():
    dataset, capture, contracts, reviews = fixture_inputs()
    observation = capture.observations[0]
    observation.predictions.append(Prediction(key="novel.policy", value="wrong"))
    for i in range(20):
        variant = deepcopy(observation.predictions[0])
        variant.evidence.excerpt += " Source context." * (i + 1)
        observation.predictions.append(variant)
        reviews[prediction_id("a", variant)] = DecisionReview("independent", True, True, True)
    result = run(dataset, capture, contracts, reviews)
    assert result["metrics"]["precision"]["numerator"] == 2
    assert result["metrics"]["precision"]["denominator"] == 3
    assert result["point_thresholds_met"] is False


@pytest.mark.parametrize("review_variant", [False, True])
def test_bad_or_unreviewed_same_value_variant_still_withholds_answer(review_variant):
    dataset, capture, contracts, reviews = fixture_inputs()
    variant = deepcopy(capture.observations[0].predictions[0])
    variant.evidence.excerpt = "The cafeteria opens at noon."
    capture.observations[0].predictions.append(variant)
    if review_variant:
        reviews[prediction_id("a", variant)] = DecisionReview("independent", True, True, True)
    result = run(dataset, capture, contracts, reviews)
    assert result["metrics"]["precision"]["numerator"] == 1
    assert result["metrics"]["precision"]["denominator"] == 2
    assert result["metrics"]["recall"]["value"] == 0


def test_declared_unresolved_conflict_overrides_positive_prediction_review():
    result = run(*fixture_inputs(), question_states={"a": {"english": "unresolved_conflict"}})
    assert result["cases"][0]["groups"]["english"]["source_answerable"] is True
    assert result["cases"][0]["groups"]["english"]["correct"] is False
    assert result["metrics"]["recall"]["value"] == 0
    assert result["metrics"]["precision"]["numerator"] == 1
    assert result["prediction_failures"]["unresolved_group_conflict"] == 1

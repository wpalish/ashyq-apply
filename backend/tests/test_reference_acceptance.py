"""A successful crawl is not evidence that the reviewed facts were recovered."""

from datetime import date

import pytest

from evaluation.research.reference_acceptance import assess
from evaluation.research.schema import Label, Observation, Prediction
from tests.test_research_benchmark import inputs


def reviewed_inputs():
    dataset, capture, evidence = inputs()
    review = dataset.cases[0].review
    review.status = "human_verified"
    review.reviewer = "Synthetic reviewer"
    review.verified_on = date(2026, 9, 20)
    capture.observations = [
        Observation(
            case_id="example",
            predictions=[Prediction(key="ielts.overall", value=6.5, evidence=evidence)],
        )
    ]
    return dataset, capture


def test_exact_supported_fact_passes_without_filling_unknown_labels():
    dataset, capture = reviewed_inputs()
    dataset.cases[0].labels.append(Label(key="tuition", status="unknown"))
    result = assess(dataset, capture)
    assert result["reference_facts_complete"]
    assert result["report"]["metrics"]["claim_recall"]["denominator"] == 1


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("missing", "missing_cases"),
        ("empty", "known_facts_not_recovered"),
        ("error", "capture_errors"),
        ("scope", "wrong_scope_claims"),
        ("value", "incorrect_scored_claims"),
        ("unsupported", "unsupported_claims"),
    ],
)
def test_incomplete_or_incorrect_captures_cannot_pass(fault, reason):
    dataset, capture = reviewed_inputs()
    observation = capture.observations[0]
    prediction = observation.predictions[0]
    if fault == "missing":
        capture.observations = []
    elif fault == "empty":
        observation.predictions = []
    elif fault == "error":
        observation.error = "BENCHMARK_PAGE_BUDGET_EXHAUSTED"
    elif fault == "scope":
        assert prediction.evidence is not None
        prediction.evidence.scope.degree = "master"
    elif fault == "value":
        prediction.value = 7.5
    elif fault == "unsupported":
        prediction.supported = False
    result = assess(dataset, capture)
    assert not result["reference_facts_complete"]
    assert reason in result["reasons"]


def test_a_corpus_without_known_facts_is_not_perfect_recall():
    dataset, capture = reviewed_inputs()
    dataset.cases[0].labels = [Label(key="tuition", status="unknown")]
    assert "no_reviewed_known_facts" in assess(dataset, capture)["reasons"]


def test_unsigned_labels_are_rejected():
    dataset, capture, _ = inputs()
    with pytest.raises(ValueError, match="human verification"):
        assess(dataset, capture)


def test_current_award_aliases_preserve_exact_identity_and_do_not_bind_faqs():
    from evaluation.research.identities import IdentityMap
    from evaluation.research.live import CURRENT_BINDINGS, REVIEWED_BINDINGS

    old = IdentityMap.model_validate_json(REVIEWED_BINDINGS.read_text())
    current = IdentityMap.model_validate_json(CURRENT_BINDINGS.read_text())
    assert current.bindings[: len(old.bindings)] == old.bindings
    for path in ("ug/scholarships", "undergraduate/scholarships-and-awards"):
        url = f"https://www.ntu.edu.sg/admissions/{path}/scholarship-opportunities/detail/nanyang-scholarship"
        assert (
            current.resolve("award", url, "Nanyang Global Scholarship")
            == "scholarships.nanyang_global"
        )
        assert current.resolve("award", url, "ASEAN Undergraduate Scholarship") is None
    assert (
        current.resolve(
            "award",
            "https://www.ntu.edu.sg/admissions/ug/scholarships/faq",
            "Nanyang Global Scholarship",
        )
        is None
    )

"""Corpus corrections round (finish-algorithm ticket 02; owner 2026-10-18, «Все да»).

Eight signed lines: the NTU award URL alias and SAT key (ID-1, see
``test_identity_url_alias``), Imperial's fee population, the fee-period
convention, Uppsala's international deadline, Chula's ISE labels, the prose
gpa labels and Delft's TOEFL twin URLs.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import JsonValue

from evaluation.research import scorecard
from evaluation.research.metrics import adjudicate, values_match
from evaluation.research.schema import Dataset, Evidence, Label, Prediction, Scope

DATA = Path(__file__).resolve().parents[1] / "evaluation/research/data"
YEAR: dict[str, JsonValue] = {"amount": 47800.0, "currency": "GBP"}
SEMESTER: dict[str, JsonValue] = {"amount": 3000.0, "currency": "EUR", "period": "semester"}


def _load(name: str) -> Dataset:
    return Dataset.model_validate_json((DATA / name).read_text(encoding="utf-8"))


def _labels(dataset: Dataset, case_id: str) -> dict[str, Label]:
    case = next(c for c in dataset.cases if c.id == case_id)
    return {label.key: label for label in case.labels}


@pytest.mark.parametrize(
    ("name", "version"),
    [
        ("ground_truth.reviewed11.json", "2026-10-17.reviewed11"),
        ("dev2.draft2.json", "2026-10-17.dev2-draft2"),
        ("dev3.draft2.json", "2026-10-17.dev3-draft2"),
    ],
)
def test_the_signed_corpora_carry_their_new_version(name: str, version: str) -> None:
    assert _load(name).version == version


def test_the_scorecard_scores_the_latest_signed_cohort_by_default() -> None:
    import inspect

    # reviewed11 from 2026-10-18; reviewed12 (the 2026-10-26 twin signatures,
    # tests/test_signed_twins_2026_10_26.py) since.
    assert "ground_truth.reviewed12.json" in inspect.getsource(scorecard.main)


class TestFeePeriod:
    """02-Q4: a fee is labelled as published; amount, currency and period compare."""

    def test_a_fee_with_no_period_is_a_fee_for_the_year(self) -> None:
        assert values_match("tuition", YEAR, YEAR)
        assert values_match("tuition", {**YEAR, "period": "academic_year"}, YEAR)
        assert values_match("mandatory_fees", {**YEAR, "period": "year"}, YEAR)

    def test_a_semester_fee_read_as_published_matches(self) -> None:
        assert values_match("tuition", dict(SEMESTER), SEMESTER)

    def test_the_same_amount_for_another_period_is_another_value(self) -> None:
        unstated: dict[str, JsonValue] = {"amount": 3000.0, "currency": "EUR"}
        assert not values_match("tuition", unstated, SEMESTER)
        assert not values_match("tuition", {**unstated, "period": "academic_year"}, SEMESTER)

    def test_an_annualised_semester_fee_is_a_wrong_value(self) -> None:
        doubled: dict[str, JsonValue] = {"amount": 6000.0, "currency": "EUR"}
        assert not values_match("tuition", doubled, SEMESTER)
        assert not values_match("tuition", {**doubled, "period": "semester"}, SEMESTER)

    def test_other_keys_still_compare_exactly(self) -> None:
        assert not values_match(
            "scholarships.x.coverage.living",
            {"currency": "SGD", "amount": 6500},
            {"currency": "SGD", "amount": 6500, "period": "academic_year"},
        )

    def test_the_verdict_reads_the_period(self) -> None:
        scope = Scope(university="Uni", degree="bachelor")
        evidence = Evidence(
            url="https://www.uni.example/fees",  # type: ignore[arg-type]
            excerpt="EUR 3,000 per semester",
            scope=scope,
            accessed_on=date(2026, 10, 18),
            source_type="official",
        )
        label = Label(key="tuition", status="known", value=SEMESTER, evidence=[evidence])
        hit = adjudicate(Prediction(key="tuition", value=SEMESTER, evidence=evidence), label)
        year = adjudicate(
            Prediction(
                key="tuition", value={"amount": 6000.0, "currency": "EUR"}, evidence=evidence
            ),
            label,
        )
        assert hit.correct and hit.value_matches
        assert not year.value_matches and not year.correct


def test_imperial_fee_is_the_international_row() -> None:
    tuition = _labels(_load("dev3.draft2.json"), "imperial")["tuition"]
    assert tuition.value == {"amount": 47800.0, "currency": "GBP"}
    assert {e.scope.population for e in tuition.evidence} == {"international"}


def test_uppsala_deadline_is_the_international_round() -> None:
    labels = _labels(_load("dev2.draft2.json"), "uppsala")
    deadline, national = labels["deadline"], labels["deadline.eu_national"]
    assert deadline.status == "known" and deadline.value == "2027-01-15"
    assert {e.scope.population for e in deadline.evidence} == {"international"}
    assert national.status == "known" and national.value == "2027-04-15"
    assert {e.scope.population for e in national.evidence} == {"eu_national"}


def test_chula_ise_labels_belong_to_another_programme() -> None:
    labels = _labels(_load("dev3.draft2.json"), "chula")
    ise = [key for key, label in labels.items() if "ise.eng.chula" in label.notes]
    assert sorted(ise) == [
        "english_evidence.duolingo.minimum",
        "english_evidence.toefl_ibt.minimum",
        "ielts.overall",
        "scholarships.ise_foreign.applicability.international",
        "scholarships.ise_foreign.exists",
    ]
    assert all(labels[key].status == "not_applicable" for key in ise)
    assert all(
        "ise.eng.chula" not in str(e.url)
        for label in labels.values()
        if label.status == "known"
        for e in label.evidence
    )


@pytest.mark.parametrize(
    ("name", "case_id"),
    [
        ("ground_truth.reviewed11.json", "ntu"),
        ("dev3.draft2.json", "um"),
        ("dev3.draft2.json", "ucph"),
        ("dev3.draft2.json", "msu"),
    ],
)
def test_prose_gpa_labels_leave_the_denominator(name: str, case_id: str) -> None:
    gpa = _labels(_load(name), case_id)["gpa"]
    assert gpa.status == "unknown" and gpa.value is None


def test_delft_toefl_urls_are_twins() -> None:
    toefl = _labels(_load("ground_truth.reviewed11.json"), "delft")[
        "english_evidence.toefl_ibt.minimum"
    ]
    urls = {str(e.url).rstrip("/").rsplit("/", 1)[-1] for e in toefl.evidence}
    assert urls == {"1-admission-requirements", "admission-requirements"}
    assert toefl.value == 90


def test_ntu_sat_label_is_the_international_section() -> None:
    sat = _labels(_load("ground_truth.reviewed11.json"), "ntu")["english_evidence.sat.minimum"]
    assert sat.value == 1250
    assert {e.scope.population for e in sat.evidence} == {"international"}

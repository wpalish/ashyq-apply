"""The claim_recall ceiling: which certified facts any claim could ever match."""

from __future__ import annotations

from pathlib import Path

from evaluation.research.expressibility import (
    NO_CLAIM_TYPE,
    REACHABLE,
    UNBOUND,
    UNSUPPORTED_FIELD,
    load_bindings,
    reach,
    report,
)
from evaluation.research.schema import Dataset

_DATA = Path(__file__).resolve().parents[1] / "evaluation" / "research" / "data"
_BINDINGS = {"scholarships.nanyang_global": "award", "documents.admission.transcript": "document"}


def test_a_directly_mapped_key_is_reachable():
    assert reach("ielts.overall", _BINDINGS) == REACHABLE
    assert reach("programme.exists", _BINDINGS) == REACHABLE


def test_a_bound_award_field_the_mapping_carries_is_reachable():
    assert reach("scholarships.nanyang_global.coverage.tuition", _BINDINGS) == REACHABLE
    assert reach("scholarships.nanyang_global.exists", _BINDINGS) == REACHABLE


def test_a_bound_award_field_the_mapping_does_not_carry_says_so():
    assert reach("scholarships.nanyang_global.bond", _BINDINGS) == UNSUPPORTED_FIELD


def test_an_unbound_award_or_document_is_unbound_not_missing():
    assert reach("scholarships.entrance.exists", _BINDINGS) == UNBOUND
    assert reach("documents.programme.supplemental_application.required", _BINDINGS) == UNBOUND


def test_a_key_no_claim_type_produces_is_named():
    assert reach("german.application_minimum", _BINDINGS) == NO_CLAIM_TYPE
    assert reach("programme.language", _BINDINGS) == REACHABLE


def test_the_reviewed_corpus_counts_the_same_population_as_claim_recall():
    """62 known facts is claim_recall's own denominator in every live run."""
    dataset = Dataset.model_validate_json(
        (_DATA / "ground_truth.reviewed.json").read_text(encoding="utf-8")
    )
    rows = report(dataset, load_bindings(_DATA / "identity_bindings.reviewed.json"))
    assert len(rows) == 62
    # 28 with the approved bindings, + 3 teaching languages under one key.
    assert sum(r.verdict == REACHABLE for r in rows) == 31


def test_without_any_bindings_the_ceiling_is_what_live_had_before_2026_09_23():
    """No award or document fact can score without an identity binding."""
    dataset = Dataset.model_validate_json(
        (_DATA / "ground_truth.reviewed.json").read_text(encoding="utf-8")
    )
    rows = report(dataset, {})
    assert sum(r.verdict == REACHABLE for r in rows) == 17

"""Synthetic policy projection and original-content controls; no official test items."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.claim_scope import ClaimScope, RequestedScope
from app.domain.preparation import project_checks
from app.schemas.claim import ClaimOut, Conflict
from app.schemas.result import RequirementCheck

REQUESTED = RequestedScope(
    university="Synthetic", programme="BSc", degree="bachelor", intake="fall 2027"
)


def claim(kind, value, key="claim1", **updates):
    data = {
        "id": key,
        "claim_type": kind,
        "normalized_value": value,
        "source_url": f"https://example.edu/{key}",
        "official_domain": True,
        "accessed_at": datetime.now(UTC),
        "status": "VERIFIED_CURRENT",
        "source_specificity": "program_intake",
        "scope": ClaimScope(
            university="Synthetic", programme="BSc", degree="bachelor", intake="fall 2027"
        ),
    }
    data.update(updates)
    return ClaimOut.model_validate(data)


def check(label, evidence, **updates):
    data = {
        "requirement": label,
        "published_value": evidence.normalized_value,
        "applicant_value": None,
        "status": "PENDING",
        "claim_ids": [evidence.id],
        "explanation": "Keep the original qualification.",
        "published_scope": "Exact source wording",
    }
    data.update(updates)
    return RequirementCheck.model_validate(data)


@pytest.mark.parametrize(
    "component,lessons",
    [("reading", ["ielts-reading-1"]), ("writing", []), ("speaking", []), ("listening", [])],
)
def test_component_gap_is_not_replaced_by_overall_or_unrelated_skill(component, lessons):
    evidence = claim("ielts_min_subscore", {component: 6.5})
    original = check(f"IELTS {component}", evidence, status="GAP", applicant_value=6.0)
    projected = project_checks([original], [evidence], REQUESTED)[0]
    assert projected.requirement_check == original
    assert projected.requirement_check.published_value == {component: 6.5}
    assert projected.lesson_ids == lessons
    assert projected.policy == "required" and projected.evidence_state == "current"


@pytest.mark.parametrize(
    "policy,expected",
    [
        ("optional", "optional"),
        ("test-optional", "optional"),
        ("test-blind", "unknown"),
        ("not considered", "unknown"),
        ("not optional", "unknown"),
    ],
)
def test_optional_is_not_blind_or_not_considered(policy, expected):
    evidence = claim("sat_policy", policy)
    original = check("SAT policy", evidence, status="NOT_APPLICABLE")
    row = project_checks([original], [evidence], REQUESTED)[0]
    assert row.policy == expected and row.requirement_check == original
    assert row.lesson_ids == []


@pytest.mark.parametrize(
    "other_kind,value,expected",
    [
        ("toefl_min_total", 90, "alternatives_unresolved"),
        ("duolingo_min", 120, "alternatives_unresolved"),
        ("english_test_waiver", "English-medium schooling must be confirmed", "waiver_check"),
    ],
)
def test_coexisting_thresholds_or_waiver_do_not_create_maximum_or_prove_a_waiver(
    other_kind, value, expected
):
    ielts = claim("ielts_min_overall", 6.5)
    other = claim(other_kind, value, "claim2")
    original = check("IELTS overall", ielts, status="GAP", applicant_value=6.0)
    row = project_checks([original], [ielts, other], REQUESTED)[0]
    assert row.policy == expected and row.lesson_ids == []
    assert row.requirement_check.published_value == 6.5 and row.requirement_check.status == "GAP"


@pytest.mark.parametrize(
    "test_type", ["academic", "general_training", "ukvi_academic", "one_skill_retake", "online"]
)
def test_overall_claim_does_not_manufacture_test_type_acceptance(test_type):
    overall = claim("ielts_min_overall", 6.5)
    original = RequirementCheck(
        requirement="Accepted IELTS test type",
        published_value=None,
        applicant_value=test_type,
        status="NEEDS_OFFICIAL_CLARIFICATION",
    )
    row = project_checks([original], [overall], REQUESTED)[0]
    assert row.evidence_state == "unknown" and row.policy == "unknown" and row.lesson_ids == []
    assert row.claims == [] and row.requirement_check == original


@pytest.mark.parametrize(
    "mutation",
    [
        "unrecorded",
        "empty",
        "old_cohort",
        "wrong_programme",
        "aggregator",
        "unofficial",
        "unverified",
    ],
)
def test_bare_current_status_cannot_prove_programme_and_intake(mutation):
    evidence = claim("sat_min_total", 1300)
    if mutation == "unrecorded":
        evidence.scope = None
    elif mutation == "empty":
        evidence.scope = ClaimScope()
    elif mutation == "old_cohort":
        evidence.scope = ClaimScope(
            university="Synthetic", programme="BSc", degree="bachelor", intake="fall 2026"
        )
    elif mutation == "wrong_programme":
        evidence.scope = ClaimScope(
            university="Synthetic", programme="BA", degree="bachelor", intake="fall 2027"
        )
    elif mutation == "aggregator":
        evidence.source_specificity = "aggregator"
    elif mutation == "unofficial":
        evidence.official_domain = False
    else:
        evidence.status = "UNVERIFIED"
    row = project_checks([check("SAT total", evidence)], [evidence], REQUESTED)[0]
    assert row.evidence_state == "unknown" and row.lesson_ids == []


def test_unresolved_conflict_is_not_erased_by_preferred_current_claim():
    evidence = claim("sat_min_total", 1300)
    conflict = Conflict(
        claim_type="sat_min_total",
        subject="Synthetic SAT",
        claim_ids=[evidence.id],
        values=[1300, 1400],
        source_urls=[evidence.source_url],
        preferred_claim_id=evidence.id,
        question_for_admissions="Which applies?",
    )
    row = project_checks(
        [check("SAT total", evidence)], [evidence], REQUESTED, conflicts=[conflict]
    )[0]
    assert row.evidence_state == "conflicted" and row.policy == "unknown" and row.lesson_ids == []


def test_unknown_reference_on_an_otherwise_current_page_stays_unknown():
    evidence = claim("sat_min_total", 1300)
    original = check("SAT total", evidence, claim_ids=[evidence.id, "unknown-id"])
    row = project_checks([original], [evidence], REQUESTED)[0]
    assert row.evidence_state == "unknown" and row.claim_ids == [evidence.id, "unknown-id"]


def test_content_answer_integrity_and_public_projection():
    from app.preparation.catalogue import LESSONS, public_lesson

    for lesson in LESSONS:
        assert 1 <= len(lesson.items) <= 20
        assert len({item.id for item in lesson.items}) == len(lesson.items)
        for item in lesson.items:
            choices = {key for key, _ in item.choices}
            assert len(choices) == len(item.choices) and item.correct_choice_id in choices
            assert item.explanation
        public = public_lesson(lesson).model_dump(mode="json")
        assert "correct_choice_id" not in str(public) and "explanation" not in str(public)


@pytest.mark.parametrize(
    "label,lessons",
    [
        ("SAT total", ["sat-math-1", "sat-rw-1"]),
        ("SAT Math", ["sat-math-1"]),
        ("SAT Reading and Writing", ["sat-rw-1"]),
    ],
)
def test_named_sat_skill_links_only_the_corresponding_original_starter(label, lessons):
    evidence = claim("sat_min_total", 1300)
    original = check(label, evidence)
    row = project_checks([original], [evidence], REQUESTED)[0]
    assert row.requirement_check == original and row.lesson_ids == lessons


# Shared-page binding regressions: legacy URLs are document provenance, not claim IDs.
SHARED_PAGE = "https://example.edu/admissions/shared-requirements"


def test_shared_legacy_page_does_not_turn_deadline_or_gpa_into_exam_goals():
    evidence = [
        claim("admission_deadline", "2027-12-01", "deadline", source_url=SHARED_PAGE),
        claim("min_gpa", 3.5, "gpa", source_url=SHARED_PAGE),
        claim("sat_min_total", 1300, "sat", source_url=SHARED_PAGE),
        claim("ielts_min_overall", 6.5, "overall", source_url=SHARED_PAGE),
        claim(
            "ielts_min_subscore", {"reading": 6.5, "writing": 6.5}, "bands", source_url=SHARED_PAGE
        ),
    ]
    originals = [
        check("Admission deadline", evidence[0], claim_ids=[SHARED_PAGE]),
        check("Minimum GPA", evidence[1], claim_ids=[SHARED_PAGE]),
        check("SAT total", evidence[2], claim_ids=[SHARED_PAGE]),
        check("IELTS overall", evidence[3], claim_ids=[SHARED_PAGE]),
        check("IELTS writing", evidence[4], published_value=6.5, claim_ids=[SHARED_PAGE]),
        check("IELTS reading", evidence[4], published_value=6.5, claim_ids=[SHARED_PAGE]),
    ]
    rows = project_checks(originals, evidence, REQUESTED)
    assert [row.requirement_check for row in rows] == originals[2:]
    assert [[item.id for item in row.claims] for row in rows] == [
        ["sat"],
        ["overall"],
        ["bands"],
        ["bands"],
    ]
    assert [row.lesson_ids for row in rows] == [
        ["sat-math-1", "sat-rw-1"],
        ["ielts-reading-1"],
        [],
        ["ielts-reading-1"],
    ]
    assert all(row.claim_ids == [SHARED_PAGE] and row.source_urls == [SHARED_PAGE] for row in rows)
    assert all(row.evidence_state == "current" for row in rows)


@pytest.mark.parametrize("component", ["listening", "reading", "writing", "speaking"])
def test_shared_url_component_binding_does_not_inherit_overall_or_sat(component):
    bands = claim("ielts_min_subscore", {component: 6.5}, "band", source_url=SHARED_PAGE)
    evidence = [
        claim("sat_min_total", 1300, "sat", source_url=SHARED_PAGE),
        claim("ielts_min_overall", 7, "overall", source_url=SHARED_PAGE),
        bands,
    ]
    original = check(f"IELTS {component}", bands, published_value=6.5, claim_ids=[SHARED_PAGE])
    row = project_checks([original], evidence, REQUESTED)[0]
    assert row.claims == [bands] and row.requirement_check == original
    assert row.lesson_ids == (["ielts-reading-1"] if component == "reading" else [])
    assert row.policy == "required" and row.evidence_state == "current"


@pytest.mark.parametrize(
    "label,kind,value,status,policy",
    [
        ("SAT policy", "sat_policy", "optional", "NOT_APPLICABLE", "optional"),
        ("Accepted IELTS test type", "ielts_accepted_types", ["academic"], "PENDING", "unknown"),
        ("TOEFL total", "toefl_min_total", 90, "GAP", "alternatives_unresolved"),
        ("Entrance examination", "entrance_exam_required", True, "PENDING", "unknown"),
    ],
)
def test_native_named_policy_types_only_bind_their_own_claim(label, kind, value, status, policy):
    target = claim(kind, value, "target", source_url=SHARED_PAGE)
    evidence = [
        claim("sat_min_total", 1300, "sat", source_url=SHARED_PAGE),
        claim("ielts_min_overall", 6.5, "overall", source_url=SHARED_PAGE),
        target,
    ]
    original = check(label, target, status=status, claim_ids=[SHARED_PAGE])
    row = project_checks([original], evidence, REQUESTED)[0]
    assert row.claims == [target] and row.requirement_check == original
    assert row.policy == policy and row.evidence_state == "current" and row.lesson_ids == []


@pytest.mark.parametrize("reference", ["url", "id", "id_and_url"])
def test_ambiguous_legacy_url_is_unknown_but_exact_id_does_not_select_its_neighbours(reference):
    target = claim("ielts_min_overall", 6.5, "target", source_url=SHARED_PAGE)
    evidence = [
        target,
        claim("ielts_min_overall", 7, "other-overall", source_url=SHARED_PAGE),
        claim("sat_min_total", 1300, "sat", source_url=SHARED_PAGE),
    ]
    refs = {
        "url": [SHARED_PAGE],
        "id": [target.id],
        "id_and_url": [target.id, SHARED_PAGE],
    }[reference]
    original = check("IELTS overall", target, claim_ids=refs)
    row = project_checks([original], evidence, REQUESTED)[0]
    assert row.requirement_check == original and row.claim_ids == refs
    if reference == "url":
        assert row.claims == [] and row.evidence_state == "unknown" and row.policy == "unknown"
        assert row.lesson_ids == [] and row.source_urls == []
    else:
        assert row.claims == [target] and row.evidence_state == "current"
        assert row.policy == "required" and row.lesson_ids == ["ielts-reading-1"]
        assert row.source_urls == [SHARED_PAGE]


@pytest.mark.parametrize(
    "kind,value,label",
    [
        ("ielts_min_overall", 6.5, "IELTS writing"),
        ("ielts_min_subscore", {"writing": 6.5}, "IELTS reading"),
    ],
)
def test_exact_id_cannot_clear_a_known_different_ielts_requirement(kind, value, label):
    target = claim(kind, value, source_url=SHARED_PAGE)
    original = check(label, target)
    row = project_checks([original], [target], REQUESTED)[0]
    assert row.requirement_check == original and row.claim_ids == [target.id]
    assert row.claims == [] and row.evidence_state == "unknown" and row.lesson_ids == []


def test_unknown_component_and_unresolved_reference_do_not_borrow_shared_page_evidence():
    target = claim("ielts_min_overall", 6.5, source_url=SHARED_PAGE)
    for original in (
        check("IELTS vocabulary", target, claim_ids=[SHARED_PAGE]),
        check("IELTS overall", target, claim_ids=[SHARED_PAGE, "unresolved-reference"]),
    ):
        row = project_checks([original], [target], REQUESTED)[0]
        assert row.requirement_check == original and row.claim_ids == original.claim_ids
        assert row.evidence_state == "unknown" and row.policy == "unknown" and row.lesson_ids == []
    vocabulary = check("IELTS vocabulary", target, claim_ids=[SHARED_PAGE])
    assert project_checks([vocabulary], [target], REQUESTED)[0].claims == []


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("scope", "unknown"),
        ("stale", "stale"),
        ("unverified", "unknown"),
        ("conflict", "conflicted"),
    ],
)
def test_legacy_family_filter_does_not_remove_scope_stale_or_conflict_controls(mode, expected):
    updates = {
        "scope": {
            "scope": ClaimScope(
                university="Other", programme="BSc", degree="bachelor", intake="fall 2027"
            )
        },
        "stale": {"is_stale": True},
        "unverified": {"status": "UNVERIFIED"},
        "conflict": {"status": "CONFLICTING"},
    }[mode]
    target = claim(
        "ielts_min_subscore", {"reading": 6.5}, "band", source_url=SHARED_PAGE, **updates
    )
    other = claim("sat_min_total", 1300, "sat", source_url=SHARED_PAGE)
    original = check("IELTS reading", target, published_value=6.5, claim_ids=[SHARED_PAGE])
    row = project_checks([original], [other, target], REQUESTED)[0]
    assert row.claims == [target] and row.requirement_check == original
    assert row.evidence_state == expected and row.policy == "unknown" and row.lesson_ids == []


@pytest.mark.parametrize("unresolved", [True, False])
def test_legacy_component_binding_preserves_unresolved_conflict_and_resolved_control(unresolved):
    target = claim("ielts_min_subscore", {"reading": 6.5}, "band", source_url=SHARED_PAGE)
    other = claim("sat_min_total", 1300, "sat", source_url=SHARED_PAGE)
    conflict = Conflict(
        claim_type="ielts_min_subscore",
        subject="Synthetic reading minimum",
        claim_ids=[target.id],
        values=[{"reading": 6.5}, {"reading": 7}],
        source_urls=[SHARED_PAGE],
        preferred_claim_id=target.id,
        question_for_admissions="Which reading minimum applies?",
        unresolved=unresolved,
    )
    original = check("IELTS reading", target, published_value=6.5, claim_ids=[SHARED_PAGE])
    row = project_checks([original], [other, target], REQUESTED, conflicts=[conflict])[0]
    assert row.claims == [target] and row.requirement_check == original
    assert row.evidence_state == ("conflicted" if unresolved else "current")
    assert row.lesson_ids == ([] if unresolved else ["ielts-reading-1"])

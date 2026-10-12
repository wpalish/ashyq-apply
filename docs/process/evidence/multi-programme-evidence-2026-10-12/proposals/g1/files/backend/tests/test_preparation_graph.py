"""G1 PROPOSAL / NOT_APPLIED / NOT_RUN. All values and institutions are synthetic.

Pure tests only: no session, fixtures/corpus, providers, app startup or saved schedules.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.claim_scope import ClaimScope, RequestedScope, Verdict
from app.domain.enums import UserDecision
from app.domain.preparation import project_checks
from app.domain.preparation_graph import (
    GraphSelectionError,
    ProgrammeEvidence,
    build_preparation_graph,
)
from app.schemas.claim import ClaimOut, Conflict
from app.schemas.preparation_graph import (
    LOCKED_NOTICE,
    PolicyGroup,
    PreparationGraph,
    PreparationGraphRequest,
    ProgrammeProjection,
)
from app.schemas.result import DocumentChecklist, DocumentItem, RequirementCheck, Scholarship

RECORDED_AT = datetime(2026, 10, 12, 0, 0, tzinfo=UTC)
SHARED_PAGE = "https://example.edu/shared"


def _claim(key: str, kind: str, value: Any, programme: str = "Programme a", **updates: Any) -> ClaimOut:
    data = {
        "id": key, "claim_type": kind, "normalized_value": value,
        "source_url": f"https://example.edu/{key}", "official_domain": True,
        "accessed_at": RECORDED_AT, "status": "VERIFIED_CURRENT",
        "source_specificity": "program_intake",
        "original_text_excerpt": "Synthetic quotation; no real admissions assertion.",
        "scope": ClaimScope(university="Synthetic", programme=programme,
                            degree="bachelor", intake="fall 2027"),
    }
    data.update(updates)
    return ClaimOut.model_validate(data)


def _check(label: str, source: ClaimOut, **updates: Any) -> RequirementCheck:
    data = {
        "requirement": label, "published_value": source.normalized_value,
        "applicant_value": None, "status": "GAP", "is_hard_filter": True,
        "claim_ids": [source.id], "explanation": "Original synthetic snapshot.",
        "published_scope": "Keep these original display words.",
    }
    data.update(updates)
    return RequirementCheck.model_validate(data)


def _row(key: str, **updates: Any) -> ProgrammeEvidence:
    evidence = _claim(f"claim-{key}", "ielts_min_overall", 6.5, programme=f"Programme {key}")
    data = {
        "profile_id": "case-a", "result_id": key, "run_id": f"run-{key}",
        "user_decision": UserDecision.APPROVED, "university": "Synthetic",
        "programme": f"Programme {key}", "research_access": True,
        "requested_scope": RequestedScope(university="Synthetic", programme=f"Programme {key}",
                                           degree="bachelor", intake="fall 2027"),
        "claims": (evidence,), "requirement_checks": (_check("IELTS overall", evidence),),
    }
    data.update(updates)
    return ProgrammeEvidence(**data)


def _graph(*rows: ProgrammeEvidence, ids: list[str] | None = None) -> PreparationGraph:
    request = PreparationGraphRequest(selected_result_ids=ids or [row.result_id for row in rows])
    return build_preparation_graph("case-a", request, tuple(rows))


def _document(name: str, **updates: Any) -> DocumentItem:
    return DocumentItem.model_validate({
        "name": name, "purpose": "admission", "owner": "applicant",
        "scope": ClaimScope(university="Synthetic", programme="Programme a",
                            degree="bachelor", intake="fall 2027"),
        **updates,
    })


def _checklist(**updates: Any) -> DocumentChecklist:
    return DocumentChecklist.model_validate({
        "result_id": "a", "university": "Synthetic", "program": "Programme a",
        "completeness": "official", **updates,
    })


def test_same_family_preserves_each_source_and_does_not_manufacture_a_maximum_target():
    a = _row("a")
    b_source = _claim("b-high", "ielts_min_overall", 7.0, programme="Programme b")
    b = _row("b", user_decision=UserDecision.MAYBE, claims=(b_source,),
             requirement_checks=(_check("IELTS overall", b_source, status="MET", applicant_value=7.0),))
    graph = _graph(a, b)
    assert [programme.result_id for programme in graph.programmes] == ["a", "b"]
    assert [atom.original_check.published_value for atom in graph.requirements] == [6.5, 7.0]
    assert [atom.original_check.status.value for atom in graph.requirements] == ["GAP", "MET"]
    assert [atom.resolved_claim_ids for atom in graph.requirements] == [["claim-a"], ["b-high"]]
    stream, = graph.exam_workstreams
    assert stream.family == "ielts" and stream.contributing_result_ids == ["a", "b"]
    assert stream.identity_state == "unknown" and stream.edition is None
    assert stream.grouping == "family_only"
    assert graph.projection_state == "partial"
    assert "targets" not in graph.model_fields and "minimum" not in stream.model_fields
    assert "graph_resolved" not in graph.model_fields


def test_output_does_not_replace_the_existing_single_result_exam_projection():
    row = _row("a")
    expected = project_checks(list(row.requirement_checks), list(row.claims), row.requested_scope)[0]
    atom, = _graph(row).requirements
    assert atom.original_check == expected.requirement_check
    assert atom.evidence_state == expected.evidence_state and atom.policy == expected.policy
    assert atom.lesson_id_hints == expected.lesson_ids
    assert atom.proofs[0].claim == expected.claims[0]


@pytest.mark.parametrize("mutation,expected", [
    ("missing_scope", "unknown"), ("wrong_programme", "unknown"),
    ("stale", "stale"), ("conflict", "conflicted"), ("partial", "unknown"),
])
def test_one_current_programme_does_not_upgrade_another_programme(mutation, expected):
    a, b = _row("a"), _row("b")
    if mutation == "missing_scope":
        b = replace(b, claims=(b.claims[0].model_copy(update={"scope": None}),))
    elif mutation == "wrong_programme":
        b = replace(b, claims=(b.claims[0].model_copy(update={"scope": a.claims[0].scope}),))
    elif mutation == "stale":
        b = replace(b, stale_result=True)
    elif mutation == "conflict":
        b = replace(b, conflicts=(Conflict(
            claim_type="ielts_min_overall", subject="Synthetic contradictory requirement",
            claim_ids=[b.claims[0].id], values=[6.5, 7.0], source_urls=[b.claims[0].source_url],
            preferred_claim_id=b.claims[0].id, question_for_admissions="Which applies?",
        ),))
    else:
        b = replace(b, partial=True)
    graph = _graph(a, b)
    assert [programme.evidence_state for programme in graph.programmes] == ["current", expected]
    assert graph.evidence_state != "current" and graph.projection_state == "partial"
    assert graph.requirements[0].original_check == a.requirement_checks[0]
    if mutation != "partial":
        assert graph.requirements[1].evidence_state == expected
        assert graph.requirements[1].lesson_id_hints == []
    if mutation == "wrong_programme":
        assert graph.requirements[1].proofs[0].scope.verdict == Verdict.NO
        assert "scope_mismatch" in graph.requirements[1].unresolved_reasons


def test_locked_payload_does_not_disclose_loaded_premium_evidence_or_source_digests():
    source = _claim("private-claim", "ielts_min_overall", 8.5,
                    source_url="https://example.edu/PRIVATE-PATH")
    row = _row("a", research_access=False, university="PRIVATE-UNIVERSITY",
               programme="PRIVATE-PROGRAMME", claims=(source,),
               requirement_checks=(_check("IELTS overall", source),),
               checklist=_checklist(admission_documents=[_document("PRIVATE-DOCUMENT")]))
    graph = _graph(row)
    serialized = graph.model_dump_json()
    for private in ("private-claim", "PRIVATE-PATH", "PRIVATE-UNIVERSITY", "PRIVATE-PROGRAMME", "PRIVATE-DOCUMENT"):
        assert private not in serialized
    assert graph.requirements == [] and graph.document_actions == []
    assert graph.programmes[0].evidence_state == "locked"
    assert graph.programmes[0].run_id is None and graph.programmes[0].requested_scope is None
    assert graph.source_manifest[0].authoritative_evidence_digest is None
    assert graph.source_manifest[0].result_snapshot_digest is None


def test_mixed_locked_state_is_visible_per_programme_and_cannot_become_current():
    graph = _graph(_row("a"), _row("b", research_access=False))
    assert [programme.evidence_state for programme in graph.programmes] == ["current", "locked"]
    assert graph.evidence_state == "locked" and graph.projection_state == "partial"
    assert [atom.result_id for atom in graph.requirements] == ["a"]


@pytest.mark.parametrize("field,value", [
    ("run_id", "private-run"),
    ("unresolved_questions", [{
        "topic": "PRIVATE-TOPIC", "question": "PRIVATE-QUESTION", "why_it_matters": "PRIVATE-REASON",
    }]),
    ("notice", "PRIVATE-NOTICE"),
    ("unresolved_reasons", ["research_locked", "checklist_partial"]),
    ("evidence_state", "current"),
    ("projection_state", "partial"),
    ("research_access", True),
])
def test_locked_dto_rejects_hidden_payload_and_inconsistent_states_without_the_graph_builder(field, value):
    data = _graph(_row("a", research_access=False)).programmes[0].model_dump(mode="json")
    assert data["notice"] == LOCKED_NOTICE
    data[field] = value
    with pytest.raises(ValidationError):
        ProgrammeProjection.model_validate(data)


@pytest.mark.parametrize("failure", ["unknown", "conflicted"])
def test_malformed_loaded_slice_is_unavailable_without_inventing_an_empty_requirement_set(failure):
    graph = _graph(_row("a", evidence_failure=failure))
    assert graph.programmes[0].projection_state == "unavailable"
    assert graph.programmes[0].evidence_state == failure
    assert graph.requirements == [] and "evidence_unavailable" in graph.programmes[0].unresolved_reasons


def test_empty_stored_checks_are_unknown_and_partial_not_proof_of_no_requirements():
    graph = _graph(_row("a", claims=(), requirement_checks=()))
    assert graph.programmes[0].evidence_state == "unknown"
    assert graph.programmes[0].projection_state == "partial"
    assert "checks_missing" in graph.programmes[0].unresolved_reasons


def test_server_loaded_order_and_unrequested_rows_cannot_change_the_explicit_selection():
    a, b, other = _row("a"), _row("b"), _row("other")
    graph = _graph(other, a, b, ids=["b", "a"])
    assert graph.requested_result_ids == graph.selected_result_ids == ["b", "a"]
    assert [programme.result_id for programme in graph.programmes] == ["b", "a"]
    assert [entry.result_id for entry in graph.source_manifest] == ["b", "a"]
    assert "other" not in graph.selected_result_ids


@pytest.mark.parametrize("ids", [[], ["a", "a"], [" a"], ["a "]])
def test_ambiguous_or_nonexact_selection_is_rejected_instead_of_trimmed(ids):
    with pytest.raises(ValidationError):
        PreparationGraphRequest(selected_result_ids=ids)


@pytest.mark.parametrize("variant", ["missing", "foreign", "rejected", "undecided"])
def test_invalid_explicit_selection_fails_as_a_whole_before_partial_projection(variant):
    a, b = _row("a"), _row("b")
    rows = (a,)
    code = "result_not_found"
    if variant == "foreign":
        rows = (a, replace(b, profile_id="case-other"))
    elif variant in {"rejected", "undecided"}:
        rows = (a, replace(b, user_decision=UserDecision(variant)))
        code = "result_not_selected"
    with pytest.raises(GraphSelectionError) as error:
        _graph(*rows, ids=["a", "b"])
    assert error.value.code == code


def test_non_exam_snapshot_is_retained_separately_without_becoming_an_exam_atom():
    source = _claim("deadline", "admission_deadline", "2027-01-15")
    original = _check("Admission deadline", source, is_hard_filter=False)
    row = _row("a", claims=(source,), requirement_checks=(original,))
    graph = _graph(row)
    assert graph.requirements == [] and graph.exam_workstreams == []
    assert graph.programmes[0].unprojected_checks == [original]
    assert "non_exam_checks_not_projected" in graph.programmes[0].unresolved_reasons


@pytest.mark.parametrize("exact", [False, True])
def test_shared_legacy_url_cannot_select_between_two_compatible_minima(exact):
    first = _claim("first", "ielts_min_overall", 6.5, source_url=SHARED_PAGE)
    second = _claim("second", "ielts_min_overall", 7.0, source_url=SHARED_PAGE)
    original = _check("IELTS overall", first, claim_ids=[first.id, SHARED_PAGE] if exact else [SHARED_PAGE])
    atom, = _graph(_row("a", claims=(first, second), requirement_checks=(original,))).requirements
    assert atom.original_check == original and atom.original_reference_ids == original.claim_ids
    if exact:
        assert atom.resolved_claim_ids == [first.id] and atom.evidence_state == "current"
    else:
        assert atom.resolved_claim_ids == [] and atom.evidence_state == "unknown"
        assert "legacy_url_ambiguous" in atom.unresolved_reasons
        assert atom.lesson_id_hints == []


@pytest.mark.parametrize("kind,value,expected", [
    ("toefl_min_total", 100, "alternatives_unresolved"),
    ("english_test_waiver", "English-medium schooling needs official confirmation", "waiver_check"),
])
def test_co_published_minima_and_waiver_remain_unresolved_without_changing_original_gap(kind, value, expected):
    ielts = _claim("ielts", "ielts_min_overall", 7.0)
    other = _claim("other", kind, value)
    original = _check("IELTS overall", ielts)
    graph = _graph(_row("a", claims=(ielts, other), requirement_checks=(original,)))
    atom, = graph.requirements
    group, = graph.policy_groups
    assert atom.original_check == original and atom.original_check.status.value == "GAP"
    assert atom.policy == expected and atom.lesson_id_hints == []
    assert group.kind == expected and {proof.claim.id for proof in group.context_proofs} == {"ielts", "other"}
    assert "selected_planning_branch" not in group.model_fields and "relation_proof" not in group.model_fields


def test_waiver_precedence_does_not_hide_the_separate_unresolved_alternatives_context():
    ielts = _claim("ielts", "ielts_min_overall", 7.0)
    toefl = _claim("toefl", "toefl_min_total", 100)
    waiver = _claim("waiver", "english_test_waiver", "Synthetic condition requires confirmation")
    original = _check("IELTS overall", ielts)
    graph = _graph(_row("a", claims=(ielts, toefl, waiver), requirement_checks=(original,)))
    atom, = graph.requirements
    assert atom.original_check == original and atom.policy == "waiver_check"
    assert atom.lesson_id_hints == []
    assert [group.kind for group in graph.policy_groups] == ["waiver_check", "alternatives_unresolved"]
    assert len({group.id for group in graph.policy_groups}) == 2
    for group in graph.policy_groups:
        assert group.requirement_ids == [atom.id]
        assert {proof.claim.id for proof in group.context_proofs} == {"ielts", "toefl", "waiver"}
    assert graph.policy_groups[0].unresolved_reasons == ["waiver_requires_review"]
    assert graph.policy_groups[1].unresolved_reasons == ["alternatives_unresolved"]


def test_an_or_word_in_stored_quotes_is_not_a_versioned_official_relation_proof():
    quote = "Synthetic: IELTS or TOEFL accepted for this sample only."
    ielts = _claim("ielts", "ielts_min_overall", 7.0, original_text_excerpt=quote)
    toefl = _claim("toefl", "toefl_min_total", 100, original_text_excerpt=quote)
    graph = _graph(_row("a", claims=(ielts, toefl), requirement_checks=(_check("IELTS overall", ielts),)))
    assert graph.policy_groups[0].kind == "alternatives_unresolved"
    for operator in ("all_of", "any_of"):
        data = graph.policy_groups[0].model_dump(mode="json")
        data["kind"] = operator
        with pytest.raises(ValidationError):
            PolicyGroup.model_validate(data)


def test_generic_english_value_does_not_infer_a_sat_identity_from_an_untyped_dictionary():
    generic = _claim("generic", "english_evidence_minimum", {"test": "SAT", "minimum": 1250})
    graph = _graph(_row("a", claims=(generic,), requirement_checks=(_check("English evidence", generic),)))
    atom, = graph.requirements
    assert atom.family == "unknown" and atom.metric == "unknown"
    assert atom.original_check.published_value == {"test": "SAT", "minimum": 1250}
    assert graph.exam_workstreams == []  # Unknown families cannot pretend to be a shared exam.


def test_overall_and_total_do_not_fill_missing_components_or_create_schedule_targets():
    sat = _claim("sat", "sat_min_total", 1400)
    ielts = _claim("ielts", "ielts_min_overall", 7.0)
    graph = _graph(_row("a", claims=(sat, ielts), requirement_checks=(
        _check("SAT total", sat), _check("IELTS overall", ielts),
    )))
    assert [atom.metric for atom in graph.requirements] == ["total", "overall"]
    assert all(atom.metric not in {"writing", "math", "reading_writing"} for atom in graph.requirements)
    assert {atom.original_check.published_value for atom in graph.requirements} == {1400, 7.0}
    with pytest.raises(ValidationError):
        PreparationGraph.model_validate({**graph.model_dump(mode="json"), "targets": {"math": 700}})


def test_optional_admission_sat_and_required_award_score_keep_separate_purposes_and_subjects():
    optional = _claim("optional", "sat_policy", "optional")
    award_score = _claim("award-score", "scholarship_min_test_score", {"sat": 1450}, subject_key="Synthetic Award")
    award_check = _check("Scholarship SAT score", award_score)
    award = Scholarship(id="award-a", name="Synthetic Award", eligibility_checks=[award_check])
    row = _row("a", claims=(optional, award_score), scholarships=(award,),
               requirement_checks=(_check("SAT policy", optional, status="NOT_APPLICABLE"),))
    atoms = _graph(row).requirements
    assert [(atom.purpose, atom.policy) for atom in atoms] == [("admission", "optional"), ("scholarship", "required")]
    assert [atom.scholarship_id for atom in atoms] == [None, "award-a"]
    assert atoms[1].scholarship_subject == "Synthetic Award"
    assert atoms[1].original_check == award_check and atoms[1].family == "sat"
    assert atoms[1].metric == "unknown"  # Generic award score is not a normalized section rule.
    assert atoms[0].original_check.status.value == "NOT_APPLICABLE"


@pytest.mark.parametrize("subject", [None, "Different Award", ""])
def test_unestablished_award_subject_does_not_borrow_the_programme_or_another_award_claim(subject):
    score = _claim("score", "scholarship_min_test_score", {"sat": 1450}, subject_key=subject)
    award = Scholarship(id="award-a", name="Synthetic Award", eligibility_checks=[_check("Scholarship SAT score", score)])
    graph = _graph(_row("a", claims=(score,), requirement_checks=(), scholarships=(award,)))
    atom, = graph.requirements
    assert atom.evidence_state == "unknown" and atom.resolved_claim_ids == []
    assert atom.policy == "unknown" and "scholarship_subject_unestablished" in atom.unresolved_reasons


def test_numeric_award_summary_without_stored_requirement_checks_does_not_become_a_new_check():
    award = Scholarship(id="award-a", name="Synthetic Award", min_test_scores={"sat": 1450})
    graph = _graph(_row("a", scholarships=(award,)))
    assert all(atom.purpose == "admission" for atom in graph.requirements)
    assert "scholarship_checks_missing" in graph.programmes[0].unresolved_reasons


def test_duplicate_award_names_do_not_create_a_unique_subject_identity():
    score = _claim("score", "scholarship_min_test_score", {"sat": 1450}, subject_key="Shared Award")
    original = _check("Scholarship SAT score", score)
    awards = (
        Scholarship(id="award-a", name="Shared Award", eligibility_checks=[original]),
        Scholarship(id="award-b", name="Shared Award", eligibility_checks=[original]),
    )
    graph = _graph(_row("a", claims=(score,), requirement_checks=(), scholarships=awards))
    assert [atom.scholarship_id for atom in graph.requirements] == ["award-a", "award-b"]
    assert all(atom.evidence_state == "unknown" and atom.resolved_claim_ids == [] for atom in graph.requirements)


def test_a_scholarship_claim_cannot_turn_a_generic_admission_check_into_a_confirmed_goal():
    score = _claim("score", "scholarship_min_test_score", {"sat": 1450}, subject_key="Synthetic Award")
    original = _check("SAT evidence", score)
    atom, = _graph(_row("a", claims=(score,), requirement_checks=(original,))).requirements
    assert atom.original_check == original and atom.evidence_state == "unknown"
    assert atom.policy == "unknown" and atom.lesson_id_hints == []
    assert "requirement_purpose_unestablished" in atom.unresolved_reasons


def test_document_owner_projections_dedupe_only_the_exact_semantic_item():
    common = _document("Statement", prompt_text="Prompt A")
    different_owner = _document("Statement", owner="school", prompt_text="Prompt A")
    different_purpose = _document("Statement", purpose="scholarship", prompt_text="Prompt A")
    different_prompt = common.model_copy(update={"prompt_text": "Prompt B"})
    checklist = _checklist(admission_documents=[common, different_owner, different_prompt],
                           scholarship_documents=[different_purpose], applicant_actions=[common])
    graph = _graph(_row("a", checklist=checklist))
    assert len(graph.document_actions) == 4
    duplicate = next(action for action in graph.document_actions if len(action.original_items) == 2)
    assert duplicate.source_locations == ["admission_documents", "applicant_actions"]
    assert all(action.fulfillment_state == "untracked" and action.action_state == "requires_review" for action in graph.document_actions)


def test_external_offer_prerequisite_is_visible_as_missing_not_fabricated_as_a_checklist_item():
    item = _document("Award essay", purpose="scholarship", depends_on=["admission offer letter"])
    graph = _graph(_row("a", checklist=_checklist(scholarship_documents=[item])))
    action, = graph.document_actions
    dependency, = action.dependencies
    assert dependency.original_name == "admission offer letter" and dependency.resolution == "missing"
    assert dependency.target_document_id is None and dependency.fulfillment_state == "untracked"
    assert "dependency_missing" in action.unresolved_reasons


def test_same_name_with_different_owners_is_ambiguous_and_cannot_pick_a_dependency():
    a = _document("Reference", owner="recommender")
    b = _document("Reference", owner="school")
    child = _document("Package", depends_on=["Reference"])
    graph = _graph(_row("a", checklist=_checklist(admission_documents=[a, b, child])))
    package = next(action for action in graph.document_actions if action.original_item.name == "Package")
    assert package.dependencies[0].resolution == "ambiguous"
    assert package.dependencies[0].target_document_id is None
    assert "dependency_ambiguous" in package.unresolved_reasons


def test_repeated_same_list_documents_are_not_silently_collapsed_into_one_requirement():
    reference = _document("Reference", owner="recommender")
    child = _document("Package", depends_on=["Reference"])
    graph = _graph(_row("a", checklist=_checklist(admission_documents=[reference, reference, child])))
    assert len(graph.document_actions) == 3
    package = next(action for action in graph.document_actions if action.original_item.name == "Package")
    assert package.dependencies[0].resolution == "ambiguous"


def test_unknown_document_scope_cannot_link_an_otherwise_same_name_prerequisite():
    parent = _document("Transcript", scope=None)
    child = _document("Translation", depends_on=["Transcript"])
    graph = _graph(_row("a", checklist=_checklist(admission_documents=[parent, child])))
    translation = next(action for action in graph.document_actions if action.original_item.name == "Translation")
    assert translation.dependencies[0].resolution == "scope_unresolved"
    assert "dependency_scope_unresolved" in translation.unresolved_reasons


def test_document_cycles_and_self_cycles_are_visible_and_cannot_create_a_ready_action():
    items = [
        _document("A", depends_on=["B"]), _document("B", depends_on=["A"]),
        _document("Self", depends_on=["Self"]), _document("Downstream", depends_on=["A"]),
    ]
    graph = _graph(_row("a", checklist=_checklist(admission_documents=items)))
    by_name = {action.original_item.name: action for action in graph.document_actions}
    for name in ("A", "B", "Self"):
        assert by_name[name].dependencies[0].resolution == "cycle"
        assert "dependency_cycle" in by_name[name].unresolved_reasons
    assert by_name["Downstream"].dependencies[0].resolution == "linked"
    assert "dependency_blocked" in by_name["Downstream"].unresolved_reasons
    assert all(action.fulfillment_state == "untracked" for action in graph.document_actions)


def test_a_document_in_another_programme_is_not_a_dependency_candidate():
    child = _document("Package", depends_on=["Transcript"])
    a = _row("a", checklist=_checklist(admission_documents=[child]))
    parent = _document("Transcript", scope=ClaimScope(university="Synthetic", programme="Programme b", degree="bachelor", intake="fall 2027"))
    b = _row("b", checklist=_checklist(result_id="b", program="Programme b", admission_documents=[parent]))
    graph = _graph(a, b)
    package = next(action for action in graph.document_actions if action.original_item.name == "Package")
    assert package.dependencies[0].resolution == "missing"


def test_official_checklist_label_or_legacy_page_url_does_not_confirm_every_document_predicate():
    source = _claim("doc-claim", "required_document", "Transcript", source_url=SHARED_PAGE)
    item = _document("Transcript", scope=None, source_url=SHARED_PAGE, claim_ids=[SHARED_PAGE], needs_apostille=True)
    graph = _graph(_row("a", claims=(_row("a").claims[0], source), checklist=_checklist(admission_documents=[item])))
    action, = graph.document_actions
    assert action.original_item.needs_apostille is True and action.original_item.scope is None
    assert action.evidence_state == "unknown" and action.proofs == []
    assert "document_exact_proof_required" in action.unresolved_reasons
    assert "document_scope_unknown" in action.unresolved_reasons


def test_partial_checklist_and_unresolved_questions_remain_visible():
    checklist = _checklist(completeness="partial", unresolved=[{
        "topic": "Synthetic format", "question": "Which format?", "why_it_matters": "The source did not say.",
    }])
    graph = _graph(_row("a", checklist=checklist))
    programme, = graph.programmes
    assert "checklist_partial" in programme.unresolved_reasons
    assert "checklist_unresolved" in programme.unresolved_reasons
    assert programme.unresolved_questions == checklist.unresolved


def test_citation_order_and_access_time_do_not_change_occurrence_identity_but_source_status_is_fingerprinted():
    first = _claim("first", "ielts_min_overall", 6.5)
    second = _claim("second", "ielts_min_overall", 6.5)
    check = _check("IELTS overall", first, claim_ids=["first", "second"])
    row = _row("a", claims=(first, second), requirement_checks=(check,))
    before = _graph(row)
    changed_check = check.model_copy(update={"claim_ids": ["second", "first"]})
    changed_source = first.model_copy(update={"accessed_at": RECORDED_AT + timedelta(hours=1)})
    after = _graph(replace(row, claims=(second, changed_source), requirement_checks=(changed_check,)))
    assert before.requirements[0].id == after.requirements[0].id
    assert before.requirements[0].resolved_claim_ids == after.requirements[0].resolved_claim_ids
    stale = _graph(replace(row, claims=(first.model_copy(update={"is_stale": True}), second)))
    assert before.requirements[0].id == stale.requirements[0].id
    assert stale.requirements[0].evidence_state == "stale"
    assert before.source_fingerprint != stale.source_fingerprint


def test_projection_does_not_mutate_checks_claims_or_checklist_and_roundtrips_the_wire_contract():
    row = _row("a", checklist=_checklist(admission_documents=[_document("Transcript")]))
    assert row.checklist is not None
    before = (
        [check.model_dump(mode="json") for check in row.requirement_checks],
        [claim.model_dump(mode="json") for claim in row.claims],
        row.checklist.model_dump(mode="json"),
    )
    graph = _graph(row)
    assert before == (
        [check.model_dump(mode="json") for check in row.requirement_checks],
        [claim.model_dump(mode="json") for claim in row.claims],
        row.checklist.model_dump(mode="json"),
    )
    assert PreparationGraph.model_validate_json(graph.model_dump_json()) == graph


def test_schema_refuses_cross_programme_dependency_identity():
    a = _row("a", checklist=_checklist(admission_documents=[_document("Transcript")]))
    parent = _document("Transcript", scope=ClaimScope(university="Synthetic", programme="Programme b", degree="bachelor", intake="fall 2027"))
    b = _row("b", checklist=_checklist(result_id="b", program="Programme b", admission_documents=[parent]))
    data = _graph(a, b).model_dump(mode="json")
    data["document_actions"][0]["dependencies"] = [{
        "original_name": "Transcript", "target_document_id": data["document_actions"][1]["id"],
        "resolution": "linked", "fulfillment_state": "untracked",
    }]
    with pytest.raises(ValidationError):
        PreparationGraph.model_validate(data)


def test_schema_refuses_a_forged_yes_scope_verdict_for_another_programme():
    data = _graph(_row("a")).model_dump(mode="json")
    data["requirements"][0]["proofs"][0]["scope"]["requested"]["programme"] = "Different programme"
    with pytest.raises(ValidationError):
        PreparationGraph.model_validate(data)


def test_schema_refuses_a_changed_selection_receipt_even_with_valid_owned_nodes():
    data = _graph(_row("a"), _row("b")).model_dump(mode="json")
    data["selected_result_ids"] = ["b", "a"]
    with pytest.raises(ValidationError):
        PreparationGraph.model_validate(data)

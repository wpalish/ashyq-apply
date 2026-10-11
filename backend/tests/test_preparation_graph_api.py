"""Native synthetic HTTP controls for owned programme evidence.

Reuse the existing migrated SQLite/private PostgreSQL prep_lab with its
no-lifespan client and IP/DNS refusal.
No live provider, corpus labels, official admissions or score assertions.
"""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import MetaData, event, select

from app.api import routes_preparation_graph as graph_api
from app.domain.enums import PipelineStage
from app.models import (
    ApplicantProfileRow,
    ClaimRow,
    ConflictRow,
    Organization,
    ProgramResultRow,
    ResearchRun,
    StudyScheduleRow,
)
from app.models.base import utcnow
from app.schemas.claim import Claim
from app.schemas.preparation_graph import LOCKED_NOTICE
from app.schemas.preparation_graph_loader import StoredPreparationGraphFields
from app.schemas.result import DocumentChecklist, RequirementCheck, Scholarship
from tests.test_preparation_api import body, full_case, grant, result_with_claim, url
from tests.test_study_schedule_api import write

pytest_plugins = ("tests.test_preparation_api",)


def _selected(lab, *, decision="approved", **kwargs):
    result_id, claim_id, check = result_with_claim(lab, reference="id", **kwargs)
    with lab["factory"]() as session:
        result = session.get(ProgramResultRow, result_id)
        result.user_decision = decision
        session.get(ResearchRun, result.run_id).stage = PipelineStage.COMPLETED.value
        # The payload's copied decision is deliberately not the column authority.
        result.payload = {**result.payload, "user_decision": "rejected"}
        session.commit()
    return result_id, claim_id, check


def _get(lab, ids, *, case=None):
    endpoint = f"/api/profiles/{case or lab['case']}/preparation/graph"
    return lab["client"].get(endpoint, params=[("result_id", key) for key in ids])


def _share_run(lab, first_id, other_ids):
    with lab["factory"]() as session:
        first = session.get(ProgramResultRow, first_id)
        for result_id in other_ids:
            result = session.get(ProgramResultRow, result_id)
            previous_run = result.run_id
            for source in session.query(ClaimRow).filter(ClaimRow.run_id == previous_run).all():
                source.run_id = first.run_id
            result.run_id = first.run_id
        session.commit()


def _foreign_case(lab):
    with lab["factory"]() as session:
        organization = Organization(name="Synthetic foreign tenant", slug=uuid4().hex)
        session.add(organization)
        session.flush()
        owned = session.get(ApplicantProfileRow, lab["case"])
        foreign = ApplicantProfileRow(
            organization_id=organization.id, payload=deepcopy(owned.payload)
        )
        session.add(foreign)
        session.commit()
        return foreign.id


def _capture(lab, callback):
    statements = []

    def record(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(lab["engine"], "before_cursor_execute", record)
    try:
        response = callback()
    finally:
        event.remove(lab["engine"], "before_cursor_execute", record)
    return response, statements


def _snapshot(lab):
    """All native table values, only from the isolated synthetic test database."""
    metadata = MetaData()
    metadata.reflect(bind=lab["engine"])
    with lab["factory"]() as session:
        return {
            name: [
                dict(row)
                for row in session.execute(select(table).order_by(*table.primary_key.columns))
                .mappings()
                .all()
            ]
            for name, table in sorted(metadata.tables.items())
        }


def test_explicit_order_authoritative_decision_and_original_check_receipts_are_preserved(prep_lab):
    full_case(prep_lab)
    first, first_claim, first_check = _selected(prep_lab)
    second, second_claim, second_check = _selected(
        prep_lab, decision="maybe", value=7.0, status="MET"
    )
    response = _get(prep_lab, [second, first])
    assert response.status_code == 200
    graph = response.json()
    assert graph["requested_result_ids"] == graph["selected_result_ids"] == [second, first]
    assert graph["selection_source"] == "server_verified_owned_explicit"
    assert [row["result_id"] for row in graph["programmes"]] == [second, first]
    assert [row["user_decision"] for row in graph["programmes"]] == ["maybe", "approved"]
    assert [row["original_check"] for row in graph["requirements"]] == [second_check, first_check]
    assert [row["resolved_claim_ids"] for row in graph["requirements"]] == [
        [second_claim],
        [first_claim],
    ]
    (group,) = graph["exam_workstreams"]
    assert group["grouping"] == "family_only" and group["identity_state"] == "unknown"
    assert "targets" not in graph and "minimum" not in group


@pytest.mark.parametrize(
    "variant", ["absent", "duplicate", "left_space", "right_space", "too_long", "too_many"]
)
def test_query_selection_is_required_bounded_exact_and_never_silently_trimmed(prep_lab, variant):
    selected, _, _ = _selected(prep_lab)
    ids = {
        "absent": [],
        "duplicate": [selected, selected],
        "left_space": [" " + selected],
        "right_space": [selected + " "],
        "too_long": ["x" * 33],
        "too_many": [uuid4().hex for _ in range(21)],
    }[variant]
    assert _get(prep_lab, ids).status_code == 422


@pytest.mark.parametrize("decision", ["rejected", "undecided", "historical-invalid"])
def test_owned_unselected_decisions_fail_as_a_whole_even_when_research_is_locked(
    prep_lab, decision
):
    approved, _, _ = _selected(prep_lab)
    other, _, _ = _selected(prep_lab, decision=decision)
    response = _get(prep_lab, [approved, other])
    assert response.status_code == 422
    assert response.json() == {"detail": "Only approved or maybe results can be selected"}


def test_missing_and_foreign_result_are_the_same_404_without_a_partial_body(prep_lab):
    full_case(prep_lab)
    approved, _, _ = _selected(prep_lab)
    other, _, _ = _selected(prep_lab)
    foreign_case = _foreign_case(prep_lab)
    with prep_lab["factory"]() as session:
        result = session.get(ProgramResultRow, other)
        session.get(ResearchRun, result.run_id).profile_id = foreign_case
        session.commit()
    for missing in (other, uuid4().hex):
        response = _get(prep_lab, [approved, missing])
        assert response.status_code == 404
        assert response.json() == {"detail": "Result not found"}


def test_case_ownership_is_checked_before_any_result_or_premium_query(prep_lab):
    own, _, _ = _selected(prep_lab)
    foreign_case = _foreign_case(prep_lab)
    for case in (foreign_case, uuid4().hex):
        response, statements = _capture(
            prep_lab, lambda case=case: _get(prep_lab, [own], case=case)
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Applicant case not found"}
        assert not any("program_results" in statement.lower() for statement in statements)


@pytest.mark.parametrize("term", ["absent", "active", "expired"])
def test_locked_path_reads_only_selection_metadata_and_preparation_term_cannot_unlock_it(
    prep_lab, term
):
    if term != "absent":
        grant(prep_lab, end=utcnow() - timedelta(seconds=1) if term == "expired" else None)
    selected, claim_id, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        result = session.get(ProgramResultRow, selected)
        result.university = "PRIVATE-UNIVERSITY"
        result.program = "PRIVATE-PROGRAMME"
        result.payload = {
            "requirement_checks": "PRIVATE-INVALID",
            "unresolved": "PRIVATE-QUESTIONS",
        }
        result.checklist = {"PRIVATE-CHECKLIST": True}
        session.get(ClaimRow, claim_id).payload = {"PRIVATE-CLAIM": True}
        session.commit()
    response, statements = _capture(prep_lab, lambda: _get(prep_lab, [selected]))
    assert response.status_code == 200 and "PRIVATE-" not in response.text
    graph = response.json()
    assert graph["requirements"] == graph["document_actions"] == graph["policy_groups"] == []
    (programme,) = graph["programmes"]
    assert programme["result_id"] == selected and programme["user_decision"] == "approved"
    assert programme["evidence_state"] == programme["projection_state"] == "locked"
    assert programme["run_id"] is None and programme["notice"] == LOCKED_NOTICE
    assert programme["unresolved_questions"] == []
    (manifest,) = graph["source_manifest"]
    assert manifest["run_id"] is None and manifest["authoritative_evidence_digest"] is None
    assert manifest["result_snapshot_digest"] is None and manifest["resolved_claim_ids"] == []
    for statement in statements:
        lowered = statement.lower()
        if lowered.lstrip().startswith("select"):
            columns = re.split(r"\bfrom\b", lowered, maxsplit=1)[0]
            assert not re.search(
                r"program_results\.(payload|checklist|university|program)\b", columns
            )
            assert not re.search(r"\bfrom\s+(claims|conflicts)\b", lowered)


def test_case_full_research_entitlement_is_independent_of_expired_preparation_term(prep_lab):
    grant(prep_lab, end=utcnow() - timedelta(seconds=1))
    full_case(prep_lab)
    selected, _, _ = _selected(prep_lab)
    assert prep_lab["client"].get(url(prep_lab, "access")).json()["allowed"] is False
    graph = _get(prep_lab, [selected]).json()
    assert graph["programmes"][0]["research_access"] is True
    assert graph["requirements"][0]["evidence_state"] == "current"


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("status", "conflicted"),
        ("specificity", "unknown"),
        ("age", "stale"),
        ("superseded", "stale"),
        ("http_url", "unknown"),
        ("unofficial", "unknown"),
        ("scope_missing", "unknown"),
        ("scope_wrong", "unknown"),
        ("profile_changed", "stale"),
    ],
)
def test_authoritative_rows_scope_and_profile_staleness_cannot_be_upgraded_from_payload(
    prep_lab, mode, expected
):
    full_case(prep_lab)
    selected, claim_id, original = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        claim = session.get(ClaimRow, claim_id)
        payload = deepcopy(claim.payload)
        if mode == "status":
            claim.status = "CONFLICTING"
        elif mode == "specificity":
            claim.source_specificity = "unknown"
        elif mode == "age":
            claim.accessed_at = utcnow() - timedelta(days=365)
        elif mode == "superseded":
            claim.status = "SUPERSEDED"
        elif mode == "http_url":
            claim.source_url = "http://example.edu/requirements"
        elif mode == "unofficial":
            payload["official_domain"] = False
        elif mode == "scope_missing":
            payload.pop("scope", None)
        elif mode == "scope_wrong":
            payload["scope"]["intake"] = "fall 2024"
        elif mode == "profile_changed":
            session.get(ApplicantProfileRow, prep_lab["case"]).updated_at = utcnow() + timedelta(
                seconds=1
            )
        claim.payload = payload
        session.commit()
    graph = _get(prep_lab, [selected]).json()
    (atom,) = graph["requirements"]
    assert atom["original_check"] == original and atom["evidence_state"] == expected
    assert atom["policy"] == "unknown" and atom["lesson_id_hints"] == []


def test_column_id_type_url_and_access_time_override_stale_result_claim_copies(prep_lab):
    full_case(prep_lab)
    selected, claim_id, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        source = session.get(ClaimRow, claim_id)
        payload = deepcopy(source.payload)
        payload.update(
            {
                "id": "copied-id",
                "claim_type": "sat_min_total",
                "source_url": "https://example.edu/copied",
                "accessed_at": "2024-01-01T00:00:00Z",
            }
        )
        source.payload = payload
        result = session.get(ProgramResultRow, selected)
        result.payload = {**result.payload, "claims": [{"id": "FORGED-PREVIEW-CLAIM"}]}
        session.commit()
    response = _get(prep_lab, [selected])
    proof = response.json()["requirements"][0]["proofs"][0]["claim"]
    assert proof["id"] == claim_id and proof["claim_type"] == "ielts_min_overall"
    assert proof["source_url"] == "https://example.edu/requirements"
    assert proof["is_stale"] is False and "FORGED-PREVIEW-CLAIM" not in response.text


def test_every_freshness_decision_uses_one_timestamp_and_the_inclusive_boundary(
    prep_lab, monkeypatch
):
    full_case(prep_lab)
    first, first_claim, _ = _selected(prep_lab)
    second, second_claim, _ = _selected(prep_lab)
    fixed = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    with prep_lab["factory"]() as session:
        session.get(ClaimRow, first_claim).accessed_at = (
            fixed - timedelta(days=180) + timedelta(microseconds=1)
        )
        session.get(ClaimRow, second_claim).accessed_at = fixed - timedelta(days=180)
        session.commit()
    calls = []

    def one_timestamp():
        calls.append(True)
        return fixed + timedelta(seconds=len(calls) - 1)

    monkeypatch.setattr(graph_api, "utcnow", one_timestamp)
    graph = _get(prep_lab, [first, second]).json()
    assert calls == [True]
    assert [atom["evidence_state"] for atom in graph["requirements"]] == ["current", "stale"]


def test_exact_run_result_and_global_partitions_do_not_include_unselected_evidence(prep_lab):
    full_case(prep_lab)
    first, first_claim, _ = _selected(prep_lab)
    second, second_claim, _ = _selected(prep_lab)
    unselected, unselected_claim, _ = _selected(prep_lab)
    _share_run(prep_lab, first, [second, unselected])
    with prep_lab["factory"]() as session:
        original = session.get(ClaimRow, first_claim)
        global_source = ClaimRow(
            run_id=original.run_id,
            result_id=None,
            claim_type=original.claim_type,
            status=original.status,
            source_url="https://example.edu/global",
            accessed_at=original.accessed_at,
            source_specificity=original.source_specificity,
            payload=deepcopy(original.payload),
        )
        session.add(global_source)
        session.flush()
        result = session.get(ProgramResultRow, first)
        original_check = result.payload["requirement_checks"][0]
        result.payload = {
            **result.payload,
            "requirement_checks": [
                {**original_check, "claim_ids": [global_source.id]},
            ],
        }
        global_id = global_source.id
        session.commit()
    graph = _get(prep_lab, [first, second]).json()
    assert [atom["resolved_claim_ids"] for atom in graph["requirements"]] == [
        [global_id],
        [second_claim],
    ]
    displayed = {proof["claim"]["id"] for atom in graph["requirements"] for proof in atom["proofs"]}
    assert first_claim not in displayed and unselected_claim not in displayed


@pytest.mark.parametrize(
    "bad",
    [
        "result_shape",
        "checks",
        "claim",
        "profile",
        "duplicate_award",
        "checklist_shape",
        "checklist_identity",
        "checklist_disagreement",
    ],
)
def test_unreadable_owned_evidence_is_an_unavailable_unknown_slice_not_an_empty_success(
    prep_lab, bad
):
    full_case(prep_lab)
    selected, claim_id, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        result = session.get(ProgramResultRow, selected)
        payload = deepcopy(result.payload)
        if bad == "result_shape":
            result.payload = ["historical invalid document"]
        elif bad == "checks":
            result.payload = {**payload, "requirement_checks": [{"status": "GAP"}]}
        elif bad == "claim":
            session.get(ClaimRow, claim_id).payload = {"unreadable": True}
        elif bad == "profile":
            session.get(ApplicantProfileRow, prep_lab["case"]).payload = {"context": {}}
        elif bad == "duplicate_award":
            award = Scholarship(id="duplicate", name="Synthetic Award").model_dump(mode="json")
            result.payload = {**payload, "scholarships": [award, award]}
        elif bad == "checklist_shape":
            result.checklist = {"unreadable": True}
        elif bad == "checklist_identity":
            result.checklist = DocumentChecklist(
                result_id=uuid4().hex,
                university=result.university,
                program=result.program,
            ).model_dump(mode="json")
        elif bad == "checklist_disagreement":
            checklist = DocumentChecklist(
                result_id=selected, university=result.university, program=result.program
            )
            result.checklist = checklist.model_dump(mode="json")
            result.payload = {
                **payload,
                "checklist": {
                    **checklist.model_dump(mode="json"),
                    "ordered_steps": ["Different snapshot"],
                },
            }
        session.commit()
    response = _get(prep_lab, [selected])
    assert response.status_code == 200
    graph = response.json()
    (programme,) = graph["programmes"]
    assert (
        programme["evidence_state"] == "unknown" and programme["projection_state"] == "unavailable"
    )
    assert programme["unresolved_reasons"] == ["evidence_unavailable"]
    assert graph["requirements"] == [] and graph["document_actions"] == []


@pytest.mark.parametrize("resolved", [False, True])
def test_unreadable_unresolved_conflict_is_conflicted_but_resolved_rows_are_excluded(
    prep_lab, resolved
):
    full_case(prep_lab)
    selected, _, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        result = session.get(ProgramResultRow, selected)
        session.add(
            ConflictRow(
                run_id=result.run_id,
                result_id=selected,
                claim_type="ielts_min_overall",
                unresolved=not resolved,
                payload={"unreadable": True},
            )
        )
        session.commit()
    graph = _get(prep_lab, [selected]).json()
    assert graph["programmes"][0]["evidence_state"] == ("current" if resolved else "conflicted")
    if not resolved:
        assert graph["programmes"][0]["projection_state"] == "unavailable"
        assert graph["requirements"] == []


def test_local_malformed_conflict_cannot_taint_or_be_borrowed_by_another_selected_result(prep_lab):
    full_case(prep_lab)
    first, _, _ = _selected(prep_lab)
    second, _, _ = _selected(prep_lab)
    _share_run(prep_lab, first, [second])
    with prep_lab["factory"]() as session:
        result = session.get(ProgramResultRow, first)
        session.add(
            ConflictRow(
                run_id=result.run_id,
                result_id=first,
                claim_type="ielts_min_overall",
                unresolved=True,
                payload={},
            )
        )
        session.commit()
    graph = _get(prep_lab, [first, second]).json()
    assert [row["evidence_state"] for row in graph["programmes"]] == ["conflicted", "current"]
    assert [atom["result_id"] for atom in graph["requirements"]] == [second]
    assert graph["evidence_state"] == "conflicted"


def test_authoritative_unresolved_conflict_and_type_override_the_copied_payload(prep_lab):
    full_case(prep_lab)
    selected, _, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        result = session.get(ProgramResultRow, selected)
        session.add(
            ConflictRow(
                run_id=result.run_id,
                result_id=selected,
                claim_type="ielts_min_overall",
                unresolved=True,
                payload={
                    "claim_type": "sat_min_total",
                    "subject": "Synthetic conflict only",
                    "claim_ids": [],
                    "values": [6.5, 7.0],
                    "source_urls": ["https://example.edu/requirements"],
                    "question_for_admissions": "Which synthetic rule is intended?",
                    "unresolved": False,
                },
            )
        )
        session.commit()
    graph = _get(prep_lab, [selected]).json()
    assert graph["requirements"][0]["evidence_state"] == "conflicted"
    assert graph["requirements"][0]["policy"] == "unknown"


@pytest.mark.parametrize("location", ["cross_paired", "unselected", "run_global"])
def test_conflict_partition_requires_same_run_and_result_or_same_run_global(prep_lab, location):
    full_case(prep_lab)
    first, _, _ = _selected(prep_lab)
    second, _, _ = _selected(prep_lab)
    unselected, _, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        first_run = session.get(ProgramResultRow, first).run_id
        if location == "unselected":
            session.get(ProgramResultRow, unselected).run_id = first_run
        session.add(
            ConflictRow(
                run_id=first_run,
                result_id=(second if location == "cross_paired" else unselected)
                if location != "run_global"
                else None,
                claim_type="ielts_min_overall",
                unresolved=True,
                payload={"unreadable": True},
            )
        )
        session.commit()
    graph = _get(prep_lab, [first, second]).json()
    assert [row["evidence_state"] for row in graph["programmes"]] == (
        ["conflicted", "current"] if location == "run_global" else ["current", "current"]
    )
    assert graph["programmes"][1]["projection_state"] == "partial"
    second_atoms = [atom for atom in graph["requirements"] if atom["result_id"] == second]
    assert second_atoms and all(
        "exam_identity_unestablished" in atom["unresolved_reasons"] for atom in second_atoms
    )
    assert any(atom["result_id"] == second for atom in graph["requirements"])


def test_resolved_conflict_column_excludes_payload_claiming_unresolved(prep_lab):
    full_case(prep_lab)
    selected, _, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        result = session.get(ProgramResultRow, selected)
        session.add(
            ConflictRow(
                run_id=result.run_id,
                result_id=None,
                claim_type="ielts_min_overall",
                unresolved=False,
                payload={
                    "claim_type": "ielts_min_overall",
                    "subject": "Synthetic conflict only",
                    "claim_ids": [],
                    "values": [6.5, 7.0],
                    "source_urls": ["https://example.edu/requirements"],
                    "question_for_admissions": "Which synthetic rule is intended?",
                    "unresolved": True,
                },
            )
        )
        session.commit()
    graph = _get(prep_lab, [selected]).json()
    assert graph["programmes"][0]["evidence_state"] == "current"
    assert graph["requirements"][0]["evidence_state"] == "current"


def test_empty_checks_and_partial_run_keep_uncertainty_without_proving_absence(prep_lab):
    full_case(prep_lab)
    first, _, _ = _selected(prep_lab)
    second, _, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        result = session.get(ProgramResultRow, first)
        result.payload = {**result.payload, "requirement_checks": []}
        other = session.get(ProgramResultRow, second)
        session.get(ResearchRun, other.run_id).stage = "failed"
        other.payload = {
            **other.payload,
            "unresolved": [
                {
                    "topic": "research read allowance",
                    "question": "Which facts remain?",
                    "why_it_matters": "Synthetic partial source; not proof of absence.",
                }
            ],
        }
        session.commit()
    graph = _get(prep_lab, [first, second]).json()
    assert [row["evidence_state"] for row in graph["programmes"]] == ["unknown", "unknown"]
    assert "checks_missing" in graph["programmes"][0]["unresolved_reasons"]
    assert "evidence_partial" in graph["programmes"][1]["unresolved_reasons"]
    assert graph["requirements"][0]["evidence_state"] == "current"
    assert graph["programmes"][1]["unresolved_questions"][0]["topic"] == "research read allowance"


@pytest.mark.parametrize(
    "stage,cancelled,partial",
    [
        (PipelineStage.COMPLETED.value, False, False),
        (PipelineStage.COMPLETED.value, True, True),
        (PipelineStage.AWAITING_USER_DECISION.value, False, True),
        (PipelineStage.FAILED.value, False, True),
    ],
)
def test_native_completed_stage_is_distinct_from_incomplete_research(
    prep_lab, stage, cancelled, partial
):
    full_case(prep_lab)
    selected, _, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        result = session.get(ProgramResultRow, selected)
        run = session.get(ResearchRun, result.run_id)
        run.stage = stage
        run.cancelled = cancelled
        session.commit()
    response = _get(prep_lab, [selected])
    assert response.status_code == 200
    graph = response.json()
    programme = graph["programmes"][0]
    assert ("evidence_partial" in programme["unresolved_reasons"]) is partial
    assert programme["evidence_state"] == ("unknown" if partial else "current")
    assert graph["requirements"][0]["evidence_state"] == "current"


def test_untyped_preview_claims_cannot_replace_a_missing_authoritative_row(prep_lab):
    full_case(prep_lab)
    selected, claim_id, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        claim = session.get(ClaimRow, claim_id)
        result = session.get(ProgramResultRow, selected)
        result.payload = {**result.payload, "claims": [{**claim.payload, "id": claim_id}]}
        session.delete(claim)
        session.commit()
    (atom,) = _get(prep_lab, [selected]).json()["requirements"]
    assert atom["resolved_claim_ids"] == [] and atom["evidence_state"] == "unknown"


def test_admission_optional_sat_and_own_scholarship_minimum_remain_separate(prep_lab):
    full_case(prep_lab)
    selected, claim_id, _ = _selected(
        prep_lab, kind="sat_policy", value="optional", label="SAT policy", status="NOT_APPLICABLE"
    )
    with prep_lab["factory"]() as session:
        source = session.get(ClaimRow, claim_id)
        claim = Claim.model_validate(
            {
                **source.payload,
                "claim_type": "scholarship_min_test_score",
                "normalized_value": {"sat": 1450},
                "subject_key": "Synthetic Award",
                "source_url": "https://example.edu/synthetic-award",
            }
        )
        award_source = ClaimRow(
            run_id=source.run_id,
            result_id=selected,
            claim_type="scholarship_min_test_score",
            status=source.status,
            source_url=claim.source_url,
            accessed_at=source.accessed_at,
            source_specificity=source.source_specificity,
            payload=claim.model_dump(mode="json"),
        )
        session.add(award_source)
        session.flush()
        check = RequirementCheck(
            requirement="Scholarship SAT score",
            published_value={"sat": 1450},
            status="GAP",
            claim_ids=[award_source.id],
        )
        award = Scholarship(
            id="synthetic-award", name="Synthetic Award", eligibility_checks=[check]
        )
        result = session.get(ProgramResultRow, selected)
        result.payload = {**result.payload, "scholarships": [award.model_dump(mode="json")]}
        session.commit()
    atoms = _get(prep_lab, [selected]).json()["requirements"]
    assert [(atom["purpose"], atom["policy"]) for atom in atoms] == [
        ("admission", "optional"),
        ("scholarship", "required"),
    ]
    assert [atom["scholarship_id"] for atom in atoms] == [None, "synthetic-award"]
    assert atoms[1]["original_check"]["published_value"] == {"sat": 1450}


def test_legacy_plan_wire_shape_and_stored_state_are_unchanged_after_graph_get(prep_lab):
    full_case(prep_lab)
    grant(prep_lab)
    selected, _, _ = _selected(prep_lab)
    legacy = prep_lab["client"].get(url(prep_lab, "plan"), params={"result_id": selected}).json()
    assert write(prep_lab).status_code == 200
    assert prep_lab["client"].post(url(prep_lab, "attempts"), json=body()).status_code in {200, 201}
    with prep_lab["factory"]() as session:
        calendar = (
            session.query(StudyScheduleRow)
            .filter(StudyScheduleRow.profile_id == prep_lab["case"])
            .one()
        )
        calendar.learning_path = {"synthetic_frozen_sidecar": "must remain byte-identical"}
        session.commit()
    before = _snapshot(prep_lab)
    response, statements = _capture(prep_lab, lambda: _get(prep_lab, [selected]))
    assert response.status_code == 200
    assert _snapshot(prep_lab) == before
    assert not any(
        re.match(r"\s*(insert|update|delete|alter|create|drop)\b", statement, re.I)
        for statement in statements
    )
    after = prep_lab["client"].get(url(prep_lab, "plan"), params={"result_id": selected}).json()
    assert after == legacy
    assert "official_score" not in response.json() and "learning_path" not in response.json()


def test_nonfinite_or_duplicate_stored_field_snapshots_are_rejected_before_hashing():
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError):
            StoredPreparationGraphFields.model_validate(
                {
                    "requirement_checks": [
                        {
                            "requirement": "IELTS overall",
                            "status": "GAP",
                            "published_value": value,
                        }
                    ]
                }
            )
    with pytest.raises(ValidationError):
        StoredPreparationGraphFields.model_validate(
            {
                "scholarships": [
                    {"id": "same", "name": "Synthetic A"},
                    {"id": "same", "name": "Synthetic B"},
                ]
            }
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["published_value", "applicant_value"])
def test_nested_nonfinite_observation_cannot_be_serialized_into_missing_evidence(value, field):
    with pytest.raises(ValidationError, match="finite JSON"):
        StoredPreparationGraphFields.model_validate(
            {
                "requirement_checks": [
                    {"requirement": "IELTS overall", "status": "GAP", field: {"scores": [value]}}
                ]
            }
        )


def test_one_unavailable_slice_does_not_remove_another_owned_selection(prep_lab):
    full_case(prep_lab)
    first, _, _ = _selected(prep_lab)
    second, second_claim, _ = _selected(prep_lab)
    with prep_lab["factory"]() as session:
        session.get(ProgramResultRow, first).payload = {"requirement_checks": None}
        session.commit()
    response = _get(prep_lab, [second, first])
    assert response.status_code == 200
    graph = response.json()
    assert graph["requested_result_ids"] == graph["selected_result_ids"] == [second, first]
    assert [row["projection_state"] for row in graph["programmes"]] == ["partial", "unavailable"]
    assert graph["requirements"][0]["resolved_claim_ids"] == [second_claim]


def test_registered_graph_route_requires_the_native_principal_when_auth_is_enabled(
    prep_lab, monkeypatch
):
    from app.config import get_settings

    selected, _, _ = _selected(prep_lab)
    monkeypatch.setenv("UNIMATCH_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    response, statements = _capture(prep_lab, lambda: _get(prep_lab, [selected]))
    assert response.status_code == 401
    assert not any("program_results" in statement.lower() for statement in statements)


# G1 finite-v2 controls. Direct ORM envelopes only: never persist nonfinite JSON.
# Append to test_preparation_graph_api.py; all referenced imports already exist.

_FINITE_V2_NONFINITE = [
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="positive-inf"),
    pytest.param(float("-inf"), id="negative-inf"),
]
_FINITE_V2_TIME = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)


def _finite_v2_scope():
    return {
        "university": "Synthetic University",
        "programme": "Synthetic Programme",
        "degree": "bachelor",
        "intake": "Fall 2027",
    }


def _finite_v2_claim_row(value, *, key="a" * 32):
    return ClaimRow(
        id=key,
        run_id="b" * 32,
        result_id="c" * 32,
        claim_type="ielts_min_overall",
        status="VERIFIED_CURRENT",
        source_url="https://example.edu/authoritative-synthetic",
        source_specificity="program_intake",
        accessed_at=_FINITE_V2_TIME,
        payload={
            "claim_type": "sat_min_total",
            "status": "UNVERIFIED",
            "source_url": "https://example.edu/copied-synthetic",
            "source_specificity": "aggregator",
            "accessed_at": "2000-01-01T00:00:00Z",
            "official_domain": True,
            "normalized_value": value,
            "original_text_excerpt": "Synthetic finite-control quotation only.",
            "scope": _finite_v2_scope(),
        },
    )


def _finite_v2_conflict_row(values):
    return ConflictRow(
        id="d" * 32,
        run_id="b" * 32,
        result_id="c" * 32,
        claim_type="ielts_min_overall",
        unresolved=True,
        payload={
            "claim_type": "sat_min_total",
            "unresolved": False,
            "subject": "Synthetic numeric-control conflict",
            "claim_ids": ["a" * 32],
            "values": values,
            "source_urls": ["https://example.edu/authoritative-synthetic"],
            "question_for_admissions": "Which synthetic observation is intended?",
        },
    )


def _finite_v2_checklist_row(size, *, origin="column", location="admission_documents"):
    checklist = {
        "result_id": "c" * 32,
        "university": "Synthetic University",
        "program": "Synthetic Programme",
        "generated_at": "2026-10-12T12:00:00Z",
        "completeness": "official",
        location: [
            {
                "name": "Synthetic transcript",
                "purpose": "scholarship" if location == "scholarship_documents" else "admission",
                "owner": "school" if location == "school_actions" else "applicant",
                "max_file_size_mb": size,
                "deadline": "2027-01-15",
                "scope": _finite_v2_scope(),
                "claim_ids": ["a" * 32],
                "source_url": "https://example.edu/synthetic-documents",
            }
        ],
    }
    return ProgramResultRow(
        id="c" * 32,
        run_id="b" * 32,
        university="Synthetic University",
        program="Synthetic Programme",
        payload={"checklist": checklist if origin == "payload" else None},
        checklist=checklist if origin == "column" else None,
    )


@pytest.mark.parametrize("value", _FINITE_V2_NONFINITE)
def test_finite_v2_raw_claim_nested_nonfinite_is_a_failed_read(value):
    bad = _finite_v2_claim_row({"scores": [value]})
    good = _finite_v2_claim_row({"scores": [7.5]}, key="e" * 32)
    before = bad.payload
    claims, failed = graph_api._claims([bad, good], _FINITE_V2_TIME)
    assert failed is True
    assert [claim.id for claim in claims] == [good.id]
    assert claims[0].normalized_value == {"scores": [7.5]}
    assert bad.payload is before


@pytest.mark.parametrize("value", _FINITE_V2_NONFINITE)
def test_finite_v2_raw_conflict_nested_nonfinite_is_a_failed_read(value):
    bad = _finite_v2_conflict_row([{"scores": [value]}])
    good = _finite_v2_conflict_row([6.5, 7.0])
    good.id = "f" * 32
    before = bad.payload
    conflicts, failed = graph_api._conflicts([bad, good])
    assert failed is True
    assert len(conflicts) == 1 and conflicts[0].values == [6.5, 7.0]
    assert conflicts[0].unresolved is True
    assert bad.payload is before


@pytest.mark.parametrize("value", _FINITE_V2_NONFINITE)
@pytest.mark.parametrize("location", ["admission_documents", "scholarship_documents", "school_actions"])
def test_finite_v2_authoritative_column_rejects_raw_nonfinite_document_size(value, location):
    row = _finite_v2_checklist_row(value, location=location)
    before = row.checklist
    with pytest.raises(ValueError):
        graph_api._stored_fields(row)
    assert row.checklist is before and row.payload == {"checklist": None}


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("origin", ["column", "payload"])
def test_finite_v2_numeric_string_document_size_is_rejected_after_coercion(value, origin):
    row = _finite_v2_checklist_row(value, origin=origin)
    with pytest.raises(ValueError, match="finite"):
        graph_api._stored_fields(row)


@pytest.mark.parametrize(
    "value", [None, 7.5, {"scores": [7.5, None]}, {"quote": "NaN"}, {"scores": (6.5, 7.5)}]
)
def test_finite_v2_claim_preserves_finite_value_scope_and_authoritative_columns(value):
    row = _finite_v2_claim_row(value)
    before = deepcopy(row.payload)
    claims, failed = graph_api._claims([row], _FINITE_V2_TIME)
    assert failed is False and len(claims) == 1
    claim = claims[0]
    assert claim.id == row.id and claim.normalized_value == value
    assert claim.claim_type.value == "ielts_min_overall"
    assert claim.status.value == "VERIFIED_CURRENT"
    assert claim.source_url == row.source_url
    assert claim.source_specificity.value == "program_intake"
    assert claim.accessed_at == _FINITE_V2_TIME
    assert claim.is_stale is False and claim.age_days == 0
    assert claim.scope is not None and claim.scope.university == "Synthetic University"
    assert claim.scope.programme == "Synthetic Programme"
    assert row.payload == before


def test_finite_v2_conflict_keeps_finite_values_and_authoritative_unresolved_type():
    values = [None, 6.5, {"band": 7.0}, "NaN"]
    row = _finite_v2_conflict_row(values)
    before = deepcopy(row.payload)
    conflicts, failed = graph_api._conflicts([row])
    assert failed is False and len(conflicts) == 1
    assert conflicts[0].claim_type.value == "ielts_min_overall"
    assert conflicts[0].unresolved is True and conflicts[0].values == values
    assert row.payload == before


@pytest.mark.parametrize("size,expected", [(None, None), (2.5, 2.5), ("2.5", 2.5)])
@pytest.mark.parametrize("origin", ["column", "payload"])
def test_finite_v2_document_keeps_finite_size_scope_dates_and_enums(size, expected, origin):
    row = _finite_v2_checklist_row(size, origin=origin)
    before_payload, before_column = deepcopy(row.payload), deepcopy(row.checklist)
    fields = graph_api._stored_fields(row)
    assert fields.checklist is not None
    checklist = fields.checklist
    item = checklist.admission_documents[0]
    assert item.max_file_size_mb == expected
    assert checklist.result_id == row.id and checklist.university == row.university
    assert checklist.program == row.program and checklist.completeness == "official"
    assert checklist.generated_at == _FINITE_V2_TIME
    assert item.deadline is not None and item.deadline.isoformat() == "2027-01-15"
    assert item.purpose.value == "admission" and item.owner.value == "applicant"
    assert item.scope is not None and item.scope.programme == "Synthetic Programme"
    assert item.claim_ids == ["a" * 32]
    assert row.payload == before_payload and row.checklist == before_column

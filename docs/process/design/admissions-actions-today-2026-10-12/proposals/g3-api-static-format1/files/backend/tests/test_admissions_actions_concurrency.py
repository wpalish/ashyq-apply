"""Migrated G3 storage controls; synthetic records and native erase routes.

Reuse the approved two-database lab, its no-lifespan client and no-IP/DNS guard.
The storage helper below is test setup, not a G3 API, fence or concurrency proof.
No provider, official admissions evidence, production data or writer race is used.
This external source proposal has not been imported, collected or run by its author.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import MetaData, delete, event, inspect, select, text
from sqlalchemy.exc import DataError, IntegrityError

from app.db import ALEMBIC_INI, MIGRATIONS_DIR
from app.domain import admissions_actions as d
from app.models import (
    ApplicantProfileRow,
    Entitlement,
    Organization,
    OrganizationMembership,
    ProgramResultRow,
    ResearchRun,
    StudyScheduleRow,
    User,
)
from app.models.admissions_actions import AdmissionsActionsCurrentRow, AdmissionsActionsEventRow
from app.models.base import ensure_utc
from app.schemas import admissions_actions as s
from app.schemas.result import DocumentChecklist, DocumentItem
from app.security import DEV_ORGANIZATION_ID, DEV_USER_ID
from tests.test_learning_schedule_api import preview as learning_preview
from tests.test_learning_schedule_api import save as learning_save
from tests.test_preparation_api import full_case, grant
from tests.test_preparation_graph_api import _capture, _selected
from tests.test_preparation_write_concurrency import (
    SYNTHETIC_PASSWORD,
    driver,
    enable_native_auth,
    g2_holder_statement,
    g2_waiter_statement,
    is_legacy_dml,
    is_profile_lock,
    move_to_shared_organization,
    native_legacy_command,
    normalized,
    ordered_race,
    profile_payload,
    request,
)
from tests.test_shared_route_api import accepted, route_input
from tests.test_study_schedule_api import unchanged_inputs, write

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")

AT = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
PARENT = "c3e71d902023"
HEAD = "d7a61e902024"
TABLES = {"admissions_actions_current", "admissions_actions_events"}


def native_snapshot(lab):
    """Exact native rows; migration version and the two new tables are separate."""
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
            if name not in TABLES | {"alembic_version"}
        }


def wire_values(values):
    return {
        key: (
            ensure_utc(value).astimezone(UTC).isoformat()
            if isinstance(value, datetime)
            else deepcopy(value)
        )
        for key, value in values.items()
    }


def stored(lab):
    """All G3 columns, read through a fresh Session after every transaction."""
    with lab["factory"]() as session:
        current = session.get(AdmissionsActionsCurrentRow, lab["case"])
        rows = (
            session.query(AdmissionsActionsEventRow)
            .filter_by(profile_id=lab["case"])
            .order_by(AdmissionsActionsEventRow.revision)
            .all()
        )
        return {
            "current": None
            if current is None
            else wire_values(
                {column.name: getattr(current, column.name) for column in current.__table__.columns}
            ),
            "events": [
                wire_values(
                    {column.name: getattr(row, column.name) for column in row.__table__.columns}
                )
                for row in rows
            ],
        }


def current_values(transition):
    return {
        "profile_id": transition.state.profile_id,
        "revision": transition.state.revision,
        "schema_version": transition.state.schema_version,
        "state": transition.state.model_dump(mode="json"),
        "state_digest": s.state_digest(transition.state),
        "updated_at": transition.receipt.accepted_at,
    }


def event_values(receipt):
    return {
        "id": receipt.event_id,
        "profile_id": receipt.profile_id,
        "revision": receipt.revision,
        "schema_version": receipt.schema_version,
        "kind": receipt.kind,
        "client_write_uuid": str(receipt.client_write_uuid),
        "request_digest": receipt.canonical_request_digest,
        "receipt_digest": receipt.receipt_digest,
        "accepted_at": receipt.accepted_at,
        "affected_refs": receipt.affected_refs.model_dump(mode="json"),
        "receipt": receipt.model_dump(mode="json"),
    }


def store_transition(lab, transition):
    """Atomic synthetic setup only: no ownership/CAS/UUID recovery API is claimed."""
    with lab["factory"]() as session:
        current = session.get(AdmissionsActionsCurrentRow, lab["case"])
        if current is None:
            session.add(AdmissionsActionsCurrentRow(**current_values(transition)))
        else:
            for name, value in current_values(transition).items():
                setattr(current, name, value)
        session.add(AdmissionsActionsEventRow(**event_values(transition.receipt)))
        session.commit()


def load_validated(lab):
    value = stored(lab)
    current = value["current"]
    assert current is not None and value["events"]
    state = s.CaseActionsStateV1.model_validate(current["state"])
    receipts = []
    metadata = []
    for row in value["events"]:
        receipt = s.ActionWriteReceiptV1.model_validate(row["receipt"])
        assert row == wire_values(event_values(receipt))
        assert receipt.receipt_digest == s.receipt_digest(receipt)
        assert receipt.canonical_request_digest == s.request_digest(lab["case"], receipt.request)
        metadata.append(
            s.EventMetadataV1.model_validate(
                {
                    "profile_id": row["profile_id"],
                    "event_id": row["id"],
                    "revision": row["revision"],
                    "kind": row["kind"],
                    "accepted_at": row["accepted_at"],
                    "affected_refs": row["affected_refs"],
                }
            )
        )
        receipts.append(receipt)
    assert current["profile_id"] == lab["case"]
    assert current["schema_version"] == state.schema_version
    assert current["revision"] == state.revision
    assert s.canonical_bytes(current["state"]) == s.canonical_bytes(state.model_dump(mode="json"))
    assert (
        d.validate_current_snapshot(
            current["state"],
            receipts[-1],
            profile_id=lab["case"],
            row_digest=current["state_digest"],
            row_updated_at=datetime.fromisoformat(current["updated_at"]),
            latest_revision=value["events"][-1]["revision"],
            metadata=metadata,
        )
        == state
    )
    assert d.validate_complete_export(state, receipts, profile_id=lab["case"]) == receipts
    return state, receipts


def store_and_assert(lab, transition, previous_receipts):
    before = native_snapshot(lab)
    store_transition(lab, transition)
    expected = [*previous_receipts, transition.receipt]
    value = stored(lab)
    assert value == {
        "current": wire_values(current_values(transition)),
        "events": [wire_values(event_values(receipt)) for receipt in expected],
    }
    state, receipts = load_validated(lab)
    assert s.canonical_bytes(state.model_dump(mode="json")) == s.canonical_bytes(
        transition.state.model_dump(mode="json")
    )
    assert [s.canonical_bytes(receipt.model_dump(mode="json")) for receipt in receipts] == [
        s.canonical_bytes(receipt.model_dump(mode="json")) for receipt in expected
    ]
    assert native_snapshot(lab) == before
    return state, receipts


def intent(kind, revision=0, *, write_uuid=None, **fields):
    return {
        "kind": kind,
        "expected_revision": revision,
        "client_write_uuid": write_uuid or str(uuid4()),
        **fields,
    }


def context(lab, index, *, local_development=True, **fields):
    with lab["factory"]() as session:
        profile = session.get(ApplicantProfileRow, lab["case"])
        user = session.get(User, DEV_USER_ID)
        assert profile is not None and user is not None and user.is_active
        assert (
            session.get(OrganizationMembership, (DEV_USER_ID, profile.organization_id)) is not None
        )
        actor = d.actor_reference(
            user.id, profile.organization_id, local_development=local_development
        )
    return d.ActionContextV1(
        profile_id=lab["case"],
        event_id=uuid4().hex,
        accepted_at=AT + timedelta(seconds=index),
        actor=actor,
        **fields,
    )


def details():
    return {"due": None, "notes": "Entered synthetic storage note"}


def personal():
    return {
        "label": "Entered synthetic transcript task",
        "responsible_actor": "applicant",
        "details": details(),
        "depends_on_task_ids": [],
    }


def first_personal(lab, *, write_uuid=None, local_development=True):
    return d.apply_action(
        None,
        intent(
            "create_personal_task", write_uuid=write_uuid, application_id=None, personal=personal()
        ),
        context(lab, 1, local_development=local_development, new_task_id=uuid4().hex),
    )


def next_report(lab, state, *, local_development=True):
    return d.apply_action(
        state,
        intent(
            "set_document_self_report",
            state.revision,
            task_id=state.document_tasks[0].id,
            report={
                "state": "prepared_reported",
                "entered_at": None,
                "confirmed_personal_report": True,
            },
        ),
        context(lab, state.revision + 1, local_development=local_development),
    )


def create_profile_only(lab):
    with lab["factory"]() as session:
        payload = deepcopy(session.get(ApplicantProfileRow, lab["case"]).payload)
    response = lab["client"].post("/api/profiles", json=payload)
    assert response.status_code == 201, response.text
    return {**lab, "case": response.json()["id"]}


def own_source(lab, result_id):
    """Observe the actual synthetic own column and entitlement, never copied decision."""
    with lab["factory"]() as session:
        result = session.get(ProgramResultRow, result_id)
        run = session.get(ResearchRun, result.run_id)
        profile = session.get(ApplicantProfileRow, lab["case"])
        assert run.profile_id == profile.id == lab["case"]
        assert result.user_decision == "approved" and result.payload["user_decision"] == "rejected"
        entitlement = (
            session.query(Entitlement)
            .filter_by(
                organization_id=profile.organization_id, profile_id=profile.id, kind="case_full"
            )
            .first()
        )
        assert entitlement is not None and result.checklist is not None
        raw = deepcopy(result.checklist)
        observation = d.TargetObservationV1(
            profile_id=profile.id,
            result_id=result.id,
            state="selected",
            decision=result.user_decision,
            research_access=entitlement is not None,
            award_ids=[],
        )
    binding = d.build_binding_selection(
        raw,
        profile_id=lab["case"],
        result_id=result_id,
        selected_occurrences=[("admission_documents", 0)],
        purpose="admission",
        award_id=None,
    )
    preview_digest = s.reference_digest("synthetic-storage-source-v1", raw)
    return observation, d.SourceObservationV1(
        target=observation, state="readable", selection=binding, preview_digest=preview_digest
    )


def full_chain(lab, *, local_development=True):
    full_case(lab)
    result_id, _, _ = _selected(lab)
    with lab["factory"]() as session:
        row = session.get(ProgramResultRow, result_id)
        row.checklist = DocumentChecklist(
            result_id=row.id,
            university=row.university,
            program=row.program,
            generated_at=AT,
            admission_documents=[
                DocumentItem(
                    name="Synthetic transcript",
                    purpose="admission",
                    owner="applicant",
                    source_url="https://example.edu/synthetic-storage-transcript",
                )
            ],
            ordered_steps=["Synthetic source step"],
            completeness="partial",
        ).model_dump(mode="json")
        session.commit()
    observation, source = own_source(lab, result_id)
    application_id = uuid4().hex
    created = d.apply_action(
        None,
        intent(
            "create_application",
            target={
                "result_id": result_id,
                "purpose": "admission",
                "award_id": None,
                "intake": {"state": "unknown"},
                "route": {"state": "applicant_entered", "value": "Entered synthetic route"},
                "confirmed_entered_context": True,
            },
            label="Entered synthetic application",
            details=details(),
        ),
        context(
            lab,
            1,
            local_development=local_development,
            new_application_id=application_id,
            target=observation,
        ),
    )
    state, receipts = store_and_assert(lab, created, [])
    bound = d.apply_action(
        state,
        intent(
            "bind_source_task",
            1,
            application_id=application_id,
            source=source.selection.model_dump(mode="python"),
            source_preview_digest=source.preview_digest,
            personal=personal(),
        ),
        context(
            lab, 2, local_development=local_development, new_task_id=uuid4().hex, source=source
        ),
    )
    state, receipts = store_and_assert(lab, bound, receipts)
    reported = next_report(lab, state, local_development=local_development)
    state, receipts = store_and_assert(lab, reported, receipts)
    task_before_submission = state.document_tasks[0].model_dump(mode="json")
    submitted = d.apply_action(
        state,
        intent(
            "declare_submission",
            3,
            application_id=application_id,
            submission={
                "entered_at": {"local_date": "2026-10-11", "local_time": None, "timezone": None},
                "channel": "Entered synthetic portal",
                "document_task_ids": [state.document_tasks[0].id],
                "confirmed_applicant_declaration": True,
            },
        ),
        context(lab, 4, local_development=local_development),
    )
    state, receipts = store_and_assert(lab, submitted, receipts)
    assert state.document_tasks[0].model_dump(mode="json") == task_before_submission
    assert receipts[-1].affected_refs.document_task_ids == []
    assert receipts[-1].applied_delta.declaration.official_verification == "not_performed"
    corrected = d.apply_action(
        state,
        intent(
            "correct_declaration",
            4,
            application_id=application_id,
            prior_declaration=state.applications[0].status_ref.model_dump(mode="python"),
            replacement={"kind": "planning", "status": "preparing"},
            confirmed_correction=True,
        ),
        context(
            lab, 5, local_development=local_development, prior_declaration_receipt=receipts[-1]
        ),
    )
    state, receipts = store_and_assert(lab, corrected, receipts)
    old_report = state.document_tasks[0].report.model_dump(mode="json")
    with lab["factory"]() as session:
        row = session.get(ProgramResultRow, result_id)
        changed = deepcopy(row.checklist)
        changed["admission_documents"][0]["word_limit"] = 300
        row.checklist = changed
        session.commit()
    _, replacement = own_source(lab, result_id)
    rebound = d.apply_action(
        state,
        intent(
            "rebind_source_task",
            5,
            task_id=state.document_tasks[0].id,
            expected_binding_digest=state.document_tasks[0].binding.binding_digest,
            source=replacement.selection.model_dump(mode="python"),
            source_preview_digest=replacement.preview_digest,
        ),
        context(lab, 6, local_development=local_development, source=replacement),
    )
    state, receipts = store_and_assert(lab, rebound, receipts)
    assert state.document_tasks[0].report.model_dump(mode="json") == old_report
    assert d.report_review_reasons(state.document_tasks[0]) == ["report_refers_to_previous_binding"]
    assert state.applications[0].status == "preparing"
    assert receipts[-2].applied_delta.corrected_declaration.event_id == receipts[3].event_id
    return state, receipts


def migrate(lab, revision, *, downgrade=False):
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option(
        "sqlalchemy.url", lab["engine"].url.render_as_string(hide_password=False).replace("%", "%%")
    )
    operation = alembic_command.downgrade if downgrade else alembic_command.upgrade
    operation(config, revision)
    with lab["engine"].connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == revision
        )


def test_populated_native_parent_upgrade_downgrade_reupgrade_is_additive(shared_route_lab):
    lab = shared_route_lab
    migrate(lab, PARENT, downgrade=True)
    assert not TABLES & set(inspect(lab["engine"]).get_table_names())
    grant(lab)
    full_case(lab)
    result_id, _, _ = _selected(lab)
    second_result_id, _, _ = _selected(lab, decision="maybe", value=7.0)
    first_calendar = write(lab)
    assert first_calendar.status_code == 200, first_calendar.text
    marked = deepcopy(first_calendar.json()["settings"])
    marked["completed_task_ids"] = [first_calendar.json()["schedule"]["tasks"][0]["id"]]
    assert write(lab, revision=1, plan=marked).status_code == 200
    saved_path = learning_save(lab, learning_preview(lab, 2))
    assert saved_path.status_code == 200, saved_path.text
    accepted(lab, route_input(lab, result_ids=[result_id, second_result_id]))
    with lab["factory"]() as session:
        calendar = session.query(StudyScheduleRow).filter_by(profile_id=lab["case"]).one()
        assert calendar.learning_path is not None and calendar.settings == marked
    before = native_snapshot(lab)
    assert before["shared_route_current"] and before["shared_route_history"]
    migrate(lab, HEAD)
    assert set(inspect(lab["engine"]).get_table_names()) >= TABLES
    assert stored(lab) == {"current": None, "events": []}
    assert native_snapshot(lab) == before
    store_and_assert(lab, first_personal(lab), [])
    migrate(lab, PARENT, downgrade=True)
    assert not TABLES & set(inspect(lab["engine"]).get_table_names())
    assert native_snapshot(lab) == before
    migrate(lab, HEAD)
    assert stored(lab) == {"current": None, "events": []}
    assert native_snapshot(lab) == before


def test_typed_chain_roundtrips_all_headers_hashes_times_and_previous_binding(shared_route_lab):
    lab = shared_route_lab
    state, receipts = full_chain(lab)
    assert [receipt.kind for receipt in receipts] == [
        "create_application",
        "bind_source_task",
        "set_document_self_report",
        "declare_submission",
        "correct_declaration",
        "rebind_source_task",
    ]
    assert [receipt.revision for receipt in receipts] == list(range(1, 7))
    assert [receipt.accepted_at for receipt in receipts] == [
        AT + timedelta(seconds=i) for i in range(1, 7)
    ]
    assert state.head_event_id == receipts[-1].event_id
    assert receipts[0].predecessor_event_id is None and receipts[0].before_state_digest is None
    assert "created_at" not in AdmissionsActionsEventRow.__table__.columns
    assert "updated_at" not in AdmissionsActionsEventRow.__table__.columns
    for model in (AdmissionsActionsCurrentRow, AdmissionsActionsEventRow):
        for column in model.__table__.columns:
            assert (
                column.default is None and column.server_default is None and column.onupdate is None
            )
        foreign_keys = inspect(lab["engine"]).get_foreign_keys(model.__tablename__)
        assert len(foreign_keys) == 1
        assert foreign_keys[0]["constrained_columns"] == ["profile_id"]
        assert foreign_keys[0]["referred_table"] == "applicant_profiles"
        assert foreign_keys[0]["options"]["ondelete"] == "CASCADE"


@pytest.mark.parametrize(
    "violation",
    [
        "current_pk",
        "event_pk",
        "event_profile_revision",
        "event_profile_uuid",
        "current_revision_zero",
        "current_revision_overflow",
        "event_revision_zero",
        "event_revision_overflow",
        "current_schema",
        "event_schema",
        "event_kind",
        "current_parent_fk",
        "event_parent_fk",
    ],
)
def test_migrated_database_rejects_physical_constraints_and_rolls_back(shared_route_lab, violation):
    lab = shared_route_lab
    sibling = create_profile_only(lab)
    first = first_personal(lab)
    store_and_assert(lab, first, [])
    before = stored(lab)
    native_before = native_snapshot(lab)
    current = current_values(first)
    receipt = event_values(first.receipt)
    current["profile_id"] = sibling["case"]
    receipt.update(id=uuid4().hex, revision=2, client_write_uuid=str(uuid4()))
    if violation == "current_pk":
        current["profile_id"] = lab["case"]
    elif violation == "event_pk":
        receipt["id"] = first.receipt.event_id
    elif violation == "event_profile_revision":
        receipt["revision"] = first.receipt.revision
    elif violation == "event_profile_uuid":
        receipt["client_write_uuid"] = str(first.receipt.client_write_uuid)
    elif violation.endswith("revision_zero"):
        (current if violation.startswith("current") else receipt)["revision"] = 0
    elif violation.endswith("revision_overflow"):
        (current if violation.startswith("current") else receipt)["revision"] = 2147483648
    elif violation.endswith("schema"):
        (current if violation.startswith("current") else receipt)["schema_version"] = "not-g3"
    elif violation == "event_kind":
        receipt["kind"] = "not-an-action"
    elif violation.endswith("parent_fk"):
        (current if violation.startswith("current") else receipt)["profile_id"] = uuid4().hex
    model = (
        AdmissionsActionsCurrentRow
        if violation.startswith("current")
        else AdmissionsActionsEventRow
    )
    values = current if violation.startswith("current") else receipt
    errors = (IntegrityError, DataError) if violation.endswith("overflow") else IntegrityError
    with lab["factory"]() as session:
        with pytest.raises(errors):
            session.execute(model.__table__.insert().values(**values))
            session.flush()
        session.rollback()
    assert stored(lab) == before
    assert stored(sibling) == {"current": None, "events": []}
    assert native_snapshot(lab) == native_before


def test_same_client_uuid_and_revision_are_allowed_for_a_distinct_own_profile(shared_route_lab):
    lab = shared_route_lab
    sibling = create_profile_only(lab)
    write_uuid = str(uuid4())
    first = first_personal(lab, write_uuid=write_uuid)
    store_and_assert(lab, first, [])
    own_before = stored(lab)
    other = first_personal(sibling, write_uuid=write_uuid)
    store_and_assert(sibling, other, [])
    assert stored(lab) == own_before
    assert other.receipt.revision == first.receipt.revision == 1
    assert other.receipt.event_id != first.receipt.event_id
    assert other.receipt.client_write_uuid == first.receipt.client_write_uuid


def test_executed_current_update_then_duplicate_event_failure_restores_the_old_pair(
    shared_route_lab,
):
    lab = shared_route_lab
    first = first_personal(lab)
    state, receipts = store_and_assert(lab, first, [])
    following = next_report(lab, state)
    before = stored(lab)
    native_before = native_snapshot(lab)
    statements = []

    def record(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lower().replace('"', ""))

    event.listen(lab["engine"], "after_cursor_execute", record)
    try:
        with lab["factory"]() as session:
            current = session.get(AdmissionsActionsCurrentRow, lab["case"])
            for name, value in current_values(following).items():
                setattr(current, name, value)
            session.flush()
            assert any(
                sql.lstrip().startswith("update admissions_actions_current ") for sql in statements
            )
            collision = event_values(following.receipt)
            collision["client_write_uuid"] = str(receipts[0].client_write_uuid)
            session.add(AdmissionsActionsEventRow(**collision))
            with pytest.raises(IntegrityError):
                session.flush()
            session.rollback()
    finally:
        event.remove(lab["engine"], "after_cursor_execute", record)
    assert stored(lab) == before
    assert load_validated(lab) == (state, receipts)
    assert native_snapshot(lab) == native_before


@contextmanager
def sqlite_orm_fk_off(lab):
    """Only the isolated SQLite engine; restore the native FK-on listener afterwards."""
    engine = lab["engine"]

    def disable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    event.listen(engine, "connect", disable_foreign_keys)
    engine.dispose()
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 0
        yield
    finally:
        engine.dispose()
        event.remove(engine, "connect", disable_foreign_keys)
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def erase_and_assert(lab, sibling, *, native):
    sibling_before = stored(sibling)
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, sibling["case"])
        sibling_profile = wire_values(
            {column.name: getattr(row, column.name) for column in row.__table__.columns}
        )
    if native:
        response = lab["client"].delete(f"/api/profiles/{lab['case']}")
        assert response.status_code == 204, response.text
    else:
        # Core DELETE deliberately bypasses ORM cascades, proving the migrated FKs.
        with lab["factory"]() as session:
            session.execute(
                delete(ApplicantProfileRow).where(ApplicantProfileRow.id == lab["case"])
            )
            session.commit()
    assert stored(lab) == {"current": None, "events": []}
    assert stored(sibling) == sibling_before
    with lab["factory"]() as session:
        assert session.get(ApplicantProfileRow, lab["case"]) is None
        row = session.get(ApplicantProfileRow, sibling["case"])
        assert (
            wire_values(
                {column.name: getattr(row, column.name) for column in row.__table__.columns}
            )
            == sibling_profile
        )


def test_physical_and_native_case_cascades_leave_sibling_bytes_unchanged(shared_route_lab):
    lab = shared_route_lab
    # Both backends execute FK-on physical and native cases; SQLite adds ORM FK-off.
    # There is no intentionally skipped PostgreSQL node for the SQLite-only control.
    for native in (False, True):
        own = create_profile_only(lab)
        sibling = create_profile_only(lab)
        store_and_assert(own, first_personal(own), [])
        store_and_assert(sibling, first_personal(sibling), [])
        erase_and_assert(own, sibling, native=native)
    if lab["engine"].dialect.name == "sqlite":
        own = create_profile_only(lab)
        sibling = create_profile_only(lab)
        store_and_assert(own, first_personal(own), [])
        store_and_assert(sibling, first_personal(sibling), [])
        with sqlite_orm_fk_off(lab):
            erase_and_assert(own, sibling, native=True)
        assert stored(own) == {"current": None, "events": []}
        load_validated(sibling)


def test_native_authenticated_account_erases_sole_case_and_retains_shared_actor_history(
    shared_route_lab,
):
    lab = shared_route_lab
    sibling = create_profile_only(lab)
    enable_native_auth(lab)
    full_chain(lab, local_development=False)
    first = first_personal(sibling, local_development=False)
    state, receipts = store_and_assert(sibling, first, [])
    _, receipts = store_and_assert(
        sibling, next_report(sibling, state, local_development=False), receipts
    )
    original_actor = d.actor_reference(DEV_USER_ID, DEV_ORGANIZATION_ID, local_development=False)
    assert all(receipt.actor == original_actor for receipt in receipts)
    organization_id, remaining_user = move_to_shared_organization(lab, sibling)
    before = stored(sibling)
    response, statements = _capture(
        lab,
        lambda: lab["client"].post(
            "/api/auth/me/delete",
            json={"password": SYNTHETIC_PASSWORD, "confirm_delete_data": True},
        ),
    )
    assert response.status_code == 204, response.text
    assert any("admissions_actions_events" in sql.lower() for sql in statements)
    assert stored(lab) == {"current": None, "events": []}
    assert stored(sibling) == before
    surviving_state, surviving_receipts = load_validated(sibling)
    assert surviving_state.profile_id == sibling["case"]
    assert surviving_receipts == receipts
    assert all(receipt.actor == original_actor for receipt in surviving_receipts)
    with lab["factory"]() as session:
        assert session.get(User, DEV_USER_ID) is None
        assert session.get(Organization, DEV_ORGANIZATION_ID) is None
        assert session.get(ApplicantProfileRow, lab["case"]) is None
        assert session.get(ApplicantProfileRow, sibling["case"]).organization_id == organization_id
        assert session.get(Organization, organization_id) is not None
        assert session.get(User, remaining_user) is not None
        assert session.get(OrganizationMembership, (remaining_user, organization_id)) is not None
        assert session.get(OrganizationMembership, (DEV_USER_ID, organization_id)) is None
    assert lab["client"].get(f"/api/profiles/{sibling['case']}").status_code == 401


# Additive API-writer controls. The original storage section above is preserved.
# These definitions are proposed source, not an executed contention qualification.
# Only approved existing native fixtures/harnesses are imported; the new API and
# Today test modules are deliberately not dependencies of this file.


def g3_action_endpoint(lab):
    return f"/api/profiles/{lab['case']}/admissions-actions"


def g3_action_request(lab, payload):
    return request(lab, "POST", g3_action_endpoint(lab) + "/commands", payload)


def g3_accepted_action(lab, payload):
    status, acknowledgement = g3_action_request(lab, payload)
    assert status == 200, acknowledgement
    receipt = s.ActionWriteReceiptV1.model_validate(acknowledgement)
    assert receipt.profile_id == lab["case"]
    assert receipt.request == d.validate_request(payload)
    assert receipt.receipt_digest == s.receipt_digest(receipt)
    assert receipt.canonical_request_digest == s.request_digest(lab["case"], receipt.request)
    assert s.canonical_bytes(acknowledgement) == s.canonical_bytes(receipt.model_dump(mode="json"))
    return acknowledgement


def g3_assert_accepted_sequence(lab, acknowledgements):
    state, receipts = load_validated(lab)
    assert [receipt.model_dump(mode="json") for receipt in receipts] == acknowledgements
    assert state.revision == len(acknowledgements)
    assert state.head_event_id == acknowledgements[-1]["event_id"]
    assert s.state_digest(state) == acknowledgements[-1]["after_state_digest"]
    return state, receipts


def g3_personal_command(revision=0, *, label="Entered synthetic personal task"):
    value = personal()
    value["label"] = label
    return intent("create_personal_task", revision, application_id=None, personal=value)


def g3_application_command(result_id, revision):
    return intent(
        "create_application",
        revision,
        target={
            "result_id": result_id,
            "purpose": "admission",
            "award_id": None,
            "intake": {"state": "unknown"},
            "route": {"state": "applicant_entered", "value": "Entered synthetic route"},
            "confirmed_entered_context": True,
        },
        label="Entered synthetic application",
        details=details(),
    )


def g3_expect_action_error(response, code):
    expected = d.ActionError(code)
    assert response == (expected.status, {"detail": expected.detail})


@pytest.mark.parametrize("present", [False, True])
@pytest.mark.parametrize("intent_relation", ["equal_uuid", "changed_body", "distinct_uuid"])
def test_real_g3_absent_and_present_writers_reconcile_uuid_or_reject_lost_cas(
    shared_route_lab, present, intent_relation, record_property
):
    lab = shared_route_lab
    previous = []
    if present:
        previous.append(g3_accepted_action(lab, g3_personal_command()))
    payload = g3_personal_command(int(present), label="Entered racing personal task")
    second_payload = deepcopy(payload)
    if intent_relation == "changed_body":
        second_payload["personal"]["details"]["notes"] = "Different entered synthetic note"
    elif intent_relation == "distinct_uuid":
        second_payload["client_write_uuid"] = str(uuid4())
    native_before = native_snapshot(lab)
    first, second, _ = ordered_race(
        lab,
        lambda: g3_action_request(lab, payload),
        lambda: g3_action_request(lab, second_payload),
        g2_holder_statement(lab, at_profile=True),
        g2_waiter_statement(lab, existing_legacy=False),
        record_property,
    )
    assert first[0] == 200, first[1]
    assert first[1]["request"] == d.validate_request(payload).model_dump(mode="json")
    if intent_relation == "equal_uuid":
        assert second == first  # Exact persisted ACK, including actor/time/event ID.
    else:
        g3_expect_action_error(
            second, "uuid_conflict" if intent_relation == "changed_body" else "revision_conflict"
        )
    state, _ = g3_assert_accepted_sequence(lab, [*previous, first[1]])
    assert len(state.document_tasks) == int(present) + 1
    assert len({task.id for task in state.document_tasks}) == len(state.document_tasks)
    before_replay = stored(lab)
    assert g3_action_request(lab, payload) == first
    assert stored(lab) == before_replay
    assert native_snapshot(lab) == native_before


@pytest.mark.parametrize("winner", ["legacy", "g3"])
def test_real_g3_personal_write_and_existing_native_legacy_tick_wait_in_both_orders(
    shared_route_lab, winner, record_property
):
    lab = shared_route_lab
    grant(lab, quota=0)
    response = write(lab)
    assert response.status_code == 200, response.text
    legacy = response.json()
    path, legacy_payload = native_legacy_command(lab, legacy, "tick")
    payload = g3_personal_command()
    inputs_before = unchanged_inputs(lab)
    profile_before = profile_payload(lab)

    def legacy_call():
        return request(lab, "PUT", path, legacy_payload)

    if winner == "legacy":
        old, new, _ = ordered_race(
            lab,
            legacy_call,
            lambda: g3_action_request(lab, payload),
            is_legacy_dml,
            g2_waiter_statement(lab, existing_legacy=True),
            record_property,
        )
    else:
        new, old, _ = ordered_race(
            lab,
            lambda: g3_action_request(lab, payload),
            legacy_call,
            g2_holder_statement(lab),
            is_legacy_dml,
            record_property,
        )
    assert old[0] == new[0] == 200
    state, _ = g3_assert_accepted_sequence(lab, [new[1]])
    assert state.active_preparation is None and len(state.document_tasks) == 1
    current_legacy = lab["client"].get(path)
    assert current_legacy.status_code == 200, current_legacy.text
    assert current_legacy.json()["revision"] == legacy["revision"] + 1
    assert current_legacy.json()["settings"] == old[1]["settings"]
    assert (
        current_legacy.json()["settings"]["completed_task_ids"]
        == (legacy_payload["settings"]["completed_task_ids"])
    )
    assert unchanged_inputs(lab) == inputs_before
    assert profile_payload(lab) == profile_before


@contextmanager
def g3_reject_event_insert(lab):
    """Actual isolated-DB rejection, following the approved G2 trigger control."""
    engine = lab["engine"]
    sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as connection:
        if sqlite:
            connection.exec_driver_sql(
                "CREATE TRIGGER g3_reject_event BEFORE INSERT ON admissions_actions_events "
                "BEGIN SELECT RAISE(ABORT, 'synthetic G3 event rejection'); END"
            )
        else:
            connection.exec_driver_sql(
                "CREATE FUNCTION g3_reject_event_fn() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'synthetic G3 event rejection' USING ERRCODE='23514'; END $$"
            )
            connection.exec_driver_sql(
                "CREATE TRIGGER g3_reject_event BEFORE INSERT ON admissions_actions_events "
                "FOR EACH ROW EXECUTE FUNCTION g3_reject_event_fn()"
            )
    try:
        yield
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "DROP TRIGGER IF EXISTS g3_reject_event"
                if sqlite
                else "DROP TRIGGER IF EXISTS g3_reject_event ON admissions_actions_events"
            )
            if not sqlite:
                connection.exec_driver_sql("DROP FUNCTION IF EXISTS g3_reject_event_fn()")


@pytest.mark.parametrize("present", [False, True])
def test_real_g3_event_insert_failure_rolls_back_executed_current_sql_and_retries_original_intent(
    shared_route_lab, present, record_property
):
    lab = shared_route_lab
    previous = []
    if present:
        previous.append(g3_accepted_action(lab, g3_personal_command()))
    payload = g3_personal_command(int(present), label="Entered retryable personal task")
    before = stored(lab)
    native_before = native_snapshot(lab)
    executed_current = []

    def after_current(connection, _cursor, sql, _params, _context, _many):
        value = normalized(sql)
        if value.startswith(
            ("insert into admissions_actions_current ", "update admissions_actions_current ")
        ):
            executed_current.append((id(driver(connection)), value))

    with g3_reject_event_insert(lab):
        event.listen(lab["engine"], "after_cursor_execute", after_current)
        try:
            response, statements = _capture(
                lab,
                lambda: lab["client"].post(g3_action_endpoint(lab) + "/commands", json=payload),
            )
        finally:
            event.remove(lab["engine"], "after_cursor_execute", after_current)
    assert executed_current, "The actual current INSERT/UPDATE never executed before rejection"
    assert len({connection_id for connection_id, _ in executed_current}) == 1
    writes = [
        normalized(sql) for sql in statements if normalized(sql).startswith(("insert ", "update "))
    ]
    current_index = next(i for i, sql in enumerate(writes) if "admissions_actions_current" in sql)
    event_index = next(i for i, sql in enumerate(writes) if "admissions_actions_events" in sql)
    assert current_index < event_index
    g3_expect_action_error((response.status_code, response.json()), "write_unconfirmed")
    assert "synthetic G3 event rejection" not in response.text
    assert stored(lab) == before  # Fresh Session; no half-written current or event.
    assert native_snapshot(lab) == native_before
    if previous:
        g3_assert_accepted_sequence(lab, previous)
    acknowledgement = g3_accepted_action(lab, payload)  # Same UUID, same original body.
    g3_assert_accepted_sequence(lab, [*previous, acknowledgement])
    after_retry = stored(lab)
    assert g3_action_request(lab, payload) == (200, acknowledgement)
    assert stored(lab) == after_retry and native_snapshot(lab) == native_before
    record_property(
        "g3_executed_current_rollback",
        json.dumps(
            {
                "dialect": lab["engine"].dialect.name,
                "current_connection": executed_current[0][0],
                "current_sql_executed": True,
                "event_sql_attempted": True,
                "fresh_pair_equal_after_rollback": True,
                "original_uuid_retried_exactly": True,
            },
            sort_keys=True,
        ),
    )


@pytest.mark.parametrize("winner", ["g3", "delete"])
def test_real_g3_and_native_case_erase_both_orders_preserve_sibling_and_never_resurrect(
    shared_route_lab, winner, record_property
):
    lab = shared_route_lab
    sibling = create_profile_only(lab)
    first = g3_accepted_action(lab, g3_personal_command())
    sibling_ack = g3_accepted_action(sibling, g3_personal_command())
    sibling_before = stored(sibling)
    sibling_export = sibling["client"].get(f"/api/profiles/{sibling['case']}/export")
    assert sibling_export.status_code == 200, sibling_export.text
    payload = g3_personal_command(1, label="Entered task racing case erasure")

    def delete_call():
        return request(lab, "DELETE", f"/api/profiles/{lab['case']}")

    if winner == "g3":
        new, erased, _ = ordered_race(
            lab,
            lambda: g3_action_request(lab, payload),
            delete_call,
            g2_holder_statement(lab, at_profile=True),
            g2_waiter_statement(lab, existing_legacy=False),
            record_property,
        )
        assert new[0] == 200 and new[1]["revision"] == first["revision"] + 1
        assert erased[0] == 204
    else:
        erased, new, _ = ordered_race(
            lab,
            delete_call,
            lambda: g3_action_request(lab, payload),
            g2_holder_statement(lab, at_profile=True),
            g2_waiter_statement(lab, existing_legacy=False),
            record_property,
        )
        assert erased[0] == 204 and new[0] == 404
    assert stored(lab) == {"current": None, "events": []}
    assert stored(sibling) == sibling_before
    g3_assert_accepted_sequence(sibling, [sibling_ack])
    exported_after = sibling["client"].get(f"/api/profiles/{sibling['case']}/export")
    assert exported_after.status_code == 200 and exported_after.json() == sibling_export.json()
    assert lab["client"].get(g3_action_endpoint(lab)).status_code == 404
    assert g3_action_request(lab, payload)[0] == 404
    assert stored(lab) == {"current": None, "events": []}
    with lab["factory"]() as session:
        assert session.get(ApplicantProfileRow, lab["case"]) is None
        assert session.get(ApplicantProfileRow, sibling["case"]) is not None


@pytest.mark.parametrize("winner", ["g3", "delete"])
def test_real_g3_and_authenticated_account_erase_both_orders_keep_other_member_actor_history(
    shared_route_lab, winner, record_property
):
    lab = shared_route_lab
    sibling = create_profile_only(lab)
    enable_native_auth(lab)
    first = g3_accepted_action(lab, g3_personal_command())
    sibling_ack = g3_accepted_action(sibling, g3_personal_command())
    original_actor = d.actor_reference(DEV_USER_ID, DEV_ORGANIZATION_ID, local_development=False)
    assert s.ActionWriteReceiptV1.model_validate(sibling_ack).actor == original_actor
    organization_id, remaining_user = move_to_shared_organization(lab, sibling)
    sibling_before = stored(sibling)
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, sibling["case"])
        sibling_profile = wire_values(
            {column.name: getattr(row, column.name) for column in row.__table__.columns}
        )
    payload = g3_personal_command(1, label="Entered task racing account erasure")

    def delete_call():
        return request(
            lab,
            "POST",
            "/api/auth/me/delete",
            {"password": SYNTHETIC_PASSWORD, "confirm_delete_data": True},
        )

    if winner == "g3":
        new, erased, statements = ordered_race(
            lab,
            lambda: g3_action_request(lab, payload),
            delete_call,
            g2_holder_statement(lab, at_profile=True),
            g2_waiter_statement(lab, existing_legacy=False),
            record_property,
        )
        assert new[0] == 200 and new[1]["revision"] == first["revision"] + 1
        assert erased[0] == 204
    else:
        erased, new, statements = ordered_race(
            lab,
            delete_call,
            lambda: g3_action_request(lab, payload),
            g2_holder_statement(lab, at_profile=True),
            g2_waiter_statement(lab, existing_legacy=False),
            record_property,
        )
        assert erased[0] == 204 and new[0] == 404
    if lab["engine"].dialect.name != "sqlite":
        sql = [statement for _, statement in statements]
        user_lock = next(
            i
            for i, value in enumerate(sql)
            if "from users" in value and value.endswith("for update")
        )
        org_lock = next(
            i
            for i, value in enumerate(sql)
            if "from organizations" in value and value.endswith("for update")
        )
        membership_lock = next(
            i
            for i, value in enumerate(sql)
            if "from organization_memberships" in value and value.endswith("for update")
        )
        account_profile_lock = next(
            i
            for i, value in enumerate(sql)
            if is_profile_lock(value) and "order by applicant_profiles.id" in value
        )
        assert user_lock < org_lock < membership_lock < account_profile_lock
    assert stored(lab) == {"current": None, "events": []}
    assert stored(sibling) == sibling_before
    surviving_state, surviving_receipts = g3_assert_accepted_sequence(sibling, [sibling_ack])
    assert surviving_state.profile_id == sibling["case"]
    assert all(receipt.actor == original_actor for receipt in surviving_receipts)
    with lab["factory"]() as session:
        assert session.get(User, DEV_USER_ID) is None
        assert session.get(Organization, DEV_ORGANIZATION_ID) is None
        assert session.get(ApplicantProfileRow, lab["case"]) is None
        row = session.get(ApplicantProfileRow, sibling["case"])
        assert (
            wire_values(
                {column.name: getattr(row, column.name) for column in row.__table__.columns}
            )
            == sibling_profile
        )
        assert row.organization_id == organization_id
        assert session.get(Organization, organization_id) is not None
        assert session.get(User, remaining_user) is not None
        assert session.get(OrganizationMembership, (remaining_user, organization_id)) is not None
        assert session.get(OrganizationMembership, (DEV_USER_ID, organization_id)) is None
    assert lab["client"].get(g3_action_endpoint(lab)).status_code == 401


def g3_result_with_raw_document(lab):
    """Actual selected-own fixture columns and raw checklist, never a fake preview."""
    result_id, _, _ = _selected(lab, decision="maybe")
    with lab["factory"]() as session:
        result = session.get(ProgramResultRow, result_id)
        result.checklist = DocumentChecklist(
            result_id=result.id,
            university=result.university,
            program=result.program,
            generated_at=AT,
            admission_documents=[
                DocumentItem(
                    name="Synthetic transcript for concurrency controls",
                    purpose="admission",
                    owner="applicant",
                    source_url="https://example.edu/synthetic-concurrency-transcript",
                )
            ],
            ordered_steps=["Synthetic reference only; no official verification"],
            completeness="partial",
        ).model_dump(mode="json")
        session.commit()
    return result_id


def g3_case_source_command(lab, result_id, revision):
    proposed = lab["client"].post(
        g3_action_endpoint(lab) + "/preview",
        json={
            "result_id": result_id,
            "purpose": "admission",
            "award_id": None,
            "occurrences": [{"location": "admission_documents", "index": 0}],
        },
    )
    assert proposed.status_code == 200, proposed.text
    value = proposed.json()
    assert value["profile_id"] == lab["case"] and value["result_id"] == result_id
    return intent(
        "bind_source_task",
        revision,
        application_id=None,
        source=value["selection"],
        source_preview_digest=value["source_preview_digest"],
        personal=personal(),
    )


def g3_current_source_union(state):
    return {application.target.result_id for application in state.applications} | {
        task.binding.result_id
        for task in state.document_tasks
        if task.application_id is None and task.binding is not None
    }


def test_real_g3_union_cap_19_to_20_is_atomic_and_keeps_withdrawn_unavailable_targets(
    shared_route_lab, record_property
):
    lab = shared_route_lab
    full_case(lab)
    application_targets = [_selected(lab)[0] for _ in range(18)]
    bound_target = g3_result_with_raw_document(lab)
    candidate_a, _, _ = _selected(lab)
    candidate_b, _, _ = _selected(lab, decision="maybe")
    acknowledgements = []
    for result_id in application_targets:
        acknowledgements.append(
            g3_accepted_action(lab, g3_application_command(result_id, len(acknowledgements)))
        )
    acknowledgements.append(
        g3_accepted_action(lab, g3_case_source_command(lab, bound_target, len(acknowledgements)))
    )
    first_application = acknowledgements[0]["applied_delta"]["applications"][0]["id"]
    acknowledgements.append(
        g3_accepted_action(
            lab,
            intent(
                "declare_withdrawal",
                len(acknowledgements),
                application_id=first_application,
                withdrawal={
                    "entered_at": None,
                    "notes": "Applicant-reported synthetic withdrawal",
                    "confirmed_applicant_declaration": True,
                },
            ),
        )
    )
    with lab["factory"]() as session:
        session.execute(
            delete(ProgramResultRow).where(ProgramResultRow.id == application_targets[0])
        )
        session.commit()
        assert session.get(ProgramResultRow, application_targets[0]) is None
    before_race = native_snapshot(lab)
    state, _ = g3_assert_accepted_sequence(lab, acknowledgements)
    assert len(state.applications) == 18 and len(state.document_tasks) == 1
    assert state.applications[0].status == "withdrawn_declared"
    assert len(g3_current_source_union(state)) == 19
    payload_a = g3_application_command(candidate_a, state.revision)
    payload_b = g3_application_command(candidate_b, state.revision)
    first, second, _ = ordered_race(
        lab,
        lambda: g3_action_request(lab, payload_a),
        lambda: g3_action_request(lab, payload_b),
        g2_holder_statement(lab, at_profile=True),
        g2_waiter_statement(lab, existing_legacy=False),
        record_property,
    )
    assert first[0] == 200, first[1]
    g3_expect_action_error(second, "revision_conflict")
    acknowledgements.append(first[1])
    state, _ = g3_assert_accepted_sequence(lab, acknowledgements)
    assert len(state.applications) == 19  # A 20th application itself would still be permitted.
    assert len(g3_current_source_union(state)) == 20
    assert application_targets[0] in g3_current_source_union(state)
    assert bound_target in g3_current_source_union(state)
    accepted_pair = stored(lab)
    fresh_reviewed_b = deepcopy(payload_b)
    fresh_reviewed_b["expected_revision"] = state.revision
    fresh_reviewed_b["client_write_uuid"] = str(uuid4())
    g3_expect_action_error(g3_action_request(lab, fresh_reviewed_b), "limit_exceeded")
    assert stored(lab) == accepted_pair
    acknowledgements.append(
        g3_accepted_action(lab, g3_case_source_command(lab, bound_target, state.revision))
    )
    state, _ = g3_assert_accepted_sequence(lab, acknowledgements)
    assert len(state.applications) == 19 and len(state.document_tasks) == 2
    assert len(g3_current_source_union(state)) == 20
    assert all(task.application_id is None for task in state.document_tasks)
    assert native_snapshot(lab) == before_race

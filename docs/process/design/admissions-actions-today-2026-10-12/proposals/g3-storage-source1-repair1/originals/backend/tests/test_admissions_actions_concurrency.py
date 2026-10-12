"""Migrated G3 storage controls; synthetic records and native erase routes.

Reuse the approved two-database lab, its no-lifespan client and no-IP/DNS guard.
The storage helper below is test setup, not a G3 API, fence or concurrency proof.
No provider, official admissions evidence, production data or writer race is used.
This external source proposal has not been imported, collected or run by its author.
"""

from __future__ import annotations

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
    enable_native_auth,
    move_to_shared_organization,
)
from tests.test_shared_route_api import accepted, route_input
from tests.test_study_schedule_api import write

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
        key: ensure_utc(value).isoformat() if isinstance(value, datetime) else deepcopy(value)
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
        "client_write_uuid": receipt.client_write_uuid,
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
    first_calendar = write(lab)
    assert first_calendar.status_code == 200, first_calendar.text
    marked = deepcopy(first_calendar.json()["settings"])
    marked["completed_task_ids"] = [first_calendar.json()["schedule"]["tasks"][0]["id"]]
    assert write(lab, revision=1, plan=marked).status_code == 200
    saved_path = learning_save(lab, learning_preview(lab, 2))
    assert saved_path.status_code == 200, saved_path.text
    accepted(lab, route_input(lab, result_ids=[result_id]))
    with lab["factory"]() as session:
        calendar = session.query(StudyScheduleRow).filter_by(profile_id=lab["case"]).one()
        assert calendar.learning_path is not None and calendar.settings == marked
    before = native_snapshot(lab)
    assert before["shared_route_current"] and before["shared_route_history"]
    migrate(lab, HEAD)
    assert TABLES <= set(inspect(lab["engine"]).get_table_names())
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
        receipt["client_write_uuid"] = first.receipt.client_write_uuid
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
            collision["client_write_uuid"] = receipts[0].client_write_uuid
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

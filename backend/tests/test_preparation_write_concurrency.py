"""Proposed physical write-fence controls. EXTERNAL / NOT_APPLIED / NOT_RUN.

Native HTTP, migrated file SQLite/private-Unix PostgreSQL and actual SQL waits.
Events pause an already executed holder statement; they never emulate a lock,
replace a route/helper, waive a network guard or synchronize two post-lock writers.
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta
from threading import Event, Lock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from app.api.preparation_transactions import begin_owned_preparation_write
from app.config import get_settings
from app.main import app
from app.models import (
    ApplicantProfileRow,
    AuditEvent,
    AuthSession,
    Organization,
    OrganizationMembership,
    StudyScheduleRow,
    Subscription,
    User,
)
from app.models.base import ensure_utc, utcnow
from app.security import (
    DEV_ORGANIZATION_ID,
    DEV_USER_ID,
    Principal,
    hash_password,
    token_hash,
)
from tests.test_preparation_api import body, grant, url
from tests.test_preparation_graph_api import _capture, _snapshot
from tests.test_shared_route_api import (
    accepted,
    command,
    endpoint,
    preview,
    route_input,
    stored_routes,
)
from tests.test_study_schedule_api import unchanged_inputs, write

pytest_plugins = ("tests.test_preparation_api", "tests.test_shared_route_api")

SYNTHETIC_PASSWORD = "Synthetic-case-delete-2026!"


def normalized(sql):
    return re.sub(r"\s+", " ", sql.lower().replace('"', "")).strip()


def driver(connection):
    return connection.connection.driver_connection


def backend_pid(connection):
    raw = driver(connection)
    if hasattr(raw, "info"):
        return raw.info.backend_pid
    return raw.get_backend_pid()


def is_profile_lock(sql):
    value = normalized(sql)
    return "from applicant_profiles" in value and value.endswith("for update")


def is_legacy_lock(sql):
    value = normalized(sql)
    return "from study_schedules" in value and value.endswith("for update")


def is_legacy_dml(sql):
    return bool(
        re.match(r"(?:update study_schedules|insert into study_schedules)\b", normalized(sql))
    )


def is_immediate(sql):
    return normalized(sql) == "begin immediate"


class NativeSqlRace:
    """Bounded pause + independent observation of an actual waiting connection."""

    def __init__(self, lab, holder_statement, waiter_statement):
        self.engine = lab["engine"]
        self.sqlite = self.engine.dialect.name == "sqlite"
        self.holder_statement = holder_statement
        self.waiter_statement = waiter_statement
        self.held = Event()
        self.release = Event()
        self.attempted = Event()
        self.driver_entered = Event()
        self.finished_wait = Event()
        self.mutex = Lock()
        self.holder_id = None
        self.waiter_id = None
        self.holder_pid = None
        self.waiter_pid = None
        self.raw_waiter = None
        self.events = []
        self.evidence = None

    def before(self, connection, _cursor, sql, _params, _context, _many):
        value = normalized(sql)
        raw = driver(connection)
        with self.mutex:
            self.events.append((id(raw), value))
            should_watch = (
                self.held.is_set()
                and id(raw) != self.holder_id
                and self.waiter_id is None
                and self.waiter_statement(value)
            )
            if should_watch:
                self.waiter_id = id(raw)
                if self.sqlite:
                    self.raw_waiter = raw

                    def trace(actual_sql):
                        if self.waiter_statement(normalized(actual_sql)):
                            self.driver_entered.set()

                    raw.set_trace_callback(trace)
                else:
                    self.waiter_pid = backend_pid(connection)
                self.attempted.set()

    def after(self, connection, _cursor, sql, _params, _context, _many):
        raw_id = id(driver(connection))
        should_hold = False
        with self.mutex:
            if self.holder_id is None and self.holder_statement(normalized(sql)):
                self.holder_id = raw_id
                if not self.sqlite:
                    self.holder_pid = backend_pid(connection)
                should_hold = True
                self.held.set()
            elif raw_id == self.waiter_id and self.waiter_statement(normalized(sql)):
                self.finished_wait.set()
        if should_hold:
            assert self.release.wait(12), "Holder release was not delivered"

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self.before)
        event.listen(self.engine, "after_cursor_execute", self.after)
        return self

    def __exit__(self, *_exc):
        self.release.set()
        event.remove(self.engine, "before_cursor_execute", self.before)
        event.remove(self.engine, "after_cursor_execute", self.after)
        if self.raw_waiter is not None:
            self.raw_waiter.set_trace_callback(None)

    def prove_wait(self, waiter_future):
        assert self.attempted.wait(3), "Waiter never reached the actual guarded SQL"
        assert self.waiter_id != self.holder_id
        assert not self.finished_wait.is_set() and not waiter_future.done()
        if self.sqlite:
            assert self.driver_entered.wait(3), "Only a Python callback ran; SQLite never stepped"
            with self.engine.connect() as connection:
                observer_id = id(driver(connection))
                assert observer_id not in {self.holder_id, self.waiter_id}
                connection.exec_driver_sql("PRAGMA busy_timeout=0")
                try:
                    with pytest.raises(OperationalError, match="locked"):
                        connection.exec_driver_sql("BEGIN IMMEDIATE")
                finally:
                    connection.rollback()
                    connection.exec_driver_sql("PRAGMA busy_timeout=15000")
            self.evidence = {
                "dialect": "sqlite",
                "holder": self.holder_id,
                "waiter": self.waiter_id,
                "observer": observer_id,
                "driver_entered": True,
                "independent_reservation": "SQLITE_BUSY",
                "first_waiter_guard": "BEGIN IMMEDIATE"
                if self.waiter_statement("begin immediate")
                else "legacy DML",
            }
        else:
            deadline = time.monotonic() + 2
            observation = None
            with self.engine.connect() as connection:
                observer_id = id(driver(connection))
                assert observer_id not in {self.holder_id, self.waiter_id}
                while time.monotonic() < deadline:
                    connection.execute(text("SELECT pg_stat_clear_snapshot()"))
                    row = (
                        connection.execute(
                            text(
                                "SELECT wait_event_type, pg_blocking_pids(pid) AS blockers, "
                                "EXISTS(SELECT 1 FROM pg_locks WHERE pid=:waiter AND NOT granted) AS ungranted "
                                "FROM pg_stat_activity WHERE pid=:waiter"
                            ),
                            {"waiter": self.waiter_pid},
                        )
                        .mappings()
                        .one()
                    )
                    if (
                        row["wait_event_type"] == "Lock"
                        and self.holder_pid in row["blockers"]
                        and row["ungranted"]
                    ):
                        observation = dict(row)
                        break
                    time.sleep(0.01)
            assert observation is not None, "No native pg_locks/blocking-pid evidence"
            self.evidence = {
                "dialect": "postgresql",
                "holder": self.holder_id,
                "waiter": self.waiter_id,
                "holder_pid": self.holder_pid,
                "waiter_pid": self.waiter_pid,
                "observer": observer_id,
                "wait_event_type": observation["wait_event_type"],
                "blockers": observation["blockers"],
                "ungranted": observation["ungranted"],
            }
        assert not self.finished_wait.is_set() and not waiter_future.done()


def request(lab, method, path, payload=None):
    # No context manager: entering the application lifespan starts worker logic.
    client = TestClient(app)
    client.cookies.update(lab["client"].cookies)
    try:
        response = client.request(method, path, json=payload)
        return response.status_code, response.json() if response.content else None
    finally:
        client.close()


def ordered_race(
    lab, holder_call, waiter_call, holder_statement, waiter_statement, record_property
):
    with (
        NativeSqlRace(lab, holder_statement, waiter_statement) as race,
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        first = pool.submit(holder_call)
        try:
            assert race.held.wait(3), "Holder never acquired its native fence"
            second = pool.submit(waiter_call)
            race.prove_wait(second)
        finally:
            race.release.set()
        holder_result = first.result(timeout=8)
        waiter_result = second.result(timeout=8)
    record_property("physical_write_wait", json.dumps(race.evidence, sort_keys=True))
    assert race.finished_wait.is_set()
    return holder_result, waiter_result, race.events


def g2_holder_statement(lab, *, at_profile=False):
    return (
        is_immediate
        if lab["engine"].dialect.name == "sqlite"
        else is_profile_lock
        if at_profile
        else is_legacy_lock
    )


def g2_waiter_statement(lab, *, existing_legacy):
    return (
        is_immediate
        if lab["engine"].dialect.name == "sqlite"
        else is_legacy_lock
        if existing_legacy
        else is_profile_lock
    )


def profile_payload(lab):
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, lab["case"])
        return deepcopy(row.payload), row.updated_at


def native_legacy_command(lab, legacy, mode):
    if mode == "v2":
        from tests.test_learning_schedule_api import endpoint as learning_endpoint
        from tests.test_learning_schedule_api import preview as learning_preview

        proposed = learning_preview(lab, legacy["revision"])
        return (
            learning_endpoint(lab),
            {
                "expected_revision": proposed["revision"],
                "legacy_fingerprint": proposed["legacy_fingerprint"],
                "draft": proposed["learning_path"]["draft"],
            },
        )
    changed = deepcopy(legacy["settings"])
    if mode == "tick":
        changed["completed_task_ids"] = [legacy["schedule"]["tasks"][0]["id"]]
    else:
        changed["weekly_minutes"] += 60
    return url(lab, "schedule"), {"expected_revision": legacy["revision"], "settings": changed}


@pytest.mark.parametrize("winner", ["legacy", "shared"])
@pytest.mark.parametrize("mode", ["tick", "structural", "v2"])
def test_existing_native_legacy_writer_and_shared_save_wait_without_lost_preview_or_second_budget(
    shared_route_lab, winner, mode, record_property
):
    lab = shared_route_lab
    grant(lab, quota=0)
    legacy = write(lab).json()
    value = route_input(lab)
    payload = command(value, preview(lab, value))
    path, legacy_payload = native_legacy_command(lab, legacy, mode)
    before = unchanged_inputs(lab)
    saved_profile = profile_payload(lab)

    def g2_call():
        return request(lab, "PUT", endpoint(lab), payload)

    def legacy_call():
        return request(lab, "PUT", path, legacy_payload)

    if winner == "legacy":
        old, new, _ = ordered_race(
            lab,
            legacy_call,
            g2_call,
            is_legacy_dml,
            g2_waiter_statement(lab, existing_legacy=True),
            record_property,
        )
        assert old[0] == 200 and new[0] == 409
        assert stored_routes(lab) == {"current": None, "history": []}
    else:
        new, old, _ = ordered_race(
            lab,
            g2_call,
            legacy_call,
            g2_holder_statement(lab),
            is_legacy_dml,
            record_property,
        )
        assert new[0] == old[0] == 200
        view = lab["client"].get(endpoint(lab)).json()["view"]
        assert view["receipt"] == new[1]
        assert new[1]["legacy_anchor"]["technical_revision"] == 1
        assert view["current_status"]["legacy_structure"] == (
            "changed" if mode == "structural" else "unchanged"
        )
        assert view["current_status"]["imported_refs"] == "not_used"
        assert all(slot["completion"] == "not_projected" for slot in new[1]["allocation"]["slots"])
    assert lab["client"].get(url(lab, "schedule")).json()["revision"] == 2
    assert unchanged_inputs(lab) == before and profile_payload(lab) == saved_profile


@pytest.mark.parametrize("winner", ["legacy", "shared"])
def test_absent_native_legacy_row_first_insert_serializes_through_immediate_parent_fk(
    shared_route_lab, winner, record_property
):
    from tests.test_study_schedule_api import settings

    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    payload = command(value, preview(lab, value))
    before = unchanged_inputs(lab)
    saved_profile = profile_payload(lab)
    legacy_payload = {"expected_revision": 0, "settings": settings()}

    def g2_call():
        return request(lab, "PUT", endpoint(lab), payload)

    def legacy_call():
        return request(lab, "PUT", url(lab, "schedule"), legacy_payload)

    if winner == "legacy":
        old, new, _ = ordered_race(
            lab,
            legacy_call,
            g2_call,
            is_legacy_dml,
            g2_waiter_statement(lab, existing_legacy=False),
            record_property,
        )
        assert old[0] == 200 and new[0] == 409
        assert stored_routes(lab) == {"current": None, "history": []}
    else:
        new, old, _ = ordered_race(
            lab,
            g2_call,
            legacy_call,
            g2_holder_statement(lab),
            is_legacy_dml,
            record_property,
        )
        assert new[0] == old[0] == 200
        assert new[1]["legacy_anchor"]["technical_revision"] == 0
        assert lab["client"].get(endpoint(lab)).json()["view"]["receipt"] == new[1]
    with lab["factory"]() as session:
        assert session.query(StudyScheduleRow).filter_by(profile_id=lab["case"]).count() == 1
    assert unchanged_inputs(lab) == before and profile_payload(lab) == saved_profile


@pytest.mark.parametrize("prep_lab", ["postgres"], indirect=True)
def test_pg_fk_is_immediate_and_weaker_parent_lock_really_does_not_fence_first_native_insert(
    shared_route_lab, record_property
):
    from tests.test_study_schedule_api import settings

    lab = shared_route_lab
    grant(lab)
    with lab["engine"].connect() as connection:
        constraint = (
            connection.execute(
                text(
                    "SELECT condeferrable, condeferred, convalidated FROM pg_constraint "
                    "WHERE conrelid='study_schedules'::regclass AND confrelid='applicant_profiles'::regclass AND contype='f'"
                )
            )
            .mappings()
            .one()
        )
        assert dict(constraint) == {
            "condeferrable": False,
            "condeferred": False,
            "convalidated": True,
        }
    # Negative control, never a production fallback: this weaker lock is compatible
    # with the real FK's KEY SHARE, so the native first INSERT commits while held.
    with lab["factory"]() as holder:
        holder.execute(
            text("SELECT id FROM applicant_profiles WHERE id=:case FOR NO KEY UPDATE"),
            {"case": lab["case"]},
        ).one()
        holder_pid = backend_pid(holder.connection())
        with ThreadPoolExecutor(max_workers=1) as pool:
            response = pool.submit(
                lambda: request(
                    lab,
                    "PUT",
                    url(lab, "schedule"),
                    {
                        "expected_revision": 0,
                        "settings": settings(),
                    },
                )
            ).result(timeout=3)
        assert response[0] == 200 and holder.in_transaction()
        holder.rollback()
    record_property(
        "weak_lock_negative_control",
        json.dumps(
            {
                "holder_pid": holder_pid,
                "lock": "FOR NO KEY UPDATE",
                "native_first_insert": "committed_while_held",
            }
        ),
    )


@pytest.mark.parametrize(
    "kind", ["same_intent", "same_uuid_different_intent", "different_uuid_same_revision"]
)
def test_native_two_delivery_race_reconciles_original_uuid_and_rejects_other_cas_intent(
    shared_route_lab, kind, record_property
):
    lab = shared_route_lab
    subscription = grant(lab)
    value = route_input(lab)
    payload = command(value, preview(lab, value))
    other = deepcopy(payload)
    if kind == "same_uuid_different_intent":
        other["applicant_input"]["shared_weekly_minutes"] += 30
    elif kind == "different_uuid_same_revision":
        other["client_write_uuid"] = str(uuid4())
    first, second, _ = ordered_race(
        lab,
        lambda: request(lab, "PUT", endpoint(lab), payload),
        lambda: request(lab, "PUT", endpoint(lab), other),
        g2_holder_statement(lab),
        g2_waiter_statement(lab, existing_legacy=False),
        record_property,
    )
    assert first[0] == 200
    if kind == "same_intent":
        assert second == first
    else:
        assert second[0] == 409
        expected = (
            "shared_route_uuid_conflict"
            if kind == "same_uuid_different_intent"
            else "shared_route_revision_conflict"
        )
        assert second[1]["detail"]["code"] == expected
    state = stored_routes(lab)
    assert len(state["history"]) == 1 and state["current"]["snapshot"] == first[1]
    with lab["factory"]() as session:
        session.get(Subscription, subscription).ends_at = utcnow() - timedelta(days=1)
        session.commit()
    assert lab["client"].put(endpoint(lab), json=payload).json() == first[1]
    assert stored_routes(lab) == state


def test_real_save_between_export_current_and_history_refuses_mixed_revision_without_write(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    _, first = accepted(lab, value)
    changed = deepcopy(value)
    changed["shared_weekly_minutes"] += 30
    payload = command(changed, preview(lab, changed, 1))
    held = Event()
    release = Event()
    mutex = Lock()
    export_connection = []

    def after(connection, _cursor, sql, _params, _context, _many):
        value = normalized(sql)
        should_hold = False
        with mutex:
            if (
                not export_connection
                and "left outer join shared_route_current" in value
                and "max(shared_route_history.revision)" in value
            ):
                export_connection.append(id(driver(connection)))
                should_hold = True
                held.set()
        if should_hold:
            assert release.wait(12), "Export snapshot release was not delivered"

    event.listen(lab["engine"], "after_cursor_execute", after)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            export = pool.submit(lambda: request(lab, "GET", f"/api/profiles/{lab['case']}/export"))
            try:
                assert held.wait(3), "Exporter did not capture current revision 1"
                saved = lab["client"].put(endpoint(lab), json=payload)
                assert saved.status_code == 200, saved.text
                second = saved.json()
                assert second["revision"] == 2
                before_read_finish = _snapshot(lab)
            finally:
                release.set()
            status, error = export.result(timeout=8)
    finally:
        release.set()
        event.remove(lab["engine"], "after_cursor_execute", after)
    assert status == 503 and error["detail"]["code"] == "shared_route_saved_unreadable"
    assert _snapshot(lab) == before_read_finish
    fresh = lab["client"].get(f"/api/profiles/{lab['case']}/export")
    assert fresh.status_code == 200, fresh.text
    assert fresh.json()["shared_route_current"] == second
    assert fresh.json()["shared_route_history"] == [first, second]


def development_principal():
    return Principal(
        DEV_USER_ID, DEV_ORGANIZATION_ID, "local@unimatch.invalid", "Local user", "owner", True
    )


def test_clean_auth_read_autobegin_is_discarded_before_actual_guard_and_parent_has_no_timestamp_write(
    shared_route_lab, record_property
):
    lab = shared_route_lab
    original = profile_payload(lab)
    statements = []

    def capture(_connection, _cursor, sql, _params, _context, _many):
        statements.append(normalized(sql))

    with lab["factory"]() as session:
        session.query(User.id).filter_by(
            id=DEV_USER_ID
        ).one()  # Native clean dependency read/autobegin.
        assert session.in_transaction() and not session.dirty
        event.listen(lab["engine"], "before_cursor_execute", capture)
        try:
            begin_owned_preparation_write(session, lab["case"], development_principal())
            if lab["engine"].dialect.name == "sqlite":
                assert statements[0] == "begin immediate"
            else:
                assert statements[0] == "set local lock_timeout = '5s'"
                assert statements[1] == "show transaction_isolation"
                assert (
                    session.execute(text("SHOW transaction_isolation")).scalar_one()
                    == "read committed"
                )
                assert any(
                    is_profile_lock(sql) and "for no key update" not in sql for sql in statements
                )
            assert not any(re.match(r"(?:insert|update|delete)\b", sql) for sql in statements)
        finally:
            session.rollback()
            event.remove(lab["engine"], "before_cursor_execute", capture)
    assert profile_payload(lab) == original
    record_property("first_guarded_sql", statements[0])


@pytest.mark.parametrize("pending", ["new", "dirty", "deleted"])
def test_dirty_dependency_session_is_refused_before_sql_and_preserves_pending_changes(
    shared_route_lab, pending
):
    lab = shared_route_lab
    before = _snapshot(lab)
    with lab["factory"]() as session:
        row = session.get(ApplicantProfileRow, lab["case"])
        if pending == "new":
            session.add(Organization(name="Unrelated pending synthetic mutation", slug=uuid4().hex))
        elif pending == "dirty":
            row.payload = {**row.payload, "synthetic_pending": True}
        else:
            session.delete(row)
        original_state = (set(session.new), set(session.dirty), set(session.deleted))
        sql = []

        def capture(_connection, _cursor, statement, _params, _context, _many):
            sql.append(statement)

        event.listen(lab["engine"], "before_cursor_execute", capture)
        try:
            with pytest.raises(HTTPException) as refusal:
                begin_owned_preparation_write(session, lab["case"], development_principal())
            assert refusal.value.status_code == 503
            assert (set(session.new), set(session.dirty), set(session.deleted)) == original_state
            assert sql == []
        finally:
            event.remove(lab["engine"], "before_cursor_execute", capture)
            session.rollback()
    assert _snapshot(lab) == before


def enable_native_auth(lab, *, stale=False):
    raw_cookie = "synthetic-g2-cookie-" + uuid4().hex
    with lab["factory"]() as session:
        user = session.get(User, DEV_USER_ID)
        user.password_hash = hash_password(SYNTHETIC_PASSWORD, n=2**14)
        auth = AuthSession(
            user_id=DEV_USER_ID,
            organization_id=DEV_ORGANIZATION_ID,
            token_hash=token_hash(raw_cookie),
            expires_at=utcnow() + timedelta(days=1),
            last_seen_at=utcnow() - timedelta(minutes=20 if stale else 1),
        )
        session.add(auth)
        session.commit()
        auth_id = auth.id
    lab["monkeypatch"].setenv("UNIMATCH_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    lab["client"].cookies.set(get_settings().session_cookie_name, raw_cookie)
    return auth_id


@pytest.mark.parametrize("stale", [False, True])
def test_actual_cookie_auth_clean_read_or_last_seen_commit_then_fresh_native_shared_write(
    shared_route_lab, stale, record_property
):
    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    payload = command(value, preview(lab, value))
    auth_id = enable_native_auth(lab, stale=stale)
    before = profile_payload(lab)
    response, sql = _capture(lab, lambda: lab["client"].put(endpoint(lab), json=payload))
    assert response.status_code == 200, response.text
    statements = [normalized(statement) for statement in sql]
    assert any("from auth_sessions" in statement for statement in statements)
    seen_updates = [
        i for i, statement in enumerate(statements) if statement.startswith("update auth_sessions ")
    ]
    assert bool(seen_updates) is stale
    guard = (
        "begin immediate"
        if lab["engine"].dialect.name == "sqlite"
        else "set local lock_timeout = '5s'"
    )
    guard_index = statements.index(guard)
    if stale:
        assert seen_updates[-1] < guard_index
    assert profile_payload(lab) == before
    with lab["factory"]() as session:
        auth = session.get(AuthSession, auth_id)
        assert utcnow() - ensure_utc(auth.last_seen_at) < timedelta(minutes=15)
    record_property(
        "native_auth_guard",
        json.dumps(
            {
                "stale_last_seen": stale,
                "first_guard_index": guard_index,
                "auth_dependency_dml_indices": seen_updates,
            }
        ),
    )


def test_real_bounded_lock_failure_returns_unconfirmed_and_release_allows_original_intent_once(
    shared_route_lab, record_property
):
    lab = shared_route_lab
    grant(lab)
    value = route_input(lab)
    payload = command(value, preview(lab, value))
    started = time.monotonic()
    with lab["factory"]() as holder:
        begin_owned_preparation_write(holder, lab["case"], development_principal())
        holder_id = id(driver(holder.connection()))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(lambda: request(lab, "PUT", endpoint(lab), payload))
            response = future.result(timeout=20)
        duration = time.monotonic() - started
        assert response[0] == 503 and "confirmed" in str(response[1]).lower()
        assert 3 <= duration <= (19 if lab["engine"].dialect.name == "sqlite" else 8)
        assert stored_routes(lab) == {"current": None, "history": []}
        holder.rollback()
    retry = lab["client"].put(endpoint(lab), json=payload)
    assert retry.status_code == 200, retry.text
    assert len(stored_routes(lab)["history"]) == 1
    assert lab["client"].put(endpoint(lab), json=payload).json() == retry.json()
    record_property(
        "real_lock_failure",
        json.dumps(
            {
                "holder": holder_id,
                "elapsed_seconds": duration,
                "status": response[0],
                "same_intent_after_release": retry.status_code,
            }
        ),
    )


def create_sibling(lab):
    value, _ = profile_payload(lab)
    response = lab["client"].post("/api/profiles", json=value)
    assert response.status_code == 201
    other = {**lab, "case": response.json()["id"]}
    accepted(other, route_input(other))
    assert write(other).status_code == 200
    assert other["client"].post(url(other, "attempts"), json=body()).status_code == 200
    return other


@pytest.mark.parametrize("winner", ["shared", "delete"])
def test_native_case_delete_and_shared_write_both_orders_never_resurrect_case_or_erase_sibling(
    shared_route_lab, winner, record_property
):
    lab = shared_route_lab
    grant(lab)
    other = create_sibling(lab)
    sibling_before = stored_routes(other)
    sibling_export = other["client"].get(f"/api/profiles/{other['case']}/export").json()
    assert write(lab).status_code == 200
    assert lab["client"].post(url(lab, "attempts"), json=body()).status_code == 200
    value = route_input(lab)
    payload = command(value, preview(lab, value))

    def g2_call():
        return request(lab, "PUT", endpoint(lab), payload)

    def delete_call():
        return request(lab, "DELETE", f"/api/profiles/{lab['case']}")

    if winner == "shared":
        new, erased, _ = ordered_race(
            lab,
            g2_call,
            delete_call,
            g2_holder_statement(lab, at_profile=True),
            g2_waiter_statement(lab, existing_legacy=False),
            record_property,
        )
        assert new[0] == 200 and erased[0] == 204
    else:
        erased, new, _ = ordered_race(
            lab,
            delete_call,
            g2_call,
            g2_holder_statement(lab, at_profile=True),
            g2_waiter_statement(lab, existing_legacy=False),
            record_property,
        )
        assert erased[0] == 204 and new[0] == 404
    assert lab["client"].get(endpoint(lab)).status_code == 404
    assert stored_routes(lab) == {"current": None, "history": []}
    assert stored_routes(other) == sibling_before
    assert other["client"].get(f"/api/profiles/{other['case']}/export").json() == sibling_export
    with lab["factory"]() as session:
        assert session.get(ApplicantProfileRow, lab["case"]) is None
        assert session.query(StudyScheduleRow).filter_by(profile_id=lab["case"]).count() == 0


def move_to_shared_organization(lab, other):
    with lab["factory"]() as session:
        organization = Organization(name="Surviving synthetic shared workspace", slug=uuid4().hex)
        user = User(
            email=f"remaining-{uuid4().hex}@example.invalid",
            display_name="Remaining synthetic member",
            password_hash="disabled",
        )
        session.add_all([organization, user])
        session.flush()
        session.add_all(
            [
                OrganizationMembership(
                    user_id=DEV_USER_ID, organization_id=organization.id, role="member"
                ),
                OrganizationMembership(
                    user_id=user.id, organization_id=organization.id, role="owner"
                ),
            ]
        )
        session.get(ApplicantProfileRow, other["case"]).organization_id = organization.id
        session.commit()
        return organization.id, user.id


@pytest.mark.parametrize("winner", ["shared", "delete"])
def test_actual_authenticated_account_erase_orders_preserve_other_member_workspace(
    shared_route_lab, winner, record_property
):
    lab = shared_route_lab
    grant(lab)
    other = create_sibling(lab)
    organization_id, remaining_user = move_to_shared_organization(lab, other)
    sibling_before = stored_routes(other)
    with lab["factory"]() as session:
        sibling_calendar = deepcopy(
            session.query(StudyScheduleRow).filter_by(profile_id=other["case"]).one().settings
        )
    assert write(lab).status_code == 200
    value = route_input(lab)
    payload = command(value, preview(lab, value))
    enable_native_auth(lab)

    def g2_call():
        return request(lab, "PUT", endpoint(lab), payload)

    def delete_call():
        return request(
            lab,
            "POST",
            "/api/auth/me/delete",
            {"password": SYNTHETIC_PASSWORD, "confirm_delete_data": True},
        )

    if winner == "shared":
        new, erased, statements = ordered_race(
            lab,
            g2_call,
            delete_call,
            g2_holder_statement(lab, at_profile=True),
            g2_waiter_statement(lab, existing_legacy=False),
            record_property,
        )
        assert new[0] == 200 and erased[0] == 204
    else:
        erased, new, statements = ordered_race(
            lab,
            delete_call,
            g2_call,
            g2_holder_statement(lab, at_profile=True),
            g2_waiter_statement(lab, existing_legacy=False),
            record_property,
        )
        assert erased[0] == 204 and new[0] == 404
    if lab["engine"].dialect.name != "sqlite":
        holder_or_waiter_sql = [sql for _, sql in statements]
        user_lock = next(
            i
            for i, sql in enumerate(holder_or_waiter_sql)
            if "from users" in sql and sql.endswith("for update")
        )
        org_lock = next(
            i
            for i, sql in enumerate(holder_or_waiter_sql)
            if "from organizations" in sql and sql.endswith("for update")
        )
        membership_lock = next(
            i
            for i, sql in enumerate(holder_or_waiter_sql)
            if "from organization_memberships" in sql and sql.endswith("for update")
        )
        account_profile = next(
            i
            for i, sql in enumerate(holder_or_waiter_sql)
            if is_profile_lock(sql) and "order by applicant_profiles.id" in sql
        )
        assert user_lock < org_lock < membership_lock < account_profile
    assert stored_routes(lab) == {"current": None, "history": []}
    assert stored_routes(other) == sibling_before
    with lab["factory"]() as session:
        assert session.get(User, DEV_USER_ID) is None
        assert session.get(Organization, DEV_ORGANIZATION_ID) is None
        assert session.get(ApplicantProfileRow, lab["case"]) is None
        assert session.get(Organization, organization_id) is not None
        assert session.get(User, remaining_user) is not None
        assert session.get(OrganizationMembership, (remaining_user, organization_id)) is not None
        assert (
            session.query(StudyScheduleRow).filter_by(profile_id=other["case"]).one().settings
            == sibling_calendar
        )
    assert lab["client"].get(endpoint(lab)).status_code == 401


@contextmanager
def reject_user_erase(lab):
    engine = lab["engine"]
    sqlite = engine.dialect.name == "sqlite"
    with engine.begin() as connection:
        if sqlite:
            connection.exec_driver_sql(
                "CREATE TRIGGER g2_reject_user_erase BEFORE DELETE ON users BEGIN SELECT RAISE(ABORT, 'synthetic user erasure rejection'); END"
            )
        else:
            connection.exec_driver_sql(
                "CREATE FUNCTION g2_reject_user_erase_fn() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic user erasure rejection' USING ERRCODE='23514'; END $$"
            )
            connection.exec_driver_sql(
                "CREATE TRIGGER g2_reject_user_erase BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION g2_reject_user_erase_fn()"
            )
    try:
        yield
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "DROP TRIGGER IF EXISTS g2_reject_user_erase"
                if sqlite
                else "DROP TRIGGER IF EXISTS g2_reject_user_erase ON users"
            )
            if not sqlite:
                connection.exec_driver_sql("DROP FUNCTION IF EXISTS g2_reject_user_erase_fn()")


def test_real_account_erase_failure_after_audit_flush_rolls_back_everything_and_keeps_session(
    shared_route_lab,
):
    lab = shared_route_lab
    grant(lab)
    _, receipt = accepted(lab, route_input(lab))
    assert write(lab).status_code == 200
    assert lab["client"].post(url(lab, "attempts"), json=body()).status_code == 200
    enable_native_auth(lab)
    before = _snapshot(lab)
    cookie = lab["client"].cookies.get(get_settings().session_cookie_name)
    with reject_user_erase(lab):
        response, statements = _capture(
            lab,
            lambda: lab["client"].post(
                "/api/auth/me/delete",
                json={"password": SYNTHETIC_PASSWORD, "confirm_delete_data": True},
            ),
        )
    assert response.status_code == 503 and "synthetic user erasure rejection" not in response.text
    sql = [normalized(statement) for statement in statements]
    audit_write = next(
        i for i, statement in enumerate(sql) if statement.startswith("insert into audit_events")
    )
    user_delete = next(
        i for i, statement in enumerate(sql) if statement.startswith("delete from users")
    )
    assert audit_write < user_delete
    assert "set-cookie" not in response.headers
    assert lab["client"].cookies.get(get_settings().session_cookie_name) == cookie
    assert _snapshot(lab) == before
    assert lab["client"].get(endpoint(lab)).json()["view"]["receipt"] == receipt
    with lab["factory"]() as session:
        assert session.query(AuditEvent).filter_by(action="account_deleted").count() == 0
    bad = lab["client"].post(
        "/api/auth/me/delete",
        json={"password": "Wrong-synthetic-password!", "confirm_delete_data": True},
    )
    assert bad.status_code == 400
    missing_confirmation = lab["client"].post(
        "/api/auth/me/delete", json={"password": SYNTHETIC_PASSWORD, "confirm_delete_data": False}
    )
    assert missing_confirmation.status_code == 409
    assert _snapshot(lab) == before

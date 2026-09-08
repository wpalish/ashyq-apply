"""T32 A1 regression tests: the freshness off-by-one, the recheck chain, and
supersession (J01 + the frozen planner contract C1/C2/C6/C7).

Authored RED-first on baseline 2ed4f51e1d5c1fae3f4cb36ad64982eb67184a2d
(branch ``ai/c2/t32/qa``). Expected result modes on that baseline, stated per
class so nobody mistakes a planned RED for a broken suite:

- ``TestStaleAtExactTtlBoundary``  — R1, true baseline-bug REDs
  (freshness.py:35 ``age_days(...) > max_age_days(...)`` misses the boundary).
- ``TestNoOpRecheckAdvancesTheChain`` — R2, true baseline-bug REDs: a no-op
  recheck re-derives ``next_recheck_at`` from the same immutable
  ``accessed_at``, so the recomputed date collides with (or lands behind) the
  finished job and the chain dies. Extends test_worker.py::490 without
  touching that file or its assertions.
- ``TestRecheckChainSurvivesTwoCycles`` — R3, contract RED-pending (the
  generation-keyed re-arm does not exist yet; on baseline it fails at the
  same chain-death as R2).
- ``TestSupersededExcluded`` — R4 + the apply_freshness pin, contract
  RED-pending (``ClaimStatus.SUPERSEDED`` does not exist on the baseline);
  the history-queryability half is GREEN by construction (the claims.status
  column is a free String(40)) and guards C6 during implementation.
- ``TestDemoRunIsByteIdentical`` — R6, GREEN on baseline by construction:
  the golden sha256 below was captured ON baseline 2ed4f51 from the demo
  corpus pipeline. It is the byte-identity guard for the developer's changes.
  A3 amendment: the replay is run under the capture-date clock
  (``frozen_clock``) because the baseline payload embeds the assessment day
  as an unmasked date-only string (pre-campaign runner code); without the
  freeze the golden breaks at every UTC date rollover with no real drift.
- ``TestT32MigrationRoundTrip`` — R8, contract RED-pending (the revision is
  located dynamically by ``down_revision == "b4e8a1c2f6d9"`` so the test
  survives the developer choosing the revision id); the single-head check is
  GREEN on baseline and guards the chain itself.

Everything runs offline: the demo corpus and the real local PostgreSQL from
conftest (pgserver). Nothing here changes expected behaviour to pass.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.domain.conflicts import find_conflicts
from app.domain.enums import ClaimStatus, ClaimType
from app.domain.freshness import (
    apply_freshness,
    is_stale,
    max_age_days,
    next_recheck_at,
)
from app.models import ClaimRow, ResearchRun
from app.models.base import ensure_utc
from tests.conftest import TEST_ORGANIZATION_ID, make_claim, profile_row

#: The revision T32's migration hangs off — the chain head on the baseline.
PRE_T32_HEAD = "b4e8a1c2f6d9"


# --- R1: the staleness boundary (J01) ---------------------------------------


class TestStaleAtExactTtlBoundary:
    """Contract C7: a claim is stale once it has aged max_age_days — inclusive.

    Baseline freshness.py:35 computes whole ``.days`` and compares with
    ``>``, so a 30-day-old deadline claim (aged 30d + 2min) is still read as
    30 > 30 → False: it is not stale until a full extra day has passed, and a
    recheck that fires at the expiry moment finds nothing to do.
    """

    @pytest.fixture(params=[ClaimType.ADMISSION_DEADLINE, ClaimType.TUITION])
    def case(self, request) -> tuple[ClaimType, int]:
        claim_type = request.param
        return claim_type, max_age_days(claim_type)

    def test_ttl_minus_one_second_is_not_stale(self, case):
        claim_type, ttl = case
        now = datetime.now(UTC)
        assert is_stale(claim_type, now - timedelta(days=ttl, seconds=-1), now) is False

    def test_exactly_at_ttl_is_stale(self, case):
        """RED on baseline: age_days floors 30d to 30 and 30 > 30 is False."""
        claim_type, ttl = case
        now = datetime.now(UTC)
        assert is_stale(claim_type, now - timedelta(days=ttl), now) is True

    def test_ttl_plus_two_minutes_is_stale(self, case):
        """RED on baseline: two minutes past the window still reads as
        ``age_days == ttl`` because the remainder is floored away."""
        claim_type, ttl = case
        now = datetime.now(UTC)
        assert is_stale(claim_type, now - timedelta(days=ttl, minutes=2), now) is True

    def test_naive_accessed_at_agrees_with_aware(self, case):
        """Both UTC-normalized (C7): naive and aware inputs agree. At the
        boundary this is a RED on baseline (both read False); it stays the
        pinned contract once the fix lands."""
        claim_type, ttl = case
        now = datetime.now(UTC)
        aware = now - timedelta(days=ttl)
        assert is_stale(claim_type, aware.replace(tzinfo=None), now) is is_stale(
            claim_type, aware, now
        )
        assert is_stale(claim_type, aware.replace(tzinfo=None), now) is True

    def test_naive_now_does_not_crash_and_agrees_with_aware_now(self, case):
        """C7 says *both* operands are normalized. Baseline age_days attaches
        UTC to accessed_at but hands a naive ``now`` straight to the
        subtraction, which raises TypeError."""
        claim_type, ttl = case
        now = datetime.now(UTC)
        accessed = now - timedelta(days=ttl + 1)  # past the window under either rule
        expected = is_stale(claim_type, accessed, now)
        assert is_stale(claim_type, accessed, now.replace(tzinfo=None)) is expected

    def test_apply_freshness_downgrades_at_the_boundary(self, case):
        """RED on baseline: a claim aged exactly max_age_days must show as
        POSSIBLY_STALE, not ride the off-by-one for another day."""
        claim_type, ttl = case
        now = datetime.now(UTC)
        assert (
            apply_freshness(
                ClaimStatus.VERIFIED_CURRENT, claim_type, now - timedelta(days=ttl), now
            )
            is ClaimStatus.POSSIBLY_STALE
        )

    def test_apply_freshness_leaves_a_fresh_claim_alone(self, case):
        claim_type, ttl = case
        now = datetime.now(UTC)
        assert (
            apply_freshness(
                ClaimStatus.VERIFIED_CURRENT,
                claim_type,
                now - timedelta(days=ttl, seconds=-1),
                now,
            )
            is ClaimStatus.VERIFIED_CURRENT
        )

    def test_next_recheck_at_is_the_accessed_at_plus_the_window(self, case):
        """The chain's deadline basis (C7 keeps this definition; naive inputs
        normalized)."""
        claim_type, ttl = case
        accessed = datetime.now(UTC)
        assert ensure_utc(next_recheck_at(claim_type, accessed)) == accessed + timedelta(days=ttl)
        assert ensure_utc(
            next_recheck_at(claim_type, accessed.replace(tzinfo=None))
        ) == accessed + timedelta(days=ttl)


# --- R2/R3: the recheck chain (J01 chain-death) ------------------------------


@pytest.fixture
def bound_db(settings, monkeypatch):
    """Mirrors tests/test_worker.py::bound_db (fixture reuse by import would
    tangle the files; the fixture stays untouched there)."""
    import app.db as db_module
    from app.db import migrate_to_head

    migrate_to_head(settings.database_url)
    engine = sa.create_engine(settings.database_url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, future=True)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", factory)
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    try:
        yield factory
    finally:
        engine.dispose()


def _run_research_to_decision(bound_db, settings, profile) -> tuple[str, str]:
    """A finished demo research run: returns (run_id, recheck_id)."""
    from app.jobs.worker import Worker
    from app.models import Job
    from tests.test_worker import seed_run

    run_id, job_id = seed_run(bound_db, profile)
    worker = Worker(settings)
    assert worker.claim_one() == job_id
    asyncio.run(worker.execute(job_id))
    with bound_db() as session:
        recheck_id = session.query(Job).filter(Job.run_id == run_id, Job.kind == "recheck").one().id
    return run_id, recheck_id


class TestNoOpRecheckAdvancesTheChain:
    """C7: a recheck that finds nothing to do must still re-arm the chain.

    Extends test_worker.py::490 (which asserts success + no work but never
    looks for the follow-up job) with the missing assertion — added here as a
    new test so the existing file and its assertions stay untouched.
    """

    def test_a_noop_recheck_leaves_a_new_queued_recheck_with_a_fresh_key(
        self, bound_db, settings, profile
    ):
        from app.jobs.worker import Worker
        from app.models import Job, JobStatus

        run_id, recheck_id = _run_research_to_decision(bound_db, settings, profile)

        with bound_db() as session:
            recheck = session.get(Job, recheck_id)
            finished_key = recheck.idempotency_key
            # Pull it forward, as the queue would once the recheck date arrives.
            session.execute(
                sa.update(Job).where(Job.id == recheck_id).values(available_at=datetime.now(UTC))
            )
            session.commit()

        worker = Worker(settings)
        assert worker.claim_one() == recheck_id
        before_execute = datetime.now(UTC)
        asyncio.run(worker.execute(recheck_id))

        with bound_db() as session:
            assert session.get(Job, recheck_id).status == JobStatus.SUCCEEDED.value
            followups = (
                session.query(Job)
                .filter(
                    Job.run_id == run_id,
                    Job.kind == "recheck",
                    Job.status == JobStatus.QUEUED.value,
                )
                .all()
            )
            assert followups, (
                "the no-op recheck must re-arm the chain: on baseline the "
                "recomputed key collides with the finished job and no new "
                "job is enqueued (chain death)"
            )
            for job in followups:
                assert ensure_utc(job.available_at) > before_execute, (
                    "the next recheck must wait for a strictly future moment"
                )
                assert job.idempotency_key != finished_key, (
                    "a completed recheck key must never be reused"
                )

    def test_a_recheck_fired_at_the_deadline_rearms_strictly_into_the_future(
        self, bound_db, settings, profile
    ):
        """The production moment: the recheck fires when the claims sit at the
        TTL boundary. Baseline: not stale (off-by-one) → next_recheck_at is
        recomputed as *now* and the follow-up job becomes available in the
        past, where it dedupes itself into oblivion on the same date."""
        from app.jobs.worker import Worker
        from app.models import Job, JobStatus

        run_id, recheck_id = _run_research_to_decision(bound_db, settings, profile)

        with bound_db() as session:
            # Age every claim to exactly the admission-deadline window (30d).
            session.execute(
                sa.update(ClaimRow)
                .where(ClaimRow.run_id == run_id)
                .values(accessed_at=datetime.now(UTC) - timedelta(days=30))
            )
            session.execute(
                sa.update(Job).where(Job.id == recheck_id).values(available_at=datetime.now(UTC))
            )
            session.commit()

        worker = Worker(settings)
        assert worker.claim_one() == recheck_id
        before_execute = datetime.now(UTC)
        asyncio.run(worker.execute(recheck_id))

        with bound_db() as session:
            run = session.get(ResearchRun, run_id)
            assert session.get(Job, recheck_id).status == JobStatus.SUCCEEDED.value
            followups = (
                session.query(Job)
                .filter(
                    Job.run_id == run_id,
                    Job.kind == "recheck",
                    Job.status == JobStatus.QUEUED.value,
                )
                .all()
            )
            assert followups, "the chain must not die at the expiry moment"
            for job in followups:
                assert ensure_utc(job.available_at) > before_execute, (
                    f"re-armed into the past (run.next_recheck_at={run.next_recheck_at!r}): "
                    "a follow-up the queue can never wait for is the chain death"
                )


class TestRecheckChainSurvivesTwoCycles:
    """R3: the chain must survive repeated no-op rechecks, each re-arm under a
    fresh generation key (C2/C7). Contract RED-pending: on baseline the first
    cycle already dies the R2 death; post-fix this pins two full cycles."""

    def test_two_noop_cycles_each_produce_a_new_generation(self, bound_db, settings, profile):
        from app.jobs.worker import Worker
        from app.models import Job, JobStatus

        run_id, recheck_id = _run_research_to_decision(bound_db, settings, profile)
        worker = Worker(settings)
        seen_keys: list[str] = []

        current = recheck_id
        for cycle in (1, 2):
            with bound_db() as session:
                job = session.get(Job, current)
                seen_keys.append(job.idempotency_key)
                session.execute(
                    sa.update(Job).where(Job.id == current).values(available_at=datetime.now(UTC))
                )
                session.commit()

            assert worker.claim_one() == current
            before_execute = datetime.now(UTC)
            asyncio.run(worker.execute(current))

            with bound_db() as session:
                assert session.get(Job, current).status == JobStatus.SUCCEEDED.value
                queued = (
                    session.query(Job)
                    .filter(
                        Job.run_id == run_id,
                        Job.kind == "recheck",
                        Job.status == JobStatus.QUEUED.value,
                    )
                    .all()
                )
                assert len(queued) == 1, f"cycle {cycle}: exactly one follow-up recheck"
                assert ensure_utc(queued[0].available_at) > before_execute
                assert queued[0].idempotency_key not in seen_keys, (
                    f"cycle {cycle}: a generation key must never repeat"
                )
                current = queued[0].id


# --- R4: SUPERSEDED stays out of conflicts, evidence and freshness ----------


class TestSupersededExcluded:
    """C2: SUPERSEDED is a real status, is invisible to find_conflicts, is
    never touched by apply_freshness, and its history stays queryable (C6).
    The enum member does not exist on the baseline — those halves are contract
    RED-pending (AttributeError). The persistence half works on the baseline's
    free-string status column and is GREEN by construction."""

    def test_the_enum_has_a_superseded_member(self):
        assert ClaimStatus.SUPERSEDED == "SUPERSEDED"

    def test_apply_freshness_never_touches_superseded(self):
        """The pin the contract asks for by name: however old the evidence,
        freshness moves VERIFIED_CURRENT only."""
        superseded = ClaimStatus.SUPERSEDED
        now = datetime.now(UTC)
        ancient = now - timedelta(days=900)
        assert apply_freshness(superseded, ClaimType.ADMISSION_DEADLINE, ancient, now) is superseded

    def test_a_superseded_value_does_not_conflict_with_its_successor(self):
        """The whole point of было/стало: yesterday's value, already marked
        superseded, must not resurrect as a CONFLICTING claim against today's.
        Contract RED-pending (no enum member; conflicts.py has no entry
        filter)."""
        now = datetime.now(UTC)
        old = make_claim(
            "tuition",
            45000,
            url="https://example.edu/costs",
            status="SUPERSEDED",
            accessed_at=now - timedelta(days=400),
        )
        new = make_claim(
            "tuition",
            50000,
            url="https://example.edu/costs",
            status="VERIFIED_CURRENT",
            accessed_at=now,
        )
        conflicts, updated = find_conflicts([old, new])
        assert conflicts == [], "a superseded value must not be treated as live evidence"
        by_status = {c.status: c for c in updated}
        assert by_status.get(ClaimStatus.VERIFIED_CURRENT) is new
        assert ClaimStatus.CONFLICTING not in by_status
        assert old.status is ClaimStatus.SUPERSEDED

    def test_superseded_history_stays_queryable_with_its_value(self, tmp_path):
        """C6 was/stale shape: the superseded row survives with payload,
        accessed_at and result_id, retrievable alongside its successor,
        ordered by accessed_at. GREEN on baseline by construction (the column
        is a plain String(40)) — this is the guard the developer must not
        break while building reextract."""
        from app.db import migrate_to_head

        url = f"sqlite:///{tmp_path / 'was_stale.db'}"
        migrate_to_head(url)
        engine = sa.create_engine(url)
        factory = sessionmaker(bind=engine, future=True)
        session = factory()
        try:
            org = profile_row(session, {"display_name": "t"})
            run = ResearchRun(profile_id=org.id, stage="awaiting_user_decision", demo_mode=True)
            session.add(run)
            session.flush()
            result_id = uuid.uuid4().hex
            now = datetime.now(UTC)
            old_payload = {
                "claim_type": "tuition",
                "status": "SUPERSEDED",
                "source_url": "https://example.edu/costs",
                "normalized_value": 45000,
            }
            new_payload = {
                "claim_type": "tuition",
                "status": "VERIFIED_CURRENT",
                "source_url": "https://example.edu/costs",
                "normalized_value": 50000,
            }
            session.add(
                ClaimRow(
                    run_id=run.id,
                    result_id=result_id,
                    claim_type="tuition",
                    status="SUPERSEDED",
                    source_url="https://example.edu/costs",
                    source_specificity="program_intake",
                    accessed_at=now - timedelta(days=400),
                    payload=old_payload,
                )
            )
            session.add(
                ClaimRow(
                    run_id=run.id,
                    result_id=result_id,
                    claim_type="tuition",
                    status="VERIFIED_CURRENT",
                    source_url="https://example.edu/costs",
                    source_specificity="program_intake",
                    accessed_at=now,
                    payload=new_payload,
                )
            )
            session.commit()

            history = (
                session.query(ClaimRow)
                .filter(ClaimRow.result_id == result_id, ClaimRow.status == "SUPERSEDED")
                .order_by(ClaimRow.accessed_at)
                .all()
            )
            assert len(history) == 1, "the superseded row must survive the reextract"
            assert history[0].payload["normalized_value"] == 45000, (
                "was/stale: the old value must stay readable"
            )
            assert ensure_utc(history[0].accessed_at) < now - timedelta(days=399)
            live = session.query(ClaimRow).filter(ClaimRow.status == "VERIFIED_CURRENT").all()
            assert len(live) == 1
        finally:
            session.close()
            engine.dispose()


# --- R6: demo byte-identity --------------------------------------------------

#: sha256 of the canonical demo-pipeline dump, captured ON baseline
#: 2ed4f51e1d5c1fae3f4cb36ad64982eb67184a2d (T32 A1 QA, 2026-09-07) with the
#: ``_canonical_demo_dump`` machinery below. GREEN on baseline by
#: construction; the developer's T32 changes must keep the demo pipeline
#: byte-identical under the same masking.
GOLDEN_DEMO_SHA256 = "aae8c595ab8f78c8a03a87eddde03a811b8986e4725817d05c65059327e4d702"

#: The golden was captured with the real clock on 2026-09-07, and the baseline
#: payload embeds that date: ``requirement_checks[*].applicant_value`` and
#: ``scholarships[*].eligibility_checks[*].applicant_value`` carry the
#: assessment day as a bare ``YYYY-MM-DD`` string (pre-campaign runner code,
#: runner.py ``_stage_assess``; commit 9cfb20b, untouched by T32). The
#: ``_mask_volatile`` patterns below do not match a date-only string, so
#: without a frozen clock this golden fails at every UTC date rollover —
#: proven on pristine baseline 2ed4f51 (A3 QA). The fix is to replay the
#: pipeline under the capture-date clock, NOT to widen the mask: of the 112
#: date-only strings in a demo dump, 96 are semantic corpus values
#: (admission_deadline, scholarships[*].deadline, normalized_value,
#: published_value) that byte-identity must keep guarding. Never re-capture
#: the hash against a real clock — re-capture means re-deriving it from a new
#: intended baseline, under this same frozen date.
GOLDEN_CAPTURE_UTC = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)


class _FrozenDatetime(datetime):
    """A ``datetime`` whose wall clock is pinned to the golden capture moment.

    Subclass (not a stub) so constructors, parsing and arithmetic behave
    exactly like the real thing; only the *reading* of the clock is pinned.
    """

    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return GOLDEN_CAPTURE_UTC.astimezone(tz)
        return GOLDEN_CAPTURE_UTC.replace(tzinfo=None)

    @classmethod
    def today(cls):
        return cls.now()

    @classmethod
    def utcnow(cls):
        return GOLDEN_CAPTURE_UTC.replace(tzinfo=None)


class _FrozenDate(date):
    @classmethod
    def today(cls):
        return GOLDEN_CAPTURE_UTC.date()


@pytest.fixture
def frozen_clock(monkeypatch):
    """Pin every wall clock the demo pipeline can read to the capture date.

    These are all the ``datetime.now``/``date.today`` call sites under
    app/pipeline and app/domain (runner._stage_assess feeds ``today`` into the
    eligibility verdicts that land in the payloads; the rest are defaults,
    heartbeat bookkeeping and masked timestamps). Only test modules are
    patched — monkeypatch restores every name after each test.
    """
    import app.domain.claim_verifier as claim_verifier
    import app.domain.currency as currency
    import app.domain.eligibility as eligibility
    import app.domain.freshness as freshness
    import app.pipeline.runner as runner
    import app.pipeline.state as state

    for module in (runner, state, eligibility, freshness):
        monkeypatch.setattr(module, "datetime", _FrozenDatetime)
    for module in (claim_verifier, currency):
        monkeypatch.setattr(module, "date", _FrozenDate)


_UUID_HEX = re.compile(r"[0-9a-f]{32}(-[a-z]+[0-9]+)?$")
_ISO_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _mask_volatile(node):
    """Mask run-to-run randomness so only real drift can move the golden.

    - uuid-shaped ids (32 hex, optionally suffixed ``-c0``/``-f12``): claim,
      result, run and scholarship ids reference each other per run.
    - ISO timestamps (accessed_at, last_verified): 'now' at run time.

    Documented blind spot: a change confined to values that only ever match
    these two shapes (e.g. one fixture timestamp replaced by another) is not
    caught. Everything a T32 change could plausibly alter — statuses, values,
    conflicts, ranking, counts — survives the mask.
    """
    if isinstance(node, dict):
        return {k: _mask_volatile(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_mask_volatile(v) for v in node]
    if isinstance(node, str):
        if _UUID_HEX.search(node):
            return "<uuid>"
        if _ISO_TS.match(node):
            return "<ts>"
    return node


def _canonical_demo_dump(session, run_id: str) -> str:
    from app.models import ProgramResultRow

    rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run_id).all()
    payloads = [_mask_volatile(r.payload) for r in rows]
    payloads.sort(key=lambda p: (p["university"], p["program"]))
    return json.dumps(payloads, sort_keys=True, indent=1)


class TestDemoRunIsByteIdentical:
    """R6: the demo pipeline's stored result payloads are part of the product.
    T32 touches runner.py (recheck advancement, _replace_evidence) and the
    freshness rules; none of that may move a byte of the demo output.

    The replay runs under the golden capture clock (``frozen_clock``): the
    baseline payload embeds the assessment day as an unmasked date-only
    string, so a real clock would break byte-identity at the first UTC
    rollover after capture without any real drift. The asserted fact is
    unchanged: payload byte-identical to the baseline golden."""

    @pytest.fixture
    def demo_session(self, frozen_clock, settings, profile):
        from app.models import ApplicantProfileRow, Base
        from app.pipeline.runner import ResearchRunner
        from app.pipeline.state import RunState

        engine = sa.create_engine(settings.database_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        row = ApplicantProfileRow(
            organization_id=TEST_ORGANIZATION_ID,
            display_name="t",
            payload=profile.model_dump(mode="json"),
        )
        session.add(row)
        session.flush()
        run = ResearchRun(
            profile_id=row.id,
            stage="queued",
            demo_mode=True,
            stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.flush()
        asyncio.run(ResearchRunner(session, run, profile, settings).run_to_decision())
        try:
            yield session, run.id
        finally:
            session.close()
            engine.dispose()

    def test_the_demo_produces_results(self, demo_session):
        session, run_id = demo_session
        assert _canonical_demo_dump(session, run_id).count('"university"') >= 1

    def test_the_demo_pipeline_payload_is_byte_identical_to_baseline(self, demo_session):
        session, run_id = demo_session
        dump = _canonical_demo_dump(session, run_id)
        assert hashlib.sha256(dump.encode("utf-8")).hexdigest() == GOLDEN_DEMO_SHA256, (
            "the demo pipeline output drifted from the baseline golden. If (and only if) "
            "the drift is intended and confined to documented masking shapes, re-capture "
            "GOLDEN_DEMO_SHA256 from the new baseline; otherwise fix the regression."
        )


# --- R8: the T32 migration ---------------------------------------------------


def _t32_migration_paths() -> list[Path]:
    """Locate T32's revision dynamically: the one migration whose
    down_revision is b4e8a1c2f6d9. The revision id is the developer's choice;
    the parent is frozen by the contract."""
    versions = Path(__file__).resolve().parent.parent / "migrations" / "versions"
    pattern = re.compile(r"down_revision\s*=\s*[\"']" + PRE_T32_HEAD + r"[\"']")
    return [
        path
        for path in sorted(versions.glob("*.py"))
        if path.name != "__init__.py" and pattern.search(path.read_text())
    ]


def _column(table_info: list[dict], name: str) -> dict:
    matches = [c for c in table_info if c["name"] == name]
    assert matches, f"column {name!r} missing"
    return matches[0]


class TestT32MigrationRoundTrip:
    """C1: one revision on b4e8a1c2f6d9; claims.source_page_id (nullable,
    FK fk_claims_source_page → source_pages.id ON DELETE SET NULL, indexed);
    research_runs.recheck_generation (NOT NULL, server default "0"); exact
    inverse downgrade; round-trip on SQLite and PostgreSQL."""

    def test_there_is_exactly_one_head(self):
        """GREEN on baseline by construction: the single-head invariant holds
        before T32 and must still hold after."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        from app.db import ALEMBIC_INI, MIGRATIONS_DIR, head_revision

        config = Config(str(ALEMBIC_INI))
        config.set_main_option("script_location", str(MIGRATIONS_DIR))
        heads = ScriptDirectory.from_config(config).get_heads()
        assert len(heads) == 1, f"migration chain forked: {heads}"
        assert heads == [head_revision()]

    def test_exactly_one_migration_hangs_off_the_baseline_head(self):
        paths = _t32_migration_paths()
        assert paths, (
            f"no migration with down_revision == {PRE_T32_HEAD!r}: the T32 "
            "revision does not exist yet (contract RED-pending)"
        )
        assert len(paths) == 1, f"expected one T32 migration, found {paths}"

    def _assert_t32_columns(self, engine):
        insp = sa.inspect(engine)
        claims = _column(insp.get_columns("claims"), "source_page_id")
        assert claims["nullable"] is True, "source_page_id must be nullable (SET NULL target)"
        fks = [
            fk
            for fk in insp.get_foreign_keys("claims")
            if fk.get("referred_table") == "source_pages"
        ]
        assert fks, "claims.source_page_id must reference source_pages"
        fk = fks[0]
        # SQLAlchemy 2.0.36 reflects the FK delete action under
        # fk["options"]["ondelete"] (both dialects); older shapes exposed it
        # at the top level. Accept either — the fact is what we assert.
        reflected_ondelete = fk.get("ondelete") or (fk.get("options") or {}).get("ondelete")
        assert reflected_ondelete == "SET NULL", (
            "the FK must be ON DELETE SET NULL or the retention purge fails "
            "on pages still referenced by superseded claims"
        )
        assert fk.get("name") == "fk_claims_source_page"
        index_names = {i["name"] for i in insp.get_indexes("claims")}
        assert "ix_claims_source_page" in index_names

        gen = _column(insp.get_columns("research_runs"), "recheck_generation")
        assert gen["nullable"] is False, "recheck_generation must be NOT NULL"
        # Reflection representation differs per dialect: PostgreSQL populates
        # server_default, SQLite exposes the DDL default as gen["default"]
        # ("'0'"). Accept either — the fact (default 0) is what we assert.
        default = gen.get("server_default")
        if default is None:
            default = gen.get("default")
        assert default is not None and "0" in str(getattr(default, "arg", default)), (
            "recheck_generation must carry a server default of 0"
        )

    def _assert_no_t32_columns(self, engine):
        insp = sa.inspect(engine)
        assert "source_page_id" not in {c["name"] for c in insp.get_columns("claims")}
        assert "recheck_generation" not in {c["name"] for c in insp.get_columns("research_runs")}

    def test_upgrade_then_downgrade_on_sqlite(self, tmp_path):
        from alembic import command

        from app.db import _alembic_config

        paths = _t32_migration_paths()
        assert paths, "the T32 revision does not exist yet (contract RED-pending)"

        url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
        command.upgrade(_alembic_config(url), PRE_T32_HEAD)
        engine = sa.create_engine(url)
        try:
            self._assert_no_t32_columns(engine)
        finally:
            engine.dispose()

        command.upgrade(_alembic_config(url), "head")
        engine = sa.create_engine(url)
        try:
            self._assert_t32_columns(engine)
        finally:
            engine.dispose()

        command.downgrade(_alembic_config(url), PRE_T32_HEAD)
        engine = sa.create_engine(url)
        try:
            self._assert_no_t32_columns(engine)
        finally:
            engine.dispose()

        command.upgrade(_alembic_config(url), "head")
        engine = sa.create_engine(url)
        try:
            self._assert_t32_columns(engine)
        finally:
            engine.dispose()

    def test_upgrade_then_downgrade_on_postgresql(self, pg_engine):
        from alembic import command

        from app.db import _alembic_config

        paths = _t32_migration_paths()
        assert paths, "the T32 revision does not exist yet (contract RED-pending)"

        url = str(pg_engine.url)
        command.downgrade(_alembic_config(url), PRE_T32_HEAD)
        self._assert_no_t32_columns(pg_engine)

        command.upgrade(_alembic_config(url), "head")
        self._assert_t32_columns(pg_engine)

    def test_deleting_a_source_page_nulls_the_claims_reference(self, pg_engine):
        """The behavioural point of SET NULL (C1 + C4): the retention purge may
        delete a page whose only referencers are SUPERSEDED; the history rows
        survive with source_page_id cleared, queryable via payload.source_url."""
        from alembic import command

        from app.db import _alembic_config
        from app.models import SourcePage

        paths = _t32_migration_paths()
        assert paths, "the T32 revision does not exist yet (contract RED-pending)"
        command.upgrade(_alembic_config(str(pg_engine.url)), "head")

        factory = sessionmaker(bind=pg_engine, future=True)
        session = factory()
        try:
            org = profile_row(session, {"display_name": "t"})
            run = ResearchRun(profile_id=org.id, stage="awaiting_user_decision", demo_mode=True)
            session.add(run)
            session.flush()
            page = SourcePage(
                url="https://example.edu/costs",
                registrable_domain="example.edu",
                active_claims=1,
            )
            session.add(page)
            session.flush()
            claim = ClaimRow(
                run_id=run.id,
                result_id=uuid.uuid4().hex,
                claim_type="tuition",
                status="SUPERSEDED",
                source_url=page.url,
                source_specificity="program_intake",
                payload={"status": "SUPERSEDED", "source_url": page.url},
            )
            claim.source_page_id = page.id
            session.add(claim)
            session.commit()

            session.delete(page)
            session.commit()

            surviving = session.query(ClaimRow).filter(ClaimRow.status == "SUPERSEDED").all()
            assert len(surviving) == 1, "purging the page must not destroy the history row"
            assert surviving[0].source_page_id is None
            assert surviving[0].payload["source_url"] == "https://example.edu/costs"
        finally:
            session.close()

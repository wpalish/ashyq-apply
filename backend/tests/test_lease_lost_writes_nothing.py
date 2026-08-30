"""Losing the lease must write nothing. It was writing the run as FAILED.

The commit that introduced `LeaseLost` said it "writes nothing at all — not a
success, not a failure, not a cancellation — because the job's state already
belongs to whoever holds it". That was true of the *job* row and false of the
*run* row, which is the one the applicant sees.

`LeaseLost` is a `RuntimeError`, so it is not a `RunCancelled`, so it fell into
`run_to_decision`'s `except Exception:` — which sets `stage = FAILED`, appends
to `run.errors`, writes a `run_failed` audit event and commits all three. For a
run that another worker had already reclaimed and was actively working on.

That is precisely the split-brain write the lease exists to prevent, arriving
through the one path nobody looked at, and it is worse than the original bug:
worker B is mid-run when A marks the shared run failed, so the applicant is
told their research failed while it is still going.

The second defect is quieter. Every stage checks ownership inside its loop —
verification, funding, documents — except assessment, which checks once before
its loop and then writes every row without looking again. A lease lost during
assessment is not observed at all, so all of it lands.
"""
from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.domain.enums import PipelineStage
from app.models import ApplicantProfileRow, AuditEvent, Base, ResearchRun
from app.pipeline.runner import LeaseLost, ResearchRunner
from app.pipeline.state import RunState


@pytest.fixture
def session(settings):
    engine = sa.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    s = factory()
    yield s
    s.close()


@pytest.fixture
def runner(session, settings, profile):
    row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
    session.add(row)
    session.flush()
    run = ResearchRun(
        profile_id=row.id,
        stage=PipelineStage.PROGRAM_VERIFICATION.value,
        demo_mode=True,
        candidate_limit=2,
        verify_limit=2,
        stage_state=RunState.load(None).dump(),
    )
    session.add(run)
    session.commit()
    return ResearchRunner(session, run, profile, settings, job_id="job-1")


class TestALostLeaseLeavesTheRunAlone:
    @pytest.mark.asyncio
    async def test_the_run_is_not_marked_failed(self, runner, session, monkeypatch):
        async def lose_the_lease(*_args, **_kwargs):
            raise LeaseLost("the lease on job job-1 was lost")

        monkeypatch.setattr(ResearchRunner, "_stage_validate", lose_the_lease)
        before = runner.run.stage

        with pytest.raises(LeaseLost):
            await runner.run_to_decision()

        session.expire_all()
        run = session.get(ResearchRun, runner.run.id)
        assert run.stage == before, (
            "the worker that lost its lease overwrote the stage of a run "
            "another worker is now running"
        )
        assert not (run.errors or []), (
            "a lost lease was recorded as an error against the applicant's run"
        )
        assert run.finished_at is None

    @pytest.mark.asyncio
    async def test_no_audit_event_is_written(self, runner, session, monkeypatch):
        """`run_failed` says a person's research failed. It did not: it moved."""

        async def lose_the_lease(*_args, **_kwargs):
            raise LeaseLost("the lease on job job-1 was lost")

        monkeypatch.setattr(ResearchRunner, "_stage_validate", lose_the_lease)
        with pytest.raises(LeaseLost):
            await runner.run_to_decision()

        session.expire_all()
        actions = [
            e.action
            for e in session.query(AuditEvent)
            .filter(AuditEvent.entity_id == runner.run.id)
            .all()
        ]
        assert "run_failed" not in actions, actions
        assert "run_cancelled" not in actions, actions

    @pytest.mark.asyncio
    async def test_a_real_failure_is_still_recorded(self, runner, session, monkeypatch):
        """The narrow handler must not swallow ordinary failures with it."""

        async def blow_up(*_args, **_kwargs):
            raise ValueError("the adapter broke")

        monkeypatch.setattr(ResearchRunner, "_stage_validate", blow_up)
        with pytest.raises(ValueError):
            await runner.run_to_decision()

        session.expire_all()
        run = session.get(ResearchRun, runner.run.id)
        assert run.stage == PipelineStage.FAILED.value
        assert any("the adapter broke" in e for e in (run.errors or []))


class TestAssessmentObservesTheLeaseToo:
    def test_the_assessment_loop_has_an_ownership_checkpoint(self):
        """Verification, funding and document collection all check ownership
        inside their loops. Assessment checked once, before its loop, and then
        wrote every row without looking again.

        Read as source rather than executed, because the defect is the absence
        of a call on a path that a demo-mode run walks in milliseconds — timing
        cannot distinguish "checked" from "finished before the check mattered".
        """
        import inspect

        source = inspect.getsource(ResearchRunner._stage_assess)
        body = source.split("for i, row in enumerate(rows):", 1)
        assert len(body) == 2, "the assessment loop has moved; update this test"
        assert "_check_cancelled()" in body[1], (
            "the assessment loop never re-checks ownership, so a lease lost "
            "during assessment is not observed and every row is written anyway"
        )


class TestARefusedCompletionIsNotSuccess:
    """`complete()` returns a bool so a stale holder learns its write did not
    land. Its only caller threw the value away.

    The store's docstring is explicit — "a worker that has lost its lease needs
    to know that its completion did not land, and silently doing nothing is how
    it would carry on believing otherwise" — and `_dispatch` then wrote a
    `job_completed` audit event regardless and returned normally, so the worker
    counted the job in `jobs_done` and moved on. Two workers, one job, both
    reporting success.
    """

    @pytest.mark.asyncio
    async def test_a_refused_completion_raises_rather_than_auditing(
        self, session, settings, profile, monkeypatch
    ):
        from app.jobs.store import JobStore
        from app.jobs.worker import Worker
        from app.models import Job

        row = ApplicantProfileRow(
            display_name="t", payload=profile.model_dump(mode="json")
        )
        session.add(row)
        session.flush()
        run = ResearchRun(
            profile_id=row.id, stage=PipelineStage.QUEUED.value, demo_mode=True,
            candidate_limit=1, verify_limit=1, stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.flush()
        job_id = JobStore(session).enqueue("research", run_id=run.id).job_id
        session.commit()
        job = session.get(Job, job_id)

        async def finished(*_a, **_k):
            return None

        monkeypatch.setattr(ResearchRunner, "run_to_decision", finished)
        # The lease went while the pipeline ran; the store refuses the write.
        monkeypatch.setattr(JobStore, "complete", lambda *a, **k: False)

        store = JobStore(session)
        with pytest.raises(LeaseLost):
            await Worker(settings)._dispatch(
                session, store, job, lease_token="stale", lease_lost=None
            )

        session.expire_all()
        actions = [
            e.action
            for e in session.query(AuditEvent)
            .filter(AuditEvent.entity_id == job_id)
            .all()
        ]
        assert "job_completed" not in actions, (
            "a worker whose completion was refused still recorded the job as done"
        )

"""After a lease is reclaimed, the old worker must not be able to write.

The crash tests SIGKILL worker A, which is the *easy* case: a dead process
writes nothing. The dangerous one is a worker that stalls — a long GC pause, a
suspended container, a wedged event loop — long enough for its lease to expire
and worker B to reclaim the job, and then wakes up and carries on.

Nothing stopped it. `heartbeat`, `complete`, `fail` and `mark_cancelled` all
matched on job id and RUNNING status alone, with no notion of *whose* run this
is, so A could extend B's lease, mark B's job succeeded, or fail work B had
already finished. `heartbeat`'s own docstring said "False if the job is no
longer ours to extend", which was not true of the query underneath it.

Two workers writing one job's results is the shape of corruption a durable
queue exists to prevent.
"""
from __future__ import annotations

import pytest

from app.jobs.store import JobStore
from app.models import Job, JobStatus


@pytest.fixture
def store(pg_session):
    return JobStore(pg_session, lease_seconds=60)


def _expire(session, job_id: str) -> None:
    """Age the lease out, as a stalled worker would."""
    from datetime import UTC, datetime, timedelta

    job = session.get(Job, job_id)
    job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.flush()


def _reclaim(store, session, job_id: str, worker_id: str):
    """Expire A's lease, reap it, and let `worker_id` take the job.

    The reaper puts a reaped job behind a retry backoff, which is right in
    production and would just make this test wait, so availability is moved
    forward deliberately rather than by sleeping.
    """
    from datetime import UTC, datetime

    _expire(session, job_id)
    store.reap_expired()
    job = session.get(Job, job_id)
    job.available_at = datetime.now(UTC)
    session.flush()
    return store.claim(worker_id=worker_id)


class TestOnlyTheCurrentHolderMayWrite:
    def test_a_stalled_worker_cannot_extend_a_lease_it_lost(self, store, pg_session):
        job_id = store.enqueue("research", payload={}).job_id
        a = store.claim(worker_id="A")
        assert a is not None
        a_token = a.lease_token

        b = _reclaim(store, pg_session, job_id, "B")
        assert b is not None and b.lease_token != a_token

        assert store.heartbeat(job_id, lease_token=a_token) is False, (
            "the stalled worker extended a lease that now belongs to another"
        )
        assert store.heartbeat(job_id, lease_token=b.lease_token) is True

    def test_a_stalled_worker_cannot_complete_another_workers_job(
        self, store, pg_session
    ):
        job_id = store.enqueue("research", payload={}).job_id
        a = store.claim(worker_id="A")
        a_token = a.lease_token
        b = _reclaim(store, pg_session, job_id, "B")

        assert store.complete(job_id, lease_token=a_token) is False
        pg_session.expire_all()
        assert pg_session.get(Job, job_id).status == JobStatus.RUNNING.value, (
            "a worker that lost its lease marked the job succeeded"
        )
        assert store.complete(job_id, lease_token=b.lease_token) is True

    def test_a_stalled_worker_cannot_fail_work_another_worker_owns(
        self, store, pg_session
    ):
        job_id = store.enqueue("research", payload={}).job_id
        a = store.claim(worker_id="A")
        a_token = a.lease_token
        b = _reclaim(store, pg_session, job_id, "B")

        assert store.fail(job_id, "stale worker's error", lease_token=a_token) is None
        pg_session.expire_all()
        after = pg_session.get(Job, job_id)
        assert after.status == JobStatus.RUNNING.value
        assert "stale worker" not in (after.last_error or "")
        assert store.fail(job_id, "real error", lease_token=b.lease_token) is not None

    def test_a_stalled_worker_cannot_cancel_another_workers_job(
        self, store, pg_session
    ):
        job_id = store.enqueue("research", payload={}).job_id
        a = store.claim(worker_id="A")
        a_token = a.lease_token
        assert _reclaim(store, pg_session, job_id, "B") is not None

        assert store.mark_cancelled(job_id, "stale", lease_token=a_token) is False
        pg_session.expire_all()
        assert pg_session.get(Job, job_id).status == JobStatus.RUNNING.value


class TestTheTokenItself:
    def test_every_claim_gets_a_different_token(self, store, pg_session):
        job_id = store.enqueue("research", payload={}).job_id
        first = store.claim(worker_id="A").lease_token
        second = _reclaim(store, pg_session, job_id, "B").lease_token
        assert first and second and first != second

    def test_the_token_is_not_derived_from_a_pid_or_a_clock(self, store, pg_session):
        """A PID is reused and a clock goes backwards. Neither can fence."""
        store.enqueue("research", payload={})
        token = store.claim(worker_id="A").lease_token
        import os

        assert str(os.getpid()) not in token
        assert len(token) >= 32

    def test_a_missing_token_is_refused_rather_than_matching_anything(
        self, store, pg_session
    ):
        """`None` must not act as a wildcard: that would restore the bug in a
        shape nobody notices."""
        job_id = store.enqueue("research", payload={}).job_id
        store.claim(worker_id="A")
        assert store.heartbeat(job_id, lease_token="") is False
        assert store.complete(job_id, lease_token="") is False

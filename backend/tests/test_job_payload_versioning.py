"""A worker must not consume work it cannot do.

An orphaned worker claimed three `documents` jobs whose payloads carried
fields added after it started, failed each three times on
`ValidationError: Extra inputs are not permitted`, and buried them in the
dead-letter state. The applicant's research stopped with no recoverable state
and no explanation anywhere they could see.

These tests cover the queue's half of that: a payload a worker cannot read is
parked, not spent.
"""
from __future__ import annotations

import pytest

from app.jobs.store import JobStore
from app.jobs.versioning import (
    PAYLOAD_SCHEMA_VERSION,
    SUPPORTED_PAYLOAD_SCHEMA_VERSIONS,
    incompatibility,
    supports,
)
from app.models.jobs import Job, JobStatus


class TestTheVersionContract:
    def test_this_build_supports_the_version_it_writes(self):
        """Otherwise a build parks its own jobs, which is worse than useless."""
        assert supports(PAYLOAD_SCHEMA_VERSION)

    def test_a_future_version_is_not_supported(self):
        assert not supports(max(SUPPORTED_PAYLOAD_SCHEMA_VERSIONS) + 1)

    def test_the_reason_carries_no_payload(self):
        """This build could not read the payload, so it cannot judge which
        parts of it are safe to repeat into a log."""
        reason = incompatibility(99)
        text = repr(reason)
        assert "payload" not in {k for k in reason if k.endswith("payload")}
        assert reason["job_payload_schema_version"] == 99
        assert "resolution" in reason
        # No free text that could have come from applicant data.
        assert all(
            isinstance(v, (int, str, list)) for v in reason.values()
        ), reason

    def test_the_reason_names_a_way_out(self):
        assert "worker" in str(incompatibility(99)["resolution"])


@pytest.fixture
def store(pg_session):
    return JobStore(pg_session, lease_seconds=60)


class TestParkingRatherThanFailing:
    def test_a_new_job_is_stamped_with_this_builds_version(self, store, pg_session):
        result = store.enqueue("research", payload={"profile_id": "p1"})
        job = pg_session.get(Job, result.job_id)
        assert job.payload_schema_version == PAYLOAD_SCHEMA_VERSION
        assert job.producer_version

    def test_an_unreadable_payload_is_parked_and_costs_no_attempt(self, store, pg_session):
        result = store.enqueue("research", payload={"profile_id": "p1"})
        job = pg_session.get(Job, result.job_id)
        job.payload_schema_version = 999
        pg_session.flush()

        status = store.park_incompatible(job.id, 999)

        parked = pg_session.get(Job, job.id)
        assert status == JobStatus.BLOCKED_INCOMPATIBLE.value
        assert parked.status == JobStatus.BLOCKED_INCOMPATIBLE.value
        assert parked.attempts == 0, "refusing work is not an attempt at it"
        assert "unsupported_payload_schema_version" in parked.last_error

    def test_a_parked_job_is_not_handed_to_another_worker(self, store, pg_session):
        result = store.enqueue("research", payload={"profile_id": "p1"})
        job = pg_session.get(Job, result.job_id)
        job.payload_schema_version = 999
        pg_session.flush()
        store.park_incompatible(job.id, 999)

        assert store.claim(worker_id="w2") is None, (
            "a parked job must not be claimed by a worker that also cannot read it"
        )

    def test_parking_is_not_a_terminal_state(self):
        """`dead` means a human has to decide. Parked means a deployment has
        to finish. Conflating them is how the three real jobs were lost."""
        from app.models.jobs import TERMINAL_STATUSES

        assert JobStatus.BLOCKED_INCOMPATIBLE not in TERMINAL_STATUSES

    def test_a_capable_worker_releases_parked_jobs(self, store, pg_session):
        result = store.enqueue("research", payload={"profile_id": "p1"})
        job = pg_session.get(Job, result.job_id)
        job.payload_schema_version = 999
        pg_session.flush()
        store.park_incompatible(job.id, 999)

        # Nothing changes while this build still cannot read it.
        assert store.release_incompatible(SUPPORTED_PAYLOAD_SCHEMA_VERSIONS) == 0

        # A build that can read it puts it back in the queue.
        assert store.release_incompatible(frozenset({999})) == 1
        released = pg_session.get(Job, job.id)
        assert released.status == JobStatus.QUEUED.value
        assert released.attempts == 0
        assert store.claim(worker_id="w3") is not None

    def test_releasing_does_not_disturb_other_jobs(self, store, pg_session):
        keep = pg_session.get(Job, store.enqueue("research", payload={}).job_id)
        keep.status = JobStatus.DEAD.value
        blocked = pg_session.get(Job, store.enqueue("documents", payload={}).job_id)
        blocked.payload_schema_version = 999
        pg_session.flush()
        store.park_incompatible(blocked.id, 999)

        store.release_incompatible(frozenset({999}))

        assert pg_session.get(Job, keep.id).status == JobStatus.DEAD.value, (
            "a dead job needs a human decision and must not be silently revived"
        )


class TestAnOlderPayloadStillRuns:
    def test_a_payload_missing_a_later_optional_field_is_accepted(self, store, pg_session):
        """The direction that has to keep working: a queue drained after a
        deploy is full of payloads written before it."""
        job_id = store.enqueue("research", payload={"profile_id": "p1"}).job_id
        job = pg_session.get(Job, job_id)
        job.payload_schema_version = min(SUPPORTED_PAYLOAD_SCHEMA_VERSIONS)
        pg_session.flush()

        assert supports(job.payload_schema_version)
        assert store.claim(worker_id="w1") is not None


class TestTheWorkerRefusesRatherThanBuries:
    """The whole path, as it actually failed.

    An orphaned worker took `documents` jobs it could not decode and, three
    attempts later, they were `dead`. The job must instead come out parked,
    unspent, and runnable once a capable worker starts.
    """

    @pytest.mark.asyncio
    async def test_a_payload_from_the_future_is_parked_not_attempted(
        self, store, pg_session, monkeypatch
    ):
        from app.jobs import worker as worker_module

        job_id = store.enqueue("documents", payload={"result_id": "r1"}).job_id
        job = pg_session.get(Job, job_id)
        job.payload_schema_version = 999
        pg_session.commit()

        seen: list[str] = []

        def _never(*args, **kwargs):
            seen.append("dispatched")
            raise AssertionError("a payload this build cannot read must not run")

        monkeypatch.setattr(worker_module.Worker, "_dispatch", _never)
        monkeypatch.setattr(
            worker_module, "session_scope", lambda: _SessionScope(pg_session)
        )

        await worker_module.Worker().execute(job_id)

        pg_session.expire_all()
        parked = pg_session.get(Job, job_id)
        assert seen == [], "the handler ran against a payload it cannot decode"
        assert parked.status == JobStatus.BLOCKED_INCOMPATIBLE.value
        assert parked.attempts == 0
        assert parked.status != JobStatus.SUCCEEDED.value, (
            "refusing work must never look like having done it"
        )

    @pytest.mark.asyncio
    async def test_the_parked_job_survives_to_be_run_by_a_capable_worker(
        self, store, pg_session
    ):
        job_id = store.enqueue("documents", payload={"result_id": "r1"}).job_id
        job = pg_session.get(Job, job_id)
        job.payload_schema_version = 999
        pg_session.flush()
        store.park_incompatible(job_id, 999)

        assert store.release_incompatible(frozenset({999})) == 1
        pg_session.expire_all()
        recovered = pg_session.get(Job, job_id)
        assert recovered.status == JobStatus.QUEUED.value
        assert recovered.payload == {"result_id": "r1"}, "the work itself is intact"

    def test_no_duplicate_result_is_produced_by_parking(self, store, pg_session):
        """Parking twice is idempotent: it is a state, not an event."""
        job_id = store.enqueue("documents", payload={}).job_id
        job = pg_session.get(Job, job_id)
        job.payload_schema_version = 999
        pg_session.flush()
        store.park_incompatible(job_id, 999)
        store.park_incompatible(job_id, 999)
        assert pg_session.get(Job, job_id).attempts == 0


class _SessionScope:
    """Hand the worker the test's session instead of opening its own."""

    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, *exc):
        return False

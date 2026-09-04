"""Dead jobs, visible to the workspace that owns them and to nobody else.

Work the queue gave up on used to be invisible outside the database. The run
said "failed" and the reason - three attempts, lease lost, last error - lived
only in a table nobody was looking at.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.test_security import register

# The two-tenant harness already exists beside the security suite, and a second
# copy would be a second thing to keep in step with the auth settings it
# configures. Loaded as a plugin rather than imported, so `auth_client` arrives
# as a fixture instead of as a module-level name every test then shadows.
pytest_plugins = ["tests.test_security"]


def make_job(session, run_id: str, *, status: str, kind: str = "research") -> str:
    from app.models import Job
    from app.models.base import new_id

    job = Job(
        id=new_id(),
        kind=kind,
        queue="default",
        run_id=run_id,
        status=status,
        attempts=3,
        max_attempts=3,
        available_at=datetime.now(UTC),
        payload={},
        last_error="the worker holding this job stopped without finishing",
    )
    session.add(job)
    session.commit()
    return job.id


def make_run(session, organization_id: str) -> str:
    """A run belonging to an organization, without paying for a research run."""
    from app.models import ApplicantProfileRow, ResearchRun
    from app.models.base import new_id

    profile = ApplicantProfileRow(
        id=new_id(), organization_id=organization_id, display_name="t", payload={}
    )
    session.add(profile)
    session.flush()
    run = ResearchRun(id=new_id(), profile_id=profile.id, stage="failed")
    session.add(run)
    session.commit()
    return run.id


@pytest.fixture
def session():
    import app.db as db_module

    s = db_module.SessionLocal()
    try:
        yield s
    finally:
        s.close()


def organization_of(client) -> str:
    return client.get("/api/auth/me").json()["organization_id"]


class TestWhatAnOwnerSees:
    def test_a_dead_job_of_my_workspace_is_listed_with_its_cause(self, auth_client, session):
        client, _ = auth_client
        register(client, "alice")
        run_id = make_run(session, organization_of(client))
        make_job(session, run_id, status="dead")

        response = client.get("/api/admin/jobs?status=dead")
        assert response.status_code == 200
        listed = response.json()
        assert len(listed) == 1
        assert listed[0]["run_id"] == run_id
        assert listed[0]["attempts"] == 3
        assert "stopped without finishing" in listed[0]["last_error"]

    def test_the_count_is_a_header_so_the_ui_need_not_fetch_the_list(self, auth_client, session):
        """ "3 jobs need attention" is one request, not a page of job rows."""
        client, _ = auth_client
        register(client, "alice")
        run_id = make_run(session, organization_of(client))
        for _ in range(3):
            make_job(session, run_id, status="dead")

        response = client.get("/api/admin/jobs?status=dead&limit=1")
        assert response.headers["X-Total-Count"] == "3"
        assert len(response.json()) == 1

    def test_healthy_jobs_are_not_reported_as_needing_attention(self, auth_client, session):
        client, _ = auth_client
        register(client, "alice")
        run_id = make_run(session, organization_of(client))
        make_job(session, run_id, status="succeeded")
        make_job(session, run_id, status="queued")

        assert client.get("/api/admin/jobs?status=dead").json() == []


class TestWhatIsRefused:
    def test_another_workspaces_dead_job_is_not_mine_to_see(self, auth_client, session):
        """The queue is one table for the whole deployment; the view is not."""
        client, _ = auth_client
        register(client, "alice")
        alice_org = organization_of(client)
        client.post("/api/auth/logout")

        register(client, "bob")
        bob_run = make_run(session, organization_of(client))
        make_job(session, bob_run, status="dead")
        alice_run = make_run(session, alice_org)
        make_job(session, alice_run, status="dead")

        listed = client.get("/api/admin/jobs?status=dead").json()
        assert [job["run_id"] for job in listed] == [bob_run]

    def test_an_unknown_status_is_refused_rather_than_matching_nothing(self, auth_client):
        """Silently returning [] would read as "your queue is fine"."""
        client, _ = auth_client
        register(client, "alice")
        response = client.get("/api/admin/jobs?status=deadd")
        assert response.status_code == 400
        assert "deadd" in response.json()["detail"]

    def test_signing_in_is_required(self, auth_client):
        client, _ = auth_client
        assert client.get("/api/admin/jobs?status=dead").status_code == 401

    def test_a_member_is_not_an_operator(self, auth_client, session):
        client, _ = auth_client
        register(client, "alice")
        from app.models import OrganizationMembership

        membership = session.query(OrganizationMembership).first()
        membership.role = "member"
        session.commit()

        assert client.get("/api/admin/jobs?status=dead").status_code == 403

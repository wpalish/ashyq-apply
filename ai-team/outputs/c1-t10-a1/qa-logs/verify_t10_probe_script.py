"""T10 VERIFY_CANDIDATE — independent adversarial probes (QA, read-only). v2

Runs against a throwaway embedded PostgreSQL (pgserver). Nothing in the
worktree is modified; this file lives in /tmp. Each probe uses its own queue
so leftover rows can never be picked up by a later claim.
"""
import asyncio
import os
import sys
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

BACKEND = Path("/Users/wpalish/ashyq-worktrees/c1-t10-verify/backend")
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

import pgserver  # noqa: E402
import sqlalchemy as sa  # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="qa-t10-verify-pg-")
_server = pgserver.get_server(_tmpdir)
PG_URI = _server.get_uri().replace("postgresql://", "postgresql+psycopg://")
_dbname = f"qa{uuid.uuid4().hex[:12]}"
_admin = sa.create_engine(PG_URI, isolation_level="AUTOCOMMIT")
with _admin.connect() as conn:
    conn.execute(sa.text(f'CREATE DATABASE "{_dbname}"'))
_admin.dispose()

from urllib.parse import urlsplit, urlunsplit  # noqa: E402

_p = urlsplit(PG_URI)
DB_URL = urlunsplit((_p.scheme, _p.netloc, f"/{_dbname}", _p.query, _p.fragment))
print("DB_URL:", DB_URL)

os.environ["UNIMATCH_DEMO_MODE"] = "true"
os.environ["UNIMATCH_DATABASE_URL"] = DB_URL
os.environ["UNIMATCH_CACHE_DIR"] = "/tmp/qa-t10-cache"
os.environ["UNIMATCH_EXPORT_DIR"] = "/tmp/qa-t10-exports"
os.environ["UNIMATCH_CORPUS_DIR"] = str(BACKEND / "app" / "corpus" / "pages")
os.environ["UNIMATCH_FETCH_DELAY_SECONDS"] = "0.0"
os.environ["UNIMATCH_ENABLE_BROWSER_TIER"] = "false"

from app.db import migrate_to_head  # noqa: E402

migrate_to_head(DB_URL)

ENGINE = sa.create_engine(DB_URL)
FACTORY = sa.orm.sessionmaker(bind=ENGINE, future=True)

from app.config import Settings  # noqa: E402
from app.domain.enums import PipelineStage  # noqa: E402
from app.jobs.store import JobStore  # noqa: E402
from app.jobs.worker import Worker  # noqa: E402
from app.models import (  # noqa: E402
    ApplicantProfileRow,
    Job,
    JobStatus,
    Organization,
    ResearchRun,
)
from app.pipeline.runner import ResearchRunner  # noqa: E402
from app.pipeline.state import RunState  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def raw_job(job_id):
    with FACTORY() as s:
        row = s.execute(
            sa.text(
                "SELECT status, attempts, worker_id, last_error, finished_at, cancel_requested,"
                " lease_expires_at, available_at FROM jobs WHERE id = :i"
            ),
            {"i": job_id},
        ).mappings().one()
    return dict(row)


PROFILE_PAYLOAD = {
    "display_name": "qa",
    "context": {
        "level": "bachelor",
        "intended_fields": ["computer science"],
        "intake_term": "fall",
        "intake_year": 2027,
        "citizenship": "Kazakhstan",
        "country_of_residence": "Kazakhstan",
        "education_country": "Kazakhstan",
        "education_system": "KZ national secondary",
        "graduation_date": "2027-05-25",
    },
    "academics": {"gpa": {"raw_value": 4.8, "raw_scale_max": 5.0, "raw_scale_label": "KZ"}},
    "preferences": {"preferred_countries": ["Netherlands"]},
    "funding": {"max_annual_budget": 6000, "max_acceptable_gap": 6000},
}


def seed(queue="default"):
    with FACTORY() as s:
        if s.get(Organization, "00000000000000000000000000000001") is None:
            s.add(
                Organization(
                    id="00000000000000000000000000000001", name="QA verify", slug="qa-verify"
                )
            )
            s.flush()
        prow = ApplicantProfileRow(
            organization_id="00000000000000000000000000000001",
            display_name="qa",
            payload=PROFILE_PAYLOAD,
        )
        s.add(prow)
        s.flush()
        run = ResearchRun(
            profile_id=prow.id,
            stage="queued",
            demo_mode=True,
            candidate_limit=3,
            verify_limit=3,
            stage_state=RunState.load(None).dump(),
        )
        s.add(run)
        s.flush()
        job_id = JobStore(s).enqueue("research", run_id=run.id, queue=queue).job_id
        s.commit()
        return run.id, job_id


def expire_lease_and_reap(job_id):
    with FACTORY() as s:
        s.execute(
            sa.update(Job)
            .where(Job.id == job_id)
            .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        s.commit()
        reaped = JobStore(s).reap_expired()
        s.execute(sa.update(Job).where(Job.id == job_id).values(available_at=datetime.now(UTC)))
        s.commit()
        return reaped


def settings_for_pg():
    return Settings(
        demo_mode=True,
        database_url=DB_URL,
        cache_dir=Path("/tmp/qa-t10-cache"),
        export_dir=Path("/tmp/qa-t10-exports"),
        corpus_dir=BACKEND / "app" / "corpus" / "pages",
        fetch_delay_seconds=0.0,
        candidate_limit=3,
        verify_limit=3,
        academic_year="2026/27",
        target_currency="USD",
        enable_browser_tier=False,
    )


# ---------------------------------------------------------------------------
print("\n=== PROBE 1: two-session PG, same worker_id reclaim fences attempt 1 ===")
_, job1_id = seed(queue="p1")
s1 = FACTORY()
store1 = JobStore(s1, worker_id="w")
j1 = store1.claim(worker_id="w", queue="p1")
s1.commit()
t1 = j1.attempts
check("1a claim t1", j1.id == job1_id and t1 == 1, f"attempts={t1}")

reaped = expire_lease_and_reap(job1_id)
check("1b reap after expiry", reaped == [job1_id], f"reaped={reaped}")

s2 = FACTORY()
store2 = JobStore(s2, worker_id="w")
j2 = store2.claim(worker_id="w", queue="p1")
s2.commit()
t2 = j2.attempts
reap_note = raw_job(job1_id)["last_error"]
check("1c same worker_id re-claims, attempts=t1+1", j2.id == job1_id and t2 == t1 + 1, f"t2={t2}")

r_complete = store1.complete(job1_id, lease_token=t1)
r_beat = store1.heartbeat(job1_id, lease_token=t1)
r_fail = store1.fail(job1_id, "STALE-1-ERROR", lease_token=t1)
r_cancel = store1.mark_cancelled(job1_id, "STALE-1-CANCEL", lease_token=t1)
s1.commit()
s1.close()
row = raw_job(job1_id)
check("1d stale complete -> False", r_complete is False, f"got {r_complete}")
check("1e stale heartbeat -> False", r_beat is False, f"got {r_beat}")
check("1f stale fail -> read-only current status", r_fail == JobStatus.RUNNING.value, f"got {r_fail!r}")
check("1g stale mark_cancelled -> False", r_cancel is False, f"got {r_cancel}")
check(
    "1h row untouched by stale attempt",
    row["status"] == "running"
    and row["attempts"] == t2
    and row["last_error"] == reap_note
    and "STALE" not in (row["last_error"] or "")
    and row["finished_at"] is None
    and row["worker_id"] == "w",
    f"row={row}",
)
own = store2.complete(job1_id, lease_token=t2)
s2.commit()
s2.close()
check("1i new owner completes with t2", own is True and raw_job(job1_id)["status"] == "succeeded")

# ---------------------------------------------------------------------------
print("\n=== PROBE 2: LeaseLost mid-run — stale attempt writes NOTHING (real PG) ===")
run2_id, job2_id = seed(queue="p2")
worker = Worker(settings_for_pg())
with FACTORY() as s:
    got = JobStore(s).claim(worker_id=worker.worker_id, queue="p2")
    s.commit()
    got_id = got.id if got else None
check("2a claim", got_id == job2_id, f"claimed={got_id}")

checkpoint = {}
original_verify = ResearchRunner._stage_verify


async def verify_then_takeover(self, fetcher):
    await original_verify(self, fetcher)
    with FACTORY() as other:
        other.execute(
            sa.text("UPDATE jobs SET worker_id = 'worker-b' WHERE id = :i"), {"i": job2_id}
        )
        other.commit()
    with FACTORY() as other:
        r = other.execute(
            sa.text("SELECT stage, errors, finished_at FROM research_runs WHERE id = :i"),
            {"i": run2_id},
        ).mappings().one()
        checkpoint["stage"] = r["stage"]
        checkpoint["errors"] = list(r["errors"] or [])
        checkpoint["finished_at"] = r["finished_at"]
        checkpoint["results"] = other.execute(
            sa.text("SELECT COUNT(*) FROM program_results WHERE run_id = :i"), {"i": run2_id}
        ).scalar()


with patch.object(ResearchRunner, "_stage_verify", verify_then_takeover):
    asyncio.run(worker.execute(job2_id))

row = raw_job(job2_id)
with FACTORY() as s:
    r = s.execute(
        sa.text("SELECT stage, errors, finished_at FROM research_runs WHERE id = :i"),
        {"i": run2_id},
    ).mappings().one()
    audits = s.execute(
        sa.text("SELECT COUNT(*) FROM audit_events WHERE entity_id = :i AND action = 'run_failed'"),
        {"i": run2_id},
    ).scalar()
    results_now = s.execute(
        sa.text("SELECT COUNT(*) FROM program_results WHERE run_id = :i"), {"i": run2_id}
    ).scalar()

check("2b worker exited via LeaseLost branch", worker.jobs_failed == 0, f"jobs_failed={worker.jobs_failed}")
check(
    "2c enough artifacts committed pre-takeover",
    checkpoint["results"] > 0,
    f"results={checkpoint['results']}",
)
check(
    "2d run.stage unchanged (not failed)",
    r["stage"] == checkpoint["stage"] and r["stage"] != PipelineStage.FAILED.value,
    f"checkpoint={checkpoint['stage']!r} final={r['stage']!r}",
)
check("2e run.errors unchanged", list(r["errors"] or []) == checkpoint["errors"], f"errors={list(r['errors'] or [])}")
check("2f run.finished_at still NULL", r["finished_at"] is None)
check("2g no run_failed audit", audits == 0, f"audits={audits}")
check("2h artifacts survive", results_now == checkpoint["results"], f"{results_now} vs {checkpoint['results']}")
check(
    "2i job still with new owner, no stale writes (last_error clean)",
    row["status"] == "running" and row["worker_id"] == "worker-b" and (row["last_error"] or "") == "",
    f"row={row}",
)

# ---------------------------------------------------------------------------
print("\n=== PROBE 3: reap vs heartbeat race (dedicated queue p3) ===")
_, job3_id = seed(queue="p3")
with FACTORY() as s:
    st = JobStore(s, worker_id="w3")
    claimed = st.claim(worker_id="w3", queue="p3")
    s.commit()
    claimed_id = claimed.id if claimed else None
check("3a claimed the probe's own job", claimed_id == job3_id, f"claimed={claimed_id}")
with FACTORY() as s:
    ok = JobStore(s, worker_id="w3").heartbeat(job3_id)
    s.commit()
check("3b heartbeat renews", ok is True)
with FACTORY() as s:
    s.execute(
        sa.text("UPDATE jobs SET lease_expires_at = now() - interval '1 second' WHERE id = :i"),
        {"i": job3_id},
    )
    s.commit()
    JobStore(s, worker_id="w3").heartbeat(job3_id)  # renew AFTER expiry is staged: lease fresh again
    s.commit()
    reaped = JobStore(s).reap_expired()
    s.commit()
row = raw_job(job3_id)
check("3c renewed lease survives reap", reaped == [], f"reaped={reaped}")
check(
    "3d row still running, owned by w3, attempts kept",
    row["status"] == "running" and row["worker_id"] == "w3" and row["attempts"] == 1,
    f"row={row}",
)

# finished job: heartbeat refused, reap skips
_, job3b_id = seed(queue="p3")
with FACTORY() as s:
    st = JobStore(s, worker_id="w3")
    cl = st.claim(worker_id="w3", queue="p3")
    s.commit()
    cl_id = cl.id if cl else None
    tok = st.get(job3b_id).attempts
    done = st.complete(job3b_id, lease_token=tok)
    s.commit()
with FACTORY() as s:
    beat = JobStore(s, worker_id="w3").heartbeat(job3b_id, lease_token=tok)
    s.commit()
with FACTORY() as s:
    reaped_done = JobStore(s).reap_expired()
    s.commit()
check("3e finished job completes once (correct job)", cl_id == job3b_id and done is True)
check("3f heartbeat after finish -> False", beat is False)
check("3g reap skips finished job", reaped_done == [], f"reaped={reaped_done}")

# reap behaviour on a genuinely expired running job: queued + backoff, attempts unchanged
_, job3c_id = seed(queue="p3")
with FACTORY() as s:
    st = JobStore(s, worker_id="w3")
    cl = st.claim(worker_id="w3", queue="p3")
    s.commit()
reaped2 = expire_lease_and_reap(job3c_id)
row = raw_job(job3c_id)
check(
    "3h reap -> queued with backoff, attempts unchanged (claim increments, reap does not)",
    reaped2 == [job3c_id]
    and row["status"] == "queued"
    and row["attempts"] == 1
    and row["worker_id"] is None
    and row["available_at"] is not None
    and row["available_at"] > datetime.now(UTC).replace(tzinfo=row["available_at"].tzinfo) - timedelta(seconds=5),
    f"row={row}",
)

# ---------------------------------------------------------------------------
print("\n=== PROBE 4: cancel API (no token) semantics (dedicated queue p4) ===")
_, job4_id = seed(queue="p4")
with FACTORY() as s:
    c = JobStore(s).cancel(job4_id)
    s.commit()
row = raw_job(job4_id)
check(
    "4a queued -> cancelled",
    c is True
    and row["status"] == "cancelled"
    and row["cancel_requested"] is True
    and row["finished_at"] is not None,
    f"row={row}",
)
with FACTORY() as s:
    c2 = JobStore(s).cancel(job4_id)
    s.commit()
check("4b terminal (cancelled) -> no-op False", c2 is False)

_, job5_id = seed(queue="p4")
with FACTORY() as s:
    cl = JobStore(s, worker_id="w5").claim(worker_id="w5", queue="p4")
    s.commit()
    cl5_id = cl.id if cl else None
check("4c claimed exactly job5", cl5_id == job5_id, f"claimed={cl5_id}")
with FACTORY() as s:
    c3 = JobStore(s).cancel(job5_id)
    s.commit()
row = raw_job(job5_id)
check(
    "4d running -> flag only, status stays running",
    c3 is True
    and row["status"] == "running"
    and row["cancel_requested"] is True
    and row["finished_at"] is None,
    f"row={row}",
)
with FACTORY() as s:
    st = JobStore(s, worker_id="w5")
    tok = st.get(job5_id).attempts
    done = st.complete(job5_id, lease_token=tok)
    s.commit()
row = raw_job(job5_id)
check("4e owner completes flagged job", done is True and row["status"] == "succeeded", f"row={row}")
with FACTORY() as s:
    c4 = JobStore(s).cancel(job5_id)
    s.commit()
check("4f succeeded is terminal -> cancel no-op", c4 is False)

# ---------------------------------------------------------------------------
print("\n=== PROBE 5: positive control — owner+token CAN write (no over-fencing) ===")
_, job6_id = seed(queue="p5")
with FACTORY() as s:
    st = JobStore(s, worker_id="w6")
    cl = st.claim(worker_id="w6", queue="p5")
    s.commit()
    tok = st.get(job6_id).attempts
    beat = st.heartbeat(job6_id, lease_token=tok)
    mk = st.mark_cancelled(job6_id, "user stopped", lease_token=tok)
    s.commit()
row = raw_job(job6_id)
check("5a owner heartbeat True", beat is True)
check(
    "5b owner mark_cancelled True -> cancelled",
    mk is True and row["status"] == "cancelled" and row["worker_id"] is None,
    f"row={row}",
)

_, job7_id = seed(queue="p5")
with FACTORY() as s:
    st = JobStore(s, worker_id="w7")
    cl = st.claim(worker_id="w7", queue="p5")
    s.commit()
    cl_id = cl.id if cl else None
    tok = st.get(job7_id).attempts
    st.fail(job7_id, "boom-1", lease_token=tok)
    s.commit()
row = raw_job(job7_id)
check(
    "5c owner fail retries: queued + last_error recorded",
    cl_id == job7_id and row["status"] == "queued" and row["last_error"] == "boom-1",
    f"row={row}",
)
with FACTORY() as s:
    s.execute(sa.update(Job).where(Job.id == job7_id).values(available_at=datetime.now(UTC)))
    s.commit()
    st = JobStore(s, worker_id="w7")
    j = st.claim(worker_id="w7", queue="p5")
    s.commit()
    tok2 = j.attempts
    final = st.fail(job7_id, "boom-final", retry=False, lease_token=tok2)
    s.commit()
row = raw_job(job7_id)
check("5d non-retry fail -> dead", final == "dead" and row["status"] == "dead", f"row={row}")

# ---------------------------------------------------------------------------
print("\n=== PROBE 6: worker.execute token re-read window (residual risk demo) ===")
run8_id, job8_id = seed(queue="default")
worker8 = Worker(settings_for_pg())
check("6a claim", worker8.claim_one() == job8_id)
# Takeover + FULL re-claim happen BEFORE execute() reads the token, and the
# re-claim uses the SAME worker_id (the self-reap loop with concurrency > 1),
# so only the token could tell the attempts apart. Only possible in
# production if the claim->execute gap outlives the whole lease.
reaped = expire_lease_and_reap(job8_id)
with FACTORY() as s:
    st = JobStore(s, worker_id=worker8.worker_id)
    j = st.claim(worker_id=worker8.worker_id, queue="default")
    s.commit()
    new_tok = j.attempts
asyncio.run(worker8.execute(job8_id))
row = raw_job(job8_id)
with FACTORY() as s:
    r = s.execute(sa.text("SELECT stage FROM research_runs WHERE id = :i"), {"i": run8_id}).scalar()
    aud = s.execute(
        sa.text(
            "SELECT COUNT(*) FROM audit_events WHERE entity_id = :i AND action='job_completed'"
        ),
        {"i": job8_id},
    ).scalar()
print(f"    run.stage after both attempts: {r!r}; job_completed audits: {aud}; jobs_done={worker8.jobs_done}")
check(
    "6b RESULT (residual): stale task read the NEW attempt's token and completed the job",
    reaped == [job8_id] and row["attempts"] == new_tok and row["status"] == "succeeded",
    f"attempts={row['attempts']} new_tok={new_tok} status={row['status']}",
)

print("\n================ SUMMARY ================")
fails = [n for n, ok, _ in RESULTS if not ok]
print(f"total checks: {len(RESULTS)}, failed: {len(fails)}")
if fails:
    print("FAILED:", fails)
ENGINE.dispose()
_server.cleanup()
sys.exit(1 if fails else 0)

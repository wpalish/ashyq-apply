"""T32 A1 contract tests: reextract supersession, the source_scan job, the
refresh endpoint and the retention purge (planner contract C2/C3/C4/C5).

Authored RED-first on baseline 2ed4f51e1d5c1fae3f4cb36ad64982eb67184a2d
(branch ``ai/c2/t32/qa``). Expected result modes on that baseline:

- Every scenario here is contract RED-pending: the ``reextract_page`` and
  ``source_scan`` job kinds, the refresh route and ``purge_source_pages`` do
  not exist yet. The dispatch-driven tests fail with assertions (the worker
  marks the unknown kind DEAD with ``unknown job kind ...`` — each failure
  message records that reason); the purge test fails on the ImportError of
  the not-yet-existing module.
- The two-session race tests use genuinely independent PostgreSQL sessions
  (one per factory call) and a lease takeover that happens mid-handler, so
  the fencing/atomicity semantics are the real thing, not a stand-in.

No network: every fetch is answered by a scripted fake bound over
``Fetcher.get`` (the class-level seam), robots outcomes included — the
contract requires all scanner/reextract traffic to go through Fetcher, so
that seam works whichever factory the implementation builds. Nothing here
changes expected behaviour to pass.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.adapters.fetching import FetchResult, Fetcher, FetchOutcome
from app.jobs.store import JobStore
from app.models import ClaimRow, Job, JobStatus, ProgramResultRow, ResearchRun, SourcePage
from tests.conftest import profile_row

#: The corpus page reused as the fake page body: its admissions text provably
#: extracts (ielts_min_overall, admission_deadline) via the html_rule
#: extractors, so the "new claims are appended" half of R5 has deterministic
#: footing.
FAKE_PAGE_BODY_PATH = "app/corpus/pages/tu-delft/admissions.html"

REEXTRACT_KEY = re.compile(r"^reextract:(?P<page>[0-9a-f]{32}):(?P<result>[0-9a-f]{32}):(?P<gen>\d+)$")
ISO_DATE_IN_KEY = re.compile(r"\d{4}-\d{2}-\d{2}")


# --- fixtures and helpers ----------------------------------------------------


@pytest.fixture
def pg_factory(pg_engine):
    """Independent sessions off one migrated PostgreSQL database (the
    test_worker.py pattern): one per call, no shared identity map."""
    return sessionmaker(bind=pg_engine, future=True)


@pytest.fixture
def pg_worker_env(pg_engine, monkeypatch, settings):
    """Point app.db at the per-test PostgreSQL so Worker/reconcile_startup run
    against it (the bound_db pattern, on PostgreSQL)."""
    import app.db as db_module

    factory = sessionmaker(bind=pg_engine, future=True)
    monkeypatch.setattr(db_module, "engine", pg_engine)
    monkeypatch.setattr(db_module, "SessionLocal", factory)
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    return factory


class ScriptedFetcher:
    """Answers Fetcher.get calls from a per-URL script, recording them.

    ``script`` maps a URL (exact) to either a FetchResult or a callable
    ``(url, etag, if_modified_since) -> FetchResult``. Unscripted URLs get a
    404-shaped HTTP_ERROR result so surprises are visible, not silent.
    Robots enforcement lives inside the real Fetcher, so a scripted
    ROBOTS_DISALLOWED result is exactly what the scanner would see.
    """

    def __init__(self, script: dict[str, Any]):
        self.script = script
        self.calls: list[dict[str, Any]] = []

    def result_for(self, url: str, etag: str | None, if_modified_since: str | None) -> FetchResult:
        entry = self.script.get(url)
        if entry is None:
            return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, status_code=404)
        if callable(entry):
            return entry(url, etag, if_modified_since)
        return entry

    async def fake_get(self, url, *, use_cache=True, etag=None, if_modified_since=None):
        self.calls.append(
            {"url": url, "etag": etag, "if_modified_since": if_modified_since}
        )
        return self.result_for(url, etag, if_modified_since)

    def install(self, monkeypatch) -> None:
        monkeypatch.setattr(Fetcher, "get", self.fake_get)


def fake_page_body() -> str:
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / FAKE_PAGE_BODY_PATH
    return path.read_text()


def _seed_page(session, url: str, **kwargs) -> SourcePage:
    page = SourcePage(
        url=url,
        registrable_domain="example.edu",
        institution_key=kwargs.pop("institution_key", "university-of-nowhere"),
        page_type="programme",
        **kwargs,
    )
    session.add(page)
    session.flush()
    return page


def _seed_run_result_claims(session, page: SourcePage, profile, *, claims: int = 1):
    """A run (under a real profile payload — the worker validates it during
    dispatch), a result and live claims reading the given page.

    Returns (run, result_id, claim_ids)."""
    org = profile_row(session, profile.model_dump(mode="json"))
    run = ResearchRun(
        profile_id=org.id,
        stage="awaiting_user_decision",
        demo_mode=True,
        finished_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()
    result_id = uuid.uuid4().hex
    session.add(
        ProgramResultRow(
            run_id=run.id,
            dedupe_key="nl-tudelft-msc-cs",
            university="TU Delft",
            university_key="tudelft",
            country="Netherlands",
            program="MSc Computer Science",
            eligibility="PENDING",
            admissions_fit="PLAUSIBLE_FIT",
            funding_fit="UNKNOWN",
            funding_classification="UNKNOWN",
            payload={"university": "TU Delft", "program": "MSc Computer Science"},
        )
    )
    claim_ids = []
    for _ in range(claims):
        row = ClaimRow(
            run_id=run.id,
            result_id=result_id,
            claim_type="ielts_min_overall",
            status="VERIFIED_CURRENT",
            source_url=page.url,
            source_specificity="program_intake",
            accessed_at=datetime.now(UTC) - timedelta(days=1),
            payload={
                "claim_type": "ielts_min_overall",
                "status": "VERIFIED_CURRENT",
                "source_url": page.url,
                "normalized_value": 6.5,
            },
        )
        session.add(row)
        claim_ids.append(row)
    session.flush()
    page.active_claims = claims
    session.flush()
    return run, result_id, claim_ids


def _enqueue_reextract(session, run, page, result_id: str, reason: str = "content_hash") -> str:
    return JobStore(session).enqueue(
        "reextract_page",
        run_id=run.id,
        payload={
            "source_page_id": page.id,
            "url": page.url,
            "reason": reason,
            "run_id": run.id,
            "result_id": result_id,
        },
    ).job_id


def _drain(settings, limit: int = 5) -> int:
    """Claim and execute queued jobs, as the worker process would."""
    from app.jobs.worker import Worker

    worker = Worker(settings)
    done = 0
    for _ in range(limit):
        job_id = worker.claim_one()
        if job_id is None:
            break
        asyncio.run(worker.execute(job_id))
        done += 1
    return done


# --- R5: reextract supersedes and appends, atomically ------------------------


class TestReextractSupersedesAndAppendsAtomically:
    """C2: one transaction flips the old claims (status column AND payload),
    links them to the source page, inserts the new claims, advances
    lastmod_seen and completes the job. A fenced or crashed attempt writes
    neither side."""

    def test_a_forced_page_change_supersedes_old_and_appends_new_in_one_commit(
        self, pg_worker_env, pg_factory, settings, profile, monkeypatch
    ):
        changed = FetchResult(
            url="https://example.edu/programme",
            outcome=FetchOutcome.OK,
            status_code=200,
            text=fake_page_body(),
            content_type="text/html; charset=utf-8",
            etag='"v2"',
            content_hash="ab" * 32,
        )
        fetcher = ScriptedFetcher({"https://example.edu/programme": changed})
        fetcher.install(monkeypatch)

        session = pg_factory()
        try:
            page = _seed_page(
                session,
                "https://example.edu/programme",
                etag='"v1"',
                content_hash="cd" * 32,
                fetched_at=datetime.now(UTC) - timedelta(days=1),
            )
            run, result_id, old_claim_rows = _seed_run_result_claims(session, page, profile)
            job_id = _enqueue_reextract(session, run, page, result_id)
            page_id = page.id
            run_id = run.id
            old_claim_ids = [c.id for c in old_claim_rows]
            session.commit()
        finally:
            session.close()

        assert _drain(settings) == 1

        check = pg_factory()
        try:
            job = check.get(Job, job_id)
            assert job.status == JobStatus.SUCCEEDED.value, (
                f"reextract_page must be a dispatched kind (baseline: "
                f"last_error={job.last_error!r} — 'unknown job kind')"
            )
            olds = check.query(ClaimRow).filter(ClaimRow.id.in_(old_claim_ids)).all()
            assert olds, "the old rows must survive — superseded, never deleted"
            for old in olds:
                assert old.status == "SUPERSEDED", "the status column must flip"
                assert old.payload["status"] == "SUPERSEDED", (
                    "GET /claims reads **payload — the embedded status must flip too"
                )
                assert old.source_page_id == page_id, "the row must link to its page"
                assert old.payload["normalized_value"] == 6.5, "the old value is history, kept"
                assert old.claim_type == "ielts_min_overall"

            news = (
                check.query(ClaimRow)
                .filter(
                    ClaimRow.run_id == run_id,
                    ClaimRow.result_id == result_id,
                    ClaimRow.status == "VERIFIED_CURRENT",
                )
                .all()
            )
            assert news, "the re-read evidence must be appended"
            assert all(c.source_url == "https://example.edu/programme" for c in news)
            assert any(c.claim_type == "ielts_min_overall" for c in news), (
                "the corpus admissions page yields ielts_min_overall claims; "
                "the new extraction must land next to the superseded rows"
            )
            assert all(c.source_page_id == page_id for c in news)

            fresh_page = check.get(SourcePage, page_id)
            assert fresh_page.etag == '"v2"', "the page row carries the new validators"
        finally:
            check.close()

    def test_a_fenced_or_crashed_attempt_writes_neither_side(
        self, pg_worker_env, pg_factory, settings, profile, monkeypatch
    ):
        """The lease is taken away mid-handler (a crash the reaper observes).
        The stale attempt's completion is refused, its transaction rolls back,
        and neither the supersession nor the new claims may appear — the new
        owner's attempt is the only writer."""
        from app.jobs.worker import Worker

        takeover = {"done": False}
        changed = FetchResult(
            url="https://example.edu/programme",
            outcome=FetchOutcome.OK,
            status_code=200,
            text=fake_page_body(),
            content_type="text/html; charset=utf-8",
            etag='"v2"',
        )

        def page_fetch(url, etag, ims):
            if not takeover["done"]:
                _take_over(pg_factory, "reextract_page", takeover)
            return changed

        fetcher = ScriptedFetcher(
            {
                "https://example.edu/programme": page_fetch,
            }
        )
        fetcher.install(monkeypatch)

        session = pg_factory()
        try:
            page = _seed_page(session, "https://example.edu/programme", etag='"v1"')
            run, result_id, old_claim_rows = _seed_run_result_claims(session, page, profile)
            job_id = _enqueue_reextract(session, run, page, result_id)
            result_id_only = result_id
            old_count = len(old_claim_rows)
            session.commit()
        finally:
            session.close()

        worker = Worker(settings)
        assert worker.claim_one() == job_id
        asyncio.run(worker.execute(job_id))

        check = pg_factory()
        try:
            job = check.get(Job, job_id)
            assert job.status == JobStatus.RUNNING.value and job.attempts == 2, (
                "the takeover must have happened mid-handler (baseline: the "
                f"unknown kind died at attempt 1: {job.status}/{job.attempts})"
            )

            for old in (
                check.query(ClaimRow).filter(ClaimRow.result_id == result_id_only).all()
            ):
                assert old.status != "SUPERSEDED", (
                    "a fenced attempt must not leave a superseded claim behind"
                )
                assert old.payload["status"] != "SUPERSEDED"
            news = (
                check.query(ClaimRow)
                .filter(
                    ClaimRow.result_id == result_id_only,
                    ClaimRow.status == "VERIFIED_CURRENT",
                )
                .all()
            )
            assert len(news) == old_count, (
                "a fenced attempt must not append re-read claims"
            )
            assert takeover["done"], "the takeover hook must have fired"
        finally:
            check.close()


def _take_over(factory, kind: str, takeover: dict) -> None:
    """Expire the lease, let the reaper queue the job, and have worker-b claim
    it — all from a second, independent session, while the handler runs."""
    takeover["done"] = True
    with factory() as session:
        job_id = session.query(Job).filter(Job.kind == kind).one().id
        session.execute(
            sa.update(Job)
            .where(Job.id == job_id)
            .values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        session.commit()
        assert JobStore(session).reap_expired() == [job_id]
        JobStore(session, worker_id="worker-b").claim(worker_id="worker-b")
        session.commit()


# --- source_scan skeleton (C3) -----------------------------------------------


def _seed_scan_world(session, profile, *, institution: str, url: str = "https://example.edu/programme", etag: str = '"v1"'):
    page = _seed_page(
        session,
        url,
        institution_key=institution,
        etag=etag,
        content_hash="cd" * 32,
        lastmod_seen=datetime.now(UTC) - timedelta(days=30),
        fetched_at=datetime.now(UTC) - timedelta(days=1),
    )
    run, result_id, _old = _seed_run_result_claims(session, page, profile)
    return page, run, result_id


def _enqueue_scan(session, institution: str) -> str:
    return JobStore(session).enqueue(
        "source_scan",
        payload={"institution_key": institution},
        idempotency_key=f"source_scan:{institution}:{datetime.now(UTC).date().isoformat()}",
    ).job_id


def _sitemap_body(lastmod: datetime) -> str:
    stamp = lastmod.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        "  <url>\n"
        "    <loc>https://example.edu/programme</loc>\n"
        f"    <lastmod>{stamp}</lastmod>\n"
        "  </url>\n"
        "</urlset>\n"
    )


class TestSourceScanSkeleton:
    """C3: a durable, self-rescheduling scan job. Robots and conditional GETs
    through Fetcher; reextract enqueued only for pages whose content moved."""

    def test_sitemap_lastmod_triggers_conditional_get_and_reextract_enqueue(
        self, pg_worker_env, pg_factory, settings, profile, monkeypatch
    ):
        newer = datetime.now(UTC) - timedelta(days=1)
        world: dict = {}

        def sitemap(url, etag, ims):
            return FetchResult(
                url=url,
                outcome=FetchOutcome.OK,
                status_code=200,
                text=_sitemap_body(newer),
                content_type="application/xml",
            )

        def page_fetch(url, etag, ims):
            assert etag == world["stored_etag"], (
                "the conditional GET must carry the stored ETag"
            )
            return FetchResult(
                url=url,
                outcome=FetchOutcome.OK,
                status_code=200,
                text=fake_page_body(),
                content_type="text/html; charset=utf-8",
                etag='"v2"',
                content_hash="ab" * 32,
            )

        fetcher = ScriptedFetcher(
            {
                "https://example.edu/sitemap.xml": sitemap,
                "https://example.edu/programme": page_fetch,
            }
        )
        fetcher.install(monkeypatch)

        session = pg_factory()
        try:
            page, run, result_id = _seed_scan_world(session, profile, institution="university-of-nowhere")
            world["page_id"] = page.id
            world["stored_etag"] = page.etag
            world["result_id"] = result_id
            job_id = _enqueue_scan(session, "university-of-nowhere")
            session.commit()
        finally:
            session.close()

        assert _drain(settings) == 1

        check = pg_factory()
        try:
            job = check.get(Job, job_id)
            assert job.status == JobStatus.SUCCEEDED.value, (
                f"source_scan must be a dispatched kind (baseline: "
                f"last_error={job.last_error!r})"
            )
            conditional = [
                c for c in fetcher.calls if c["url"] == "https://example.edu/programme"
            ]
            assert conditional, "a stored page with a moved lastmod must get a conditional GET"
            assert conditional[0]["etag"] == world["stored_etag"]

            reextracts = check.query(Job).filter(Job.kind == "reextract_page").all()
            assert len(reextracts) == 1, "one reextract per affected (page, result)"
            payload = reextracts[0].payload or {}
            assert payload.get("source_page_id") == world["page_id"]
            assert payload.get("result_id") == world["result_id"]
            assert payload.get("reason") == "sitemap_lastmod"

            fresh = check.get(SourcePage, world["page_id"])
            assert fresh.lastmod_seen is not None, "lastmod_seen must advance"
            tomorrow = _next_utc_midnight()
            followups = (
                check.query(Job)
                .filter(Job.kind == "source_scan", Job.status == JobStatus.QUEUED.value)
                .all()
            )
            assert followups, "the scan must reschedule itself for tomorrow"
            assert all(ensure_utc_strict(j.available_at) >= tomorrow for j in followups)
        finally:
            check.close()

    def test_a_304_short_circuits_without_extraction(
        self, pg_worker_env, pg_factory, settings, profile, monkeypatch
    ):
        def sitemap(url, etag, ims):
            return FetchResult(
                url=url,
                outcome=FetchOutcome.OK,
                status_code=200,
                text=_sitemap_body(datetime.now(UTC)),
                content_type="application/xml",
            )

        fetcher = ScriptedFetcher(
            {
                "https://example.edu/sitemap.xml": sitemap,
                "https://example.edu/programme": lambda url, etag, ims: FetchResult(
                    url=url,
                    outcome=FetchOutcome.CACHED,
                    status_code=304,
                    etag=etag or "",
                ),
            }
        )
        fetcher.install(monkeypatch)

        session = pg_factory()
        try:
            page, run, _result = _seed_scan_world(session, profile, institution="university-of-nowhere")
            page_id = page.id
            fetched_before = page.fetched_at
            job_id = _enqueue_scan(session, "university-of-nowhere")
            session.commit()
        finally:
            session.close()

        assert _drain(settings) == 1

        check = pg_factory()
        try:
            assert check.query(Job).filter(Job.kind == "reextract_page").count() == 0, (
                "a 304 means the copy is current: zero extraction, zero reextract"
            )
            fresh = check.get(SourcePage, page_id)
            assert fresh.etag == '"v1"', "a 304 must not invent new validators"
            assert fetched_before is not None
            assert check.get(Job, job_id).status == JobStatus.SUCCEEDED.value
        finally:
            check.close()

    def test_robots_disallowed_skips_and_records_nothing(
        self, pg_worker_env, pg_factory, settings, profile, monkeypatch
    ):
        fetcher = ScriptedFetcher(
            {
                "https://example.edu/sitemap.xml": FetchResult(
                    url="https://example.edu/sitemap.xml",
                    outcome=FetchOutcome.ROBOTS_DISALLOWED,
                    error="robots.txt disallows this path",
                ),
            }
        )
        fetcher.install(monkeypatch)

        session = pg_factory()
        try:
            page, _run, _result = _seed_scan_world(session, profile, institution="university-of-nowhere")
            page_id = page.id
            before = (
                page.etag,
                page.fetched_at,
                page.content_hash,
                page.lastmod_seen,
            )
            job_id = _enqueue_scan(session, "university-of-nowhere")
            session.commit()
        finally:
            session.close()

        assert _drain(settings) == 1

        check = pg_factory()
        try:
            job = check.get(Job, job_id)
            assert job.status == JobStatus.SUCCEEDED.value, (
                f"source_scan must be a dispatched kind (baseline: "
                f"last_error={job.last_error!r})"
            )
            fresh = check.get(SourcePage, page_id)
            assert (
                fresh.etag,
                fresh.fetched_at,
                fresh.content_hash,
                fresh.lastmod_seen,
            ) == before, "a robots-disallowed source must be skipped, recording nothing"
            assert check.query(Job).filter(Job.kind == "reextract_page").count() == 0
        finally:
            check.close()


def _next_utc_midnight() -> datetime:
    now = datetime.now(UTC)
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def ensure_utc_strict(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class TestSourceScanBootstrapRaces:
    """C3: reconcile_startup bootstraps one scan per institution; the
    idempotency key (date IS the generation) makes a double bootstrap and a
    lease takeover safe. Two independent PostgreSQL sessions throughout."""

    def test_double_bootstrap_enqueues_one_scan_per_institution(
        self, pg_worker_env, pg_factory, settings, profile
    ):
        from app.jobs.worker import reconcile_startup

        session = pg_factory()
        try:
            _seed_scan_world(session, profile, institution="university-a", url="https://a.example.edu/programme")
            _seed_page(session, "https://a.example.edu/other", institution_key="university-a")
            _seed_scan_world(session, profile, institution="university-b", url="https://b.example.edu/programme")
            session.commit()
        finally:
            session.close()

        reconcile_startup()
        reconcile_startup()

        check = pg_factory()
        try:
            scans = check.query(Job).filter(Job.kind == "source_scan").all()
            assert len(scans) == 2, (
                f"one scan per institution, double bootstrap or not (baseline: "
                f"{len(scans)} — reconcile_startup does not bootstrap scans yet)"
            )
            keys = {j.idempotency_key for j in scans}
            assert len(keys) == 2
            tomorrow = _next_utc_midnight()
            for job in scans:
                assert ensure_utc_strict(job.available_at) >= tomorrow
                assert ensure_utc_strict(job.available_at) < tomorrow + timedelta(hours=1), (
                    "the bootstrap stagger must stay inside the first hour"
                )
                assert ISO_DATE_IN_KEY.search(job.idempotency_key), (
                    "the date IS the generation for scans"
                )
        finally:
            check.close()

    def test_a_lease_takeover_does_not_duplicate_reextract_enqueues(
        self, pg_worker_env, pg_factory, settings, profile, monkeypatch
    ):
        """worker-a loses the lease mid-scan; everything it staged must roll
        back, and the surviving attempt must leave exactly one reextract set."""
        from app.jobs.worker import Worker

        takeover = {"done": False}

        def sitemap(url, etag, ims):
            if not takeover["done"]:
                _take_over(pg_factory, "source_scan", takeover)
            return FetchResult(
                url=url,
                outcome=FetchOutcome.OK,
                status_code=200,
                text=_sitemap_body(datetime.now(UTC) - timedelta(hours=2)),
                content_type="application/xml",
            )

        fetcher = ScriptedFetcher(
            {
                "https://example.edu/sitemap.xml": sitemap,
                "https://example.edu/programme": lambda url, etag, ims: FetchResult(
                    url=url,
                    outcome=FetchOutcome.OK,
                    status_code=200,
                    text=fake_page_body(),
                    content_type="text/html; charset=utf-8",
                    etag='"v2"',
                    content_hash="ab" * 32,
                ),
            }
        )
        fetcher.install(monkeypatch)

        session = pg_factory()
        try:
            page, run, result_id = _seed_scan_world(session, profile, institution="university-of-nowhere")
            page_id = page.id
            _enqueue_scan(session, "university-of-nowhere")
            session.commit()
        finally:
            session.close()

        worker = Worker(settings)
        scan_id = worker.claim_one()
        assert scan_id is not None
        asyncio.run(worker.execute(scan_id))

        # worker-b now owns a RUNNING attempt it never executed: run it.
        check = pg_factory()
        try:
            job = check.get(Job, scan_id)
            assert job.status == JobStatus.RUNNING.value and job.attempts == 2, (
                "the takeover must have happened mid-scan (baseline: the "
                f"unknown kind died at attempt 1: {job.status}/{job.attempts})"
            )
        finally:
            check.close()
        asyncio.run(worker.execute(scan_id))

        check = pg_factory()
        try:
            reextracts = (
                check.query(Job)
                .filter(
                    Job.kind == "reextract_page",
                    Job.status == JobStatus.QUEUED.value,
                )
                .all()
            )
            assert len(reextracts) == 1, (
                f"exactly one reextract set must survive the takeover (got "
                f"{len(reextracts)})"
            )
            payload = reextracts[0].payload or {}
            assert payload.get("result_id") == result_id
            assert payload.get("source_page_id") == page_id
        finally:
            check.close()


# --- C4: the retention purge -------------------------------------------------


class TestRetentionPurge:
    """C4: purge_source_pages bulk-deletes rows the T28 predicate calls
    purgeable; once a day; active pages never touched."""

    def test_purge_removes_only_purgeable_rows(self, pg_factory):
        from app.jobs.source_scanner import purge_source_pages

        session = pg_factory()
        try:
            now = datetime.now(UTC)
            old_empty = _seed_page(
                session,
                "https://example.edu/old-empty",
                fetched_at=now - timedelta(days=200),
            )
            old_active = _seed_page(
                session,
                "https://example.edu/old-active",
                fetched_at=now - timedelta(days=200),
            )
            old_active.active_claims = 3
            fresh = _seed_page(session, "https://example.edu/fresh", fetched_at=now)
            session.commit()

            purged = purge_source_pages(session, now)
            session.commit()

            assert purged >= 1
            assert session.get(SourcePage, old_empty.id) is None, "purgeable rows go"
            assert session.get(SourcePage, fresh.id) is not None, "fresh rows stay"
            assert session.get(SourcePage, old_active.id) is not None, (
                "active_claims > 0 is never purged"
            )
        finally:
            session.close()


# --- R7: the refresh endpoint (C5) -------------------------------------------


def _unlock_case(client, case_id: str) -> None:
    import json as _json

    from tests.conftest import sign_webhook

    order = client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    ).json()
    body = _json.dumps(
        {"event": "invoice.status_changed", "data": {"id": order["id"], "status": "paid"}}
    ).encode()
    client.post(
        "/webhooks/apipay",
        content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sign_webhook(body)},
    )


def _seed_refresh_run(client, case_id: str, *, demo: bool, pages: int, unknown_url: bool = False):
    """A run (optionally non-demo), a result, live claims over source_pages.

    Seeded directly so no network is involved: the point is the endpoint's
    contract, not the pipeline's."""
    from app.db import session_scope

    with session_scope() as session:
        run = ResearchRun(
            profile_id=case_id,
            stage="awaiting_user_decision",
            demo_mode=demo,
            finished_at=datetime.now(UTC),
        )
        session.add(run)
        session.flush()
        result_id = uuid.uuid4().hex
        session.add(
            ProgramResultRow(
                run_id=run.id,
                dedupe_key=f"dedupe-{result_id[:8]}",
                university="TU Delft",
                university_key="tudelft",
                country="Netherlands",
                program="MSc Computer Science",
                eligibility="PENDING",
                admissions_fit="PLAUSIBLE_FIT",
                funding_fit="UNKNOWN",
                funding_classification="UNKNOWN",
                payload={"university": "TU Delft", "program": "MSc Computer Science"},
            )
        )
        urls = []
        for n in range(pages):
            url = f"https://example.edu/programme-{n}"
            page = SourcePage(
                url=url,
                registrable_domain="example.edu",
                active_claims=1,
            )
            session.add(page)
            session.flush()
            session.add(
                ClaimRow(
                    run_id=run.id,
                    result_id=result_id,
                    claim_type="ielts_min_overall",
                    status="VERIFIED_CURRENT",
                    source_url=url,
                    source_specificity="program_intake",
                    payload={
                        "claim_type": "ielts_min_overall",
                        "status": "VERIFIED_CURRENT",
                        "source_url": url,
                    },
                )
            )
            urls.append(url)
        if unknown_url:
            session.add(
                ClaimRow(
                    run_id=run.id,
                    result_id=result_id,
                    claim_type="tuition",
                    status="VERIFIED_CURRENT",
                    source_url="https://unmapped.example.edu/costs",
                    source_specificity="program_intake",
                    payload={
                        "claim_type": "tuition",
                        "status": "VERIFIED_CURRENT",
                        "source_url": "https://unmapped.example.edu/costs",
                    },
                )
            )
        session.flush()
        return {
            "run_id": run.id,
            "result_id": result_id,
            "urls": urls,
        }


class TestRefreshEndpoint:
    """C5: POST /api/runs/{run_id}/results/{result_id}/refresh — 402 for the
    free tier, 404 across tenants, 409 for demo runs, 202 + jobs for a paying
    tenant, and a double click that still costs one job set."""

    PATH = "/api/runs/{run_id}/results/{result_id}/refresh"

    def test_a_free_tenant_is_refused_with_the_standard_402(self, paid_client, case_id):
        seeded = _seed_refresh_run(paid_client, case_id, demo=False, pages=1)
        response = paid_client.post(
            self.PATH.format(run_id=seeded["run_id"], result_id=seeded["result_id"])
        )
        assert response.status_code == 402, (
            f"the paywall comes first (baseline: route missing → "
            f"{response.status_code} {response.text[:120]!r})"
        )
        assert response.json().get("code") == "payment_required"

    def test_another_tenants_run_is_404_not_a_leak(self, paid_client, case_id):
        """A foreign run must 404 like get_result — never 402/403, which would
        reveal that the identifier exists."""
        from app.db import session_scope
        from app.models import ApplicantProfileRow, Organization

        #: The paid client's principal is the dev tenant (...0001); this is
        #: deliberately a different organization.
        FOREIGN_ORG_ID = "000000000000000000000000000000ff"

        seeded = _seed_refresh_run(paid_client, case_id, demo=False, pages=1)
        # Stand in for another tenant: a second organization and profile; the
        # run is moved under it, so the paid client's principal does not own it.
        with session_scope() as session:
            if session.get(Organization, FOREIGN_ORG_ID) is None:
                session.add(
                    Organization(
                        id=FOREIGN_ORG_ID,
                        name="Another workspace",
                        slug="another-workspace",
                    )
                )
                session.flush()
            foreign_profile = ApplicantProfileRow(
                organization_id=FOREIGN_ORG_ID,
                display_name="foreign",
                payload={"display_name": "foreign"},
            )
            session.add(foreign_profile)
            session.flush()
            session.query(ResearchRun).filter(ResearchRun.id == seeded["run_id"]).update(
                {"profile_id": foreign_profile.id}
            )

        response = paid_client.post(
            self.PATH.format(run_id=seeded["run_id"], result_id=seeded["result_id"])
        )
        assert response.status_code == 404, (
            f"cross-tenant is 404 (baseline: route missing → {response.status_code})"
        )
        assert response.json()["detail"] == "Research run not found", (
            "the tenancy 404 must come from owned_run, not from a missing route"
        )

    def test_a_demo_run_is_409_read_only(self, paid_client, case_id):
        _unlock_case(paid_client, case_id)
        seeded = _seed_refresh_run(paid_client, case_id, demo=True, pages=1)
        response = paid_client.post(
            self.PATH.format(run_id=seeded["run_id"], result_id=seeded["result_id"])
        )
        assert response.status_code == 409, (
            f"demo runs are read-only (baseline: route missing → "
            f"{response.status_code})"
        )
        assert response.json() == {"detail": "demo runs are read-only"}

    def test_a_paid_refresh_schedules_one_reextract_per_page_and_result(
        self, paid_client, case_id
    ):
        _unlock_case(paid_client, case_id)
        seeded = _seed_refresh_run(paid_client, case_id, demo=False, pages=2, unknown_url=True)
        response = paid_client.post(
            self.PATH.format(run_id=seeded["run_id"], result_id=seeded["result_id"])
        )
        assert response.status_code == 202, (
            f"paid refresh schedules work asynchronously (baseline: route "
            f"missing → {response.status_code} {response.text[:120]!r})"
        )
        body = response.json()
        assert body["status"] == "refresh_scheduled"
        assert body["pages"] == 2
        assert len(body["job_ids"]) == 2

        from app.db import session_scope

        with session_scope() as s:
            jobs = s.query(Job).filter(Job.id.in_(body["job_ids"])).all()
            assert len(jobs) == 2
            for job in jobs:
                assert job.kind == "reextract_page"
                payload = job.payload or {}
                assert payload.get("reason") == "manual"
                assert payload.get("run_id") == seeded["run_id"]
                assert payload.get("result_id") == seeded["result_id"]
                assert payload.get("source_page_id")
                assert REEXTRACT_KEY.match(job.idempotency_key), (
                    f"generation key, never a date: {job.idempotency_key!r}"
                )
                assert not ISO_DATE_IN_KEY.search(job.idempotency_key)

            # No fetch/extraction in the request loop: nothing has moved yet.
            flipped = (
                s.query(ClaimRow)
                .filter(
                    ClaimRow.run_id == seeded["run_id"],
                    ClaimRow.status == "SUPERSEDED",
                )
                .count()
            )
            assert flipped == 0

            skipped = body.get("skipped_urls") or []
            assert "https://unmapped.example.edu/costs" in skipped, (
                "a live claim over an unknown URL must be reported, not dropped"
            )

    def test_zero_live_claims_is_a_valid_noop(self, paid_client, case_id):
        _unlock_case(paid_client, case_id)
        seeded = _seed_refresh_run(paid_client, case_id, demo=False, pages=0)
        response = paid_client.post(
            self.PATH.format(run_id=seeded["run_id"], result_id=seeded["result_id"])
        )
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "refresh_scheduled"
        assert body["pages"] == 0
        assert body["job_ids"] == []

    def test_a_double_click_still_costs_one_job_set(self, paid_client, case_id):
        _unlock_case(paid_client, case_id)
        seeded = _seed_refresh_run(paid_client, case_id, demo=False, pages=2)
        path = self.PATH.format(run_id=seeded["run_id"], result_id=seeded["result_id"])
        first = paid_client.post(path)
        assert first.status_code == 202
        second = paid_client.post(path)
        assert second.status_code == 202

        from app.db import session_scope

        with session_scope() as s:
            jobs = s.query(Job).filter(Job.kind == "reextract_page").all()
            assert len(jobs) == len(first.json()["job_ids"]) == 2, (
                "the double click must dedupe to one job set via the "
                f"generation keys (baseline: route missing → {second.status_code})"
            )

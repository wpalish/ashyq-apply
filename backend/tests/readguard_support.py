"""Synthetic real SQL support for native readguard tests; normal application imports.

The claim is real enqueue/claim SQL. Private activation is only a low-level
reservation fixture; full run_to_decision and Worker entry tests are separate.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher, FetchResult
from app.catalogue import discovery as catalogue
from app.config import Settings
from app.domain.enums import ClaimStatus, ClaimType, DegreeLevel, FetchOutcome, PipelineStage
from app.jobs.store import JobStore
from app.models import (
    ApplicantProfileRow,
    ClaimRow,
    Job,
    Organization,
    ProgramResultRow,
    ResearchRun,
)
from app.models import Base as ModelBase
from app.pipeline import read_budget
from app.pipeline.runner import ResearchRunner, _to_out
from app.pipeline.state import RunState
from app.schemas.claim import Claim
from app.schemas.profile import ApplicantProfileIn, ApplicationContext
from app.schemas.result import ProgramResult


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Network/provider/model forbidden in readguard tests")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(httpx.AsyncClient, "send", deny)
    monkeypatch.setattr(httpx.Client, "send", deny)
    from app.adapters import search

    monkeypatch.setattr(search, "get_search_provider", deny)
    monkeypatch.setattr(catalogue, "get_search_provider", deny)


@contextmanager
def make_context(engine, root):
    """Yield a genuine claimed synthetic Job and independent SQL observer factory."""
    if engine.dialect.name == "sqlite":
        ModelBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    s = factory()
    profile = ApplicantProfileIn(
        context=ApplicationContext(
            level="bachelor",
            intended_fields=["computer science"],
            intake_term="fall",
            intake_year=2027,
            citizenship="Example",
            country_of_residence="Example",
            education_country="Example",
            education_system="secondary",
        )
    )
    settings = Settings(
        _env_file=None,
        database_url=str(engine.url),
        demo_mode=False,
        enable_browser_tier=False,
        cache_dir=root / "cache",
        export_dir=root / "exports",
        fetch_delay_seconds=0,
        respect_robots=False,
        candidate_limit=2,
        verify_limit=2,
    )
    org = Organization(name="Synthetic readguard test", slug="synthetic-readguard")
    s.add(org)
    s.flush()
    row = ApplicantProfileRow(organization_id=org.id, payload=profile.model_dump(mode="json"))
    s.add(row)
    s.flush()
    run = ResearchRun(
        profile_id=row.id,
        demo_mode=False,
        stage="queued",
        stage_state=RunState.load(None).dump(),
        candidate_limit=2,
        verify_limit=2,
    )
    s.add(run)
    s.flush()
    run_id = run.id
    enqueue = JobStore(s).enqueue(
        "research", run_id=run_id, idempotency_key="test-research:" + run_id
    )
    s.commit()
    with factory() as claim_session:
        store = JobStore(claim_session, worker_id="worker-one")
        job = store.claim(worker_id="worker-one")
        assert (
            enqueue.created and job is not None and job.id == enqueue.job_id and job.attempts == 1
        )
        claim_session.commit()
    job = s.get(Job, enqueue.job_id)
    runner = ResearchRunner(
        s, run, profile, settings, job_id=job.id, worker_id="worker-one", lease_token=1
    )
    queries = []
    sql_errors = []

    def before(conn, cursor, statement, params, sqlctx, executemany):
        sqlctx._readguard_test_started = time.monotonic_ns()
        queries.append(
            {
                "at_ns": sqlctx._readguard_test_started,
                "thread": threading.get_ident(),
                "sql": statement,
                "params": repr(params)[:1500],
            }
        )

    def after(conn, cursor, statement, params, sqlctx, executemany):
        queries.append(
            {
                "elapsed_ns": time.monotonic_ns()
                - getattr(sqlctx, "_readguard_test_started", time.monotonic_ns()),
                "sql_prefix": statement[:100],
            }
        )

    def error(excctx):
        sql_errors.append(
            {
                "sqlstate": getattr(excctx.original_exception, "sqlstate", None),
                "sqlite_errorcode": getattr(excctx.original_exception, "sqlite_errorcode", None),
                "type": type(excctx.original_exception).__name__,
                "statement": excctx.statement,
            }
        )

    event.listen(engine, "before_cursor_execute", before)
    event.listen(engine, "after_cursor_execute", after)
    event.listen(engine, "handle_error", error)
    evidence = root / "readguard-evidence"
    evidence.mkdir(exist_ok=True)

    def record(name, value):
        (evidence / (name + ".json")).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n"
        )

    ctx = SimpleNamespace(
        engine=engine,
        factory=factory,
        session=s,
        run=run,
        job=job,
        run_id=run.id,
        job_id=job.id,
        runner=runner,
        profile=profile,
        settings=settings,
        root=root,
        queries=queries,
        sql_errors=sql_errors,
        backend=engine.dialect.name,
        record=record,
    )
    try:
        yield ctx
    finally:
        s.rollback()
        s.close()
        record("sql", {"queries": queries, "sql_errors": sql_errors})
        event.remove(engine, "before_cursor_execute", before)
        event.remove(engine, "after_cursor_execute", after)
        event.remove(engine, "handle_error", error)


@contextmanager
def sqlite_context(tmp_path, monkeypatch):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", True)
    engine = create_engine("sqlite:///" + str(tmp_path / "state.db"))
    try:
        with make_context(engine, tmp_path) as ctx:
            yield ctx
    finally:
        engine.dispose()


def activate(ctx):
    ctx.runner._read_guard_enabled = True
    ctx.runner._read_episode_fresh = ctx.run.started_at is None
    ctx.run.started_at = datetime.now(UTC)
    ctx.run.stage = PipelineStage.CANDIDATE_DISCOVERY.value
    return ctx.runner._make_fetcher()


def candidate(identity="u-one", *, name="Test University", country="Example"):
    result = Candidate(
        name=name,
        country=country,
        city="City",
        domain="example.edu",
        catalogue_id=identity,
        programs=[
            CandidateProgram(
                "BSc Computer Science",
                "computer science",
                DegreeLevel.BACHELOR,
                "https://example.edu/degree",
            )
        ],
    )
    return result


def counts(ctx):
    saved = snapshot(ctx)
    return deepcopy(
        saved.get(read_budget.LEDGER_KEY, {})
        .get("episodes", {})
        .get("decision:" + ctx.job_id, {})
        .get("read_counts", {})
    )


def mock_original_get(monkeypatch, ctx, *, outcome="ok", callback=None):
    seen = []

    async def original_get(fetcher, url, **kwargs):
        # This is inside the real Fetcher.get: durable charge must already be visible.
        visible = counts(ctx)
        seen.append({"url": url, "kwargs": kwargs, "durable": visible})
        if callback:
            callback(len(seen))
        from app.domain.enums import FetchOutcome

        return FetchResult(
            url=url,
            outcome=FetchOutcome(outcome),
            status_code=200 if outcome in {"ok", "cached"} else None,
            from_cache=outcome == "cached",
            text="<html><main><p>Official synthetic page.</p></main></html>",
        )

    monkeypatch.setattr(Fetcher, "_get", original_get)
    return seen


def program_claim(value="BSc Computer Science", kind=ClaimType.PROGRAM_EXISTS):
    return Claim(
        claim_type=kind,
        normalized_value={"program": value, "degree": "bachelor", "language": None},
        original_text_excerpt=value,
        source_url="https://example.edu/degree",
        accessed_at=datetime.now(UTC),
        status=ClaimStatus.VERIFIED_CURRENT,
        official_domain=True,
        program="BSc Computer Science",
    )


def error_chain(exc):
    result = []
    while exc is not None and len(result) < 5:
        result.append(
            {
                "type": type(exc).__name__,
                "reason": getattr(exc, "reason", None),
                "sqlstate": getattr(getattr(exc, "orig", exc), "sqlstate", None),
                "sqlite_errorcode": getattr(getattr(exc, "orig", exc), "sqlite_errorcode", None),
                "message": str(exc)[:1200],
            }
        )
        exc = exc.__cause__
    return result


def snapshot(c):
    with c.factory() as s:
        return deepcopy(
            s.execute(
                select(ResearchRun.settings_snapshot).where(ResearchRun.id == c.run_id)
            ).scalar_one()
        )


def original_mock(monkeypatch, c, callback=None):
    seen = []
    lock = threading.Lock()

    async def get(fetcher, url, **kwargs):
        entry = {
            "url": url,
            "kwargs": kwargs,
            "durable": counts(c),
            "thread": threading.get_ident(),
            "at_ns": time.monotonic_ns(),
        }
        with lock:
            seen.append(entry)
        if callback:
            callback(entry)
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            from_cache=True,
            text="Official synthetic BSc Computer Science page.",
        )

    monkeypatch.setattr(Fetcher, "_get", get)
    return seen


def new_runner(c, s, worker="worker-one", token=1):
    run = s.get(ResearchRun, c.run_id)
    runner = ResearchRunner(
        s, run, c.profile, c.settings, job_id=c.job_id, worker_id=worker, lease_token=token
    )
    runner._read_guard_enabled = True
    return runner


def lock_row(c, s, row):
    model = Job if row == "job" else ResearchRun
    ident = c.job_id if row == "job" else c.run_id
    s.execute(select(model.id).where(model.id == ident).with_for_update())


def claim_fact():
    return Claim(
        claim_type=ClaimType.PROGRAM_EXISTS,
        normalized_value={
            "program": "BSc Computer Science",
            "degree": "bachelor",
            "language": None,
        },
        original_text_excerpt="Previous completed official evidence",
        source_url="https://example.edu/degree",
        accessed_at=datetime.now(UTC),
        status=ClaimStatus.VERIFIED_CURRENT,
        official_domain=True,
        program="BSc Computer Science",
    )


def seed_prior(c):
    cand = candidate()
    value = ProgramResult(
        id="pg-prior-result",
        run_id=c.run_id,
        university=cand.name,
        university_id="prior-key",
        country=cand.country,
        city=cand.city,
        program=cand.programs[0].name,
        program_url=cand.programs[0].url,
        degree=DegreeLevel.BACHELOR,
        intake="fall 2027",
    )
    fact = claim_fact()
    value.claims = [_to_out(fact, "pg-prior-claim")]
    c.runner._persist_result(value, [fact], [])
    c.runner._save()
    return prior(c)


def prior(c):
    with c.factory() as s:
        return {
            "claims": [deepcopy(x.payload) for x in s.query(ClaimRow).all()],
            "results": [deepcopy(x.payload) for x in s.query(ProgramResultRow).all()],
        }

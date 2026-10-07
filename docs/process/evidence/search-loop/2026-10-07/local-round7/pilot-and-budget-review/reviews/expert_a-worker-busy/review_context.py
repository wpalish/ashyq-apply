"""Independent actual-PG controls; no repository writes or real Fetcher transport."""
from __future__ import annotations
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
from types import SimpleNamespace
import uuid

BASE = Path(__file__).resolve().parent
PIN = BASE / 'candidate-pinned'
sys.path.insert(0, str(PIN))
import shadow_import
shadow_import.install()

import pytest
from sqlalchemy import create_engine, event, select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher, FetchResult
from app.config import Settings
from app.domain.enums import ClaimStatus, ClaimType, DegreeLevel, FetchOutcome, PipelineStage
from app.jobs.store import JobStore
from app.models import ApplicantProfileRow, AuditEvent, Base as ModelBase, ClaimRow, Job, Organization, ProgramResultRow, ResearchRun
from app.models.jobs import JobStatus
from app.pipeline import read_budget
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from app.pipeline.runner import ResearchRunner, _to_out
from app.pipeline.state import RunState
from app.schemas.claim import Claim
from app.schemas.profile import ApplicantProfileIn, ApplicationContext
from app.schemas.result import ProgramResult

MODE = os.environ['WORKER_REVIEW_TARGET']
RAW = BASE / 'raw' / MODE
WRITE_LOCK = threading.Lock()


def raw(name, value):
    with WRITE_LOCK:
        (RAW / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


def error_chain(exc):
    result = []
    while exc is not None and len(result) < 5:
        result.append({'type': type(exc).__name__, 'reason': getattr(exc, 'reason', None), 'sqlstate': getattr(getattr(exc, 'orig', exc), 'sqlstate', None), 'sqlite_errorcode':getattr(getattr(exc,'orig',exc),'sqlite_errorcode',None), 'message': str(exc)[:1200]})
        exc = exc.__cause__
    return result


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Real network/provider/HTTP forbidden in independent PG review')
    # PostgreSQL uses libpq AF_UNIX, not Python socket; allow no Python transports.
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)
    monkeypatch.setattr(read_budget, 'UNIVERSITY_READ_BUDGET', True)
    from app.adapters import search
    from app.catalogue import discovery
    monkeypatch.setattr(search, 'get_search_provider', deny)
    monkeypatch.setattr(discovery, 'get_search_provider', deny)
    import httpx
    monkeypatch.setattr(httpx.AsyncClient, 'send', deny)
    monkeypatch.setattr(httpx.Client, 'send', deny)


@pytest.fixture(params=['postgresql','sqlite'])
def ctx(request, tmp_path):
    uri = os.environ['UNIMATCH_DATABASE_URL']
    assert uri.startswith('postgresql+psycopg://') and '?host=' in uri
    backend = request.param
    schema = 'rga_' + uuid.uuid4().hex if backend=='postgresql' else None
    admin = None
    if backend=='postgresql':
        admin = create_engine(uri, isolation_level='AUTOCOMMIT')
        with admin.connect() as conn: conn.exec_driver_sql('CREATE SCHEMA ' + schema)
        engine = create_engine(uri,pool_size=8,max_overflow=5,connect_args={'options':'-csearch_path='+schema+' -cstatement_timeout=1500'})
    else:
        engine = create_engine('sqlite:///'+str(tmp_path/'synthetic-state.db'),connect_args={'timeout':0})
    queries = []
    sql_errors = []
    def before(conn, cursor, statement, params, context, executemany):
        context._review_started = time.monotonic_ns()
        queries.append({'at_ns': context._review_started, 'thread': threading.get_ident(), 'sql': statement, 'params': repr(params)[:1500]})
    def after(conn, cursor, statement, params, context, executemany):
        queries.append({'finished_ns': time.monotonic_ns(), 'elapsed_ns': time.monotonic_ns() - getattr(context, '_review_started', time.monotonic_ns()), 'sql_prefix': statement[:100]})
    def handle(exception_context):
        sql_errors.append({'at_ns': time.monotonic_ns(), 'sqlstate': getattr(exception_context.original_exception, 'sqlstate', None), 'type': type(exception_context.original_exception).__name__, 'statement': exception_context.statement, 'sqlite_errorcode':getattr(exception_context.original_exception,'sqlite_errorcode',None)})
    event.listen(engine, 'before_cursor_execute', before)
    event.listen(engine, 'after_cursor_execute', after)
    event.listen(engine, 'handle_error', handle)
    ModelBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    profile = ApplicantProfileIn(context=ApplicationContext(level='bachelor', intended_fields=['computer science'], intake_term='fall', intake_year=2027, citizenship='Example', country_of_residence='Example', education_country='Example', education_system='secondary'))
    settings = Settings(_env_file=None, demo_mode=False, enable_browser_tier=False, cache_dir=tmp_path/'cache', fetch_delay_seconds=0, respect_robots=False, candidate_limit=2, verify_limit=2)
    org = Organization(name='Independent PG synthetic', slug='pg-' + uuid.uuid4().hex)
    session.add(org); session.flush()
    profile_row = ApplicantProfileRow(organization_id=org.id, payload=profile.model_dump(mode='json'))
    session.add(profile_row); session.flush()
    run = ResearchRun(profile_id=profile_row.id, demo_mode=False, stage='queued', stage_state=RunState.load(None).dump(), candidate_limit=2, verify_limit=2)
    session.add(run); session.flush()
    job = Job(kind='research', run_id=run.id, status='running', attempts=1, worker_id='worker-one', available_at=datetime.now(UTC), lease_expires_at=datetime.now(UTC)+timedelta(minutes=5))
    session.add(job); session.commit()
    runner = ResearchRunner(session, run, profile, settings, job_id=job.id, worker_id='worker-one', lease_token=1)
    result = SimpleNamespace(engine=engine, factory=factory, session=session, profile=profile, settings=settings, run=run, job=job, run_id=run.id, job_id=job.id, runner=runner, queries=queries, sql_errors=sql_errors, backend=backend)
    try:
        yield result
    finally:
        session.rollback(); session.close()
        raw(request.node.name + '-sql', {'schema': schema, 'queries': queries, 'sql_errors': sql_errors})
        engine.dispose()
        if admin is not None:
            with admin.connect() as conn: conn.exec_driver_sql('DROP SCHEMA ' + schema + ' CASCADE')
            admin.dispose()


def candidate(key='u-one'):
    return Candidate(name='Independent Test University', country='Example', city='City', domain='example.edu', programs=[CandidateProgram('BSc Computer Science', 'computer science', DegreeLevel.BACHELOR, 'https://example.edu/degree')], catalogue_id=key)


def activate(c):
    c.runner._read_guard_enabled = True
    c.run.started_at = c.run.started_at or datetime.now(UTC)
    c.run.stage = PipelineStage.CANDIDATE_DISCOVERY.value
    return c.runner._make_fetcher()


def snapshot(c):
    with c.factory() as s:
        return deepcopy(s.execute(select(ResearchRun.settings_snapshot).where(ResearchRun.id == c.run_id)).scalar_one())


def counts(c):
    data = snapshot(c)
    ledger = data.get(read_budget.LEDGER_KEY, {})
    return ledger.get('episodes', {}).get('decision:' + c.job_id, {}).get('read_counts', {})


def original_mock(monkeypatch, c, callback=None):
    seen = []
    lock = threading.Lock()
    async def get(fetcher, url, **kwargs):
        entry = {'url': url, 'kwargs': kwargs, 'durable': counts(c), 'thread': threading.get_ident(), 'at_ns': time.monotonic_ns()}
        with lock:
            seen.append(entry)
        if callback:
            callback(entry)
        return FetchResult(url=url, outcome=FetchOutcome.OK, status_code=200, from_cache=True, text='Official synthetic BSc Computer Science page.')
    monkeypatch.setattr(Fetcher, '_get', get)
    return seen


def new_runner(c, s, worker='worker-one', token=1):
    run = s.get(ResearchRun, c.run_id)
    runner = ResearchRunner(s, run, c.profile, c.settings, job_id=c.job_id, worker_id=worker, lease_token=token)
    runner._read_guard_enabled = True
    return runner


def lock_row(c, s, row):
    model = Job if row == 'job' else ResearchRun
    ident = c.job_id if row == 'job' else c.run_id
    s.execute(select(model.id).where(model.id == ident).with_for_update())


def claim_fact():
    return Claim(claim_type=ClaimType.PROGRAM_EXISTS, normalized_value={'program':'BSc Computer Science','degree':'bachelor','language':None}, original_text_excerpt='Previous completed official evidence', source_url='https://example.edu/degree', accessed_at=datetime.now(UTC), status=ClaimStatus.VERIFIED_CURRENT, official_domain=True, program='BSc Computer Science')


def seed_prior(c):
    cand = candidate()
    value = ProgramResult(id='pg-prior-result', run_id=c.run_id, university=cand.name, university_id='prior-key', country=cand.country, city=cand.city, program=cand.programs[0].name, program_url=cand.programs[0].url, degree=DegreeLevel.BACHELOR, intake='fall 2027')
    fact = claim_fact()
    value.claims = [_to_out(fact, 'pg-prior-claim')]
    c.runner._persist_result(value, [fact], [])
    c.runner._save()
    return prior(c)


def prior(c):
    with c.factory() as s:
        return {'claims': [deepcopy(x.payload) for x in s.query(ClaimRow).all()], 'results': [deepcopy(x.payload) for x in s.query(ProgramResultRow).all()]}



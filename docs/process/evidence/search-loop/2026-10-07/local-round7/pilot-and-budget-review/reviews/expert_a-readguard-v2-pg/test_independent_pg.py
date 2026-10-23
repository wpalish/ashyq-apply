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

RAW = BASE / 'raw'
WRITE_LOCK = threading.Lock()


def raw(name, value):
    with WRITE_LOCK:
        (RAW / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


def error_chain(exc):
    result = []
    while exc is not None and len(result) < 5:
        result.append({'type': type(exc).__name__, 'reason': getattr(exc, 'reason', None), 'sqlstate': getattr(getattr(exc, 'orig', exc), 'sqlstate', None), 'message': str(exc)[:1200]})
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


@pytest.fixture
def ctx(request, tmp_path):
    uri = os.environ['UNIMATCH_DATABASE_URL']
    assert uri.startswith('postgresql+psycopg://') and '?host=' in uri
    schema = 'rga_' + uuid.uuid4().hex
    admin = create_engine(uri, isolation_level='AUTOCOMMIT')
    with admin.connect() as conn:
        conn.exec_driver_sql('CREATE SCHEMA ' + schema)
    engine = create_engine(uri, pool_size=8, max_overflow=5, connect_args={'options': '-csearch_path=' + schema + ' -cstatement_timeout=5000'})
    queries = []
    sql_errors = []
    def before(conn, cursor, statement, params, context, executemany):
        context._review_started = time.monotonic_ns()
        queries.append({'at_ns': context._review_started, 'thread': threading.get_ident(), 'sql': statement, 'params': repr(params)[:1500]})
    def after(conn, cursor, statement, params, context, executemany):
        queries.append({'finished_ns': time.monotonic_ns(), 'elapsed_ns': time.monotonic_ns() - getattr(context, '_review_started', time.monotonic_ns()), 'sql_prefix': statement[:100]})
    def handle(exception_context):
        sql_errors.append({'at_ns': time.monotonic_ns(), 'sqlstate': getattr(exception_context.original_exception, 'sqlstate', None), 'type': type(exception_context.original_exception).__name__, 'statement': exception_context.statement})
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
    result = SimpleNamespace(engine=engine, factory=factory, session=session, profile=profile, settings=settings, run=run, job=job, run_id=run.id, job_id=job.id, runner=runner, queries=queries, sql_errors=sql_errors)
    try:
        yield result
    finally:
        session.rollback(); session.close()
        raw(request.node.name + '-sql', {'schema': schema, 'queries': queries, 'sql_errors': sql_errors})
        engine.dispose()
        with admin.connect() as conn:
            conn.exec_driver_sql('DROP SCHEMA ' + schema + ' CASCADE')
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


def test_pg_00_real_isolated_runtime_and_independent_sessions(ctx):
    with ctx.factory() as a, ctx.factory() as b:
        first = a.execute(text('SELECT pg_backend_pid(), current_schema(), current_setting(\'server_version\'), current_setting(\'listen_addresses\')')).one()
        second = b.execute(text('SELECT pg_backend_pid()')).scalar_one()
        assert first[0] != second and ctx.engine.dialect.name == 'postgresql'
        assert first[1].startswith('rga_') and first[3] == ''
        raw('PG-00', {'backend_pids': [first[0], second], 'schema': first[1], 'server_version': first[2], 'listen_addresses': first[3], 'original_io': 0})


@pytest.mark.parametrize('row', ['job', 'run'])
def test_pg_01_02_actual_nowait_lock_order_and_rollback(ctx, monkeypatch, row):
    fetcher = activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    before = snapshot(ctx)
    with ctx.factory() as blocker:
        lock_row(ctx, blocker, row)
        start = time.monotonic_ns()
        with pytest.raises(UniversityReadStopped) as info:
            with ctx.runner._university_read_scope(candidate()):
                asyncio.run(fetcher.get('https://example.edu/denied'))
        end = time.monotonic_ns()
        assert info.value.reason == 'checkpoint_busy'
        assert info.value.__cause__.orig.sqlstate == '55P03'
        assert not ctx.session.in_transaction()
        assert seen == [] and snapshot(ctx) == before
        if row == 'run':
            with ctx.factory() as observer:
                observer.execute(select(Job.id).where(Job.id == ctx.job_id).with_for_update(nowait=True))
        blocker.rollback()
    lock_sql = [q['sql'] for q in ctx.queries if 'sql' in q and 'FOR UPDATE NOWAIT' in q['sql']]
    assert 'jobs' in lock_sql[0]
    if row == 'run':
        assert 'research_runs' in lock_sql[1]
    raw('PG-01' if row == 'job' else 'PG-02', {'exception': error_chain(info.value), 'caller_elapsed_ns': end-start, 'lock_sql': lock_sql, 'original_get': len(seen), 'counter_before_after': [before, snapshot(ctx)], 'job_lock_released': row == 'run'})


def test_pg_03_exact_80_attempts_60_committed_admissions_two_pg_sessions(ctx, monkeypatch):
    f = activate(ctx)
    seen = original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(candidate()):
        pass
    cv = threading.Condition()
    turn = {'next': 0}
    outcomes = []
    pids = []
    errors = []
    def thread_work(index):
        try:
            with ctx.factory() as s:
                pids.append(s.execute(text('SELECT pg_backend_pid()')).scalar_one()); s.commit()
                r = new_runner(ctx, s); fetcher = r._make_fetcher()
                for i in range(40):
                    ordinal = 2*i + index
                    with cv:
                        ok = cv.wait_for(lambda: turn['next'] == ordinal, timeout=10)
                        assert ok, ('round_robin_timeout', ordinal)
                        try:
                            with r._university_read_scope(candidate()):
                                asyncio.run(fetcher.get(f'https://example.edu/program-{index}/{i}', use_cache=True))
                            outcomes.append({'ordinal': ordinal, 'status': 'admitted'})
                        except UniversityReadStopped as exc:
                            outcomes.append({'ordinal': ordinal, 'status': exc.reason})
                        finally:
                            turn['next'] += 1; cv.notify_all()
        except BaseException as exc:
            errors.append(error_chain(exc))
    ts = [threading.Thread(target=thread_work, args=(i,)) for i in range(2)]
    for t in ts: t.start()
    for t in ts: t.join(15); assert not t.is_alive()
    raw('PG-03', {'attempts':len(outcomes),'original_get':len(seen),'outcomes':outcomes,'seen':seen,'durable':counts(ctx),'backend_pids':pids,'errors':errors,'coordination':'round-robin attempt start, no retry'})
    assert not errors and len(set(pids)) == 2
    assert len(outcomes) == 80 and len(seen) == 60
    assert sum(x['status']=='read_cap' for x in outcomes)==20
    assert [x['durable']['catalogue:u-one'] for x in seen] == list(range(1,61))
    assert counts(ctx) == {'catalogue:u-one':60}


def test_pg_04_simultaneous_nowait_and_cap_saturation_no_hidden_retry(ctx, monkeypatch):
    f = activate(ctx); seen = original_mock(monkeypatch, ctx)
    with ctx.runner._university_read_scope(candidate()):
        for i in range(59): asyncio.run(f.get(f'https://example.edu/prior/{i}'))
    holding = threading.Event(); release = threading.Event(); first_errors = []
    def first():
        try:
            with ctx.factory() as s:
                r = new_runner(ctx,s); fetcher=r._make_fetcher(); original=r._lock_read_checkpoint_job
                def hold():
                    original(); holding.set(); assert release.wait(5)
                r._lock_read_checkpoint_job=hold
                with r._university_read_scope(candidate()): asyncio.run(fetcher.get('https://example.edu/last'))
        except BaseException as exc: first_errors.append(error_chain(exc))
    thread = threading.Thread(target=first); thread.start(); assert holding.wait(5)
    with ctx.factory() as s:
        r=new_runner(ctx,s); ff=r._make_fetcher()
        with pytest.raises(UniversityReadStopped) as info:
            with r._university_read_scope(candidate()): asyncio.run(ff.get('https://example.edu/racing-denied'))
        assert info.value.reason=='checkpoint_busy' and info.value.__cause__.orig.sqlstate=='55P03'
    release.set(); thread.join(5); assert not thread.is_alive() and not first_errors
    with pytest.raises(UniversityReadStopped, match='read_cap'):
        with ctx.runner._university_read_scope(candidate()): asyncio.run(f.get('https://example.edu/61'))
    statuses=[]; errors=[]; ready=threading.Barrier(2)
    def race(index):
        try:
            with ctx.factory() as s:
                r=new_runner(ctx,s); ff=r._make_fetcher(); ready.wait(5)
                for i in range(40):
                    try:
                        with r._university_read_scope(candidate('concurrent')): asyncio.run(ff.get(f'https://example.edu/race-{index}/{i}'))
                        statuses.append('admitted')
                    except UniversityReadStopped as exc: statuses.append(exc.reason)
        except BaseException as exc: errors.append(error_chain(exc))
    ts=[threading.Thread(target=race,args=(i,)) for i in range(2)]
    for t in ts:t.start()
    for t in ts:t.join(15);assert not t.is_alive()
    raw('PG-04', {'saturation_prior_gets':59,'racing_refusal':error_chain(info.value),'saturation_count':counts(ctx).get('catalogue:u-one'),'concurrent_attempts':len(statuses),'concurrent_outcomes':{x:statuses.count(x) for x in set(statuses)},'concurrent_admitted_original':sum('/race-' in x['url'] for x in seen),'durable':counts(ctx),'errors':errors,'retry':False})
    assert not errors and len(statuses)==80
    n=sum('/race-' in x['url'] for x in seen)
    assert n==statuses.count('admitted') and n<=60
    assert counts(ctx)['catalogue:concurrent']==n and counts(ctx)['catalogue:u-one']==60


@pytest.mark.parametrize('new_worker',['worker-two','worker-one'])
def test_pg_05_real_reap_claim_fresh_attempt_fence(ctx,monkeypatch,new_worker):
    f=activate(ctx);seen=original_mock(monkeypatch,ctx)
    with ctx.runner._university_read_scope(candidate()):asyncio.run(f.get('https://example.edu/before-reap'))
    now=datetime.now(UTC)
    with ctx.factory() as other:
        other.execute(update(Job).where(Job.id==ctx.job_id).values(lease_expires_at=now-timedelta(seconds=1)));other.commit()
        store=JobStore(other,worker_id=new_worker)
        assert store.reap_expired(now=now)==[ctx.job_id]
        other.execute(update(Job).where(Job.id==ctx.job_id).values(available_at=now-timedelta(seconds=1)));other.commit()
        claimed=store.claim(worker_id=new_worker); assert claimed.id==ctx.job_id and claimed.attempts==2;other.commit()
    with pytest.raises(LeaseLost):
        with ctx.runner._university_read_scope(candidate()):asyncio.run(f.get('https://example.edu/stale'))
    assert len(seen)==1 and counts(ctx)['catalogue:u-one']==1
    with ctx.factory() as current:
        r=new_runner(ctx,current,new_worker,2)
        monkeypatch.setattr(read_budget,'UNIVERSITY_READ_BUDGET',False)
        assert r._effective_read_guard() is True
        with r._university_read_scope(candidate()):asyncio.run(r._make_fetcher().get('https://example.edu/reclaimed'))
    raw('PG-05-'+new_worker,{'original_get':len(seen),'durable':counts(ctx),'new_worker':new_worker,'new_attempt':2,'stale_denied':True,'recorded_on_source_false':True,'expiry_alone_claim':False})
    assert len(seen)==2 and counts(ctx)['catalogue:u-one']==2


@pytest.mark.parametrize('kind',['user','coroutine'])
def test_pg_06_committed_user_cancel_and_post_charge_async_cancel(ctx,monkeypatch,kind):
    f=activate(ctx);seen=original_mock(monkeypatch,ctx)
    with ctx.runner._university_read_scope(candidate()):
        if kind=='user':
            asyncio.run(f.get('https://example.edu/before-cancel'))
            with ctx.factory() as cancel:
                assert JobStore(cancel).cancel(ctx.job_id);cancel.commit()
            with pytest.raises(RunCancelled):asyncio.run(f.get('https://example.edu/after-cancel'))
            assert len(seen)==1
        else:
            async def entered(fetcher,url,**kwargs):
                assert counts(ctx)['catalogue:u-one']==1
                raise asyncio.CancelledError('independent cancellation after committed charge')
            monkeypatch.setattr(Fetcher,'_get',entered)
            with pytest.raises(asyncio.CancelledError):asyncio.run(f.get('https://example.edu/coroutine-cancel'))
    raw('PG-06-'+kind,{'durable':counts(ctx),'original_mock_completed':len(seen),'post_charge_no_refund':kind=='coroutine','pages_failed':ctx.run.pages_failed})
    assert counts(ctx)['catalogue:u-one']==1 and ctx.run.pages_failed==0


def test_pg_07_first_namespace_dirty_off_save_serializes_and_preserves_60(ctx,monkeypatch):
    f=activate(ctx);seen=original_mock(monkeypatch,ctx);interleaved=[]
    with ctx.factory() as off_s:
        off_run=off_s.get(ResearchRun,ctx.run_id)
        off=ResearchRunner(off_s,off_run,ctx.profile,ctx.settings,job_id=ctx.job_id,worker_id='worker-one',lease_token=1)
        off_run.settings_snapshot={'off_writer':'first dirty replacement'}
        actual=off_s.execute
        def intercept(statement,*args,**kwargs):
            result=actual(statement,*args,**kwargs)
            if not interleaved and getattr(statement,'is_select',False) and any(getattr(d.get('expr'),'key',None)=='settings_snapshot' for d in getattr(statement,'column_descriptions',[])):
                value=result.scalar_one()
                with pytest.raises(UniversityReadStopped) as info:
                    with ctx.runner._university_read_scope(candidate()):asyncio.run(f.get('https://example.edu/interleaved'))
                interleaved.append(error_chain(info.value));assert info.value.reason=='checkpoint_busy'
                return SimpleNamespace(scalar_one=lambda:value)
            return result
        monkeypatch.setattr(off_s,'execute',intercept)
        off._save();monkeypatch.setattr(off_s,'execute',actual)
        assert seen==[]
        f=activate(ctx)
        with ctx.runner._university_read_scope(candidate()):
            for i in range(60):asyncio.run(f.get(f'https://example.edu/allowed/{i}'))
        saved_ledger=deepcopy(snapshot(ctx)[read_budget.LEDGER_KEY])
        off_run.settings_snapshot={'off_writer':'second stale replacement'};off._save()
        assert snapshot(ctx)[read_budget.LEDGER_KEY]==saved_ledger
        with pytest.raises(UniversityReadStopped,match='read_cap'):
            with ctx.runner._university_read_scope(candidate()):asyncio.run(f.get('https://example.edu/61'))
    raw('PG-07',{'first_on_refused':interleaved,'original_get':len(seen),'durable':snapshot(ctx),'fresh_namespace_not_erased':True,'scope':'dirty/pending checkpoint writer; not universal OFF I/O cap'})
    assert len(seen)==60 and counts(ctx)['catalogue:u-one']==60


@pytest.mark.parametrize('row',['job','run'])
@pytest.mark.parametrize('entry',['stage_verify','run_to_decision'])
def test_pg_08_busy_actual_caller_preserves_completed_facts(ctx,monkeypatch,row,entry):
    from app.pipeline import runner as rm
    f=activate(ctx)
    with ctx.runner._university_read_scope(candidate()):pass
    old=seed_prior(ctx);before=snapshot(ctx);seen=original_mock(monkeypatch,ctx)
    ctx.runner._candidates=[candidate()]
    real=rm.WebRequirementsAdapter
    with ctx.factory() as blocker:
        def requirements(*args,**kwargs):
            value=real(*args,**kwargs);lock_row(ctx,blocker,row);return value
        monkeypatch.setattr(rm,'WebRequirementsAdapter',requirements)
        if entry=='run_to_decision':
            ctx.runner.state[PipelineStage.PROFILE_VALIDATION].status='done'
            async def discovered(fetcher):ctx.runner._candidates=[candidate()]
            monkeypatch.setattr(ctx.runner,'_stage_discover',discovered)
        start=time.monotonic_ns()
        with pytest.raises(UniversityReadStopped) as info:
            asyncio.run(ctx.runner._stage_verify(f) if entry=='stage_verify' else ctx.runner.run_to_decision())
        elapsed=time.monotonic_ns()-start
        assert info.value.reason=='checkpoint_busy' and info.value.__cause__.orig.sqlstate=='55P03'
        assert not ctx.session.in_transaction() and seen==[]
        blocker.rollback()
    after=prior(ctx)
    with ctx.factory() as observer:
        persisted=observer.get(ResearchRun,ctx.run_id)
        details={'stage':persisted.stage,'unknowns':persisted.unknowns,'errors':persisted.errors,'run_failed_audits':observer.query(AuditEvent).filter(AuditEvent.action=='run_failed').count()}
    raw('PG-08-'+row+'-'+entry,{'exception':error_chain(info.value),'caller_elapsed_ns':elapsed,'original_get':len(seen),'prior_before':old,'prior_after':after,'ledger_before':before[read_budget.LEDGER_KEY],'ledger_after':snapshot(ctx)[read_budget.LEDGER_KEY],'run':details,'durable_busy_unknown_promised':False})
    assert after==old and snapshot(ctx)[read_budget.LEDGER_KEY]==before[read_budget.LEDGER_KEY]
    assert details['stage']!=PipelineStage.FAILED.value and details['run_failed_audits']==0
    assert not any('checkpoint_busy' in x for x in details['unknowns'] or [])


@pytest.mark.parametrize('row',['run','job'])
def test_pg_09_actual_worker_boundary_retry_vs_locked_job_limitation(ctx,monkeypatch,row):
    from app.jobs import worker as wm
    from app.pipeline import runner as rm
    f=activate(ctx)
    with ctx.runner._university_read_scope(candidate()):pass
    old=seed_prior(ctx);seen=original_mock(monkeypatch,ctx)
    @contextmanager
    def owned_scope():
        s=ctx.factory()
        try:yield s;s.commit()
        except BaseException:s.rollback();raise
        finally:s.close()
    monkeypatch.setattr(wm,'session_scope',owned_scope)
    worker=wm.Worker(ctx.settings,worker_id='worker-one')
    async def no_background_heartbeat(*args,**kwargs):return None
    monkeypatch.setattr(worker,'_beat',no_background_heartbeat)
    real=rm.WebRequirementsAdapter
    with ctx.factory() as blocker:
        def requirements(*args,**kwargs):
            value=real(*args,**kwargs);lock_row(ctx,blocker,row);return value
        monkeypatch.setattr(rm,'WebRequirementsAdapter',requirements)
        async def dispatch(s,store,job,*,lease_token):
            r=new_runner(ctx,s,'worker-one',lease_token);r._candidates=[candidate()]
            await r._stage_verify(r._make_fetcher())
        monkeypatch.setattr(worker,'_dispatch',dispatch)
        escaped=None;start=time.monotonic_ns()
        try:asyncio.run(worker.execute(ctx.job_id))
        except BaseException as exc:escaped=exc
        elapsed=time.monotonic_ns()-start
        assert seen==[]
        blocker.rollback()
    with ctx.factory() as s:
        job=s.get(Job,ctx.job_id);run=s.get(ResearchRun,ctx.run_id)
        durable={'job_status':job.status,'job_last_error':job.last_error,'run_stage':run.stage,'run_unknowns':run.unknowns,'worker_jobs_failed':worker.jobs_failed}
    raw('PG-09-'+row,{'escaped':error_chain(escaped) if escaped else [],'caller_elapsed_ns':elapsed,'original_get':len(seen),'prior_before':old,'prior_after':prior(ctx),'durable':durable,'classification':'known-unresolved worker fail persistence when Job remains locked' if row=='job' else 'worker retry write possible when only Run remains locked'})
    assert prior(ctx)==old and durable['run_stage']!=PipelineStage.FAILED.value
    if row=='run':
        assert escaped is None and durable['job_status']=='queued' and 'checkpoint_busy' in durable['job_last_error']
    else:
        assert isinstance(escaped,OperationalError) and escaped.orig.sqlstate=='57014'
        assert durable['job_status']=='running'
        # Preserve a real red for the broad prepared worker-control target.
        # Candidate explicitly excludes guaranteed retry write under this lock.
        assert isinstance(escaped,UniversityReadStopped), 'PG-09 planned typed worker boundary fails: Worker.fail waits on still-locked Job and releases 57014; documented v2 limitation, not a READ admission bypass'


def test_pg_10_prior_dirty_run_flush_then_job_nowait_releases_opposite_order(ctx,monkeypatch):
    f=activate(ctx);seen=original_mock(monkeypatch,ctx)
    with ctx.runner._university_read_scope(candidate()):pass
    original=snapshot(ctx)
    ctx.run.pages_checked=17
    ctx.session.flush() # Actual dirty ORM Run row lock predates next guarded Job lock.
    with ctx.factory() as blocker:
        lock_row(ctx,blocker,'job')
        with pytest.raises(UniversityReadStopped) as info:
            with ctx.runner._university_read_scope(candidate()):asyncio.run(f.get('https://example.edu/opposite'))
        assert info.value.reason=='checkpoint_busy' and info.value.__cause__.orig.sqlstate=='55P03'
        with ctx.factory() as observer:
            observer.execute(select(ResearchRun.id).where(ResearchRun.id==ctx.run_id).with_for_update(nowait=True))
        blocker.rollback()
    with ctx.factory() as observer: persisted_pages=observer.get(ResearchRun,ctx.run_id).pages_checked
    raw('PG-10',{'exception':error_chain(info.value),'original_get':len(seen),'durable_ledger':snapshot(ctx),'pages_checked_after_rollback':persisted_pages,'prior_run_lock_released':True,'deadlock_freedom_claim':False})
    assert not seen and persisted_pages==0 and snapshot(ctx)==original


def test_pg_11_corrupt_envelope_and_commit_refusal_fail_closed(ctx,monkeypatch):
    f=activate(ctx);seen=original_mock(monkeypatch,ctx)
    with ctx.runner._university_read_scope(candidate()):pass
    valid=snapshot(ctx)
    with ctx.factory() as other:
        run=other.get(ResearchRun,ctx.run_id);run.settings_snapshot={read_budget.LEDGER_KEY:{'version':True}};other.commit()
    with pytest.raises(UniversityReadStopped,match='invalid_ledger'):
        with ctx.runner._university_read_scope(candidate()):asyncio.run(f.get('https://example.edu/corrupt'))
    ctx.session.rollback();assert not seen
    assert snapshot(ctx)=={read_budget.LEDGER_KEY:{'version':True}}
    with ctx.factory() as other:
        run=other.get(ResearchRun,ctx.run_id);run.settings_snapshot=deepcopy(valid);other.commit()
    with ctx.runner._university_read_scope(candidate()):
        def refuse():raise RuntimeError('independent injected pre-commit refusal')
        monkeypatch.setattr(ctx.session,'commit',refuse)
        with pytest.raises(RuntimeError,match='pre-commit refusal'):asyncio.run(f.get('https://example.edu/not-committed'))
        visible=counts(ctx)
        ctx.session.rollback()
    raw('PG-11',{'original_get':len(seen),'counter_visible_while_uncommitted':visible,'durable_after_rollback':snapshot(ctx),'explicit_rollback':True})
    assert not seen and visible=={'catalogue:u-one':0} and snapshot(ctx)==valid

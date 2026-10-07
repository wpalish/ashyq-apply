"""Own actual SQLite controls over the exact frozen proposal; no real network."""
from __future__ import annotations

import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from threading import Barrier, Lock
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'candidate-pinned'))
import test_production_readguard as controls
pytest_plugins=('test_production_readguard',)

import pytest
from app.adapters.fetching import Fetcher,FetchResult
from app.domain.enums import FetchOutcome,PipelineStage
from app.models import ClaimRow,Job,ResearchRun,ProgramResultRow
from app.pipeline import read_budget
from app.pipeline.control import LeaseLost,RunCancelled,UniversityReadStopped
from app.pipeline.runner import ResearchRunner
from sqlalchemy import event,select,update
from sqlalchemy.exc import OperationalError


def snapshot(ctx):
    with ctx.factory() as session:
        return deepcopy(session.execute(select(ResearchRun.settings_snapshot).where(ResearchRun.id==ctx.run.id)).scalar_one())


def write_raw(ctx,name,raw):
    folder=ROOT/'raw-controls';folder.mkdir(exist_ok=True)
    (folder/(name+'.json')).write_text(json.dumps(raw,indent=2)+'\n')


@pytest.mark.asyncio
@pytest.mark.parametrize('which',['worker','same_worker_attempt'])
async def test_fresh_sql_fence_stops_stale_runner_even_with_same_worker_id(context,monkeypatch,which):
    f=controls.activate(context);c=controls.candidate();seen=controls.mock_original_get(monkeypatch,context)
    with context.runner._university_read_scope(c):await f.get('https://example.edu/first')
    before=snapshot(context)
    with context.factory() as changer:
        changer.execute(update(Job).where(Job.id==context.job.id).values(**({'worker_id':'new-worker'} if which=='worker' else {'attempts':2})))
        changer.commit()
    with pytest.raises(LeaseLost),context.runner._university_read_scope(c):await f.get('https://example.edu/stale')
    assert len(seen)==1 and snapshot(context)==before
    write_raw(context,'fresh-fence-'+which,{'before':before,'after':snapshot(context),'original_get_count':len(seen),'stale_mode':which,'control':'LeaseLost','network_calls':0})


@pytest.mark.asyncio
async def test_preio_commit_failure_never_reaches_original_and_uncommitted_count_rolls_back(context,monkeypatch):
    f=controls.activate(context);c=controls.candidate();seen=controls.mock_original_get(monkeypatch,context)
    with context.runner._university_read_scope(c):pass
    before=snapshot(context);real_commit=context.session.commit
    def fail():raise RuntimeError('independent injected commit refusal')
    monkeypatch.setattr(context.session,'commit',fail)
    with pytest.raises(RuntimeError,match='independent injected'),context.runner._university_read_scope(c):await f.get('https://example.edu/not-admitted')
    assert seen==[] and snapshot(context)==before
    context.session.rollback()
    monkeypatch.setattr(context.session,'commit',real_commit)
    assert snapshot(context)==before
    write_raw(context,'commit-refusal',{'before':before,'after':snapshot(context),'original_get_count':0,'rollback_by_test_after_exception':True,'claim':'pre-commit failure forbids original IO; worker/session cleanup remains separate','network_calls':0})


@pytest.mark.asyncio
async def test_post_admission_async_cancel_does_not_refund_committed_charge(context,monkeypatch):
    f=controls.activate(context);c=controls.candidate();seen=[]
    async def original(fetcher,url,**kwargs):
        seen.append(snapshot(context));raise asyncio.CancelledError()
    monkeypatch.setattr(Fetcher,'_get',original)
    with pytest.raises(asyncio.CancelledError),context.runner._university_read_scope(c):await f.get('https://example.edu/cancelled-after-admission')
    assert len(seen)==1 and controls.counts(context)['catalogue:u-one']==1
    assert context.run.pages_failed==0
    write_raw(context,'cancel-after-admission',{'snapshots_inside_original':seen,'after':snapshot(context),'original_get_count':1,'pages_failed':context.run.pages_failed,'network_calls':0})


def test_80_scope_attempts_two_sqlite_sessions_admit_exactly_60(context,monkeypatch):
    controls.activate(context)
    with context.runner._university_read_scope(controls.candidate()):pass
    barrier=Barrier(2,timeout=5);mutex=Lock();originals=[];attempts=[]
    async def original(fetcher,url,**kwargs):
        durable=snapshot(context)
        with mutex:originals.append({'url':url,'visible':durable[read_budget.LEDGER_KEY]['episodes']['decision:'+context.job.id]['read_counts']['catalogue:u-one']})
        return FetchResult(url=url,outcome=FetchOutcome.CACHED,from_cache=True)
    monkeypatch.setattr(Fetcher,'_get',original)
    def worker(index):
        with context.factory() as session:
            runner=ResearchRunner(session,session.get(ResearchRun,context.run.id),context.profile,context.settings,job_id=context.job.id,worker_id='worker-one',lease_token=1)
            runner._read_guard_enabled=True;runner._read_episode_fresh=False
            barrier.wait()
            async def work():
                f=runner._make_fetcher()
                for i in range(40):
                    try:
                        # Same university, alternating programme-labelled public URLs.
                        with runner._university_read_scope(controls.candidate()):await f.get(f'https://example.edu/programme-{i%2}/{index}/{i}')
                        outcome='admitted'
                    except UniversityReadStopped as e:outcome=e.reason
                    with mutex:attempts.append({'worker':index,'i':i,'outcome':outcome})
            asyncio.run(work())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(worker,i) for i in range(2)]
        for future in futures:future.result(timeout=20)
    assert len(attempts)==80 and len(originals)==60
    assert sum(x['outcome']=='read_cap' for x in attempts)==20
    assert controls.counts(context)=={'catalogue:u-one':60}
    assert all(1<=x['visible']<=60 for x in originals)
    write_raw(context,'80-attempts-two-sqlite-sessions',{'attempts':attempts,'originals':originals,'final':snapshot(context),'database':'actual local SQLite; two threads/sessions, no PostgreSQL proof','network_calls':0})


@pytest.mark.asyncio
async def test_busy_actual_verification_caller_has_zero_get_and_preserves_prior_evidence_not_durable_unknown(context,monkeypatch):
    from app.pipeline import runner as runner_module
    from app.pipeline.runner import _to_out
    from app.schemas.result import ProgramResult
    from app.domain.enums import DegreeLevel
    f=controls.activate(context);c=controls.candidate()
    with context.runner._university_read_scope(c):pass
    previous=ProgramResult(id='independent-old-result',run_id=context.run.id,university=c.name,university_id='old-key',country=c.country,city=c.city,program=c.programs[0].name,program_url=c.programs[0].url,degree=DegreeLevel.BACHELOR,intake='fall 2027')
    claim=controls.program_claim('Independent previous official degree proof')
    previous.claims=[_to_out(claim,'independent-old-claim')]
    context.runner._persist_result(previous,[claim],[]);context.runner._save()
    context.runner._candidates=[c]
    before=snapshot(context)
    with context.factory() as observer:
        prior_claim=deepcopy(observer.query(ClaimRow).one().payload)
        prior_result=deepcopy(observer.query(ProgramResultRow).one().payload)
    seen=controls.mock_original_get(monkeypatch,context)
    def zero_timeout(dbapi_connection,*args):dbapi_connection.execute('PRAGMA busy_timeout=0')
    event.listen(context.engine,'checkout',zero_timeout)
    real_requirements=runner_module.WebRequirementsAdapter
    with context.engine.connect() as blocker:
        def requirements(*args,**kwargs):
            instance=real_requirements(*args,**kwargs)
            blocker.exec_driver_sql('BEGIN IMMEDIATE')
            return instance
        monkeypatch.setattr(runner_module,'WebRequirementsAdapter',requirements)
        try:
            with pytest.raises((UniversityReadStopped,OperationalError)) as raised:
                await context.runner._stage_verify(f)
            escaped=type(raised.value).__name__
            reason=getattr(raised.value,'reason',None)
        finally:
            context.session.rollback();blocker.rollback()
            event.remove(context.engine,'checkout',zero_timeout)
    assert seen==[]
    with context.factory() as observer:
        assert observer.query(ClaimRow).one().payload==prior_claim
        assert observer.query(ProgramResultRow).one().payload==prior_result
        durable_unknowns=observer.get(ResearchRun,context.run.id).unknowns
    assert not any('checkpoint_busy' in x for x in durable_unknowns or [])
    write_raw(context,'busy-real-verification-caller',{'escaped_type':escaped,'escaped_reason':reason,'before':before,'after':snapshot(context),'prior_claim_preserved':True,'prior_result_preserved':True,'durable_unknowns':durable_unknowns,'original_get_count':0,'scope':'Actual _stage_verify; local busy catch cannot promise durable diagnostic persistence while database remains locked','database':'actual local SQLite only','network_calls':0})


def test_mixed_off_save_before_first_namespace_creation_can_erase_60_then_read_61(context,monkeypatch):
    f=controls.activate(context);c=controls.candidate();seen=controls.mock_original_get(monkeypatch,context)
    with context.factory() as off_session:
        stale=off_session.get(ResearchRun,context.run.id)
        off=ResearchRunner(off_session,stale,context.profile,context.settings,job_id=context.job.id,worker_id='worker-one',lease_token=1)
        off._read_guard_enabled=False
        stale.settings_snapshot={'off_writer':'predates first namespace'}
        stale.stage=PipelineStage.CANDIDATE_DISCOVERY.value
        actual=off_session.execute;intercepted=[]
        def execute(statement,*args,**kwargs):
            result=actual(statement,*args,**kwargs)
            if not intercepted and getattr(statement,'is_select',False) and any(getattr(d.get('expr'),'key',None)=='settings_snapshot' for d in getattr(statement,'column_descriptions',[])):
                old=result.scalar_one();intercepted.append(old)
                async def on_work():
                    with context.runner._university_read_scope(c):
                        for i in range(60):await f.get('https://example.edu/on/'+str(i))
                asyncio.run(on_work())
                assert controls.counts(context)['catalogue:u-one']==60
                return SimpleNamespace(scalar_one=lambda:old)
            return result
        monkeypatch.setattr(off_session,'execute',execute)
        off._save()
        after_off=snapshot(context)
        async def last():
            with context.runner._university_read_scope(c):await f.get('https://example.edu/on/61')
        asyncio.run(last())
        after_last=snapshot(context)
        write_raw(context,'mixed-off-on-first-namespace-hole',{'off_preflight':intercepted,'durable_after_off_save':after_off,'durable_after_extra_get':after_last,'original_get_count':len(seen),'all_observed_durable_counts':seen,'same_job':True,'same_worker':True,'same_attempt':True,'on_episode_fresh_retained':context.runner._read_episode_fresh,'ordinary_worker_reachability':'not established by this synthetic concurrent-runner control','frozen_guard_intent_enforced':False,'network_calls':0})
        # Deliberately red universal-contract control. Candidate excludes this mode;
        # durable intent or a reachability proof is needed before universal claims.
        assert len(seen)<=60

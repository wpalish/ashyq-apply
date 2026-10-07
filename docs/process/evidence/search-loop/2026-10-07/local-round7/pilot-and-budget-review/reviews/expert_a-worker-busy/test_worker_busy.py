"""Independent actual SQL Worker controls against unchanged baseline and exact proposal."""
from __future__ import annotations
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import importlib.abc
import importlib.util
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

BASE=Path(__file__).resolve().parent
MODE=os.environ['WORKER_REVIEW_TARGET']
assert MODE in {'baseline','proposal'}
class WorkerShadow(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname=='app.jobs.worker':
            name='worker.proposed.py' if MODE=='proposal' else 'worker.original.py'
            return importlib.util.spec_from_file_location(fullname,BASE/'worker-pinned'/name)
sys.meta_path.insert(0,WorkerShadow())
import review_context as c
pytest_plugins=('review_context',)
import pytest
from sqlalchemy import select, update
from app.jobs import worker as wm
from app.jobs.store import JobStore
from app.models import Job, ResearchRun, ClaimRow, ProgramResultRow
from app.models.base import ensure_utc
from app.pipeline import read_budget
from app.pipeline.control import UniversityReadStopped, LeaseLost, RunCancelled
from app.pipeline.runner import ResearchRunner
from app.pipeline import runner as rm


def state(cxt):
    with cxt.factory() as s:
        job=s.get(Job,cxt.job_id);run=s.get(ResearchRun,cxt.run_id)
        return {'job':{col.key:deepcopy(getattr(job,col.key)) for col in Job.__table__.columns},'run':{col.key:deepcopy(getattr(run,col.key)) for col in ResearchRun.__table__.columns},'facts':c.prior(cxt)}


def prepare(cxt,monkeypatch):
    f=c.activate(cxt);seen=c.original_mock(monkeypatch,cxt)
    with cxt.runner._university_read_scope(c.candidate()):
        for i in range(59):asyncio.run(f.get(f'https://example.edu/previous/{i}'))
    assert c.counts(cxt)=={'catalogue:u-one':59}
    old=c.seed_prior(cxt)
    seen.clear()
    return seen,old


def worker(cxt,monkeypatch):
    @contextmanager
    def scoped():
        s=cxt.factory()
        try:yield s;s.commit()
        except BaseException:s.rollback();raise
        finally:s.close()
    monkeypatch.setattr(wm,'session_scope',scoped)
    w=wm.Worker(cxt.settings,worker_id='worker-one')
    fails=[];mark=[];actual_fail=JobStore.fail;actual_cancel=JobStore.mark_cancelled
    def fail(store,*args,**kwargs):
        fails.append({'args':args,'kwargs':kwargs})
        return actual_fail(store,*args,**kwargs)
    def cancel(store,*args,**kwargs):
        mark.append({'args':args,'kwargs':kwargs})
        return actual_cancel(store,*args,**kwargs)
    monkeypatch.setattr(JobStore,'fail',fail);monkeypatch.setattr(JobStore,'mark_cancelled',cancel)
    return w,fails,mark


async def execute_and_cleanup(w,job_id):
    tasks=[]
    loop=asyncio.get_running_loop();real=loop.create_task
    def create(coro,*args,**kwargs):
        task=real(coro,*args,**kwargs);tasks.append(task);return task
    # Only this running loop is instrumented; heartbeat itself is the real Worker._beat.
    loop.create_task=create
    sem=asyncio.Semaphore(0)
    escaped=None;started=time.monotonic_ns()
    try:
        try:await w._run_and_release(job_id,sem)
        except BaseException as exc:escaped=exc
        await asyncio.sleep(0)
        await asyncio.gather(*tasks,return_exceptions=True)
        elapsed=time.monotonic_ns()-started
        return {'escaped':escaped,'elapsed_ns':elapsed,'semaphore_released':sem._value==1,'heartbeat_tasks':len(tasks),'heartbeat_cancelled':[t.cancelled() for t in tasks],'heartbeat_done':[t.done() for t in tasks]}
    finally:loop.create_task=real


def serialized_execution(value):
    return {**{k:v for k,v in value.items() if k!='escaped'},'escaped':c.error_chain(value['escaped']) if value['escaped'] else []}


def stage_dispatch(cxt):
    async def dispatch(s,store,job,*,lease_token):
        r=c.new_runner(cxt,s,'worker-one',lease_token);r._candidates=[c.candidate()]
        await r._stage_verify(r._make_fetcher())
    return dispatch


@pytest.mark.parametrize('lock_kind',['first','second'])
def test_busy_bounded_return_no_failure_sql_then_real_reaper_same_episode_cap(ctx,monkeypatch,lock_kind):
    seen,old=prepare(ctx,monkeypatch)
    w,fails,marks=worker(ctx,monkeypatch)
    monkeypatch.setattr(w,'_dispatch',stage_dispatch(ctx))
    real=rm.WebRequirementsAdapter;at_lock=[]
    with ctx.factory() as blocker:
        def requirements(*args,**kwargs):
            value=real(*args,**kwargs)
            at_lock.append(state(ctx)) # after legitimate initial stage checkpoint, before blocker
            if ctx.backend=='postgresql':
                c.lock_row(ctx,blocker,'job' if lock_kind=='first' else 'run')
            else:
                blocker.connection().exec_driver_sql('BEGIN IMMEDIATE' if lock_kind=='first' else 'BEGIN EXCLUSIVE')
            return value
        monkeypatch.setattr(rm,'WebRequirementsAdapter',requirements)
        result=asyncio.run(execute_and_cleanup(w,ctx.job_id))
        blocker.rollback()
    after=state(ctx)
    stopped={'mode':MODE,'backend':ctx.backend,'blocker':('Job' if lock_kind=='first' else 'Run') if ctx.backend=='postgresql' else ('BEGIN IMMEDIATE' if lock_kind=='first' else 'BEGIN EXCLUSIVE'),'execution':serialized_execution(result),'failure_writer_calls':fails,'cancel_writer_calls':marks,'before_blocker':at_lock[0],'after_unlock':after,'prior_before':old,'prior_after':c.prior(ctx),'original_io_during_stop':len(seen),'durable_current_count':c.counts(ctx),'worker_jobs_failed':w.jobs_failed,'worker_jobs_done':w.jobs_done}
    c.raw('busy-'+ctx.backend+'-'+lock_kind,stopped)
    assert result['semaphore_released'] and result['heartbeat_tasks']==1 and all(result['heartbeat_cancelled'])
    assert result['escaped'] is None, 'bounded typed busy proposal target: unchanged baseline failure writer escapes/waits under real lock'
    assert not fails, 'typed checkpoint_busy must skip failure-writer SQL even when only Run is locked'
    assert result['elapsed_ns']<1_000_000_000, 'observed local bounded return target (not production hard deadline)'
    assert seen==[] and after==at_lock[0] and c.prior(ctx)==old and c.counts(ctx)=={'catalogue:u-one':59}
    # Recovery occurs only after the lock is gone; simulate expired stored lease,
    # then use real reaper/claim SQL rather than mutating the attempt counter.
    now=datetime.now(UTC)
    with ctx.factory() as recovery:
        recovery.execute(update(Job).where(Job.id==ctx.job_id).values(lease_expires_at=now-timedelta(seconds=1)));recovery.commit()
        store=JobStore(recovery,worker_id='worker-one')
        reaped=store.reap_expired(now=now);assert reaped==[ctx.job_id];recovery.commit()
        recovery.execute(update(Job).where(Job.id==ctx.job_id).values(available_at=now-timedelta(seconds=1)));recovery.commit()
        claimed=store.claim(worker_id='worker-one');assert claimed.id==ctx.job_id and claimed.attempts==2;recovery.commit()
    with pytest.raises(LeaseLost):
        with ctx.runner._university_read_scope(c.candidate()):asyncio.run(ctx.runner._make_fetcher().get('https://example.edu/old-token'))
    assert seen==[] and c.counts(ctx)=={'catalogue:u-one':59}
    monkeypatch.setattr(read_budget,'UNIVERSITY_READ_BUDGET',False)
    with ctx.factory() as resumed:
        r=c.new_runner(ctx,resumed,'worker-one',2)
        assert r._effective_read_guard() is True
        f=r._make_fetcher()
        with r._university_read_scope(c.candidate()):
            asyncio.run(f.get('https://example.edu/resume/60'))
            with pytest.raises(UniversityReadStopped,match='read_cap'):asyncio.run(f.get('https://example.edu/resume/61'))
    c.raw('recovery-'+ctx.backend+'-'+lock_kind,{'same_job_id':ctx.job_id,'actual_reap':reaped,'actual_claim_token':2,'same_worker':True,'old_token_refused':True,'recorded_on_source_false':True,'original_io_after_recovery':len(seen),'inside_io_counts':seen,'durable_count':c.counts(ctx),'prior_before':old,'prior_after':c.prior(ctx),'episode_ids':list(c.snapshot(ctx)[read_budget.LEDGER_KEY]['episodes'])})
    assert len(seen)==1 and seen[0]['durable']=={'catalogue:u-one':60} and c.counts(ctx)=={'catalogue:u-one':60}
    assert c.prior(ctx)==old
    assert list(c.snapshot(ctx)[read_budget.LEDGER_KEY]['episodes'])==['decision:'+ctx.job_id]


@pytest.mark.parametrize('kind',['message_only','typed_other_reason'])
def test_other_errors_still_real_ordinary_fenced_backoff(ctx,monkeypatch,kind):
    seen,old=prepare(ctx,monkeypatch);w,fails,marks=worker(ctx,monkeypatch);before=state(ctx)
    async def dispatch(*args,**kwargs):
        if kind=='message_only':raise RuntimeError('checkpoint_busy is only text, not typed control')
        raise UniversityReadStopped('read_cap')
    monkeypatch.setattr(w,'_dispatch',dispatch)
    result=asyncio.run(execute_and_cleanup(w,ctx.job_id));after=state(ctx)
    c.raw('ordinary-'+ctx.backend+'-'+kind,{'execution':serialized_execution(result),'failure_writer_calls':fails,'before':before,'after':after,'original_io':len(seen),'current_count':c.counts(ctx),'prior_before':old,'prior_after':c.prior(ctx)})
    assert result['escaped'] is None and result['semaphore_released'] and all(result['heartbeat_cancelled'])
    assert len(fails)==1 and not marks and after['job']['status']=='queued' and after['job']['attempts']==1
    assert ensure_utc(after['job']['available_at'])>datetime.now(UTC)
    assert after['job']['worker_id'] is None and c.counts(ctx)=={'catalogue:u-one':59}
    assert not seen and c.prior(ctx)==old and after['run']==before['run'] and w.jobs_failed==1


def test_real_user_cancel_keeps_cancelled_path(ctx,monkeypatch):
    seen,old=prepare(ctx,monkeypatch);w,fails,marks=worker(ctx,monkeypatch);before=state(ctx)
    with ctx.factory() as other:assert JobStore(other).cancel(ctx.job_id);other.commit()
    monkeypatch.setattr(w,'_dispatch',stage_dispatch(ctx))
    result=asyncio.run(execute_and_cleanup(w,ctx.job_id));after=state(ctx)
    c.raw('cancel-'+ctx.backend,{'execution':serialized_execution(result),'failure_writer_calls':fails,'cancel_writer_calls':marks,'after':after,'original_io':len(seen),'current_count':c.counts(ctx),'prior_before':old,'prior_after':c.prior(ctx)})
    assert result['escaped'] is None and result['semaphore_released'] and all(result['heartbeat_cancelled'])
    assert not fails and len(marks)==1 and after['job']['status']=='cancelled' and after['job']['cancel_requested']
    assert after['job']['lease_expires_at'] is None and not seen and c.prior(ctx)==old and after['run']==before['run']
    assert c.counts(ctx)=={'catalogue:u-one':59} and w.jobs_failed==0


def test_real_attempt_takeover_preserves_worker_lease_lost_path(ctx,monkeypatch):
    seen,old=prepare(ctx,monkeypatch);w,fails,marks=worker(ctx,monkeypatch);before=state(ctx)
    async def dispatch(s,store,job,*,lease_token):
        assert lease_token==1
        with ctx.factory() as new:
            new.execute(update(Job).where(Job.id==ctx.job_id).values(attempts=2));new.commit()
        r=c.new_runner(ctx,s,'worker-one',lease_token);r._candidates=[c.candidate()]
        await r._stage_verify(r._make_fetcher())
    monkeypatch.setattr(w,'_dispatch',dispatch)
    result=asyncio.run(execute_and_cleanup(w,ctx.job_id));after=state(ctx)
    c.raw('lease-'+ctx.backend,{'execution':serialized_execution(result),'failure_writer_calls':fails,'cancel_writer_calls':marks,'before':before,'after':after,'original_io':len(seen),'current_count':c.counts(ctx),'prior_before':old,'prior_after':c.prior(ctx)})
    assert result['escaped'] is None and result['semaphore_released'] and all(result['heartbeat_cancelled'])
    assert not fails and not marks and after['job']['status']=='running' and after['job']['attempts']==2 and after['job']['worker_id']=='worker-one'
    assert not seen and c.prior(ctx)==old and c.counts(ctx)=={'catalogue:u-one':59} and w.jobs_failed==0
    # Stage transition before the fenced _save is rolled back; never persists FAILED.
    assert after['run']==before['run']

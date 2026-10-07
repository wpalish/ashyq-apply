"""Complete prepared actual caller/recorder coverage without rerunning the PG-09 red."""
from __future__ import annotations
import asyncio
from copy import deepcopy
import hashlib
from types import SimpleNamespace
import pytest
import test_independent_pg as c
pytest_plugins=('test_independent_pg',)
from sqlalchemy import select, update
from app.adapters.discovery.catalog_walker import CatalogWalker
from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter
from app.adapters.fetching import Fetcher
from app.catalogue import discovery
from app.models import Job, ResearchRun, SourcePage
from app.pipeline import read_budget
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped


@pytest.mark.parametrize('renderer',[False,True])
def test_pg_06_actual_walker_plain_and_renderer_broad_catch_propagates_db_busy(ctx,monkeypatch,renderer):
    f=c.activate(ctx);seen=c.original_mock(monkeypatch,ctx)
    if renderer:
        async def render(url):return await f.get(url)
        f._renderer=SimpleNamespace(render=render,catalog_payloads=[])
    walker=CatalogWalker(fetcher=f,domain='example.edu',degree='bachelor',fields=['computer science'])
    with ctx.runner._university_read_scope(c.candidate()):
        with ctx.factory() as blocker:
            c.lock_row(ctx,blocker,'run')
            with pytest.raises(UniversityReadStopped) as info:asyncio.run(walker.walk(['https://example.edu/catalogue']))
            assert info.value.reason=='checkpoint_busy' and info.value.__cause__.orig.sqlstate=='55P03'
            blocker.rollback()
    c.raw('PG-06-walker-renderer-'+str(renderer),{'exception':c.error_chain(info.value),'original_get':len(seen),'durable':c.counts(ctx),'actual_walk':True,'renderer_callback_uses_guarded_fetcher':renderer})
    assert seen==[] and c.counts(ctx)=={'catalogue:u-one':0}


@pytest.mark.parametrize('signal',['cancel','fence'])
def test_pg_06_actual_walker_cancellation_and_lease_control_not_swallowed(ctx,monkeypatch,signal):
    f=c.activate(ctx);seen=c.original_mock(monkeypatch,ctx)
    walker=CatalogWalker(fetcher=f,domain='example.edu',degree='bachelor',fields=['computer science'])
    with ctx.runner._university_read_scope(c.candidate()):
        with ctx.factory() as other:
            fields={'cancel_requested':True} if signal=='cancel' else {'attempts':2}
            other.execute(update(Job).where(Job.id==ctx.job_id).values(**fields));other.commit()
        expected=RunCancelled if signal=='cancel' else LeaseLost
        with pytest.raises(expected) as info:asyncio.run(walker.walk(['https://example.edu/catalogue']))
    c.raw('PG-06-walker-'+signal,{'exception':c.error_chain(info.value),'original_get':len(seen),'durable':c.counts(ctx),'actual_walk':True})
    assert seen==[] and c.counts(ctx)=={'catalogue:u-one':0}


@pytest.mark.parametrize('row',['job','run'])
def test_pg_08_actual_funding_busy_retains_prior_claims(ctx,monkeypatch,row):
    from app.pipeline import runner as rm
    f=c.activate(ctx)
    with ctx.runner._university_read_scope(c.candidate()):pass
    old=c.seed_prior(ctx);seen=c.original_mock(monkeypatch,ctx);before=c.snapshot(ctx)
    ctx.runner._candidates=[c.candidate()]
    real=rm.WebScholarshipAdapter
    with ctx.factory() as blocker:
        def scholarship(*args,**kwargs):
            value=real(*args,**kwargs);c.lock_row(ctx,blocker,row);return value
        monkeypatch.setattr(rm,'WebScholarshipAdapter',scholarship)
        with pytest.raises(UniversityReadStopped) as info:asyncio.run(ctx.runner._stage_funding(f))
        assert info.value.reason=='checkpoint_busy' and info.value.__cause__.orig.sqlstate=='55P03'
        assert not ctx.session.in_transaction();blocker.rollback()
    after=c.prior(ctx)
    c.raw('PG-08-funding-'+row,{'exception':c.error_chain(info.value),'original_get':len(seen),'prior_before':old,'prior_after':after,'ledger_before':before[read_budget.LEDGER_KEY],'ledger_after':c.snapshot(ctx)[read_budget.LEDGER_KEY]})
    assert not seen and after==old and c.snapshot(ctx)[read_budget.LEDGER_KEY]==before[read_budget.LEDGER_KEY]


@pytest.mark.parametrize('route',['catalogue','curated'])
def test_pg_09_real_discovery_broad_catch_preserves_typed_busy(ctx,monkeypatch,route):
    f=c.activate(ctx);seen=c.original_mock(monkeypatch,ctx)
    with ctx.runner._university_read_scope(c.candidate()):pass
    entry={'name':'Independent Test University','country':'Example','city':'City','homepage':'https://example.edu/'}
    if route=='catalogue':
        uni=SimpleNamespace(id='u-one',name=entry['name'],country=entry['country'],city='City',domain='example.edu',registry_entry=entry)
        monkeypatch.setattr(discovery,'retrieve',lambda *a,**k:[uni])
    else:
        monkeypatch.setattr(discovery,'retrieve',lambda *a,**k:[])
        monkeypatch.setattr(LiveDiscoveryAdapter,'registry',lambda _:[entry])
        ctx.run.university_ids=None
    adapter=ctx.runner._make_discovery_adapter(f)
    with ctx.factory() as blocker:
        c.lock_row(ctx,blocker,'job')
        with pytest.raises(UniversityReadStopped) as info:asyncio.run(adapter.discover(ctx.profile,1))
        assert info.value.reason=='checkpoint_busy' and info.value.__cause__.orig.sqlstate=='55P03'
        blocker.rollback()
    c.raw('PG-09-discovery-'+route,{'exception':c.error_chain(info.value),'original_get':len(seen),'durable':c.counts(ctx),'actual_discover_loop':True})
    assert not seen and c.counts(ctx)=={'catalogue:u-one':0}


def test_pg_10_actual_source_recorder_flush_can_hold_run_before_job_nowait(ctx,monkeypatch):
    f=c.activate(ctx);seen=c.original_mock(monkeypatch,ctx)
    with ctx.runner._university_read_scope(c.candidate()):pass
    before=c.snapshot(ctx);old=c.seed_prior(ctx)
    ctx.run.pages_checked=23
    adapter=ctx.runner._make_discovery_adapter(f)
    page=adapter.page_recorder(url='https://example.edu/earlier-recorded-page',registrable_domain='example.edu',http_status=200,page_type='program_detail')
    assert page.id and ctx.session.query(SourcePage).count()==1
    with ctx.factory() as blocker:
        c.lock_row(ctx,blocker,'job')
        with pytest.raises(UniversityReadStopped) as info:
            with ctx.runner._university_read_scope(c.candidate()):asyncio.run(f.get('https://example.edu/next'))
        assert info.value.reason=='checkpoint_busy' and info.value.__cause__.orig.sqlstate=='55P03'
        with ctx.factory() as third:third.execute(select(ResearchRun.id).where(ResearchRun.id==ctx.run_id).with_for_update(nowait=True))
        blocker.rollback()
    with ctx.factory() as observer:
        source_count=observer.query(SourcePage).count();pages=observer.get(ResearchRun,ctx.run_id).pages_checked
    source_path=__import__('pathlib').Path(__import__('app.models.source_page',fromlist=['SourcePage']).__file__)
    c.raw('PG-10-actual-source-recorder',{'source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),'exception':c.error_chain(info.value),'original_get':len(seen),'source_rows_after_rollback':source_count,'pages_checked_after_rollback':pages,'prior_before':old,'prior_after':c.prior(ctx),'prior_run_lock_released':True,'source_insertion_was_uncommitted':True})
    assert not seen and source_count==0 and pages==0 and c.prior(ctx)==old and c.snapshot(ctx)==before


def test_pg_07_explicit_new_untracked_default_false_is_legacy_not_universal_cap(ctx,monkeypatch):
    monkeypatch.setattr(read_budget,'UNIVERSITY_READ_BUDGET',False)
    assert ctx.runner._effective_read_guard() is False
    seen=c.original_mock(monkeypatch,ctx)
    f=ctx.runner._make_fetcher();assert type(f) is Fetcher
    for i in range(61):asyncio.run(f.get(f'https://example.edu/legacy-off/{i}'))
    c.raw('PG-07-untracked-off-boundary',{'original_get':len(seen),'durable_snapshot':c.snapshot(ctx),'classification':'explicitly excluded untracked OFF legacy path; no universal preexisting OFF/ON deployment cap'})
    assert len(seen)==61 and read_budget.LEDGER_KEY not in c.snapshot(ctx)

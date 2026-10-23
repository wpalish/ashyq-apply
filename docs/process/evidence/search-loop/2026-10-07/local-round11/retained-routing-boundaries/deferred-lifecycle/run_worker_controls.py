from __future__ import annotations

import asyncio
import json
import sys
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import control_support as p
from sqlalchemy import create_engine
from app.adapters.discovery import catalog_walker as aw
from app.adapters.fetching import Fetcher
from app.jobs import worker as wm
from app.models import AuditEvent, ClaimRow, Job, ProgramResultRow, ResearchRun, SourcePage, University
from app.pipeline import read_budget as rb
from app.pipeline import runner as rm
from tests import readguard_support as c
from tests.test_worker_checkpoint_busy import execute_and_cleanup, serialized_execution


async def execute(ctx, flag):
    p.live.RETAIN_CONFIRMED_DISCOVERY_PARTIAL = flag
    cat = "https://www.rug.nl/bachelors/synthetic-catalogue"
    tail = "https://www.rug.nl/bachelors/zz-computing-science-tail-later-route"
    catalog_html = p.catalog([(p.GRCS, "BSc Computer Science", p.retained[p.GRCS]),
        (tail, "BSc Computer Science", p.programme())], cat)[cat]
    seen = []
    adapters = []
    publications = []
    gets = []
    real_maker = rm.ResearchRunner._make_discovery_adapter

    def maker(runner, fetcher):
        adapter = real_maker(runner, fetcher)
        adapters.append(adapter)
        real_apply = adapter._apply
        def apply(*args, **kwargs):
            publications.append({"during_exception": sys.exc_info()[0] is not None,
                "native_count": c.counts(ctx), "gets": list(gets)})
            return real_apply(*args, **kwargs)
        adapter._apply = apply
        async def sitemaps(*args, **kwargs):
            # Synthetic generator activity only. The production guard + Fetcher.get remain intact.
            for index in range(58):
                await fetcher.get(f"https://www.rug.nl/synthetic-noise/{index}")
        adapter.sitemaps.collect = sitemaps
        adapter._navigation_fallback = p.no_navigation
        adapter._add_search_results = p.no_search
        return adapter

    async def source_transport(fetcher, url, **kwargs):
        gets.append(url)
        visible = c.counts(ctx)
        seen.append({"url": url, "durable_before_original_IO": visible})
        item = p.retained[p.GRCS] if url==p.GRCS else catalog_html if url==cat else '<html><title>Synthetic noise</title><p>No source assertions.</p></html>'
        return p.result(url,item)

    @contextmanager
    def scoped():
        s=ctx.factory()
        try:
            yield s
            s.commit()
        except BaseException:
            s.rollback()
            raise
        finally:
            s.close()

    with patch.object(rb,"UNIVERSITY_READ_BUDGET",True), patch.object(rm,"CatalogueDiscoveryAdapter",p.catalogue.CatalogueDiscoveryAdapter), patch.object(rm,"LiveDiscoveryAdapter",p.live.LiveDiscoveryAdapter), patch.object(aw,"CatalogWalker",p.walker.CatalogWalker), patch.object(rm.ResearchRunner,"_make_discovery_adapter",maker), patch.object(Fetcher,"_get",source_transport), patch.object(wm,"session_scope",scoped):
        w=wm.Worker(ctx.settings,worker_id="worker-one")
        assert w._dispatch.__func__ is wm.Worker._dispatch
        outcome=await execute_and_cleanup(w,ctx.job_id)
    with ctx.factory() as observer:
        job=observer.get(Job,ctx.job_id);run=observer.get(ResearchRun,ctx.run_id)
        results=[x.payload for x in observer.query(ProgramResultRow).filter_by(run_id=ctx.run_id).all()]
        claims=observer.query(ClaimRow).count()
        sources=[{"url":x.url,"page_type":x.page_type,"content_hash":x.content_hash} for x in observer.query(SourcePage).all()]
        completed=observer.query(AuditEvent).filter_by(action="job_completed",entity_id=ctx.job_id).count()
        values={"flag":flag,"job_status":job.status,"attempt_token":job.attempts,"run_stage":run.stage,
            "unknowns":run.unknowns,"errors":run.errors,"results":results,"claim_rows":claims,
            "source_pages":sources,"job_completed":completed,"worker_done":w.jobs_done,
            "worker_failed":w.jobs_failed,"ledger":c.snapshot(ctx),"counts":c.counts(ctx),
            "source_transport_calls":seen,"apply_calls":publications,
            "candidate_outputs":[asdict(x) for adapter in adapters for x in getattr(adapter,"returned_candidates",[])],
            "adapter_traces":[asdict(trace) for adapter in adapters for trace in adapter.traces],
            "execution":serialized_execution(outcome),"case_root":str(ctx.root)}
        if flag:
            expected_urls=[p.GRCS]
        else:
            expected_urls=[None]
        checks={
            "real_job_terminal_success_is_not_fact_success":job.status=="succeeded" and job.attempts==1 and completed==1 and w.jobs_done==1,
            "real_60_charge_commits_before_each_original_io":len(seen)==60 and c.counts(ctx)=={"catalogue:u-one":60} and [x["durable_before_original_IO"].get("catalogue:u-one") for x in seen]==list(range(1,61)),
            "saved_correct_source_read60_no_tail_read61":gets[-1]==p.GRCS and tail not in gets,
            "expected_provisional_URL_retained_on_only":[x.get("program_url") for x in results]==expected_urls,
            "zero_claim_all_applicability_unknown":claims==0 and all(not x["claims"] for x in results) and any("read_cap" in x for x in run.unknowns),
            "real_SourcePage_prior_to_confirmation_preserved":any(x["url"]==p.GRCS and x["content_hash"]=="a0972cf0d971f1b7863e72914d72099d5c069081553cc9fb4265b76e37f742a1" for x in sources),
            "heartbeat_cleaned_and_no_exception":outcome["escaped"] is None and outcome["semaphore_released"] and outcome["heartbeat_tasks"]==1 and all(outcome["heartbeat_done"]),
            "no_apply_during_exception_unwind":not any(x["during_exception"] for x in publications),
        }
        values["checks"]=[{"case":name,"status":"PASS" if okay else "RED"} for name,okay in checks.items()]
    return values


async def main():
    bundle=[]
    label=sys.argv[1] if len(sys.argv)>1 else "worker.attempt1"
    for flag in [False,True]:
        root=p.B/(label+('.on' if flag else '.off'));assert not root.exists();root.mkdir()
        engine=create_engine("sqlite:///"+str(root/'state.db'))
        try:
            with c.make_context(engine,root) as ctx:
                ctx.run.university_ids=["u-one"]
                ctx.run.profile.payload=p.profile().model_dump(mode="json")
                ctx.session.add(University(id="u-one",identity_key="synthetic-retention-u-one",name="University of Groningen",country="Netherlands",city="Groningen",domain="www.rug.nl",registry_entry={"name":"University of Groningen","country":"Netherlands","city":"Groningen","homepage":"https://www.rug.nl/","seeds":{p.live.PageCategory.PROGRAM_CATALOG:"https://www.rug.nl/bachelors/synthetic-catalogue"}}))
                ctx.session.commit()
                bundle.append(await execute(ctx,flag))
        finally:
            engine.dispose()
    target=p.B/(label+'.json');assert not target.exists()
    target.write_text(json.dumps(bundle,indent=2,default=str)+'\n')
    checks=[x for case in bundle for x in case['checks']]
    print(json.dumps({"PASS":sum(x['status']=='PASS' for x in checks),"RED":sum(x['status']=='RED' for x in checks),"total":len(checks)}))
    for case in bundle:
        for check in case['checks']:
            if check['status']=='RED':print(case['flag'],check['case'])


if __name__=='__main__':
    asyncio.run(main())

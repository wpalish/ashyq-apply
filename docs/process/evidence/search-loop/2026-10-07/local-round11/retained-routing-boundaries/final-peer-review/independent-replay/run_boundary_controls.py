import asyncio
import json
import sys
from datetime import UTC, datetime
from dataclasses import asdict

import control_support as c
from run_controls import safe, urls, wrapper
from app.adapters.discovery import live_discovery as native
from app.adapters.search.base import SearchFailureReason, SearchUnavailable, SearchResponse, SearchResult
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped

ROWS=[]


def record(name, expected, okay, **extra):
    ROWS.append({"case":name,"expected":expected,"status":"PASS" if okay else "RED",**extra})


async def main():
    cap=UniversityReadStopped("read_cap")
    tail=c.PREFIX+"z"
    good=c.programme()
    # Correct expectation follows the actual unchanged native scoring, not profile list order.
    p=c.catalog([(c.PREFIX+"a","BSc Computer Science",good),
        (c.PREFIX+"math","BSc Mathematics",c.programme("BSc Mathematics")),(tail,"BSc Computer Science",cap)])
    for kind,module in [('live',c.live),('catalogue',c.catalogue)]:
        out=await wrapper(module,True,p,['computer science','mathematics'],kind=kind)
        actual_read_prefix=[u for u in out['gets'][1:] if u!=tail]
        record('multifield_native_order.'+kind,'Retained strict subset follows actual native confirmed prefix, both requested fields, no extra reads',urls(out)==actual_read_prefix and set(urls(out))=={c.PREFIX+'a',c.PREFIX+'math'} and out['gets'][-1]==tail,result=safe(out))
    for status,reason in [(None,SearchFailureReason.RATE_LIMITED),(429,None),(None,SearchFailureReason.TIMEOUT)]:
        refusal=SearchUnavailable('Synthetic only',http_status=status,reason=reason)
        class Provider:
            name='fake'
            async def search(self,*args,**kwargs):
                raise refusal
        f=c.MockFetcher({tail:cap})
        async def search(entry,domain,selected,trace,profile):
            adapter=c.live.LiveDiscoveryAdapter(f);adapter._search_provider=Provider();adapter._search_provider_resolved=True
            await adapter._add_search_results(entry,domain,selected,trace,profile)
            await f.get(tail)
        for kind,module in [('live',c.live),('catalogue',c.catalogue)]:
            out=await wrapper(module,True,c.catalog([(c.PREFIX+'a','BSc Computer Science',good)]),['computer science'],kind=kind,search=search)
            record('failure_declines_retention.'+str(status)+'.'+str(reason)+'.'+kind,
                'Any structural search_failures entry conservatively rejects retention: ORIGINAL later read_cap rethrows; original provider error already lost natively',
                out['error_object'] is cap and not out['candidates'],result=safe(out),original_provider_exception_recovered=False)
    # Actual entry-point await fetch is caught inside native retrieval. No raising _add_search_results stub.
    for index,signal in enumerate([UniversityReadStopped('read_cap'),UniversityReadStopped('checkpoint_busy'),RunCancelled('synthetic cancel'),LeaseLost('synthetic stale fence')]):
        class Provider:
            name='fake'
            async def search(self,*,query,**kwargs):
                now=datetime.now(UTC)
                return SearchResponse(query=query,provider='fake',retrieved_at=now,
                    results=(SearchResult(url=c.PREFIX+'a',title='BSc Computer Science',provider='fake',rank=1,retrieved_at=now),))
        resultset=[]
        for module,flag in [(c.actual_live,False),(c.live,True)]:
            f=c.MockFetcher({'https://example.edu/':signal})
            async def search(entry,domain,selected,trace,profile):
                adapter=module.LiveDiscoveryAdapter(f);adapter._search_provider=Provider();adapter._search_provider_resolved=True
                await adapter._add_search_results(entry,domain,selected,trace,profile)
            out=await wrapper(module,flag,c.catalog([(c.PREFIX+'a','BSc Computer Science',good)]),['computer science'],search=search)
            resultset.append(out)
        record('native_entry_point_exception_'+str(index),
            'Full original typed control should propagate through the actual provider entry-point reader; inherited native broad catch currently violates it',
            all(out['error_object'] is signal and not out['candidates'] for out in resultset),
            native=safe(resultset[0]),on=safe(resultset[1]),inner_fetch_calls=f.calls,
            introduced_by_retention=False,complete_output_equality=safe(resultset[0])['candidates']==safe(resultset[1])['candidates'])
    # Exact saved Groningen body, only synthetic catalogue construction; complete native equality stays meaningful.
    p=c.catalog([(c.GRCS,'BSc Computer Science',c.retained[c.GRCS])],cat=c.GRCAT)
    for kind,module,actual in [('live',c.live,c.actual_live),('catalogue',c.catalogue,c.actual_catalogue)]:
        old=await wrapper(actual,False,p,['computer science'],cat=c.GRCAT,kind=kind)
        on=await wrapper(module,True,p,['computer science'],cat=c.GRCAT,kind=kind)
        keys=['candidates','traces','gets','error']
        record('saved_groningen_exact_body_complete.'+kind,'Native complete accepted saved URL remains whole-output equal ON and no hidden missing-body failure',
            all(old[k]==on[k] for k in keys) and urls(on)==[c.GRCS] and not on['error'],native=safe(old),on=safe(on))
    report={'counts':{'PASS':sum(x['status']=='PASS' for x in ROWS),'RED':sum(x['status']=='RED' for x in ROWS),'total':len(ROWS)},'checks':ROWS,
        'global_provider_stop_proof':False,'real_provider_calls':0,'native_refusal_boundary':'Original provider exceptions are lost; conservative any-failure refusal is not original-provider propagation.'}
    target=c.B/(sys.argv[1] if len(sys.argv)>1 else 'boundary-controls.final.json');assert not target.exists()
    target.write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps(report['counts']))
    for row in ROWS:
        if row['status']=='RED':print(row['case'])


if __name__=='__main__':
    asyncio.run(main())

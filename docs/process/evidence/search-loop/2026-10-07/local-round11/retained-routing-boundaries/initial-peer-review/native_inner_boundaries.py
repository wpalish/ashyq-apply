from __future__ import annotations

import asyncio
import json
import socket
from datetime import UTC, datetime
from pathlib import Path

DENIED = []
def deny(*args, **kwargs):
    DENIED.append('external_transport_attempt')
    raise AssertionError('Offline-only native boundary control')

socket.getaddrinfo = deny
socket.create_connection = deny
socket.socket.connect = deny
import httpx
httpx.Client.send = deny
httpx.AsyncClient.send = deny

from app.adapters.search.base import SearchFailureReason, SearchResponse, SearchResult, SearchUnavailable
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.retrieval import discover_candidates
from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped
from evaluation.research.live import _ExpertBudget

ROWS = []
INTENT = DiscoveryIntent(institution='Example University', domain='example.edu', degree='bachelor', field='computer science')

class ResultProvider:
    name = 'fake'
    def __init__(self): self.calls = 0
    async def search(self, *, query, **kwargs):
        self.calls += 1
        r = SearchResult(url='https://example.edu/bachelors/computer-science', title='BSc Computer Science', provider=self.name, rank=1, retrieved_at=datetime(2026,10,8,tzinfo=UTC))
        return SearchResponse(query=query,provider=self.name,retrieved_at=r.retrieved_at,results=(r,))

async def swallowed_controls():
    for signal in [UniversityReadStopped('read_cap'), UniversityReadStopped('checkpoint_busy'), RunCancelled('synthetic cancellation'), LeaseLost('synthetic stolen lease'), asyncio.CancelledError('synthetic coroutine cancel')]:
        p=ResultProvider();opened=[];escaped=None;report=None
        async def read(url):
            opened.append(url)
            raise signal
        try: report=await discover_candidates(p,INTENT,query_budget=1,fetch=read)
        except BaseException as exc: escaped=exc
        expected_propagation=escaped is signal
        ROWS.append({'case':'native_entrypoint_'+type(signal).__name__+'_'+str(getattr(signal,'reason','')),'status':'PASS' if expected_propagation else 'RED','qualification':'Inherited native retrieval boundary; NOT newly introduced proposal failure','expected':'Original control exception propagates from entry-point fetch','escaped':type(escaped).__name__ if escaped else None,'report_returned':report is not None,'fake_search_calls':p.calls,'entry_fetch_calls':opened,'entry_points_unreachable':getattr(report,'entry_points_unreachable',None)})

class RefusalProvider:
    name='exa_mcp'
    def __init__(self, signal, budget=None): self.signal=signal;self.budget=budget;self.fake_dispatches=0
    async def search(self, **kwargs):
        if self.budget: self.budget.before_search(self.name)
        self.fake_dispatches+=1
        if self.budget: raise self.budget.failed_search(self.signal)
        raise self.signal

async def refusal_controls():
    for name,signal,bounded in [
        ('native_unwrapped_rate_limit',SearchUnavailable('synthetic refusal',reason=SearchFailureReason.RATE_LIMITED),False),
        ('strict_inmemory_rate_limit',SearchUnavailable('synthetic refusal',reason=SearchFailureReason.RATE_LIMITED),True),
        ('strict_inmemory_http429',SearchUnavailable('synthetic refusal',http_status=429),True),
    ]:
        budget=_ExpertBudget(max_fetcher_calls=60,seconds=120,provider_name='exa_mcp',started=0,clock=lambda:0) if bounded else None
        p=RefusalProvider(signal,budget);attempts=[]
        report=await discover_candidates(p,INTENT,query_budget=6,on_query_attempt=lambda:attempts.append(len(attempts)+1))
        if not bounded:
            okay=p.fake_dispatches==6 and len(report.failed_queries)==6 and not report.throttled
        else:
            before=(budget.provider_failure.copy(),budget.stop_reason,budget.search_queries)
            future_errors=[]
            for next_work in [budget.before_fetch,lambda:budget.before_search('exa_mcp')]:
                try:next_work()
                except SearchUnavailable as exc:future_errors.append({'type':type(exc).__name__,'status':exc.http_status})
            after=(budget.provider_failure.copy(),budget.stop_reason,budget.search_queries)
            okay=p.fake_dispatches==1 and len(future_errors)==2 and before==after and budget.provider_failure is not None
        ROWS.append({'case':name,'status':'PASS' if okay else 'RED','expected':'Observe native diagnostic degradation separately from strict sticky first refusal; mock dispatch never vendor HTTP','mock_provider_dispatches':p.fake_dispatches,'search_seam_attempts':len(attempts),'failed_queries':len(report.failed_queries),'report_throttled':report.throttled,'failure_diagnostics':list(report.failure_diagnostics),'budget_snapshot':budget.snapshot() if budget else None,'STOP_file_written':False})

async def main():
    await swallowed_controls();await refusal_controls()
    out={'source':'Normal unchanged native imports; no search/discover/Fetcher implementation replaced','results':ROWS,'counts':{'PASS':sum(r['status']=='PASS' for r in ROWS),'RED':sum(r['status']=='RED' for r in ROWS),'total':len(ROWS)},'denied_transport_attempts':DENIED,'real_network_provider_model_calls':0,'STOP_file_written':False}
    path=Path(__file__).with_suffix('.json');assert not path.exists();path.write_text(json.dumps(out,indent=2,default=str)+'\n')
    print(json.dumps(out['counts']))

if __name__=='__main__':asyncio.run(main())

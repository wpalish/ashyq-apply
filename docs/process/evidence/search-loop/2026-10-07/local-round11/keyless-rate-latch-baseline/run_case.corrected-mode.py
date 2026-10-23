"""Fresh interpreter, original native methods, MockTransport only; no throttle reset."""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import socket
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

B=Path(__file__).resolve().parent
REPO=B.parents[1]/'ashyq-apply/backend'
sys.path.insert(0,str(REPO))
PLAN=json.loads((B/'PLAN.json').read_text())


def pins():
    return {rel:hashlib.sha256((REPO/rel).read_bytes()).hexdigest() for rel in PLAN['original_source_sha256']}


def deny(*args,**kwargs):
    raise AssertionError('Real network/DNS/socket forbidden')


resolutions=[]
def synthetic_resolver(host,port,*args,**kwargs):
    assert host=='mcp.exa.ai',host
    resolutions.append({'host':host,'port':port,'kind':'synthetic resolver, zero real DNS'})
    return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',port))]


socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
socket.getaddrinfo=synthetic_resolver

import httpx
from app import config
from app.adapters import search
from app.adapters.search import exa_mcp as mcp
from app.adapters.search.base import SearchFailureReason,SearchUnavailable
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.retrieval import discover_candidates

# No direct search-method replacement and no reset: the module starts empty in this process.
assert search._THROTTLED_UNTIL=={}
assert mcp._last_query_at is None
assert pins()==PLAN['original_source_sha256']
METHODS={name:getattr(mcp.ExaMcpSearchProvider,name) for name in ['search','_search_once','_post','_initialize']}


class Clock:
    value=100.0
    sleeps=[]
    def monotonic(self):return self.value
    async def sleep(self,seconds):
        self.sleeps.append(seconds);self.value+=seconds


class Server:
    def __init__(self,mode):
        self.mode=mode;self.events=[]
    async def handle(self,request):
        payload=json.loads(request.content)
        row={'method':payload['method'],'request_id':payload.get('id'),'payload':payload,
            'url':str(request.url),'session_header':request.headers.get('mcp-session-id')}
        self.events.append(row)
        method=payload['method']
        if method=='initialize':
            body={'jsonrpc':'2.0','id':payload['id'],'result':{'protocolVersion':mcp.PROTOCOL_VERSION,'capabilities':{},'serverInfo':{'name':'offline-synthetic-mcp','version':'1'}}}
            row.update(status=200,response=body)
            return httpx.Response(200,json=body,headers={'mcp-session-id':'synthetic-session'})
        if method=='notifications/initialized':
            row.update(status=202,response=None)
            return httpx.Response(202)
        assert method=='tools/call'
        assert payload['params']['name']=='web_search_advanced_exa'
        if self.mode=='http429':
            row.update(status=429,response={'error':'synthetic refusal'})
            return httpx.Response(429,json={'error':'synthetic refusal'})
        if self.mode=='transport':
            row.update(status=None,raised='httpx.ConnectError')
            raise httpx.ConnectError('Synthetic transport only',request=request)
        if self.mode=='timeout':
            row.update(status=None,raised='httpx.ReadTimeout')
            raise httpx.ReadTimeout('Synthetic timeout only',request=request)
        result={'structuredContent':{'results':[{'url':'https://example.edu/bachelors/computer-science','title':'BSc Computer Science','highlights':['Public discovery hint only']}]}}
        if self.mode=='meta':
            # Exact current Exa tool key, boolean True, normal HTTP200. Valid rows cannot turn refusal into success.
            result['_meta']={'ai.exa/rateLimited':True}
        elif self.mode=='meta-false':
            result['_meta']={'ai.exa/rateLimited':False}
        body={'jsonrpc':'2.0','id':payload['id'],'result':result}
        row.update(status=200,response=body)
        return httpx.Response(200,json=body)


def failure(exc):
    return {'type':type(exc).__name__,'reason':exc.reason.value if isinstance(exc.reason,SearchFailureReason) else exc.reason,
        'http_status':exc.http_status,'message':str(exc)}


async def main(name):
    clock=Clock();mode='meta-false' if name=='factory-meta-false-corrected' else 'meta' if 'meta' in name and name!='factory-meta-false' else name.split('-')[-1]
    server=Server(mode);clients=[];seam=[];checks=[]
    original_client=httpx.AsyncClient
    def client_factory(*args,**kwargs):
        assert 'transport' not in kwargs
        kwargs['transport']=httpx.MockTransport(server.handle)
        client=original_client(*args,**kwargs);clients.append(client);return client
    def check(key,expected,okay):
        checks.append({'case':key,'expected':expected,'status':'PASS' if okay else 'RED'})
    settings=SimpleNamespace(search_provider='exa_mcp')
    current_retry=mcp.RATE_LIMIT_RETRY
    effective_retry=False if name.endswith('no-retry') else current_retry
    with patch.object(config,'get_settings',lambda:settings),patch.object(httpx,'AsyncClient',client_factory),patch.object(search,'time',SimpleNamespace(monotonic=clock.monotonic)),patch.object(mcp,'time',SimpleNamespace(monotonic=clock.monotonic)),patch.object(mcp,'asyncio',SimpleNamespace(sleep=clock.sleep,Lock=asyncio.Lock,timeout=asyncio.timeout)),patch.object(mcp,'RATE_LIMIT_RETRY',effective_retry):
        first=search.get_search_provider()
        assert isinstance(first,search._ThrottleLatch) and type(first.inner) is mcp.ExaMcpSearchProvider
        assert all(getattr(mcp.ExaMcpSearchProvider,key) is value for key,value in METHODS.items())
        if name.startswith('factory'):
            reports=[];counts=[]
            for provider,query in [(first,'public computer science first'),(first,'public computer science repeat'),(search.get_search_provider(),'public computer science other instance')]:
                seam.append({'query':query,'instance':len(reports),'request_count_before':len(server.events)})
                try:
                    got=await provider.search(query=query,domains=['example.edu'],max_results=10)
                    reports.append({'error':None,'response':asdict(got)})
                except SearchUnavailable as exc:
                    reports.append({'error':failure(exc),'response':None})
                counts.append({method:sum(x['method']==method for x in server.events) for method in ['initialize','notifications/initialized','tools/call']})
            if mode in {'meta','http429'}:
                first_tools=2 if mode=='meta' and effective_retry else 1
                check('initial_actual_error_preserves_reason_status','Explicit metadata keeps RATE_LIMITED/http_statusNone; HTTP429 keeps429 without pretending metadata status429',
                    all(r['error'] is not None and r['error']['http_status']==(None if mode=='meta' else 429) and r['error']['reason']==('rate limited' if mode=='meta' else None) for r in reports))
                check('factory_process_latch_engages','Process factory marks this explicit refusal after the initial native call',bool(search._THROTTLED_UNTIL.get('exa_mcp')))
                check('same_instance_repeat_is_local','Repeat query seam does not dispatch another Mock HTTP tool or protocol message after first refusal',counts[1]==counts[0] and counts[0]['tools/call']==first_tools)
                check('separate_factory_instance_is_local','Another factory adapter is suppressed before initialize/notification/tool HTTP dispatch',counts[2]==counts[0])
            else:
                check('nonquota_no_latch','Success/transport/timeout do not acquire a quota latch',search._THROTTLED_UNTIL=={})
                check('nonquota_three_seams_three_tools','Three caller attempts dispatch exactly3 tools and2 isolated handshakes; no added native retry',counts[-1]=={'initialize':2,'notifications/initialized':2,'tools/call':3} and not clock.sleeps)
                if mode in {'success','meta-false'}:
                    check('normal_success_native_results','Normal response including explicit metaFalse yields actual native SearchResponse result',all(r['error'] is None and len(r['response']['results'])==1 for r in reports))
                else:
                    check('nonquota_reason_status','Transport/timeout reason retained and statusNone remainsNone',all(r['error'] is not None and r['error']['http_status'] is None and r['error']['reason']==('transport error' if mode=='transport' else 'timeout') for r in reports))
        else:
            def charged():seam.append({'family_attempt':len(seam)+1,'HTTP_count_before':len(server.events)})
            report=await discover_candidates(first,DiscoveryIntent(institution='Synthetic University',domain='example.edu',degree='bachelor',field='computer science'),query_budget=6,fetch=None,on_query_attempt=charged)
            reports={'retrieval':asdict(report)};counts={method:sum(x['method']==method for x in server.events) for method in ['initialize','notifications/initialized','tools/call']}
            if mode in {'meta','http429'}:
                first_tools=2 if mode=='meta' and effective_retry else 1
                check('retrieval_stops_after_first_refused_family','Only first refused query family is charged/sent; remaining original families are not attempted',len(seam)==1 and len(report.queries_run)==1)
                check('retrieval_dispatch_bound_after_original_refusal','No further tool dispatches after the first native search call raises refusal (existing inner retry multiplicity recorded separately)',counts['tools/call']==first_tools)
                check('failure_metadata_not_status_fabrication','Diagnostic carries original refusal category: meta rate limited has no fabricated HTTP429, explicit HTTP429 remainsHTTP429',bool(report.failure_diagnostics) and all(('rate limited' in x and 'HTTP 429' not in x) if mode=='meta' else 'HTTP 429' in x for x in report.failure_diagnostics))
                if mode=='http429':check('existing_429_throttled','ExplicitHTTP429 marks current native report.throttled',report.throttled is True)
            else:
                check('normal_six_attempts','Ordinary successful retrieval keeps six actual original query families and tool calls',len(seam)==6 and counts['tools/call']==6 and len(report.queries_run)==6)
                check('normal_success_no_failure_or_throttle','Success remains native ranked result with no failures/throttle',not report.failure_diagnostics and report.throttled is False and search._THROTTLED_UNTIL=={} and bool(report.candidates))
        check('original_native_methods_unchanged','Actual ExaMcp search/_search_once/_post/_initialize functions never substituted',all(getattr(mcp.ExaMcpSearchProvider,key) is value for key,value in METHODS.items()))
        check('real_network_denied','All owned clients use MockTransport and are closed; all source resolution is synthetic',all(isinstance(client._transport,httpx.MockTransport) for client in clients) and all(client.is_closed for client in clients))
        state=dict(search._THROTTLED_UNTIL)
    after=pins();assert after==PLAN['original_source_sha256']
    result={'scenario':name,'counts':{'PASS':sum(x['status']=='PASS' for x in checks),'RED':sum(x['status']=='RED' for x in checks),'total':len(checks)},'checks':checks,
        'current_source_flags':{'RATE_LIMIT_RETRY':current_retry,'RETRY_429_ONCE':mcp.RETRY_429_ONCE,'MIN_QUERY_INTERVAL_SECONDS':mcp.MIN_QUERY_INTERVAL_SECONDS},'effective_isolated_child_retry':effective_retry,
        'source_sha256_before':PLAN['original_source_sha256'],'source_sha256_after':after,'native_methods':{key:{'qualname':method.__qualname__,'file':inspect.getsourcefile(method)} for key,method in METHODS.items()},
        'query_seam_attempts':seam,'mock_HTTP_counts':counts,'mock_HTTP_original_events':server.events,'outputs':reports,
        'owned_process_latch_after':state,'fake_clock_sleeps':clock.sleeps,'synthetic_resolutions':resolutions,
        'primary_throttle_or_STOP_reset':False,'network_real_DNS_provider_model_Git_app_changes':0,'client_closed':[client.is_closed for client in clients],
        'qualification':'Source-default metadata retryTrue can call native _search_once twice inside each search. This existing retry rule is recorded separately, not silently disabled in native scenarios. No source rule proposed.'}
    path=B/(name+'.original.json');assert not path.exists();path.write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps(result['counts']))
    for row in checks:
        if row['status']=='RED':print(row['case'])
    return 1 if result['counts']['RED'] else 0


if __name__=='__main__':
    raise SystemExit(asyncio.run(main(sys.argv[1])))

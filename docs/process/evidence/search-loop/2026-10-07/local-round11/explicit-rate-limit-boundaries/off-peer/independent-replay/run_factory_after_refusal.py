"""A new factory object created after the actual first refusal, in a fresh child."""
import asyncio
import json
import sys
from types import SimpleNamespace
from unittest.mock import patch

import run_case as c


async def main(mode):
    clock=c.Clock();server=c.Server(mode);clients=[];methods=[];errors=[];checks=[]
    original_client=c.httpx.AsyncClient
    def client_factory(*args,**kwargs):
        client=original_client(*args,transport=c.httpx.MockTransport(server.handle),**kwargs)
        clients.append(client);return client
    def check(name,okay):checks.append({'case':name,'status':'PASS' if okay else 'RED'})
    with patch.object(c.config,'get_settings',lambda:SimpleNamespace(search_provider='exa_mcp')),patch.object(c.httpx,'AsyncClient',client_factory),patch.object(c.search,'time',SimpleNamespace(monotonic=clock.monotonic)),patch.object(c.mcp,'time',SimpleNamespace(monotonic=clock.monotonic)),patch.object(c.mcp,'asyncio',SimpleNamespace(sleep=clock.sleep,Lock=asyncio.Lock,timeout=asyncio.timeout)):
        first=c.search.get_search_provider()
        try:await first.search(query='Public university CS first',domains=['example.edu'])
        except c.SearchUnavailable as exc:errors.append(c.failure(exc))
        before_new=len(server.events)
        second=c.search.get_search_provider()  # Explicitly after first exception and Mock HTTP dispatch.
        created_at=len(server.events)
        try:await second.search(query='Public university CS separate later caller',domains=['example.edu'])
        except c.SearchUnavailable as exc:errors.append(c.failure(exc))
        check('original_reason_status_preserved',len(errors)==2 and all(x['http_status']==(None if mode=='meta' else 429) and x['reason']==('rate limited' if mode=='meta' else None) for x in errors))
        check('second_factory_genuinely_after_refusal',bool(errors) and before_new>0 and created_at==before_new and first is not second and first.inner is not second.inner)
        check('new_factory_process_stop_suppresses_ALL_HTTP',len(server.events)==before_new)
        check('explicit_refusal_latch_recorded',bool(c.search._THROTTLED_UNTIL.get('exa_mcp')))
        check('original_search_methods_unchanged',all(getattr(c.mcp.ExaMcpSearchProvider,k) is v for k,v in c.METHODS.items()))
        check('all_mock_clients_closed',all(isinstance(client._transport,c.httpx.MockTransport) and client.is_closed for client in clients))
        state=dict(c.search._THROTTLED_UNTIL)
    assert c.pins()==c.PLAN['original_source_sha256']
    value={'mode':mode,'counts':{'PASS':sum(x['status']=='PASS' for x in checks),'RED':sum(x['status']=='RED' for x in checks),'total':len(checks)},'checks':checks,
        'first_query_actual_Mock_HTTP_count':before_new,'new_factory_created_after_HTTP_count':created_at,'all_actual_Mock_HTTP_count':len(server.events),
        'method_counts':{key:sum(x['method']==key for x in server.events) for key in ['initialize','notifications/initialized','tools/call']},
        'errors':errors,'mock_HTTP_original_events':server.events,'process_latch':state,'sleeps':clock.sleeps,
        'source_sha256_before':c.PLAN['original_source_sha256'],'source_sha256_after':c.pins(),'real_calls_or_source_changes':0,'reset_called':False}
    target=c.B/(mode+'.factory-created-after-refusal.original.json');assert not target.exists()
    target.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value['counts']))
    return 1 if value['counts']['RED'] else 0


if __name__=='__main__':raise SystemExit(asyncio.run(main(sys.argv[1])))

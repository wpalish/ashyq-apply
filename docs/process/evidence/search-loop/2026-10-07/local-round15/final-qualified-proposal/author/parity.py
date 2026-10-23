import asyncio,json,sys,socket
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,UTC
from evaluation.research.expert import controller,selector
from evaluation.research.expert.models import Action,ExpertTrace
from evaluation.research.expert.packet import digest
from evaluation.research.expert.journal import AcceptedJournal
socket.socket.connect=lambda *_a,**_k:(_ for _ in ()).throw(AssertionError('denied network'))
socket.getaddrinfo=lambda *_a,**_k:(_ for _ in ()).throw(AssertionError('denied DNS'))
fixed=datetime(2026,1,1,tzinfo=UTC)
async def get(url):return SimpleNamespace(url=url,final_url=url,ok=True,outcome='ok',status_code=200,content_type='text/plain',content=b'Synthetic legacy admissions source',error='',from_cache=False,fetch_tier='http',fetched_at=fixed)
plan=dict(case_id='synthetic',provider='exa_mcp',strict_budget=True,max_calls=60,max_search_queries=6,max_ms=120000,official_domains=['example.edu'],budget_origin='independent_full_budget',actions=[dict(tool='fetcher',url='https://example.edu/admissions')])
root=Path(sys.argv[1]);root.mkdir(parents=True)
summary=asyncio.run(controller.execute(plan,root/'raw',get=get,search=None,provider_name='exa_mcp',now=lambda:fixed,monotonic=lambda:1.0))
r=summary['actions'][0]
a=Action(step=1,at=r['at'],observed_before='Read source.',observed_from_step=None,tool=r['tool'],action='Read source.',outcome_status=r['outcome_status'],outcome=r['outcome'],stage='page_understanding',policy_mode=r['policy_mode'],url='https://example.edu/admissions',final_url=r['final_url'],request=r['request'],raw_log_path=r['raw_log_path'],raw_log_sha256=r['raw_log_sha256'],elapsed_ms=r['elapsed_ms'],elapsed_ms_cumulative=r['elapsed_ms_cumulative'],fetcher_calls_cumulative=r['fetcher_calls_cumulative'],search_queries_cumulative=r['search_queries_cumulative'])
packet={'schema_version':'1','baseline_budget':{'max_fetcher_calls':60,'max_search_queries':6,'max_elapsed_ms':120000}}
t=ExpertTrace(case_id='synthetic',packet_sha256=digest(packet),baseline_pipeline_sha='synthetic-source',max_fetcher_calls=60,max_search_queries=6,max_elapsed_ms=120000,initial_fetcher_calls=0,initial_elapsed_ms=0,started_at=fixed,ended_at=fixed,actions=[a])
try:selector.select(None,None,None,{},timeout_seconds=56)
except ValueError as exc:diagnostic=str(exc)
out=dict(summary=summary,trace=t.model_dump(mode='json'),trace_digest=digest(t.model_dump(mode='json')),packet_digest=digest(packet),journal=AcceptedJournal.initial().snapshot(),selector_legacy_error=diagnostic)
(root/'parity.original.json').write_text(json.dumps(out,sort_keys=True,indent=2));print(json.dumps({'raws':len(list((root/'raw').glob('*.json'))),'trace_digest':out['trace_digest']}))

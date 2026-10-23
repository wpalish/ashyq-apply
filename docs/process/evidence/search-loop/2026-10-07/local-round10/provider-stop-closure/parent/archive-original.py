# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
R=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply');W=R.parent;P=W/'local-round10/genuine-baseline'
D=R/'docs/process/evidence/search-loop/2026-10-07/local-round10/provider-stop-closure'
assert not D.exists();D.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((P/'PLAN.json').read_text());full=json.loads((Path(plan['full_gate_run'])/'summary.json').read_text())
errors=[];verified=0
for name,digest in full['source']['files'].items():
 if name.startswith(('backend/app/','backend/tests/','backend/evaluation/','backend/scripts/','frontend/')):
  for base in [R,Path(plan['source_snapshot'])]:
   if sha(base/name)!=digest:errors.append(str(base/name))
  verified+=1
assert verified==999 and not errors
assert sha(P/'execute_baseline.py')=='4fa670fb54d6f62c296b68e682c2f46417cf02ba0daf75deb69f329be32f269b'
assert sha(P/'PLAN.json')=='031ba703f3fa41079bb59650322af8505d32eb6bd4094ebdb538f42fb8b7e078'
assert sha(P/'score_after_collection.py')=='7d183e1781b458d3ec5c4cd130963ff59547116c5440d43aa636c7098d4814a9'
stop=Path(plan['stop_file']);stopdata=json.loads(stop.read_text());assert stopdata['case_id']=='kaist' and stopdata['failure_reason']=='rate limited'
execution=json.loads((P/'execution-receipt.json').read_text());assert execution['status']=='GLOBAL_PROVIDER_STOP_UNSCORED'
files={}
def cp(origin,rel,digest=None):
 assert origin.is_file() and not origin.is_symlink(),origin
 if digest:assert sha(origin)==digest,origin
 assert origin.suffix in ('.json','.py','.log','.md','.diff','.txt','.html','.xml'),origin
 data=origin.read_bytes();dest=D/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 assert sha(dest)==sha(origin)
 files[rel]={'original':str(origin),'sha256':sha(origin),'bytes':len(data)}
cp(stop,'provider-STOP.original.json')
for p in sorted(P.iterdir()):
 if p.is_file() and p.suffix in ('.json','.py','.log'):cp(p,'controller/'+p.name)
rows=[]
for case in plan['cases']:
 for p in sorted((P/case).rglob('*')):
  if p.is_file() and p.suffix in ('.json','.log'):cp(p,'captures/'+str(p.relative_to(P)))
 b=json.loads(next((P/case).rglob(case+'.budget.json')).read_text());o=json.loads(next((P/case).rglob(case+'.json')).read_text())
 rows.append({'case_id':case,'fetcher_calls':b['fetcher_calls'],'search_queries':b['search_queries'],'elapsed_ms':b['elapsed_ms'],'programme_url_records':len(o['programme_urls']),'prediction_records':len(o['predictions']),'provider_failure':b['provider_failure'],'capture_kind':execution['capture_kinds'].get(case,'PROVIDER_FAILURE_NOT_ADMITTED')})
reviews=[(W/'local-round10/reviews/expert_b-scoring-preparation','MANIFEST.original.json','score-review-original'),(W/'local-round10/reviews/expert_b-scoring-closure-v2','MANIFEST.json','score-review-final'),(W/'local-round9/b-ielts-v5-review','MANIFEST.json','ielts-v5-rejection'),(W/'local-round10/a-confirmed-source-checkpoint-plan','ready-manifest.json','durable-partial-contract')]
for own,manifest,label in reviews:
 m=json.loads((own/manifest).read_text());cp(own/manifest,label+'/'+manifest)
 for rel,v in m['files'].items():cp(own/rel,label+'/'+rel,v if isinstance(v,str) else v.get('sha256'))
cp(Path(__file__),'parent/archive-closure.py')
totals={k:sum(v[k] for v in rows) for k in ['fetcher_calls','search_queries','elapsed_ms','programme_url_records','prediction_records']}
summary=json.loads((P/'summary.json').read_text())
receipt={'status':'GLOBAL_PROVIDER_STOP_UNSCORED','archived_at_utc':datetime.now(timezone.utc).isoformat(),'collection_started_at':summary['started_at'],'collection_finished_at':summary['finished_at'],'source_head':plan['source_head'],'snapshot_sha256':plan['source_tree_sha256'],'source_paths_reverified':verified,'changed_executable_paths':errors,'stop_original_sha256':sha(stop),'provider_refusal':stopdata,'controller_exit_code':2,'cases_attempted':10,'captures_admitted_before_stop':9,'completed_job_captures':6,'bounded_partial_job_captures':3,'provider_failure_captures_not_admitted':1,'physical_counters_not_quality_scores':totals,'cases':rows,'files':files,'selected_files':len(files),'selected_bytes':sum(v['bytes'] for v in files.values()),'scoring_executed':False,'reviewed_labels_read':False,'hosted_ci_started':False,'production_changed':False,'limits':['rate limited is the preserved provider reason; HTTP status null is not proven HTTP429 or proven account-balance exhaustion','exit0 child logs mean capture persisted, not Job success or quality acceptance','all physical totals include failed KAIST; no precision/core completeness/paired gain/launch percent is claimed','source counts are Fetcher.get and charged search seam queries, not unique pages or independent HTTP/provider billable requests','capture is local Mac isolated SQLite, not Fly or PostgreSQL canary','only selected public JSON/log/py/HTML/XML originals are archived; no runtime databases, env, private Git or browser storage','score controller is static-reviewed but unexecuted; stopped cohort is never eligible','no retry/reset/provider/model switch/purchase or old cohort resume; only offline saved-source work remains authorized']}
(D/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
entry=f'''**[search-genuine-baseline] GLOBAL PROVIDER STOP / UNSCORED, {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MUTC')}.** Fresh collection01:17:02–01:33:08UTC:10attempted,9admittedcaptures=6completedJobs+3boundedpartialJobs; KAIST first Exa MCP refusal 'rate limited' at01:33:07UTC, HTTPstatusnull. Physical totals391Fetcher.get/56chargedqueries/108predictionrecords/14programmeURLrecords across6cases, NOT quality scores. Exact STOP retained SHA `{sha(stop)}`. Closure archive `{D.relative_to(R)}/receipt.json` SHA `{sha(D/'receipt.json')}`: {len(files)} selected originals/{receipt['selected_bytes']} bytes. All999 executable paths reverified unchanged from full7c74/snapshot19f349; full13/13/4292unique eachDB/95.25% remains technical proof. Exit2controller; childexit0 merely preservedcaptures. No labels read or score executed; precision/core completeness/default/launch unknown. Owner attachment§7 requires global live STOP: no retry/reset/switch/purchase/resume. Next: A strict own-programme/degree early-return proof and B Aalto CLASSIFIER/EXTRACTOR/JS saved-byte diagnosis only, then conservative negative controls and review. External scorer7d183e17 static15/15PASS remains unexecuted; IELTSv5 independent7PASS/11RED rejected. Historical READY --execute instructions below are superseded and must not run.'''
p=R/'docs/process/HANDOFF.md';s=p.read_text()
for section in [1,2,3,5,6,7,8,9]:
 marker=next(l for l in s.splitlines() if l.startswith(f'## {section}. '));s=s.replace(marker+'\n',marker+'\n\n'+entry+'\n',1)
s+=f'\n- {datetime.now(timezone.utc).isoformat()} — gpt-6-astra: [search-genuine-baseline] 89b06eae → UNSCORED closure pending commit; exact provider STOP preserved, live globally stopped, offline A/B work only.\n';p.write_text(s)
for name in ['CLAUDE_SEARCH_RELAY_2026-10-07.md','SEARCH_LOOP_LEDGER_2026-10-07.md']:
 p=R/'docs/process'/name;s=p.read_text();i=s.find('\n');s=s[:i+1]+'\n'+entry+'\n'+s[i+1:];p.write_text(s)
print(json.dumps({'closure_receipt_sha256':sha(D/'receipt.json'),'selected_files':len(files),'selected_bytes':receipt['selected_bytes'],'totals':totals,'source_paths_reverified':verified,'STOP_sha256':sha(stop)},ensure_ascii=False))

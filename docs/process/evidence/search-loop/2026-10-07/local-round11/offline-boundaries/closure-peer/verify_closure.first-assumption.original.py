"""Independent offline archive/counter peer check. Standard library only."""
import hashlib,json
from collections import Counter
from datetime import datetime
from pathlib import Path

B=Path(__file__).resolve().parent
plan=json.loads((B/'PLAN.json').read_text());D=Path(plan['closure']);R=json.loads((B/'closure-receipt.original.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(D/'receipt.json')==plan['receipt_sha256']
checks={};file_checks=[]
for rel,entry in R['files'].items():
 p=D/rel;origin=Path(entry['original']);digest=sha(p);size=p.stat().st_size
 assert p.is_file() and not p.is_symlink()
 assert digest==entry['sha256'] and size==entry['bytes'],rel
 assert origin.is_file() and sha(origin)==digest and origin.stat().st_size==size,('original_drift',rel)
 file_checks.append({'file':rel,'sha256':digest,'bytes':size,'archive_matches':True,'original_matches':True})
actual={str(p.relative_to(D)) for p in D.rglob('*') if p.is_file()}
assert actual==set(R['files'])|{'receipt.json'}
assert len(file_checks)==R['selected_files']==332
assert sum(x['bytes'] for x in file_checks)==R['selected_bytes']==37160511
checks['selected332_archived_and_original_hash_and_size']=True
checks['no_unlisted_archived_file_except_receipt']=True
stop=json.loads((D/'provider-STOP.original.json').read_text());assert stop==R['provider_refusal'];assert sha(D/'provider-STOP.original.json')==R['stop_original_sha256'];assert stop=={'case_id':'kaist','provider':'exa_mcp','http_status':None,'failure_reason':'rate limited','time':'2026-10-08T01:33:07.997034+00:00'}
ctrlplan=json.loads((D/'controller/PLAN.json').read_text());execution=json.loads((D/'controller/execution-receipt.json').read_text())
assert sha(Path(ctrlplan['stop_file']))==R['stop_original_sha256']
assert execution['status']==R['status']=='GLOBAL_PROVIDER_STOP_UNSCORED';assert len(execution['attempted'])==R['cases_attempted']==10 and execution['attempted']==ctrlplan['cases'];assert execution['remaining']==[]
assert len(execution['capture_kinds'])==R['captures_admitted_before_stop']==9 and 'kaist' not in execution['capture_kinds']
rows=[]
for expected in R['cases']:
 case=expected['case_id'];case_dir=D/'captures'/case
 def one(name):
  found=list(case_dir.rglob(name));assert len(found)==1,(case,name,len(found));return found[0]
 b=json.loads(one(case+'.budget.json').read_text());o=json.loads(one(case+'.json').read_text());raw=json.loads(one(case+'.raw.json').read_text());cap=json.loads(one('capture.json').read_text());job=raw['canary']['job_protocol']
 for key,limit in [('fetcher_calls',60),('search_queries',6),('elapsed_ms',120000)]:assert type(b[key]) is int and 0<=b[key]<=limit
 assert b['strict_expert_budget'] is True and b['max_fetcher_calls']==60 and b['max_search_queries']==6 and b['max_active_seconds']==120 and b['source_work_deadline_ms']==119000 and b['finalization_reserve_ms']==1000
 assert o['case_id']==case and o['telemetry']['http_fetches']==b['fetcher_calls'] and o['telemetry']['search_calls']==b['search_queries']
 assert type(o['programme_urls']) is list and type(o['predictions']) is list
 assert cap['mode']=='live' and cap['pipeline_sha']==R['source_head']
 assert cap['config']['fenced_research_job'] is True and cap['config']['university_read_budget'] is False and cap['config']['strict_expert_budget'] is True
 assert cap['observations'][0]==o
 assert job['kind']=='genuine-research-job' and job['native_enabled'] is False and job['native_ledger'] is None
 assert type(job['claim_token']) is int and job['claim_token']==1 and type(job['lease_token']) is int and job['lease_token']==1
 assert job['heartbeat_done']==[True] and job['heartbeat_tasks']==1 and job['heartbeat_cancelled']==[False]
 for key in ['browser_fetches','pdf_fetches','model_input_tokens','jev_input_tokens']:assert o['telemetry'][key]==0
 kind=execution['capture_kinds'].get(case,'PROVIDER_FAILURE_NOT_ADMITTED')
 if kind=='COMPLETED_JOB_CAPTURE':assert job['job_status']=='succeeded' and job['worker_jobs_done']==1 and not o['error'] and not b['provider_failure']
 elif kind.startswith('BOUNDED_TERMINAL_PARTIAL_JOB_'):assert job['job_status']==kind.rsplit('_',1)[-1] and job['worker_jobs_done']==0 and o['error'] and not b['provider_failure']
 else:assert case=='kaist' and job['job_status']=='queued' and job['worker_jobs_done']==0 and b['stop_reason']=='provider_failure' and b['provider_failure']['reason']==stop['failure_reason'] and b['provider_failure']['http_status'] is None
 row={'case_id':case,'fetcher_calls':b['fetcher_calls'],'search_queries':b['search_queries'],'elapsed_ms':b['elapsed_ms'],'programme_url_records':len(o['programme_urls']),'prediction_records':len(o['predictions']),'provider_failure':b['provider_failure'],'capture_kind':kind}
 assert row==expected,(case,row,expected)
 rows.append({**row,'native_job_status':job['job_status'],'worker_jobs_done':job['worker_jobs_done'],'observation_error_present':bool(o['error']),'raw_semantic_claim_or_prediction_values_not_adjudicated':True})
count=Counter(x['capture_kind'] for x in rows)
assert count['COMPLETED_JOB_CAPTURE']==R['completed_job_captures']==6
assert sum(v for k,v in count.items() if k.startswith('BOUNDED_TERMINAL_PARTIAL_JOB_'))==R['bounded_partial_job_captures']==3
assert count['PROVIDER_FAILURE_NOT_ADMITTED']==R['provider_failure_captures_not_admitted']==1
checks['native_status_and_capture_split_6_3_1']=True
keys=['fetcher_calls','search_queries','elapsed_ms','programme_url_records','prediction_records'];totals={k:sum(x[k] for x in rows) for k in keys};assert totals==R['physical_counters_not_quality_scores']=={'fetcher_calls':391,'search_queries':56,'elapsed_ms':956979,'programme_url_records':14,'prediction_records':108}
checks['physical_totals_391_56_108_14']=True
checks['sticky_stop_original_and_live_copy_identical']=True
fullpath=Path(ctrlplan['full_gate_run']);full=json.loads((fullpath/'summary.json').read_text());manifest=json.loads((fullpath/'source-manifest.json').read_text());f={k:v for k,v in full['source']['files'].items() if k.startswith(('backend/app/','backend/tests/','backend/evaluation/','backend/scripts/','frontend/'))}
assert len(f)==R['source_paths_reverified']==999
assert all(manifest['files'].get(k)==v for k,v in f.items())
assert full['source']['source_head']==manifest['source_head']==R['source_head']==execution['source_head']==ctrlplan['source_head']
assert full['source']['source_tree_sha256']==manifest['source_tree_sha256']==R['snapshot_sha256']==execution['source_tree_sha256']==ctrlplan['source_tree_sha256']
assert R['changed_executable_paths']==[]
assert full['status']=='passed' and full['suite']=='full' and len(full['steps'])==13 and all(s['exit_code']==0 for s in full['steps'])
for pre in ['preflight-ready.json','preflight-before-execution.json']:
 q=json.loads((D/'controller'/pre).read_text());assert q['source_head']==R['source_head'] and q['source_tree_sha256']==R['snapshot_sha256'] and q['source_paths_verified']==999
checks['same999_saved_full_summary_and_source_manifest_pins']=True
checks['saved_full13technical_gate_pass_not_quality']=True
assert all(R[k] is False for k in ['scoring_executed','reviewed_labels_read','hosted_ci_started','production_changed'])
assert not any('/score-' in n and n.endswith('results.json') for n in R['files'])
pr=(B/'pr-body.original.md').read_text();assert 'GLOBAL_PROVIDER_STOP_UNSCORED' in pr and 'never executed' in pr and 'not achieved' in pr and 'No score, semantic label read' in pr and 'broad diff --check reports original trailing whitespace' in pr
checks['pr_no_quality_acceptance_and_whitespace_limits_explicit']=True
checks['root_recorded_no_labels_score_or_resumed_collection']=True
assert datetime.fromisoformat(stop['time'])<datetime.fromisoformat(R['collection_finished_at'])<datetime.fromisoformat(R['archived_at_utc'])
assert len(rows)==10 and rows[-1]['case_id']=='kaist' and ctrlplan['cases'][-1]=='kaist'
checks['stop_last_case_no_post_refusal_case_in_saved_sequence']=True
(B/'file-checks.json').write_text(json.dumps({'selected_file_checks':file_checks},indent=2)+'\n')
(B/'physical-counters-and-statuses.json').write_text(json.dumps({'cases':rows,'totals':totals,'counts':dict(count)},indent=2)+'\n')
(B/'saved-source-pins.checked.json').write_text(json.dumps({'full_summary_original':str(fullpath/'summary.json'),'full_summary_sha256':sha(fullpath/'summary.json'),'source_manifest_original':str(fullpath/'source-manifest.json'),'source_manifest_sha256':sha(fullpath/'source-manifest.json'),'source_head':R['source_head'],'source_tree_sha256':R['snapshot_sha256'],'saved_full13_steps_exit0':True,'executable_files999_recorded_digests':f,'comparison_basis':'Saved full summary↔saved source manifest↔recorded preflight/execution/closure. No repository/fresh process/source/Git verification or corpus semantic reads.'},indent=2)+'\n')
receipt={'verdict':'ACCEPTED_UNSCORED_CLOSURE_ONLY','root_receipt_sha256':plan['receipt_sha256'],'checks':checks,'selected_files':332,'selected_bytes':37160511,'source_pins_compared':999,'stop_sha256':R['stop_original_sha256'],'stop':stop,'attempted':10,'admitted':9,'completed':6,'bounded_partial':3,'unadmitted_refusal':1,'physical_counters_not_quality_scores':totals,'pr_body_sha256':plan['pr_body_sha256'],'runtime_actions':{'main_preflight_driver_scorer_import_or_execution':0,'network_model_provider_calls':0,'repo_source_Git_STOP_mutations':0,'semantic_gold_label_reads':0},'limits':['No quality score or semantic adjudication; counts only lengths and physical meters.','No broad diff --check PASS; archived original whitespace preserved.','No fresh 999-file executable/Git proof: same saved fullsource digests and recorded reverify receipts verified only.','No post-refusal case in retained collection; independent global audit of every later machine process was not performed.','scoring_executed/reviewed_labels_read/production_changed are preserved owner/controller declarations consistent with archive, not independent history reconstruction.','HTTPstatus null does not prove HTTP429/account balance.']}
(B/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ('checks','limits')},indent=2));print('checks',len(checks),'PASS')

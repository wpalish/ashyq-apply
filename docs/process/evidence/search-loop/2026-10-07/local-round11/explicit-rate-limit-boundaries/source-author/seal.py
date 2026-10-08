from __future__ import annotations
from pathlib import Path
from datetime import UTC,datetime
import hashlib,json,difflib
B=Path(__file__).resolve().parent
REPO=B.parents[1]/'ashyq-apply/backend'
plan=json.loads((B/'PLAN.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert {r:sha(REPO/r) for r in plan['source_sha256']}==plan['source_sha256']
files=plan['source_files']
manifest={'original':plan['source_sha256'],'proposed':{r:sha(B/'proposed'/r) for r in files},'source_flags_unchanged':{'RATE_LIMIT_RETRY':True,'RETRY_429_ONCE':False,'MIN_QUERY_INTERVAL_SECONDS':0.0,'THROTTLE_COOLDOWN_SECONDS':300.0},'methods_unchanged':['ExaMcpSearchProvider.search','ExaMcpSearchProvider._search_once','ExaMcpSearchProvider._post','ExaMcpSearchProvider._initialize'],'execution': 'normal app dependency imports; only3external target modules substituted in fresh child, never search methods'}
(B/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
patch=''.join(''.join(difflib.unified_diff((B/'original'/r).read_text().splitlines(keepends=True),(B/'proposed'/r).read_text().splitlines(keepends=True),fromfile='a/backend/'+r,tofile='b/backend/'+r)) for r in files)
(B/'explicit-rate-limit.patch').write_text(patch)
final=json.loads((B/'attempt3-final/execution.json').read_text())
assert final['counts']['on']=={'PASS':171,'RED':0,'exceptions':0,'total':171}
assert len(final['whole_output_equality'])==15 and all(r['status']=='PASS' for r in final['whole_output_equality'])
for p in (B/'pytest-controls').rglob('*.on.json'):
 d=json.loads(p.read_text());assert d['counts']['RED']==0 and d['proposal_source_before']==manifest['proposed']==d['proposal_source_after']
assert sum(1 for p in (B/'pytest-controls/enabled').rglob('*.on.json'))==37
assert sum(1 for p in (B/'pytest-controls/equality').rglob('*.json'))==30
for p in (B/'attempt3-final').glob('*.json'):
 if p.name=='execution.json':continue
 d=json.loads(p.read_text());assert d['proposal_source_before']==manifest['proposed']==d['proposal_source_after']
receipt={'sealed_utc':datetime.now(UTC).isoformat(),'status':'EXTERNAL_PROPOSAL_READY_FOR_INDEPENDENT_PEER_NOT_APPLIED',
 'plan_sha256':sha(B/'PLAN.json'),'addendum_sha256':sha(B/'plan-addendum.json'),'source_manifest_sha256':sha(B/'source-manifest.json'),'patch_sha256':sha(B/'explicit-rate-limit.patch'),'proposed_source_sha256':manifest['proposed'],
 'test_sha256':sha(B/'test_explicit_rate_limit.py'),'child_sha256':sha(B/'run_control.py'),'executor_sha256':sha(B/'execute_controls.py'),
 'final_source_replay':final['counts'],'normal_full_output_dispatch_equality':{'PASS':15,'RED':0},
 'pytest':{'passed':52,'failed':0,'skipped':0,'exit':0,'node_distribution':{'enabled':37,'whole_normal_equality':15},'log_sha256':sha(B/'pytest-final.log'),'qualification':'52 completed dots and exit0; 37 fresh ONchildren plus15fresh OFF/ON comparisons. This repeats the same bounded scenario matrix, not52 independent new defects.'},
 'static':{'Ruff':(B/'ruff-final.log').read_text().strip(),'mypy':(B/'mypy-final.log').read_text().strip(),'format':(B/'format-final.log').read_text().strip()},
 'historical':{'attempt1':{'on':{'PASS':125,'RED':0,'fixture_exceptions':6},'off':{'PASS':114,'RED':11,'fixture_exceptions':6},'qualification':'PageCategory is a namespace, notEnum; same6caller fixtures failbeforetargetseam inbothmodes. Original source/tests/logs preserved.'},'attempt2':{'on':{'PASS':156,'RED':0,'exceptions':0},'off':{'PASS':138,'RED':18,'exceptions':0},'qualification':'Before finalgrammar/comment fix and3additionalnative controls; sourcepins saved separately, never relabeled exactfinalproof.'}},
 'native_HTTP_examples':{},'zero_actual_network_provider_model_Git_app_STOP_mutations':True,
 'limits':['Process-local sequential latch, not cross-process or retroactive suppression of already-started concurrent requests.','Native approved RATE_LIMIT_RETRYTrue still2tools insidefirstfailed metadata search; isolatedFalse control1tool explicitlyrecorded.','Float-only fallback is knownoldHTTP429 teststate. Currentmetadata stampedNone never becomes429.','Native private origin stores only deadline/status/fixedenum, notvendor text. Rawstringreason andvendor-onlytext never triggernewpredicate.','No API/schema/budget/timeout/retryflag/retention/scopehelper/outerSTOP change; no quality gain or launch acceptance claimed.','Existing broad retrieval hop catches and coverage/query-field planned semantics are unchanged; trace.search_queries_sent proveschargedseams, notvendor dispatch.','Actual provider protocol/token/account/quota access nottested; officialpagefacts none.','Peer review and parentintegration are still required; OFFproof original4da30620 untouched.']}
for name in ['factory-meta','factory-no-retry','factory-http429','retrieval-meta','retrieval-meta-unwrapped','retrieval-http429','native-expiry','native-recovery-meta','caller-single-meta','caller-multi-meta']:
 d=json.loads((B/'attempt3-final'/f'{name}.on.json').read_text());receipt['native_HTTP_examples'][name]={'HTTP':d['mock_HTTP_counts'],'query_seams':len(d['query_seam_attempts']),'sleep':d['fake_clock_sleeps']}
(B/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
ready={}
for p in sorted(B.rglob('*')):
 if not p.is_file() or any(part in {'mypy-cache','__pycache__','.pytest_cache'} for part in p.relative_to(B).parts):continue
 if p.name=='ready-manifest.json':continue
 ready[str(p.relative_to(B))]={'sha256':sha(p),'bytes':p.stat().st_size}
(B/'ready-manifest.json').write_text(json.dumps({'status':receipt['status'],'files':ready,'selected_files':len(ready),'selected_bytes':sum(r['bytes'] for r in ready.values()),'excluded':['mypy-cache','__pycache__','.pytest_cache','DB/PGDATA/env none present'],'app_original_hashes_after':{r:sha(REPO/r) for r in plan['source_sha256']}},indent=2)+'\n')
print(json.dumps({'ready':sha(B/'ready-manifest.json'),'receipt':sha(B/'receipt.json'),'patch':receipt['patch_sha256'],'source':manifest['proposed'],'tests':receipt['test_sha256'],'files':len(ready),'bytes':sum(r['bytes'] for r in ready.values())},indent=2))

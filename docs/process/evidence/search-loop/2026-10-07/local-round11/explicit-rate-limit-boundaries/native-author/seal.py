from pathlib import Path
from datetime import UTC,datetime
import ast,difflib,hashlib,json,xml.etree.ElementTree as ET
B=Path(__file__).resolve().parent
R=B.parents[1]/'ashyq-apply/backend'
P=B.parent/'a-explicit-rate-limit-proposal'
plan=json.loads((B/'PLAN.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P/'ready-manifest.json')==plan['source_proposal_ready_sha256']
assert {r:sha(R/r) for r in plan['app_original_sha256']}==plan['app_original_sha256']
assert {r:sha(R/r) for r in plan['ownership']}==plan['tests_original_sha256']
assert {r:sha(B/'replay-source'/r) for r in plan['source_proposal_sha256']}==plan['source_proposal_sha256']
tests={r:sha(B/'proposed'/r) for r in plan['ownership']}
for lane in ['off','on']:
 d=json.loads((B/f'attempt1-{lane}.json').read_text())
 assert d['original_app_before']==d['original_app_after']==plan['app_original_sha256']
 assert d['proposal_app_before']==d['proposal_app_after']==plan['source_proposal_sha256']
 assert d['test_before']==d['test_after']==tests
on=json.loads((B/'attempt1-on.json').read_text());off=json.loads((B/'attempt1-off.json').read_text())
assert on['pytest']=={'passed':90,'failed':0,'skipped':0,'error':0} and on['exit']==0
assert off['pytest']=={'passed':78,'failed':12,'skipped':0,'error':0} and off['exit']==1
old_names={n.name for r in plan['ownership'] for n in ast.parse((B/'original'/r).read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')}
rename={'test_a_throttled_run_records_status_and_incomplete_rate_limit_stop':'test_a_throttled_run_records_a_quota_stop_not_a_miss'}
xml=ET.parse(B/'attempt1-on.xml');cases=list(xml.iter('testcase'))
legacy=sum(rename.get(c.get('name').split('[')[0],c.get('name').split('[')[0]) in old_names for c in cases)
assert legacy==70 and len(cases)==90
patch=''.join(''.join(difflib.unified_diff((B/'original'/r).read_text().splitlines(keepends=True),(B/'proposed'/r).read_text().splitlines(keepends=True),fromfile='a/backend/'+r,tofile='b/backend/'+r)) for r in plan['ownership'])
(B/'native-tests.patch').write_text(patch)
imports={'ordinary_dependencies':plan['app_original_sha256'],'only_external_replay_modules':plan['source_proposal_sha256'],'test_paths':plan['ownership'],'original_tests':plan['tests_original_sha256'],'proposed_tests':tests,'runtime_proof':{'on':on['target_files'],'off':off['target_files'],'native_search_method_identity_unchanged':on['native_method_identity_unchanged'] and off['native_method_identity_unchanged']},'loader_is_external_only_not_in_patch':True}
(B/'imports-manifest.json').write_text(json.dumps(imports,indent=2)+'\n')
receipt={'sealed_utc':datetime.now(UTC).isoformat(),'status':'NATIVE_TEST_PROPOSAL_READY_FOR_PEER_NOT_APPLIED','plan_sha256':sha(B/'PLAN.json'),'source_ready_sha256':plan['source_proposal_ready_sha256'],'source_proposal_sha256':plan['source_proposal_sha256'],'patch_sha256':sha(B/'native-tests.patch'),'proposed_test_sha256':tests,'imports_manifest_sha256':sha(B/'imports-manifest.json'),'focused_OFF':off['pytest'],'focused_ON':on['pytest'],'collected':90,'test_distribution':{'existing_expanded_controls':70,'new_parameterized_controls':20,'total':90},'off_failed_nodes':[c.get('name') for c in ET.parse(B/'attempt1-off.xml').iter('testcase') if c.find('failure') is not None],'original_failures_preserved':True,'packaging_count_correction':'Initial mental count69/21 failedtheJUnitclassificationassert; immutableJUnitshows70/20. Originalseal/report preserved; no testcaseorresult changed.','static':{'Ruff':(B/'ruff-final.log').read_text().strip(),'mypy':(B/'mypy-initial.log').read_text().strip(),'mypy_qualification':'Configured check passes3testfiles; notes explicitly retain untyped-function-body checking limits.','initial_lint':'3 safe import-sort errors preserved, all safelyfixed before first focused replay.'},'qualifications':['Only3testcopies are in the proposed patch; externalconftest/sourcecopies/loaders are reproducibility evidence, not proposedrepochanges.','Shared factory/nativeMCP methods run with real JSONRPC HTTP MockTransport; no search/search_once/post methodoverride.','Source-default RATE_LIMIT_RETRY=True2tools beforeescapedfailure preserved; explicitisolatedFalse1tool; postescape0extraHTTP; recoverednative retry doesnotlatch.','Same ordinary child testresetcontract as repositoryconftest; primaryprocess throttle/STOP untouched.','CurrentOFF baseline12RED are expected semantic failures including2known429 generic-message relocation assertions, not12newindependentproductiondefects.','Lowlevel scriptedproviders testlatch/query accounting, notnativeExa I/O; nativefactoryintegration separatelypreserved.','No budgets,guard,API,timeout,retrydefault,wholefullsuite,gold/scoring/live/provider/model/remoteDB touched.','Root integration and B peer stillrequired; original source/test files and sealedsource133b unchanged.'],'actual_network_model_provider_app_Git_STOP_mutations':0}
(B/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
selected={}
for p in sorted(B.rglob('*')):
 if not p.is_file() or any(s in {'mypy-cache','__pycache__','.pytest_cache'} for s in p.relative_to(B).parts) or p.name=='ready-manifest.json':continue
 selected[str(p.relative_to(B))]={'sha256':sha(p),'bytes':p.stat().st_size}
(B/'ready-manifest.json').write_text(json.dumps({'status':receipt['status'],'files':selected,'selected_files':len(selected),'selected_bytes':sum(v['bytes'] for v in selected.values()),'excluded':['mypy-cache','__pycache__','.pytest_cache','DB/env none present']},indent=2)+'\n')
print(json.dumps({'ready':sha(B/'ready-manifest.json'),'receipt':sha(B/'receipt.json'),'patch':sha(B/'native-tests.patch'),'tests':tests,'files':len(selected),'bytes':sum(v['bytes'] for v in selected.values())},indent=2))

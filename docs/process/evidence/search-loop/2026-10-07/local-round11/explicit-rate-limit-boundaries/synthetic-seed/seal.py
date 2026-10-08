from pathlib import Path
from datetime import UTC,datetime
import hashlib,json
B=Path(__file__).resolve().parent
P=json.loads((B/'PLAN.json').read_text());S=Path(P['snapshot'])
R=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prefix=json.loads((B/'verified-source-prefix.json').read_text())
assert {r:sha(S/r) for r in prefix}==prefix
app={r:h for r,h in prefix.items() if r.startswith('backend/app/')}
assert {r:sha(R/r) for r in app}==app
assert sha(Path(P['fullLOCAL_run'])/'source-manifest.json')==P['source_manifest_sha256']
assert sha(Path(P['safe_env_module']))==P['safe_env_module_sha256']
commands=json.loads((B/'commands.original.json').read_text());second=json.loads((B/'commands-inspection2.original.json').read_text())
assert [r['exit'] for r in commands]==[0,0,0,1]
assert len(second)==1 and second[0]['exit']==0
checks={name:json.loads((B/(name+'.execution.json')).read_text()) for name in ['heads','migrate','seed','inspect','inspect2']}
assert all(not r['network_attempts'] and r['snapshot_prefix_999_before_after_equal'] for r in checks.values())
inspection=json.loads((B/'inspection2.original.json').read_text())
assert inspection['heads']==inspection['database_revisions']==['d8e412c6a901']
assert inspection['first']=='University of Groningen' and inspection['UBC']['bucket']=='OUT_OF_BUDGET'
assert inspection['rows']==20 and inspection['no_approve_all_undecided']
state=[{'file':r,'expected_snapshot':h,'primary_now':sha(R/r)} for r,h in prefix.items() if sha(R/r)!=h]
(B/'source-after.original.json').write_text(json.dumps({'snapshot999_match':True,'primary_app_file_count':len(app),'primary_all_app_match':True,'parent_owned_primary_differences':state,'same_frozen_app_source_tree_context':P['source_tree_sha256'],'fullLOCAL_manifest_sha256':P['source_manifest_sha256']},indent=2)+'\n')
receipt={'sealed_utc':datetime.now(UTC).isoformat(),'status':'SYNTHETIC_DEMO_AND_SINGLE_HEAD_PASS_WITH_PRESERVED_INSPECTION_RED','PLAN_sha256':sha(B/'PLAN.json'),'fullLOCAL_firstsnapshot_manifest_sha256':P['source_manifest_sha256'],'source_tree_sha256':P['source_tree_sha256'],'source_snapshot':str(S),'source_head_metadata':P['source_head'],'source_branch_metadata':P['source_branch'],'execution_source_sha256':P['execution_source_sha256'],'primary_app_after_sha256':app,'commands':commands,'followup_readonly_inspection':second,'head':'d8e412c6a901','demo':{k:v for k,v in inspection.items() if k!='ordering_and_classifications'},'semantic_demo_state_sha256':hashlib.sha256(json.dumps(inspection['ordering_and_classifications'],sort_keys=True).encode()).hexdigest(),'first_inspection_red':'owncontrol used funding_classification instead of portfolio bucket; UBC FULL_TUITION andOUT_OF_BUDGET coexist in actual persistedrow. Originalred retained; no seed/migrate repeat or expectationchange.','safe_env_module_sha256':P['safe_env_module_sha256'],'safe_env_import_only':True,'runtime_database_own_only':str(B/'runtime/seed.db'),'source_999_unchanged':True,'primary_all_app_unchanged':True,'no_primaryenv_userDB_fullsuiteDB':True,'real_network_DNS_provider_model_git_app_STOP_mutations':0,'all_child_processes_completed_no_PG_server_started':True,'qualifications':['Firstfullsnapshot was independently interrupted byparent on3test importsort I001 errors; this seedreceipt is notfullgatePASS. Parentimports-onlyrepair/newfull separate.','Syntheticdemo rank/bucket/migration proof only, notlivesearchquality/score/launch acceptance.','Original20syntheticresults and427claims are corpusdemodata, notnewofficialfacts orcoverage.','Currentdemo98pagechecks include15failed; recorded honestly, noabsence inference.','Read-only correction changedthefieldlocator, notOUT_OF_BUDGET expectation; originalrawerror preserved.','Runtime DB/cache/export and anyephemeralSQLitejournals are excludedfromsealedcopyplan. No sharedrunner checks.db/primaryDB wasaccessed.']}
(B/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
selected={}
for p in sorted(B.rglob('*')):
 if not p.is_file() or p.name=='ready-manifest.json' or any(x in {'runtime','__pycache__'} for x in p.relative_to(B).parts):continue
 selected[str(p.relative_to(B))]={'sha256':sha(p),'bytes':p.stat().st_size}
(B/'ready-manifest.json').write_text(json.dumps({'status':receipt['status'],'files':selected,'selected_files':len(selected),'selected_bytes':sum(r['bytes'] for r in selected.values()),'excluded':['runtime ownDB/cache/export/journals','__pycache__','env files neverread/copied']},indent=2)+'\n')
print(json.dumps({'ready':sha(B/'ready-manifest.json'),'receipt':sha(B/'receipt.json'),'head':receipt['head'],'demo_state':receipt['semantic_demo_state_sha256'],'files':len(selected),'bytes':sum(r['bytes'] for r in selected.values()),'snapshot_prefix':len(prefix),'primary_app':len(app),'parent_primary_changed_files':[r['file'] for r in state]},indent=2))

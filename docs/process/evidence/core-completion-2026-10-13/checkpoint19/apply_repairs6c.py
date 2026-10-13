from pathlib import Path
import fcntl,json,hashlib,datetime,shutil,subprocess
s=Path(__file__).resolve().parent;b=s.parents[1];r=b/'work/unimatch-calendar-materials';lab=b/'product-platform/2026-10-12/g3-execution/source';h=lambda v:hashlib.sha256(v).hexdigest()
lock=(b/'local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
m=json.loads((s/'REPAIRS_6C_PREPARATION.json').read_text());rows={};assert len(m['paths'])==5
for p,sha in m['paths'].items():
 for tree in [r,lab]:assert h((tree/p).read_bytes())==sha,(tree,p)
 rows[p]={'preimage':sha,'postimage':h((s/'repairs6c-proposal'/p).read_bytes())}
grant={'status':'ROOT_REVIEW_WRITE_AHEAD_NOT_APPLIED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'paths':rows,'review':['Domain retains only exact existing own application full target, personal label/details edit does not assert new source. Missing/current own state remains guarded and all target changes still fresh selected/award/access validation. Original signed schemas unchanged.','API uses same exact retained target for source locks/token/context; no forged TargetObservation/research access. History/replay and linked tasks unchanged.','Read filter applies existing per-claim-type inclusive freshness windows in SQL before count/page; other lifecycle states not changed. Authoritative row type/status/access moment and deterministic type+ID pagination; no DML/rerank/network.','New native SQLite/privatePG controls deleted source/not selected/expired award access+changed-target rejection/replay/payload equality and exact microsecond boundary/filter/count/paging/all lifecycle preservation.'],'native':'NOT_RUN','browser':'NOT_RUN','live':'NOT_MEASURED_OLD_STOPS_UNCHANGED'}
(s/'REPAIRS_6C_GRANT.json').write_text(json.dumps(grant,indent=2)+'\n')
p=r/'docs/process/HANDOFF.md';p.write_text(p.read_text().replace('## 5. NEXT STEP — exact and executable\n\n','## 5. NEXT STEP — exact and executable\n\n**[core6c write-ahead] Exact5 REPAIRS_6C_GRANT paths: admissions_actions domain/API/tests and results API/freshness tests. Only an exact retained full target on the current owned application permits personal label/details edit without fresh result/selection/award access; any target/context change keeps existing fresh source checks, no fake observation. Claim filter/count/paging uses existing inclusive pertype current-age projection before SQL count/page, row authoritative metadata and deterministic type/ID order; other lifecycle and original stored payload/history unchanged. Native new 2DB controls plus frontend-contract consumer, fresh static/full bothDB required. Current6b FE853 PASS before/after, exact8 read UI; types.ts changed native consumer so old backend5826 is historical until new full. Native Demo/Auth later; root solo, no live/main/prod.**\n\n',1))
for p,v in rows.items():
 raw=(s/'repairs6c-proposal'/p).read_bytes()
 for tree in [r,lab]:(tree/p).write_bytes(raw);assert h((tree/p).read_bytes())==v['postimage']
(s/'REPAIRS_6C_APPLICATION.json').write_text(json.dumps({'status':'APPLIED_NOT_EXECUTED','paths':rows},indent=2)+'\n')
helper=s/'backend-native12';assert not helper.exists();shutil.copytree(s/'backend-native11',helper)
p=helper/'run_full_backend.py';t=p.read_text();old="DIAGNOSTIC_TARGETS = ['tests/test_research_input_provenance.py', 'tests/test_result_read_freshness.py', 'tests/test_programme_observation_publication.py']";assert old in t;p.write_text(t.replace(old,"DIAGNOSTIC_TARGETS = ['tests/test_admissions_action_edits.py', 'tests/test_result_read_freshness.py', 'tests/test_frontend_contract.py']"))
p=helper/'expected-native-source-pins.json';expected=json.loads(p.read_text());changes={}
for path in list(rows)+['frontend/src/types.ts']:
 if path in expected:
  changes[path]={'before':expected[path],'after':h((lab/path).read_bytes())};expected[path]=changes[path]['after']
p.write_text(json.dumps(expected,indent=2)+'\n')
assert all(h((r/path).read_bytes())==sha and h((lab/path).read_bytes())==sha for path,sha in expected.items())
(s/'REPAIRS_6C_HELPER_GRANT.json').write_text(json.dumps({'status':'ROOT_REVIEW_CLONE11_TO12_GUARDS_ASSETS_PREREQS_UNCHANGED','expected_map':len(expected),'changed':changes,'diagnostic_targets':['edits','freshness','frontend_contract'],'whole_mode':'unchanged both defaultDB/coverage92/socketguard/OSdeny/privatePG/full tests'},indent=2)+'\n')
(s/'run_static_repairs6c1.py').write_text((s/'run_static_inputs6a3.py').read_text().replace('inputs-static6a3','repairs-static6c1'))
print('Exact5 source applied and native12 pins sealed; native tests/full/browser pending.');fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

"""Verify completed native full originals/source only; no tests or app imports."""
import hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
own=Path(__file__).resolve().parent
repo=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
run=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T053629Z-check-6693acd5')
oldrun=run.parent/'20261008T043357Z-check-0d98eeb3'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((run/'summary.json').read_bytes());s=json.loads((run/'source-manifest.json').read_bytes())
assert m['status']=='passed' and m.get('finished_at')
assert len(m['steps'])==13 and all(x['exit_code']==0 for x in m['steps'])
assert s['source_head']=='ab273163d73f3fc6af78b7ebbee47d6863044aa3'
assert s['source_tree_sha256']=='75497406d33bb8c4fe3015d44b13e20786d8cf9a74d4e6138c16d3341164d446'
assert sha(run/'source-manifest.json')=='0ef04ff7a09aaffc49d27fd6596dc6543bbbd0ec65027e05bbde098937fad689'
pins=json.loads((own/'source-after-999.json').read_bytes())['file_sha256']
assert len(pins)==999
for p,h in pins.items():assert sha(repo/p)==sha(run/'source'/p)==s['files'][p]==h,p
stop=repo.parent/'local-round7/provider-STOP.json';assert sha(stop)=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
b=repo.parent/'local-round13/b-stopped-trace-proposal'
c=json.loads((b/'qualified-controls.json').read_bytes())
expected_new={tuple(row['identity']) for row in c['native']['on'] if row['new']}
assert len(expected_new)==19
ids={}; added={}
for mode in ['backend-sqlite','backend-postgresql']:
 cases=list(ET.parse(run/(mode+'.xml')).getroot().iter('testcase'))
 assert all(not any(x.tag in ['failure','error','skipped'] for x in case) for case in cases)
 keys=[(case.get('classname'),case.get('name')) for case in cases];assert len(keys)==len(set(keys))
 ids[mode]=set(keys)
 oldcases=list(ET.parse(oldrun/(mode+'.xml')).getroot().iter('testcase'))
 oldids={(case.get('classname'),case.get('name')) for case in oldcases};assert len(oldids)==4330
 assert oldids<=ids[mode]; added[mode]=ids[mode]-oldids
 assert added[mode]==expected_new and len(ids[mode])==4349,(mode,len(ids[mode]),added[mode]-expected_new)
assert ids['backend-sqlite']==ids['backend-postgresql']
log=(run/'backend-sqlite.log').read_text();coverage=float(re.search(r'Total coverage: ([0-9.]+)%',log).group(1));assert coverage>=92
seed=repo.parent/'local-round13/b-stopped-trace-seed'
sp=json.loads((seed/'candidate-app-pins.json').read_bytes());assert len(sp)==242
for p,h in sp.items():assert sha(repo/p)==sha(run/'source'/p)==h,p
receipt={'time':datetime.now(timezone.utc).isoformat(),'status':'FRESH_FULL13_OF13_PASS_EXACT_SOURCE','run_id':run.name,'head':s['source_head'],'snapshot_sha256':s['source_tree_sha256'],'source_manifest_file_sha256':sha(run/'source-manifest.json'),'source_prefix_paths':len(pins),'SQLite_unique':len(ids['backend-sqlite']),'PG_unique':len(ids['backend-postgresql']),'same_backend_identities':True,'old4330_preserved_eachDB':True,'new19_exact_author_identities_eachDB':sorted(expected_new),'SQLite_coverage_percent':coverage,'full_elapsed_seconds':(datetime.fromisoformat(m['finished_at'])-datetime.fromisoformat(m['started_at'])).total_seconds(),'seed_app242_bound':True,'steps':m['steps'],'STOP_sha256':sha(stop),'quality':'UNSCORED/no live/production/launch; containers and hosted CI not performed'}
(own/'final-full-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['steps','new19_exact_author_identities_eachDB']},indent=2))

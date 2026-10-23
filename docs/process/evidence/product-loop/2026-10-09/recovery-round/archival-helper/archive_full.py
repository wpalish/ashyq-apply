"""Archive only actual passed own full originals and bind source. No check execution."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,shutil,subprocess,xml.etree.ElementTree as ET
ROOT=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO=ROOT/'work/ashyq-apply'
TASK=ROOT/'work/product-round5'
BUNDLE=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
STOP=ROOT/'work/local-round7/provider-STOP.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(STOP)=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
execution=json.loads((TASK/'native-queue/execution.json').read_text())
assert [r['suite'] for r in execution]==['core','full'] and all(r['exit_code']==0 for r in execution)
assert len(execution[-1]['owned_runs'])==1
record=execution[-1]['owned_runs'][0]; run=Path(record['path'])
assert run.parent==BUNDLE/'runs' and sha(run/'summary.json')==record['summary_sha256']
s=json.loads((run/'summary.json').read_text()); m=json.loads((run/'source-manifest.json').read_text())
assert s['status']=='passed' and s['suite']=='full' and len(s['steps'])==13
assert all(x['exit_code']==0 for x in s['steps']) and s['source']==m
assert not s['github_actions_started'] and not s['live_network_capture_started'] and not s['includes_container_gates']
assert m['repository']==str(REPO) and m['source_branch']=='task/product-research-recovery'
assert m['source_head']==(TASK/'applied-head.txt').read_text().strip()
pins=json.loads((TASK/'applied-source-pins.json').read_text()); assert len(pins)==16
for n,h in pins.items():
 assert sha(REPO/n)==h and sha(run/'source'/n)==h and m['files'][n]==h,n
identities=[]
for name in ['backend-sqlite.xml','backend-postgresql.xml']:
 tree=ET.parse(run/name); nodes=tree.findall('.//testcase'); ids={(x.attrib['classname'],x.attrib['name']) for x in nodes}
 assert len(nodes)==len(ids)==4369 and not any(x.find(k) is not None for x in nodes for k in ['failure','error','skipped'])
 identities.append(ids)
assert identities[0]==identities[1]
selected=['summary.json','source-manifest.json','backend-sqlite.xml','backend-postgresql.xml']+[Path(x['log']).name for x in s['steps']]
assert len(selected)==len(set(selected))==17
parent_names=['execution.json','core-console-original.log','full-console-original.log']
for step in s['steps']:
 assert Path(step['log']).resolve()==(run/Path(step['log']).name).resolve()
for path in [run/n for n in selected]+[TASK/'native-queue'/n for n in parent_names]:
 assert path.is_file() and not path.is_symlink(),path
pins_destination=REPO/'docs/process/evidence/product-loop/2026-10-09/recovery-round/applied-source-pins.json'
pins_bytes=(json.dumps(pins,indent=2)+'\n').encode()
assert not pins_destination.exists() or pins_destination.read_bytes()==pins_bytes
out=REPO/'docs/process/evidence/product-loop/2026-10-09/recovery-round/full'
assert not out.exists(); out.mkdir()
files={}
for n in selected:
 p=run/n; assert p.is_file(); shutil.copy2(p,out/n); assert p.read_bytes()==(out/n).read_bytes()
 files[n]={'source':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
receipt={'created_at':datetime.now(timezone.utc).isoformat(),'source_run':str(run),'source_head':m['source_head'],'source_tree_sha256':m['source_tree_sha256'],'summary_sha256':sha(run/'summary.json'),'files':files,'count':len(files),'bytes':sum(x['bytes'] for x in files.values()),'qualification':'Exact17 actual native full originals, not17 experiments. No runtime/source/dependencies/private payload copied.13actual full steps, same4369IDs in each DB; no unique-count doubling. Counts beyond JUnit remain log assertions for peer review.'}
parent_files={}
for n in parent_names:
 p=TASK/'native-queue'/n; dst=out/('queue-'+n); shutil.copy2(p,dst); assert p.read_bytes()==dst.read_bytes()
 parent_files[dst.name]={'source':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
receipt['parent_queue_originals']=parent_files
receipt['parent_queue_count']=len(parent_files)
(out/'COPY_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
if not pins_destination.exists(): pins_destination.write_bytes(pins_bytes)
print(json.dumps({k:receipt[k] for k in ['source_run','source_head','source_tree_sha256','count','bytes']}))

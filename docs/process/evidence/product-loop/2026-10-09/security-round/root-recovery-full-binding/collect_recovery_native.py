"""Finite root-owned native originals, outside primary until runner is terminal."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, sys

task=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1')
bundle=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
suite=sys.argv[1]
head=(task/'recovery-head.txt').read_text().strip()
if suite=='doctor':
    run=bundle/'runs/20261009T012630Z-doctor-87227274'
else:
    assert suite=='core'
    execution=json.loads((task/'native-queue-recovery/execution.json').read_text())
    row=execution[0]
    assert row['suite']=='core' and row['exit_code']==0 and len(row['owned_runs'])==1
    run=Path(row['owned_runs'][0]['path'])
    assert run.parent==bundle/'runs' and sha(run/'summary.json')==row['owned_runs'][0]['summary_sha256']
summary=json.loads((run/'summary.json').read_text())
assert summary['status']=='passed' and summary['source']['source_head']==head
assert summary['source']['repository']==str(task.parent/'ashyq-apply')
assert len(summary['steps'])==(5 if suite=='doctor' else 8) and all(x['exit_code']==0 for x in summary['steps'])
names=['summary.json']+[Path(x['log']).name for x in summary['steps']]
if suite=='core':
    names+=['source-manifest.json','backend-sqlite.xml']
    manifest=json.loads((run/'source-manifest.json').read_text())
    assert summary['source']==manifest
    pins=json.loads((task/'recovery-source-pins.json').read_text())
    for n,h in pins.items():
        assert sha(task.parent/'ashyq-apply'/n)==h and sha(run/'source'/n)==h and manifest['files'][n]==h
assert len(names)==len(set(names))
out=task/(suite+'-recovery-originals')
assert not out.exists()
out.mkdir()
files={}
for name in names:
    p=run/name
    assert p.is_file() and not p.is_symlink()
    dst=out/'originals'/name
    dst.parent.mkdir(exist_ok=True)
    shutil.copyfile(p,dst)
    assert sha(p)==sha(dst)
    files['originals/'+name]={'sha256':sha(dst),'bytes':dst.stat().st_size}
receipt={'created_at':datetime.now(timezone.utc).isoformat(),'status':'DOCTOR_ENVIRONMENT_PASS' if suite=='doctor' else 'CORE8_PASS_FULL_NOT_INFERRED',
 'source_run':str(run),'source_head':head,'selected_originals':len(names),
 'qualification':'Exact bounded native originals; doctor environment only, core excludes PG/browser/audit; no DB/deps/source/private payload copied.'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files['receipt.json']={'sha256':sha(out/'receipt.json'),'bytes':(out/'receipt.json').stat().st_size}
(out/'READY.json').write_text(json.dumps({'status':receipt['status'],'files':files},indent=2)+'\n')
print(json.dumps({'packet':str(out),'READY_sha256':sha(out/'READY.json'),'originals':len(names)}))

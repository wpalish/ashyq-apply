"""Sole root source writer: integrate only exact accepted proposals."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess

ROOT=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO=ROOT/'work/ashyq-apply'
TASK=ROOT/'work/security-round1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
STOP=ROOT/'work/local-round7/provider-STOP.json'
assert sha(STOP)=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
decision=json.loads((TASK/'root-integration-decision.json').read_text())
assert decision['status']=='ACCEPT_SOURCE_PROPOSALS_FULL_PENDING'
for relative, expected in decision['peer_receipts'].items():
    assert sha(TASK/relative)==expected,relative
original=json.loads((TASK/'backend-proposal/original-source.json').read_text())
original.update(json.loads((TASK/'browser-proposal/base-source-pins.json').read_text())['files'])
legal=json.loads((TASK/'legal-proposal/PROPOSAL.json').read_text())
for name, value in original.items():
    assert sha(REPO/name)==value['sha256'],name
assert sha(REPO/'SECURITY.md')==json.loads((TASK/'frontend-audit/source-pins.json').read_text())['files']['SECURITY.md']['sha256']
for name, expected in legal['source_before'].items():
    assert sha(REPO/name)==expected,name
records={}
backend=json.loads((TASK/'backend-proposal/proposed-source.json').read_text())
browser=json.loads((TASK/'browser-proposal-final/source-manifest.json').read_text())['files']
for packet, files in [('backend-proposal',backend),('browser-proposal-final',browser)]:
    for name,record in files.items(): records[name]=(TASK/packet/'proposed'/name,record)
for name in ['LegalScreen.tsx','LegalScreen.privacy.test.tsx']:
    records['frontend/src/screens/'+name]=(TASK/'legal-proposal'/name,legal['files'][name])
assert len(records)==19
source_pins={n:record['sha256'] for n,(_,record) in records.items()}
for name, record in legal['files'].items():
    if name.startswith('LegalScreen'): continue
    destination='SECURITY.md' if name=='SECURITY.md' else 'docs/legal/'+name
    records[destination]=(TASK/'legal-proposal'/name,record)
assert len(records)==29
before={}
for name,(source,record) in records.items():
    assert source.is_file() and not source.is_symlink()
    assert sha(source)==record['sha256'] and source.stat().st_size==record['bytes'],name
    target=REPO/name
    before[name]=sha(target) if target.exists() else None
    if name not in original and name not in legal['source_before'] and name!='SECURITY.md':
        assert before[name] is None,name
    if before[name] is None: assert not target.is_symlink()
(TASK/'integration-before.json').write_text(json.dumps(before,indent=2)+'\n')
for name,(source,record) in records.items():
    target=REPO/name;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    assert sha(target)==record['sha256'],name
(TASK/'applied-source-pins.json').write_text(json.dumps(source_pins,indent=2)+'\n')
receipt={'at':datetime.now(timezone.utc).isoformat(),'before_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
         'app_test_paths':19,'legal_doc_paths':10,'files':{n:r for n,(_,r) in records.items()},
         'status':'APPLIED_EXACT_SOURCE_FULL_PENDING','peer_decision_sha256':sha(TASK/'root-integration-decision.json')}
(TASK/'integration-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert sha(STOP)=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
print(json.dumps({k:receipt[k] for k in ['at','app_test_paths','legal_doc_paths','status']}))

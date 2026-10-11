from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil
base=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026')
root=base/'exam-preparation-2026-10-11'
src=base/'integration-2026-10-11/source'
old=base/'continuation-2026-10-11/backend-full-interrupted-final'
new=root/'backend-full'
assert not new.exists()
new.mkdir()
receipt={'prepared_utc':datetime.now(timezone.utc).isoformat(),'source':str(src),'executed':False,'copies':[],'source_mutation':False}
def pin(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p in sorted(old.iterdir()):
    if not p.is_file():continue
    target=new/p.name
    shutil.copyfile(p,target)
    assert pin(p)==pin(target)
    receipt['copies'].append({'from':str(p),'to':str(target),'sha256':pin(p),'exact_bytes':True})
for name in ('run_static_frontend_final.py','run_demo_seed_final.py'):
    p=base/'continuation-2026-10-11'/name
    target=root/name
    shutil.copyfile(p,target)
    assert pin(p)==pin(target)
    receipt['copies'].append({'from':str(p),'to':str(target),'sha256':pin(p),'exact_bytes':True})
(root/'e2e').mkdir()
for name in ('run-native.py','runtime-child.py','loopback-only.sb'):
    p=base/'integration-2026-10-11/e2e'/name
    text=p.read_text()
    target=root/'e2e'/name
    if name=='run-native.py':
        assert "SOURCE = ROOT / 'source'" in text
        text=text.replace("SOURCE = ROOT / 'source'",f'SOURCE = Path({str(src)!r})',1)
    elif name=='runtime-child.py':
        assert "cwd = ROOT / 'source' / 'backend'" in text
        assert "cwd = ROOT / 'source' / 'frontend'" in text
        text=text.replace("cwd = ROOT / 'source' / 'backend'",f"cwd = Path({str(src / 'backend')!r})",1)
        text=text.replace("cwd = ROOT / 'source' / 'frontend'",f"cwd = Path({str(src / 'frontend')!r})",1)
    target.write_text(text)
    receipt['copies'].append({'from':str(p),'to':str(target),'original_sha256':pin(p),'sha256':pin(target),'exact_bytes':name=='loopback-only.sb','adaptation':'external source root only; assertions/native configs/ports/isolation/cleanup unchanged' if name!='loopback-only.sb' else None})
(root/'harness/PREPARATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'prepared':len(receipt['copies']),'executed':False,'expected_source_pins':'not yet rebound; only after reviewed source application','source_mutation':False}))

from pathlib import Path
import json,hashlib,shutil,datetime
b=Path(__file__).resolve().parent;a=b.parent/'a-schema-compatibility';base=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20');repo=base/'work/ashyq-apply'
def meta(p):
 data=p.read_bytes();return {'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
m=a/'ready-manifest.json';assert meta(m)['sha256']=='804e0959a665ad116465921c2235da69d2df7875ca80e21b4dd2bde717c4e17e';files=json.loads(m.read_text())['files'];assert all(meta(a/k)==v for k,v in files.items())
receipt=json.loads((a/'receipt.json').read_text());assert len(receipt['two_changed_files'])==2
for k,v in receipt['six_proposal_files'].items():
 p=a/'proposed'/k;assert meta(p)==v['proposal'];assert meta(repo/k)==v['current_primary'];q=b/'runtime'/k;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
(b/'logs/admitted-copy.json').write_text(json.dumps({'time_utc':datetime.datetime.now(datetime.UTC).isoformat(),'A_manifest':meta(m),'A_all34_checked':True,'A_selected_bytes':sum(v['bytes'] for v in files.values()),'two_changes':receipt['two_changed_files'],'six_exact_copied':{k:meta(b/'runtime'/k) for k in receipt['six_proposal_files']},'primary_before':{k:meta(repo/k) for k in receipt['six_proposal_files']},'STOP':meta(base/'work/local-round7/provider-STOP.json'),'status':'EXACT_PINNED_COPY_READY_FOR_NATIVE_OFFLINE_PEER'},indent=2)+'\n');print('34 files verified; exact six overlaid, only two differ origin')

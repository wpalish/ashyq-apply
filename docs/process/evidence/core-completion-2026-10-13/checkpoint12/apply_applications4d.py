from pathlib import Path
import hashlib,json,fcntl,datetime,subprocess
s=Path(__file__).resolve().parent;base=s.parents[1];r=base/'work/unimatch-calendar-materials';lab=base/'product-platform/2026-10-12/g3-execution/source';h=lambda raw:hashlib.sha256(raw).hexdigest()
lock=(base/'local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
review=json.loads((s/'APPLICATIONS_4D_ROOT_REVIEW.json').read_text());assert review['status']=='ROOT_SOURCE_REVIEW_ONLY_NOT_APPLIED_OR_EXECUTED';paths=review['source_postimages'];assert len(paths)==11
for p,v in paths.items():
 for tree in [r,lab]:
  f=tree/p;assert (h(f.read_bytes()) if f.exists() else None)==v['preimage'],(p,tree)
 assert h((s/'applications4d-proposal'/p).read_bytes())==v['postimage']
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip();now=datetime.datetime.now(datetime.timezone.utc).isoformat()
grant={'baseline':head,'at_utc':now,'paths':paths,'scope':'Closed companion V2 metadata/context/remove codec and own forms; explicit confirmations, retained removed history and exact original intent recovery; frozen V1 guards byte-equal. Read/edit target fields and dependency IDs from own native state only; lock declared programme context; no file deletion or university withdrawal on personal-record removal. Root alone, actual API/browser integration pending.','checks':review['review']}
(s/'APPLICATIONS_4D_GRANT.json').write_text(json.dumps(grant,indent=2)+'\n')
p=r/'docs/process/HANDOFF.md';t=p.read_text().replace('## 5. NEXT STEP — exact and executable\n\n','## 5. NEXT STEP — exact and executable\n\n**[core4d write-ahead] Qualified server4c5807 both DBs. Exact11 FE paths from APPLICATIONS_4D_GRANT.json: closed companion request/current/head/receipt/remove snapshot codecs, unchanged V1 guards/journal64/original UUID/CAS; personal document label/responsible/date/link/dependencies editor with confirmation, app context label/programme/intake/route exact retained scholarship fields, declared target lock, explicit deletion and retained snapshot history. No linked-document cascade, fake resultID or official submission. First external root review rejected unbounded generator V1 current edit; exact original V1 restored before apply. Root-only reviewed proposal/preimages, no native runtime active. Apply exact primary/lab, preserve WIP/push then fresh frozen type/lint/unit/build. Native browser/Today/old finding closure pending; no live/main/prod.**\n\n',1);p.write_text(t)
for p,v in paths.items():
 raw=(s/'applications4d-proposal'/p).read_bytes()
 for tree in [r,lab]:q=tree/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw);assert h(q.read_bytes())==v['postimage']
(s/'APPLICATIONS_4D_APPLICATION.json').write_text(json.dumps({'status':'APPLIED_NOT_EXECUTED','at_utc':now,'paths':paths},indent=2)+'\n')
runner=(s/'run_applications_frontend_4b3.py').read_text().replace('applications-frontend-4b3','applications-frontend-4d1');(s/'run_applications_frontend_4d1.py').write_text(runner)
print('Applied exact 11 paths, original proposal review and preimages retained; FE native gates NOT_RUN.');fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

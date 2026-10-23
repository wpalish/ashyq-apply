from pathlib import Path
import fcntl,hashlib,json,datetime,subprocess
s=Path(__file__).resolve().parent;b=s.parents[1];r=b/'work/unimatch-calendar-materials';lab=b/'product-platform/2026-10-12/g3-execution/source'
lock=(b/'local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
h=lambda v:hashlib.sha256(v).hexdigest();m=json.loads((s/'INPUTS_6B_PREPARATION.json').read_text());rows={}
assert len(m['paths'])==8
for p,sha in m['paths'].items():
 for tree in [r,lab]:
  f=tree/p;assert(h(f.read_bytes()) if f.exists() else None)==sha,(tree,p)
 rows[p]={'preimage':sha,'postimage':h((s/'inputs6b-proposal'/p).read_bytes())}
grant={'status':'ROOT_REVIEW_WRITE_AHEAD','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'paths':rows,'scope':'Existing GET run/context only, named sections and recorded assessment notice. Stable getter and rendered/synchronous/serial/mounted case-generation/run/profile-object fences. Unknown legacy/corrupt/current read failure explicit; retain only confirmed same-profile read. No local profile hash, research/rerank, stored result/history/receipt mutation. Original frozen G3 types untouched. Native backend consumes frontend/types.ts; final whole backend gate follows 6c and includes these changed bytes.','integration':'NOT_RUN','live':'NOT_MEASURED_OLD_STOPS_UNCHANGED'}
(s/'INPUTS_6B_GRANT.json').write_text(json.dumps(grant,indent=2)+'\n')
p=r/'docs/process/HANDOFF.md';t=p.read_text().replace('## 5. NEXT STEP — exact and executable\n\n','## 5. NEXT STEP — exact and executable\n\n**[core6b write-ahead] Exact8 frontend paths INPUTS_6B_GRANT: types.ts additive read DTO, researchReadContext validators, useResearchInputRead hook+test, ResearchReadNotice+test, App mount, i18nEN/RU/KK. Existing GET run only after saved-profile identity changes, own rendered/sync/serial fences and last confirmed same-profile read; no Store overwrite/research/rerank/purchase. UI unknown/changed/mixed/recorded evaluation/current source age caveats. Original G3 signed types unchanged. Fresh FE all gates then6c retained-target/filter controls and current whole backend (types.ts is consumed), native journey later. Root solo, STOPs/main/prod unchanged.**\n\n',1);p.write_text(t)
for p,v in rows.items():
 raw=(s/'inputs6b-proposal'/p).read_bytes()
 for tree in [r,lab]:
  f=tree/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw);assert h(f.read_bytes())==v['postimage']
(s/'INPUTS_6B_APPLICATION.json').write_text(json.dumps({'status':'APPLIED_NOT_TESTED','paths':rows},indent=2)+'\n')
(s/'run_inputs_frontend6b1.py').write_text((s/'run_today_frontend5c.py').read_text().replace('today-frontend5c','inputs-frontend6b1'))
print('Applied exact8 read context files; native qualification pending.');fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply');W=R.parent;D=R/'docs/process/evidence/search-loop/2026-10-07/local-round11/offline-boundaries'
assert not D.exists();D.mkdir(parents=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
packets=[('local-round10/b-provider-stop-closure-review','MANIFEST.json','closure-peer','d03561b739a056a0fd5b2c58ad10bc21ec2bb495a05a521f1dbe019ee4ae9433'),('local-round10/a-strict-walker-preparation','ready-manifest.json','rejected-strict-stop','232f6edd02cf33ed61a472d51012cd1598ecc13d84cfbfe0980b2a3cea2dc5e9'),('local-round10/a-stable-walker-ordering','ready-manifest.json','deferred-stable-ordering','ea7a79383e18a77de92d6385b28d491fd17480d0672ff6c37d6be9a35ec770cb'),('local-round10/b-aalto-tuition-row-proposal','ready-manifest.json','tuition-contract-gap','b0c20345cd53054952ab672d7968507bd59b8c99fe73c5e48e3ffa2256816da3'),('local-round11/root-primary-purpose-diagnostic','ready-manifest.json','primary-purpose-diagnostic','33a861bf1c34c0072700885bb7a1b3eab498e9604241999aba27f20ac4bd7a56'),('local-round10/b-provisional-routing-review','PREPARATION-manifest.json','routing-peer-preparation','6d38bb1226f66d99567e69f0eefabb8e1e0a7cc912bcc62d243b73fa25029e98')]
files={};origins=[]
def cp(p,rel,digest=None):
 assert p.is_file() and not p.is_symlink(),p
 if digest:assert sha(p)==digest,p
 assert any(p.name.endswith(x) for x in ['.json','.py','.md','.log','.txt','.body','.diff','.html','.xml','.stderr','.stdout','.patch','.json.original','.py.original','.md.original','.log.original']),p
 dest=D/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());assert sha(dest)==sha(p)
 files[rel]={'original':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
for rel,manifest,label,digest in packets:
 own=W/rel;assert sha(own/manifest)==digest,manifest;m=json.loads((own/manifest).read_text());fs=m['files'];rows=fs.items() if isinstance(fs,dict) else [(v['path'],v) for v in fs]
 for name,v in rows:
  q=Path(name);assert not q.is_absolute() and '..' not in q.parts
  cp(own/q,label+'/'+name,v if isinstance(v,str) else v['sha256'])
 cp(own/manifest,label+'/'+manifest)
 origins.append({'packet':rel,'manifest_sha256':digest,'verdict':m.get('status','see receipt')})
F=W/'local-round11/archive-boundaries-incomplete'
cp(F/'archive-first.original.py','parent/archive-first.original.py');cp(F/'failure.json','parent/archive-first-failure.json');cp(Path(__file__),'parent/archive-boundaries.py')
stop=W/'local-round7/provider-STOP.json';assert sha(stop)=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
full=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T004040Z-check-bc90e5dc/summary.json');source=json.loads(full.read_text())['source'];matched=0
for name,digest in source['files'].items():
 if name.startswith(('backend/app/','backend/tests/','backend/evaluation/','backend/scripts/','frontend/')):
  assert sha(R/name)==digest,name;matched+=1
assert matched==999
receipt={'status':'OFFLINE_BOUNDARIES_ARCHIVED_NO_SOURCE_APPLY','created_utc':datetime.now(timezone.utc).isoformat(),'source_head':source['source_head'],'snapshot_sha256':source['source_tree_sha256'],'selected_paths_unchanged':matched,'global_STOP_sha256':sha(stop),'selected_files':len(files),'selected_bytes':sum(v['bytes'] for v in files.values()),'files':files,'packets':origins,'outcomes':{'closed_collection_peer':'10PASS,332files37160511bytes matched;UNSCORED only','strict_stop':'46PASS/3RED rejected: late2027/population/nondegree route lost','stable_ordering':'37PASS, deferred: Groningen0reads saved/current endtoend gain absent','tuition':'10nativechecksPASS; typedcohort/field/period gap; no patch;16ONnegatives NOT_RUN','primary_purpose':'30native original outputs equal;2changed cases;Aalto remains scholarship_index;2newsynthetic falseprogramme permissions;ablation not a rule','provisional_routing_peer':'18pinned native source copies/11 expected boundaries; A exactproposal review NOT_RUN'},'application_flags_added':False,'source_patch_applied':False,'live_model_provider_calls':0,'scoring_executed':False,'semantic_label_reads':False,'limitations':['saved-source diagnostics and synthetic controls are not quality scores or accepted blind expert pilot','999 prefix-selected paths include research data JSON, not all executable code','native read_cap recovery is distinct from harness asyncio cancellation; current Groningen cancellation uncorrected','source observations/provisional routing/real Claims/Job completion/source completeness are distinct','no rule/default/provider/quota/STOP/purchase/production change']}
(D/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'receipt_sha256':sha(D/'receipt.json'),'selected_files':len(files),'selected_bytes':receipt['selected_bytes'],'source_unchanged_paths':matched}))

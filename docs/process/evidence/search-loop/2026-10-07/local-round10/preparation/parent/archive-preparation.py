# -*- coding: utf-8 -*-
from pathlib import Path
import hashlib,importlib.util,json,shutil
from datetime import datetime,timezone
R=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply'); W=R.parent; P=W/'local-round10/genuine-baseline'; sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
A=W/'local-round9/a-baseline-repaired-validator-review-v4';B=W/'local-round9/b-baseline-validator-final-4fa'
assert sha(A/'ready-manifest.json')=='cd010e6e519d9af043f3f528e67de880e2a33ac90e52cf9c9c5fd22d587855e2'
assert sha(B/'MANIFEST.json')=='171fe86d4d0426463ce3c7d09e6b8ff2dc1cad5f728d97f3cecab8bb4f55d931'
x=json.loads((P/'PLAN.json').read_text());x.update(status='READY_FRESH_ORIGINAL10_EXECUTION_NOT_STARTED',accepted_driver_reviews={'A':{'manifest':str(A/'ready-manifest.json'),'sha256':sha(A/'ready-manifest.json'),'verdict':'accepted requested protocol contract; qualified historical no-ops retained'},'B':{'manifest':str(B/'MANIFEST.json'),'sha256':sha(B/'MANIFEST.json'),'314_assertions_PASS':True}},prepared_at_utc=datetime.now(timezone.utc).isoformat(),execution_command=[str(Path(x['source_snapshot'])/'backend/.venv/bin/python'),str(P/'execute_baseline.py'),'--execute'])
(P/'PLAN.json').write_text(json.dumps(x,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('round10_final_preflight',P/'execute_baseline.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);source,snapshot,n=m.preflight();assert n==999 and sha(P/'execute_baseline.py')==x['driver_sha256']
r={'status':'FINAL_READ_ONLY_PREFLIGHT_READY_NO_LIVE','at_utc':datetime.now(timezone.utc).isoformat(),'source_paths_verified':n,'source_head':source['source_head'],'source_tree_sha256':source['source_tree_sha256'],'plan_sha256':sha(P/'PLAN.json'),'controller_sha256':sha(P/'execute_baseline.py'),'package_sha256':sha(m.PACKAGE/'run_local.py'),'new_STOP_absent':not m.STOP.exists(),'both_peer_acceptances':True,'network_model_provider_process_calls':0};(P/'preflight-ready.json').write_text(json.dumps(r,indent=2)+'\n')
D=R/'docs/process/evidence/search-loop/2026-10-07/local-round10/preparation';assert not D.exists();D.mkdir(parents=True)
files={}
def cp(origin,rel,digest=None):
 assert origin.is_file() and not origin.is_symlink(),origin
 if digest:assert sha(origin)==digest,origin
 data=origin.read_bytes()
 assert origin.suffix in ('.json','.py','.log','.md','.diff','.txt','.html','.xml'),origin
 dest=D/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);assert sha(dest)==sha(origin)
 files[rel]={'original':str(origin),'sha256':sha(origin),'bytes':len(data)}
for own,name,manifest in [(A,'expert-a-final','ready-manifest.json'),(B,'expert-b-final','MANIFEST.json'),(W/'local-round9/a-ielts-v5-proposal','ielts-v5-external','ready-manifest.json')]:
 y=json.loads((own/manifest).read_text())
 for rel,digest in y['files'].items():cp(own/rel,name+'/'+rel,digest)
 cp(own/manifest,name+'/'+manifest)
for p in sorted(P.iterdir()):
 if p.is_file() and p.suffix in ('.json','.py'):cp(p,'fresh-plan/'+p.name)
for name in ['REPAIR_PLAN_v4.json','REPAIR_PLAN_v5.json','execute_baseline.rejected-v3.original.py','execute_baseline.rejected-url.original.py','root-v4-default.log','root-v4-partial.log']:
 cp(W/'local-round9/genuine-baseline'/name,'parent-history/'+name)
for name in ['MANIFEST.original.json','receipt.original.json','accepted-reds.original.json']:
 cp(W/'local-round9/b-baseline-repaired-validator-review'/name,'rejected-driver-v3/'+name)
for name in ['manifest.a56e.original.json','receipt.a56e.original.json','url-seam.original.json']:
 cp(W/'local-round9/b-baseline-repaired-validator-review-v2'/name,'rejected-url-representation/'+name)
cp(Path('/tmp/x20-baseline-transfer.py'),'parent/transfer-smoke.py');cp(Path('/tmp/x20-prepare-offline-score.py'),'parent/prepare-offline-score.py');cp(Path(__file__),'parent/archive-preparation.py')
receipt={**r,'status':'FRESH_ORIGINAL10_PREPARATION_ARCHIVED_NO_LIVE','files':files,'selected_files':len(files),'selected_bytes':sum(v['bytes'] for v in files.values()),'limits':['synthetic protocol controls are not live quality evidence','IELTSv5 remains external and independently rejected; no apply','pending old draft metadata timestamps are qualified by actual Git checkpoints','runtime DB/cache/env/private Git/browser storage excluded','all app/harness source unchanged from tested7c74']};(D/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
clock=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MUTC');entry=f'''**[search-genuine-baseline] READY FOR FRESH LOCAL EXECUTION, {clock}.** New round10 PLAN SHA `{r['plan_sha256']}`, controller4fa670fb, package4d5a0953, source7c74/full19f349 pinned. A manifestcd010e6e accepted scoped contract (qualified old no-ops); B manifest171fe86d314/314 PASS. Root transfer18/18 and read-only preflight999 unchanged/STOP absent. Prepared archive receipt SHA `{sha(D/'receipt.json')}`, {len(files)} selected files/{receipt['selected_bytes']} bytes. Next exact command is PLAN.execution_command with --execute after this preparation is committed/pushed. Original10 sequential6/60/120/119+1/nativeFalse, first refusal globally stops. No live has started at this checkpoint. All partial Jobs/missing facts remain explicit and in denominator. No old attempt resume, quality/default/purchase/launch inference.'''
p=R/'docs/process/HANDOFF.md';s=p.read_text()
for sec in (2,3,5,6):
 marker=next(l for l in s.splitlines() if l.startswith(f'## {sec}. '));s=s.replace(marker+'\n',marker+'\n\n'+entry+'\n',1)
s+=f'\n- {clock} — gpt-6-astra: final driver4fa two-peer accepted, fresh round10 preparation archived; source7c unchanged, next authorized original10 --execute.\n';p.write_text(s)
for name in ['CLAUDE_SEARCH_RELAY_2026-10-07.md','SEARCH_LOOP_LEDGER_2026-10-07.md']:
 p=R/'docs/process'/name;p.write_text(p.read_text()+'\n\n'+entry+'\n')
p=W.parent/'outputs/CLAUDE_CONTINUE.md';p.write_text(p.read_text()+'\n\n'+entry+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('files','limits')},indent=2));print('archive receipt SHA',sha(D/'receipt.json'))

from pathlib import Path
import fcntl,json,hashlib,datetime,shutil
s=Path(__file__).resolve().parent;b=s.parents[1];r=b/'work/unimatch-calendar-materials';lab=b/'product-platform/2026-10-12/g3-execution/source';h=lambda v:hashlib.sha256(v).hexdigest();lock=(b/'local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);m=json.loads((s/'PROFILE_10_PREPARATION.json').read_text());rows={};assert len(m['paths'])==5
for p,sha in m['paths'].items():
 for tree in [r,lab]:
  f=tree/p;assert(h(f.read_bytes()) if f.exists() else None)==sha,(tree,p)
 rows[p]={'preimage':sha,'postimage':h((s/'profile10-proposal'/p).read_bytes())}
grant={'status':'ROOT_REVIEW_WRITE_AHEAD','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'paths':rows,'scope':m['scope'],'review':'Shared publishProfileSave called only after op-generation and owner fence, accepts actual primary response before optional case-list GET. Canonical baseline/current-draft equality preserves newer typing, same-case generation unchanged, pointer local case retired. Metadata failure cannot undo confirmed save; subsequent POST failure retains old run/results. Exact known saved-name fallback shows no guessed counter. Native true201/aborted metadata GET and PUT/aborted run POST, unchanged original evaluation, actual named funding warning;3 Store controls for normalized save/newer typing/stale case.','native':'NOT_RUN','live':'NOT_MEASURED_STOPS_RETAINED'};(s/'PROFILE_10_GRANT.json').write_text(json.dumps(grant,indent=2)+'\n')
f=r/'docs/process/HANDOFF.md';f.write_text(f.read_text().replace('## 5. NEXT STEP — exact and executable\n\n','## 5. NEXT STEP — exact and executable\n\n**[core10 write-ahead] Exact5 PROFILE_10_GRANT paths: Store shared publishProfileSave, newStore start-save controls/newnative input spec, App exact current-name fallback, i18nEN/RU/KK. Actual profile response accepted after opgen/owner fence before optional casesGET; canonical baseline/newer typing/pointer are reused across ordinary/create/start saves. Existing-profile start no longer ignores durable returned profile; later runPOST failure retains previous research/results. Optional list failure remains an error but cannot un-confirm primaryACK; saved-name fallback has no invented counts. Native10 owned5243/8153 Demo/Auth metadataGETdeliveryabort and later runPOSTprecommitabort with unchanged old stored evaluations and namedFunding warning. No primary/provider/default/network/STOP changes. Fresh FE/all native shared consumers and final full bothDB follow; root solo.**\n\n',1))
for p,v in rows.items():
 raw=(s/'profile10-proposal'/p).read_bytes()
 for tree in [r,lab]:f=tree/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
(s/'PROFILE_10_APPLICATION.json').write_text(json.dumps({'status':'APPLIED_NOT_TESTED','paths':rows},indent=2)+'\n')
new=s/'native-core10';new.mkdir(exist_ok=False);(new/'e2e').mkdir();files={}
for name in ['run-native-recovery.py','runtime-child.py','loopback-only.sb']:
 raw=(s/'native-core9/e2e'/name).read_bytes();t=raw.decode().replace('5241','5243').replace('8151','8153').replace('core-admissions-fences.spec.ts','core-research-inputs.spec.ts')
 if name=='run-native-recovery.py':
  start=t.index("receipt['network_fault_controls']");end=t.index('\n',start);t=t[:start]+"receipt['network_fault_controls'] = {'metadata_ack': 'actual primary profile201 received, subsequent actual own casesGET UI delivery aborted', 'start_failure': 'actual profilePUT200 received, subsequent new runPOST transport aborted before native server', 'assertions': 'confirmed saved pointer/name/canonicalbaseline survives; actual named funding input warning and old run/results evaluation retained, no automatic rerank or new run'}"+t[end:]
 (new/'e2e'/name).write_text(t);files[name]={'preimage':h(raw),'postimage':h(t.encode())}
shutil.copyfile(s/'native-core9/run_native_recovery_pair.py',new/'run_native_recovery_pair.py')
v=json.loads((s/'native-core9/expected-source-pins.json').read_text())
for p,row in rows.items():
 if row['preimage'] is not None:assert v[p]==row['preimage']
 v[p]=row['postimage']
assert all(h((r/p).read_bytes())==sha and h((lab/p).read_bytes())==sha for p,sha in v.items());(new/'expected-source-pins.json').write_text(json.dumps(v,indent=2)+'\n')
for folder in ['native-core7','native-core8','native-core9']:(s/folder/'expected-source-pins.json').write_text(json.dumps(v,indent=2)+'\n')
(s/'PROFILE_10_HELPER_GRANT.json').write_text(json.dumps({'status':'ROOT_REVIEWED_NATIVE9_CLONE_GUARDS_RETAINED','source_count':len(v),'changed':files,'ports':[5243,8153],'scope':'Actual native app/worker/auth/privateSQLite/corpus, providerNone/noAPI or receipts fabrication, labelled network delivery faults; no runtime yet'},indent=2)+'\n')
(s/'run_profile_frontend10a1.py').write_text((s/'run_core_frontend9a1.py').read_text().replace('core-frontend9a1','profile-frontend10a1'));print('Exact5 profile acknowledgement/read-context files and native10 helper applied.');fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

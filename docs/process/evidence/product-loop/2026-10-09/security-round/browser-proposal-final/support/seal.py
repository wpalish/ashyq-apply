from pathlib import Path
import json,hashlib,difflib,xml.etree.ElementTree as E
r=Path(__file__).resolve().parent.parent;old=r.with_name('browser-proposal')
info=lambda p:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
m=json.loads((old/'READY.json').read_text());assert info(old/'READY.json')['sha256']=='6063029c598e7c05cdb207f74bdcb7de47d0773f58752ce9aa6fef2381df4bb0'
for rel,v in m['files'].items():assert info(old/rel)==v,rel
newprefix=('private browser state belongs','case privacy controls','unmounted applicant actions','actual API owner boundary','native checklist mark owner scope','independent A actual auth acknowledgment regression')
rows=[];sets=[]
for mode in ['final-off','sealed-on-v2']:
 cases=E.parse(r/f'logs/{mode}/junit.xml').getroot().findall('.//testcase');assert len(cases)==63
 result=[]
 for c in cases:
  bad=c.find('failure') is not None or c.find('error') is not None;assert c.find('skipped') is None
  result.append({'file':c.attrib['classname'],'name':c.attrib['name'],'old':not c.attrib['name'].startswith(newprefix),'status':'RED' if bad else 'PASS'})
 assert sum(x['old'] for x in result)==36;assert all(x['status']=='PASS' for x in result if x['old'])
 sets.append({(x['file'],x['name']) for x in result});rows.append({'mode':mode,'pass':sum(x['status']=='PASS' for x in result),'red':sum(x['status']=='RED' for x in result),'cases':result})
assert sets[0]==sets[1] and rows[0]['red']==20 and rows[1]['red']==0
(r/'native-comparison.json').write_text(json.dumps({'runs':rows,'same_cases':True,'predecessor606_own62pass_A1materialRED':'peer-input/READY.json','A_on_original_OFF':'fails at B status revalidation prerequisite; not proof of the same late-owner overwrite cause as606'},indent=2)+'\n')
files={};patch='';delta=[]
for p in sorted((r/'proposed').rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(r/'proposed');files[str(rel)]=info(p);orig=r/'original'/rel
 patch+=''.join(difflib.unified_diff(orig.read_text().splitlines(True) if orig.exists() else [],p.read_text().splitlines(True),fromfile='a/'+str(rel) if orig.exists() else '/dev/null',tofile='b/'+str(rel)))
 if info(old/'proposed'/rel)!=info(p):delta.append(str(rel))
assert len(files)==12 and delta==['frontend/src/AuthGate.test.tsx','frontend/src/AuthGate.tsx']
(r/'source-manifest.json').write_text(json.dumps({'files':files,'delta_from606_only':delta},indent=2)+'\n')
(r/'browser-privacy.patch').write_text(patch)
(r/'predecessor-binding.json').write_text(json.dumps({'sha256':info(old/'READY.json')['sha256'],'all110files_unchanged':True,'status':'REJECTED_NATIVE_POST_AUTH_STATUS_RACE','A_peer_red_ready_sha':info(r/'peer-input/READY.json')['sha256'],'repair':'common post-login/reset status owner-at-request fence; independent test body expectation unchanged'},indent=2)+'\n')
net={str(p.relative_to(r)):json.loads(p.read_text()) for p in sorted((r/'logs').rglob('network-*.json'))}
assert all(x['network_or_listen_attempts']==0 for x in net.values())
(r/'network-receipts.json').write_text(json.dumps(net,indent=2)+'\n')
receipt={'status':'READY_FOR_INDEPENDENT_REVIEW','applied':False,'paths':12,'source_paths':8,'test_paths':4,'native_on':{'pass':63,'red':0,'error':0,'skip':0},'native_off':{'pass':43,'red':20,'expected':True},'original_controls_pass':36,'added_controls':27,'A_added_regression_preserved':True,'predecessor606_rejected_unchanged':True,'primary_base_unchanged':True,'stop_sha':'65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d','static_exits':[0,0,0],'network_receipt_count':len(net),'network_or_listen_attempts':0,'limits':['already-sentHTTP/externalcookiechanges','noactualbrowser/full/deployment','case marks only current result IDs','noaccountwideexport/deletion'],'qualifications':['A originalOFF fails prerequisite, not the606lateoverwrite stage','guard output directory failure and initial19count assumption retained']}
(r/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
selected={}
for p in sorted(r.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(r)
 if rel.parts[0]=='runtime' or rel.name=='READY.json':continue
 assert not p.is_symlink(),str(rel)
 selected[str(rel)]=info(p)
(r/'READY.json').write_text(json.dumps({'status':'READY_FOR_INDEPENDENT_REVIEW','files':selected,'file_count':len(selected),'bytes':sum(x['bytes'] for x in selected.values()),'exclude':'runtime/dependencies/cache/DB'},indent=2)+'\n')
print(json.dumps({'READY_sha':info(r/'READY.json')['sha256'],'files':len(selected),'bytes':sum(x['bytes'] for x in selected.values()),'patch_sha':info(r/'browser-privacy.patch')['sha256'],'AuthGate_sha':files['frontend/src/AuthGate.tsx']['sha256'],'AuthGate_test_sha':files['frontend/src/AuthGate.test.tsx']['sha256'],'receipt_sha':info(r/'receipt.json')['sha256']}))

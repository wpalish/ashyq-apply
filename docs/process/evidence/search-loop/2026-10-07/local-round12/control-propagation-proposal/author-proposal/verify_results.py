from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET
p=Path(__file__).resolve().parent;base=p.parent
A={mode:json.loads((p/'executions'/(mode+'-A')/'outcomes.attempt1.original.json').read_text()) for mode in ('off','on')}
B={mode:json.loads((p/'executions'/(mode+'-B')/'boundaries.original.json').read_text()) for mode in ('off','on')}
oldA=json.loads((base/'a-control-propagation-off-proof/outcomes.attempt1.original.json').read_text())
oldB=json.loads((base/'b-control-propagation-boundaries/boundaries.original.json').read_text())
rows=[]
for old,out,field,tag in [(oldA,A,'cases','A'),(oldB,B,'controls','B')]:
 assert out['off'][field]==old[field],tag+'OFF original drift'
 for i,(off,on) in enumerate(zip(out['off'][field],out['on'][field],strict=True)):
  ordinary=(off.get('kind') is not None and off.get('lane') is None) if tag=='B' else off['case'] not in {'read_cap','checkpoint_busy','run_cancelled','lease_lost','async_cancelled'}
  if ordinary:
   assert off==on,(tag,i,'ordinary equality failed')
   rows.append({'origin':tag,'name':off.get('case',off.get('kind')),'complete_row_and_dispatch_equal':True})
assert len(rows)==12
(p/'whole-output-equality.json').write_text(json.dumps({'ordinary_complete_output_and_dispatch':rows,'ordinary_equalities':12,'A_OFF11_exact_original':True,'B_OFF21_exact_original':True,'qualification':'Imports/source-path provenance differs intentionally by frozen off/on native copy; compared complete semantic control rows, HTTP/request/DNS/query/nativeget effects, not source import paths. A proof preserves original OFF-only description string in both raw modes; actual mode is explicit execution SOURCE_ROOT and imported retrieval SHA.'},indent=2)+'\n')
junit={}
for mode in ('off','on'):
 r=ET.parse(p/'executions'/(mode+'-pytest')/'junit.original.xml').getroot()
 cases=list(r.iter('testcase'));new=[n for n in cases if n.attrib['name'].startswith(('test_native_entry_root_control_','test_native_live_search_caller_'))]
 failures=[n for n in cases if n.find('failure') is not None or n.find('error') is not None]
 old=[n for n in cases if n not in new]
 assert len(cases)==99 and len(new)==18 and len(old)==81
 assert not any(n.find('failure') is not None or n.find('error') is not None for n in old)
 assert len(failures)==(15 if mode=='off' else 0)
 imported=json.loads((p/'executions'/(mode+'-pytest')/'pytest-native-imports.json').read_text())
 assert imported['denied_network_attempts']==0
 for m,row in imported['modules'].items():
  pp=Path(row['path']);assert pp.is_relative_to(p/'replay'/mode/'backend/app')
  assert hashlib.sha256(pp.read_bytes()).hexdigest()==row['sha256']
 junit[mode]={'executed':len(cases),'passed':len(cases)-len(failures),'failed':len(failures),'skipped':sum(n.find('skipped') is not None for n in cases),'original81_allPASS':True,'appended_controls':18,'new_control_failures':len(failures),'network_attempts':0,'failures':[n.attrib['name'] for n in failures]}
(p/'junit-qualification.json').write_text(json.dumps(junit,indent=2)+'\n')
expected=json.loads((p/'replay-source-manifest.json').read_text());matches={}
for mode,files in expected.items():
 for rel,row in files.items():
  pp=p/'replay'/mode/rel;b=pp.read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256'],(mode,rel)
 matches[mode]={'original_manifest_files':len(files),'unchanged':True}
(p/'replay-source-after.json').write_text(json.dumps(matches,indent=2)+'\n')
print(json.dumps({'native_test_summary':junit,'ordinary_whole_output_equalities':12,'OFF_original_rows_exact':True,'source_copies_unchanged':True}))

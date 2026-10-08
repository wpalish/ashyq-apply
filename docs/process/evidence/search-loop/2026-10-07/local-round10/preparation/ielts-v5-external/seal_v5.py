"""Seal external-only candidate; never imports writer/main or app network."""
from pathlib import Path
from datetime import UTC, datetime
import ast
import difflib
import hashlib
import json
import xml.etree.ElementTree as ET

BASE=Path(__file__).resolve().parent
WORK=BASE.parent.parent
REPO=WORK/'ashyq-apply/backend'
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
pins={
 'v4':(WORK/'local-round9/a-ielts-v4-proposal','ready-manifest.json','edf5cadf68f863ddf483d177ce76015cf8ff18c80a2345382714a7c55e30fb83'),
 'B17':(WORK/'local-round9/b-ielts-v4-review','MANIFEST.json','b3ccb628e431cf04af884b3a12a34de549023aae70b115d3a8c07c92f140e79f'),
}
origins={}
for name,(folder,manifest,pin) in pins.items():
 p=folder/manifest
 assert sha(p)==pin,(name,'manifest',sha(p))
 data=json.loads(p.read_text());files=data['files']
 for rel,expected in files.items():
  # Both manifests use path -> SHA mappings.
  assert sha(folder/rel)==expected,(name,rel)
 origins[name]={'manifest_path':str(p),'manifest_sha256':pin,'files_verified':len(files)}
source_records=[]
v4=json.loads((pins['v4'][0]/'ready-manifest.json').read_text())
for rel,expected in v4['files'].items():
 if not rel.startswith('original/'):
  continue
 repo_rel=rel.removeprefix('original/')
 p=REPO/repo_rel
 assert sha(p)==expected,('actual_app_changed',repo_rel)
 q=BASE/rel;q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():
  assert sha(q)==expected
 else:
  q.write_bytes(p.read_bytes())
 source_records.append({'path':str(p),'owned_copy':str(q),'sha256':expected})
for row in json.loads((BASE/'pytest-final.imports.json').read_text())['normal_current_app_dependencies']:
 p=Path(row['path']);assert p.is_relative_to(REPO) and sha(p)==row['sha256']
 source_records.append(row)
for name in ['extraction.py','requirements/web_requirements.py']:
 p=BASE/'proposed/app/adapters'/name
 assert sha(p)==v4['files']['proposed/app/adapters/'+name]
for name in ['A19.original.json','v4-controls.original-input.json','v4-additional.original-input.json','v4-modal-require.original-input.json']:
 assert sha(BASE/name)==v4['files'][name]
for p in (BASE/'tests').glob('*.py'):
 if p.name not in {'test_b17.py','test_v5_grammar.py','test_v5_adverb.py','test_v5_scale.py'}:
  assert sha(p)==v4['files']['tests/'+p.name]
assert sha(BASE/'B17.original.json')=='5609131efe606eeae0b6cc85523d1370ead4c2affb1f107f3510f0e82253d224'
web_tree=ast.parse((BASE/'proposed/app/adapters/requirements/web_requirements.py').read_text())
flags=[n for n in web_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='IELTS_PROSE_SECTION_OWNERSHIP' for t in n.targets)]
assert len(flags)==1 and ast.literal_eval(flags[0].value) is False
parts=[]
for rel in ['app/adapters/extraction.py','app/adapters/requirements/web_requirements.py','app/adapters/requirements/ielts_sections.py']:
 original=REPO/rel;new=BASE/'proposed'/rel
 before=original.read_text().splitlines(keepends=True) if original.exists() else []
 parts.extend(difflib.unified_diff(before,new.read_text().splitlines(keepends=True),fromfile='a/backend/'+rel if original.exists() else '/dev/null',tofile='b/backend/'+rel))
(BASE/'implementation.proposed.diff').write_text(''.join(parts))
old=pins['v4'][0]/'proposed/app/adapters/requirements/ielts_sections.py'
new=BASE/'proposed/app/adapters/requirements/ielts_sections.py'
(BASE/'implementation.v4-to-v5.diff').write_text(''.join(difflib.unified_diff(old.read_text().splitlines(keepends=True),new.read_text().splitlines(keepends=True),fromfile='v4/ielts_sections.py',tofile='v5/ielts_sections.py')))
xml=ET.parse(BASE/'pytest-final.xml').getroot().find('testsuite');assert xml is not None
assert (int(xml.attrib['tests']),int(xml.attrib['failures']),int(xml.attrib['errors']),int(xml.attrib['skipped']))==(229,0,0,0)
compat=json.loads((BASE/'v5.compatibility.offline.json').read_text())
assert compat['summary']['retained_cases']==10 and compat['summary']['synthetic_cases']==134
assert compat['summary']['source_hash_formula_matches_count']==10
calls=sum(len(out['fetcher_calls']) for row in compat['retained']+compat['synthetic'] for out in row['modes'].values());assert calls==720
for log,token in [('ruff-final.log','All checks passed!'),('format-check-final.log','3 files already formatted'),('mypy-final.log','Success: no issues found in 3 source files')]:assert token in (BASE/log).read_text()
receipt={
 'created_utc':datetime.now(UTC).isoformat(),'status':'SEALED_EXTERNAL_V5_READY_FOR_INDEPENDENT_PEER_REVIEW_NOT_APPLIED',
 'source_module_default_false':True,'network_provider_model_calls':0,'repository_edits':0,
 'writeahead_plan_sha256':sha(BASE/'PLAN.json'),'origins_verified_after_tests':origins,'actual_app_sources':source_records,
 'candidate_sources':{str(p.relative_to(BASE)):sha(p) for p in (BASE/'proposed').rglob('*.py')},
 'pytest':{'passed':229,'failed':0,'skipped':0,'seconds':8.93,'warnings':5998,'categories':{'author95':95,'A19':19,'V4':52,'B17_exact':17,'V5_independent':46}},
 'prior_reds_preserved':{'V4_B17':{'passed':7,'failed':10,'log':'pytest-original-B17.log'},'V5_first183':{'passed':182,'failed':1,'log':'pytest-attempt1.log','helper_sha256':sha(BASE/'historical/ielts_sections.v5-attempt1.py')},'neutral_adverb_positions':{'passed':4,'failed':8,'log':'pytest-adverb-original.log','helper_sha256':sha(BASE/'historical/ielts_sections.v5-attempt2-formatted.py')},'full_ratio_atom':{'passed':1,'failed':3,'log':'pytest-scale-original.log','helper_sha256':sha(BASE/'historical/ielts_sections.v5-attempt3.py')}},
 'configured_static':{'ruff':'PASS3sources','format':'PASS3sources','mypy':'PASS3sources'},
 'compatibility':{**compat['summary'],'one_page_mock_fetcher_calls':calls},
 'author_diagnostic_classifier_override_invocations':len(json.loads((BASE/'pytest-final.imports.json').read_text())['diagnostic_classifier_overrides']),
 'not_live_experiment':True,'not_full_pipeline_gain':True,'native_unknown_permission_unchanged':True,
 'future_peer_commands':['Copy/snapshot this sealed candidate into a NEW owned peer output folder; do not rerun its writer tests inside sealed BASE.', 'REVIEW_ATTEMPT=v5-peer .venv/bin/python -m pytest <newcopy>/tests -q --basetemp=<newcopy>/pytest-peer --junitxml=<newcopy>/pytest-peer.xml', '.venv/bin/python <newcopy>/capture_v5.py', 'Verify exact candidate/app/immutable origin hashes before tests; native classification overrides remain0 outside separately labeled author diagnostics.'],
}
write(BASE/'receipt.json',receipt)
selected=[]
for p in BASE.rglob('*'):
 if not p.is_file() or p.name=='ready-manifest.json':continue
 rel=p.relative_to(BASE)
 if any(x.startswith(('mypy-cache','pytest-attempt','pytest-final','pytest-adverb-original','pytest-scale-original','pytest-original-B17')) and p.is_relative_to(BASE/x) for x in rel.parts if (BASE/x).is_dir()):continue
 if any(x in {'__pycache__','.pytest_cache'} for x in rel.parts) or p.suffix in {'.pyc','.db'}:continue
 selected.append(p)
manifest={'status':receipt['status'],'helper_sha256':sha(new),'patch_sha256':sha(BASE/'implementation.proposed.diff'),'receipt_sha256':sha(BASE/'receipt.json'),'tests_pass':229,'tests_fail':0,'tests_skip':0,'source_default_false':True,'network_provider_model_calls':0,'selected_files':len(selected),'selected_bytes':sum(p.stat().st_size for p in selected),'files':{str(p.relative_to(BASE)):sha(p) for p in sorted(selected)}}
write(BASE/'ready-manifest.json',manifest)
print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2));print('manifest_sha256='+sha(BASE/'ready-manifest.json'))

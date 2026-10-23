import hashlib,importlib.util,json,sys,shutil
from pathlib import Path
from dataclasses import asdict
root=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20');out=root/'work/search-loop-round6';repo=root/'work/ashyq-apply'
sys.path.insert(0,str(repo/'backend'))
from app.adapters import page_classifier as legacy

def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
b=module('root_frozen_b_cases',out/'reviews/expert_b/revision2/replay_classifier.py')
a=module('root_frozen_a_tests',out/'reviews/expert_a/revision3/test_funding_discovery.py')
controls=[]
for name,url,html,expected in b.controls():
 if name=='programme_secondary_faq':expected='scholarship_faq'
 controls.append(dict(name='b_'+name,url=url,html=html,expected=expected,off=asdict(legacy.classify_page(url=url,html=html))))
for name,html,url,expected in a.CONTROLS:
 controls.append(dict(name='a_'+name,url=url,html=html,expected=expected,off=asdict(legacy.classify_page(url=url,html=html))))
fixture=dict(frozen_classifier_sha256=hashlib.sha256((repo/'backend/app/adapters/page_classifier.py').read_bytes()).hexdigest(),accepts={k:sorted(x.value for x in v) for k,v in legacy.ACCEPTS.items()},controls=controls,original_a_controls=a.ORIGINAL)
(out/'programme_funding_scope.fixture.json').write_text(json.dumps(fixture,indent=2,ensure_ascii=False)+'\n')
manifest=json.loads((out/'reviews/expert_a/review-start.manifest.json').read_text())
shutil.copy2(manifest['wits_body_original'],out/'wits-programme.html');shutil.copy2(manifest['wits_metadata_original'],out/'wits-programme.meta.json')
t=(out/'reviews/expert_a/revision3/test_funding_discovery.py').read_text()
s=t.index('ROOT=');e=t.index("MARKER=",s)
t=t[:s]+'''ROOT=Path(__file__).resolve().parent/'fixtures/programme_funding'
SNAPSHOTS=json.loads((ROOT/'scope-controls.json').read_text())
OFF={(x['url'],x['html']):x['off'] for x in SNAPSHOTS['controls']}
ORIGINAL=SNAPSHOTS['original_a_controls']
''' +t[e:]
s=t.index('NEW_CONTROLS=');e=t.index('\n\ndef denied',s)
t=t[:s]+"CONTROLS=[(x['name'],x['html'],x['url'],x['expected']) for x in SNAPSHOTS['controls']]"+t[e:]
t=t.replace("asdict(legacy.classify_page(url=url,html=html))","OFF[(url,html)]").replace("old=legacy.classify_page(url=url,html=html)","old=OFF[(url,html)]").replace("old.page_type.value=='scholarship_index'","old['page_type']=='scholarship_index'").replace('asdict(result)==asdict(old)','asdict(result)==old').replace('classifier.ACCEPTS==legacy.ACCEPTS',"classifier.ACCEPTS=={k:frozenset(v) for k,v in SNAPSHOTS['accepts'].items()}")
s=t.index('    raw=Path(MANIFEST');e=t.index("    html=raw.decode",s)
t=t[:s]+'''    raw=(ROOT/'wits-programme.html').read_bytes()
    mp=ROOT/'wits-programme.meta.json';meta=json.loads(mp.read_text())
    assert hashlib.sha256(raw).hexdigest()=='88d1f716c82840fa66317ff1ceb42a152439a924d7625c0d2ef18a0f315f0a87'
    assert hashlib.sha256(mp.read_bytes()).hexdigest()=='d54f742c251cd9cd36c06ee4b89a74a7c1ca701b829b5ffa99d6cc5701096b8c'
''' +t[e:]
t=t.replace('legacy._title(legacy._parse_markup(html))','classifier._title(classifier._parse_markup(html))')
t=t.replace('import importlib.util\n','').replace('import sys\n','')
(out/'test_programme_funding_scope.proposed.py').write_text(t)
print(json.dumps({'frozen_controls':len(controls),'legacy_source':fixture['frozen_classifier_sha256'],'body_bytes':(out/'wits-programme.html').stat().st_size,'repo_edits':0}))

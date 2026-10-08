# -*- coding: utf-8 -*-
"""Offline loss locator, not an executable rule proposal or quality score."""
from pathlib import Path
import json,hashlib,importlib.util,sys
from dataclasses import asdict
from datetime import datetime,timezone
P=Path(__file__).resolve().parent
R=P.parents[1]/'ashyq-apply'
B=P.parents[1]/'local-round10/b-aalto-source-funnel'
S=R/'backend/app/adapters/page_classifier.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S)=='7c74866f7fe562077be36bb33379434d7e378985ccfe75f170fa94fb38746c9c'
STOP=P.parents[1]/'local-round7/provider-STOP.json';assert sha(STOP)=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
assert sha(B/'MANIFEST.json')=='90a27182835b19be19e8b0523c93d8a258f697446b845ec2995f6a543522554f'
plan={'status':'OFFLINE_ABLATION_LOSS_LOCATOR_NOT_RULE','created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':sha(S),'source_head':'7c74a12d71bd00228014c11d194928d223e110be','global_STOP_sha256':sha(STOP),'scope':'Compare unchanged native classifier with external one-line primary-title/identity irrelevant vocabulary ablation. No reader eligibility expansion/application flag/claims/routing/class override/live/labels/score. Ablation is diagnostic only, never apply. Use saved public HTML and synthetic negatives; no Fetcher or provider construction.'}
(P/'PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
source=S.read_text();assert source.count('if _IRRELEVANT.search(low_head):')==1
(P/'page_classifier.original.py').write_bytes(S.read_bytes())
(P/'page_classifier.ablation.py').write_text(source.replace('if _IRRELEVANT.search(low_head):','if _IRRELEVANT.search(" ".join([title, identity]).lower()):'))
sys.path.insert(0,str(R/'backend'))
from app.adapters.page_classifier import classify_page as native
spec=importlib.util.spec_from_file_location('root_primary_ablation',P/'page_classifier.ablation.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
rows=[];origins={}
for meta in sorted((B/'public-cache').glob('*.meta.json')):
 d=json.loads(meta.read_text())
 if 'text/html' not in d['content_type']:continue
 body=meta.with_name(meta.name.replace('.meta.json','.body'));html=body.read_bytes().decode(d.get('encoding') or 'utf-8')
 orig=asdict(native(url=d['final_url'],html=html));abl=asdict(m.classify_page(url=d['final_url'],html=html))
 origins[str(meta.relative_to(B))]=sha(meta);origins[str(body.relative_to(B))]=sha(body)
 rows.append({'url':d['url'],'final_url':d['final_url'],'original':orig,'ablation':abl,'whole_output_equal':orig==abl,'ablation_accepts_requirements':m.classify_page(url=d['final_url'],html=html).accepts('requirements')})
expected=json.loads((B/'page-purpose.offline.json').read_text());lookup={d['url']:d['classification'] for d in expected};assert all(r['original']==lookup[r['url']] for r in rows)
fixtures=[('job-with-degree-identity','<main><h1>BSc Computer Science</h1><p>This job requires applicants to hold a bachelor degree. This is a recruitment listing, no degree programme is offered.</p><h2>Contact us</h2></main>'),('primary-contact','<main><h1>Contact us</h1><h2>BSc Computer Science</h2><p>The bachelor programme lasts three years.</p></main>'),('secondary-recruitment','<main><h1>BSc Computer Science</h1><p>This role requires a bachelor degree.</p><h2>Recruitment</h2></main>')]
negatives=[]
for name,html in fixtures:
 a=native(url='https://uni.test/study/cs',html=html);b=m.classify_page(url='https://uni.test/study/cs',html=html)
 negatives.append({'id':name,'html':html,'original':asdict(a),'ablation':asdict(b),'new_programme_acceptance':a.page_type.value=='irrelevant' and b.page_type.value in ('program_detail','intake_specific_program')})
changed=[r for r in rows if not r['whole_output_equal']]
aalto=next(r for r in rows if r['url']=='https://www.aalto.fi/en/admission-services')
raw={'status':'DIAGNOSTIC_NO_RULE_READY','public_html_cases':len(rows),'changed_cases':len(changed),'whole_output_equal_cases':sum(r['whole_output_equal'] for r in rows),'cases':rows,'synthetic_counterexamples':negatives,'native_original_reproduction_equal':True,'native_imports_only_except_explicit_external_ablation':True,'network_provider_model_calls':0,'semantic_labels_read':False,'scoring_executed':False,'application_source_changed':False,'input_origins_sha256':origins,'decision':'Do not apply primary-only irrelevant relaxation; inspect downstream funding/other-purpose priority and strict own purpose before any scoped rule.'}
(P/'controls.original.json').write_text(json.dumps(raw,indent=2,default=str)+'\n')
assert sha(S)==plan['source_sha256'] and sha(STOP)==plan['global_STOP_sha256']
print(json.dumps({'public_html_cases':len(rows),'changed_cases':len(changed),'aalto_original_type':aalto['original']['page_type'],'aalto_ablation_type':aalto['ablation']['page_type'],'aalto_ablation_accepts_requirements':aalto['ablation_accepts_requirements'],'new_synthetic_programme_acceptances':sum(n['new_programme_acceptance'] for n in negatives),'source_STOP_unchanged':True},default=str))

"""Independent actual caller controls; copied candidate only; zero network."""
from pathlib import Path
import asyncio
import hashlib
import json
import subprocess

BASE=Path(__file__).resolve().parent
SOURCE=BASE.parent/'a-ielts-v5-proposal'
PIN='1de653d920992de184329744dc3493dd662332a9cf72d3fbc47bbbae4761c83f'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE/'ready-manifest.json')==PIN
manifest=json.loads((SOURCE/'ready-manifest.json').read_text())
for name,digest in manifest['files'].items():assert sha(SOURCE/name)==digest
assert sha(BASE/'proposed/app/adapters/requirements/ielts_sections.py')==manifest['helper_sha256']
def denied(*a,**k):raise AssertionError('No process/network provider in independent reader review')
subprocess.run=subprocess.Popen=subprocess.check_output=denied
import replay_proposal as replay
from app.domain.claim_verifier import is_verbatim_excerpt
assert not (BASE/'independent-controls.original.json').exists()
inputs=json.loads((BASE/'independent-inputs.original.json').read_text())
results=[]
for case in inputs:
    body='<html><head><title>Bachelor admission requirements</title></head><body><main><h1>Bachelor admission requirements</h1>'+case['inner']+'</main></body></html>'
    outputs=[asyncio.run(replay.read('https://admissions.example.edu/admission-requirements',body,domain='example.edu',**kwargs)) for kwargs in ({'old':True},{'on':False},{'on':True},{'on':True},{'on':False})]
    vals=lambda out:{c['claim_type']:c['normalized_value'] for c in out['claims'] if c['claim_type'].startswith('ielts_')}
    scope_matches=[all(c.get('scope',{}).get(k)==v for k,v in case.get('scope',{}).items()) for c in outputs[2]['claims'] if c['claim_type'].startswith('ielts_')]
    scope_pass=all(scope_matches)
    guards={'old_off_whole_equal':outputs[0]==outputs[1]==outputs[4],
            'on_repeat_whole_equal':outputs[2]==outputs[3],
            'classes_unchanged':[o['page_type'] for o in outputs[0]['page_outcomes']]==[o['page_type'] for o in outputs[2]['page_outcomes']],
            'actual_native_admitted':all(o['page_type']!='unknown' for o in outputs[2]['page_outcomes']),
            'one_get_each':all(len(o['fetcher_calls'])==1 for o in outputs),
            'contiguous_quotes':all(is_verbatim_excerpt(c['original_text_excerpt'],replay.readable_text(body)) for c in outputs[2]['claims']),
            'scope_expected':scope_pass}
    results.append({**case,'body':body,'old':outputs[0],'off':outputs[1],'on':outputs[2],'observed':vals(outputs[2]),'old_observed':vals(outputs[0]),'passed':vals(outputs[2])==case['expected'] and all(guards.values()),'guards':guards})
    (BASE/'independent-controls.original.json').write_text(json.dumps({'manifest_sha256':PIN,'helper_sha256':manifest['helper_sha256'],'normal_actual_app_dependencies':True,'classifier_overrides':replay.DIAGNOSTIC_OVERRIDES,'network_provider_model_calls':0,'results':results},indent=2)+'\n')
assert not replay.DIAGNOSTIC_OVERRIDES
for name,digest in manifest['files'].items():assert sha(SOURCE/name)==digest
print('controls',len(results),'PASS',sum(r['passed'] for r in results),'RED',sum(not r['passed'] for r in results))
for r in results:
    if not r['passed']:print(r['case'],'expected',r['expected'],'actual',r['observed'],'old',r['old_observed'],'failed_guards',[k for k,v in r['guards'].items() if not v])

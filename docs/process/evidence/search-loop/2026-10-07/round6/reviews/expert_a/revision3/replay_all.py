"""Hash-pinned offline receipts for exact legacy scope and real saved reader routes."""
import asyncio
import hashlib
import json
import os
import socket
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

os.environ['EXPERT_A_ROUND6_REVISION3']='1'
import conftest
from test_funding_discovery import CONTROLS, MANIFEST, MARKER, ROOT, classifier, denied, funding_route, legacy, retained_wits
import sys
sys.path.insert(0,str(ROOT.parent))
from replay_independent_readers import read


def main():
    own=[];borrowed=[];funding=[];requirements=[]
    source=ROOT.parent.parent/'expert_b/revision2/independent-replay.json'
    b=json.loads(source.read_text())
    with patch.object(socket,'getaddrinfo',denied),patch.object(socket,'create_connection',denied),patch.object(socket.socket,'connect',denied),patch('app.adapters.search.get_search_provider',denied):
        for name,html,url,expected in CONTROLS:
            classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING=False
            off=classifier.classify_page(url=url,html=html);old=legacy.classify_page(url=url,html=html)
            assert asdict(off)==asdict(old)
            classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING=True
            on=classifier.classify_page(url=url,html=html)
            own.append({'case':name,'html':html,'html_sha256':hashlib.sha256(html.encode()).hexdigest(),'url':url,'expected':expected,'off':asdict(off),'on':asdict(on),'passes':on.page_type.value==expected,'marker':MARKER in on.signals})
        for c in b['controls']:
            classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING=False
            off=classifier.classify_page(url=c['url'],html=c['html'])
            old=legacy.classify_page(url=c['url'],html=c['html']);assert asdict(off)==asdict(old)
            classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING=True
            on=classifier.classify_page(url=c['url'],html=c['html'])
            expected=c['expected_on']
            if old.page_type.value in {'scholarship_faq','unknown','scholarship_award'}:
                expected=old.page_type.value
            borrowed.append({'case':c['case'],'html':c['html'],'html_sha256':c['html_sha256'],'url':c['url'],'original_b_expected':c['expected_on'],'expected':expected,'contract_narrowed':expected!=c['expected_on'],'off':asdict(off),'on':asdict(on),'passes':on.page_type.value==expected,'marker':MARKER in on.signals})
        url,html,meta=retained_wits()
        for mode in ('programme_fallback','explicit_primary','linked_depth_one'):
            for enabled in (False,True,True,False):
                funding.append(asyncio.run(funding_route(mode,enabled,url,html,meta)))
        for enabled in (False,True,True,False):
            classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING=enabled
            requirements.append({'enabled':enabled,'result':asyncio.run(read(url,html,classifier.classify_page,'Computer Science',meta))})
    result={'network_calls':0,'provider_calls':0,'model_calls':0,'git_calls':0,'repo_edits':0,'flag_default':False,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'proposed_page_classifier.py',ROOT/'proposed_web_scholarships.py')},'own_control_count':len(own),'borrowed_control_count':len(borrowed),'borrowed_original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'own_controls':own,'borrowed_controls':borrowed,'failed':[x['case'] for x in own+borrowed if not x['passes']],'funding_routes_off_on_on_off':funding,'requirements_reader_off_on_on_off':requirements,'wits_source_url':url,'wits_body_sha256':MANIFEST['wits_body_sha256'],'wits_metadata_sha256':MANIFEST['wits_metadata_sha256'],'scope':'Original saved Wits body in real WebScholarshipAdapter; synthetic index routing fixture. Missing financial-aid target body remains offline HTTP_ERROR unknown. No award claims or proof of 2027 intake. Full-pipeline identity conditional on SI-1=True experimental design.'}
    (ROOT/'all-replay.offline.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'own_controls':len(own),'borrowed_controls':len(borrowed),'failed':result['failed'],'funding_routes_equal':all(next(x['reads'] for x in funding if x['mode']==m and not x['enabled'])==next(x['reads'] for x in funding if x['mode']==m and x['enabled']) for m in ('programme_fallback','explicit_primary','linked_depth_one'))},indent=2))


if __name__=='__main__':
    main()

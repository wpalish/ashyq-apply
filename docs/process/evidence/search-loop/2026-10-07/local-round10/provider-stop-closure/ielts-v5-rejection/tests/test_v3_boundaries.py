"""Independent red seams of the new v3 grammar, through actual admitted verify."""
import asyncio,pytest
import replay_proposal as replay
from replay_v3_boundaries import CASES,IELTS
from app.domain.claim_verifier import is_verbatim_excerpt
@pytest.mark.parametrize('case',CASES,ids=lambda c:c[0])
def test_v3_new_boundaries(case):
 name,inner,expected=case
 body='<html><head><title>Bachelor admission requirements</title></head><body><main><h1>Bachelor admission requirements</h1>'+inner+'</main></body></html>'
 out=asyncio.run(replay.read('https://admissions.example.edu/admission-requirements',body,domain='example.edu',on=True))
 assert len(out['fetcher_calls'])==1 and all(o['page_type']!='unknown' for o in out['page_outcomes'])
 claims={c['claim_type']:c for c in out['claims'] if c['claim_type'] in IELTS}
 numbers={k:c['normalized_value'] for k,c in claims.items() if k!='ielts_accepted_types'}
 assert numbers==expected
 if not expected:assert not claims
 for c in claims.values():
  assert is_verbatim_excerpt(c['original_text_excerpt'],replay.readable_text(body))
 if name=='each_component_qualification_year':
  c=claims['ielts_min_subscore']
  assert c['scope']['qualification']=='A-levels'
  assert c['scope']['academic_year']==c['academic_year']=='2024/25'
  assert 'A-level applicants academic year 2024/25' in c['original_text_excerpt']

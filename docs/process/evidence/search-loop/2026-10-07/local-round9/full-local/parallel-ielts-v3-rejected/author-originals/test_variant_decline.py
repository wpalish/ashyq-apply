"""Reject variant refusal contamination introduced by accepted-type grammar."""
import asyncio,pytest
import replay_proposal as replay
from replay_variant_decline import CASES
from app.domain.claim_verifier import is_verbatim_excerpt
@pytest.mark.parametrize('case',CASES,ids=lambda c:c[0])
def test_refused_variant_is_not_other_variant_permission(case):
 name,inner,expected=case
 body='<html><head><title>Bachelor admission requirements</title></head><body><main><h1>Bachelor admission requirements</h1>'+inner+'</main></body></html>'
 out=asyncio.run(replay.read('https://admissions.example.edu/admission-requirements',body,domain='example.edu',on=True))
 assert len(out['fetcher_calls'])==1 and all(o['page_type']!='unknown' for o in out['page_outcomes'])
 values={c['claim_type']:c['normalized_value'] for c in out['claims'] if c['claim_type'].startswith('ielts_')}
 assert values==expected
 for c in out['claims']:assert is_verbatim_excerpt(c['original_text_excerpt'],replay.readable_text(body))

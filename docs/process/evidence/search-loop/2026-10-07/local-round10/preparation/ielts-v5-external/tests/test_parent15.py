"""Parent independent grammar regressions through native admitted verify."""
import asyncio,pytest
import replay_parent15 as parent
import replay_proposal as replay
from app.domain.claim_verifier import is_verbatim_excerpt
@pytest.mark.parametrize('case',parent.CASES,ids=lambda c:c['case'])
def test_parent_exact15(case):
    out=asyncio.run(replay.read('https://admissions.example.edu/admission-requirements',case['body'],domain='example.edu',on=True))
    assert len(out['fetcher_calls'])==1 and all(o['page_type']!='unknown' for o in out['page_outcomes'])
    claims={c['claim_type']:c['normalized_value'] for c in out['claims'] if c['claim_type'] in parent.IELTS}
    for key,value in case['expected'].items():
        if key=='all_ielts_absent':assert not claims
        else:assert claims.get(key)==value
    for c in out['claims']:
        assert is_verbatim_excerpt(c['original_text_excerpt'],replay.readable_text(case['body']))

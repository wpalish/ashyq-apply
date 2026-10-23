"""Independent semantic pairs using native unmodified page permission."""
import asyncio
import json

import pytest

import replay_proposal as replay
from app.domain.claim_verifier import is_verbatim_excerpt

CASES = json.loads((replay.BASE / 'v5-scale.original-input.json').read_text())
RESULTS = []


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['case'])
def test_v5_full_ratio_atom(case):
    body = '<html><head><title>Bachelor admission requirements</title></head><body><main><h1>Bachelor admission requirements</h1>' + case['inner'] + '</main></body></html>'
    outputs = [asyncio.run(replay.read('https://admissions.example.edu/admission-requirements', body, domain='example.edu', **kw)) for kw in ({'old': True}, {'on': False}, {'on': True})]
    values = {c['claim_type']: c['normalized_value'] for c in outputs[2]['claims'] if c['claim_type'].startswith('ielts_')}
    RESULTS.append({**case, 'body': body, 'old': outputs[0], 'off': outputs[1], 'on': outputs[2], 'observed': values, 'passed': values == case['expected']})
    (replay.BASE / (__import__('os').environ.get('REVIEW_ATTEMPT', 'v4-unknown') + '.v5scale.json')).write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2) + '\n')
    assert outputs[0] == outputs[1]
    assert all(o['page_type'] != 'unknown' for o in outputs[2]['page_outcomes'])
    assert [o['page_type'] for o in outputs[0]['page_outcomes']] == [o['page_type'] for o in outputs[2]['page_outcomes']]
    assert len(outputs[2]['fetcher_calls']) == 1
    for c in outputs[2]['claims']:
        assert is_verbatim_excerpt(c['original_text_excerpt'], replay.readable_text(body))
        if c['claim_type'].startswith('ielts_'):
            assert c['academic_year'] is None and c['intake'] is None
            assert c['scope']['academic_year'] is None and c['scope']['intake'] is None
    assert values == case['expected']

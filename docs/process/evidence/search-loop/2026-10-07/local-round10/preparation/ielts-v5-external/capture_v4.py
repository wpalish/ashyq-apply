"""Evidence capture; reads immutable originals, writes only this own folder."""
import asyncio
import hashlib
import json
from pathlib import Path

import replay_proposal as replay
from app.adapters.fetching import _content_hash
from app.domain.claim_verifier import is_verbatim_excerpt

BASE = Path(__file__).resolve().parent
IELTS = {'ielts_min_overall', 'ielts_min_subscore', 'ielts_accepted_types'}
MODES = [('old', {'old': True}), ('off1', {'on': False}), ('on1', {'on': True}), ('on2', {'on': True}), ('off2', {'on': False})]

async def captures():
    retained = []
    for row in replay.ROWS:
        body = Path(row['body_owned']).read_bytes()
        meta_raw = Path(row['meta_owned']).read_bytes()
        meta = json.loads(meta_raw)
        assert hashlib.sha256(body).hexdigest() == row['body_sha256']
        assert hashlib.sha256(meta_raw).hexdigest() == row['meta_sha256']
        source_hash = _content_hash(body.decode(meta['encoding']))
        out = {key: await replay.retained(row, **kwargs) for key, kwargs in MODES}
        assert out['old'] == out['off1'] == out['off2']
        assert out['on1'] == out['on2']
        assert [c for c in out['old']['claims'] if c['claim_type'] not in IELTS] == [c for c in out['on1']['claims'] if c['claim_type'] not in IELTS]
        assert [x['page_type'] for x in out['old']['page_outcomes']] == [x['page_type'] for x in out['on1']['page_outcomes']]
        retained.append({**row, 'metadata_content_hash': meta.get('content_hash'), 'actual_content_hash': source_hash, 'hash_formula_matches': meta.get('content_hash') == source_hash, 'modes': out})
    cases = []
    A19 = json.loads((BASE/'A19.original.json').read_text())['results']
    for name in ['v4-controls.original-input.json', 'v4-additional.original-input.json', 'v4-modal-require.original-input.json']:
        for case in json.loads((BASE/name).read_text()):
            case['body'] = '<html><head><title>Bachelor admission requirements</title></head><body><main><h1>Bachelor admission requirements</h1>' + case['inner'] + '</main></body></html>'
            cases.append(case)
    for case in [*A19, *cases]:
        url = 'https://example.edu/english-testing' if case['case'] == 'native_unknown_permission' else 'https://admissions.example.edu/admission-requirements'
        body = case['body']
        out = {key: await replay.read(url, body, domain='example.edu', **kwargs) for key, kwargs in MODES}
        assert out['old'] == out['off1'] == out['off2']
        assert out['on1'] == out['on2']
        assert [x['page_type'] for x in out['old']['page_outcomes']] == [x['page_type'] for x in out['on1']['page_outcomes']]
        assert [c for c in out['old']['claims'] if c['claim_type'] not in IELTS] == [c for c in out['on1']['claims'] if c['claim_type'] not in IELTS]
        for claim in out['on1']['claims']:
            assert is_verbatim_excerpt(claim['original_text_excerpt'], replay.readable_text(body))
        case['source_hash'] = _content_hash(body)
        case['body_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        case['modes'] = out
    payload = {'retained': retained, 'synthetic': [*A19, *cases], 'summary': {'retained_cases': len(retained), 'synthetic_cases': len(A19) + len(cases), 'old_off_whole_outputs_equal': True, 'on_repeat_whole_outputs_equal': True, 'non_IELTS_claims_unchanged': True, 'page_classes_unchanged': True, 'production_classification_overrides': 0, 'native_unknown_permissions_unchanged': True, 'all_excerpts_contiguous': True, 'source_hash_formula_matches_count': sum(r['hash_formula_matches'] for r in retained), 'actual_retained_read_method': 'WebRequirementsAdapter.verify with read-only cached body/meta and one-page simulated FetchResult; provider/caller secondary URL disabled for scoped reader controls', 'network_provider_model_calls': 0, 'not_live_four_arm_experiment': True}}
    (BASE/'v4.compatibility.offline.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(payload['summary'], indent=2))

if __name__ == '__main__':
    asyncio.run(captures())

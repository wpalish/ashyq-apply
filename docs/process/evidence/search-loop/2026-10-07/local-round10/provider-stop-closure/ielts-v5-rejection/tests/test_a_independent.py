import asyncio,json
from pathlib import Path
import pytest
import replay_proposal as replay
A=json.loads((replay.BASE/'A19.original.json').read_text())['results']
TYPES={'ielts_min_overall','ielts_min_subscore','ielts_accepted_types'}

@pytest.mark.parametrize('case',A,ids=lambda c:c['case'])
def test_a19_preserved_input_with_qualified_year_ambiguity(case):
 url='https://example.edu/english-testing' if case['case']=='native_unknown_permission' else 'https://admissions.example.edu/admission-requirements'
 outputs=[asyncio.run(replay.read(url,case['body'],domain='example.edu',**kw)) for kw in ({'old':True},{'on':False},{'on':True})]
 assert outputs[0]==outputs[1]
 assert [o['page_type'] for o in outputs[0]['page_outcomes']]==[o['page_type'] for o in outputs[2]['page_outcomes']]
 values={c['claim_type']:c['normalized_value'] for c in outputs[2]['claims'] if c['claim_type'] in TYPES}
 if case['case']=='native_unknown_permission':
  assert not values and outputs[2]['page_outcomes'][0]['page_type']=='unknown'
 elif case['case']=='local_year_title_conflict':
  # Original raw RED remains. Parent-qualified ambiguity is None, not assumed2024.
  assert values['ielts_min_overall']==6.5
  assert all(c['academic_year'] is None and c['scope']['academic_year'] is None for c in outputs[2]['claims'] if c['claim_type'] in TYPES)
 elif not case['expected_numeric']:assert not values
 else:
  for k,v in case['expected_numeric'].items():assert values.get(k)==v

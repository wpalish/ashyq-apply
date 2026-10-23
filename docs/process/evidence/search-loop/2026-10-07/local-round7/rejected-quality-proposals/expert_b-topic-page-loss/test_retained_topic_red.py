"""Retained actual-reader red controls, diagnostic permission is never a proposal."""
import asyncio
import json
from pathlib import Path
import pytest
from replay_reader_boundary import BASE, one

ROWS=json.loads((BASE/'original-cache-receipt.json').read_text())['pages']
ENGLISH=[r for r in ROWS if 'english-language' in r['url']]
REJECTED=[r for r in ROWS if 'english-language' in r['url'] or r['url'].endswith('deadlines')]

def read(row, force=False):return asyncio.run(one(row,force))
def claims(row, claim_type):return [c for c in read(row,True)['claims'] if c['claim_type']==claim_type]

@pytest.mark.parametrize('row',REJECTED,ids=lambda r:r['url'])
def test_exact_four_baseline_rejections_reproduced(row):
    result=read(row)
    assert result['claims']==[]
    assert result['outcomes'][0]['category']=='classifier-rejected'
    assert result['outcomes'][0]['page_type']=='unknown'

@pytest.mark.parametrize('row',ENGLISH,ids=lambda r:r['url'])
def test_subscore_excerpt_must_belong_to_ielts_not_cael(row):
    cs=claims(row,'ielts_min_subscore')
    assert len(cs)==1
    excerpt=cs[0]['original_text_excerpt'].lower()
    assert 'ielts' in excerpt and 'cael' not in excerpt, cs[0]

@pytest.mark.parametrize('row',ENGLISH,ids=lambda r:r['url'])
def test_sibling_ib_qualification_must_not_scope_ielts_claim(row):
    cs=claims(row,'ielts_min_overall')
    assert len(cs)==1 and cs[0]['normalized_value']==6.5
    assert cs[0]['scope']['qualification'] is None, cs[0]


def test_document_supplementary_deadline_must_not_be_application_deadline():
    row=next(r for r in ROWS if '/admissions/dates-deadlines' in r['url'])
    cs=claims(row,'admission_deadline')
    assert not any(c['normalized_value']=='2027-02-01' for c in cs), cs


def test_review_of_applications_does_not_prove_credential_evaluation():
    row=next(r for r in ROWS if r['url']=='https://future.utoronto.ca/deadlines')
    assert not claims(row,'credential_evaluation_required')


def test_accepted_programme_control_unchanged_by_diagnostic():
    row=next(r for r in ROWS if r['url'].endswith('/computer-science'))
    off,on=read(row),read(row,True)
    assert off['claims']==on['claims']
    assert any(c['claim_type']=='program_exists' for c in off['claims'])


def test_accepted_apply_hub_stays_no_requirement_claims():
    row=next(r for r in ROWS if r['url']=='https://future.utoronto.ca/apply')
    off,on=read(row),read(row,True)
    assert off['claims']==on['claims']==[]
    assert off['outcomes'][0]['page_type']=='general_admissions'

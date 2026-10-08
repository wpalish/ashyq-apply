"""Offline actual verify caller controls, independent of classifier permission."""
import asyncio
from pathlib import Path

import pytest

import replay_proposal as replay
from app.domain.claim_scope import RequestedScope
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.programme_identity import Verdict

URL = 'https://admissions.example.edu/admission-requirements'
TYPES = {'ielts_min_overall', 'ielts_min_subscore', 'ielts_accepted_types'}

def html(inner, title='Bachelor admission requirements'):
    return f'<html><head><title>{title}</title></head><body><main><h1>{title}</h1>{inner}</main></body></html>'

def read(inner, *, on=True, title='Bachelor admission requirements'):
    body = html(inner, title)
    out = asyncio.run(replay.read(URL, body, domain='example.edu', on=on))
    assert out['page_outcomes'][0]['category'] in {'fetched-ok', 'no-pattern-match'}, out
    assert out['page_outcomes'][0]['page_type'] != 'unknown', out
    assert len(out['fetcher_calls']) == 1
    # Intake/programme unknowns are honest unrelated caller outputs, not read failures.
    for claim in out['claims']:
        assert is_verbatim_excerpt(claim['original_text_excerpt'], replay.readable_text(body))
    return out

def ielts(out):
    return {c['claim_type']: c for c in out['claims'] if c['claim_type'] in TYPES}

def value(out, key='ielts_min_overall'):
    return ielts(out)[key]['normalized_value']

@pytest.mark.parametrize('prefix', ['CAEL overall 60, no part below 60.', 'TOEFL overall 100, no part below 20.', 'Duolingo overall 120, no part below 100.'])
def test_other_exams_are_not_ielts(prefix):
    assert not ielts(read(f'<h2>English tests</h2><p>{prefix}</p>'))

def test_actual_admitted_caller_prevents_cael_prefix_and_sibling_ib_scope():
    inner = ('<h2>CAEL</h2><p>CAEL overall 60, no part below 60.</p>'
             '<h2>International Baccalaureate</h2><p>English at grade 5.</p>'
             '<h2>IELTS Academic</h2><p>Minimum overall 6.5 with no part below 6.0.</p>')
    old = read(inner, on=False)
    assert value(old, 'ielts_min_subscore') == 6.0
    assert 'CAEL' in ielts(old)['ielts_min_subscore']['original_text_excerpt']
    assert ielts(old)['ielts_min_overall']['scope']['qualification'] == 'IB'
    fixed = read(inner)
    assert value(fixed) == 6.5
    assert value(fixed, 'ielts_min_subscore') == 6.0
    for c in ielts(fixed).values():
        assert 'IELTS' in c['original_text_excerpt']
        assert 'CAEL' not in c['original_text_excerpt']
        assert c['scope']['qualification'] is None
        assert c['scope']['academic_year'] is None

@pytest.mark.parametrize('bad', ['60', '6.5001', '106.5', '16.5', '.65'])
def test_whole_numeric_atom_is_never_prefix_sliced(bad):
    out = read(f'<h2>IELTS</h2><p>Minimum overall {bad} with no part below {bad}.</p>')
    claims = ielts(out)
    # The domain verifier rejects fractional bands; no rounding/prefix claim.
    assert not {'ielts_min_overall', 'ielts_min_subscore'} & claims.keys()

@pytest.mark.parametrize('wording', [
    '<h2>IELTS Academic</h2><p>Minimum overall 6.50. No part below 6.0.</p>',
    '<p>IELTS Academic requires overall 6.50 with no part below 6.0.</p>',
    '<section><h2>IELTS Academic</h2><p>Minimum overall 6.50 with no part below 6.0.</p></section>',
])
def test_owned_heading_same_statement_and_sentence_period(wording):
    out = read(wording)
    assert value(out) == 6.5
    # A separate unlabelled sentence is not itself an IELTS statement.
    if wording.startswith('<p>'):
        assert value(out, 'ielts_min_subscore') == 6.0

@pytest.mark.parametrize('inner', [
    '<h2>IELTS</h2><section><p>Minimum overall 6.0 with no part below 6.0.</p></section>',
    '<h2>IELTS</h2><h2>TOEFL</h2><p>Minimum overall 6.0 with no part below 6.0.</p>',
    '<aside><h2>IELTS</h2></aside><p>Minimum overall 6.0 with no part below 6.0.</p>',
    '<nav><h2>IELTS</h2><p>Minimum overall 6.0.</p></nav><p>Minimum overall 6.0.</p>',
    '<div role="navigation"><h2>IELTS</h2><p>Minimum overall 6.0.</p></div><p>Minimum overall 6.0.</p>',
    '<div class="menu-links"><h2>IELTS</h2><p>Minimum overall 6.0.</p></div><p>Minimum overall 6.0.</p>',
])
def test_sibling_regions_equal_heading_and_chrome_do_not_own_other_prose(inner):
    assert not ielts(read(inner))

def test_local_qualification_is_preserved_as_mismatch():
    out = read('<h2>A-level applicants: IELTS Academic</h2><p>Minimum overall 6.5.</p>')
    c = ielts(out)['ielts_min_overall']
    assert c['scope']['qualification'] == 'A-levels'
    assert c['scope']['academic_year'] is None
    from app.domain.claim_scope import ClaimScope
    scope = ClaimScope(**c['scope'])
    assert scope.covers(RequestedScope(qualification='attestat')) is Verdict.NO

@pytest.mark.parametrize('year', ['2024/25', '2025/26'])
def test_explicit_local_old_year_is_not_requested_2027(year):
    out = read(f'<section><h2>IELTS Academic {year}</h2><p>Minimum overall 6.5.</p></section>')
    c = ielts(out)['ielts_min_overall']
    assert c['scope']['academic_year'] == year
    assert c['academic_year'] == year  # original page classifier's observed year survives

@pytest.mark.parametrize('wording', ['Next year', 'For the next intake', ''])
def test_relative_or_absent_year_remains_unknown(wording):
    out = read(f'<h2>IELTS Academic</h2><p>{wording} minimum overall 6.5.</p>')
    assert ielts(out)['ielts_min_overall']['scope']['academic_year'] is None

def test_excerpt_keeps_intervening_words_and_abstains_when_too_long():
    inner = '<h2>IELTS Academic</h2><div>Intervening ownership text.</div><p>Minimum overall 6.5.</p>'
    c = ielts(read(inner))['ielts_min_overall']
    assert 'Intervening ownership text.' in c['original_text_excerpt']
    assert not ielts(read(inner.replace('Intervening ownership text.', 'A long unrelated fragment. ' * 40)))

def test_exchange_filter_remains_before_reader():
    inner = ('<h2>Exchange students</h2><p>IELTS Academic overall 5.5.</p>'
             '<h2>Full degree applicants</h2><p>IELTS Academic overall 6.5.</p>')
    assert value(read(inner)) == 6.5

def test_structural_table_still_has_priority():
    inner = ('<table><tr><th>English test</th><th>Overall minimum</th></tr>'
             '<tr><td>IELTS Academic</td><td>7.0 with no part less than 6.5</td></tr></table>'
             '<h2>IELTS Academic</h2><p>Minimum overall 6.0 with no part below 5.5.</p>')
    off, on = read(inner, on=False), read(inner)
    assert value(off) == value(on) == 7.0
    assert value(off, 'ielts_min_subscore') == value(on, 'ielts_min_subscore') == 6.5

@pytest.mark.parametrize('statement,expected', [
    ('IELTS General Training is accepted with overall 6.5.', ['general_training']),
    ('IELTS UKVI Academic is accepted with overall 6.5.', ['academic', 'ukvi_academic']),
    ('IELTS General Training is not accepted; IELTS Academic requires overall 6.5.', ['academic']),
])
def test_existing_accepted_type_vocabulary_and_explicit_negation(statement, expected):
    out = read(f'<p>{statement}</p>')
    assert value(out, 'ielts_accepted_types') == expected

@pytest.mark.parametrize('row', replay.ROWS, ids=lambda r:r['url'])
def test_all_retained_off_results_equal_frozen_whole_output(row):
    assert asyncio.run(replay.retained(row, old=True)) == asyncio.run(replay.retained(row, on=False))

def test_existing_admitted_delft_positive_and_toronto_diagnostic_only():
    for row in replay.ROWS:
        on = asyncio.run(replay.retained(row, on=True))
        if 'tudelft.nl' in row['url']:
            assert on['page_outcomes'][0]['category'] == 'fetched-ok'
            assert value(on) == 6.5
            assert ielts(on)['ielts_min_overall']['scope']['academic_year'] is None
        elif 'english-language' in row['url']:
            assert on['page_outcomes'][0]['category'] == 'classifier-rejected'
            assert not on['claims']
            diagnostic = asyncio.run(replay.retained(row, on=True, diagnostic=True))
            assert value(diagnostic) == 6.5
            assert value(diagnostic, 'ielts_min_subscore') == 6.0
            for c in ielts(diagnostic).values():
                assert c['scope']['qualification'] is None
                assert c['scope']['academic_year'] is None
                assert 'IELTS' in c['original_text_excerpt']
                assert 'CAEL' not in c['original_text_excerpt']
                body = Path(row['body_owned']).read_text()
                assert is_verbatim_excerpt(c['original_text_excerpt'], replay.readable_text(body))

@pytest.mark.parametrize('atom', ['-6.5', '6.5e1', '6,500', '6.5.2027', '6.5abc'])
def test_signed_or_continued_numeric_token_is_not_a_valid_band(atom):
    assert not {'ielts_min_overall', 'ielts_min_subscore'} & ielts(read(
        f'<h2>IELTS</h2><p>Minimum overall {atom} with no part below {atom}.</p>'
    )).keys()

def test_local_ancestor_qualification_year_are_part_of_contiguous_evidence():
    out = read('<section><h2>A-level applicants academic year 2024/25</h2><h3>IELTS Academic</h3>'
               '<p>Minimum overall 6.5.</p></section>')
    c = ielts(out)['ielts_min_overall']
    assert c['scope']['qualification'] == 'A-levels'
    assert c['scope']['academic_year'] == '2024/25'
    assert 'A-level applicants academic year 2024/25' in c['original_text_excerpt']
    assert 'IELTS Academic' in c['original_text_excerpt']

def test_old_ielts_year_does_not_become_sibling_current_toefl_year():
    out = read('<section><h2>IELTS Academic year 2024/25</h2><p>Minimum overall 6.5.</p></section>'
               '<section><h2>TOEFL admission year 2027/28</h2><p>Overall 100.</p></section>')
    c = ielts(out)['ielts_min_overall']
    assert c['scope']['academic_year'] == '2024/25'
    from app.domain.claim_scope import ClaimScope
    assert ClaimScope(**c['scope']).covers(RequestedScope(academic_year='2027/28')) is Verdict.NO
    assert '2024/25' in c['original_text_excerpt']
    assert 'TOEFL' not in c['original_text_excerpt']

ROOT_CONTROLS = __import__('json').loads((replay.BASE/'root-controls.original.json').read_text())['results']

@pytest.mark.parametrize('case', ROOT_CONTROLS, ids=lambda c:c['case'])
def test_four_parent_independent_admitted_caller_blockers(case):
    out = asyncio.run(replay.read(URL,case['body'],domain='example.edu',on=True))
    assert out['page_outcomes'][0]['category'] in {'fetched-ok','no-pattern-match'}
    assert out['page_outcomes'][0]['page_type'] != 'unknown'
    claims = ielts(out)
    if case['case'] == 'sibling_toefl_year':
        assert value(out) == 6.5
        assert all(c['scope']['academic_year'] is None and c['academic_year'] is None for c in claims.values())
        assert all(c['scope']['intake'] is None and c['intake'] is None for c in claims.values())
    elif case['case'] in {'writing_months','named_negative'}:
        assert value(out) == 6.5
        assert 'ielts_min_subscore' not in claims
    else:
        assert not claims

@pytest.mark.parametrize('wording', ['Writing: 6.5, Reading: 6.0.', 'Writing score of 6.5, Reading minimum 6.0.'])
def test_named_band_real_score_role_positive(wording):
    out=read(f'<h2>IELTS Academic</h2><p>Minimum overall 6.5. {wording}</p>')
    assert value(out,'ielts_min_subscore') == {'reading':6.0,'writing':6.5}

@pytest.mark.parametrize('wording', ['Writing 6 months.', 'Writing: -6.5.', 'Writing score of -6.5.'])
def test_named_band_time_or_negative_not_score(wording):
    out=read(f'<h2>IELTS Academic</h2><p>Minimum overall 6.5. {wording}</p>')
    assert value(out) == 6.5
    assert 'ielts_min_subscore' not in ielts(out)

def test_same_owner_decline_other_paragraph_and_duplicate_header_boundary():
    out=read('<section><h2>IELTS Academic</h2><p>Minimum overall 6.5.</p>'
             '<p>IELTS Academic is no longer accepted.</p></section>'
             '<section><h2>IELTS Academic</h2><p>Minimum overall 7.0.</p></section>')
    assert value(out) == 7.0

def test_title_only_year_and_intake_are_source_metadata_not_request():
    title='Bachelor admission requirements academic year 2026/27 Fall 2026 intake'
    body=f'<html><head><title>{title}</title></head><body><main><h1>Admission requirements</h1><h2>IELTS Academic</h2><p>Minimum overall 6.5.</p></main></body></html>'
    out=asyncio.run(replay.read(URL,body,domain='example.edu',on=True))
    c=ielts(out)['ielts_min_overall']
    assert c['scope']['academic_year']==c['academic_year']=='2026/27'
    assert c['scope']['intake']==c['intake']=='Fall 2026'
    assert c['page_title']==title
    assert is_verbatim_excerpt(c['original_text_excerpt'],replay.readable_text(body))

def test_sibling_intake_does_not_set_ielts_intake():
    out=read('<section><h2>IELTS Academic</h2><p>Minimum overall 6.5.</p></section>'
             '<section><h2>TOEFL for Fall 2027 intake</h2><p>Overall 100.</p></section>')
    assert ielts(out)['ielts_min_overall']['scope']['intake'] is None
    assert ielts(out)['ielts_min_overall']['intake'] is None

def test_reversed_older_toefl_then_current_ielts_all_declared_fields():
    out=read('<section><h2>TOEFL academic year 2024/25 Fall 2024 intake</h2><p>Overall 100.</p></section>'
             '<section><h2>IELTS Academic year 2027/28 Fall 2027 intake</h2><p>Minimum overall 6.5.</p></section>')
    for c in ielts(out).values():
        assert c['scope']['academic_year']==c['academic_year']=='2027/28'
        assert c['scope']['intake']==c['intake']=='Fall 2027'
        assert '2027/28' in c['original_text_excerpt']
        assert '2024/25' not in c['original_text_excerpt']

def test_retained_all_year_fields_unknown_and_other_claim_metadata_unchanged():
    for row in replay.ROWS:
        old=asyncio.run(replay.retained(row,old=True))
        on=asyncio.run(replay.retained(row,on=True))
        assert [c for c in old['claims'] if c['claim_type'] not in TYPES]==[c for c in on['claims'] if c['claim_type'] not in TYPES]
        if 'english-language' in row['url']:
            on=asyncio.run(replay.retained(row,on=True,diagnostic=True))
        if 'tudelft.nl' in row['url'] or 'english-language' in row['url']:
            for c in ielts(on).values():
                assert c['scope']['academic_year'] is c['academic_year'] is None
                assert c['scope']['intake'] is c['intake'] is None

def test_admitted_table_only_whole_output_unchanged_including_legacy_types():
    inner=('<table><tr><th>English test</th><th>Overall minimum</th></tr>'
           '<tr><td>IELTS Academic</td><td>7.0 with no part less than 6.5</td></tr></table>')
    old=asyncio.run(replay.read(URL,html(inner),domain='example.edu',old=True))
    assert old==read(inner,on=False)==read(inner,on=True)
    assert value(old)==7.0
    assert value(old,'ielts_accepted_types')==['academic']

def test_unknown_language_follow_structural_table_whole_route_unchanged():
    body='<html><head><title>English information</title></head><body><main><h1>English information</h1><table><tr><th>English test</th><th>Overall minimum</th></tr><tr><td>IELTS Academic</td><td>7.0 with no part less than 6.5</td></tr></table></main></body></html>'
    outputs=[asyncio.run(replay.read(URL,body,domain='example.edu',language_follow=True,**kw)) for kw in ({'old':True},{'on':False},{'on':True})]
    assert outputs[0]==outputs[1]==outputs[2]
    assert outputs[0]['page_outcomes'][0]['page_type']=='unknown'
    assert outputs[0]['page_outcomes'][0]['category']=='fetched-ok'
    assert value(outputs[0])==7.0

def test_actual_pdf_reader_path_unchanged_with_mocked_conversion():
    text='Admission requirements for A-level applicants. IELTS Academic requires overall 6.5 with no part below 6.0.'
    url=URL+'.pdf'
    outputs=[asyncio.run(replay.read(url,'',pdf_text=text,domain='example.edu',**kw)) for kw in ({'old':True},{'on':False},{'on':True})]
    assert outputs[0]==outputs[1]==outputs[2]
    assert outputs[0]['page_outcomes'][0]['page_type']=='country_credential_requirements'
    assert outputs[0]['page_outcomes'][0]['category']=='fetched-ok'
    assert value(outputs[0])==6.5

@pytest.mark.parametrize('year,verdict', [('2027/28',Verdict.YES),('2024/25',Verdict.NO),(None,Verdict.UNKNOWN)])
def test_requested_scope_year_coverages_remain_honest(year,verdict):
    inner=f'<h2>IELTS Academic'+(f' year {year}' if year else '')+'</h2><p>Minimum overall 6.5.</p>'
    c=ielts(read(inner))['ielts_min_overall']
    from app.domain.claim_scope import ClaimScope
    assert ClaimScope(**c['scope']).covers(RequestedScope(academic_year='2027/28')) is verdict
    assert c['academic_year']==c['scope']['academic_year']==year

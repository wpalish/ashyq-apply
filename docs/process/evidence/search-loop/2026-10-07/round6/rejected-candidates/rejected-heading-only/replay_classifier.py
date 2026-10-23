"""Offline retained-page and independent classifier controls; no networking."""
import asyncio
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from unittest.mock import patch

from app.adapters import page_classifier as legacy
from app.adapters.base import Candidate, CandidateProgram
from app.adapters.extraction import readable_text
from app.adapters.fetching import FetchResult
from app.adapters.requirements import web_requirements
from app.domain.claim_verifier import is_verbatim_excerpt
from app.domain.enums import DegreeLevel, FetchOutcome

BASE = Path(__file__).resolve().parent
REPO = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
ROUND = BASE.parent.parent
STOP = REPO.parent / 'development-STOP.json'
BODY = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/search-loop-round2/pair-temp/on1/canary-o450usf2/cache/1a/1ad11c46fa894ecfacf4423150e42b74.body')
URL = 'https://www.wits.ac.za/course-finder/undergraduate/science/computer-science'
EXPECTED_BODY_SHA = '88d1f716c82840fa66317ff1ceb42a152439a924d7625c0d2ef18a0f315f0a87'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def load_proposal():
    spec = importlib.util.spec_from_file_location('expert_b_funding_classifier', BASE / 'proposed_page_classifier.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def page(title, body, h1=None):
    h1 = title if h1 is None else h1
    return f'<html><head><title>{title}</title></head><body><main><h1>{h1}</h1>{body}</main></body></html>'


AWARD_LINKS = '<ul><li><a href="/award/a">Alpha Scholarship</a></li><li><a href="/award/b">Beta Scholarship</a></li></ul>'
AWARD_PROSE = '<p>The award covers tuition fees. Its value is EUR 5000 per year. Eligibility: open to admitted undergraduate students. No separate application is required.</p>'
FUNDING_PROSE = '<p>Choose a funding opportunity for undergraduate study. Each award has individual eligibility rules, terms and application steps. No degree is offered on this support page.</p>'
PROGRAM_PROSE = '<p>This three-year bachelor degree teaches algorithms, software and computer systems. Students study programming and complete an academic project.</p>'
PROGRAM_BLOCK = PROGRAM_PROSE + '<h2>Curriculum</h2><p>First year: mathematics and programming. Second year: algorithms, databases and operating systems. Third year: academic project.</p>'
PROGRAM_LINKS = '<ul>' + ''.join(f'<li><a href="/bachelors/subject{i}">BSc Subject {i}</a></li>' for i in range(7)) + '</ul>'


def controls():
    return [
        ('own_programme_secondary_funding', 'https://example.edu/bachelors/computer-science', page('BSc Computer Science', PROGRAM_BLOCK + '<h2>University Fees and Funding</h2>' + AWARD_LINKS), 'program_detail'),
        ('bare_programme_secondary_funding', 'https://example.edu/bachelors/computer-science', page('Computer Science | Bachelor | University', PROGRAM_BLOCK + '<h2>Funding</h2>' + AWARD_LINKS, 'Computer Science'), 'program_detail'),
        ('programme_structure_synonym', 'https://example.edu/degree', page('Bachelor of Science in Mathematics', PROGRAM_PROSE + '<h2>Programme structure</h2><p>Study algebra, calculus and geometry.</p><h2>Scholarships</h2>' + AWARD_LINKS), 'program_detail'),
        ('programme_secondary_faq', 'https://example.edu/bachelors/computer-science', page('BSc Computer Science', PROGRAM_BLOCK + '<h2>Funding</h2><h2>Frequently asked questions</h2>' + AWARD_LINKS), 'program_detail'),
        ('programme_no_funding_unchanged', 'https://example.edu/degree', page('BSc Computer Science', PROGRAM_BLOCK), 'program_detail'),
        ('no_identity_not_promoted_by_curriculum', 'https://example.edu/about', page('Student support', '<h2>Curriculum</h2><p>Contact your department for academic questions.</p><h2>Funding</h2>' + FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('generic_funding_index', 'https://example.edu/student-support/offer', page('Student support', '<h2>Scholarships</h2>' + FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('undergraduate_support_index', 'https://example.edu/student-support/offer', page('Undergraduate support', '<h2>Scholarships</h2>' + FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('undergraduate_support_index_with_curriculum', 'https://example.edu/student-support/offer', page('Undergraduate support', '<h2>Curriculum</h2><p>Eligible faculties publish their current academic course structure.</p><h2>Scholarships</h2>' + FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('named_merit_award_secondary_funding', 'https://example.edu/student-support/offer', page('Example Merit Award', '<h2>Funding</h2>' + AWARD_PROSE), 'scholarship_award'),
        ('index_primary_scholarships', 'https://example.edu/support', page('Scholarships', FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('index_primary_financial_aid', 'https://example.edu/support', page('Financial aid', FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('index_primary_bursaries', 'https://example.edu/support', page('Bursaries', FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('index_primary_grants', 'https://example.edu/support', page('Grants for international students', FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('index_title_funding_h1_generic', 'https://example.edu/support', page('Scholarships | University', FUNDING_PROSE + AWARD_LINKS, 'Freshmen'), 'scholarship_index'),
        ('scholarship_url_generic_page', 'https://example.edu/scholarships/freshmen', page('Freshmen', FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('financial_aid_url_generic_page', 'https://example.edu/financial-aid/freshmen', page('Freshmen', FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
        ('scholarship_url_programme_named', 'https://example.edu/scholarships/bsc-computer-science', page('BSc Computer Science', PROGRAM_BLOCK + AWARD_LINKS), 'scholarship_index'),
        ('financial_aid_url_programme_named', 'https://example.edu/financial-aid/bsc-computer-science', page('BSc Computer Science', PROGRAM_BLOCK + AWARD_LINKS), 'scholarship_index'),
        ('detail_primary_scholarship', 'https://example.edu/support/merit', page('Example Merit Scholarship', AWARD_PROSE), 'scholarship_award'),
        ('detail_primary_bursary', 'https://example.edu/support/merit', page('Example Merit Bursary', AWARD_PROSE), 'scholarship_award'),
        ('detail_named_award_with_programme_content', 'https://example.edu/bachelors/funding', page('Undergraduate Merit Award', '<h2>Curriculum</h2><p>Applicants study science.</p><h2>Funding</h2>' + AWARD_PROSE), 'scholarship_award'),
        ('funding_faq_own', 'https://example.edu/support', page('Scholarship FAQs', '<h2>When can I apply?</h2><p>Applications are considered each year for eligible students.</p>'), 'scholarship_faq'),
        ('financial_aid_faq_own', 'https://example.edu/support', page('Financial aid frequently asked questions', '<p>Read our answers before submitting a funding application.</p>'), 'scholarship_faq'),
        ('generic_funding_faq', 'https://example.edu/support', page('Student support', '<h2>Financial aid</h2><h2>Frequently asked questions</h2><p>Read our answers before submitting a funding application.</p>'), 'scholarship_faq'),
        ('catalogue_own', 'https://example.edu/all', page("Bachelor's programmes", PROGRAM_PROSE + PROGRAM_LINKS), 'program_catalog'),
        ('documents_own_funding_links', 'https://example.edu/submit', page('Required documents', '<p>Submit your transcript and identity documents. The checklist helps you prepare your application.</p>' + AWARD_LINKS), 'documents'),
        ('admissions_own', 'https://example.edu/admissions', page('Admission procedure', '<p>Read our application procedure and prepare your official school records for admission.</p>'), 'general_admissions'),
        ('costs_own', 'https://example.edu/fees', page('Tuition fees', '<p>Review tuition fees and payment dates for the coming academic year.</p>' + AWARD_LINKS), 'costs'),
        ('neutral_programme_scoped_funding_page', 'https://example.edu/support/computer-science', page('BSc Computer Science', '<h2>Scholarships</h2>' + FUNDING_PROSE + AWARD_LINKS), 'scholarship_index'),
    ]


async def reader_replay(classifier, html):
    requested = []
    async def get(url):
        requested.append(url)
        if url == URL:
            return FetchResult(url=url, outcome=FetchOutcome.OK, status_code=200, content=html.encode(), text=html, final_url=url, from_cache=True, fetched_at=datetime(2026, 10, 7, tzinfo=UTC))
        return FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR, error='Offline replay: no retained body supplied for this followed URL')
    candidate = Candidate(name='University of Witwatersrand', country='South Africa', city='Johannesburg', domain='wits.ac.za', search_queries_used=6)
    program = CandidateProgram(name='Computer Science', field='Computer Science', degree=DegreeLevel.BACHELOR, url=URL)
    with patch.object(web_requirements, 'classify_page', classifier), patch('app.adapters.search.get_search_provider', side_effect=AssertionError('No provider calls allowed')):
        result = await web_requirements.WebRequirementsAdapter(SimpleNamespace(get=get), '2027/28').verify(candidate, program, 'fall 2027')
    text = readable_text(html)
    claims = [{'claim': c.model_dump(mode='json'), 'verbatim_in_original_readable_text': is_verbatim_excerpt(c.original_text_excerpt, text)} for c in result.claims]
    return {'fake_fetcher_urls': requested, 'result': asdict(result), 'claims': claims}


async def main():
    before = sha(REPO / 'backend/app/adapters/page_classifier.py'); stop_before = sha(STOP)
    raw = BODY.read_bytes(); assert hashlib.sha256(raw).hexdigest() == EXPECTED_BODY_SHA
    html = raw.decode('utf-8', errors='replace')
    proposed = load_proposal()
    parent_ns = dict(vars(legacy)); exec((ROUND / 'funding-heading.proposal.txt').read_text(), parent_ns)
    parent = parent_ns['classify_page']
    results = []
    for name, url, body, expected in controls():
        old = legacy.classify_page(url=url, html=body)
        parent_new = parent(url=url, html=body)
        proposed.PROGRAMME_IDENTITY_BEFORE_FUNDING = False
        off = proposed.classify_page(url=url, html=body)
        assert asdict(old) == asdict(off), name
        proposed.PROGRAMME_IDENTITY_BEFORE_FUNDING = True
        on = proposed.classify_page(url=url, html=body)
        results.append({'case': name, 'url': url, 'html': body, 'html_sha256': hashlib.sha256(body.encode()).hexdigest(), 'expected_on': expected, 'legacy': asdict(old), 'parent_title_only': asdict(parent_new), 'flag_off_equal_legacy': True, 'conservative_on': asdict(on), 'on_passes_expected': on.page_type.value == expected, 'on_accepts_program_exists': on.accepts('program_exists')})
    retained = []
    for text in ('', readable_text(html)):
        arms = []
        for enabled in (False, True, True, False):
            proposed.PROGRAMME_IDENTITY_BEFORE_FUNDING = enabled
            found = proposed.classify_page(url=URL, html=html, text=text)
            arms.append({'enabled': enabled, 'classification': asdict(found)})
        assert arms[0]['classification'] == arms[3]['classification'] == asdict(legacy.classify_page(url=URL, html=html, text=text))
        retained.append({'caller': 'html_only' if not text else 'html_and_original_readable_text', 'arms': arms})
    limitation_html = page('Undergraduate admissions', '<p>Read our application procedure and prepare your official school records for admission.</p>')
    old_limit = legacy.classify_page(url='https://example.edu/admissions', html=limitation_html)
    proposed.PROGRAMME_IDENTITY_BEFORE_FUNDING = True
    new_limit = proposed.classify_page(url='https://example.edu/admissions', html=limitation_html)
    limitations = [{'case': 'preexisting_undergraduate_admissions_false_programme', 'semantic_expected': 'general_admissions', 'legacy': asdict(old_limit), 'conservative_on': asdict(new_limit), 'unchanged': asdict(old_limit) == asdict(new_limit)}]
    proposed.PROGRAMME_IDENTITY_BEFORE_FUNDING = False
    old_reader = await reader_replay(proposed.classify_page, html)
    proposed.PROGRAMME_IDENTITY_BEFORE_FUNDING = True
    new_reader = await reader_replay(proposed.classify_page, html)
    def safe(v):
        if hasattr(v, 'model_dump'): return v.model_dump(mode='json')
        if hasattr(v, 'value'): return v.value
        if isinstance(v, datetime): return v.isoformat()
        raise TypeError(type(v).__name__)
    payload = {'source_sha_before': before, 'source_sha_after': sha(REPO / 'backend/app/adapters/page_classifier.py'), 'source_unchanged': before == sha(REPO / 'backend/app/adapters/page_classifier.py'), 'sticky_stop_sha_before': stop_before, 'sticky_stop_sha_after': sha(STOP), 'sticky_stop_unchanged': stop_before == sha(STOP), 'network_calls': 0, 'provider_calls': 0, 'model_calls': 0, 'git_calls': 0, 'retained': {'url': URL, 'body_path': str(BODY), 'body_sha256': EXPECTED_BODY_SHA, 'body_unchanged': sha(BODY) == EXPECTED_BODY_SHA, 'caller_replays': retained, 'requirements_reader_off': old_reader, 'requirements_reader_on': new_reader}, 'independent_control_count': len(results), 'all_control_expectations_passed': all(x['on_passes_expected'] for x in results), 'controls': results, 'known_unchanged_classifier_limitations': limitations, 'scope': 'External flagged classifier shadow + actual requirements reader on retained body; synthetic controls are independently authored, not heldout or gold'}
    (BASE / 'independent-replay.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=safe) + '\n')
    print(json.dumps({'source_unchanged': payload['source_unchanged'], 'sticky_stop_unchanged': payload['sticky_stop_unchanged'], 'controls': len(results), 'all_passed': payload['all_control_expectations_passed'], 'failed': [{'case':x['case'],'got':x['conservative_on']['page_type'],'expected':x['expected_on']} for x in results if not x['on_passes_expected']], 'retained_types': [a['classification']['page_type'] for a in retained[0]['arms']], 'reader_off_claims':len(old_reader['claims']), 'reader_on_claims':len(new_reader['claims'])}, ensure_ascii=False))


if __name__ == '__main__':
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Real network forbidden')), patch.object(socket, 'create_connection', side_effect=AssertionError('Real network forbidden')):
        asyncio.run(main())

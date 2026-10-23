"""Independently authored offline scope controls against the pinned Round6 proposal."""
import hashlib
import importlib.util
import json
import socket
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from app.adapters import page_classifier as legacy

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("expert_a_r6_classifier", ROOT / "proposal-pinned/proposed_page_classifier.py")
proposal = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = proposal
spec.loader.exec_module(proposal)

LINKS = '<a href="/awards/one">Alpha Scholarship</a><a href="/awards/two">Beta Scholarship</a>'
ACADEMIC = '<h2>Curriculum</h2><p>Students take first-year courses in programming and second-year modules in algorithms, followed by a project.</p>'


def page(body):
    return '<html><head><title>BSc Computer Science</title></head><body><main><h1>BSc Computer Science</h1>' + body + '</main></body></html>'


CASES = [
    ('funding_eligibility_with_academic_conditions',
     '<p>This is a funding eligibility page for enrolled students.</p><h2>Curriculum</h2><p>Applicants must have completed first-year courses and second-year modules to qualify.</p><h2>Funding opportunities</h2>' + LINKS,
     'scholarship_index'),
    ('explicit_sibling_section_scope',
     '<section id="curriculum"><h2>Curriculum</h2><p>Ask the office for advice.</p></section><section aria-label="Award eligibility"><p>Applicants must complete first-year courses and second-year modules before applying.</p></section><h2>Scholarships</h2>' + LINKS,
     'scholarship_index'),
    ('role_navigation_academic_copy',
     '<div role="navigation"><h2>Curriculum</h2><p>First-year courses and second-year modules.</p></div><h2>Scholarships</h2><p>View our award opportunities for enrolled students.</p>' + LINKS,
     'scholarship_index'),
    ('funding_eligibility_credits_without_progression',
     '<p>This is a financial support eligibility page.</p><h2>Curriculum</h2><p>Applicants need courses worth 120 credits to qualify.</p><h2>Scholarships</h2>' + LINKS,
     'scholarship_index'),
    ('programme_negates_bursaries_not_degree',
     ACADEMIC + '<h2>Funding</h2><p>We do not offer bursaries for this degree.</p>' + LINKS,
     'program_detail'),
    ('programme_negates_funding_not_degree',
     ACADEMIC + '<h2>Funding</h2><p>We do not offer financial assistance for this programme.</p>' + LINKS,
     'program_detail'),
    ('comment_academic_only',
     '<h2>Curriculum</h2><!-- First-year courses and second-year modules. --><p>Ask the office.</p><h2>Scholarships</h2>' + LINKS,
     'scholarship_index'),
    ('next_equal_heading_is_closed',
     '<h2>Curriculum</h2><p>Ask the office.</p><h2>Eligibility</h2><p>First-year courses and second-year modules.</p><h2>Scholarships</h2>' + LINKS,
     'scholarship_index'),
    ('real_academic_same_block_positive',
     ACADEMIC + '<h2>Funding</h2>' + LINKS,
     'program_detail'),
]


def denied(*args, **kwargs):
    raise AssertionError('Offline scope replay attempted network')


def main():
    results = []
    with patch.object(socket, 'getaddrinfo', denied), patch.object(socket, 'create_connection', denied), patch.object(socket.socket, 'connect', denied):
        for name, body, expected in CASES:
            html = page(body); url = 'https://example.edu/support/computer-science'
            proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING = False
            off = proposal.classify_page(url=url, html=html)
            original = legacy.classify_page(url=url, html=html)
            assert asdict(off) == asdict(original)
            proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING = True
            on = proposal.classify_page(url=url, html=html)
            full = proposal._parse_markup(html); soup = proposal.main_content(full)
            blocks = [{'heading': h.get_text(' ', strip=True), 'block': proposal._academic_section_text(h, soup)} for h in soup.find_all(['h1','h2','h3']) if proposal._ACADEMIC_HEADING.fullmatch(h.get_text(' ', strip=True))]
            results.append({'case':name,'expected':expected,'html':html,'html_sha256':hashlib.sha256(html.encode()).hexdigest(),'url':url,'off':asdict(off),'on':asdict(on),'on_matches_expected':on.page_type.value==expected,'academic_blocks':blocks,'no_degree_match':proposal._NO_DEGREE_OFFER.search(proposal._text(soup)).group(0) if proposal._NO_DEGREE_OFFER.search(proposal._text(soup)) else None})
    result={'network_calls':0,'real_provider_calls':0,'repo_edits':0,'proposal_sha256':hashlib.sha256((ROOT/'proposal-pinned/proposed_page_classifier.py').read_bytes()).hexdigest(),'controls':results,'failed':[r['case'] for r in results if not r['on_matches_expected']]}
    (ROOT/'independent-scope-negatives.offline.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'controls':len(results),'failed':result['failed'],'classifications':[{'case':r['case'],'expected':r['expected'],'actual':r['on']['page_type'].value} for r in results]},indent=2))


if __name__ == '__main__':
    main()

"""Own offline controls; the nine revision1 controls remain byte-for-byte retained."""
import hashlib
import importlib.util
import json
import socket
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from replay_independent_scope_negatives import ACADEMIC, CASES as ORIGINAL_CASES, LINKS, legacy, page

spec = importlib.util.spec_from_file_location("expert_a_r6_classifier_v2", ROOT / "proposal-pinned/proposed_page_classifier.py")
proposal = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = proposal
spec.loader.exec_module(proposal)

EXTRA_CASES = [
    ('genuine_curriculum_optional_module_eligibility',
     '<h2>Curriculum</h2><p>Students take first-year courses in programming and second-year modules in algorithms. Students are eligible to choose optional third-year modules after completing prerequisites.</p><h2>Funding</h2>' + LINKS,
     'program_detail'),
    ('genuine_curriculum_qualifies_for_honours',
     '<h2>Curriculum</h2><p>Students take first-year courses in programming and second-year modules in algorithms. This degree qualifies graduates for entry to honours study.</p><h2>Funding</h2>' + LINKS,
     'program_detail'),
    ('genuine_bachelor_negates_different_master_degree',
     ACADEMIC + '<h2>Further study</h2><p>We do not offer a master\'s degree in this subject.</p><h2>Funding</h2>' + LINKS,
     'program_detail'),
    ('genuine_bachelor_negates_this_bachelor_degree',
     ACADEMIC + '<p>We do not offer this undergraduate degree.</p><h2>Funding</h2>' + LINKS,
     'scholarship_index'),
    ('funding_eligibility_no_formula_page_purpose',
     '<p>Financial support eligibility for current students is described below.</p><h2>Curriculum</h2><p>Applicants must complete first-year courses and second-year modules before receiving assistance.</p><h2>Funding</h2>' + LINKS,
     'scholarship_index'),
]
CASES = ORIGINAL_CASES + EXTRA_CASES


def denied(*args, **kwargs):
    raise AssertionError('No network/provider/model permitted in offline review')


def main():
    result = []
    with patch.object(socket, 'getaddrinfo', denied), patch.object(socket, 'create_connection', denied), patch.object(socket.socket, 'connect', denied):
        for name, body, expected in CASES:
            html = page(body)
            url = 'https://example.edu/support/computer-science'
            proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING = False
            off = proposal.classify_page(url=url, html=html)
            original = legacy.classify_page(url=url, html=html)
            assert asdict(off) == asdict(original)
            proposal.PROGRAMME_IDENTITY_BEFORE_FUNDING = True
            on = proposal.classify_page(url=url, html=html)
            soup = proposal.main_content(proposal._parse_markup(html))
            blocks = [{'heading': h.get_text(' ', strip=True), 'block': proposal._academic_section_text(h, soup)} for h in soup.find_all(['h1','h2','h3']) if proposal._ACADEMIC_HEADING.fullmatch(h.get_text(' ',strip=True))]
            no_degree = proposal._NO_DEGREE_OFFER.search(proposal._text(soup))
            result.append({'case': name, 'expected': expected, 'html': html, 'html_sha256': hashlib.sha256(html.encode()).hexdigest(), 'url': url, 'off': asdict(off), 'on': asdict(on), 'on_matches_expected': on.page_type.value == expected, 'academic_blocks': blocks, 'eligibility_matches': [proposal._ACADEMIC_ELIGIBILITY.findall(b['block']) for b in blocks], 'no_degree_match': no_degree.group(0) if no_degree else None})
    raw = {'proposal_sha256': hashlib.sha256((ROOT/'proposal-pinned/proposed_page_classifier.py').read_bytes()).hexdigest(), 'network_calls': 0, 'provider_calls': 0, 'model_calls': 0, 'repo_edits': 0, 'controls': result, 'failed': [r['case'] for r in result if not r['on_matches_expected']]}
    (ROOT/'scope-controls.offline.json').write_text(json.dumps(raw, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'controls': len(result), 'original_nine_failed': [r['case'] for r in result[:9] if not r['on_matches_expected']], 'new_failed': raw['failed'], 'classifications': [{'case':r['case'],'expected':r['expected'],'actual':r['on']['page_type'].value} for r in result]},indent=2))


if __name__ == '__main__':
    main()

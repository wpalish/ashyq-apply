"""Byte-grounded DOM inventory only; no production rule implementation."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from app.adapters.fetching import _content_hash
from app.adapters.page_classifier import full_degree_titles

WORK = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work')
OUT = Path(__file__).resolve().parent
BODY = WORK / 'development-baseline-temp/canary-e9ioklso/cache/1c/1c604897f3d098cef1ba5cef3e1b9584.body'
META = BODY.with_suffix('.meta.json')
EXPERT_VIEW = WORK / 'development-experts/expert_a/dalian/view-013.json'
EXPERT_RAW = WORK / 'development-experts/expert_a/dalian/raw/dalian-013.json'
EARLIER_REPLAY = WORK / 'search-loop-round2/reviews/expert_a/dalian-discovery-loss.offline.json'
sha = lambda data: hashlib.sha256(data).hexdigest()

body, meta_bytes = BODY.read_bytes(), META.read_bytes()
metadata = json.loads(meta_bytes)
html = body.decode(metadata['encoding'])
soup = BeautifulSoup(html, 'lxml')
heading = soup.find('h2')
assert heading and heading.get_text(' ', strip=True) == 'Introduction to Undergraduate Training Programs in Computer Science and Technology'
# CSS selectors describe this retained source for analysis only, not a proposed
# institution-specific extraction rule.
article = heading.find_parent('div', class_='services-single')
assert article is not None
sidebar = soup.find('aside', class_='sidebar')
assert sidebar is not None
article_text = article.get_text('\n', strip=True)
headings = [{'tag': h.name, 'text': h.get_text(' ', strip=True)}
            for h in article.find_all(re.compile(r'^h[1-6]$'))]
paragraphs = [' '.join(p.get_text(' ', strip=True).split()) for p in article.find_all('p')
              if p.get_text(strip=True)]
links = [{'href': str(a.get('href') or ''), 'text': a.get_text(' ', strip=True)}
         for a in article.find_all('a')]
sidebar_links = [{'href': str(a.get('href') or ''), 'text': a.get_text(' ', strip=True)}
                 for a in sidebar.find_all('a')]
heading_line = next(i + 1 for i, line in enumerate(html.splitlines())
                    if '<h2 align="center">' in line and 'Undergraduate Training Programs' in line)
layout_line = next(i + 1 for i, line in enumerate(html.splitlines())
                   if '<div class="sidebar-page-container">' in line)
inventory = {
    'headings': headings,
    'nonempty_paragraph_count': len(paragraphs),
    'programme_entry_links': links,
    'table_count': len(article.find_all('table')),
    'definition_list_count': len(article.find_all('dl')),
    'main_content_section_labels': [p for p in paragraphs if re.match(r'^\d\.', p)][:3],
    'production_full_degree_titles_on_article': full_degree_titles(article_text),
    'explicit_bachelor_award_words_on_article': re.findall(r'\bbachelor\b|\bBSc\b|\bBEng\b|degree awarded', article_text, re.I),
    'intake_years_on_article': re.findall(r'\b20\d{2}\b', article_text),
    'scope_qualifier_observations': {
        'undergraduate': 'Named in actual article heading and training description',
        'field': 'Computer Science and Technology named in the same actual article heading',
        'programme_cardinality': 'One field-specific training section; formal programme count not explicitly established',
        'catalogue': 'No separate named major/degree entries or programme links in this article',
        'international': 'International vision/competitiveness are educational objectives, not applicant admission scope',
        'campus': 'Footer school address is not a programme campus assignment',
        'language': 'English webpage language is not evidence of programme teaching language',
        'award_and_intake': 'No explicit awarded degree name or intake year in this article snapshot',
    },
    'sidebar_education_links': sidebar_links,
}
assert len(headings) == 1 and not links
assert not inventory['production_full_degree_titles_on_article']
assert not inventory['explicit_bachelor_award_words_on_article']
assert not inventory['intake_years_on_article']
excerpts = []
for label, text in [
    ('actual_main_heading', heading.get_text(' ', strip=True)),
    ('orientation_statement', paragraphs[1]),
    ('core_courses_heading', next(p for p in paragraphs if 'Professional Core Courses' in p)),
    ('core_courses', paragraphs[-1]),
]:
    excerpts.append({'label': label, 'text': text, 'utf8_sha256': sha(text.encode()),
                     'source_scope': 'Exact DOM-rendered text; whitespace collapsed for paragraph excerpts'})
artifact_paths = [BODY, META, EXPERT_VIEW, EXPERT_RAW, EARLIER_REPLAY]
before = {str(p): sha(p.read_bytes()) for p in artifact_paths}
replay = json.loads(EARLIER_REPLAY.read_text())
result = {
    'at': datetime.now(timezone.utc).isoformat(),
    'mode': 'Offline design evidence inventory; no proposed rule implemented or evaluated',
    'official_url': metadata['url'], 'fetched_at': metadata['fetched_at'],
    'body_byte_sha256': sha(body), 'metadata_content_hash': metadata['content_hash'],
    'production_content_hash_matches': _content_hash(html) == metadata['content_hash'],
    'raw_source_lines': {'layout_wrapper': layout_line, 'actual_main_heading': heading_line},
    'original_artifacts': before, 'article_dom_inventory': inventory,
    'exact_dom_excerpts': excerpts,
    'earlier_reproduction_scope': {
        'body_bytes_identical_across_three_captures': replay['all_three_body_bytes_identical'],
        'original_candidate_confirm_selected': replay['originals'][0]['actual_candidate_confirm_replay']['selected'],
        'counterfactual_selected': {k:v['candidate_confirm_replay']['selected']
                                  for k,v in replay['in_memory_controls'].items()},
        'meaning': 'Structural controls isolate extraction/heading precedence. Selection after both controls does not prove exact programme identity.',
    },
    'assessment': 'Field-specific departmental undergraduate training description. Not demonstrably a multi-programme catalogue, not enough to prove one exact applicable awarded-degree programme.',
    'retention_recommendation': 'Keep as unresolved official subject/level resource lead; preserve exact header and curriculum context. Do not automatically make it PROGRAM_DETAIL or programme.exists evidence for exact applicant scope.',
    'unknowns': ['formal programme cardinality', 'exact awarded degree', 'international admission applicability', 'programme campus', 'teaching language', 'active admissions', 'fall2027 intake'],
    'originals_unchanged': all(sha(Path(p).read_bytes()) == h for p,h in before.items()),
    'network_actions': 0, 'provider_actions': 0,
}
assert result['production_content_hash_matches'] and result['originals_unchanged']
(OUT / 'dalian-content-heading.design-evidence.offline.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'body_sha256': result['body_byte_sha256'],
                  'article_main_headings': len(headings), 'paragraphs': len(paragraphs),
                  'programme_links': len(links), 'formal_degree_titles': [],
                  'intake_years': [], 'originals_unchanged': True,
                  'network_actions': 0, 'provider_actions': 0}))

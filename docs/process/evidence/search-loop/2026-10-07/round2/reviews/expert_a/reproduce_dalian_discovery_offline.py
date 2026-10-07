"""Read immutable Dalian captures and reproduce only the candidate-confirm stage.

No provider, production Fetcher, socket, or original-file mutation is used.
The wrapper/heading controls are in-memory only, not official source assertions.
"""
import asyncio
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from bs4 import BeautifulSoup

from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter, profile_rejects
from app.adapters.extraction import html_to_text
from app.adapters.fetching import FetchResult, _content_hash
from app.adapters.page_classifier import classify_page, main_content, _identity, _title, _CHROME_HINT
from app.adapters.search.identity import verify_candidate
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.retrieval import RankedCandidate
from app.domain.enums import DegreeLevel, FetchOutcome

WORK = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work')
REPO = WORK / 'ashyq-apply/backend'
OUT = Path(__file__).resolve().parent
CASE = '01d3bb22815c61aa8454283116cbd4fa'
URL = 'https://cs.dlut.edu.cn/ENGLISH/education/Undergraduate_Education.htm'
HEADING = 'Introduction to Undergraduate Training Programs in Computer Science and Technology'
BODY_REL = 'cache/1c/1c604897f3d098cef1ba5cef3e1b9584.body'
RUNS = {
    'baseline': ('development-baseline/20261007T164735Z', 'development-baseline-temp/canary-e9ioklso'),
    'fixed_repeat': ('scope-fix-repeat/20261007T172952Z', 'scope-fix-repeat-temp/canary-pya0cox3'),
    'prior_expert': (None, 'development-experts/expert_a/dalian'),
}
sha = lambda data: hashlib.sha256(data).hexdigest()


class OnlyGivenBody:
    def __init__(self, html):
        self.html = html
        self.reads = []

    async def get(self, url, **kwargs):
        self.reads.append(url)
        assert url == URL, f'Unexpected offline read: {url}'
        return FetchResult(url=url, final_url=url, outcome=FetchOutcome.OK,
                           content=self.html.encode(), text=self.html,
                           content_type='text/html', from_cache=True)


async def recover(html):
    fetcher = OnlyGivenBody(html)
    adapter = LiveDiscoveryAdapter(fetcher)
    profile = SimpleNamespace(context=SimpleNamespace(
        level=DegreeLevel.BACHELOR, intended_fields=['computer science']))
    trace = DiscoveryTrace('Dalian University of Technology', 'en.dlut.edu.cn')
    pages = []
    lead = RankedCandidate(URL, HEADING, 1.0, 'offline-retained-candidate')
    await adapter._recover_search_pages([lead], pages, trace, profile)
    return {'retained_body_reads': fetcher.reads, 'selected': pages,
            'rejected': trace.rejected, 'errors': trace.errors,
            'provider_queries': 0, 'network_calls': 0}


async def main():
    records = []
    originals = {}
    bodies = []
    for name, (run_rel, cache_rel) in RUNS.items():
        body = WORK / cache_rel / BODY_REL
        meta = body.with_suffix('.meta.json')
        raw_body, raw_meta = body.read_bytes(), meta.read_bytes()
        originals[str(body)] = sha(raw_body)
        originals[str(meta)] = sha(raw_meta)
        metadata = json.loads(raw_meta)
        html = raw_body.decode(metadata.get('encoding') or 'utf8')
        bodies.append(raw_body)
        soup = BeautifulSoup(html, 'lxml')
        main_dom = main_content(soup)
        page = classify_page(url=URL, html=html)
        heading_node = next(h for h in soup.find_all(['h1', 'h2'])
                            if ' '.join(h.get_text(' ', strip=True).split()) == HEADING)
        lost_ancestors = [{'tag': a.name, 'attrs': a.attrs}
                          for a in heading_node.parents
                          if a.get('class') and any(_CHROME_HINT.search(c) for c in a['class'])]
        record = {'name': name, 'body_path': str(body), 'body_byte_sha256': sha(raw_body),
                  'meta_path': str(meta), 'meta_byte_sha256': sha(raw_meta),
                  'fetched_at': metadata['fetched_at'],
                  'metadata_content_hash': metadata['content_hash'],
                  'computed_content_hash': _content_hash(html),
                  'hash_formula_matches': metadata['content_hash'] == _content_hash(html),
                  'official_main_heading_tag': heading_node.name,
                  'official_main_heading': HEADING,
                  'heading_survives_classifier_main_content': HEADING in main_dom.get_text(' ', strip=True),
                  'classifier_main_content_text': main_dom.get_text('\n', strip=True),
                  'chrome_hint_matching_ancestors_of_official_heading': lost_ancestors,
                  'main_h1_present': main_dom.find('h1') is not None,
                  'classifier_identity': _identity(main_dom, _title(soup)),
                  'classification': asdict(page),
                  'profile_rejection': profile_rejects(page, 'bachelor', ['computer science']),
                  'actual_candidate_confirm_replay': await recover(html)}
        if run_rel:
            paths = {ext: WORK / run_rel / f'{CASE}.{ext}'
                     for ext in ['raw.json', 'json', 'log', 'budget.json']}
            record['run_artifacts'] = {ext: {'path': str(p), 'byte_sha256': sha(p.read_bytes())}
                                       for ext, p in paths.items()}
            for p in paths.values():
                originals[str(p)] = sha(p.read_bytes())
            captured = json.loads(paths['raw.json'].read_text())['canary']['institutions'][0]
            record['captured_rejection'] = [entry for entry in captured['discovery_trace']['rejected_sample']
                                             if entry[0] == URL]
            record['captured_selected'] = captured['discovery_trace']['selected']
        assert record['hash_formula_matches']
        assert record['profile_rejection'] == (
            "page subject 'Undergraduate Education-计算机科学与技术学院' does not match requested fields ['computer science']")
        assert not record['actual_candidate_confirm_replay']['selected']
        records.append(record)
    assert len({sha(b) for b in bodies}) == 1

    html = bodies[0].decode('utf8')
    original_page = classify_page(url=URL, html=html)
    controls = {}
    for kind, remove_layout_word, promote_heading in [
        ('wrapper_only', True, False), ('heading_only', False, True),
        ('wrapper_and_heading', True, True),
    ]:
        shadow = BeautifulSoup(html, 'lxml')
        own_h2 = next(h for h in shadow.find_all('h2')
                      if ' '.join(h.get_text(' ', strip=True).split()) == HEADING)
        if remove_layout_word:
            wrapper = next(a for a in own_h2.parents if 'sidebar-page-container' in a.get('class', []))
            wrapper['class'] = ['page-container' if c == 'sidebar-page-container' else c for c in wrapper['class']]
        if promote_heading:
            own_h2.name = 'h1'
        shadow_html = str(shadow)
        shadow_page = classify_page(url=URL, html=shadow_html)
        shadow_main = main_content(BeautifulSoup(shadow_html, 'lxml'))
        controls[kind] = {
            'kind': 'In-memory structural control; original official bytes unchanged',
            'remove_only_sidebar_word_from_layout_wrapper': remove_layout_word,
            'promote_only_actual_main_h2_to_h1': promote_heading,
            'official_heading_survives_main_content': HEADING in shadow_main.get_text(' ',strip=True),
            'classification': asdict(shadow_page),
            'profile_rejection': profile_rejects(shadow_page, 'bachelor', ['computer science']),
            'candidate_confirm_replay': await recover(shadow_html)}
        assert shadow_page.academic_year is None
    assert controls['wrapper_only']['official_heading_survives_main_content']
    assert not controls['wrapper_only']['candidate_confirm_replay']['selected']
    assert not controls['heading_only']['official_heading_survives_main_content']
    assert not controls['heading_only']['candidate_confirm_replay']['selected']
    assert controls['wrapper_and_heading']['profile_rejection'] is None
    assert controls['wrapper_and_heading']['candidate_confirm_replay']['selected'] == [URL]

    intent = DiscoveryIntent(institution='Dalian University of Technology', domain='dlut.edu.cn',
                             degree=DegreeLevel.BACHELOR, field='computer science', intake_year=2027)
    subject_identity = verify_candidate(url=URL, intent=intent, title=HEADING, text=html_to_text(html))
    source_paths = [REPO / rel for rel in [
        'app/adapters/page_classifier.py', 'app/adapters/discovery/live_discovery.py',
        'app/adapters/search/identity.py', 'app/adapters/search/ontology.py',
        'app/adapters/search/ontology.json', 'app/adapters/requirements/web_requirements.py']]
    source_artifacts = {}
    for p in source_paths:
        content = p.read_bytes()
        dest = OUT / ('source-snapshot.' + p.name + '.txt')
        dest.write_bytes(content)
        originals[str(p)] = sha(content)
        source_artifacts[str(p)] = {'byte_sha256': sha(content), 'snapshot': str(dest)}
    assert all(sha(Path(p).read_bytes()) == expected for p, expected in originals.items())
    record = {'mode': 'offline candidate-confirm regression; no provider or Fetcher use',
              'at': datetime.now(timezone.utc).isoformat(),
              'case_id': CASE, 'base_revision_requested_by_parent': 'b0b1a9c',
              'source_artifacts': source_artifacts,
              'originals': records, 'all_three_body_bytes_identical': True,
              'in_memory_controls': controls,
              'identity_using_explicit_main_heading': asdict(subject_identity),
              'originals_unchanged_after_replay': True,
              'network_calls': 0, 'provider_calls': 0,
              'confirmed_loss': 'Earliest: main_content removes the content-bearing ancestor class sidebar-page-container via substring chrome regex, leaving only generic document title. Later independent loss: _identity ignores actual degree-and-field h2 when no h1 and chooses generic document title; profile gate rejects the generic subject. Same bytes/rejection in baseline and repeat.',
              'limits': 'Programme-description lead only. No proof of exact international Bachelor award, campus, teaching language, active admission or 2027 intake. Controls isolate two losses; preserving the wrapper alone does not make the current confirm stage select the page. Not a production patch design or 2027 claim.'}
    (OUT / 'dalian-discovery-loss.offline.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'confirmed_loss': True, 'body_sha256': records[0]['body_byte_sha256'],
                      'same_bytes_three_sources': True,
                      'original_selected': records[0]['actual_candidate_confirm_replay']['selected'],
                      'control_selected': {k:v['candidate_confirm_replay']['selected'] for k,v in controls.items()},
                      'intake_verdict': str(subject_identity.intake),
                      'active_verdict': str(subject_identity.active),
                      'network_calls': 0, 'provider_calls': 0,
                      'originals_unchanged': True}, ensure_ascii=False))


asyncio.run(main())

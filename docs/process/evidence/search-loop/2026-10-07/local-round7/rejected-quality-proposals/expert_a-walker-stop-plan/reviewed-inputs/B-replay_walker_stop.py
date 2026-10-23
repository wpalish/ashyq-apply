"""Actual frozen CatalogWalker replay with retained bytes and denied all I/O."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys

BASE = Path(__file__).resolve().parent
SOURCE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261007T220539Z-live-6d0aa77b/source/backend')


def denied(*args, **kwargs):
    raise AssertionError('Offline replay attempted forbidden network/process action')


socket.getaddrinfo = denied
socket.create_connection = denied
subprocess.run = denied
subprocess.Popen = denied
subprocess.check_output = denied
sys.path.insert(0, str(SOURCE))

from app.adapters.discovery.catalog_walker import CatalogWalker, CatalogWalk, WalkerLink
from app.adapters.discovery.live_discovery import _distinct_fields
from app.adapters.fetching import FetchOutcome, FetchResult

CATALOGUE = 'https://www.rug.nl/bachelors/alphabet'
CS = 'https://www.rug.nl/bachelors/computing-science'
INFO = 'https://www.rug.nl/bachelors/information-science'
ROBOTS = 'https://test.ucms.rug.nl/bachelors/pedagogical-sciences'


class RetainedFetcher:
    def __init__(self):
        self.calls = []
        self.pages = {}
        for row in json.loads((BASE / 'retained-cache-index.json').read_text()):
            meta = json.loads(Path(row['meta_path']).read_text())
            raw = Path(row['body_path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row['body_sha256']
            self.pages[row['url']] = (meta, raw)

    async def get(self, url, **kwargs):
        self.calls.append(url)
        if url == ROBOTS:
            return FetchResult(url=url, outcome=FetchOutcome.ROBOTS_DISALLOWED,
                error='Retained terminal log get#32: robots_disallowed; no synthetic HTML')
        if url == 'https://www.rug.nl/sitemaps/publicSitemap-00001.xml':
            return FetchResult(url=url, outcome=FetchOutcome.TOO_LARGE,
                error='Retained terminal log get#3: too_large; no body retained')
        if url not in self.pages:
            raise AssertionError('Offline evidence missing, no live fallback: ' + url)
        meta, body = self.pages[url]
        return FetchResult(url=url, outcome=FetchOutcome.OK, status_code=meta['status_code'],
            content=body, text=body.decode(meta['encoding'], errors='replace'),
            content_type=meta['content_type'], final_url=meta['final_url'],
            fetched_at=datetime.fromisoformat(meta['fetched_at']), from_cache=False,
            content_hash=meta['content_hash'])


class ConfirmedStop(Exception):
    def __init__(self, walk):
        self.walk = walk


class ProposedWalker(CatalogWalker):
    """External control-only prototype. Production flag would remain False."""

    def __init__(self, *args, stop_on_confirm=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_on_confirm = stop_on_confirm

    async def _read_lead(self, link, walk):
        await super()._read_lead(link, walk)
        if self.stop_on_confirm and len(_distinct_fields(self.fields)) == 1 and walk.confirmed:
            raise ConfirmedStop(walk)

    async def walk_catalog(self, *args, **kwargs):
        try:
            return await super().walk_catalog(*args, **kwargs)
        except ConfirmedStop as stopped:
            return stopped.walk


async def walk(flag=False, fields=None, frozen=False):
    fetcher = RetainedFetcher()
    cls = CatalogWalker if frozen else ProposedWalker
    kwargs = {} if frozen else {'stop_on_confirm': flag}
    walker = cls(fetcher=fetcher, domain='www.rug.nl', degree='bachelor',
        fields=['computer science'] if fields is None else fields, **kwargs)
    result = await walker.walk_catalog(CATALOGUE, top_n=5)
    return fetcher, result


async def direct(url, degree='bachelor', fields=None, foreign_redirect=False):
    fetcher = RetainedFetcher()
    if foreign_redirect:
        original = fetcher.get

        async def redirect(target, **kwargs):
            result = await original(target, **kwargs)
            result.final_url = 'https://foreign.example/programme'
            return result

        fetcher.get = redirect
    walker = ProposedWalker(fetcher=fetcher, domain='www.rug.nl', degree=degree,
        fields=['computer science'] if fields is None else fields, stop_on_confirm=True)
    result = CatalogWalk(CATALOGUE)
    stopped = False
    try:
        await walker._read_lead(WalkerLink(url=url, label='Retained official lead',
            score=1, source='html'), result)
    except ConfirmedStop:
        stopped = True
    return {'calls': fetcher.calls, 'confirmed': result.confirmed,
            'outcomes': result.outcomes, 'stopped_early': stopped}


async def replay():
    legacy_fetcher, legacy = await walk(frozen=True)
    off_fetcher, off = await walk(False)
    on_fetcher, on = await walk(True)
    assert legacy_fetcher.calls == off_fetcher.calls and asdict(legacy) == asdict(off)
    assert off.confirmed == on.confirmed == [CS]
    assert legacy_fetcher.calls == [CATALOGUE, CS, INFO,
        'https://www.rug.nl/bachelors/data-science-society',
        'https://www.rug.nl/bachelors/liberal-arts-and-sciences', ROBOTS]
    assert on_fetcher.calls == [CATALOGUE, CS]
    negatives = {'wrong_subject': await direct(INFO), 'wrong_degree': await direct(CS, degree='master'),
        'no_requested_subject': await direct(CS, fields=[]), 'access_robots': await direct(ROBOTS),
        'multiple_distinct_fields': await direct(CS, fields=['computer science', 'mathematics']),
        'off_site_redirect_synthetic': await direct(CS, foreign_redirect=True),
        'other_page_purpose': await direct('https://www.rug.nl/education/bachelor/bachelor-open-day')}
    assert all(not value['stopped_early'] for value in negatives.values())
    assert all(not negatives[key]['confirmed'] for key in negatives if key != 'multiple_distinct_fields')
    assert negatives['multiple_distinct_fields']['confirmed'] == [CS]
    return {'frozen_calls': legacy_fetcher.calls, 'off_calls': off_fetcher.calls,
        'on_calls': on_fetcher.calls, 'frozen': asdict(legacy), 'on': asdict(on),
        'read_admissions_saved_in_this_replay': len(legacy_fetcher.calls) - len(on_fetcher.calls),
        'negative_controls': negatives, 'network_calls': 0, 'provider_calls': 0,
        'model_calls': 0, 'rule_default': False,
        'scope_limit': 'Confirmed own bachelor subject identity only; no fall2027 requirements/fees fact proof',
        'full_pipeline_success': 'unknown; no provider result or production end-to-end replay invented'}


if __name__ == '__main__':
    result = asyncio.run(replay())
    (BASE / 'walker-stop.offline.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'frozen_gets': len(result['frozen_calls']), 'on_gets': len(result['on_calls']),
        'confirmed': result['on']['confirmed'], 'negative_controls': len(result['negative_controls'])}))

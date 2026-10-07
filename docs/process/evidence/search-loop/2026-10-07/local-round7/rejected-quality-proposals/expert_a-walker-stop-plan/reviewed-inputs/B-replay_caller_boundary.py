"""Actual Catalogue._enrich→_discover_one caller until saved search boundary."""

import asyncio
from dataclasses import asdict
import json
from pathlib import Path
from types import SimpleNamespace

from replay_walker_stop import BASE, RetainedFetcher, CS

from app.adapters.base import Candidate
from app.adapters.discovery.live_discovery import DiscoveryTrace, PageCategory
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from scripts.canary_discovery import canary_profile


class BoundaryAdapter(CatalogueDiscoveryAdapter):
    async def _identify_site(self, *args, **kwargs):
        raise AssertionError('Curated registry entry must bypass identity probing here')

    async def _add_search_results(self, entry, domain, selected, trace, profile):
        # This replaces only the non-retained provider seam. It proves input
        # to the real caller, not the result of the six actual search calls.
        self.search_boundary = {
            'selected': {k: list(v) for k, v in selected.items()},
            'walker': json.loads(json.dumps(trace.walker)),
            'fields': list(profile.context.intended_fields),
            'level': str(profile.context.level),
            'intake_year': profile.context.intake_year,
            'reads_completed_before_search': list(self.fetcher.calls),
        }


async def replay():
    public = json.loads((BASE / 'retained-public-entry.json').read_text())
    uni = SimpleNamespace(**{k: public[k] for k in ['id', 'name', 'country', 'city', 'domain', 'registry_entry']})
    fetcher = RetainedFetcher()
    adapter = BoundaryAdapter(fetcher, session=None, university_ids=[uni.id], live_limit=1)
    initial = Candidate(name=uni.name, country=uni.country, city=uni.city)
    profile = canary_profile()
    result, trace = await adapter._enrich(uni, profile, initial, DiscoveryTrace(uni.name, uni.domain))
    boundary = adapter.search_boundary
    assert boundary['selected'][PageCategory.PROGRAM_PAGE] == [CS]
    assert boundary['walker']['programs_confirmed'] == 1
    assert boundary['reads_completed_before_search'][-6:] == [
        'https://www.rug.nl/bachelors/alphabet', CS,
        'https://www.rug.nl/bachelors/information-science',
        'https://www.rug.nl/bachelors/data-science-society',
        'https://www.rug.nl/bachelors/liberal-arts-and-sciences',
        'https://test.ucms.rug.nl/bachelors/pedagogical-sciences']
    actual = json.loads((BASE / 'terminal-log-counters.json').read_text())
    assert boundary['reads_completed_before_search'] == actual['get_urls'][:32]
    return {
        'identity_probe_called': False, 'curated_entry_used': True,
        'same_frozen_canary_profile': {'degree': boundary['level'], 'fields': boundary['fields'],
            'intake_year': boundary['intake_year']},
        'search_boundary': boundary, 'candidate_after_no_provider_result_control': asdict(result),
        'trace_after_no_provider_result_control': trace.as_dict(),
        'full_32_get_prefix_matches_live_log': True,
        'provider_result_control': 'search replaced by no-op; actual provider results unknown',
        'actual_timeout_result': 'does not return from discovery; DB0 program_results/claims',
        'network_calls': 0, 'provider_calls': 0, 'model_calls': 0,
    }


if __name__ == '__main__':
    result = asyncio.run(replay())
    (BASE / 'caller-boundary.offline.json').write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({'identity_probe_called': result['identity_probe_called'],
        'confirmed_before_search': result['search_boundary']['selected']['program_page'],
        'get_prefix_matches': result['full_32_get_prefix_matches_live_log']}))

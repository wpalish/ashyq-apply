"""Offline protocol-only controls using the actual terminal Toronto capture."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
import socket
import subprocess
import pytest

from test_validate_v4_legacy29 import pilot

BASE = Path(__file__).resolve().parent
TORONTO = pilot.PRIOR / 'execution/toronto/capture/20261007T223010Z'

@pytest.fixture(autouse=True)
def no_external_actions(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('offline review forbids external actions/main')
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    for name in ('Popen', 'run', 'check_output'):
        monkeypatch.setattr(subprocess, name, denied)
    monkeypatch.setattr(pilot, 'main', denied)


def fixture(tmp_path):
    for name in ('capture.json', 'toronto.budget.json', 'toronto.json', 'toronto.raw.json'):
        shutil.copy2(TORONTO / name, tmp_path / name)
    return json.loads((tmp_path / 'capture.json').read_text())


def flush(tmp_path, c, raw=None):
    b = deepcopy(c['config']['case_budgets']['toronto'])
    for k in ('parent_process_elapsed_seconds', 'process_error', 'active_checkpoint_available'):
        b.pop(k, None)
    (tmp_path / 'toronto.budget.json').write_text(json.dumps(b))
    (tmp_path / 'toronto.json').write_text(json.dumps(c['observations'][0]))
    if raw is not None:
        (tmp_path / 'toronto.raw.json').write_text(json.dumps(raw))


def check_rejected(c, tmp_path):
    result = pilot.validate(c, 'toronto', tmp_path)
    assert result['errors'], result
    assert not result.get('bounded_page_cap_with_full_raw', False), result
    return result


def test_actual_toronto_bounded_pagecap_accepted(tmp_path):
    c = fixture(tmp_path)
    result = pilot.validate(c, 'toronto', tmp_path)
    assert result['errors'] == [], result
    assert result['bounded_page_cap_with_full_raw'] is True
    assert result['bounded_timeout_without_full_raw'] is False
    assert result['quality_status'] == 'UNSCORED'
    assert result['fetcher_calls'] == 60


@pytest.mark.parametrize('count', [59, 61, True, 60.0])
def test_pagecap_requires_exact_typed_sixty(tmp_path, count):
    c = fixture(tmp_path)
    c['config']['case_budgets']['toronto']['fetcher_calls'] = count
    c['observations'][0]['telemetry']['http_fetches'] = count
    flush(tmp_path, c)
    check_rejected(c, tmp_path)


@pytest.mark.parametrize('reason', [None, 'search_budget_exhausted', 'http_429', 'unknown_stop'])
def test_exact_error_requires_exact_page_reason(tmp_path, reason):
    c = fixture(tmp_path)
    c['config']['case_budgets']['toronto']['stop_reason'] = reason
    flush(tmp_path, c)
    check_rejected(c, tmp_path)


@pytest.mark.parametrize('error', ['BENCHMARK_PAGE_BUDGET_EXHAUSTED', 'RuntimeError: unrelated',
                                 'RuntimeError: BENCHMARK_PAGE_BUDGET_EXHAUSTED suffix'])
def test_pagecap_exact_error_only(tmp_path, error):
    c = fixture(tmp_path)
    c['observations'][0]['error'] = error
    raw = json.loads((tmp_path / 'toronto.raw.json').read_text())
    raw['canary']['run_error'] = error
    flush(tmp_path, c, raw)
    check_rejected(c, tmp_path)


@pytest.mark.parametrize('file', ['toronto.raw.json', 'toronto.budget.json', 'toronto.json'])
def test_pagecap_needs_all_physical_evidence(tmp_path, file):
    c = fixture(tmp_path)
    (tmp_path / file).unlink()
    check_rejected(c, tmp_path)


@pytest.mark.parametrize('text', ['', '{}', '[]', 'not-json'])
def test_pagecap_malformed_raw_rejected(tmp_path, text):
    c = fixture(tmp_path)
    (tmp_path / 'toronto.raw.json').write_text(text)
    check_rejected(c, tmp_path)


def test_pagecap_physical_budget_disagrees(tmp_path):
    c = fixture(tmp_path)
    b = json.loads((tmp_path / 'toronto.budget.json').read_text())
    b['fetcher_calls'] = 59
    (tmp_path / 'toronto.budget.json').write_text(json.dumps(b))
    check_rejected(c, tmp_path)


def test_pagecap_physical_observation_disagrees(tmp_path):
    c = fixture(tmp_path)
    obs = json.loads((tmp_path / 'toronto.json').read_text())
    obs['error'] = None
    (tmp_path / 'toronto.json').write_text(json.dumps(obs))
    check_rejected(c, tmp_path)


def test_pagecap_cannot_mask_explicit_vendor_failure(tmp_path):
    c = fixture(tmp_path)
    c['config']['case_budgets']['toronto']['provider_failure'] = {'http_status': 429, 'reason': 'provider refused'}
    flush(tmp_path, c)
    check_rejected(c, tmp_path)


def test_pagecap_raw_terminal_error_mismatch_rejected(tmp_path):
    c = fixture(tmp_path)
    raw = json.loads((tmp_path / 'toronto.raw.json').read_text())
    raw['canary']['run_error'] = ''
    flush(tmp_path, c, raw)
    check_rejected(c, tmp_path)


@pytest.mark.parametrize('count', [59, 60])
def test_pagecap_reason_cannot_claim_error_free_completion(tmp_path, count):
    # The production guard throws on this fatal reason; a completed observation
    # cannot be accepted by bypassing the narrowly permitted error branch.
    c = fixture(tmp_path)
    c['config']['case_budgets']['toronto']['fetcher_calls'] = count
    c['observations'][0]['telemetry']['http_fetches'] = count
    c['observations'][0]['error'] = None
    raw = json.loads((tmp_path / 'toronto.raw.json').read_text())
    raw['canary']['run_error'] = ''
    flush(tmp_path, c, raw)
    check_rejected(c, tmp_path)


@pytest.mark.parametrize('case', ['groningen', 'delft', 'aalto', 'vienna', 'warsaw', 'ubc', 'toronto'])
def test_seven_actual_terminal_captures_still_valid(case):
    paths = list((pilot.PRIOR / 'execution' / case / 'capture').glob('*/capture.json'))
    assert len(paths) == 1
    c = json.loads(paths[0].read_text())
    result = pilot.validate(c, case, paths[0].parent)
    assert not result['errors'], result
    assert result['quality_status'] == 'UNSCORED'

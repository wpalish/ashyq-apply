"""Cold offline validator review, with synthetic physical evidence; no main."""

from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import socket
import subprocess

import pytest

from test_validate_v1 import envelope

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "local_pilot.v3-reviewed.py"
spec = importlib.util.spec_from_file_location("local_pilot_v2_offline_review", SOURCE)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


@pytest.fixture(autouse=True)
def no_external_actions(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("Review attempted a forbidden external action")

    monkeypatch.setattr(socket, "getaddrinfo", refused)
    monkeypatch.setattr(socket, "create_connection", refused)
    monkeypatch.setattr(subprocess, "Popen", refused)
    monkeypatch.setattr(subprocess, "run", refused)
    monkeypatch.setattr(subprocess, "check_output", refused)
    monkeypatch.setattr(pilot, "main", refused)


def capture():
    c = envelope()
    cfg = c["config"]
    cfg.update(cold_fetcher_reads=True, child_active_seconds=120,
               parent_process_reserve_seconds=15, parent_process_timeout_seconds=135,
               batch_attempted_case_ids=["groningen"], batch_completed_case_ids=["groningen"],
               batch_remaining_case_ids=[], batch_stop_reason=None)
    source = pilot.PREPARED / "source/backend/evaluation/research"
    cfg["harness_sha256"] = pilot.digest(source / "live.py")
    cfg["mapping_sha256"] = pilot.digest(source / "mapping.py")
    c["observations"][0].update(programme_urls=[])
    c["observations"][0]["telemetry"].update(http_fetches=2, search_calls=1,
                                             model_input_tokens=0, jev_input_tokens=0)
    return c


def full_raw():
    # Full retained schema, adapted only for synthetic protocol identity.
    p = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/development-baseline/20261007T164735Z/0386940c5cef525b3c8e7966868f5ed6.raw.json')
    r = json.loads(p.read_text())
    r['canary']['batch'] = ['University of Groningen']
    r["canary"]["institutions"][0].update(domain="rug.nl", programs=[],
        catalogue_id=None, institution='University of Groningen', country='Netherlands')
    return r


def evidence(tmp_path, c, r=None):
    b = deepcopy(c["config"]["case_budgets"]["groningen"])
    for k in ("parent_process_elapsed_seconds", "process_error", "active_checkpoint_available"):
        b.pop(k, None)
    (tmp_path / "groningen.budget.json").write_text(json.dumps(b))
    (tmp_path / "groningen.json").write_text(json.dumps(c["observations"][0]))
    (tmp_path / "groningen.raw.json").write_text(json.dumps(full_raw() if r is None else r))


def accepted(c, tmp_path):
    result = pilot.validate(c, "groningen", tmp_path)
    assert result["errors"] == [], result
    return result


def rejected(c, tmp_path):
    result = pilot.validate(c, "groningen", tmp_path)
    assert result["errors"], result


def test_actual_strict_get_vs_network_semantics_accepted(tmp_path):
    c = capture()
    assert c["config"]["case_budgets"]["groningen"]["fetcher_calls"] == 2
    assert c["config"]["case_budgets"]["groningen"]["network_http_requests"] == 3
    evidence(tmp_path, c)
    accepted(c, tmp_path)


def test_normalized_observation_programme_url_accepted(tmp_path):
    c = capture()
    c["observations"][0]["programme_urls"] = ["https://example.edu/"]
    r = full_raw()
    r["canary"]["institutions"][0]["programs"] = ["https://example.edu"]
    evidence(tmp_path, c, r)
    accepted(c, tmp_path)


def test_retained_actual_schema_with_adapted_protocol_provenance_accepted(tmp_path):
    old = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/development-baseline/20261007T164735Z')
    r = json.loads((old / '0386940c5cef525b3c8e7966868f5ed6.raw.json').read_text())
    b = json.loads((old / '0386940c5cef525b3c8e7966868f5ed6.budget.json').read_text())
    c = capture()
    b['provider'] = 'exa_mcp'  # Synthetic identity/provenance adaptation only.
    c['config']['case_budgets']['groningen'] = {**b, 'process_error': None,
        'active_checkpoint_available': True, 'parent_process_elapsed_seconds': 12.0}
    c['observations'][0]['telemetry'].update(http_fetches=b['fetcher_calls'],
        search_calls=b['search_queries'], latency_seconds=b['elapsed_ms'] / 1000)
    c['observations'][0]['programme_urls'] = r['canary']['institutions'][0]['programs']
    r['canary']['institutions'][0]['domain'] = 'rug.nl'
    evidence(tmp_path, c, r)
    accepted(c, tmp_path)


def test_bounded_timeout_missing_raw_accepted_and_marked(tmp_path):
    c = capture()
    c['observations'][0]['error'] = 'BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED'
    c['config']['case_budgets']['groningen']['stop_reason'] = 'source_work_deadline_exhausted'
    c['config']['case_budgets']['groningen']['elapsed_ms'] = 117050
    c['config']['case_budgets']['groningen']['parent_process_elapsed_seconds'] = 117.1
    c['observations'][0]['telemetry']['latency_seconds'] = 117.04
    evidence(tmp_path, c)
    (tmp_path / 'groningen.raw.json').unlink()
    assert accepted(c, tmp_path)['bounded_timeout_without_full_raw'] is True


@pytest.mark.parametrize('key', ['fetcher_calls', 'search_queries', 'provider_failure', 'process_error',
                                 'strict_expert_budget', 'network_http_requests'])
def test_missing_required_budget_fields_rejected(tmp_path, key):
    c = capture()
    evidence(tmp_path, c)
    c['config']['case_budgets']['groningen'].pop(key)
    rejected(c, tmp_path)


@pytest.mark.parametrize('part,value', [('config', None), ('config', []), ('observations', None),
                                      ('observations', [None]), ('pipeline_sha', 'wrong'), ('mode', 'fixture')])
def test_malformed_or_wrong_capture_rejected(tmp_path, part, value):
    c = capture()
    evidence(tmp_path, c)
    c[part] = value
    rejected(c, tmp_path)


@pytest.mark.parametrize('file', ['groningen.json', 'groningen.budget.json', 'groningen.raw.json'])
def test_missing_physical_evidence_rejected(tmp_path, file):
    c = capture()
    evidence(tmp_path, c)
    (tmp_path / file).unlink()
    rejected(c, tmp_path)


@pytest.mark.parametrize('text', ['', '{}', '[]', 'not-json'])
def test_malformed_full_raw_rejected(tmp_path, text):
    c = capture()
    evidence(tmp_path, c)
    (tmp_path / 'groningen.raw.json').write_text(text)
    rejected(c, tmp_path)


def test_http429_without_failure_envelope_rejected(tmp_path):
    c = capture()
    c['config']['case_budgets']['groningen']['stop_reason'] = 'http_429'
    evidence(tmp_path, c)
    rejected(c, tmp_path)


def test_missing_physical_meter_rejected(tmp_path):
    c = capture()
    evidence(tmp_path, c)
    b = json.loads((tmp_path / 'groningen.budget.json').read_text())
    b.pop('fetcher_calls')
    (tmp_path / 'groningen.budget.json').write_text(json.dumps(b))
    rejected(c, tmp_path)


def test_missing_observation_telemetry_rejected(tmp_path):
    c = capture()
    c['observations'][0].pop('telemetry')
    evidence(tmp_path, c)
    rejected(c, tmp_path)


def test_raw_terminal_error_contradicts_completed_observation_must_reject(tmp_path):
    c = capture()
    r = full_raw()
    r['canary']['run_error'] = 'RuntimeError: interrupted before terminal report'
    evidence(tmp_path, c, r)
    rejected(c, tmp_path)


def test_raw_terminal_totals_missing_meters_must_reject(tmp_path):
    c = capture()
    r = full_raw()
    r['canary']['totals'] = {}
    evidence(tmp_path, c, r)
    rejected(c, tmp_path)


def test_claimed_source_deadline_at_one_second_must_reject(tmp_path):
    c = capture()
    c['observations'][0]['error'] = 'BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED'
    c['config']['case_budgets']['groningen']['stop_reason'] = 'source_work_deadline_exhausted'
    evidence(tmp_path, c)
    (tmp_path / 'groningen.raw.json').unlink()
    rejected(c, tmp_path)

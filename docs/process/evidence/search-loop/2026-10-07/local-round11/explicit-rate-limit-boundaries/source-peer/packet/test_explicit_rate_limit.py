"""Actual native methods in fresh denied-transport processes; frozen OFF controls retained."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

B = Path(__file__).resolve().parent
PYTHON = B.parents[1] / 'ashyq-apply/backend/.venv/bin/python'
SCENARIOS = (
    'factory:meta', 'factory:no-retry', 'factory:http429', 'factory:success',
    'factory:transport', 'factory:timeout', 'factory:meta-false', 'factory:meta-one',
    'factory:meta-string', 'factory:vendor-text', 'factory:vendor-error',
    'retrieval:meta', 'retrieval:no-retry', 'retrieval:http429', 'retrieval:success',
    'retrieval:transport', 'retrieval:timeout', 'retrieval:vendor-error',
    'caller:single-meta', 'caller:multi-meta', 'caller:single-429', 'caller:multi-429',
    'caller:single-success', 'caller:multi-success', 'native:expiry',
    'native:recovery-meta', 'retrieval:meta-unwrapped', 'state:stamp', 'state:expiry',
    'state:isolation', 'state:stale', 'state:reset', 'state:string-reason',
    'state:vendor-text', 'state:429-untyped', 'state:500-typed', 'state:legacy-float',
)
NORMAL = (
    'factory:success', 'factory:transport', 'factory:timeout', 'factory:meta-false',
    'factory:meta-one', 'factory:meta-string', 'factory:vendor-text', 'factory:vendor-error',
    'retrieval:success', 'retrieval:transport', 'retrieval:timeout', 'retrieval:vendor-error',
    'caller:single-success', 'caller:multi-success', 'native:recovery-meta',
)


def execute(mode: str, scenario: str, lane: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    directory = f'pytest-controls/{lane}/{scenario.replace(":", "-")}'
    proc = subprocess.run(
        [str(PYTHON), str(B / 'run_control.py'), mode, scenario, directory],
        cwd=PYTHON.parent.parent.parent, env=env, capture_output=True, text=True, timeout=30,
    )
    dest = B / directory / (mode + '.log')
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert not dest.exists()
    dest.write_text(proc.stdout + proc.stderr)
    result = B / directory / (scenario.replace(':', '-') + '.' + mode + '.json')
    assert result.exists(), proc.stderr
    return proc, json.loads(result.read_text())


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_explicit_refusal_or_negative_control(scenario: str) -> None:
    proc, result = execute('on', scenario, 'enabled')
    assert proc.returncode == 0, [row for row in result['checks'] if row['status'] == 'RED']
    assert result['counts']['RED'] == 0
    assert result['native_source_before'] == result['native_source_after']
    assert result['proposal_source_before'] == result['proposal_source_after']
    assert result['real_network_provider_model_Git_app_STOP_changes'] == 0


@pytest.mark.parametrize('scenario', NORMAL)
def test_full_normal_outputs_and_dispatches_equal_frozen_source(scenario: str) -> None:
    off_proc, off = execute('off', scenario, 'equality')
    on_proc, on = execute('on', scenario, 'equality')
    assert off_proc.returncode == on_proc.returncode == 0
    for key in ('outputs', 'query_seam_attempts', 'mock_HTTP_events', 'mock_HTTP_counts', 'fake_clock_sleeps'):
        assert off[key] == on[key], key

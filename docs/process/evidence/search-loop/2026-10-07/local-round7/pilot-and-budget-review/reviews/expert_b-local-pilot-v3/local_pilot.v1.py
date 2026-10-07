"""Fresh local UNSCORED pilot: reuse prepared runner isolation, never resume trials."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import subprocess
from datetime import datetime, timezone

ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
BUNDLE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
PREPARED = BUNDLE / 'runs/20261007T220539Z-live-6d0aa77b'
REPO = ROOT / 'work/ashyq-apply'
OWNED = ROOT / 'work/local-round7/baseline-original10'
PROVIDER_STOP = ROOT / 'work/local-round7/provider-STOP.json'
HISTORICAL_STOP = ROOT / 'work/development-STOP.json'
HISTORICAL_SHA = 'dd669c6d73d89ba2586676b46b120e4c8af2ea95e4e15cd7ae75c554f9557cad'
EXPECTED_HEAD = '7277c154bda838688268b7a07d4286ed8f4688ce'
EXPECTED_TREE = 'b18f63fe7bf47773ffd6f97ef0cea45967a4fa061dd616da0aafa5723389826b'
CASES = ('groningen', 'delft', 'aalto', 'vienna', 'warsaw', 'ubc', 'toronto', 'hku', 'ntu', 'kaist')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def write_new(path, obj):
    with path.open('x') as out:
        json.dump(obj, out, indent=2, ensure_ascii=False)
        out.write('\n')

def executable(name):
    return name.startswith(('backend/app/', 'backend/evaluation/', 'backend/tests/',
                            'backend/scripts/', 'backend/alembic/', 'frontend/src/', 'frontend/e2e/')) or name in (
        'backend/requirements.txt', 'backend/requirements-dev.txt', 'backend/pytest.ini',
        'frontend/package.json', 'frontend/package-lock.json')

def validate(capture, case, raw_root):
    errors = []
    cfg = capture.get('config', {})
    expected = {'strict_expert_budget': True, 'seconds_per_case': 120,
                'max_fetcher_calls_per_case': 60, 'max_search_queries_per_case': 6,
                'finalization_reserve_ms': 3000, 'source_work_deadline_ms': 117000,
                'search_provider': 'exa_mcp', 'browser_enabled': False,
                'site_branding_identity': False, 'subject_phrase_match': False,
                'programme_identity_before_funding': False, 'shared_query_budget': True}
    if capture.get('pipeline_sha') != EXPECTED_HEAD:
        errors.append('wrong_pipeline_head')
    for key, value in expected.items():
        if type(cfg.get(key)) is not type(value) or cfg.get(key) != value:
            errors.append('wrong_config:' + key)
    if cfg.get('cohort') != [case]:
        errors.append('wrong_cohort')
    observations = capture.get('observations', [])
    if len(observations) != 1 or observations[0].get('case_id') != case:
        errors.append('missing_or_wrong_observation')
    budget = cfg.get('case_budgets', {}).get(case, {})
    for key, cap in [('fetcher_calls', 60), ('search_queries', 6), ('elapsed_ms', 120000)]:
        value = budget.get(key)
        if type(value) is not int or not 0 <= value <= cap:
            errors.append('invalid_cap:' + key)
    if budget.get('provider') != 'exa_mcp':
        errors.append('wrong_budget_provider')
    if budget.get('active_checkpoint_available') is not True:
        errors.append('missing_active_checkpoint')
    if budget.get('process_error') is not None:
        errors.append('process_error')
    if budget.get('provider_failure') is not None or cfg.get('batch_stop_reason'):
        errors.append('stopped_batch')
    missing_raw = False
    if observations:
        error = observations[0].get('error')
        bounded = error == 'BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED' and budget.get('stop_reason') == 'source_work_deadline_exhausted'
        if error is not None and not bounded:
            errors.append('unavailable_observation')
        missing_raw = not (raw_root / (case + '.raw.json')).is_file()
        if missing_raw and error is None:
            errors.append('missing_completed_raw')
    return {'errors': errors, 'bounded_timeout_without_full_raw': missing_raw and not errors,
            'fetcher_calls': budget.get('fetcher_calls'), 'search_queries': budget.get('search_queries'),
            'elapsed_ms': budget.get('elapsed_ms'), 'quality_status': 'UNSCORED'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('local_runner_pilot', BUNDLE / 'run_local.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    prepared = read(PREPARED / 'summary.json')
    manifest = read(PREPARED / 'source-manifest.json')
    snapshot = Path(manifest['snapshot'])
    assert prepared['status'] == 'prepared_not_executed'
    assert manifest['source_head'] == EXPECTED_HEAD and manifest['source_status'] == ''
    assert manifest['source_tree_sha256'] == EXPECTED_TREE
    assert runner.git(REPO, 'rev-parse', 'HEAD') == EXPECTED_HEAD
    assert runner.git(REPO, 'status', '--porcelain=v1') == ''
    assert digest(HISTORICAL_STOP) == HISTORICAL_SHA
    assert not PROVIDER_STOP.exists(), 'Global live STOP; no retries'
    full = read(BUNDLE / 'runs/20261007T214413Z-check-1f0de05f/source-manifest.json')
    files = manifest['files']
    assert {n: h for n, h in files.items() if executable(n)} == {n: h for n, h in full['files'].items() if executable(n)}
    assert all(digest(snapshot / n) == h for n, h in files.items())
    assert runner.git(snapshot, 'rev-parse', 'HEAD') == EXPECTED_HEAD
    commands = []
    for case in CASES:
        command = list(prepared['live_plan']['command'])
        command[command.index('--case') + 1] = case
        command[command.index('--out') + 1] = str(OWNED / 'execution' / case / 'capture')
        command += ['--stop-file', str(PROVIDER_STOP), '--finalization-reserve-ms', '3000']
        commands.append({'case': case, 'argv': command, 'cwd': str(snapshot / 'backend')})
    plan = {'kind': 'NEW fresh local original10 UNSCORED algorithm baseline',
            'created_at': datetime.now(timezone.utc).isoformat(), 'source_head': EXPECTED_HEAD,
            'source_tree_sha256': EXPECTED_TREE, 'source_matches_full_checked_executable_files': True,
            'package_plan_sha256': digest(PREPARED / 'live-plan.json'),
            'package_runner_sha256': digest(BUNDLE / 'run_local.py'),
            'controller_sha256': digest(Path(__file__)), 'ordered_cases': list(CASES),
            'provider': 'exa_mcp', 'model_calls': 0, 'network_location': 'local computer, not Fly',
            'commands': commands, 'limits': {'reads': 60, 'queries': 6, 'active_ms': 120000,
                                           'source_work_ms': 117000, 'finalization_reserve_ms': 3000},
            'expert_controller_started': False, 'heldout_used': False, 'automatic_scoring': False,
            'query_policy': 'Unchanged frozen algorithm planner; actual query/action traces retained',
            'on_first_new_refusal': 'global stop without retry/substitution/reset/purchase',
            'missing_or_invalid_checkpoint': 'stop remaining cases, protocol unknown; no invented score'}
    OWNED.mkdir(exist_ok=True)
    if not args.execute:
        write_new(OWNED / 'plan.json', plan)
        print('PREPARED ONLY', OWNED / 'plan.json', digest(OWNED / 'plan.json'))
        return
    pinned = read(OWNED / 'plan.json')
    for key in plan.keys() - {'created_at'}:
        assert pinned[key] == plan[key], 'Prepared plan changed: ' + key
    execution = OWNED / 'execution'
    execution.mkdir()  # one-shot: no resume/overwrite of this baseline
    with (BUNDLE / '.run.lock').open('r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        env = runner.safe_env(Path(read(BUNDLE / 'config.json')['node_bin']), execution)
        run = runner.Run(execution, env, manifest)
        run.summary.update(plan_sha256=digest(OWNED / 'plan.json'), live_network_capture_started=True,
                           case_results=[], quality_status='UNSCORED')
        run.save()
        for index, item in enumerate(commands):
            if PROVIDER_STOP.exists():
                run.summary['remaining_cases'] = list(CASES[index:])
                run.finish('GLOBAL_PROVIDER_STOP_UNSCORED')
                return
            code = run.step('case-' + item['case'], item['argv'], Path(item['cwd']))
            paths = list((execution / item['case'] / 'capture').glob('*/capture.json'))
            result = {'case': item['case'], 'exit_code': code}
            if len(paths) == 1:
                result.update(capture_path=str(paths[0]), **validate(read(paths[0]), item['case'], paths[0].parent))
            else:
                result['errors'] = ['missing_or_ambiguous_capture']
            run.summary['case_results'].append(result)
            run.save()
            if PROVIDER_STOP.exists():
                run.summary['remaining_cases'] = list(CASES[index + 1:])
                run.finish('GLOBAL_PROVIDER_STOP_UNSCORED')
                return
            if code or result['errors']:
                run.summary['remaining_cases'] = list(CASES[index + 1:])
                write_new(OWNED / 'protocol-stop.json', result)
                run.finish('PROTOCOL_STOP_UNSCORED')
                return
        run.summary['remaining_cases'] = []
        assert all(digest(snapshot / n) == h for n, h in files.items())
        assert digest(HISTORICAL_STOP) == HISTORICAL_SHA
        run.finish('TEN_CASES_CAPTURED_UNSCORED')

if __name__ == '__main__':
    main()

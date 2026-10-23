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
from pydantic import HttpUrl

ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
BUNDLE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
PREPARED = BUNDLE / 'runs/20261007T220539Z-live-6d0aa77b'
REPO = ROOT / 'work/ashyq-apply'
OWNED = ROOT / 'work/local-round7/remaining3-v4'
PRIOR = ROOT / 'work/local-round7/baseline-original10-v2'
PRIOR_RECEIPT = OWNED / 'prior-revalidation.json'
PROVIDER_STOP = ROOT / 'work/local-round7/provider-STOP.json'
HISTORICAL_STOP = ROOT / 'work/development-STOP.json'
HISTORICAL_SHA = 'dd669c6d73d89ba2586676b46b120e4c8af2ea95e4e15cd7ae75c554f9557cad'
EXPECTED_HEAD = '7277c154bda838688268b7a07d4286ed8f4688ce'
EXPECTED_TREE = 'b18f63fe7bf47773ffd6f97ef0cea45967a4fa061dd616da0aafa5723389826b'
CASES = ('hku', 'ntu', 'kaist')

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

def _validate(capture, case, raw_root):
    errors = []
    if not isinstance(capture, dict):
        return {'errors': ['capture_not_object'], 'quality_status': 'UNSCORED'}
    cfg = capture.get('config', {})
    if not isinstance(cfg, dict):
        return {'errors': ['config_not_object'], 'quality_status': 'UNSCORED'}
    if capture.get('mode') != 'live':
        errors.append('wrong_capture_mode')
    expected = {'strict_expert_budget': True, 'seconds_per_case': 120,
                'max_fetcher_calls_per_case': 60, 'max_search_queries_per_case': 6,
                'finalization_reserve_ms': 3000, 'source_work_deadline_ms': 117000,
                'search_provider': 'exa_mcp', 'browser_enabled': False,
                'site_branding_identity': False, 'subject_phrase_match': False,
                'programme_identity_before_funding': False, 'shared_query_budget': True,
                'cold_fetcher_reads': True, 'child_active_seconds': 120,
                'parent_process_reserve_seconds': 15, 'parent_process_timeout_seconds': 135}
    if capture.get('pipeline_sha') != EXPECTED_HEAD:
        errors.append('wrong_pipeline_head')
    for key, value in expected.items():
        if type(cfg.get(key)) is not type(value) or cfg.get(key) != value:
            errors.append('wrong_config:' + key)
    if cfg.get('cohort') != [case]:
        errors.append('wrong_cohort')
    for key, value in {'batch_attempted_case_ids': [case], 'batch_completed_case_ids': [case],
                       'batch_remaining_case_ids': [], 'batch_stop_reason': None}.items():
        if key not in cfg or cfg[key] != value:
            errors.append('wrong_batch_metadata:' + key)
    observations = capture.get('observations', [])
    if not isinstance(observations, list) or any(not isinstance(o, dict) for o in observations):
        return {'errors': ['invalid_observation_container'], 'quality_status': 'UNSCORED'}
    if len(observations) != 1 or observations[0].get('case_id') != case:
        errors.append('missing_or_wrong_observation')
    budgets = cfg.get('case_budgets', {})
    if not isinstance(budgets, dict) or not isinstance(budgets.get(case), dict):
        return {'errors': ['invalid_budget_container'], 'quality_status': 'UNSCORED'}
    budget = budgets[case]
    child_keys = {'strict_expert_budget', 'provider', 'max_fetcher_calls', 'max_search_queries',
                  'max_active_seconds', 'finalization_reserve_ms', 'source_work_deadline_ms',
                  'fetcher_calls', 'search_queries', 'blocked_search_queries', 'network_http_requests',
                  'elapsed_ms', 'stop_reason', 'provider_failure', 'active_time_basis'}
    if not child_keys.issubset(budget):
        errors.append('missing_budget_fields')
    if not {'active_checkpoint_available', 'process_error', 'parent_process_elapsed_seconds'}.issubset(budget):
        errors.append('missing_parent_budget_fields')
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
    if budget.get('stop_reason') not in {None, 'source_work_deadline_exhausted', 'page_budget_exhausted', 'search_budget_exhausted'}:
        errors.append('unrecognized_or_refused_stop_reason')
    for key in ['blocked_search_queries', 'network_http_requests']:
        if type(budget.get(key)) is not int or budget[key] < 0:
            errors.append('invalid_counter:' + key)
    elapsed = budget.get('parent_process_elapsed_seconds')
    if type(elapsed) not in {int, float} or not 0 <= elapsed < 135:
        errors.append('invalid_parent_process_elapsed')
    missing_raw = False
    if observations:
        if not isinstance(observations[0].get('telemetry'), dict):
            errors.append('missing_observation_telemetry')
        else:
            telemetry = observations[0]['telemetry']
            for key, value in {'browser_fetches': 0, 'model_input_tokens': 0, 'jev_input_tokens': 0,
                               'search_calls': budget.get('search_queries'),
                               'http_fetches': budget.get('fetcher_calls')}.items():
                if type(telemetry.get(key)) is not int or telemetry[key] != value:
                    errors.append('wrong_telemetry:' + key)
            latency = telemetry.get('latency_seconds')
            if type(latency) not in {int, float} or not 0 <= latency <= 120:
                errors.append('invalid_telemetry_latency')
            if any(telemetry.get(k) is not None for k in ['document_reads', 'document_seconds', 'document_stop']):
                errors.append('unexpected_documents_phase')
        error = observations[0].get('error')
        bounded = error == 'BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED' and budget.get('stop_reason') == 'source_work_deadline_exhausted'
        if bounded and (type(budget.get('elapsed_ms')) is not int or budget['elapsed_ms'] < 116999):
            errors.append('early_claimed_source_deadline')
        page_capped = (error == 'RuntimeError: BENCHMARK_PAGE_BUDGET_EXHAUSTED'
                       and budget.get('stop_reason') == 'page_budget_exhausted'
                       and type(budget.get('fetcher_calls')) is int
                       and budget['fetcher_calls'] == 60)
        if budget.get('stop_reason') == 'page_budget_exhausted' and not page_capped:
            errors.append('inconsistent_page_cap_terminal')
        if error is not None and not (bounded or page_capped):
            errors.append('unavailable_observation')
        missing_raw = not (raw_root / (case + '.raw.json')).is_file()
        if missing_raw and (error is None or page_capped):
            errors.append('missing_completed_raw')
    try:
        checkpoint = read(raw_root / (case + '.budget.json'))
        observation_file = read(raw_root / (case + '.json'))
        if not isinstance(checkpoint, dict) or not checkpoint:
            errors.append('invalid_physical_budget')
        else:
            if not child_keys.issubset(checkpoint):
                errors.append('missing_physical_budget_fields')
            for key, value in checkpoint.items():
                if key not in budget or type(budget[key]) is not type(value) or budget[key] != value:
                    errors.append('physical_budget_mismatch:' + key)
            for key, value in {'strict_expert_budget': True, 'provider': 'exa_mcp',
                               'max_fetcher_calls': 60, 'max_search_queries': 6,
                               'max_active_seconds': 120, 'finalization_reserve_ms': 3000,
                               'source_work_deadline_ms': 117000}.items():
                if type(checkpoint.get(key)) is not type(value) or checkpoint.get(key) != value:
                    errors.append('physical_budget_config:' + key)
        if len(observations) == 1 and observation_file != observations[0]:
            errors.append('physical_observation_mismatch')
        if not missing_raw:
            raw = read(raw_root / (case + '.raw.json'))
            canary = raw.get('canary') if isinstance(raw, dict) else None
            if not isinstance(canary, dict) or not isinstance(raw.get('claims'), list):
                errors.append('invalid_raw_schema')
            else:
                institutions = canary.get('institutions')
                domain = {'groningen': 'rug.nl', 'delft': 'tudelft.nl', 'aalto': 'aalto.fi',
                          'vienna': 'univie.ac.at', 'warsaw': 'uw.edu.pl', 'ubc': 'ubc.ca',
                          'toronto': 'utoronto.ca', 'hku': 'hku.hk', 'ntu': 'ntu.edu.sg',
                          'kaist': 'kaist.ac.kr'}[case]
                if not isinstance(institutions, list) or len(institutions) != 1 or not isinstance(institutions[0], dict):
                    errors.append('invalid_raw_institutions')
                elif institutions[0].get('domain') != domain:
                    errors.append('wrong_raw_university')
                elif [str(HttpUrl(u)) for u in institutions[0].get('programs', [])] != observations[0].get('programme_urls'):
                    errors.append('raw_programmes_mismatch')
                if 'run_error' not in canary or not isinstance(canary.get('totals'), dict):
                    errors.append('raw_missing_terminal_report')
                elif (canary['run_error'] or None) != observations[0].get('error'):
                    errors.append('raw_terminal_error_mismatch')
                totals = canary.get('totals', {})
                meters = ['institutions', 'reached', 'blocked', 'program_pages_found',
                          'scholarship_pages_found', 'claims', 'false_positives',
                          'catalogs_walked', 'walker_programs_confirmed', 'source_pages_recorded']
                if not isinstance(totals, dict) or any(type(totals.get(k)) is not int or totals[k] < 0 for k in meters):
                    errors.append('invalid_raw_terminal_meters')
                elif totals['institutions'] != 1:
                    errors.append('wrong_raw_terminal_institution_count')
                if not isinstance(totals, dict) or any(not isinstance(totals.get(k), dict) for k in ['page_outcomes', 'page_types', 'recall', 'fetch_tiers']):
                    errors.append('invalid_raw_terminal_maps')
                else:
                    tiers = totals['fetch_tiers']
                    if any(type(v) is not int or v < 0 for v in tiers.values()) or tiers.get('browser', 0) != 0:
                        errors.append('invalid_raw_fetch_tiers')
                if any(not isinstance(c, dict) or 'claim_type' not in c or 'source_url' not in c for c in raw['claims']):
                    errors.append('invalid_raw_claims')
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        errors.append('physical_evidence_unavailable_or_malformed')
    snapshot = PREPARED / 'source/backend/evaluation/research'
    if cfg.get('harness_sha256') != digest(snapshot / 'live.py'):
        errors.append('wrong_harness_sha256')
    if cfg.get('mapping_sha256') != digest(snapshot / 'mapping.py'):
        errors.append('wrong_mapping_sha256')
    return {'errors': errors, 'bounded_timeout_without_full_raw': missing_raw and not errors,
            'bounded_page_cap_with_full_raw': bool(observations and page_capped and not errors),
            'fetcher_calls': budget.get('fetcher_calls'), 'search_queries': budget.get('search_queries'),
            'elapsed_ms': budget.get('elapsed_ms'), 'quality_status': 'UNSCORED'}

def validate(capture, case, raw_root):
    try:
        return _validate(capture, case, raw_root)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, IndexError) as error:
        return {'errors': ['malformed_evidence:' + type(error).__name__], 'quality_status': 'UNSCORED'}

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
    prior = read(PRIOR_RECEIPT)
    assert prior['revalidated_cases'] == ['groningen', 'delft', 'aalto', 'vienna', 'warsaw', 'ubc', 'toronto']
    assert prior['remaining_cases'] == list(CASES)
    assert all(not item['errors'] for item in prior['case_results'])
    assert all(digest(PRIOR / n) == h for n, h in prior['immutable_files'].items())
    assert prior['quality_status'] == 'UNSCORED' and prior['network_actions'] == 0
    commands = []
    for case in CASES:
        command = list(prepared['live_plan']['command'])
        command[command.index('--case') + 1] = case
        command[command.index('--out') + 1] = str(OWNED / 'execution' / case / 'capture')
        command += ['--stop-file', str(PROVIDER_STOP), '--finalization-reserve-ms', '3000']
        commands.append({'case': case, 'argv': command, 'cwd': str(snapshot / 'backend')})
    plan = {'kind': 'NEW remaining-only three cases after offline bounded-page-cap protocol repair'
            , 'prior_revalidation_sha256': digest(PRIOR_RECEIPT),
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
            if runner.git(REPO, 'rev-parse', 'HEAD') != EXPECTED_HEAD or runner.git(REPO, 'status', '--porcelain=v1') or not all(digest(snapshot / n) == h for n, h in files.items()):
                result = {'case': item['case'], 'errors': ['source_changed_before_case'], 'executed': False}
                run.summary['case_results'].append(result)
                run.summary['remaining_cases'] = list(CASES[index:])
                write_new(OWNED / 'protocol-stop.json', result)
                run.finish('PROTOCOL_STOP_UNSCORED')
                return
            code = run.step('case-' + item['case'], item['argv'], Path(item['cwd']))
            paths = list((execution / item['case'] / 'capture').glob('*/capture.json'))
            result = {'case': item['case'], 'exit_code': code}
            # Source ledger normally writes this sentinel itself. Preserve a
            # global refusal even if that write was absent, using only explicit
            # vendor failure fields, never a university HTTP failure.
            for budget_path in (execution / item['case'] / 'capture').glob('*/' + item['case'] + '.budget.json'):
                try:
                    failure = read(budget_path)
                    if isinstance(failure, dict) and (failure.get('provider_failure') is not None or
                            failure.get('stop_reason') in {'http_429', 'provider_failure', 'external_provider_failure'}):
                        if not PROVIDER_STOP.exists():
                            write_new(PROVIDER_STOP, {'kind': 'global fresh-local provider refusal',
                                      'case': item['case'], 'raw_budget_path': str(budget_path),
                                      'provider_failure': failure.get('provider_failure'),
                                      'stop_reason': failure.get('stop_reason')})
                except (OSError, ValueError, TypeError):
                    pass  # Malformed evidence becomes protocol STOP below.
            if len(paths) == 1:
                try:
                    result.update(capture_path=str(paths[0]), **validate(read(paths[0]), item['case'], paths[0].parent))
                except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
                    result['errors'] = ['malformed_capture:' + type(error).__name__]
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
        run.finish('THREE_REMAINING_CASES_CAPTURED_UNSCORED')

if __name__ == '__main__':
    main()

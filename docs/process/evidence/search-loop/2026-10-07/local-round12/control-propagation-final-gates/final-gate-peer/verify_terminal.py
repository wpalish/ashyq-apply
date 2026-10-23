from pathlib import Path
import collections
import datetime as dt
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET

OWN = Path(__file__).resolve().parent
PLAN = json.loads((OWN / 'PLAN.json').read_text())
BASE = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = BASE / 'work/ashyq-apply'
RUN = Path(PLAN['run'])
PREV = Path(PLAN['original_baseline_run'])
ROOT = BASE / 'work/local-round12/root-control-propagation'
SEED = BASE / 'work/local-round12/b-control-propagation-demo-seed'
STOP = BASE / 'work/local-round7/provider-STOP.json'
CHECKS = []

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def save(path, value):
    assert not path.exists(), str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def check(name, condition, detail):
    CHECKS.append({'check': name, 'status': 'PASS' if condition else 'RED', 'detail': detail})

def rows(path):
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    ids = [(t.attrib['classname'], t.attrib['name']) for t in cases]
    bad = [(t.attrib['classname'], t.attrib['name'], c.tag) for t in cases for c in t if c.tag in ('failure', 'error', 'skipped')]
    return {'root': root, 'cases': cases, 'ids': ids, 'unique': set(ids), 'bad': bad}

# Inputs pinned before any prototype execution.
input_mismatches = {p: sha(Path(p)) for p, expected in PLAN['input_pins'].items() if sha(Path(p)) != expected}
check('writeahead_input_pins', not input_mismatches, input_mismatches)
summary = read(RUN / 'summary.json')
manifest = read(RUN / 'source-manifest.json')
selected = read(ROOT / 'source-after-999.json')
expected = selected['file_sha256']
seed_map = read(SEED / 'candidate-app-pins.json')
seed_ready = read(SEED / 'ready-manifest.json')
seed_receipt = read(SEED / 'receipt.json')
seed_inspection = read(SEED / 'inspection.original.json')
seed_commands = read(SEED / 'commands.original.json')
stop_before = sha(STOP)
source_pre = {p: {'snapshot': sha(RUN / 'source' / p), 'current': sha(REPO / p), 'manifest': manifest['files'].get(p), 'root': h} for p, h in expected.items()}

check('terminal_full_summary', summary.get('status') == 'passed' and summary.get('suite') == 'full' and bool(summary.get('finished_at')), {k: summary.get(k) for k in ('status', 'suite', 'started_at', 'finished_at')})
step_names = ['ruff', 'ruff-format', 'mypy', 'backend-sqlite', 'frontend-typecheck', 'frontend-lint', 'frontend-tests', 'frontend-build', 'backend-postgresql', 'e2e', 'e2e-auth', 'pip-audit', 'npm-audit']
steps = summary['steps']
check('thirteen_distinct_steps_exit0', len(steps) == 13 and [s['name'] for s in steps] == step_names and all(type(s['exit_code']) is int and s['exit_code'] == 0 for s in steps), [{'name': s['name'], 'exit_code': s['exit_code'], 'seconds': s['seconds']} for s in steps])
check('physical_step_provenance', all(Path(s['log']) == RUN / (s['name'] + '.log') and Path(s['log']).is_file() and str(Path(s['cwd'])).startswith(str(RUN / 'source') + '/') for s in steps), 'All thirteen logs and working directories belong to this physical frozen run.')
check('local_only_summary_scope', summary.get('github_actions_started') is False and summary.get('live_network_capture_started') is False and summary.get('includes_container_gates') is False, 'No hosted/container/live capture is asserted by this package run.')
check('frozen_source_manifest_identity', sha(RUN / 'source-manifest.json') == PLAN['expected_manifest_sha256'] and manifest['source_head'] == PLAN['expected_run_head'] and manifest['source_tree_sha256'] == PLAN['expected_snapshot_tree_sha256'] and manifest['source_status'] == '' and Path(manifest['snapshot']) == RUN / 'source', {'manifest_sha256': sha(RUN / 'source-manifest.json'), 'head': manifest['source_head'], 'tree_sha256': manifest['source_tree_sha256'], 'source_status': manifest['source_status']})
check('selected999_physical_current_manifest_root', len(expected) == 999 and selected['count'] == 999 and all(len(set(x.values())) == 1 for x in source_pre.values()), {'selected': len(expected), 'mismatches': {p: x for p, x in source_pre.items() if len(set(x.values())) != 1}})
check('accepted_exact_three_source_test_bytes', all(expected.get(p) == h and source_pre[p]['current'] == h for p, h in PLAN['accepted_three_sha256'].items()) and set(selected['changed_paths']) == set(PLAN['accepted_three_sha256']), PLAN['accepted_three_sha256'])
old_manifest = read(PREV / 'source-manifest.json')
check('prior_full_source_manifest_pin', sha(PREV / 'source-manifest.json') == 'ec39dc311865d2cbfbff5f55c1ae85838a71bd24c6db482df268e6a282d6e8f8', sha(PREV / 'source-manifest.json'))
old_source_missing = [p for p in expected if p not in old_manifest['files']]
old_source_delta = [p for p, h in expected.items() if old_manifest['files'].get(p) != h]
check('only_three_selected_delta_from4312_full', not old_source_missing and set(old_source_delta) == set(PLAN['accepted_three_sha256']), {'missing': old_source_missing, 'changed': old_source_delta, 'unchanged': len(expected) - len(old_source_delta)})

sqlite = rows(RUN / 'backend-sqlite.xml')
pg = rows(RUN / 'backend-postgresql.xml')
old_sqlite = rows(PREV / 'backend-sqlite.xml')
old_pg = rows(PREV / 'backend-postgresql.xml')
check('baseline_xml_sha256', all(sha(PREV / p) == h for p, h in PLAN['baseline_xml_expected'].items()), {p: sha(PREV / p) for p in PLAN['baseline_xml_expected']})
for label, data in [('SQLite', sqlite), ('PostgreSQL', pg)]:
    check(label + '_4330_unique_no_bad', len(data['cases']) == len(data['unique']) == 4330 and not data['bad'], {'case_count': len(data['cases']), 'unique_count': len(data['unique']), 'bad': data['bad']})
    suites = list(data['root'].iter('testsuite'))
    check(label + '_junit_declared_counts', sum(int(s.get('tests', 0)) for s in suites) == 4330 and all(int(s.get(key, 0)) == 0 for s in suites for key in ('failures', 'errors', 'skipped')), [dict(s.attrib) for s in suites])
check('bothDB_exact_case_identity_sets', sqlite['unique'] == pg['unique'], {'SQLite_only': sorted(sqlite['unique'] - pg['unique']), 'PostgreSQL_only': sorted(pg['unique'] - sqlite['unique'])})
check('old4312_equal_and_all_retained', len(old_sqlite['unique']) == len(old_pg['unique']) == 4312 and old_sqlite['unique'] == old_pg['unique'] and old_sqlite['unique'] <= sqlite['unique'] and not old_sqlite['bad'] and not old_pg['bad'], {'old_count': len(old_sqlite['unique']), 'missing': sorted(old_sqlite['unique'] - sqlite['unique'])})
signals = ['async-cancelled', 'checkpoint-busy', 'future-read-reason', 'lease-lost', 'read-cap', 'run-cancelled']
expected_added = {('tests.test_hybrid_retrieval', f'test_native_entry_root_control_stops_before_second_get[{signal}]') for signal in signals}
expected_added |= {('tests.test_search_layer_budget_fixes', f'test_native_live_search_caller_preserves_get_control[{signal}-{field}]') for signal in signals for field in ('single-field', 'multi-field')}
added = sqlite['unique'] - old_sqlite['unique']
check('exact_eighteen_candidate_native_additions', added == expected_added and len(added) == 18, sorted(added))
modules = ['tests.test_hybrid_retrieval', 'tests.test_search_layer_budget_fixes']
belongs = lambda classname: any(classname == m or classname.startswith(m + '.') for m in modules)
focused = {x for x in sqlite['unique'] if belongs(x[0])}
old_focused = {x for x in old_sqlite['unique'] if belongs(x[0])}
check('native_twofiles99_old81_plus18', len(focused) == 99 and len(old_focused) == 81 and focused == old_focused | expected_added and not [b for b in sqlite['bad'] if belongs(b[0])] and not [b for b in pg['bad'] if belongs(b[0])], {'focused_cases': len(focused), 'old_cases': len(old_focused), 'module_and_nested_class_counts': dict(collections.Counter(x[0] for x in focused))})
save(OWN / 'backend-identities.json', {'identity_key': ['actual JUnit classname preserving nested classes', 'parameterized test name'], 'SQLite': sorted(sqlite['unique']), 'PostgreSQL': sorted(pg['unique']), 'old4312': sorted(old_sqlite['unique']), 'added18': sorted(added), 'focused99': sorted(focused)})

logs = {s['name']: Path(s['log']).read_text(errors='replace') for s in steps}
check('backend_raw_counts_and_coverage', bool(re.search(r'4330 passed, 2 warnings', logs['backend-sqlite'])) and bool(re.search(r'4330 passed, 2 warnings', logs['backend-postgresql'])) and 'Total coverage: 95.26%' in logs['backend-sqlite'] and 'Required test coverage of 92% reached' in logs['backend-sqlite'], {'SQLite_tail': logs['backend-sqlite'][-350:], 'PostgreSQL_tail': logs['backend-postgresql'][-150:]})
check('static_raw_success', 'All checks passed!' in logs['ruff'] and '383 files already formatted' in logs['ruff-format'] and 'Success: no issues found in 383 source files' in logs['mypy'], {'ruff': logs['ruff'].strip(), 'format': logs['ruff-format'].strip(), 'mypy_final': logs['mypy'].strip().splitlines()[-1], 'unchecked_body_notes': logs['mypy'].count('[annotation-unchecked]')})
check('frontend232_and28files_raw', bool(re.search(r'Test Files\s+28 passed \(28\)', logs['frontend-tests'])) and bool(re.search(r'Tests\s+232 passed \(232\)', logs['frontend-tests'])), 'Actual Vitest final summary; stderr from negative UI controls is retained, not assumed empty.')
check('frontend_type_lint_build_raw', 'tsc --noEmit' in logs['frontend-typecheck'] and 'eslint src e2e' in logs['frontend-lint'] and bool(re.search(r'✓ built in [0-9.]+s', logs['frontend-build'])), 'Terminal step exit0 plus actual command/output for all three.')
check('demo_e2e79pass1skip_raw', bool(re.search(r'\n\s*1 skipped\s*\n\s*79 passed', logs['e2e'])), logs['e2e'][-75:])
check('auth_e2e6pass_raw', bool(re.search(r'\n\s*6 passed \(', logs['e2e-auth'])), logs['e2e-auth'][-65:])
check('dependency_audits_actual_raw', 'No known vulnerabilities found' in logs['pip-audit'] and 'found 0 vulnerabilities' in logs['npm-audit'], {'pip': logs['pip-audit'].strip(), 'npm': logs['npm-audit'].strip()})

seed_errors = []
for name, record in seed_ready['files'].items():
    path = SEED / name
    if path.stat().st_size != record['bytes'] or sha(path) != record['sha256']:
        seed_errors.append(name)
check('prior_seed286_immutable_packet', len(seed_ready['files']) == 286 and sum(r['bytes'] for r in seed_ready['files'].values()) == 2894906 and not seed_errors and sha(SEED / 'receipt.json') == seed_ready['receipt_sha256'], {'selected_files': len(seed_ready['files']), 'selected_bytes': sum(r['bytes'] for r in seed_ready['files'].values()), 'mismatches': seed_errors})
seed_binding_mismatches = {p: {'seed': h, 'root': expected.get(p), 'current': source_pre.get(p, {}).get('current'), 'snapshot': source_pre.get(p, {}).get('snapshot')} for p, h in seed_map.items() if expected.get(p) != h or source_pre.get(p, {}).get('current') != h or source_pre.get(p, {}).get('snapshot') != h}
check('prior_seed_app242_exact_final_binding', len(seed_map) == 242 and not seed_binding_mismatches and sha(SEED / 'candidate-app-pins.json') == 'b4ef4c7cc470231164a4b47bef12070e5248077cc7e4c4e53c0d9b1c484ed73e', {'app_files': len(seed_map), 'mismatches': seed_binding_mismatches})
check('synthetic_demo_order_and_cost_bucket_raw', seed_inspection['heads'] == seed_inspection['database_revisions'] == ['d8e412c6a901'] and seed_inspection['rows'] == 20 and seed_inspection['first'] == 'University of Groningen' and seed_inspection['UBC']['funding_classification'] == 'FULL_TUITION' and seed_inspection['UBC']['portfolio_bucket'] == 'OUT_OF_BUDGET' and seed_inspection['all_undecided_no_approve'] is True and all(c['exit_code'] == 0 for c in seed_commands) and len(seed_commands) == 4 and seed_receipt['network_attempts'] == 0, seed_inspection)

# Copy only already pinned review inputs/public logs, and recheck originals afterwards.
copy_inputs = {}
for p in [RUN / 'summary.json', RUN / 'source-manifest.json', RUN / 'backend-sqlite.xml', RUN / 'backend-postgresql.xml'] + [Path(s['log']) for s in steps]:
    copy_inputs['raw/' + p.name] = p
for name in ['source-after-999.json', 'source-integration.json']:
    copy_inputs['root/' + name] = ROOT / name
for p in PLAN['accepted_three_sha256']:
    copy_inputs['accepted/' + p] = REPO / p
for name in ['inspection.original.json', 'commands.original.json', 'heads.raw.log', 'seed.raw.log', 'inspect.raw.log', 'candidate-app-pins.json', 'receipt.json', 'ready-manifest.json']:
    copy_inputs['seed/' + name] = SEED / name
copy_inputs['STOP.original.json'] = STOP
before = {str(p): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in copy_inputs.values()}
for dest, source in copy_inputs.items():
    target = OWN / dest
    assert not target.exists(), str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
after = {str(p): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in copy_inputs.values()}
copy_errors = [dest for dest, source in copy_inputs.items() if sha(OWN / dest) != before[str(source)]['sha256']]
check('raw_copies_exact_and_sources_pre_post', before == after and not copy_errors, {'original_paths': len(before), 'copy_mismatches': copy_errors})
source_post = {p: {'snapshot': sha(RUN / 'source' / p), 'current': sha(REPO / p), 'manifest': manifest['files'].get(p), 'root': h} for p, h in expected.items()}
check('selected999_source_pre_post_immutable', source_pre == source_post, {'selected': len(source_post), 'changed': [p for p in source_pre if source_pre[p] != source_post[p]]})
check('input_pins_post_immutable', all(sha(Path(p)) == h for p, h in PLAN['input_pins'].items()), 'All original writeahead input pins still exact.')
check('global_provider_STOP_pre_post_immutable', stop_before == sha(STOP) == PLAN['expected_stop_sha256'] and selected['STOP_sha256'] == stop_before, {'before': stop_before, 'after': sha(STOP), 'no_resumed_live': True})
save(OWN / 'source999.pre-post.json', {'selected_count': 999, 'pre': source_pre, 'post': source_post, 'only_three_previous_full_delta': old_source_delta})
save(OWN / 'raw-origin-manifest.json', {'before': before, 'after': after, 'copies': {dest: str(p) for dest, p in copy_inputs.items()}})
save(OWN / 'checks.json', CHECKS)
wall_seconds = (dt.datetime.fromisoformat(summary['finished_at']) - dt.datetime.fromisoformat(summary['started_at'])).total_seconds()
receipt = {'status': 'ACCEPT_EXACT_LOCAL_FULL_AND_SYNTHETIC_SEED_BINDING' if all(c['status'] == 'PASS' for c in CHECKS) else 'RED_SAVED_EVIDENCE_REVIEW', 'created_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'plan_sha256': sha(OWN / 'PLAN.json'), 'check_counts': dict(collections.Counter(c['status'] for c in CHECKS)), 'run': str(RUN), 'summary_sha256': sha(RUN / 'summary.json'), 'source_manifest_sha256': sha(RUN / 'source-manifest.json'), 'frozen_head': manifest['source_head'], 'snapshot_tree_sha256': manifest['source_tree_sha256'], 'source_selected999_equal': all(len(set(x.values())) == 1 for x in source_pre.values()), 'local_full_steps': 13, 'wall_seconds': wall_seconds, 'backend_each_db_unique_cases': len(sqlite['unique']), 'old4312_retained': old_sqlite['unique'] <= sqlite['unique'], 'exact_new_cases': len(added), 'native_twofile_cases_included_in_full': len(focused), 'coverage_percent': 95.26, 'backend_warnings_each': 2, 'frontend_tests': 232, 'demo_e2e': {'passed': 79, 'skipped': 1}, 'auth_e2e_passed': 6, 'prior_synthetic_seed_exact_app_binding': len(seed_map), 'STOP_sha256': stop_before, 'review_execution': 'stdlib saved-file parsing/hashing/copying only; no app/test imports, test reruns, primary mutations, network/provider/model/gold/scoring', 'limits': PLAN['scope_limits'] + ['E2E has one skip; backend two warnings each; do not call all tests unconditionally executed.', 'These local gates validate a narrow exact-object propagation repair, not current DEV recall, source quality, global query telemetry, retention, hosted or production readiness.']}
save(OWN / 'receipt.json', receipt)
print(json.dumps({'status': receipt['status'], 'checks': receipt['check_counts'], 'receipt_sha256': sha(OWN / 'receipt.json'), 'wall_seconds': wall_seconds, 'failed_checks': [c for c in CHECKS if c['status'] != 'PASS']}, ensure_ascii=False, indent=2))

from pathlib import Path
import collections
import datetime as dt
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET

OWN = Path(__file__).resolve().parent
BASE = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = BASE / 'work/ashyq-apply'
ROOT = BASE / 'work/local-round13/root-stopped-trace-accounting'
PROP = BASE / 'work/local-round13/b-stopped-trace-proposal'
SEED = BASE / 'work/local-round13/b-stopped-trace-seed'
ARCHIVE = REPO / 'docs/process/evidence/search-loop/2026-10-07/local-round13/stopped-trace-full-raw'
PLAN = json.loads((OWN / 'PLAN.json').read_text())
APPLIED = json.loads((OWN / 'APPLIED-SOURCE-PLAN.json').read_text())
TERMINAL = json.loads((OWN / 'TERMINAL-REVIEW-PLAN.json').read_text())
RUN = Path(APPLIED['run'])
OLD = Path(PLAN['old_full_run'])
STOP = Path(PLAN['STOP']['path'])
CHECKS = []


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def record(p):
    return {'sha256': sha(p), 'bytes': p.stat().st_size}


def read(p):
    return json.loads(p.read_text())


def save(p, value):
    assert not p.exists(), str(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def check(name, condition, detail):
    CHECKS.append({'check': name, 'status': 'PASS' if condition else 'RED', 'detail': detail})


def rows(p):
    root = ET.parse(p).getroot()
    cases = list(root.iter('testcase'))
    ids = [(c.attrib['classname'], c.attrib['name']) for c in cases]
    bad = [(c.attrib['classname'], c.attrib['name'], x.tag) for c in cases for x in c if x.tag in ('failure', 'error', 'skipped')]
    return {'root': root, 'cases': cases, 'ids': ids, 'unique': set(ids), 'bad': bad}


input_pins = dict(TERMINAL['input_pins']) | dict(PLAN['old_full_pins'])
input_pins[PLAN['source999_before_map']] = PLAN['source999_before_sha256']
input_pins[str(OWN / 'PLAN.json')] = 'b35607670dea685d36eb07f9dd72d5021c52f8a3c03111520482e4a5488ef308'
input_pins[str(OWN / 'APPLIED-SOURCE-PLAN.json')] = 'f1e7e9f4e527fbcb5ed5e0a110379a5c49c21345a01309971fe5837c145d4885'
input_pins[str(OWN / 'TERMINAL-REVIEW-PLAN.json')] = '1832be5fe998d041c12988820cb45d042bc4161a41f21495c122493af04f6469'
input_pins[str(PROP / 'ready-manifest.json')] = PLAN['proposal_ready_sha256']
input_pins[str(SEED / 'ready-manifest.json')] = PLAN['seed_ready_sha256']
input_pins[str(SEED / 'candidate-app-pins.json')] = PLAN['seed_app242_sha256']
check('writeahead_and_terminal_original_input_pins', all(sha(Path(p)) == h for p, h in input_pins.items()), {p: sha(Path(p)) for p, h in input_pins.items() if sha(Path(p)) != h})
stop_pre = sha(STOP)
summary = read(RUN / 'summary.json')
manifest = read(RUN / 'source-manifest.json')
selected = read(ROOT / 'source-after-999.json')
expected = selected['file_sha256']
source_pre = {p: {'snapshot': sha(RUN / 'source' / p), 'current': sha(REPO / p), 'manifest': manifest['files'].get(p), 'root_after': h} for p, h in expected.items()}
pre_applied = read(OWN / 'source999.applied-pre.json')
check('terminal_full_summary', summary.get('status') == 'passed' and summary.get('suite') == 'full' and bool(summary.get('finished_at')), {k: summary.get(k) for k in ('status', 'suite', 'started_at', 'finished_at')})
steps = summary['steps']
step_names = ['ruff', 'ruff-format', 'mypy', 'backend-sqlite', 'frontend-typecheck', 'frontend-lint', 'frontend-tests', 'frontend-build', 'backend-postgresql', 'e2e', 'e2e-auth', 'pip-audit', 'npm-audit']
check('thirteen_distinct_steps_exit0', [s['name'] for s in steps] == step_names and len(steps) == 13 and all(type(s['exit_code']) is int and s['exit_code'] == 0 for s in steps), [{'name': s['name'], 'exit_code': s['exit_code'], 'seconds': s['seconds']} for s in steps])
check('physical_step_logs_and_cwd', all(Path(s['log']) == RUN / (s['name'] + '.log') and Path(s['log']).is_file() and str(Path(s['cwd'])).startswith(str(RUN / 'source') + '/') for s in steps), 'Every actual step log and cwd belongs to the frozen run.')
check('local_only_summary', summary.get('github_actions_started') is False and summary.get('live_network_capture_started') is False and summary.get('includes_container_gates') is False, 'No hosted/container/live capture is claimed by this run.')
check('frozen_source_identity', manifest['source_head'] == APPLIED['frozen_head'] and manifest['source_tree_sha256'] == APPLIED['snapshot_tree_sha256'] and manifest['source_status'] == '' and Path(manifest['snapshot']) == RUN / 'source' and summary['source'] == manifest, {'head': manifest['source_head'], 'tree_sha256': manifest['source_tree_sha256'], 'manifest_file_sha256': sha(RUN / 'source-manifest.json'), 'summary_source_equals_manifest': summary['source'] == manifest})
check('source999_physical_current_snapshot_manifest_root_equal', len(expected) == 999 and all(len(set(x.values())) == 1 for x in source_pre.values()) and source_pre == pre_applied, {'selected': len(expected), 'mismatches': {p: x for p, x in source_pre.items() if len(set(x.values())) != 1}, 'pre_applied_changed': [p for p in source_pre if source_pre[p] != pre_applied.get(p)]})
check('exact_accepted_three_source_bytes', selected['changed_exact'] == PLAN['proposal_source3'] and all(record(REPO / p) == rec and record(RUN / 'source' / p) == rec for p, rec in PLAN['proposal_source3'].items()), PLAN['proposal_source3'])
old_manifest = read(OLD / 'source-manifest.json')
old_before = read(Path(PLAN['source999_before_map']))['file_sha256']
changed = sorted(p for p, h in expected.items() if old_manifest['files'].get(p) != h)
check('exact_three_changes_old_full_and999', set(old_before) == set(expected) and set(changed) == set(PLAN['proposal_source3']) and sorted(p for p, h in expected.items() if old_before[p] != h) == changed and selected['unchanged_other_paths'] == 996, {'changed': changed, 'unchanged': len(expected) - len(changed)})

originals = read(ROOT / 'full-originals-manifest.json')
raw_errors = [n for n, rec in originals['files'].items() if record(RUN / n) != rec]
required_raw = {'summary.json', 'source-manifest.json', 'backend-sqlite.xml', 'backend-postgresql.xml'} | {n + '.log' for n in step_names}
check('seventeen_raw_original_SHA_size', set(originals['files']) == required_raw and len(originals['files']) == originals['selected_files'] == 17 and sum(x['bytes'] for x in originals['files'].values()) == originals['selected_bytes'] == 5486328 and not raw_errors and originals['session_id'] == 17835 and originals['exit_code'] == 0 and originals['run'] == str(RUN), {'selected': len(originals['files']), 'bytes': sum(x['bytes'] for x in originals['files'].values()), 'mismatches': raw_errors})

sqlite = rows(RUN / 'backend-sqlite.xml')
pg = rows(RUN / 'backend-postgresql.xml')
old_sqlite = rows(OLD / 'backend-sqlite.xml')
old_pg = rows(OLD / 'backend-postgresql.xml')
expected_added = {tuple(x) for x in read(OWN / 'expected19-new-identities.json')}
old_saved = {tuple(x) for x in read(OWN / 'old4330-identities.json')}
check('old4330_actual_and_saved_identity_set', len(old_saved) == len(old_sqlite['cases']) == len(old_pg['cases']) == 4330 and old_sqlite['unique'] == old_pg['unique'] == old_saved and not old_sqlite['bad'] and not old_pg['bad'], {'old': len(old_saved), 'bad_sqlite': old_sqlite['bad'], 'bad_pg': old_pg['bad']})
check('expected19_writeahead_identity_set', len(expected_added) == 19 and expected_added == {tuple(x) for x in PLAN['expected_exact19_new_identities']}, sorted(expected_added))
for label, data in [('SQLite', sqlite), ('PostgreSQL', pg)]:
    check(label + '_4349_unique_no_failure_error_skip', len(data['cases']) == len(data['unique']) == 4349 and not data['bad'], {'actual': len(data['cases']), 'unique': len(data['unique']), 'bad': data['bad']})
    suites = list(data['root'].iter('testsuite'))
    check(label + '_declared_JUnit_counts', sum(int(s.get('tests', 0)) for s in suites) == 4349 and all(int(s.get(k, 0)) == 0 for s in suites for k in ('failures', 'errors', 'skipped')), [dict(s.attrib) for s in suites])
    check(label + '_old4330_and_exact19_delta', old_saved <= data['unique'] and data['unique'] - old_saved == expected_added, {'old_retained': len(old_saved & data['unique']), 'new': sorted(data['unique'] - old_saved), 'missing': sorted(old_saved - data['unique'])})
check('both_DB_exact_same_identity_set', sqlite['unique'] == pg['unique'], {'SQLite_only': sorted(sqlite['unique'] - pg['unique']), 'PG_only': sorted(pg['unique'] - sqlite['unique'])})
author_ready = read(PROP / 'ready-manifest.json')
check('author_native250_original_XML_pin', record(PROP / 'native.on.final.xml') == author_ready['files']['native.on.final.xml'], record(PROP / 'native.on.final.xml'))
author = rows(PROP / 'native.on.final.xml')
modules = ['tests.test_live_discovery', 'tests.test_university_catalogue', 'tests.test_identity_query_ledger']
belongs = lambda c: any(c == m or c.startswith(m + '.') for m in modules)
focus = {x for x in sqlite['unique'] if belongs(x[0])}
focus_old = {x for x in old_saved if belongs(x[0])}
pg_import = ('tests.test_university_catalogue', 'test_real_postgres_catalogue_import')
check('native_threefiles_full251_author250_plusPGimport', len(focus) == 251 and len(author['cases']) == len(author['unique']) == 250 and not author['bad'] and author['unique'] <= sqlite['unique'] and author['unique'] <= pg['unique'] and focus - author['unique'] == {pg_import} and len(focus_old) == 232 and focus == focus_old | expected_added, {'full_selected': len(focus), 'author_selected': len(author['unique']), 'old_selected': len(focus_old), 'additional': sorted(focus - author['unique']), 'module_nestedclass_counts': dict(collections.Counter(x[0] for x in focus))})
check('native_singleLive151_including_nestedclasses', sum(c == 'tests.test_live_discovery' or c.startswith('tests.test_live_discovery.') for c, _ in focus) == 151, 'Original PLAN called three-file250 a single file; original PLAN unchanged and correction stated before terminal verifier.')
save(OWN / 'backend-identities.json', {'key': ['actual JUnit classname preserving nested classes', 'parameterized test name'], 'SQLite': sorted(sqlite['unique']), 'PostgreSQL': sorted(pg['unique']), 'old4330': sorted(old_saved), 'new19': sorted(expected_added), 'native_threefiles251': sorted(focus), 'author250': sorted(author['unique'])})

logs = {s['name']: Path(s['log']).read_text(errors='replace') for s in steps}
check('backend_raw4349_32warnings_coverage9527', all(re.search(r'4349 passed, 32 warnings', logs[n]) for n in ('backend-sqlite', 'backend-postgresql')) and 'Total coverage: 95.27%' in logs['backend-sqlite'] and 'Required test coverage of 92% reached' in logs['backend-sqlite'], {'SQLite_tail': logs['backend-sqlite'][-190:], 'PG_tail': logs['backend-postgresql'][-120:]})
check('backend_warnings_parser30_plusbaseline2', all(logs[n].count('tests/test_live_discovery.py: 15 warnings') == 2 and all(k in logs[n] for k in ('MarkupResemblesLocatorWarning', 'XMLParsedAsHTMLWarning', 'StarletteDeprecationWarning', 'tests/test_documents_by_completion.py: 1 warning')) for n in ('backend-sqlite', 'backend-postgresql')), 'Actual raw warns twice15 synthetic parser warnings, baseline2 preserved; no zero-warning claim.')
check('static_raw_success', 'All checks passed!' in logs['ruff'] and '383 files already formatted' in logs['ruff-format'] and 'Success: no issues found in 383 source files' in logs['mypy'], {'ruff': logs['ruff'].strip(), 'format': logs['ruff-format'].strip(), 'mypy_final': logs['mypy'].strip().splitlines()[-1], 'unchecked_body_notes': logs['mypy'].count('[annotation-unchecked]')})
check('frontend232_28files_actualraw', bool(re.search(r'Test Files\s+28 passed \(28\)', logs['frontend-tests'])) and bool(re.search(r'Tests\s+232 passed \(232\)', logs['frontend-tests'])), 'Actual Vitest final summary. Negative UI test stderr retained.')
check('frontend_type_lint_build_actualraw', 'tsc --noEmit' in logs['frontend-typecheck'] and 'eslint src e2e' in logs['frontend-lint'] and bool(re.search(r'✓ built in [0-9.]+s', logs['frontend-build'])), 'Actual command/output plus terminal exit0.')
check('e2e79pass_oneviewportskip_actualraw', bool(re.search(r'\n\s*1 skipped\s*\n\s*79 passed', logs['e2e'])), logs['e2e'][-70:])
community = (RUN / 'source/frontend/e2e/community.spec.ts').read_text()
skip_line = [line for line in logs['e2e'].splitlines() if re.search(r'^\s*-\s+\d+\s+\[', line)]
check('E2E_skip_identity_and_frozen_source_condition', len(skip_line) == 1 and '[desktop-chromium]' in skip_line[0] and 'e2e/community.spec.ts:80:1' in skip_line[0] and 'every community screen is reachable on a phone' in skip_line[0] and "(page.viewportSize()?.width ?? 0) >= 900" in community and "the wrapped navigation only applies below 900px" in community, {'skipped_raw_line': skip_line, 'source_condition': 'desktop viewport width >=900; mobile scenario not claimed skipped'})
check('auth6_actualraw', bool(re.search(r'\n\s*6 passed \(', logs['e2e-auth'])), logs['e2e-auth'][-60:])
check('dependency_audits_actualraw', 'No known vulnerabilities found' in logs['pip-audit'] and 'found 0 vulnerabilities' in logs['npm-audit'], {'pip': logs['pip-audit'].strip(), 'npm': logs['npm-audit'].strip()})

seed_map = read(SEED / 'candidate-app-pins.json')
seed_inspection = read(SEED / 'inspection.original.json')
seed_receipt = read(SEED / 'receipt.json')
seed_commands = read(SEED / 'commands.original.json')
seed_ready = read(SEED / 'ready-manifest.json')
seed_pins = ['receipt.json', 'inspection.original.json', 'commands.original.json', 'candidate-app-pins.json', 'heads.raw.log', 'migrate.raw.log', 'seed.raw.log', 'inspect.raw.log']
check('prior_own_seed_selected_small_metadata_pins', all(record(SEED / n) == seed_ready['files'][n] for n in seed_pins) and sha(SEED / 'receipt.json') == seed_ready['receipt_sha256'], {n: record(SEED / n) for n in seed_pins})
seed_bad = {p: h for p, h in seed_map.items() if expected.get(p) != h or source_pre.get(p, {}).get('current') != h or source_pre.get(p, {}).get('snapshot') != h}
check('prior_synthetic_seed242_final_current_snapshot_binding', len(seed_map) == 242 and not seed_bad and sha(SEED / 'candidate-app-pins.json') == PLAN['seed_app242_sha256'], {'app_files': len(seed_map), 'mismatches': seed_bad})
check('carried_synthetic_order_and_singlehead_raw', seed_inspection['heads'] == seed_inspection['database_revisions'] == ['d8e412c6a901'] and seed_inspection['rows'] == 20 and seed_inspection['first'] == 'University of Groningen' and seed_inspection['UBC']['funding_classification'] == 'FULL_TUITION' and seed_inspection['UBC']['portfolio_bucket'] == 'OUT_OF_BUDGET' and seed_inspection['all_undecided_no_approve'] is True and len(seed_commands) == 4 and all(type(x['exit_code']) is int and x['exit_code'] == 0 for x in seed_commands) and seed_receipt['network_attempts'] == 0, seed_inspection)
wall_seconds = (dt.datetime.fromisoformat(summary['finished_at']) - dt.datetime.fromisoformat(summary['started_at'])).total_seconds()
root_verified = read(ROOT / 'final-full-verification.json')
check('root_terminal_verification_matches_independent_facts', root_verified['status'] == 'FRESH_FULL13_OF13_PASS_EXACT_SOURCE' and root_verified['head'] == manifest['source_head'] and root_verified['snapshot_sha256'] == manifest['source_tree_sha256'] and root_verified['source_manifest_file_sha256'] == sha(RUN / 'source-manifest.json') and root_verified['source_prefix_paths'] == 999 and root_verified['SQLite_unique'] == root_verified['PG_unique'] == len(sqlite['unique']) and root_verified['same_backend_identities'] is True and root_verified['old4330_preserved_eachDB'] is True and {tuple(x) for x in root_verified['new19_exact_author_identities_eachDB']} == expected_added and root_verified['SQLite_coverage_percent'] == 95.27 and root_verified['steps'] == steps and root_verified['full_elapsed_seconds'] == wall_seconds and root_verified['seed_app242_bound'] is True, {'full_elapsed_seconds': wall_seconds, 'root_verification_file_sha256': sha(ROOT / 'final-full-verification.json'), 'root_verifier_not_executed_by_peer': True})

archive_receipt = read(ARCHIVE / 'receipt.json')
archive_records = archive_receipt['file_sha256']
archive_errors = []
for n, rec in archive_records.items():
    target = ARCHIVE / n
    origin = Path(rec['original'])
    expected_rec = {k: rec[k] for k in ('sha256', 'bytes')}
    if record(target) != expected_rec or record(origin) != expected_rec:
        archive_errors.append(n)
archive_physical = {str(p.relative_to(ARCHIVE)) for p in ARCHIVE.rglob('*') if p.is_file()}
check('root_archive25_receipt_member_origin_SHA_size', sha(ARCHIVE / 'receipt.json') == TERMINAL['archive_expected_receipt_sha256'] and len(archive_records) == archive_receipt['selected_files'] == 25 and sum(x['bytes'] for x in archive_records.values()) == archive_receipt['selected_bytes'] == 5646969 and not archive_errors and archive_physical == set(archive_records) | {'receipt.json'}, {'receipt_sha256': sha(ARCHIVE / 'receipt.json'), 'selected': len(archive_records), 'bytes': sum(x['bytes'] for x in archive_records.values()), 'physical_including_receipt': len(archive_physical), 'mismatches': archive_errors})
check('root_archive_full17_matches_native_original_manifest', all(archive_records.get('parent/full/' + n) == rec | {'original': str(RUN / n)} for n, rec in originals['files'].items()) and len([n for n in archive_records if n.startswith('parent/full/')]) == 17 and archive_receipt['source_prefix_selected_paths_matched'] == 999 and archive_receipt['STOP_sha256'] == stop_pre, 'Exactly the17 completed full originals;8root bindings. Archive receipts/scripts are data only, never executed.')
save(OWN / 'root-raw-archive-binding.json', {'receipt_sha256': sha(ARCHIVE / 'receipt.json'), 'archive': str(ARCHIVE), 'selected25': archive_records, 'selected_bytes': 5646969, 'physical26_including_receipt': sorted(archive_physical), 'all_member_and_original_hash_sizes_equal': not archive_errors})

copies = {'raw/' + n: RUN / n for n in originals['files']}
for n in ['source-after-999.json', 'source-integration.json', 'seed-primary-binding.json', 'final-full-verification.json', 'full-originals-manifest.json']:
    copies['root/' + n] = ROOT / n
copies['root-archive/receipt.original.json'] = ARCHIVE / 'receipt.json'
for n in seed_pins + ['ready-manifest.json']:
    copies['seed/' + n] = SEED / n
copies['STOP.original.json'] = STOP
origins_pre = {str(p): record(p) for p in copies.values()}
for name, p in copies.items():
    dest = OWN / name
    assert not dest.exists(), str(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
origins_post = {str(p): record(p) for p in copies.values()}
copy_errors = [n for n, p in copies.items() if record(OWN / n) != origins_pre[str(p)]]
check('raw_metadata_copies_exact_originals_prepost', origins_pre == origins_post and not copy_errors, {'copied_paths': len(copies), 'mismatches': copy_errors})
source_post = {p: {'snapshot': sha(RUN / 'source' / p), 'current': sha(REPO / p), 'manifest': manifest['files'].get(p), 'root_after': h} for p, h in expected.items()}
check('selected999_final_source_prepost', source_pre == source_post, {'selected': len(source_post), 'changed': [p for p in source_pre if source_pre[p] != source_post[p]]})
check('all_original_input_pins_post', all(sha(Path(p)) == h for p, h in input_pins.items()), 'All earlier source/summary/plan/XML/proposal/seed/terminal/archive receipt pins still exact.')
check('global_provider_STOP_prepost', stop_pre == sha(STOP) == PLAN['STOP']['sha256'] and selected['STOP_sha256'] == root_verified['STOP_sha256'] == archive_receipt['STOP_sha256'] == stop_pre, {'before': stop_pre, 'after': sha(STOP), 'no_live_resumption': True})
save(OWN / 'source999.pre-post.json', {'selected_count': len(expected), 'pre': source_pre, 'post': source_post, 'exact_three_changes_old_full': changed})
save(OWN / 'raw-origin-manifest.json', {'before': origins_pre, 'after': origins_post, 'copies': {n: str(p) for n, p in copies.items()}})
save(OWN / 'checks.json', CHECKS)
receipt = {'status': 'ACCEPT_EXACT_LOCAL_FULL_SOURCE_SEED_AND_RAW_ARCHIVE_BINDING' if all(x['status'] == 'PASS' for x in CHECKS) else 'RED_SAVED_EVIDENCE_REVIEW', 'time': dt.datetime.now(dt.timezone.utc).isoformat(), 'writeahead_plan_sha256': sha(OWN / 'PLAN.json'), 'applied_source_plan_sha256': sha(OWN / 'APPLIED-SOURCE-PLAN.json'), 'terminal_plan_sha256': sha(OWN / 'TERMINAL-REVIEW-PLAN.json'), 'check_counts': dict(collections.Counter(x['status'] for x in CHECKS)), 'run': str(RUN), 'summary_sha256': sha(RUN / 'summary.json'), 'source_manifest_file_sha256': sha(RUN / 'source-manifest.json'), 'frozen_head': manifest['source_head'], 'snapshot_tree_sha256': manifest['source_tree_sha256'], 'local_full_steps': len(steps), 'elapsed_seconds': wall_seconds, 'backend_eachDB_unique_cases': len(sqlite['unique']), 'old4330_preserved': old_saved <= sqlite['unique'], 'exact19_new_native': len(expected_added), 'native_threefiles_in_full': len(focus), 'native_author250_in_full_plus_pgimport': True, 'singleLive_file_cases_in_full': 151, 'coverage_percent': 95.27, 'backend_warnings_each': 32, 'frontend_tests': 232, 'demo_e2e': {'passed': 79, 'skipped': 1, 'skip': skip_line}, 'auth_e2e_passed': 6, 'source999_equal': all(len(set(x.values())) == 1 for x in source_pre.values()), 'prior_synthetic_seed_app242_bound': len(seed_map), 'raw_originals17_bytes': 5486328, 'root_raw_archive': {'receipt_sha256': sha(ARCHIVE / 'receipt.json'), 'selected_files': 25, 'selected_bytes': 5646969, 'physical_including_receipt': 26}, 'STOP_sha256': stop_pre, 'review_execution': 'stdlib saved-file parsing/hashing/copying only; no app/test imports or execution, source/Git/DB/STOP writes, live/provider/model/DNS/HTTP/gold/labels/scorer', 'qualifications': ['Native controls, copied evidence counts and synthetic seed are not university quality/recall or unique paid experiments.', 'No hosted/container/production journey, new live quality, SQL durable query accounting or historical cancellation-retention proof.', '32warnings each DB include30 new synthetic parser and baseline2; mypy unchecked-body notes remain.', 'E2E79passed1desktop viewport skip; do not call every configured E2E executed.', 'Original PLAN singlefile250 label retained immutably and corrected by terminal writeahead: author threefiles250; actual fullthree251 incl oldPGimport; singleLive151.', 'Prior author setup/fixture histories and one excluded PG test remain preserved; actual fresh full includes that PG identity passing.', 'Seed was carried forward by exact242 app binding; no new seed/full/test execution by this verifier.']}
save(OWN / 'receipt.json', receipt)
print(json.dumps({'status': receipt['status'], 'checks': receipt['check_counts'], 'receipt_sha256': sha(OWN / 'receipt.json'), 'elapsed_seconds': wall_seconds, 'red': [x for x in CHECKS if x['status'] != 'PASS']}, ensure_ascii=False, indent=2))
raise SystemExit(0 if all(x['status'] == 'PASS' for x in CHECKS) else 1)

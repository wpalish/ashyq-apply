"""Finite stdlib saved-byte review. Does not import/execute app, tests or runners."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import traceback
import xml.etree.ElementTree as ET

OWN = Path(__file__).resolve().parent
BASE = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
ROUND = BASE / 'work/local-round15'
REPO = BASE / 'work/ashyq-apply'
RUN = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T085213Z-check-97246db0')
RAW = ROUND / 'root-orchestrator/corrected-full-raw'
STOP = BASE / 'work/local-round7/provider-STOP.json'
HEAD = 'eb81c127c8a2a5154dd0d6f7ac115d8dc4464288'
TREE = '3da2152c711107623edd78f1e9f2cf41c36a58415df1bdc90494d63a0fc2ef84'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
SIX = {
 'backend/evaluation/research/expert/controller.py': 'aefe7e1f883e1a70449cfa4add659649b7c6108162c40c0efeb091097167fc09',
 'backend/evaluation/research/expert/models.py': '52039924cd1d0e1806ecb03fdb16a2dc8cb7567ca0c5e9502226d75077eb501e',
 'backend/evaluation/research/expert/selector.py': 'd9cbefb4780648a8cd0ee91708202db5e2f9dc87997f282c3b6717d7f6ca0af1',
 'backend/evaluation/research/local_pilot.py': 'c7ddc2c68ef6b149e84308ad3016bb75a9087bc1099324558acabc4a85d20d10',
 'backend/evaluation/research/pilot_admission.py': 'ea4ff281ad038b2321bc9851c0d6f7c7d7704603d79a5ff2ec4c5534f4a55bca',
 'backend/tests/test_local_pilot.py': '1cf361de7f01b0974682e93acd4241d66bdfc0af10193fe24ae9a75b1aa6bcda',
}
NEW_NAMES = '''test_legacy_default_raw_output_shape test_null_unknown_crossmode_and_types_fail_closed test_tool_over120_and_resume_original_wall test_read60_query6_no_extra_dispatch test_resume_legacy_to_wall_rejected test_selector_wall_remaining_and_legacy55 test_owned_process_timeout_kills_own_group test_prepare_only_and_exact_owner_grant test_public_profile_scope_canonical_closed test_neutral_completed_and_honest_partial test_algorithm_exit0_refusal_global_stop test_algorithm_wrong_identity_stops_before_expert test_isolation_failure_partial_receipt_zero_dispatch test_complete_adaptive10_plus20_not_runtime_admitted test_zero_source_submit_partial_not_unrun test_failed_later_model_preserves_journal_and_raw test_protective_wall_includes_thinking_no_reset test_stale_delta_cannot_replace_latest_journal test_prepare_real_shaped_homepage_and_opaque_bindings test_complete_citation_chain_and_mutation_closure'''.split()
OLD_NODE = ('tests.test_expert_catalogue_trace', 'test_complete_findings_are_unreviewed_and_match_the_saved_source')

def meta(path):
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

def load(path):
    return json.loads(path.read_text())

def write(name, value):
    (OWN / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def sealed(folder, expected):
    path = folder / 'ready-manifest.json'
    assert meta(path)['sha256'] == expected, str(path)
    packet = load(path)
    for name, stamp in packet['files'].items():
        assert meta(folder / name) == stamp, str(folder / name)
    return packet

def cases(path):
    elements = list(ET.parse(path).iter('testcase'))
    keys = [(x.attrib['classname'], x.attrib['name']) for x in elements]
    assert len(keys) == len(set(keys)), str(path)
    outcomes = {k: [y.tag for y in x if y.tag in {'failure', 'error', 'skipped'}] for k, x in zip(keys, elements)}
    return set(keys), outcomes

def run_review():
    stop_pre = meta(STOP)
    assert stop_pre == {'sha256': STOP_SHA, 'bytes': 142}
    root_packet = sealed(RAW, '82e4dd6f325424f054ca3d521bb9d14e133ec71269224552a15c4965abea9e33')
    originals = root_packet['files']
    assert len(originals) == 17 and sum(v['bytes'] for v in originals.values()) == 5697217
    for name, stamp in originals.items():
        assert meta(RUN / name) == stamp, 'original/copy mismatch: ' + name
    raw_pre = {name: meta(RUN / name) for name in originals}
    summary = load(RUN / 'summary.json')
    source = load(RUN / 'source-manifest.json')
    assert summary['source'] == source
    assert summary['status'] == 'passed' and summary['suite'] == 'full'
    for key in ('github_actions_started', 'live_network_capture_started', 'includes_container_gates'):
        assert summary[key] is False
    step_names = ['ruff', 'ruff-format', 'mypy', 'backend-sqlite', 'frontend-typecheck', 'frontend-lint', 'frontend-tests', 'frontend-build', 'backend-postgresql', 'e2e', 'e2e-auth', 'pip-audit', 'npm-audit']
    assert [x['name'] for x in summary['steps']] == step_names
    assert all(type(x['exit_code']) is int and x['exit_code'] == 0 for x in summary['steps'])
    for step in summary['steps']:
        assert Path(step['log']) == RUN / (step['name'] + '.log')
        assert Path(step['cwd']).is_relative_to(Path(source['snapshot']))
    elapsed = (datetime.datetime.fromisoformat(summary['finished_at']) - datetime.datetime.fromisoformat(summary['started_at'])).total_seconds()
    assert elapsed == 923.97619
    assert source['source_head'] == HEAD and source['source_status'] == '' and source['source_tree_sha256'] == TREE
    assert hashlib.sha256(json.dumps(source['files'], sort_keys=True).encode()).hexdigest() == TREE
    snapshot = Path(source['snapshot'])
    assert snapshot == RUN / 'source'
    source_map_file = ROUND / 'root-orchestrator/source-after-schema-1002.json'
    assert meta(source_map_file)['sha256'] == 'dfd9d425190a196cfef05af9efcbf4258b46320d4c8e751b84248f17e611b8bf'
    mapping = load(source_map_file)['file_sha256']
    assert len(mapping) == 1002
    current_pre = {key: meta(REPO / key)['sha256'] for key in mapping}
    frozen = {key: meta(snapshot / key)['sha256'] for key in mapping}
    assert current_pre == frozen == mapping
    assert all(source['files'][key] == value for key, value in mapping.items())
    prior_map = load(ROUND / 'root-orchestrator/source-after-1002.json')['file_sha256']
    changes = sorted(key for key in mapping if mapping[key] != prior_map[key])
    assert changes == ['backend/evaluation/research/expert/models.py', 'backend/tests/test_local_pilot.py']
    assert all(mapping[key] == value for key, value in SIX.items())
    fixtures = {'backend/evaluation/research/expert/data/trace.schema.json': 'de2efb6c801d5c4f94ee079f5706072711f84ac299790ecccbd4d45fe9a6bb20', 'backend/tests/test_expert_catalogue_trace.py': 'ea04e62df826513665901ccb00ff3d0bc5cd079a441b3554c9a3fcf074b170ec'}
    assert all(mapping[key] == value for key, value in fixtures.items())
    old_run = RUN.parent / '20261008T053629Z-check-6693acd5'
    old_set, old_status = cases(old_run / 'backend-sqlite.xml')
    assert meta(old_run / 'backend-sqlite.xml')['sha256'] == '7a577fa87222dce809b15bf21476b70447ebdfbe3164d012ff1fb7392e87ab5e'
    old_pg_set, _ = cases(old_run / 'backend-postgresql.xml')
    assert meta(old_run / 'backend-postgresql.xml')['sha256'] == '7399ba762f6151e8da101f87511e783505f392995dba4c9103ec83961c00ae95'
    assert old_set == old_pg_set and len(old_set) == 4349 and all(not x for x in old_status.values())
    expected_new = {('tests.test_local_pilot', name) for name in NEW_NAMES}
    db = {}
    final_set = None
    for mode in ('sqlite', 'postgresql'):
        identities, statuses = cases(RUN / ('backend-' + mode + '.xml'))
        assert len(identities) == 4369 and all(not x for x in statuses.values())
        assert old_set <= identities and identities - old_set == expected_new
        assert OLD_NODE in identities and statuses[OLD_NODE] == []
        if final_set is not None:
            assert final_set == identities
        final_set = identities
        text = (RUN / ('backend-' + mode + '.log')).read_text()
        match = re.search(r'4369 passed, 32 warnings in ([\d.]+)s', text)
        assert match
        assert all(x in text for x in ('StarletteDeprecationWarning', 'MarkupResemblesLocatorWarning', 'XMLParsedAsHTMLWarning', 'tests/test_documents_by_completion.py: 1 warning', 'tests/test_live_discovery.py: 15 warnings'))
        db[mode] = {'unique': len(identities), 'passed': 4369, 'failures': 0, 'errors': 0, 'skipped': 0, 'warnings': 32, 'pytest_seconds': float(match[1]), 'identities_sha256': hashlib.sha256(json.dumps(sorted(identities)).encode()).hexdigest(), 'unchanged_schema_node': 'PASS'}
    sqlite_text = (RUN / 'backend-sqlite.log').read_text()
    assert 'Total coverage: 95.27%' in sqlite_text
    db['sqlite']['app_coverage_percent'] = 95.27
    db['postgresql']['app_coverage_percent'] = None
    assert 'Total coverage:' not in (RUN / 'backend-postgresql.log').read_text()
    assert (RUN / 'ruff.log').read_text() == 'All checks passed!\n'
    assert '386 files already formatted' in (RUN / 'ruff-format.log').read_text()
    assert 'Success: no issues found in 386 source files' in (RUN / 'mypy.log').read_text()
    assert re.search(r'Tests\s+232 passed \(232\)', (RUN / 'frontend-tests.log').read_text())
    e2e = (RUN / 'e2e.log').read_text()
    assert re.search(r'\b1 skipped\b', e2e) and re.search(r'\b79 passed\b', e2e)
    skipped = [line for line in e2e.splitlines() if re.search(r'-\s+\d+ \[desktop-chromium\].*every community screen is reachable on a phone', line)]
    assert len(skipped) == 1
    assert any('[mobile]' in line and 'every community screen is reachable on a phone' in line and '✓' in line for line in e2e.splitlines())
    assert re.search(r'\b6 passed\b', (RUN / 'e2e-auth.log').read_text())
    assert (RUN / 'pip-audit.log').read_text().strip() == 'No known vulnerabilities found'
    assert (RUN / 'npm-audit.log').read_text().strip() == 'found 0 vulnerabilities'
    seed_folder = ROUND / 'a-corrected-owned-seed'
    seed_packet = sealed(seed_folder, '50c7043d7f941547b90ee8ca141274e3ec2d0cd22fa3b2ec878779a9e2ac9a9b')
    assert len(seed_packet['files']) == 28
    assert meta(seed_folder / 'receipt.json')['sha256'] == 'e1e6e28649a0148b74b22517c56b34cba2f065e99e92af0fcdab27dda6bd5c43'
    seed = load(seed_folder / 'receipt.json')
    seed_pins = load(seed_folder / 'candidate-source-pins.json')
    assert len(seed_pins) == 265 and seed['source_head'] == HEAD
    assert all(meta(REPO / key)['sha256'] == value == meta(snapshot / key)['sha256'] == meta(seed_folder / 'candidate' / key)['sha256'] for key, value in seed_pins.items())
    assert [x['action'] for x in seed['commands']] == ['heads', 'migrate', 'seed', 'inspect']
    assert all(x['exit_code'] == 0 and x['control'] is None for x in seed['commands'])
    for command in seed['commands']:
        for stream in ('stdout', 'stderr'):
            assert meta(seed_folder / (command['action'] + '.' + stream + '.original.log'))['sha256'] == command[stream + '_sha256']
    inspection = load(seed_folder / 'inspection.original.json')
    assert inspection == seed['inspection']
    assert inspection['heads'] == inspection['database_revisions'] == ['d8e412c6a901']
    assert inspection['rows'] == 20 and inspection['first'] == 'University of Groningen' and inspection['all_undecided_no_approve'] is True
    assert inspection['UBC']['portfolio_bucket'] == 'OUT_OF_BUDGET' and inspection['UBC']['funding_classification'] == 'FULL_TUITION'
    assert seed['network_attempts'] == seed['provider_model_university_calls'] == seed['approvals'] == 0
    application = seed['application_binding']
    assert meta(Path(application['path'])) == {k: application[k] for k in ('sha256', 'bytes')}
    prior_seed = sealed(ROUND / 'a-owned-seed', 'b7e50f3abd6f6ef56704fccd7990c4dc4dfa9a1ca8196df02e0966767ad1e57d')
    assert len(prior_seed['files']) == 30
    failed_folder = ROUND / 'b-full-closure'
    failed_packet = sealed(failed_folder, 'd553e2fc4afb98d20aa8bd449355f6526d111efa00d09d8f6a83b94e34e62b34')
    assert len(failed_packet['files']) == 11
    failed_originals = load(failed_folder / 'failed-full-originals-manifest.json')
    for name, stamp in failed_originals['files'].items():
        assert meta(Path(failed_originals['root']) / name) == stamp
    assert load(Path(failed_originals['root']) / 'summary.json')['status'] == 'failed'
    for mode in ('sqlite', 'postgresql'):
        failed_ids, failed_status = cases(Path(failed_originals['root']) / ('backend-' + mode + '.xml'))
        assert failed_ids == final_set and failed_status[OLD_NODE] == ['failure']
        assert sum(bool(x) for x in failed_status.values()) == 1
    current_post = {key: meta(REPO / key)['sha256'] for key in mapping}
    assert current_pre == current_post == mapping
    assert meta(STOP) == stop_pre
    assert all(meta(RUN / name) == stamp == meta(RAW / name) for name, stamp in raw_pre.items())
    assert all(meta(seed_folder / name) == stamp for name, stamp in seed_packet['files'].items())
    assert all(meta(failed_folder / name) == stamp for name, stamp in failed_packet['files'].items())
    write('corrected-full-originals-manifest.json', {'root': str(RUN), 'root_copy': str(RAW), 'root_ready_manifest': meta(RAW / 'ready-manifest.json'), 'files': raw_pre, 'files_count': 17, 'total_bytes': 5697217, 'all_pre_post_equal': True})
    record = {'status': 'CORRECTED_LOCAL_FULL13_PASS_SAVED_EVIDENCE_VERIFIED_NOT_LIVE_QUALITY_ACCEPTANCE', 'sealed_utc': datetime.datetime.now(datetime.UTC).isoformat(), 'run': str(RUN), 'source_head': HEAD, 'source_tree_sha256': TREE, 'source_manifest': meta(RUN / 'source-manifest.json'), 'selected_source': {'count': 1002, 'map': meta(source_map_file), 'current_frozen_metadata_pre_post_exact': True, 'six_exact': SIX, 'changes_from_failed_full': changes, 'other1000_unchanged': True, 'fixture_and_old_test_unchanged': fixtures}, 'full_steps': summary['steps'], 'elapsed_seconds': elapsed, 'backend': db, 'old_unique_backend_cases_preserved': 4349, 'exact_new_cases': sorted(expected_new), 'new_cases_count': 20, 'warnings_qualification': 'Each DB has1 Starlette dependency warning,16 Markup warnings (15 live_discovery synthetic cases +1 documents case),15 XML parser warnings; not suppressed. SQLite only measures app coverage; PG no coverage line.', 'frontend': {'unit_passed': 232, 'demo_passed': 79, 'demo_skipped': 1, 'skip_original_line': skipped[0], 'phone_test_mobile_passed': True, 'auth_passed': 6, 'audits_exit0': True}, 'static': {'ruff': 'PASS app/tests/evaluation', 'ruff_format_files': 386, 'mypy_source_files': 386, 'mypy_unchecked_body_notes_preserved': True}, 'raw_originals': {'files': 17, 'bytes': 5697217, 'copies_match_originals_pre_post': True}, 'seed': {'manifest': meta(seed_folder / 'ready-manifest.json'), 'receipt': meta(seed_folder / 'receipt.json'), 'selected': 28, 'bytes': sum(v['bytes'] for v in seed_packet['files'].values()), 'current_frozen_candidate_pins': 265, 'four_saved_commands_exit0': True, 'inspection': inspection, 'qualification': 'Saved isolated demo compatibility only; no own seed rerun or operational/runtime/quality acceptance.'}, 'history': {'failed_full_manifest': meta(failed_folder / 'ready-manifest.json'), 'failed_full_originals_unchanged': len(failed_originals['files']), 'failed_full_4368pass_1schema_failure_each_db_preserved': True, 'prior_seed30_unchanged': True}, 'STOP': stop_pre, 'own_app_import_tests_full_seed_SQL_CLI_network_calls': 0, 'qualification': 'Finite saved-byte independent corroboration of this corrected local full and seed. No live/model/provider/university dispatch, gold/labels/scoring, owner grant or actual OS/model isolation admission; no hosted/container/production/quality claim. Failed first-full history remains FAILED.'}
    write('corrected-full-verification.json', record)
    print(json.dumps({'status': record['status'], 'raw_files': 17, 'raw_bytes': 5697217, 'backend_unique_each': 4369, 'old': 4349, 'new': 20, 'steps': len(summary['steps']), 'verification': meta(OWN / 'corrected-full-verification.json')}, indent=2))

if __name__ == '__main__':
    try:
        run_review()
    except Exception as exc:
        write('checker-error.original.json', {'time': datetime.datetime.now(datetime.UTC).isoformat(), 'type': type(exc).__name__, 'error': str(exc), 'traceback': traceback.format_exc(), 'qualification': 'Verifier error is preserved; it is not itself an app test failure.'})
        raise

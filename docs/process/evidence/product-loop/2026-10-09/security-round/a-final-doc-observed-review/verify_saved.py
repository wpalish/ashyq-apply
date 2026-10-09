# -*- coding: utf-8 -*-
"""Read-only saved-evidence verification. Writes only this owned review directory."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import xml.etree.ElementTree as ET

BASE = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1')
REPO = BASE.parent / 'ashyq-apply'
OUT = BASE / 'a-final-doc-observed-review'
CANON = REPO / 'docs/process/evidence/product-loop/2026-10-09/security-round/full-final'
PINS = {}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pin(p, expected=None, size=None):
    p = Path(p)
    row = {'sha256': sha(p), 'bytes': p.stat().st_size}
    if expected is not None:
        assert row['sha256'] == expected, str(p)
    if size is not None:
        assert row['bytes'] == size, str(p)
    PINS[str(p)] = row
    return row


def data(p):
    pin(p)
    return json.loads(Path(p).read_text())


def ready(folder, name, expected):
    p = BASE / folder / name
    pin(p, expected)
    v = data(p)
    for rel, row in v['files'].items():
        q = p.parent / rel
        assert q.resolve().is_relative_to(p.parent.resolve()) and not q.is_symlink()
        pin(q, row['sha256'], row['bytes'])
    return v


def ids(p):
    pin(p)
    nodes = ET.parse(p).getroot().findall('.//testcase')
    result = {(v.get('classname'), v.get('name')) for v in nodes}
    assert len(result) == len(nodes)
    assert all(v.find('failure') is None and v.find('error') is None and v.find('skipped') is None for v in nodes)
    return result


def saved_suite(path, count):
    v = data(Path(path) / 'summary.json')
    assert v['status'] == 'passed' and v.get('finished_at')
    assert len(v['steps']) == count and all(s['exit_code'] == 0 for s in v['steps'])
    assert v['source']['source_head'] == HEAD
    return v


accept = data(BASE / 'root-final-acceptance.json')
pin(BASE / 'root-final-acceptance.json', '2555f40b7767991dfbe2f21082c7d8677c541e42168c974ae15bfe3536c1235b')
assert accept['status'] == 'QUALIFIED_LOCAL_SECURITY_INCREMENT_ACCEPT'
HEAD = accept['source_head']
assert (BASE / 'final-head.txt').read_text().strip() == HEAD
pin(BASE / 'final-head.txt')
source20 = data(BASE / 'final-source-pins.json')
pin(BASE / 'final-source-pins.json', accept['source20_sha256'])
assert len(source20) == 20
pin(BASE.parent / 'local-round7/provider-STOP.json', '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d', 142)

B = ready('b-security-release-doc-review', 'ready-manifest.json', '85335e02496a3fecc54d77052a0fa04acc2d56cbdf45b67bceb52ffa313e98f1')
R = ready('b-final-doc-qualification-plan', 'READY.json', 'e493d743780e7d12698edda0d9cd8565a7a7ce002296c512c80dc04b93637fdd')
D = ready('a-security-export-final-native/full-terminal', 'READY.json', accept['native_review_READY_sha256'])
U = ready('a-export-final-ui-closure-review', 'READY.json', accept['UI_cleanup_review_READY_sha256'])
C = ready('c-export-view-final-observed', 'READY.json', accept['browser_READY_sha256'])

receipt = data(BASE / 'b-security-release-doc-review/receipt.json')
names = {'SECURITY.md', 'docs/legal/RELEASE_READINESS.md', 'docs/legal/PRIVACY_POLICY_RU.md'}
assert set(receipt['baseline_documents']) == set(receipt['proposed_documents']) == names
texts = {}
for rel in names:
    for sub, record in [('original', receipt['baseline_documents'][rel]), ('proposed', receipt['proposed_documents'][rel])]:
        pin(BASE / 'b-security-release-doc-review' / sub / rel, record['sha256'], record['bytes'])
    texts[rel] = (BASE / 'b-security-release-doc-review/proposed' / rel).read_text()
history = texts['docs/legal/RELEASE_READINESS.md'].split('<details>', 1)[1]
items = data(BASE / 'b-final-doc-qualification-plan/exact-replacements.json')['items']
assert len(items) == 11
for item in items:
    old, rel = item['exact_old'], item['document']
    assert texts[rel].count(old) == 1
    texts[rel] = texts[rel].replace(old, item['candidate_new'].replace('<FINAL_SOURCE_HEAD>', HEAD), 1)
pin(BASE / 'final-local-closure.md', '782495b308bebcf8e8c7605f434790b0a1c1f6dfdf972976ca47e7f285a19189')
closure = (BASE / 'final-local-closure.md').read_text()
marker = '## История проверки и незакрытый итог'
assert texts['docs/legal/RELEASE_READINESS.md'].count(marker) == 1
texts['docs/legal/RELEASE_READINESS.md'] = texts['docs/legal/RELEASE_READINESS.md'].replace(marker, '## Квалифицированная локальная проверка\n\n' + closure + '\n\n' + marker, 1)
assert texts['docs/legal/RELEASE_READINESS.md'].split('<details>', 1)[1] == history
application = data(BASE / 'final-docs-application-receipt.json')
pin(BASE / 'final-docs-application-receipt.json', '4f901df7d91a5e0d842f290bd85dcd8d2cd864e97b9a0a720395f5ac201941b1')
assert application['source_head'] == HEAD
assert application['root_acceptance_sha256'] == sha(BASE / 'root-final-acceptance.json')
assert application['historical_details_unchanged'] is True and application['operator_version_consent_facts_changed'] is False
assert set(application['output_documents']) == names
for rel in names:
    row = application['output_documents'][rel]
    pin(REPO / rel, row['sha256'], row['bytes'])
    assert (REPO / rel).read_bytes() == texts[rel].encode('utf-8')
assert '2026-10-09.draft1' in texts['docs/legal/PRIVACY_POLICY_RU.md']
assert all('<FINAL_SOURCE_HEAD>' not in v for v in texts.values())

copies = data(CANON / 'COPY_RECEIPT.json')
assert len(copies['files']) == copies['count'] == 17
for rel, record in {**copies['files'], **copies['parent_queue_originals']}.items():
    pin(CANON / rel, record['sha256'], record['bytes'])
    pin(Path(record['source']), record['sha256'], record['bytes'])
assert sum(v['bytes'] for v in copies['files'].values()) == copies['bytes'] == 6319285
manifest = data(CANON / 'source-manifest.json')
pin(CANON / 'source-manifest.json', accept['full_manifest_sha256'])
full = data(CANON / 'summary.json')
pin(CANON / 'summary.json', accept['full_summary_sha256'])
assert full['status'] == 'passed' and full['suite'] == 'full' and full.get('finished_at')
assert len(full['steps']) == 13 and all(s['exit_code'] == 0 for s in full['steps'])
assert not full['github_actions_started'] and not full['live_network_capture_started'] and not full['includes_container_gates']
assert full['source'] == manifest and manifest['source_head'] == HEAD
assert manifest['source_tree_sha256'] == accept['initial_source_tree_sha256']
assert hashlib.sha256(json.dumps(manifest['files'], sort_keys=True).encode()).hexdigest() == manifest['source_tree_sha256']
snapshot = Path(manifest['snapshot'])
for rel, expected in source20.items():
    pin(REPO / rel, expected)
    pin(snapshot / rel, expected)
    assert manifest['files'][rel] == expected
changed = []
for rel, expected in manifest['files'].items():
    q = snapshot / rel
    assert q.is_file()
    got = sha(q)
    if got != expected:
        changed.append({'path': rel, 'before': expected, 'after': got})
assert len(changed) == 38
assert all(v['path'].startswith('docs/screenshots/') and v['path'].endswith('.png') for v in changed)
assert sum('/mobile/' in v['path'] for v in changed) == 18
assert len(manifest['files']) - len(changed) == accept['other_declared_files_exact'] == 11449
delta = data(BASE / 'post-export-view-full-delta.json')
native_id_set = ids(CANON / 'backend-sqlite.xml')
assert len(native_id_set) == 4384 and native_id_set == ids(CANON / 'backend-postgresql.xml')
assert native_id_set == ids(REPO / 'docs/process/evidence/product-loop/2026-10-09/security-round/full-recovery/backend-sqlite.xml')
queue = data(BASE / 'native-queue-final/execution.json')
assert len(queue) == 2 and all(v['exit_code'] == 0 for v in queue)
core = saved_suite(queue[0]['owned_runs'][0]['path'], 8)
assert queue[1]['owned_runs'][0]['path'] == copies['source_run']
doctor_receipt = data(BASE / 'doctor-final-originals/receipt.json')
doctor = saved_suite(doctor_receipt['source_run'], 5)
assert doctor['docker_available'] is False
assert ids(Path(queue[0]['owned_runs'][0]['path']) / 'backend-sqlite.xml') == native_id_set

logs = {n: (CANON / n).read_text() for n in ['backend-sqlite.log', 'backend-postgresql.log', 'frontend-tests.log', 'e2e.log', 'e2e-auth.log', 'mypy.log', 'pip-audit.log', 'npm-audit.log']}
sqlite = re.search(r'(\d+) passed, (\d+) warnings in ([\d.]+)s', logs['backend-sqlite.log']).groups()
pg = re.search(r'(\d+) passed, (\d+) warnings in ([\d.]+)s', logs['backend-postgresql.log']).groups()
coverage = float(re.search(r'Total coverage: ([\d.]+)%', logs['backend-sqlite.log']).group(1))
assert sqlite == ('4384', '32', '486.44') and pg == ('4384', '32', '362.95') and coverage == 95.26
assert re.search(r'Test Files\s+34 passed', logs['frontend-tests.log']) and re.search(r'Tests\s+357 passed', logs['frontend-tests.log'])
assert re.search(r'\b79 passed\b', logs['e2e.log']) and re.search(r'\b1 skipped\b', logs['e2e.log'])
assert re.search(r'\b6 passed\b', logs['e2e-auth.log'])
assert 'Success: no issues found in 386 source files' in logs['mypy.log']
assert 'No known vulnerabilities found' in logs['pip-audit.log'] and 'found 0 vulnerabilities' in logs['npm-audit.log']
core_sqlite = Path(queue[0]['owned_runs'][0]['path']) / 'backend-sqlite.log'
pin(core_sqlite)
assert '4384 passed, 32 warnings in 490.18s' in core_sqlite.read_text()

ui = BASE / 'c-export-view-final-observed'
action = data(ui / '01-immediate-ack-action.json')
reload = data(ui / 'reload-action.json')
assert action['tested_head'] == HEAD and action['source20_sha256'] == accept['source20_sha256']
assert action['acknowledged'] and not action['navigation_or_reload_before_capture']
assert action['before_delete_opened_JSON'] and action['before_delete_runs_empty']
assert action['DELET_enabled'] is False and action['exact_DELETE_enabled'] is True
assert all(action[k] is False for k in ['stored_data_region_in_ACK_AX', 'old_marker_in_ACK_AX', 'stored_data_region_in_ACK_DOM', 'old_marker_in_ACK_DOM'])
chronology = {k: datetime.fromisoformat(action[k].replace('Z', '+00:00')) for k in ['native_delete_at', 'recorded_at']}
assert chronology['native_delete_at'] < chronology['recorded_at'] < datetime.fromisoformat(reload['recorded_at'].replace('Z', '+00:00'))
assert (chronology['recorded_at'] - chronology['native_delete_at']).total_seconds() == 0.425
assert action['actual_geometry']['viewport'] == {'width': 1440, 'height': 900}
for n in ['01-immediate-ack-ax.txt', '01-immediate-ack-dom.txt']:
    value = (ui / n).read_text()
    assert 'Deleted. The profile and its linked research records were removed from the active service.' in value
    assert 'Stored profile data' not in value
assert reload['saved_case_option_present'] is False and reload['old_marker_present'] is False and reload['stored_data_region_present'] is False
assert reload['screenshot'] == 'NONE_AX_ONLY' and reload['optional_phone'] == 'NOT_RUN_NOT_NEEDED'
assert 'Новый абитуриент' in (ui / 'reload-settled-ax.txt').read_text()
assert C['mandatory_desktop_captures'] == C['JPEG_count'] == 1
binding = data(ui / 'source-runtime-binding.json')
for rel, row in binding['selected_safe_receipts'].items():
    pin(ui / 'selected-safe-receipts' / rel, row['sha256'], row['bytes'])
    pin(Path(row['origin_path']), row['sha256'], row['bytes'])
for rel, expected in binding['config_input_pins'].items():
    pin(REPO / rel, expected)
    pin(snapshot / rel, expected)
cleanup = data(BASE / 'preview-auth-export-final/cleanup-receipt.json')
pin(BASE / 'preview-auth-export-final/cleanup-receipt.json', accept['cleanup_sha256'])
assert cleanup['errors'] == [] and all(cleanup[k] is True for k in ['lock_held_during_cleanup', 'all_owned_cleanup_attempts_complete', 'source_and_config_postcheck_passed', 'ports_free_before_unlock'])
execution = data(BASE / 'final-preview-execution.json')
pin(BASE / 'final-preview-execution.json', accept['root_preview_execution_sha256'])
assert execution['exit_code'] == 0 and execution['owned_pids'] == cleanup['owned_pids'] == [5810, 5811]
assert execution['selected_GO_sha256'] == accept['qualified_GO_sha256'] == binding['root_GO_sha256']
browser_cleanup = data(ui / 'browser-cleanup.json')
assert browser_cleanup['viewport_override_reset'] and browser_cleanup['errors'] == [] and browser_cleanup['owned_tabs_created'] == 1

report_receipt = data(BASE / 'final-report-source-receipt.json')
pin(Path(report_receipt['output_path']), '8d13c8a4446362cb78890d4ca37531e9b44fbfba3a4d39a6606f04f1a95be8fa', 12585)
assert report_receipt['root_acceptance_sha256'] == sha(BASE / 'root-final-acceptance.json')
assert report_receipt['source_head'] == HEAD and report_receipt['source20_unchanged'] is True
report = Path(report_receipt['output_path']).read_text()
assert all(value in report for value in [HEAD, accept['initial_source_tree_sha256'], accept['source20_sha256'], 'DRAFT', '13/13', '357 PASS', '95,26%', 'NOT_RUN_NOT_NEEDED', 'FAILED 12/13'])
pin(BASE / 'final-acceptance-author-diagnostic.md')
pin(BASE / 'apply_final_qualified_docs.py', '97463857ed5a8dc8d0f0c2928c44345f0c5e589ee9e9cc3175e4c1ae3d916d6c')
pin(BASE / 'a-final-doc-prospective-review/READY.json', 'a5025daa0bafa8443dd987338592b2528ee6c11bafe7cdd8142b6394d42f60c7')

findings = {
    'status': 'QUALIFIED_ACCEPT_APPLIED_DRAFT_DOCS_AND_SAVED_LOCAL_REPORT',
    'source_head': HEAD,
    'source20_sha256': accept['source20_sha256'],
    'root_acceptance_sha256': sha(BASE / 'root-final-acceptance.json'),
    'exact3_reconstructed_bytes_equal': True,
    'unique_conditional_replacements': len(items),
    'historical_details_byte_exact': True,
    'DRAFT_policy_version_operator_consent_not_changed': True,
    'native': {'doctor_passed': 5, 'core_passed': 8, 'single_full_passed': 13, 'SQLite': {'unique_passed': 4384, 'warnings': 32, 'coverage': coverage, 'test_seconds': 486.44}, 'PostgreSQL': {'same_unique_IDs': 4384, 'warnings': 32, 'coverage': 'NOT_MEASURED', 'test_seconds': 362.95}, 'backend_IDs_equal_prior_recovery_and_core': True, 'frontend_passed': 357, 'frontend_files': 34, 'demo_passed': 79, 'demo_old_skip': 1, 'auth_passed': 6, 'mypy_files': 386, 'pip_known_vulnerabilities': 0, 'npm_known_vulnerabilities': 0, 'native_originals': 17, 'native_original_bytes': 6319285, 'queue_originals': 3},
    'snapshot': {'initial_tree': manifest['source_tree_sha256'], 'declared_count': len(manifest['files']), 'PNG_deltas': 38, 'mobile_PNG_deltas': 18, 'other_declared_exact': 11449, 'primary_whole_tree_equality': 'NOT_CLAIMED'},
    'observed_UI': {'captures': 1, 'desktop': '1440x900', 'immediate_ACK_clear': 'AX/DOM/JPEG before navigation/reload', 'ACK_to_saved_observation_ms': 425, 'reload': 'same-owner AX-only absence', 'phone': 'NOT_RUN_NOT_NEEDED', 'JPEG_visual_review': 'Deleted notice visible; profile buttons disabled; no open JSON in viewport, whole AX/DOM establishes region absence'},
    'cleanup': {'saved_owned_exit': 0, 'saved_owned_pids': [5810, 5811], 'errors': [], 'source_config_and_free_ports_before_unlock': True, 'own_tab_closed_and_viewport_reset': True, 'peer_new_process_port_checks': 0},
    'document_and_report_boundaries': ['Case export, not account-wide', 'Profile direct Show/Download only; shortlist unchanged', 'Cooperative client controls, not server atomicity/shared-cookie request cancellation', 'No completed-download/recipient/cache/backup recall guarantee', 'Reset request detail-only but ConsoleSender may log links; reset concurrency/PII/Nginx gaps stay queued', 'Operator/versioned consent/minor/retention legal facts unresolved; DRAFT remains', 'No production/hosted/container/search-quality/legal-ready/security-superiority acceptance'],
    'history': 'First FAILED security full, previous c7b full/C7 residual and author setup diagnostics retained as distinct history; no relabelled PASS',
    'material_findings': [],
    'scope': 'Read-only stdlib saved artifacts and one local JPEG view; no app imports/runtime/tests/Git/SQL/ports/live/scorer calls. No legal applicability or new operator facts verified.',
    'recorded_at': datetime.now(timezone.utc).isoformat(),
}
(OUT / 'pins.json').write_text(json.dumps(PINS, ensure_ascii=False, indent=2) + '\n')
(OUT / 'findings.json').write_text(json.dumps(findings, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': findings['status'], 'input_pin_count': len(PINS), 'exact3': True, 'replacement_count': 11, 'source20': True, 'full': '13/13', 'backend_unique': 4384, 'frontend': 357, 'snapshot_other_exact': 11449, 'UI': '1desktop_ACK425ms_then_reloadAX', 'cleanup': 'saved_exit0/errors[]', 'material_findings': []}))

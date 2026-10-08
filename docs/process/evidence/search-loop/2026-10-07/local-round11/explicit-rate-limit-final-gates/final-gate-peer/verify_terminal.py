"""Terminal saved-artifact audit only. No app imports, subprocesses or test execution."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

B = Path(__file__).resolve().parent
plan = json.loads((B / 'PLAN.json').read_text())
run = Path(plan['run'])
sha = lambda data: hashlib.sha256(data).hexdigest()

source_bytes = (run / 'source-manifest.json').read_bytes()
source = json.loads(source_bytes)
expected_map = json.loads((B / 'packet/source-after-isort-999.json').read_text())['file_sha256']
expected_ids = {tuple(x) for x in json.loads((B / 'packet/expected-native90-identities.json').read_text())['identities']}
summary_bytes = (run / 'summary.json').read_bytes()
summary = json.loads(summary_bytes)
assert summary['status'] != 'running', 'Parent completion required; no result written while running'

checks = []
def check(name, expected, actual):
    checks.append({'name': name, 'expected': expected, 'actual': actual,
                   'status': 'PASS' if expected == actual else 'RED'})

check('source_manifest_immutable', plan['source_manifest_sha256'], sha(source_bytes))
check('frozen_head', plan['source_head'], source['source_head'])
check('frozen_source_tree', plan['source_tree_sha256'], source['source_tree_sha256'])
check('selected_source_map999', True, all(source['files'].get(path) == value for path, value in expected_map.items()) and len(expected_map) == 999)
steps = summary.get('steps', [])
check('terminal_summary_status', 'passed', summary['status'])
check('actual_full_steps13', 13, len(steps))
check('unique_step_names13', 13, len({s.get('name') for s in steps}))
check('each_step_exit0_noerror', True, all(type(s.get('exit_code')) is int and s['exit_code'] == 0 and not s.get('error') for s in steps))
check('github_actions_not_started', False, summary.get('github_actions_started'))
check('live_network_capture_not_started', False, summary.get('live_network_capture_started'))

native_modules = {'test_exa_mcp', 'test_search_layer_budget_fixes', 'test_search_throttle_latch'}
databases = {}
for db in ['sqlite', 'postgresql']:
    filename = f'backend-{db}.xml'
    data = (run / filename).read_bytes()
    root = ET.fromstring(data)
    cases = root.findall('.//testcase')
    whole_ids = [(n.get('classname', ''), n.get('name', '')) for n in cases]
    focused = [n for n in cases if n.get('classname', '').split('.')[-1] in native_modules]
    native_ids = [(n.get('classname', '').split('.')[-1], n.get('name', '')) for n in focused]
    bad = [{'identity': (n.get('classname'), n.get('name')), 'tags': [c.tag for c in n]}
           for n in focused if any(c.tag in {'failure', 'error', 'skipped'} for c in n)]
    check(f'{db}_native_cases90', 90, len(focused))
    check(f'{db}_native_unique90', 90, len(set(native_ids)))
    check(f'{db}_native_exact_accepted_identities', True, set(native_ids) == expected_ids)
    check(f'{db}_native_fail_skip_error0', 0, len(bad))
    check(f'{db}_backend_unique4312', 4312, len(set(whole_ids)))
    check(f'{db}_backend_no_duplicate_identites', 0, len(whole_ids) - len(set(whole_ids)))
    databases[db] = {'junit_sha256': sha(data), 'testcases': len(cases), 'unique_backend_identities': len(set(whole_ids)),
                     'native_cases': len(focused), 'native_unique': len(set(native_ids)), 'native_missing': sorted(expected_ids-set(native_ids)),
                     'native_extra': sorted(set(native_ids)-expected_ids), 'native_bad': bad, 'all_backend_identities': sorted(set(whole_ids)),
                     'native_identities': sorted(native_ids), 'all_backend_skipped': sum(any(c.tag=='skipped' for c in n) for n in cases),
                     'all_backend_failed': sum(any(c.tag=='failure' for c in n) for n in cases), 'all_backend_errors': sum(any(c.tag=='error' for c in n) for n in cases)}
    (B / 'packet' / filename).write_bytes(data)
check('both_DB_backend_identity_sets_match', True, databases['sqlite']['all_backend_identities'] == databases['postgresql']['all_backend_identities'])

stop = B.parents[1] / 'local-round7/provider-STOP.json'
check('sticky_STOP_unchanged', plan['STOP_sha256'], sha(stop.read_bytes()))
(B / 'packet/terminal-summary.json').write_bytes(summary_bytes)
result = {'status': 'ACCEPT_TERMINAL_SOURCE_AND_COLLECTION_ALIGNMENT' if not any(c['status']=='RED' for c in checks) else 'RED_TERMINAL_ALIGNMENT',
          'checks': checks, 'PASS': sum(c['status']=='PASS' for c in checks), 'RED': sum(c['status']=='RED' for c in checks),
          'summary_sha256': sha(summary_bytes), 'source_manifest_sha256': sha(source_bytes), 'source_tree_sha256': source['source_tree_sha256'],
          'databases': databases, 'steps': steps, 'B_tests_executed': 0, 'B_app_imports': 0, 'B_network_reset_Git_source_actions': 0,
          'qualification': 'Only saved source/hash metadata, native JUnit collection/result identities and terminal summary. No quality/newdefect score or corpus/label read. Expected total verified against actual case sets, not manufactured.'}
out = B / 'terminal-validation.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['status','PASS','RED']}))

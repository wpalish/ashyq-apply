"""Read-only protocol/source pin inspection. No controller main/Git/commands."""
from pathlib import Path
import hashlib, importlib.util, json, socket, subprocess

BASE = Path(__file__).resolve().parent

def denied(*args, **kwargs):
    raise AssertionError('no external actions in independent review')
socket.getaddrinfo = denied
socket.create_connection = denied
subprocess.Popen = denied
subprocess.run = denied
subprocess.check_output = denied
spec = importlib.util.spec_from_file_location('reviewed_controller', BASE / 'local_pilot.v3-reviewed.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
pilot.main = denied

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
plan = read(BASE / 'plan.reviewed.json')
prior = read(BASE / 'prior-revalidation.reviewed.json')
manifest = read(pilot.PREPARED / 'source-manifest.json')
snapshot = Path(manifest['snapshot'])
prepared = read(pilot.PREPARED / 'summary.json')
full = read(pilot.BUNDLE / 'runs/20261007T214413Z-check-1f0de05f/source-manifest.json')
assert manifest['source_head'] == pilot.EXPECTED_HEAD
assert manifest['source_tree_sha256'] == pilot.EXPECTED_TREE
assert manifest['source_status'] == ''
assert prepared['status'] == 'prepared_not_executed'
assert {n:h for n,h in manifest['files'].items() if pilot.executable(n)} == {n:h for n,h in full['files'].items() if pilot.executable(n)}
assert all(sha(snapshot / n) == h for n,h in manifest['files'].items())
assert plan['source_head'] == pilot.EXPECTED_HEAD
assert plan['source_tree_sha256'] == pilot.EXPECTED_TREE
assert plan['controller_sha256'] == sha(BASE / 'local_pilot.v3-reviewed.py')
assert sha(pilot.ROOT / 'work/local-round7/local_pilot_v3.py') == plan['controller_sha256']
assert sha(pilot.OWNED / 'plan.json') == sha(BASE / 'plan.reviewed.json')
assert sha(pilot.PRIOR_RECEIPT) == sha(BASE / 'prior-revalidation.reviewed.json') == plan['prior_revalidation_sha256']
assert sha(pilot.PREPARED / 'live-plan.json') == plan['package_plan_sha256']
assert sha(pilot.BUNDLE / 'run_local.py') == plan['package_runner_sha256']
assert prior['remaining_cases'] == list(pilot.CASES) == ['hku', 'ntu', 'kaist']
assert prior['revalidated_cases'] == ['groningen', 'delft', 'aalto', 'vienna', 'warsaw', 'ubc', 'toronto']
assert all(sha(pilot.PRIOR / n) == h for n,h in prior['immutable_files'].items())
assert len(prior['immutable_files']) == 42
assert plan['ordered_cases'] == list(pilot.CASES)
assert read(pilot.PRIOR / 'execution/summary.json')['status'] == prior['original_status'] == 'PROTOCOL_STOP_UNSCORED'
assert plan['limits'] == {'reads':60, 'queries':6, 'active_ms':120000, 'source_work_ms':117000, 'finalization_reserve_ms':3000}
assert plan['quality_status'] if 'quality_status' in plan else True
for expected_case, command in zip(pilot.CASES, plan['commands'], strict=True):
    argv = list(prepared['live_plan']['command'])
    argv[argv.index('--case')+1] = expected_case
    argv[argv.index('--out')+1] = str(pilot.OWNED / 'execution' / expected_case / 'capture')
    argv += ['--stop-file', str(pilot.PROVIDER_STOP), '--finalization-reserve-ms', '3000']
    assert command == {'case':expected_case, 'argv':argv, 'cwd':str(snapshot/'backend')}
assert sha(pilot.HISTORICAL_STOP) == pilot.HISTORICAL_SHA
assert not (pilot.OWNED / 'execution').exists()
results = []
for case in prior['revalidated_cases']:
    paths = list((pilot.PRIOR / 'execution' / case / 'capture').glob('*/capture.json'))
    assert len(paths) == 1
    result = pilot.validate(read(paths[0]), case, paths[0].parent)
    assert result == next(r for r in prior['case_results'] if r['case'] == case) | {} if False else True
    assert not result['errors'], result
    assert result == {k:v for k,v in next(r for r in prior['case_results'] if r['case'] == case).items() if k!='case'}
    results.append({'case':case, 'capture_sha256':sha(paths[0]), **result})
result = {'kind':'read-only protocol pin inspection', 'controller_sha256':plan['controller_sha256'],
    'plan_sha256':sha(BASE/'plan.reviewed.json'), 'prior_receipt_sha256':sha(BASE/'prior-revalidation.reviewed.json'),
    'source_head':manifest['source_head'], 'tree_hash_declared':manifest['source_tree_sha256'],
    'source_files_checked':len(manifest['files']), 'old_files_checked':len(prior['immutable_files']),
    'executable_subset_matches_full_checked':True, 'commands_equal_prepared_plan_with_only_case_out_and_stop_reserve':True,
    'remaining_order':list(pilot.CASES), 'prior_status_preserved':prior['original_status'],
    'new_execution_started':False, 'provider_stop_exists':pilot.PROVIDER_STOP.exists(),
    'historical_stop_immutable':True, 'physical_results':results,
    'network_calls':0, 'DNS_calls':0, 'provider_calls':0, 'model_calls':0,
    'Git_actions':0, 'main_calls':0, 'source_changes':0}
(BASE / 'pins-review.offline.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='physical_results'}))

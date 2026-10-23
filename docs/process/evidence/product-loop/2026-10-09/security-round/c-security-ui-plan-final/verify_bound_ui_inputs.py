"""DESIGN_ONLY proposed verifier: read bindings, print a plan; never launch or seed.

Not executed in this preparation. Root must confirm final actual source/full
receipts after independent review within the user's already-authorized reversible
local synthetic test scope. This is not a request for new human approval.
No DB/env/provider/Git/socket/process API.
The printed plan does not reserve ports; a future root-owned launcher must hold
the shared lock for its full process lifecycle and recheck every input.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
from pathlib import Path

ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
TASK = ROOT / 'work/security-round1'
REPO = ROOT / 'work/ashyq-apply'
BUNDLE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
STOP = ROOT / 'work/local-round7/provider-STOP.json'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
RUNNER_SHA = '46e9866db102966fd42e07aa5b291411cbac1cca0a76f9b49551ca8a4fb919f5'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), 'Input file missing or symlink')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_bound(path: Path, expected: str) -> dict | list:
    require(digest(path) == expected, 'Input receipt hash mismatch')
    return json.loads(path.read_text())


def relative_source(name: str) -> Path:
    path = Path(name)
    require(not path.is_absolute() and '..' not in path.parts, 'Unsafe source path')
    require(not any(part.startswith('.env') for part in path.parts), 'Env source forbidden')
    require(not any(part in {'.git', '.venv', 'node_modules', '__pycache__'} for part in path.parts), 'Dependency/private path forbidden')
    require(not name.startswith(('backend/data/', 'artifacts/')), 'Runtime source forbidden')
    require(not name.endswith(('.db', '.sqlite', '.sqlite3', '-wal', '-shm')), 'DB input forbidden')
    return path


def source_digest(base: Path, relative: Path) -> str:
    path = base / relative
    require(path.resolve().is_relative_to(base.resolve()), 'Source escaped its root')
    return digest(path)


def verify(go: dict) -> dict:
    require(go['status'] == 'ROOT_CONFIRMED_SOURCE_BOUND_UI_GO', 'No root source-bound runtime confirmation')
    require(go['helper_sha256'] == digest(Path(__file__)), 'Helper changed after review')
    require(digest(STOP) == STOP_SHA == go['STOP_sha256'], 'Retained STOP changed')
    require(digest(BUNDLE / 'run_local.py') == RUNNER_SHA == go['runner_sha256'], 'Approved runner changed')
    peer_path = Path(go['static_review_path']).resolve()
    require(peer_path.is_relative_to(TASK.resolve()) and peer_path.suffix == '.json', 'Peer receipt must belong to this round')
    peer = read_bound(peer_path, go['static_review_sha256'])
    require(isinstance(peer, dict) and peer['status'] == 'QUALIFIED_ACCEPT', 'Independent static review required')
    require(peer['helper_sha256'] == go['helper_sha256'], 'Peer reviewed a different helper')
    pins = read_bound(TASK / 'applied-source-pins.json', go['source19_sha256'])
    require(isinstance(pins, dict) and len(pins) == 19, 'Exact applied19 map required')
    require(digest(TASK / 'applied-head.txt') == go['applied_head_file_sha256'], 'Head receipt changed')
    head = (TASK / 'applied-head.txt').read_text().strip()
    require(head == go['actual_full_head'], 'Applied head differs from approved full')
    execution = read_bound(TASK / 'native-queue/execution.json', go['execution_sha256'])
    require(isinstance(execution, list), 'Expected approved queue execution record list')
    full = execution[go['full_record_index']]
    require(full['suite'] == 'full' and full['exit_code'] == 0, 'Selected full did not pass')
    require(len(full['owned_runs']) == 1, 'Ambiguous full run')
    owned = full['owned_runs'][0]
    require(owned['status'] == 'passed', 'Owned full not passed')
    run = Path(owned['path']).resolve()
    require(run.parent == BUNDLE / 'runs', 'Full is not an owned approved runner run')
    summary = read_bound(run / 'summary.json', owned['summary_sha256'])
    require(owned['summary_sha256'] == go['full_summary_sha256'], 'Different actual summary')
    manifest = read_bound(run / 'source-manifest.json', go['full_manifest_sha256'])
    require(summary['status'] == 'passed' and summary['source'] == manifest, 'Summary source/status mismatch')
    require(len(summary['steps']) == 13 and all(step['exit_code'] == 0 for step in summary['steps']), 'Full steps incomplete')
    require(manifest['repository'] == str(REPO) and manifest['source_head'] == head, 'Full repository/head mismatch')
    require(manifest['source_branch'] == go['actual_full_branch'], 'Full branch mismatch')
    require(manifest['source_tree_sha256'] == go['initial_source_tree_sha256'], 'Initial manifest identity mismatch')
    require(hashlib.sha256(json.dumps(manifest['files'], sort_keys=True).encode()).hexdigest() == manifest['source_tree_sha256'], 'Initial declared map digest invalid')
    source = Path(manifest['snapshot']).resolve()
    require(source == run / 'source', 'Unexpected full snapshot')
    delta_path = Path(go['artifact_delta_path']).resolve()
    require(delta_path.is_relative_to(TASK.resolve()), 'Delta receipt must belong to this round')
    delta = read_bound(delta_path, go['artifact_delta_sha256'])
    require(delta['status'] == 'HASH_BOUND_DECLARED_E2E_PNG_DELTA', 'Qualified actual delta required')
    require(delta['source_head'] == head and delta['initial_source_tree_sha256'] == manifest['source_tree_sha256'], 'Delta source mismatch')
    overrides = {}
    for row in delta['files']:
        name = row['path']
        relative_source(name)
        require(name.startswith('docs/screenshots/') and name.endswith('.png'), 'Non-PNG declared delta forbidden')
        require(name not in overrides and row['before_sha256'] == manifest['files'][name], 'Delta duplicated or wrong before hash')
        overrides[name] = row['after_sha256']
    for name, initial in manifest['files'].items():
        relative = relative_source(name)
        require(source_digest(source, relative) == overrides.get(name, initial), 'Snapshot bytes differ outside exact declared delta')
    for name, expected in pins.items():
        relative = relative_source(name)
        require(manifest['files'][name] == expected, 'Applied19 differs from tested source')
        require(source_digest(REPO, relative) == expected and source_digest(source, relative) == expected, 'Applied19 drift')
    for name, expected in go['config_input_pins'].items():
        require(name in {'frontend/playwright.auth.config.ts', 'frontend/vite.config.ts', 'backend/run.sh', 'backend/app/config.py'}, 'Unexpected config input')
        relative = relative_source(name)
        require(manifest['files'][name] == expected and source_digest(source, relative) == expected and source_digest(REPO, relative) == expected, 'Config drift')
    require(len(go['config_input_pins']) == 4, 'All four config inputs required')
    runtime = Path(go['new_preview_root']).resolve()
    require(runtime.parent == TASK.resolve() and runtime.name.startswith('preview-auth-') and not runtime.exists(), 'Preview must be fresh and owned')
    require(digest(STOP) == STOP_SHA, 'STOP changed during verification')
    return {
        'status': 'BOUND_PLAN_ONLY_NO_SERVER_OR_DB',
        'source': str(source), 'fresh_preview_root': str(runtime),
        'actual_full_head': head, 'initial_source_tree_sha256': manifest['source_tree_sha256'],
        'declared_PNG_delta_count': len(overrides),
        'qualification': 'Initial pre-check identity; final physical whole-tree equality is not asserted. Exact declared PNG delta separately verified; unlisted generated runtime artifacts are outside this declared source map.',
        'required_launch': {
            'lock': str(BUNDLE / '.run.lock'), 'lock_duration': 'preflight through all owned process-group cleanup',
            'ports': [5173, 8099], 'reuseExistingServer': False,
            'api_command': ['bash', 'run.sh'], 'frontend_command': ['npm', 'run', 'dev'],
            'with_worker': False, 'must_recheck_free_ports_before_launch': True,
            'database': str(runtime / 'runtime/checks.db'), 'fresh_SQLite_only': True,
            'settings': {'UNIMATCH_ENVIRONMENT': 'development', 'UNIMATCH_DEMO_MODE': 'true', 'UNIMATCH_AUTH_ENABLED': 'true', 'UNIMATCH_DATABASE_URL': f'sqlite:///{runtime / "runtime/checks.db"}', 'UNIMATCH_CACHE_DIR': str(runtime / 'runtime/httpcache'), 'UNIMATCH_EXPORT_DIR': str(runtime / 'runtime/exports'), 'UNIMATCH_CORS_ORIGINS': 'http://127.0.0.1:5173,http://localhost:5173', 'UNIMATCH_COOKIE_SECURE': 'false', 'UNIMATCH_SEARCH_PROVIDER': 'none', 'UNIMATCH_DECISION_PROVIDER': 'none', 'UNIMATCH_ENABLE_BROWSER_TIER': 'false', 'UNIMATCH_PAYMENTS_ENABLED': 'false', 'UNIMATCH_PASSWORD_RESET_ENABLED': 'false', 'UNIMATCH_PASSWORD_SCRYPT_LOG2': '14', 'UNIMATCH_AUTH_RATE_LIMIT_PER_MINUTE': '60'},
            'fixture': 'Empty DB migrated once by owned API startup; accounts/cases created later through local native UI only. No reused DB/seed.',
            'cleanup': 'Only saved owned PID groups; wait including surviving members; retain errors/logs/receipt; verify both ports free before releasing lock.'
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--go-receipt', type=Path, required=True)
    args = parser.parse_args()
    go_path = args.go_receipt.resolve()
    require(go_path.is_relative_to(TASK.resolve()), 'Go receipt must belong to this round')
    go = json.loads(go_path.read_text())
    # This read-only lock acquisition guards verification only. It is not a launch lease.
    with (BUNDLE / '.run.lock').open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(json.dumps(verify(go), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

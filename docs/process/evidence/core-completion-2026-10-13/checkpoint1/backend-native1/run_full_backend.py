"""Prepared, not executed: two FULL native backend gates, root-reviewed external lab only."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import pwd
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

PACKET = Path(__file__).resolve().parent
WORKSPACE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026')
SHARED_LOCK = WORKSPACE / 'local-runner/.run.lock'
PRIMARY = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials').resolve()

DIAGNOSTIC_TARGETS = ['tests/test_programme_observation_publication.py', 'tests/test_live_discovery.py', 'tests/test_university_catalogue.py', 'tests/test_worker.py']

def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def requirements() -> list[dict]:
    rows = json.loads((PACKET / 'asset-requirements.json').read_text())['entries']
    rows += json.loads((PACKET / 'transitive-requirements.json').read_text())['entries']
    return rows


def approved_assets() -> set[str]:
    return {r['path'] for r in requirements() if '/evaluation/research/' in r['path']}


def pins(source: Path) -> dict[str, str]:
    paths = set()
    for directory in ('backend/app', 'backend/tests', 'backend/scripts', 'backend/migrations'):
        paths.update(p for p in (source / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    # Pin evaluation CODE only, plus the explicitly approved immutable fixtures.
    paths.update(p for p in (source / 'backend/evaluation').rglob('*.py') if '__pycache__' not in p.parts)
    paths.update(source / r['path'] for r in requirements() if (source / r['path']).is_file())
    paths.update(source / p for p in (
        'backend/pytest.ini', 'backend/alembic.ini', 'backend/requirements.txt',
        'backend/requirements-dev.txt', '.dockerignore', 'backend/.dockerignore',
        '.github/workflows/benchmark-capture.yml', 'frontend/src/types.ts',
        'frontend/src/lib/format.ts', 'frontend/src/components/social.tsx',
    ))
    out = {}
    for p in sorted(paths):
        if p.is_symlink() or not p.resolve().is_relative_to(source):
            raise RuntimeError('Source symlink refused: ' + str(p.relative_to(source)))
        out[p.relative_to(source).as_posix()] = sha(p)
    return out


def preflight(source: Path) -> dict:
    issues = []
    if source == PRIMARY or source.is_relative_to(PRIMARY) or source.name != 'source':
        issues.append('Source must be an external lab /source, never primary')
    for forbidden in ('backend/.env', '.env', 'backend/data'):
        private_path = source / forbidden
        empty_git_placeholder = (forbidden == 'backend/data' and private_path.is_dir()
            and sorted(p.name for p in private_path.iterdir()) == ['.gitkeep']
            and (private_path / '.gitkeep').is_file()
            and not (private_path / '.gitkeep').is_symlink()
            and (private_path / '.gitkeep').stat().st_size == 0)
        if private_path.exists() and not empty_git_placeholder:
            issues.append('Forbidden source-private path present: ' + forbidden)
    expected = json.loads((PACKET / 'expected-native-source-pins.json').read_text())
    for relative, expected_sha in expected.items():
        p = source / relative
        if not p.is_file() or p.is_symlink() or sha(p) != expected_sha:
            issues.append('Sealed final native source drift/missing: ' + relative)
    for r in requirements():
        p = source / r['path']
        if not p.is_file():
            issues.append('Missing exact native prerequisite: ' + r['path'])
            continue
        metadata = r.get('frozen_blob_metadata', '').split()
        if metadata and (len(metadata) != 3 or metadata[1] != 'blob' or blob_sha(p) != metadata[0]):
            issues.append('Frozen native prerequisite differs: ' + r['path'])
    for directory in ('backend/tests/fixtures', 'backend/app/corpus/pages', 'backend/migrations/versions'):
        if not (source / directory).is_dir() or not any((source / directory).iterdir()):
            issues.append('Missing native fixture/migration directory: ' + directory)
    # Never let native corpus_dir build fixtures into the pinned source tree.
    if not (source / 'backend/app/corpus/pages/u-groningen/fees.pdf').is_file():
        issues.append('Synthetic corpus PDF is required; do not build during gate')
    venv = source / 'backend/.venv'
    python = venv / 'bin/python'
    if not python.is_file():
        issues.append('Existing interpreter missing; installation is outside this helper')
    site = venv / 'lib/python3.12/site-packages'
    distributions = {}
    for name in ('pytest', 'pytest_cov', 'pytest_asyncio', 'coverage', 'pgserver', 'psycopg', 'psycopg_binary', 'SQLAlchemy', 'alembic', 'fasteners', 'psutil', 'urllib3'):
        found = sorted(p for p in site.glob('*.dist-info/METADATA') if p.parent.name.lower().startswith(name.replace('-', '_').lower() + '-'))
        if not found:
            issues.append('Installed metadata missing: ' + name)
        else:
            distributions[name] = {'metadata_path': str(found[-1].resolve()), 'sha256': sha(found[-1])}
    pg_bin = site / 'pgserver/pginstall/bin'
    binaries = {}
    for name in ('postgres', 'initdb', 'pg_ctl'):
        p = pg_bin / name
        if not p.is_file() or not os.access(p, os.X_OK):
            issues.append('Bundled executable missing: ' + name)
        else:
            binaries[name] = {'path': str(p.resolve()), 'sha256': sha(p)}
    if sys.platform != 'darwin' or not Path('/usr/bin/sandbox-exec').is_file():
        issues.append('Reviewed macOS inherited sandbox launcher unavailable; no network fallback')
    return {'issues': issues, 'ready_for_root_execution': not issues,
            'python': str(python), 'pg_bin': str(pg_bin.resolve()),
            'distributions': distributions, 'binaries': binaries,
            'isolation_status': 'PROPOSED_NOT_EXECUTED; negative OS and positive private PG probes required before pytest',
            'native_fixture_semantics': 'Both phases retain explicit SQLite and PostgreSQL native fixtures. PG phase changes default Settings DB only.'}


def profile(runtime: Path) -> str:
    prefix = json.dumps(str(runtime) + '/')
    return '\n'.join((
        '(version 1)', '(allow default)', '(deny network*)',
        f'(allow network-bind (local unix-socket (path-prefix {prefix})))',
        f'(allow network-outbound (remote unix-socket (path-prefix {prefix})))',
        f'(allow network-inbound (local unix-socket (path-prefix {prefix})))',
        '',
    ))


def run_child(argv: list[str], cwd: Path, env: dict, output: Path, timeout: int) -> dict:
    started = time.monotonic()
    timed_out = False
    with output.open('w') as log:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                returncode = proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                returncode = proc.wait(timeout=10)
        except BaseException:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
            raise
    return {'argv': argv, 'exit_code': returncode, 'timed_out': timed_out,
            'duration_seconds': round(time.monotonic() - started, 3), 'log_sha256': sha(output)}


def stop_owned_clusters(runtime: Path, pg_bin: Path, evidence: Path, env: dict) -> dict:
    import psutil  # installed dependency, no app/provider/config import

    rows = []
    for marker in sorted(runtime.rglob('postmaster.pid')):
        data = marker.parent.resolve()
        if not data.is_relative_to(runtime):
            rows.append({'pgdata': str(data), 'error': 'outside runtime; no stop attempted'})
            continue
        try:
            lines = marker.read_text().splitlines()
            pid = int(lines[0])
            if Path(lines[1]).resolve() != data:
                raise RuntimeError('PID file data directory mismatch')
            if not psutil.pid_exists(pid):
                rows.append({'pgdata': str(data), 'already_stopped': True})
                continue
            process = psutil.Process(pid)
            command = process.cmdline()
            owned = (process.uids().real == os.getuid() and command
                     and Path(command[0]).resolve() == (pg_bin / 'postgres').resolve()
                     and '-D' in command and Path(command[command.index('-D') + 1]).resolve() == data)
            if not owned:
                raise RuntimeError('Process ownership/executable/data directory not proven; no stop attempted')
            receipt = run_child([str(pg_bin / 'pg_ctl'), '-D', str(data), 'stop', '-m', 'fast', '-w', '-t', '10'],
                                data, env, evidence / f'cleanup-{pid}.log', 15)
            rows.append({'pgdata': str(data), 'pid': pid, **receipt})
        except Exception as exc:
            rows.append({'pgdata': str(data), 'error': str(exc)})
    remaining = []
    for marker in runtime.rglob('postmaster.pid'):
        try:
            pid = int(marker.read_text().splitlines()[0])
            if psutil.pid_exists(pid):
                remaining.append(str(marker))
        except (OSError, ValueError, IndexError):
            remaining.append(str(marker))
    stopped = not remaining and not any('error' in row or row.get('exit_code', 0) != 0 for row in rows)
    return {'owned_cluster_cleanup': rows, 'active_cluster_markers': remaining, 'shutdown_confirmed': stopped}


def junit_summary(path: Path) -> dict:
    if not path.is_file():
        return {'missing': True}
    cases = list(ET.parse(path).getroot().iter('testcase'))
    return {'tests': len(cases), 'failures': sum(c.find('failure') is not None for c in cases),
            'errors': sum(c.find('error') is not None for c in cases),
            'skips': sum(c.find('skipped') is not None for c in cases), 'sha256': sha(path)}


def phase(name: str, source: Path, output: Path, check: dict, timeout: int, diagnostic: bool = False) -> dict:
    evidence = output / name
    evidence.mkdir()
    runtime = Path(tempfile.mkdtemp(prefix='um-full-', dir='/tmp')).resolve()
    runtime.chmod(0o700)
    for sub in ('tmp', 'home', 'pg-config', 'cache', 'exports'):
        (runtime / sub).mkdir(mode=0o700)
    (runtime / 'empty.pgpass').write_bytes(b'')
    (runtime / 'empty.pgpass').chmod(0o600)
    username = pwd.getpwuid(os.getuid()).pw_name
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8',
           'HOME': str(runtime / 'home'), 'USER': username, 'LOGNAME': username,
           'PYTHONPATH': os.pathsep.join((str(PACKET), str(source / 'backend'))),
           'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
           'TMPDIR': str(runtime / 'tmp'), 'PGPASSFILE': str(runtime / 'empty.pgpass'),
           'PGSYSCONFDIR': str(runtime / 'pg-config'), 'COVERAGE_FILE': str(evidence / '.coverage'),
           'FULL_BACKEND_RUNTIME': str(runtime), 'FULL_BACKEND_EVIDENCE': str(evidence),
           'FULL_BACKEND_SOURCE': str(source), 'FULL_BACKEND_PHASE': name,
           'FULL_BACKEND_ALLOWED_ASSETS': json.dumps(sorted(approved_assets())),
           'FULL_BACKEND_ARM_GUARD': '1',
           'UNIMATCH_DATABASE_URL': f'sqlite:///{runtime / "bootstrap.db"}',
           'UNIMATCH_DEMO_MODE': 'true', 'UNIMATCH_SEARCH_PROVIDER': 'none',
           'UNIMATCH_ENABLE_BROWSER_TIER': 'false', 'UNIMATCH_AUTH_ENABLED': 'false',
           'UNIMATCH_PAYMENTS_ENABLED': 'false', 'UNIMATCH_CACHE_DIR': str(runtime / 'cache'),
           'UNIMATCH_EXPORT_DIR': str(runtime / 'exports'),
           'UNIMATCH_CORPUS_DIR': str(source / 'backend/app/corpus/pages')}
    sb = evidence / 'network.sb'
    sb.write_text(profile(runtime))
    before = pins(source)
    write_json(evidence / 'source-before.json', before)
    receipt = {'phase': name, 'runtime': str(runtime), 'mode': 'FOCUSED_DIAGNOSTIC_NOT_FULL' if diagnostic else 'FULL_NATIVE', 'scope': 'Focused native harness controls; NOT a full gate or coverage proof' if diagnostic else 'FULL unchanged native backend tests; historical offline contract replay, not search quality'}
    try:
        # -I excludes sitecustomize/PYTHONPATH: probe the inherited OS restriction,
        # rather than mistaking our Python guard for an OS-level result.
        negative = run_child(['/usr/bin/sandbox-exec', '-f', str(sb), check['python'], '-I',
                              str(PACKET / 'os_network_probe.py'), str(evidence / 'os-network-probe.json')],
                             source / 'backend', env, evidence / 'os-network-probe.log', 15)
        receipt['os_probe'] = negative
        if negative['exit_code'] != 0:
            receipt['status'] = 'BLOCKED_ISOLATION'; return receipt
        coverage_args = [] if diagnostic else [
            '--cov=app', '--cov-fail-under=92', '--cov-report=term-missing',
            '--cov-report=json:' + str(evidence / 'coverage.json'),
            '--cov-report=xml:' + str(evidence / 'coverage.xml')]
        argv = ['/usr/bin/sandbox-exec', '-f', str(sb), check['python'], str(PACKET / 'pytest_full.py'),
                *(DIAGNOSTIC_TARGETS if diagnostic else ['tests']), *coverage_args,
                '--junitxml=' + str(evidence / 'junit.xml'), '--tb=short',
                '--basetemp=' + str(runtime / 'tmp/pytest'), '-p', 'no:cacheprovider',
                '-p', 'pytest_cov.plugin', '-p', 'pytest_asyncio.plugin', '-p', 'mock_endpoint_plugin']
        receipt['pytest'] = run_child(argv, source / 'backend', env, evidence / 'pytest.log', timeout)
        receipt['junit'] = junit_summary(evidence / 'junit.xml')
        coverage = evidence / 'coverage.json'
        receipt['coverage_percent'] = json.loads(coverage.read_text()).get('totals', {}).get('percent_covered') if coverage.exists() else None
        guards = [json.loads(p.read_text()) for p in evidence.glob('guard-*.json')]
        receipt['outside_attempts'] = [a for g in guards for a in g.get('outside_attempts', [])]
        receipt['guard_startup_failures'] = [p.name for p in evidence.glob('guard-startup-failed-*.json')]
        receipt['guard_receipts'] = len(guards)
        receipt['pg_connection_events'] = sum(len(g.get('allowed_pg_connections', [])) for g in guards)
        receipt['ipv6_trait_restored'] = bool(guards) and all(g.get('ipv6_trait_restored') for g in guards)
        receipt['app_preimported'] = any(g.get('app_preimported') for g in guards)
        receipt['status'] = 'EXECUTED_PENDING_RECEIPT_VALIDATION'
    except Exception as exc:
        receipt['status'] = 'HARNESS_ERROR'
        receipt['harness_error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        after = pins(source)
        write_json(evidence / 'source-after.json', after)
        receipt['source_unchanged_during_gate'] = before == after
        cleanup = stop_owned_clusters(runtime, Path(check['pg_bin']), evidence, env)
        receipt.update(cleanup)
        if cleanup['shutdown_confirmed']:
            shutil.rmtree(runtime)
        receipt['runtime_removed'] = not runtime.exists()
        if receipt.get('status') == 'EXECUTED_PENDING_RECEIPT_VALIDATION':
            j = receipt['junit']; cov = receipt['coverage_percent']
            accepted = (receipt['pytest']['exit_code'] == 0 and not receipt['pytest']['timed_out']
                        and j.get('tests', 0) > 0 and j.get('failures', 1) == 0 and j.get('errors', 1) == 0
                        and j.get('skips', 1) == 0 and (diagnostic or (cov is not None and cov >= 92))
                        and not receipt['outside_attempts'] and not receipt['guard_startup_failures']
                        and receipt['guard_receipts'] > 0 and receipt['ipv6_trait_restored']
                        and not receipt['app_preimported'] and receipt['pg_connection_events'] > 0
                        and before == after and receipt['shutdown_confirmed'] and receipt['runtime_removed'])
            receipt['status'] = ('FOCUSED_DIAGNOSTIC_PASS_NOT_FULL' if accepted else 'FOCUSED_DIAGNOSTIC_FAIL_NOT_FULL') if diagnostic else ('PASS' if accepted else 'FAIL_OR_INCOMPLETE')
        receipt['evidence_hashes'] = {p.name: sha(p) for p in evidence.iterdir() if p.is_file() and p.name != 'result.json'}
        write_json(evidence / 'result.json', receipt)
    return receipt


def main() -> int:
    os.umask(0o077)  # raw native logs may contain fixture assertion details; keep them private
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--output-root', required=True, type=Path)
    parser.add_argument('--diagnostic', action='store_true', help='Fixed focused native harness controls only; no full/coverage PASS claim')
    parser.add_argument('--execute', action='store_true', help='Root review/authorization; default is static preflight only')
    parser.add_argument('--phase-timeout', type=int, default=1800)
    args = parser.parse_args()
    if not 60 <= args.phase_timeout <= 3600:
        parser.error('phase timeout must be 60..3600 seconds')
    source = args.source_root.resolve(); output_parent = args.output_root.resolve()
    if output_parent == source or output_parent.is_relative_to(source) or output_parent.is_relative_to(PRIMARY):
        parser.error('Evidence must be outside source and primary')
    lock = None
    if args.execute:
        # Never truncate, unlink, replace, or overwrite another runner's lock.
        lock = SHARED_LOCK.open('r+')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close(); print('BLOCKED_QUEUE: shared local-runner lock is held; no execution started', flush=True); return 75
    try:
        output = output_parent / datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')
        output.mkdir(parents=True)
        check = preflight(source)
        write_json(output / 'preflight.json', check)
        write_json(output / 'helper-pins.json', {p.name: sha(p) for p in PACKET.iterdir() if p.is_file()})
        if check['issues']:
            write_json(output / 'result.json', {'status': 'BLOCKED_PREREQUISITE', 'issues': check['issues'], 'executed': False})
            print('BLOCKED_PREREQUISITE: ' + str(output), flush=True); return 2
        if not args.execute:
            write_json(output / 'result.json', {'status': 'PREPARED_NOT_EXECUTED', 'executed': False})
            print('PREPARED_NOT_EXECUTED: ' + str(output), flush=True); return 0
        results = []
        for name in (('sqlite',) if args.diagnostic else ('sqlite', 'postgres')):
            print('Starting full native backend phase: ' + name, flush=True)
            result = phase(name, source, output, check, min(args.phase_timeout, 300) if args.diagnostic else args.phase_timeout, args.diagnostic)
            results.append(result)
            print('Finished ' + name + ': ' + result['status'], flush=True)
            if result['status'] != 'PASS':
                break  # no silent retries, phase two remains NOT_RUN on phase-one failure
        status = ('FOCUSED_DIAGNOSTIC_PASS_NOT_FULL' if results and results[0]['status'] == 'FOCUSED_DIAGNOSTIC_PASS_NOT_FULL' else 'FOCUSED_DIAGNOSTIC_FAIL_NOT_FULL') if args.diagnostic else ('PASS' if len(results) == 2 and all(r['status'] == 'PASS' for r in results) else 'FAIL_OR_INCOMPLETE')
        write_json(output / 'result.json', {'status': status, 'phases': results,
                    'postgres_if_not_started': 'NOT_RUN', 'primary_modified': False,
                    'current_search_quality': 'NOT_MEASURED; existing GLOBAL_PROVIDER_STOP/UNSCORED remains closed'})
        print(status + ': ' + str(output), flush=True)
        return 0 if status in ('PASS', 'FOCUSED_DIAGNOSTIC_PASS_NOT_FULL') else 2
    finally:
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_UN); lock.close()


if __name__ == '__main__':
    raise SystemExit(main())

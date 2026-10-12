"""External isolated runner; imports/executes no app code in the parent."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/source')
FRONTEND = SOURCE / 'frontend'
BACKEND = SOURCE / 'backend'
NODE = Path('/Users/wpalish/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
PYTHON = BACKEND / '.venv/bin/python'
suite = sys.argv[1]
assert suite in {'demo', 'auth', 'ux'}
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
runtime = ROOT / 'evidence' / 'e2e' / f'{stamp}-{suite}'
runtime.mkdir(parents=True)
for directory in ('frontend', 'docs/screenshots', 'tmp', 'cache', 'exports'):
    (runtime / directory).mkdir(parents=True)
snapshot = runtime / 'harness'; snapshot.mkdir()
harness_pins = {}
for path in sorted((ROOT / 'e2e').iterdir()):
    if path.is_file():
        shutil.copyfile(path, snapshot / path.name)
        harness_pins[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
(runtime / 'harness-before.json').write_text(json.dumps(harness_pins, indent=2) + '\n')


def ports() -> subprocess.CompletedProcess[str]:
    return subprocess.run(['/usr/sbin/lsof', '-nP', '-iTCP:5229', '-iTCP:8139',
                           '-sTCP:LISTEN'], text=True, capture_output=True)


def source_pins() -> dict[str, str]:
    # Only retained app/native test/config source. Never inspect omitted
    # research, held-out, labels, scorer, baseline or expert payloads.
    paths = [p for prefix in ('frontend/src', 'frontend/e2e', 'backend/app',
                              'backend/migrations')
             for p in (SOURCE / prefix).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    paths += [SOURCE / name for name in (
        'frontend/playwright.config.ts', 'frontend/playwright.auth.config.ts',
        'frontend/vite.config.ts', 'frontend/package.json', 'frontend/package-lock.json',
        'frontend/index.html', 'backend/run.sh', 'backend/alembic.ini',
        'backend/pyproject.toml') if (SOURCE / name).is_file()]
    return {str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths))}


before = source_pins()
(runtime / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
assert not (BACKEND / '.env').exists()
assert not (FRONTEND / '.env').exists()
listeners = ports()
(runtime / 'ports-before.log').write_text(listeners.stdout + listeners.stderr)
assert listeners.returncode == 1 and not listeners.stdout.strip(), 'Foreign port occupied: STOP'

native_config = FRONTEND / ('playwright.auth.config.ts' if suite == 'auth' else 'playwright.config.ts')
config = runtime / 'playwright.config.mts'
child = ROOT / 'e2e/runtime-child.py'
import shlex
webservers = [
    {'command': ' '.join(map(shlex.quote, [str(PYTHON), str(child), mode, str(runtime)])),
     'cwd': str(FRONTEND), 'url': f'http://127.0.0.1:{port}' + ('/api/health' if mode == 'backend' else ''),
     'reuseExistingServer': False, 'timeout': 90000 if mode == 'backend' and suite == 'auth' else 60000,
     'stdout': 'pipe', 'stderr': 'pipe'}
    for mode, port in [('backend', 8139), ('frontend', 5229)]
]
config.write_text(
    f'import native from {json.dumps(str(native_config))};\n'
    'export default { ...native,\n'
    f' testDir: {json.dumps(str(ROOT / "e2e" if suite == "ux" else FRONTEND / "e2e"))},\n'
    + (' testMatch: "ux-observations.spec.ts", projects: [native.projects[0]],\n' if suite == 'ux' else '')
    +
    f' outputDir: {json.dumps(str(runtime / "test-results"))},\n'
    ' use: { ...native.use, baseURL: "http://127.0.0.1:5229" },\n'
    f' reporter: [["list"],["html",{{open:"never",outputFolder:{json.dumps(str(runtime / "playwright-report"))}}}],'
    f'["junit",{{outputFile:{json.dumps(str(runtime / "junit.xml"))}}}]],\n'
    f' webServer: {json.dumps(webservers)},\n'
    '};\n')
(runtime / 'vite.config.ts').write_text(
    f'import native from {json.dumps(str(FRONTEND / "vite.config.ts"))};\n'
    'export default { ...native,\n'
    f' cacheDir: {json.dumps(str(runtime / "vite-cache"))},\n'
    ' server: {...native.server,host:"127.0.0.1",port:5229,strictPort:true,\n'
    f' fs:{{...native.server?.fs,allow:[...(native.server?.fs?.allow ?? []),{json.dumps(str(FRONTEND))},{json.dumps(str((FRONTEND / "node_modules/@fontsource/inter").resolve()))},{json.dumps(str((FRONTEND / "node_modules/@fontsource/jetbrains-mono").resolve()))}]}},\n'
    ' proxy:{"/api":{target:"http://127.0.0.1:8139",changeOrigin:true}}},\n'
    '};\n')
env = {
    'PATH': str(NODE.parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
    'LANG': 'en_US.UTF-8', 'TMPDIR': str(runtime / 'tmp'),
    'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1',
    'PLAYWRIGHT_BROWSERS_PATH': '/Users/wpalish/Library/Caches/ms-playwright',
    'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD': '1',
    'PORT': '8139',
    'UNIMATCH_DATABASE_URL': f'sqlite:///{runtime / "synthetic.db"}',
    'UNIMATCH_CACHE_DIR': str(runtime / 'cache'),
    'UNIMATCH_EXPORT_DIR': str(runtime / 'exports'),
    'UNIMATCH_CORPUS_DIR': str(BACKEND / 'app/corpus/pages'),
    'UNIMATCH_ENVIRONMENT': 'development',
    'UNIMATCH_AUTO_MIGRATE': 'false', 'UNIMATCH_DEMO_MODE': 'true',
    'UNIMATCH_AUTH_ENABLED': 'true' if suite == 'auth' else 'false',
    'UNIMATCH_SEARCH_PROVIDER': 'none', 'UNIMATCH_DECISION_PROVIDER': 'none',
    'UNIMATCH_PAYMENTS_ENABLED': 'false', 'UNIMATCH_PAYMENTS_PROVIDER': 'fake',
    'UNIMATCH_EMAIL_SENDER': 'console', 'UNIMATCH_METRICS_ENABLED': 'false',
    'UNIMATCH_ENABLE_BROWSER_TIER': 'false',
    'UNIMATCH_CORS_ORIGINS': 'http://127.0.0.1:5229',
    'UNIMATCH_PUBLIC_BASE_URL': 'http://127.0.0.1:5229',
}
if suite == 'auth':
    # Preserve the native auth config's test-only cost and rate settings.
    env.update(UNIMATCH_PASSWORD_SCRYPT_LOG2='14', UNIMATCH_AUTH_RATE_LIMIT_PER_MINUTE='60')
(runtime / 'synthetic-environment.json').write_text(json.dumps(env, indent=2) + '\n')
command = ['/usr/bin/sandbox-exec', '-f', str(ROOT / 'e2e/loopback-only.sb'),
           str(NODE), str(FRONTEND / 'node_modules/@playwright/test/cli.js'),
           'test', '--config', str(config)]
receipt = {'suite': suite, 'runtime': str(runtime), 'command': command,
           'cwd': str(runtime / 'frontend'), 'native_config': str(native_config),
           'source_count': len(before), 'mock_routes_or_apis': False,
           'providers': 'none', 'demo_lifespan_and_worker': True}
if suite == 'demo':
    # One explicitly labelled fault control forwards the actual loopback PUT,
    # records its real accepted receipt, then hides only that UI response.
    receipt['network_fault_control'] = {
        'scope': 'one owned shared-route PUT in native Demo recovery test',
        'forwarded_actual_loopback_api': True,
        'fault': 'abort UI delivery after observed real server receipt',
        'fabricated_response_or_receipt': False,
        'automatic_client_PUT_retry_permitted': False,
    }
if suite == 'ux':
    receipt['count_scope'] = 'separate diagnostic observations; not native E2E'
    receipt['mock_routes_or_apis'] = 'save diagnostic only: imposed delay forwards real API; injected abort explicitly labelled'
(runtime / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('RUN_ROOT=' + str(runtime), flush=True)
with (runtime / 'test.log').open('w') as log:
    process = subprocess.Popen(command, cwd=runtime / 'frontend', env=env,
                               stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    receipt['runner_pid'] = process.pid
    (runtime / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
    try:
        code = process.wait()
    except BaseException:
        os.killpg(process.pid, signal.SIGTERM)
        raise
    finally:
        # Native Playwright owns each webServer wrapper. Independently clean
        # only groups created and recorded by our wrappers in this runtime.
        cleaned = []
        for file in runtime.glob('*-process.json'):
            owner = json.loads(file.read_text())
            assert Path(owner['cwd']).is_relative_to(SOURCE)
            group = owner['pgid']
            try:
                os.killpg(group, signal.SIGTERM)
                cleaned.append({'pgid': group, 'signal': 'SIGTERM'})
            except ProcessLookupError:
                cleaned.append({'pgid': group, 'already_gone': True})
        (runtime / 'owned-cleanup.json').write_text(json.dumps(cleaned, indent=2) + '\n')
        # Uvicorn may need a brief grace period after group termination. Do
        # not confuse an in-progress owned shutdown with a foreign listener.
        time.sleep(0.5)
after = source_pins()
(runtime / 'source-after.json').write_text(json.dumps(after, indent=2) + '\n')
receipt.update(exit_code=code, source_unchanged=before == after)
listeners = ports()
(runtime / 'ports-after.log').write_text(listeners.stdout + listeners.stderr)
receipt['ports_clear_after'] = listeners.returncode == 1 and not listeners.stdout.strip()
(runtime / 'run.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2), flush=True)
sys.exit(code if receipt['source_unchanged'] and receipt['ports_clear_after'] else 2)

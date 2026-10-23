"""Owned normal imports, denied real transports, only isolated SQLite allowed."""
from pathlib import Path
import importlib
import json
import os
import socket
import sqlite3
import subprocess
import sys

OWN = Path(__file__).resolve().parents[1]
mode = sys.argv[1]
assert mode in {'off', 'on'}
sys.path.insert(0, str(OWN / 'runtime' / mode / 'backend'))
counts = {'dns': 0, 'connect': 0, 'listen': 0, 'child': 0, 'forbidden_DB': 0, 'owned_SQLite_connect': 0}


def denied(kind):
    def reject(*args, **kwargs):
        counts[kind] += 1
        raise AssertionError('DENIED_' + kind)
    return reject


socket.getaddrinfo = denied('dns')
socket.socket.connect = denied('connect')
socket.socket.connect_ex = denied('connect')
socket.socket.listen = denied('listen')
subprocess.Popen = denied('child')
original_connect = sqlite3.connect


def own_connect(database, *args, **kwargs):
    target = Path(str(database)).resolve()
    if not target.is_relative_to((OWN / 'runtime').resolve()):
        counts['forbidden_DB'] += 1
        raise AssertionError('Only owned SQLite path admitted')
    counts['owned_SQLite_connect'] += 1
    return original_connect(database, *args, **kwargs)


sqlite3.connect = own_connect
sqlite3.dbapi2.connect = own_connect
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
attempt = sys.argv[2] if len(sys.argv) > 2 else 'attempt1'
assert attempt in {'attempt1', 'attempt2', 'attempt3'}
logs = OWN / 'logs' / (mode + '-' + attempt)
logs.mkdir(exist_ok=False)
os.environ['OWN_OBSERVATIONS'] = str(logs)
os.environ['REJECTED_DIAGNOSTICS_PROOF_MODE'] = mode
os.environ['REJECTED_DIAGNOSTICS_PROOF_DIR'] = str(logs)
pytest = importlib.import_module('pytest')
try:
    code = pytest.main([
        str(OWN / 'harness/test_author_groups.py'),
        str(OWN / 'harness/test_corrected_hop.py') + '::TestPoisonedRedirectHops::test_a_credential_in_a_hop_query_is_refused_not_fetched',
        str(OWN / 'harness/test_independent_persistence.py'),
        '-q', '-ra', '--tb=short', '-p', 'pytest_asyncio.plugin', '-o', 'asyncio_mode=auto',
        '--confcutdir=' + str(OWN / 'harness'), '--basetemp=' + str(OWN / 'runtime' / mode / 'temporary'),
        '--junitxml=' + str(logs / 'junit.xml'),
    ])
finally:
    (logs / 'guard.json').write_text(json.dumps(counts, indent=2) + '\n')
assert all(v == 0 for k, v in counts.items() if k != 'owned_SQLite_connect'), counts
sys.exit(code)

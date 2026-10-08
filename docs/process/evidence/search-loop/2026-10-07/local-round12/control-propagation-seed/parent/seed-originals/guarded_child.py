"""Owner-authorized candidate synthetic seed; no real socket or DNS allowed."""
from __future__ import annotations

import hashlib
import json
import os
import runpy
import socket
import sqlite3
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'candidate'
BACKEND = SOURCE / 'backend'
ACTION = sys.argv[1]
assert ACTION in {'heads', 'migrate', 'seed', 'inspect'}
assert Path.cwd() == BACKEND
assert not (BACKEND / '.env').exists() and not (BACKEND / '.env').is_symlink()
DB = ROOT / 'runtime/seed.db'
assert os.environ['UNIMATCH_DATABASE_URL'] == f'sqlite:///{DB}'
assert os.environ['UNIMATCH_CACHE_DIR'] == str(ROOT / 'runtime/httpcache')
assert os.environ['UNIMATCH_EXPORT_DIR'] == str(ROOT / 'runtime/exports')
assert os.environ['UNIMATCH_DEMO_MODE'] == 'true'
assert os.environ['UNIMATCH_ENABLE_BROWSER_TIER'] == 'false'
assert os.environ['UNIMATCH_SEARCH_PROVIDER'] == 'none'
PINS = json.loads((ROOT / 'candidate-source-pins.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = {rel: sha(SOURCE / rel) for rel in PINS}
assert before == PINS
sys.path.insert(0, str(BACKEND))
attempts = []


def deny(*args, **kwargs):
    attempts.append('forbidden real network or DNS')
    raise AssertionError('Synthetic seed denied network')


socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
socket.getaddrinfo = deny

code = 0
try:
    if ACTION in {'heads', 'migrate'}:
        sys.argv = ['alembic', '-c', str(BACKEND / 'alembic.ini')]
        sys.argv += ['heads'] if ACTION == 'heads' else ['upgrade', 'head']
        runpy.run_module('alembic', run_name='__main__')
    elif ACTION == 'seed':
        sys.argv = [str(BACKEND / 'seed_demo.py')]
        runpy.run_path(str(BACKEND / 'seed_demo.py'), run_name='__main__')
    else:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        config = Config(str(BACKEND / 'alembic.ini'))
        config.set_main_option('script_location', str(BACKEND / 'migrations'))
        heads = ScriptDirectory.from_config(config).get_heads()
        assert len(heads) == 1
        assert DB.is_file()
        with sqlite3.connect(f'file:{DB}?mode=ro', uri=True) as con:
            current = [r[0] for r in con.execute('SELECT version_num FROM alembic_version')]
            assert current == heads
            rows = con.execute('SELECT university,funding_classification,bucket,user_decision FROM program_results ORDER BY score_total DESC').fetchall()
            runs = con.execute('SELECT stage,pages_checked,pages_failed,claims_recorded FROM research_runs').fetchall()
        assert len(runs) == 1
        assert rows and rows[0][0] == 'University of Groningen'
        ubc = [r for r in rows if r[0] == 'University of British Columbia']
        assert len(ubc) == 1 and ubc[0][2] == 'OUT_OF_BUDGET'
        assert all(r[3] == 'undecided' for r in rows)
        result = {'heads': heads, 'database_revisions': current, 'rows': len(rows),
                  'first': rows[0][0], 'UBC': {'university': ubc[0][0], 'funding_classification': ubc[0][1], 'portfolio_bucket': ubc[0][2]},
                  'run': {'stage': runs[0][0], 'pages_checked': runs[0][1], 'pages_failed': runs[0][2], 'claims_recorded': runs[0][3]},
                  'all_undecided_no_approve': True, 'qualification': 'Synthetic demo ordering; no live university or quality evidence.'}
        target = ROOT / 'inspection.original.json'
        assert not target.exists()
        target.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
except SystemExit as error:
    code = int(error.code or 0)
except BaseException:
    traceback.print_exc()
    code = 1
after = {rel: sha(SOURCE / rel) for rel in PINS}
if attempts or after != before:
    code = code or 2
record = {'action': ACTION, 'exit_code': code, 'network_attempts': attempts,
          'candidate_pins_pre_post_equal': before == after,
          'candidate_pin_count': len(PINS), 'candidate_app_files': sum(rel.startswith('backend/app/') for rel in PINS),
          'cwd': str(BACKEND), 'own_database': str(DB),
          'flags': {'demo': True, 'browser': False, 'provider': 'none'},
          'qualification': 'Synthetic candidate source only; final accepted app binding separate.'}
target = ROOT / f'{ACTION}.execution.json'
assert not target.exists()
target.write_text(json.dumps(record, indent=2)+'\n')
sys.exit(code)

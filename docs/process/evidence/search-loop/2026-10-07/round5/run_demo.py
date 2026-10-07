"""Offline final-source demo, isolated database, retained complete logs."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

WORK = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work')
REPO = WORK / 'ashyq-apply'
OUT = WORK / 'search-loop-round5/gates'
LINK = REPO / 'backend/.env'
TARGET = LINK.resolve()
assert LINK.is_symlink()
env = dict(os.environ, UNIMATCH_DATABASE_URL='sqlite:///' + str(OUT / 'demo.sqlite'),
           UNIMATCH_DEMO_MODE='true', UNIMATCH_ENABLE_BROWSER_TIER='false',
           UNIMATCH_SEARCH_PROVIDER='none', UNIMATCH_DECISION_PROVIDER='none')
assert not (OUT / 'demo.sqlite').exists()
LINK.unlink()
commands = []
try:
    for name, args in [('demo-migration', ['.venv/bin/alembic', 'upgrade', 'head']),
                       ('demo', ['.venv/bin/python', 'seed_demo.py'])]:
        with (OUT / (name + '.log')).open('w') as log:
            result = subprocess.run(args, cwd=REPO/'backend', env=env,
                                    stdout=log, stderr=subprocess.STDOUT)
        commands.append({'name': name, 'exit_code': result.returncode})
        assert result.returncode == 0, name
finally:
    LINK.symlink_to(TARGET)
def stable(path):
    return '\n'.join(path.read_text().splitlines()[2:])
before = WORK / 'search-loop-round3/gates/demo.log'
assert stable(before) == stable(OUT / 'demo.log')
record = {'commands': commands, 'dotenv_restored': LINK.is_symlink(),
          'comparison': 'stage/counts/20 result rows byte-identical to preceding green source',
          'stable_output_sha256': hashlib.sha256(stable(before).encode()).hexdigest(),
          'groningen_first': True, 'ubc_legacy_vocabulary_caveat': 'unchanged; see prior source acceptance',
          'database_archived': False}
(OUT / 'demo-comparison.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))

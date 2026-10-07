"""Bounded rejected-proposal archive; no application edits or runtime databases."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from dotenv import dotenv_values

TASK = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = TASK / 'work/ashyq-apply'
ROUND = TASK / 'work/search-loop-round4'
OUT = REPO / 'docs/process/evidence/search-loop/2026-10-07/round4/rejected-readguard-b603'
private_values = [
    value.encode() for key, value in dotenv_values(REPO / 'backend/.env').items()
    if value and len(value) >= 12 and any(word in key.upper() for word in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD'))
]

def copy_file(source: Path, destination: Path) -> None:
    assert source.is_file() and not source.is_symlink()
    assert source.suffix not in {'.db', '.sqlite', '.sqlite3', '.pyc'}
    assert not source.name.endswith(('-wal', '-shm'))
    data = source.read_bytes()
    if any(value in data for value in private_values):
        raise RuntimeError('Known secret detected; archive stopped')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert destination.read_bytes() == data, 'Immutable archive cannot be replaced'
    else:
        shutil.copy2(source, destination)

a = ROUND / 'reviews/expert_a-readguard'
plan = json.loads((a / 'bundle-files.json').read_text())
for relative in plan['include']:
    copy_file(a / relative, OUT / 'independent_a' / relative)

b = ROUND / 'reviews/expert_b-readguard'
for path in sorted(b.rglob('*')):
    if not path.is_file() or path.is_symlink():
        continue
    relative = path.relative_to(b)
    if len(relative.parts) > 1 and relative.parts[0] not in {'original', 'proposed', 'rejected-no-sqlite-write-lock'}:
        continue
    if any(part.startswith('.') or part == '__pycache__' or part.startswith('pytest-') for part in relative.parts[:-1]):
        continue
    if path.suffix in {'.db', '.sqlite', '.sqlite3', '.pyc'} or path.name.endswith(('-wal', '-shm')):
        continue
    copy_file(path, OUT / 'author_b' / relative)

parent = ROUND / 'reviews/parent-frozen-readguard-review'
for path in sorted(parent.iterdir()):
    if path.is_file():
        copy_file(path, OUT / 'parent' / path.name)
for name in ['root_review_checkpoint.py', 'archive_rejected_readguard.py']:
    copy_file(ROUND / name, OUT / 'parent' / name)

(OUT / 'README.md').write_text(
    '# Rejected production read-budget candidate b603fe6a\n\n'
    'This is an immutable review checkpoint, not applied production code. Exact author manifest '
    'b603fe6a75660679e39b1b59545e21aae3aac79793ef2ae5d84c1ec6dc483a31 and patch '
    'c09219f02f30a89ec083484868586264f91cabb89eb8cb7e80c0e30221b8b0f7 were rejected by A/root '
    'after independent actual SQLite controls.\n\n'
    'First-namespace race: stale guard-off settings replacement removes committed count60, '
    'then the on runner admits original get61 and persists count1. Duplicate same Job/worker/attempt '
    'is synthetic; ordinary worker reachability is unproved. This still prevents a universal durable-cap claim. '
    'Busy real verification caller: zero original get and unchanged prior ClaimRow/ProgramResult, '
    'but OperationalError escapes and durable unknown is absent. A deliberate cap red is retained; '
    'it is not a green result. Author70 tests and other independent6 controls pass.\n\n'
    'The earlier author SQLite no-write-lock proposal (two get/count1), failed fixtures and raw logs '
    'are also preserved. Local SQLite runtime DB/WAL/SHM, pytest runtime trees and cache files are '
    'excluded. Known configured secrets scanned with zero matches; no live/provider/model calls. '
    'PG concurrency, hard120s, durable queries, guard intent and genuine fenced capture remain open. '
    'A separately pinned v2 must be reviewed before repository source changes.\n'
)
index = [
    {'path': str(path.relative_to(OUT)), 'bytes': path.stat().st_size,
     'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    for path in sorted(OUT.rglob('*')) if path.is_file() and path.name != 'ARCHIVE_INDEX.json'
]
(OUT / 'ARCHIVE_INDEX.json').write_text(json.dumps(index, indent=2) + '\n')
print(json.dumps({'archived_files': len(index), 'bytes': sum(x['bytes'] for x in index), 'known_secret_matches': 0, 'application_source_edited': False}))

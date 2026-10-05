# Prospective V10 recovery snapshot

This is an unfrozen draft. No trial or live pilot was allocated. The original
V9 closed attempt is unchanged. See docs/process/EXPERT500_PHASE1_V10_DRAFT_2026-10-05.md.

The manifest binds12 helper snapshots,21 current source modules,20 original gate
logs and the test bytes preceding one style-only correction. All33 preserved
original records were reread and hash-verified. The combined444 tests passed;
after the style correction all48 actual-parent tests and helper quality gates
passed. Negative preparation outputs are retained separately in logs/.

## Restore matching helper bytes

Run from the repository root. This restores source files only. It does not
freeze, allocate, retry or launch a pilot. A different existing /tmp file is
refused rather than overwritten.

```bash
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

draft = Path('backend/evaluation/research/expert/data/protocol.2026-10-05/v10-draft')
manifest = json.loads((draft / 'manifest.json').read_text())
pending = []
for record in manifest['records']:
    if record['kind'] != 'helper':
        continue
    source, target = draft / record['snapshot'], Path(record['original_path'])
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == record['sha256']
    assert target.parent == Path('/tmp') and not target.is_symlink()
    if target.exists():
        assert target.read_bytes() == data, f'Different existing helper: {target}'
    else:
        pending.append((target, data))
for target, data in pending:
    with target.open('xb') as output:
        output.write(data)
print(f'Verified 12 helper snapshots; restored {len(pending)} missing files.')
PY
```

Fresh live work requires legitimate free availability for the same Codex CLI
account, current-main integration, current source/OS gates, one final freeze,
source/tag/CI verification and one new whole-ten trial. Original V9 must never
be resumed or reset. The62-fact gate and deferred150 remain unchanged.

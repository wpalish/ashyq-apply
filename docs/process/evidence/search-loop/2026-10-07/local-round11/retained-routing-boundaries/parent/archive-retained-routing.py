# -*- coding: utf-8 -*-
"""Copy exactly pinned, selected offline packets; never discovery or scoring."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

REPO = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
WORK = REPO.parent
DEST = REPO / 'docs/process/evidence/search-loop/2026-10-07/local-round11/retained-routing-boundaries'
STOP = WORK / 'local-round7/provider-STOP.json'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
FULL = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T004040Z-check-bc90e5dc/summary.json')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(STOP) == STOP_SHA
source = json.loads(FULL.read_text())['source']
source_pins = {
    name: digest for name, digest in source['files'].items()
    if name.startswith(('backend/app/', 'backend/tests/', 'backend/evaluation/', 'backend/scripts/', 'frontend/'))
}
assert len(source_pins) == 999
for name, digest in source_pins.items():
    assert sha(REPO / name) == digest, name

# Arguments are an explicit JSON list of own folder/manifest/hash/label records.
# All packet files are checked before any repository evidence write.
packets = json.loads(Path(sys.argv[1]).read_text())
selected = {}
origins = []
allowed = ('.json', '.py', '.md', '.log', '.txt', '.html', '.xml', '.body', '.diff', '.patch', '.stdout', '.stderr')


def stage(path, relative, digest=None):
    assert path.is_file() and not path.is_symlink(), str(path)
    assert path.name.endswith(allowed), str(path)
    assert not any(part in {'__pycache__', '.git', 'node_modules'} for part in path.parts)
    assert not path.name.startswith('.env'), str(path)
    actual = sha(path)
    if digest:
        assert actual == digest, str(path)
    assert relative not in selected, relative
    selected[relative] = {
        'original': str(path), 'sha256': actual,
        'bytes': path.stat().st_size, 'body': path.read_bytes(),
    }


for packet in packets:
    folder = WORK / packet['folder']
    manifest = folder / packet['manifest']
    assert sha(manifest) == packet['sha256'], str(manifest)
    data = json.loads(manifest.read_text())
    files = data.get('files', data.get('selected_files_sha256'))
    assert files is not None, str(manifest)
    rows = files.items() if isinstance(files, dict) else [(v['path'], v) for v in files]
    for name, item in rows:
        relative = Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        digest = item if isinstance(item, str) else item['sha256']
        stage(folder / relative, packet['label'] + '/' + name, digest)
    stage(manifest, packet['label'] + '/' + packet['manifest'])
    origins.append({
        'folder': packet['folder'], 'manifest': packet['manifest'],
        'manifest_sha256': packet['sha256'],
        'status': data.get('status', data.get('state', 'see original receipt')),
    })

stage(Path(__file__), 'parent/archive-retained-routing.py')
stage(Path(sys.argv[1]), 'parent/selected-packets.json')
stage(WORK / 'local-round11/retained-routing-preflight-first-error.json', 'parent/preflight-first-error.json')
assert not DEST.exists(), str(DEST)
DEST.mkdir(parents=True)
for name, item in selected.items():
    path = DEST / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(item.pop('body'))
    assert sha(path) == item['sha256'], name

assert sha(STOP) == STOP_SHA
for name, digest in source_pins.items():
    assert sha(REPO / name) == digest, name
receipt = {
    'status': 'OFFLINE_RETENTION_DEFERRED_NOT_SOURCE_READY',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'source_head': source['source_head'],
    'source_snapshot_sha256': source['source_tree_sha256'],
    'selected_prefix_paths_unchanged': len(source_pins),
    'selected_prefix_paths_include_research_json': True,
    'global_STOP_sha256': STOP_SHA,
    'selected_files': len(selected),
    'selected_bytes': sum(x['bytes'] for x in selected.values()),
    'files': selected, 'packets': origins,
    'application_source_applied': False, 'new_source_flag': False,
    'live_provider_model_calls': 0, 'semantic_gold_reads': 0,
    'quality_scoring_executed': False, 'current_DEV_gain_proven': False,
    'limitations': [
        'Repeated peer checks are not extra distinct backend test identities.',
        'Genuine isolated SQLite Worker plus synthetic transport is not PostgreSQL contention or product acceptance.',
        'Native read-cap retention does not fix exact externally capped Toronto or asyncio-cancelled Groningen.',
        'Initial material failures, fixture qualifications, and inherited native inner-catch failures remain preserved.',
        'Routing evidence is not Claim, intake/population applicability, quality coverage, or complete research.',
        'Source remains exact tested 7c74/19f349; carried technical gates are not rerun proposal acceptance.',
        'Provider/global STOP is not reset, switched, retried, or resumed; the cohort stays UNSCORED.',
    ],
}
output = DEST / 'receipt.json'
output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({
    'receipt': str(output), 'receipt_sha256': sha(output),
    'selected_files': len(selected), 'selected_bytes': receipt['selected_bytes'],
    'source_prefix_paths_unchanged': len(source_pins), 'decision': receipt['status'],
}))

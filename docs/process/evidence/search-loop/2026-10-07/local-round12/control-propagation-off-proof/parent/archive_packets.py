"""Preserve exact selected offline proofs; no application imports or network."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


root = Path(__file__).resolve().parent
config_path = Path(sys.argv[1]).resolve()
config = json.loads(config_path.read_bytes())
repo = Path(config['repo'])
work = repo.parent
stop = work / 'local-round7/provider-STOP.json'
assert sha(stop) == config['STOP_sha256']
expected = json.loads((root / config['source_manifest']).read_bytes())['file_sha256']
for name, digest in expected.items():
    assert sha(repo / name) == digest, name

destination_relative = Path(config['destination'])
assert not destination_relative.is_absolute() and '..' not in destination_relative.parts
destination = repo / destination_relative
assert not destination.exists(), str(destination)
selected = {}
origins = []
allowed = {'.json', '.py', '.md', '.log', '.txt', '.html', '.xml', '.body',
           '.diff', '.patch', '.stdout', '.stderr'}


def stage(path, target_name, digest=None, byte_count=None):
    relative = Path(target_name)
    assert not relative.is_absolute() and '..' not in relative.parts
    assert path.is_file() and not path.is_symlink(), str(path)
    assert path.suffix in allowed and not path.name.startswith('.env'), str(path)
    assert not {'__pycache__', '.git', 'node_modules'} & set(path.parts), str(path)
    body = path.read_bytes()
    actual = hashlib.sha256(body).hexdigest()
    if digest is not None:
        assert actual == digest, str(path)
    if byte_count is not None:
        assert len(body) == byte_count, str(path)
    assert target_name not in selected, target_name
    selected[target_name] = {'body': body, 'sha256': actual, 'bytes': len(body),
                             'original': str(path)}


for packet in config['packets']:
    folder = work / packet['folder']
    manifest = folder / packet['manifest']
    assert sha(manifest) == packet['sha256'], str(manifest)
    data = json.loads(manifest.read_bytes())
    files = data[packet.get('files_key', 'files')]
    assert isinstance(files, (dict, list))
    rows = files.items() if isinstance(files, dict) else [(row['path'], row) for row in files]
    for name, row in rows:
        byte_key = packet.get('byte_count_key', 'bytes')
        assert isinstance(row, dict) and {'sha256', byte_key} <= set(row), name
        stage(folder / name, packet['label'] + '/' + name, row['sha256'], row[byte_key])
    stage(manifest, packet['label'] + '/' + packet['manifest'])
    origins.append({'folder': packet['folder'], 'manifest_sha256': packet['sha256'],
                    'physical_selected_files': len(files) + 1})

for row in config.get('parent_files', []):
    stage(Path(row['path']), 'parent/' + row['name'], row['sha256'])
stage(Path(__file__), 'parent/archive_packets.py')
stage(config_path, 'parent/archive-config.json')

# Complete verification precedes the first repository evidence write.
for name, row in selected.items():
    target = destination / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(row['body'])
    assert sha(target) == row['sha256']
for name, digest in expected.items():
    assert sha(repo / name) == digest, name
assert sha(stop) == config['STOP_sha256']
receipt = {
    'time': datetime.now(timezone.utc).isoformat(), 'status': config['status'],
    'origins': origins, 'selected_files': len(selected),
    'selected_bytes': sum(row['bytes'] for row in selected.values()),
    'file_sha256': {name: {key: value for key, value in row.items() if key != 'body'}
                    for name, row in selected.items()},
    'source_prefix_selected_paths_matched': len(expected),
    'STOP_sha256': config['STOP_sha256'],
    'qualification': 'Physical originals include copied peer evidence; file counts are not unique experiments. No live calls or quality scoring.'
}
receipt_path = destination / 'receipt.json'
receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'receipt': str(receipt_path), 'sha256': sha(receipt_path),
                  'selected_files': receipt['selected_files'],
                  'selected_bytes': receipt['selected_bytes'],
                  'source_paths_matched': len(expected)}))

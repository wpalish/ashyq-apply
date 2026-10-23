"""Apply only the exact root-qualified fourteen-path privacy increment."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess

ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = ROOT / 'work/ashyq-apply'
TASK = ROOT / 'work/security-round2'
C = ROOT / 'work/security-round1/c-rejected-pii-native-correction'
A = ROOT / 'work/security-round1/a-rejected-pii-persistence-test-port'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
approval = json.loads((TASK / 'root-native-acceptance.json').read_text())
expected_head = (TASK / 'integration-pre-apply-head.txt').read_text().strip()
assert subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip() == expected_head
assert subprocess.check_output(['git', '-C', str(REPO), 'branch', '--show-current'], text=True).strip() == 'task/product-privacy-diagnostics'
assert not subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain'], text=True).strip()
assert approval['status'] == 'QUALIFIED_CORRECTED_NATIVE_ACCEPTED_PENDING_FULL'
assert approval['proposal_READY_sha256'] == sha(C / 'READY.json') == '2dd776c38d489df632fc84a89e87331943e5af8d1b33ccb48feb43c2a9f4c3f3'
assert sha(Path(approval['peer_READY_path'])) == approval['peer_READY_sha256']
assert sha(A / 'READY.json') == approval['portable_READY_sha256']
plan_file = TASK / 'integration-plan.json'
assert sha(plan_file) == approval['integration_plan_sha256'] == '80c63a44c35fd262eca8ff4720c18b1e3d31ab11fcd89dfcd37bf12f8495a02b'
plan = json.loads(plan_file.read_text())
paths = plan['paths']
assert len(paths) == 14
assert sha(ROOT / 'work/local-round7/provider-STOP.json') == '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
previous = json.loads((ROOT / 'work/security-round1/final-source-pins.json').read_text())
assert sha(ROOT / 'work/security-round1/final-source-pins.json') == '22ca29438dadb49deb393941ed6d67624301418118f0dd501b63949a41a2a1df'
assert len(previous) == 20 and not (set(previous) & set(paths))
assert all(sha(REPO / n) == h for n, h in previous.items())
for name, r in paths.items():
    rel = Path(name)
    assert not rel.is_absolute() and '..' not in rel.parts and rel.parts[0] == 'backend'
    before = r['before_primary_sha256']
    assert sha(REPO / name) == before if before else not (REPO / name).exists()
    src = (A if name.endswith('/test_rejected_diagnostics_persistence.py') else C) / 'proposed' / name
    assert not src.is_symlink() and sha(src) == r['proposed_sha256'] and src.stat().st_size == r['bytes']
    assert approval['accepted_paths'][name] == r['proposed_sha256']
assert not (TASK / 'application-receipt.json').exists()
assert not (TASK / 'applied-source-pins.json').exists()
dest = REPO / 'docs/process/evidence/product-loop/2026-10-09/privacy-diagnostics'
assert sha(dest / 'root-native-acceptance.json') == sha(TASK / 'root-native-acceptance.json')
assert not (dest / 'applied-source-pins.json').exists()
assert not (dest / 'application-receipt.json').exists()
for name, r in paths.items():
    src = (A if name.endswith('/test_rejected_diagnostics_persistence.py') else C) / 'proposed' / name
    shutil.copyfile(src, REPO / name)
    assert sha(REPO / name) == r['proposed_sha256']
pins = {**previous, **{n: r['proposed_sha256'] for n, r in paths.items()}}
assert len(pins) == 34 and all(sha(REPO / n) == h for n, h in pins.items())
(TASK / 'applied-source-pins.json').write_text(json.dumps(pins, indent=2) + '\n')
receipt = {'utc': datetime.now(timezone.utc).isoformat(), 'applied_paths': paths,
    'pre_apply_head': expected_head, 'pre_apply_branch': 'task/product-privacy-diagnostics',
    'root_native_acceptance_sha256': sha(TASK / 'root-native-acceptance.json'),
    'proposal_READY_sha256': sha(C / 'READY.json'), 'peer_READY_sha256': approval['peer_READY_sha256'],
    'portable_READY_sha256': approval['portable_READY_sha256'], 'source34_pins_sha256': sha(TASK / 'applied-source-pins.json'),
    'status': 'EXACT_SOURCE_APPLIED_FULL_PENDING',
    'qualification': 'Source-bound synthetic/native privacy increment; no full/production/compliance/history cleanup/research-quality acceptance.'}
(TASK / 'application-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
for n in ['applied-source-pins.json', 'application-receipt.json']:
    shutil.copyfile(TASK / n, dest / n)
print(json.dumps({'status': receipt['status'], 'paths': len(paths), 'source34_pins_sha256': receipt['source34_pins_sha256']}))

"""Copy only pinned finite completed own doctor/core originals outside primary."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import xml.etree.ElementTree as ET

OUT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round2/e-first-native-failure-originals')
TASK = OUT.parent
REPO = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
BUNDLE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
MANIFEST_SHA = '710f142ac007f24287f68848b0a577cb54608c8c48fe0695c46d7ef4081697ff'
HEAD = '08450f71e6bbeadd9a2212fbd6c9f96f5c428755'
PINS_SHA = 'bc960dfdf50a140698ff399c7929cc503f6fee24ef5f050c34d3ef9f72a71dd6'
STOP_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest_path = OUT / 'selection-manifest.json'
assert sha(manifest_path) == MANIFEST_SHA
selection = json.loads(manifest_path.read_text())
assert selection['record_count'] == 23 and len(selection['records']) == 23
assert selection['source_head'] == HEAD and selection['source34_pins_sha256'] == PINS_SHA
assert selection['full_status'] == 'NOT_RUN'
assert sha(REPO.parent.parent / 'work/local-round7/provider-STOP.json') == STOP_SHA
assert not (OUT / 'originals').exists() and not (OUT / 'collection-receipt.json').exists()
allowed_roots = {BUNDLE / 'runs' / selection['doctor'], BUNDLE / 'runs' / selection['core'], TASK / 'native-queue', TASK}
allowed_suffix = {'.log', '.json', '.xml', '.txt'}
bodies = {}
for record in selection['records']:
    src = Path(record['source'])
    rel = Path(record['target'])
    assert src.parent in allowed_roots and src.is_file() and not src.is_symlink()
    assert src.suffix in allowed_suffix and not src.name.startswith('.env')
    assert not rel.is_absolute() and '..' not in rel.parts and rel.parts[0] == 'originals'
    assert all(part not in {'.venv','node_modules','data','runtime','.git','private-backups'} for part in rel.parts)
    assert not (OUT / rel).exists()
    body = src.read_bytes()
    assert len(body) == record['bytes'] and hashlib.sha256(body).hexdigest() == record['sha256']
    assert b'-----BEGIN PRIVATE KEY-----' not in body and b'-----BEGIN RSA PRIVATE KEY-----' not in body
    assert b'-----BEGIN OPENSSH PRIVATE KEY-----' not in body
    bodies[str(rel)] = body
assert len(bodies) == 23
queue = json.loads(bodies['originals/queue/execution.json'])
assert [r['suite'] for r in queue] == ['doctor','core'] and [r['exit_code'] for r in queue] == [0,1]
for record in queue:
    assert record['head'] == HEAD and record['source_pins_sha256'] == PINS_SHA
    assert len(record['owned_runs']) == 1 and record['owned_runs'][0]['reported_by_own_child_stdout']
    assert Path(record['owned_runs'][0]['path']).parent == BUNDLE / 'runs'
    assert record['argv'][2:4] == ['--repo', str(REPO)]
doctor = json.loads(bodies['originals/doctor/summary.json'])
core = json.loads(bodies['originals/core/summary.json'])
assert hashlib.sha256(bodies['originals/doctor/summary.json']).hexdigest() == queue[0]['owned_runs'][0]['summary_sha256']
assert hashlib.sha256(bodies['originals/core/summary.json']).hexdigest() == queue[1]['owned_runs'][0]['summary_sha256']
assert doctor['status'] == 'passed' and core['status'] == 'failed'
assert len(doctor['steps']) == 5 and all(r['exit_code'] == 0 for r in doctor['steps'])
assert len(core['steps']) == 8 and [r['name'] for r in core['steps'] if r['exit_code'] != 0] == ['backend-sqlite']
source_manifest = json.loads(bodies['originals/core/source-manifest.json'])
assert core['source'] == source_manifest and source_manifest['source_head'] == HEAD
assert source_manifest['source_status'] == ''
assert hashlib.sha256(json.dumps(source_manifest['files'], sort_keys=True).encode()).hexdigest() == source_manifest['source_tree_sha256']
pins = json.loads(bodies['originals/binding/applied-source-pins.json'])
assert len(pins) == 34 and hashlib.sha256(bodies['originals/binding/applied-source-pins.json']).hexdigest() == PINS_SHA
assert all(source_manifest['files'][n] == h for n,h in pins.items())
assert bodies['originals/binding/applied-head.txt'].decode().strip() == HEAD
app = json.loads(bodies['originals/binding/application-receipt.json'])
assert app['source34_pins_sha256'] == PINS_SHA and app['status'] == 'EXACT_SOURCE_APPLIED_FULL_PENDING'
for rel,body in bodies.items():
    dest = OUT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    assert sha(dest) == hashlib.sha256(body).hexdigest()
for record in selection['records']:
    assert sha(Path(record['source'])) == record['sha256']
receipt = {
    'utc': datetime.now(timezone.utc).isoformat(), 'status':'FIRST_NATIVE_CORE_FAILED_ORIGINALS_PRESERVED',
    'manifest_sha256':MANIFEST_SHA,'originals':selection['records'],'record_count':23,
    'total_original_bytes':selection['total_bytes'],'source_head':HEAD,'source34_pins_sha256':PINS_SHA,
    'source_snapshot_manifest_sha256':sha(OUT/'originals/core/source-manifest.json'),
    'source_snapshot_tree_sha256':source_manifest['source_tree_sha256'],'declared_source_files':len(source_manifest['files']),
    'doctor_environment_pass':5,'core_gate_pass':7,'core_gate_failed':1,'queue_exit_code':1,
    'full_status':'NOT_RUN','private_db_env_zip_deps_or_source_tree_copied':False,
    'tests_or_servers_rerun':False,'primary_or_git_modified':False,
    'source_originals_unchanged_pre_post':True,'provider_STOP_unchanged':sha(REPO.parent.parent/'work/local-round7/provider-STOP.json')==STOP_SHA,
    'qualification':'Actual completed own doctor/core only; failed core is preserved, full/PG/E2E/audits and production not accepted.'
}
(OUT/'collection-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
xml = ET.fromstring(bodies['originals/core/backend-sqlite.xml'])
cases = xml.findall('.//testcase')
failed = [c for c in cases if c.find('failure') is not None]
errors = [c for c in cases if c.find('error') is not None]
skipped = [c for c in cases if c.find('skipped') is not None]
counts={'total':len(cases),'unique_case_identifiers':len({(c.get('classname'),c.get('name')) for c in cases}),
        'failed':len(failed),'errors':len(errors),'skipped':len(skipped),
        'passed':len(cases)-len(failed)-len(errors)-len(skipped)}
log = bodies['originals/core/backend-sqlite.log'].decode()
finish = re.search(r'(\d+) failed, (\d+) passed, (\d+) warnings in ([0-9.]+)s',log)
coverage = re.search(r'Total coverage: ([0-9.]+)%',log)
assert finish and coverage and counts=={'total':4392,'unique_case_identifiers':4392,'failed':1,'errors':0,'skipped':0,'passed':4391}
assert list(map(int,finish.group(1,2,3))) == [1,4391,32]
frontend = bodies['originals/core/frontend-tests.log'].decode()
assert re.search(r'Test Files\s+34 passed \(34\)',frontend) and re.search(r'Tests\s+357 passed \(357\)',frontend)
failure = failed[0].find('failure')
analysis={
    'utc':datetime.now(timezone.utc).isoformat(),'status':'FAILED_CORE_FULL_NOT_RUN',
    'doctor':{'environment_checks':5,'passed':5,'failed':0,'snapshot_manifest':'NOT_PRESENT_ENVIRONMENT_DOCTOR_ONLY'},
    'core':{'gate_count':8,'passed':7,'failed':1,'failed_step':'backend-sqlite'},
    'backend_sqlite':{**counts,'warnings':32,'coverage_percent':float(coverage.group(1)),
                      'pytest_summary_seconds':float(finish.group(4)),
                      'native_step_seconds':next(r['seconds'] for r in core['steps'] if r['name']=='backend-sqlite'),
                      'junit_suite_attributes':[s.attrib for s in xml.findall('.//testsuite')]},
    'frontend':{'test_files_passed':34,'tests_passed':357},
    'static':{'ruff_exit':0,'ruff_format_exit':0,'mypy_exit':0,'mypy_files':388},
    'first_failure':{'classname':failed[0].get('classname'),'name':failed[0].get('name'),
                     'assertion':'assert any("Traceback" in log["json"] for log in captured(caplog))',
                     'source_location':'tests/test_rejected_diagnostics.py:615',
                     'message':failure.get('message'),'original_failure_text':failure.text,
                     'cause':'NOT_DIAGNOSED_BY_COLLECTOR',
                     'preceding_rethrow_identity_and_audit_detail_assertions_passed':True,
                     'later_P6_assertions_not_reached':True},
    'source_head':HEAD,'source34_pins_sha256':PINS_SHA,'source_tree_sha256':source_manifest['source_tree_sha256'],
    'declared_source_files':len(source_manifest['files']),'snapshot_manifest_digest_matches_declared_map':True,
    'full':'NOT_RUN','backend_postgresql':'NOT_RUN','demo_e2e':'NOT_RUN','auth_e2e':'NOT_RUN',
    'dependency_audits':'NOT_RUN','containers':'NOT_RUN','production':'NOT_RUN',
    'not_unique_additional_tests':'Doctor/core step counts and JUnit test cases are different units; no duplicate rerun is counted.'
}
(OUT/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'records':23,'bytes':receipt['total_original_bytes'],
                  'analysis_sha256':sha(OUT/'analysis.json'),'receipt_sha256':sha(OUT/'collection-receipt.json')}))

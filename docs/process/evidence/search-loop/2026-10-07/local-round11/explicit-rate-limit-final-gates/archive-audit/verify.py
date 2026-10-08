"""Finite stdlib-only opaque-byte archive audit; no app/test/gold execution."""
from __future__ import annotations
from pathlib import Path
from datetime import UTC,datetime
import hashlib,json

B=Path(__file__).resolve().parent
P=json.loads((B/'PLAN.json').read_text());A=Path(P['archive'])
R=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
W=Path(P['origin_root'])
PROVIDER=W/'local-round7/provider-STOP.json';DEVELOPMENT=W/'development-STOP.json'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
STOP_BEFORE={str(p):sha(p) for p in [PROVIDER,DEVELOPMENT]}
receipt_before=sha(A/'receipt.json')
assert receipt_before==P['archive_receipt_sha256']
d=json.loads((A/'receipt.json').read_text())
entries=d['file_sha256'];assert isinstance(entries,dict)
checks=[];issues=[]
for relative,row in entries.items():
 rel=Path(relative)
 assert not rel.is_absolute() and '..' not in rel.parts
 assert isinstance(row,dict) and type(row['bytes']) is int and row['bytes']>=0
 assert isinstance(row['sha256'],str) and len(row['sha256'])==64
 original=Path(row['original']);assert original.is_absolute()
 target=A/rel
 assert target.is_file() and not target.is_symlink()
 assert original.is_file() and not original.is_symlink()
 copied=target.read_bytes();prior=original.read_bytes()
 got={'path':relative,'archive_sha256':hashlib.sha256(copied).hexdigest(),'archive_bytes':len(copied),'original':str(original),'original_sha256':hashlib.sha256(prior).hexdigest(),'original_bytes':len(prior),'bytes_equal':copied==prior}
 got['status']='PASS' if got['archive_sha256']==row['sha256'] and len(copied)==row['bytes'] and got['bytes_equal'] else 'RED'
 checks.append(got)
 if got['status']=='RED':issues.append(got)
physical={str(p.relative_to(A)) for p in A.rglob('*') if p.is_file() and p!=A/'receipt.json'}
assert physical==set(entries),{'missing':list(set(entries)-physical),'unlisted':list(physical-set(entries))}
assert len(entries)==d['selected_files']==P['expected_selected_files']==931
assert sum(row['bytes'] for row in entries.values())==d['selected_bytes']==P['expected_selected_bytes']==16787404

origin_results=[]
for origin in d['origins']:
 folder=W/origin['folder']
 candidates=[(rel,row) for rel,row in entries.items() if Path(row['original'])==folder/'ready-manifest.json']
 assert len(candidates)==1
 relative,entry=candidates[0]
 assert sha(A/relative)==sha(folder/'ready-manifest.json')==origin['manifest_sha256']
 header=json.loads((A/relative).read_text())
 selected=header.get('files')
 if not isinstance(selected,dict):
  rows=header['selected_files_sha256'];assert isinstance(rows,list)
  selected={row['path']:{'sha256':row['sha256'],'bytes':row['bytes']} for row in rows}
 assert isinstance(selected,dict)
 prefix=Path(relative).parent
 for rel,row in selected.items():
  path=prefix/rel;expected=entries[str(path)]
  expected_sha=row['sha256'] if isinstance(row,dict) else row
  assert expected['sha256']==expected_sha
  if isinstance(row,dict) and 'bytes' in row:assert expected['bytes']==row['bytes']
 archived_count=sum(Path(rel).is_relative_to(prefix) for rel in entries)
 assert archived_count==origin['physical_selected_files']==len(selected)+1
 origin_results.append({'origin':str(folder),'archive_prefix':str(prefix),'manifest_sha256':origin['manifest_sha256'],'selected_entries':len(selected),'physical_including_manifest':archived_count,'status':'PASS'})

prefix_file=A/'parent/source-after-isort-999.json'
map_data=json.loads(prefix_file.read_text());final=map_data['file_sha256']
assert len(final)==d['source_prefix_selected_paths_matched']==999
assert sha(prefix_file)==sha(A/'import-repair-peer/packet/source-after-isort-999.json')
prefix_checks=[]
for path,digest in final.items():
 current=sha(R/path)
 prefix_checks.append({'path':path,'expected':digest,'actual':current,'status':'PASS' if current==digest else 'RED'})
 if current!=digest:issues.append(prefix_checks[-1])
assert map_data['STOP_sha256']==d['STOP_sha256']==P['STOP_expected_sha256']==STOP_BEFORE[str(PROVIDER)]
STOP_AFTER={str(p):sha(p) for p in [PROVIDER,DEVELOPMENT]}
assert STOP_AFTER==STOP_BEFORE
summary=json.loads((A/'parent/interrupted-first-full/summary.json').read_text())
steps={row['name']:row for row in summary['steps']}
assert summary['status']=='interrupted'
assert steps['ruff']['exit_code']==1 and steps['backend-sqlite']['exit_code']==130
assert steps['ruff-format']['exit_code']==steps['mypy']['exit_code']==0
assert 'Found 3 errors.' in (A/'parent/interrupted-first-full/ruff.log').read_text()
assert d['status']=='APPLIED_OPERATIONAL_REPAIR_EXACT_PEER_ACCEPT_FRESH_FULL_PENDING'
assert 'not unique experiments' in d['qualification']
assert map_data['full_tests_not_yet_run'] is True
assert sha(A/'receipt.json')==receipt_before
(B/'entries.original.json').write_text(json.dumps(checks,indent=2)+'\n')
(B/'prefix999.original.json').write_text(json.dumps(prefix_checks,indent=2)+'\n')
result={'verified_utc':datetime.now(UTC).isoformat(),'status':'PASS' if not issues else 'RED','archive_receipt_sha256':receipt_before,'file_checks':{'PASS':sum(row['status']=='PASS' for row in checks),'RED':sum(row['status']=='RED' for row in checks),'physical':len(entries),'bytes':sum(row['bytes'] for row in entries.values()),'unique_content_hashes':len({row['sha256'] for row in entries.values()}),'qualification':'Physical copiedfiles and distinctcontenthashes are notuniqueexperiments/calls.'},'origins':origin_results,'source_prefix999':{'PASS':sum(row['status']=='PASS' for row in prefix_checks),'RED':sum(row['status']=='RED' for row in prefix_checks),'map_sha256':sha(prefix_file)},'STOP_before':STOP_BEFORE,'STOP_after':STOP_AFTER,'STOP_reference_is_hash_not_embedded_copy':not any('stop' in path.lower() for path in entries),'first_full':{'status':summary['status'],'ruff_exit':steps['ruff']['exit_code'],'ruff_errors':3,'format_exit':steps['ruff-format']['exit_code'],'mypy_exit':steps['mypy']['exit_code'],'sqlite_exit':steps['backend-sqlite']['exit_code']},'qualification':'Archive records operational safetyrepair/noqualityscore and finalfullpending atcheckpoint. No finalfullPASS provedhere; no originalsemanticcontrols rerun.','metadata_only_parsed':['archive receipts/ready-manifests','sourceprefix map','interruptedfullstatus/rufflog'],'opaque_original_bytes_only':True,'app_import_test_network_Git_source_default_STOP_gold_scoring_changes':0,'issues':issues}
(B/'verification.original.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key in ['status','file_checks','source_prefix999','first_full','STOP_reference_is_hash_not_embedded_copy']},indent=2))
raise SystemExit(1 if issues else 0)

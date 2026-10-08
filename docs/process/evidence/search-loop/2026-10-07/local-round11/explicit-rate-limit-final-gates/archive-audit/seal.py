from pathlib import Path
from datetime import UTC,datetime
import hashlib,json
B=Path(__file__).resolve().parent
P=json.loads((B/'PLAN.json').read_text());V=json.loads((B/'verification.original.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert V['status']=='PASS' and V['file_checks']['PASS']==931 and V['source_prefix999']['PASS']==999
assert sha(Path(P['archive'])/'receipt.json')==P['archive_receipt_sha256']
for path,digest in V['STOP_after'].items():assert sha(Path(path))==digest
receipt={'sealed_utc':datetime.now(UTC).isoformat(),'status':'INDEPENDENT_ARCHIVE_HASH_SIZE_ORIGIN_PASS','PLAN_sha256':sha(B/'PLAN.json'),'verified_archive_receipt_sha256':P['archive_receipt_sha256'],'verification_sha256':sha(B/'verification.original.json'),'entries_proof_sha256':sha(B/'entries.original.json'),'prefix999_proof_sha256':sha(B/'prefix999.original.json'),'raw_log_sha256':sha(B/'verification.raw.log'),'file_checks':V['file_checks'],'origin_count':len(V['origins']),'source_prefix999':V['source_prefix999'],'STOP_after':V['STOP_after'],'first_full':V['first_full'],'qualification':'Operationalrepair/finalfullpending atarchivedcheckpoint. Countsarephysicalcopiesnotexperiments. No controls/source/livescoring reexecution. STOP verifiedasimmutablehashreference; noembeddedcopyinthese931entries.','mutations_imports_tests_network_gold_scoring_DB_actions':0}
(B/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
files={str(p.relative_to(B)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(B.rglob('*')) if p.is_file() and p.name!='ready-manifest.json' and '__pycache__' not in p.parts}
(B/'ready-manifest.json').write_text(json.dumps({'status':receipt['status'],'files':files,'selected_files':len(files),'selected_bytes':sum(v['bytes'] for v in files.values())},indent=2)+'\n')
print(json.dumps({'ready':sha(B/'ready-manifest.json'),'receipt':sha(B/'receipt.json'),'files':len(files),'bytes':sum(v['bytes'] for v in files.values())},indent=2))

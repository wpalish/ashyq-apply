from pathlib import Path
import json,hashlib,datetime
base=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20');own=base/'work/local-round15/b-full-closure';repo=base/'work/ashyq-apply';a=base/'work/local-round15/a-local-pilot-proposal';root=base/'work/local-round15/root-orchestrator'
def meta(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def save(name,v):(own/name).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
src=root/'source-after-1002.json';archive=repo/'docs/process/evidence/search-loop/2026-10-07/local-round15/final-qualified-proposal/receipt.json';stop=base/'work/local-round7/provider-STOP.json'
plan={'time_utc':datetime.datetime.now(datetime.UTC).isoformat(),'scope':'read-only saved-source/archive binding followed by terminal full raw/JUnit validation; no app imports/tests/full/seed/scorer/SQL/network/CLI','applied_head':'c8c9dfcd9fb810a13a80e983f8d16754a1e3fde2','source_map':{'path':str(src),**meta(src)},'proposal_A':{'path':str(a/'ready-manifest.json'),**meta(a/'ready-manifest.json')},'proposal_B':{'path':str(base/'work/local-round15/b-final-peer/ready-manifest.json'),**meta(base/'work/local-round15/b-final-peer/ready-manifest.json')},'archive':{'path':str(archive),**meta(archive)},'STOP':meta(stop),'terminal_full':'AWAITING_ROOT_COMPLETION_AND_PATH','required_checks':['exact1002 selected source/current/frozen; six accepted files; all180 archive selected originals hash+size','actual13 step exit0/terminalpassed; SQLite/PG equal unique JUnit sets; old4349 identities retained and20new exacttestnames, countfromraw','static6/fullstatic/frontend232/demo79+viewportskip1/auth6/audits, actual warnings/coverage qualification; no live/quality inference'],'read_only_preparation':True}
save('PLAN.json',plan)
assert plan['source_map']['sha256'].startswith('d1220c3c')
sv=json.loads(src.read_text());mapping=sv['file_sha256'];assert len(mapping)==1002
assert all(meta(repo/k)['sha256']==v for k,v in mapping.items())
accepted=json.loads((a/'source-manifest.json').read_text())['proposal_files']
assert all(meta(repo/k)==v['proposal'] for k,v in accepted.items())
old=json.loads((base/'work/local-round13/root-stopped-trace-accounting/source-after-999.json').read_text())['file_sha256']
changed=[k for k,v in old.items() if mapping[k]!=v];added=sorted(set(mapping)-set(old));assert set(changed)|set(added)==set(accepted);assert len(changed)==3 and len(added)==3
ar=json.loads(archive.read_text());entries=ar['file_sha256'];assert len(entries)==180
assert all(meta(archive.parent/k)=={'sha256':v['sha256'],'bytes':v['bytes']}==meta(Path(v['original'])) for k,v in entries.items())
assert sum(v['bytes'] for v in entries.values())==ar['selected_bytes']==2468657
assert meta(stop)['sha256']=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
rec={'time_utc':datetime.datetime.now(datetime.UTC).isoformat(),'status':'SOURCE_AND_PROPOSAL_ARCHIVE_BOUND_FULL_PENDING','current_selected_sources':1002,'exact_six':{k:meta(repo/k) for k in accepted},'unchanged_prior_source_paths':996,'changed_existing3':changed,'new3':added,'archive_receipt':meta(archive),'archive_selected_files':180,'archive_selected_bytes':2468657,'archive_originals_and_destinations_equal':True,'STOP':meta(stop),'tests_or_imports_run':0,'full_verdict':'PENDING'}
save('preparation.json',rec);print(json.dumps(rec,indent=2))

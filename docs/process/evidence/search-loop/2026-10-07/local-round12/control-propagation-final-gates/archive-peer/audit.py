"""Finite archive hash/opaque-byte origin verification only."""
from pathlib import Path
from datetime import datetime, UTC
import hashlib
import json

HERE=Path(__file__).resolve().parent
BASE=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO=BASE/'work/ashyq-apply'
ROUND=BASE/'work/local-round12'
ARCHIVE=REPO/'docs/process/evidence/search-loop/2026-10-07/local-round12'
PLAN=json.loads((HERE/'PLAN.json').read_text())


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):return json.loads(p.read_text())


def member(p,row):
    assert p.is_file(),str(p)
    assert p.stat().st_size==row['bytes'],str(p)+' size'
    assert sha(p)==row['sha256'],str(p)+' hash'


results={};all_origin_pins={}
for name,expected in PLAN['archives'].items():
    archive=ARCHIVE/name
    recpath=archive/'receipt.json'
    assert sha(recpath)==expected['receipt_sha256']
    receipt=load(recpath);selection=receipt['file_sha256']
    assert len(selection)==receipt['selected_files']==expected['physical_selected_files']
    assert sum(row['bytes'] for row in selection.values())==receipt['selected_bytes']==expected['selected_bytes']
    copied=[]
    for rel,row in selection.items():
        assert not Path(rel).is_absolute() and '..' not in Path(rel).parts
        original=Path(row['original']);target=archive/rel
        assert original.is_relative_to(BASE/'work')
        assert original.suffix not in {'.db','.pyc'} and not any(part.startswith('.env') for part in original.parts)
        member(target,row);member(original,row)
        assert target.read_bytes()==original.read_bytes(),rel+' original-byte mismatch'
        copied.append({'archive_path':rel,'original_path':str(original),'sha256':row['sha256'],'bytes':row['bytes'],'exact_origin':True})
    actual={str(p.relative_to(archive)) for p in archive.rglob('*') if p.is_file()}
    assert actual==set(selection)|{'receipt.json'},name+' unexpected/missing archive member'
    origins=[]
    for o in receipt['origins']:
        folder=BASE/'work'/o['folder'];man=folder/'ready-manifest.json'
        assert sha(man)==o['manifest_sha256']
        m=load(man)
        for rel,row in m['files'].items():member(folder/rel,row)
        assert len(m['files'])+1==o['physical_selected_files']
        rows=[row for row in selection.values() if Path(row['original']).is_relative_to(folder)]
        assert len(rows)==o['physical_selected_files']
        original_set={str(folder/rel) for rel in m['files']}|{str(man)}
        assert {row['original'] for row in rows}==original_set
        origins.append({'folder':str(folder),'manifest_sha256':sha(man),'manifest_members_verified':len(m['files']),'physical_archive_members':len(rows),'original_selection_exact':True})
        all_origin_pins[str(man)]=sha(man)
    results[name]={'receipt_sha256':sha(recpath),'physical_selected_files':len(selection),'selected_bytes':receipt['selected_bytes'],'copied_originals_all_exact':True,'physical_set_exact':True,'origins':origins,'status_from_root_receipt':receipt['status'],'qualification_from_root':receipt['qualification'],'copies':copied}

seedfolder=ROUND/'b-control-propagation-demo-seed'
seedman=seedfolder/'ready-manifest.json'
assert sha(seedman)=='511fb556d71eaf4d08efc7de44883e13e85ba167042ba66f9046fc8838e712fc'
seed=load(seedman)
assert len(seed['files'])==286 and seed['selected_files']==286
candidate={rel for rel in seed['files'] if rel.startswith('candidate/')}
noncandidate=set(seed['files'])-candidate
assert len(candidate)==265 and len(noncandidate)==21
for rel,row in seed['files'].items():member(seedfolder/rel,row)
seedselection=load(ARCHIVE/'control-propagation-seed/receipt.json')['file_sha256']
origins={row['original'] for row in seedselection.values()}
assert {str(seedfolder/rel) for rel in noncandidate}.issubset(origins)
assert str(seedman) in origins
assert not any(row['original'].startswith(str(seedfolder/'candidate')+'/') for row in seedselection.values())
assert not any('/candidate/' in rel for rel in seedselection)
seedclosure={'original_manifest_sha256':sha(seedman),'all_original_manifest_members_verified':286,'candidate_members_verified_not_copied':265,'noncandidate_originals21_all_copied':True,'full_ready_manifest_copied':True,'candidate_duplicate_tree_absent':True,'qualification':'265 source/assets include PDF; opaque SHA/size check only, no semantic corpus/label read.21 original controls+source pins are physical evidence, not21 experiments.'}
source=ROUND/'root-control-propagation/source-after-999.json'
source_data=load(source)['file_sha256'];assert len(source_data)==999
for rel,h in source_data.items():assert sha(REPO/rel)==h,rel+' source changed'
stop=BASE/'work/local-round7/provider-STOP.json';stop_sha=sha(stop)
assert stop_sha=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
for obj in results.values():
    rr=load(ARCHIVE/next(k for k,v in results.items() if v is obj)/'receipt.json')
    assert rr['source_prefix_selected_paths_matched']==999 and rr['STOP_sha256']==stop_sha
result={'status':'PASS_BOTH_ARCHIVES_EXACT_HASH_SIZE_ORIGIN_SELECTION','checked_utc':datetime.now(UTC).isoformat(),'archives':results,'seed_original_closure':seedclosure,'source999_current_match':True,'source_after999_sha256':sha(source),'STOP_sha256':stop_sha,'STOP_unchanged':True,'physical_selected_sum':152,'physical_selected_sum_is_not_unique_experiments':True,'source_original_manifests':all_origin_pins,'no_replays_imports_Git_network_DB_semantics':True,'qualification':'Fresh exact-source full is still pending; operational archive verification only. No source/control/scoring/quality decisions rerun.'}
(HERE/'audit-results.original.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'proposal':'126files/1469777bytes exact','seed':'26files/176641bytes exact','seed_original286_verified':True,'candidate265_not_duplicated':True,'source999_unchanged':True,'STOP_unchanged':True}))

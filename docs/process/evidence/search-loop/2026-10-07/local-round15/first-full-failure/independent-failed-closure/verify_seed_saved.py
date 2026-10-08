from pathlib import Path
import json,hashlib,datetime
b=Path(__file__).resolve().parent;base=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20');a=base/'work/local-round15/a-owned-seed';start=json.loads((b/'full-start.json').read_text());snapshot=Path(start['snapshot']);repo=base/'work/ashyq-apply'
def meta(p):
 data=p.read_bytes();return {'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
p=a/'ready-manifest.json';assert meta(p)['sha256']=='b7e50f3abd6f6ef56704fccd7990c4dc4dfa9a1ca8196df02e0966767ad1e57d'
m=json.loads(p.read_text());assert len(m['files'])==30;assert all(meta(a/k)==v for k,v in m['files'].items());assert sum(v['bytes'] for v in m['files'].values())==130742
r=json.loads((a/'receipt.json').read_text());assert meta(a/'receipt.json')['sha256']=='f33427b75d308eea12d98fcf29201409857c9deaca27c55c8e8fd105d7572a74'
sources=json.loads((a/'candidate-source-pins.json').read_text());assert len(sources)==265;assert all(meta(snapshot/k)['sha256']==v==meta(repo/k)['sha256']==meta(a/'candidate'/k)['sha256'] for k,v in sources.items())
assert len([k for k in sources if k.startswith('backend/app/')])==242
assert [c['action'] for c in r['commands']]==['heads','migrate','seed','inspect'] and all(c['exit_code']==0 and c['control'] is None for c in r['commands'])
for c in r['commands']:
 for stream in ('stdout','stderr'):assert meta(a/(c['action']+'.'+stream+'.original.log'))['sha256']==c[stream+'_sha256']
actual=json.loads((a/'inspection.original.json').read_text());assert actual==r['inspection'];assert actual['heads']==actual['database_revisions']==['d8e412c6a901'];assert actual['rows']==20 and actual['first']=='University of Groningen';assert actual['UBC']['portfolio_bucket']=='OUT_OF_BUDGET' and actual['UBC']['funding_classification']=='FULL_TUITION';assert actual['all_undecided_no_approve'] is True;assert r['network_attempts']==r['provider_model_university_calls']==r['approved_requests']==0
out={'time_utc':datetime.datetime.now(datetime.UTC).isoformat(),'status':'SAVED_SYNTHETIC_SEED_COMPATIBILITY_BOUND','manifest':meta(p),'receipt':meta(a/'receipt.json'),'selected_files':30,'selected_bytes':130742,'exact_physical_current_frozen_candidate_source_hashes':265,'actual_four_commands_exit0':True,'inspection':actual,'no_own_execution':True,'STOP':meta(base/'work/local-round7/provider-STOP.json'),'qualification':'saved native own-SQLite synthetic demo only; no real university/provider/model/runtime admission/quality; author initial metadata-count preflight error remains preserved'}
(b/'seed-saved-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))

"""Read-only byte/source/static qualification of sealed outer OFF packet."""
from pathlib import Path
from datetime import datetime, UTC
import ast
import hashlib
import json

HERE=Path(__file__).resolve().parent
BASE=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO=BASE/'work/ashyq-apply'
ROUND=BASE/'work/local-round12'
B=ROUND/'b-outer-trace-preparation'
RUN=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T043357Z-check-0d98eeb3')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):return json.loads(p.read_text())


assert sha(B/'ready-manifest.json')=='8e4a13b345aea6e00b05ec944124f8a349a7f144f18a4c5137a41399d53ac51f'
m=load(B/'ready-manifest.json');bp=load(B/'PLAN.json')
for rel,row in m['files'].items():
 p=B/rel;assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],rel
assert len(m['files'])==m['selected_files']==24
assert sum(r['bytes'] for r in m['files'].values())==m['selected_bytes']
rootafter=load(ROUND/'root-control-propagation/source-after-999.json')['file_sha256']
full=load(RUN/'source-manifest.json');assert full['source_head']=='d076e435cb1a6247f171ffb2411c6ab79a0ba857'
assert len(bp['sources'])==18
source={}
for rel,row in bp['sources'].items():
 f=REPO/rel;b=f.read_bytes();h=hashlib.sha256(b).hexdigest()
 assert h==row['sha256']==rootafter[rel]==full['files'][rel]
 assert len(b)==row['bytes'] and b==(B/'source'/rel).read_bytes()
 assert sha(Path(full['snapshot'])/rel)==h
 source[rel]={'sha256':h,'bytes':len(b),'current_after999_d076_snapshot_exact':True}
# Search method's file was not one ofB's18 copiedsources; bind its actual
# imported source path independently to current source999/full snapshot.
additional={}
rel='backend/app/adapters/search/fake.py';h=sha(REPO/rel)
assert h==rootafter[rel]==full['files'][rel]
additional[rel]={'sha256':h,'current_after999_full_match':True,'qualification':'Not inB18selected sourcecopies, now independentlybound codehash. Native FakeSearchProvider method is named inBactualimports.'}
raw=load(B/'outcomes.original.json');rec=load(B/'receipt.json');execution=load(B/'execution.json')
assert len(raw['paths'])==2 and raw['source_pre_post_equal'] is True and raw['network_attempts']==[]
assert rec['script_sha256']==execution['script_sha256']==sha(B/'proof_outer.py')
assert rec['raw_sha256']==sha(B/'outcomes.original.json')
assert execution['exit_code']==0 and execution['fixture_failures']==0 and execution['network_attempts']==0
assert execution['cwd']==str(B) and execution['argv'][-2:]==[str(REPO/'backend/.venv/bin/python'),'proof_outer.py']
rows=[]
for r in raw['paths']:
 assert len(r['checks'])==11 and all(r['checks'].values())
 inner=r['inner_native_trace'];outer=r['exported_native_trace'];candidate=r['exported_candidate']
 assert len(r['mock_provider_query_calls'])==inner['search_queries_attempted']==6
 assert outer['search_queries_attempted']==candidate['search_queries_used']==0
 assert inner['domain']=='example.edu' and outer['domain']==('' if r['kind']=='curated' else 'example.edu')
 assert candidate['domain']=='' and candidate['programs']==[]
 guards=r['guard_events'];assert len(guards)==5
 assert [x['before'] for x in guards]==[56,57,58,59,60]
 assert sum(x['admitted'] for x in guards)==4 and guards[-1]['same_original_stop'] is True
 assert r['simulated_read_count_start']==56 and r['simulated_read_count_end']==60
 assert len(r['mock_HTTP_exchanges'])==guards[-1]['http_exchanges_before_refusal']==4
 assert r['native_fetcher_stats']['ok']==3 and r['native_fetcher_stats']['cached']==1
 assert sum(r['native_fetcher_stats'].values())==4 and r['native_fetch_tiers']['http']==4
 assert r['native_fetch_tiers']['browser']==r['native_fetch_tiers']['pdf']==0
 assert len(r['walker_outcomes_remain_separate'])==inner['walker']['catalogs_walked']==1
 assert outer['walker']['catalogs_walked']==0 and len(inner['sitemaps_read'])==1 and not outer['sitemaps_read']
 if r['kind']=='catalogue':assert candidate['catalogue_id']=='synthetic-offline-university'
 rows.append({'route':r['kind'],'checks_verified':11,'fake_query_calls':6,'inner_query_charges':6,'exported_trace_queries':0,'exported_candidate_queries':0,'admissions':'manual56→60;4admitted1refused;notSQL','native_stats':'3OK+1CACHED;4HTTPtier','mock_HTTP_exchanges':4,'surviving_separate_walker_outcomes':1,'candidate_domain':'','programme_URLs':0})
expected=[('BudgetedFetcher.get','app.pipeline.read_budget'),('Fetcher.get','app.adapters.fetching'),('Fetcher._get','app.adapters.fetching'),('FakeSearchProvider.search','app.adapters.search.fake'),('LiveDiscoveryAdapter.discover','app.adapters.discovery.live_discovery'),('LiveDiscoveryAdapter._discover_one','app.adapters.discovery.live_discovery'),('CatalogueDiscoveryAdapter.discover','app.catalogue.discovery'),('CatalogueDiscoveryAdapter._enrich','app.catalogue.discovery')]
assert [(x['name'],x['module']) for x in raw['native_method_imports']]==expected
for row in raw['native_method_imports']:
 assert Path(row['source_file'])==REPO/'backend'/Path(*row['module'].split('.')).with_suffix('.py')
# Structuralreview of the executable: pure observation/method delegation,
# syntheticselection hooks only; no native Fetcher/provider/discovery-body replacement.
script=ast.parse((B/'proof_outer.py').read_text())
classes={n.name:n for n in script.body if isinstance(n,ast.ClassDef)}
spy=classes['TraceSpy'];assert len(spy.body)==2 #docstring+observermethod
method=spy.body[1];assert isinstance(method,ast.AsyncFunctionDef)
assert len(method.body)==2 and isinstance(method.body[1],ast.Return) and isinstance(method.body[1].value,ast.Await)
patchcalls=[n for n in ast.walk(script) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='patch' and n.func.attr=='object']
assert len(patchcalls)==2 and [c.args[1].value for c in patchcalls]==['registry','retrieve']
#Extract only narrowlyrelevant staticcode excerpts, not imported/executed modules.
excerpts={}
seams={
 'curated_outer':('backend/app/adapters/discovery/live_discovery.py',1131,1153),
 'catalogue_outer':('backend/app/catalogue/discovery.py',105,154),
 'late_candidate_apply':('backend/app/adapters/discovery/live_discovery.py',1946,1959),
 'production_fetcher_and_discovery_scope':('backend/app/pipeline/runner.py',158,199),
 'production_read_scope_cap':('backend/app/pipeline/runner.py',625,668),
 'production_discovery_transfer':('backend/app/pipeline/runner.py',742,773),
 'topic_missing_domain':('backend/app/adapters/requirements/web_requirements.py',584,605),
}
for name,(rel,start,end) in seams.items():
 text=(REPO/rel).read_text().splitlines();excerpts[name]={'path':rel,'source_sha256':sha(REPO/rel),'start':start,'end':end,'source_excerpt':'\n'.join(text[start-1:end])}
(HERE/'source-findings.json').write_text(json.dumps({'B_source18':source,'additional_method_source':additional,'seams':excerpts},indent=2)+'\n')
stop=Path(bp['STOP']['path']);assert sha(stop)==bp['STOP']['sha256']=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
result={'status':'ACCEPT_QUALIFIED_OUTER_OFF_PREPARATION_NO_REPLAY_NO_PATCH','checked_utc':datetime.now(UTC).isoformat(),'B_manifest_sha256':sha(B/'ready-manifest.json'),'B_selected_files':24,'B_selected_bytes':m['selected_bytes'],'source18_current_after999_d076_bound':True,'native_methods8_provenance_consistent':True,'method_delegation_unchanged_except_pure_trace_observation':True,'source_selection_patches_only':['registry','retrieve'],'rows':rows,'fact_pattern22_checked_not_reexecuted':True,'material_ambiguity_requiring_replay':False,'production_reachability':'Static reachable for native enabled or recordedON genuine research-job episode, sameuniversityscope and56alreadyadmittedgets, registry/catalogue row and incomplete discovery that reaches fallbacksearch. Curated productionroute isCatalogue no-row/no-explicitids fallback. Source defaultFalse current; syntheticcallback/sessionNone do not execute actualRunner/Worker/SQLfence or prove persisted/cancelled state.','ordinary_cancel_checkpoint_scope':'Read-onlystatic source review only: outer noncheckpoint UniversityReadStopped catches returnseed/unknown; checkpoint_busy rethrows; RunCancelled/LeaseLost/asyncioCancelledError propagate beyondthese outer catches. Catalogue TimeoutError keeps localoutercandidate. No newordinary/cancel/checkpoint execution here or inB22.','limitations':['No >6 fake/provider/vendor dispatch proven','candidate missingdomain and noURLs; currenttopic search earlyexits, scholarshipgate/scope stillcontrols','Canary serializesexported adaptertraces bycode; no canary/Runner/Worker or completepersistedreport executed','nativeFetchstats and standalonewalkeroutcomes survive; strict evaluation wrappercounters independent','identity-search prefix notexercised since registry_entry supplied','8methodprovenance includesFakeProviderfile not originally inB18; independentlybound here','no currentbaseline/qualitygain/default/retention/Worker/SQL/crash promise'],'STOP_sha256':sha(stop),'no_replays_imports_DB_Git_network_gold_scoring_primarywrites':True,'fresh_full':'SEPARATE_PENDING'}
(HERE/'audit-results.original.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'sources18_exact':True,'native_method_provenance':8,'checks22_consistent':True,'both_routes_fakequery6_export0':True,'stats4_walker1_survive':True,'no_replay':True,'STOP_unchanged':True}))

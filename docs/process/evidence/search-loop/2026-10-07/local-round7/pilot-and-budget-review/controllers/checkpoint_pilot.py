from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,re,shutil,subprocess

ROOT=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
ROUND=ROOT/'work/local-round7'
REPO=ROOT/'work/ashyq-apply'
DEST=REPO/'docs/process/evidence/search-loop/2026-10-07/local-round7/pilot-and-budget-review'
EXPECTED='7277c154bda838688268b7a07d4286ed8f4688ce'
BUNDLE=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(REPO),*a],text=True).strip()
assert git('rev-parse','HEAD')==EXPECTED and not git('status','--porcelain=v1')
assert not DEST.exists()
assert sha(ROOT/'work/development-STOP.json')=='dd669c6d73d89ba2586676b46b120e4c8af2ea95e4e15cd7ae75c554f9557cad'
assert not (ROUND/'provider-STOP.json').exists(), 'STOP observed; do not use successful-cohort checkpoint'
first=read(ROUND/'baseline-original10-v2/execution/summary.json')
last=read(ROUND/'remaining3-v4/execution/summary.json')
assert first['status']=='PROTOCOL_STOP_UNSCORED'
assert last['status']=='THREE_REMAINING_CASES_CAPTURED_UNSCORED'
assert all(not c['errors'] for c in last['case_results'])
prior=read(ROUND/'remaining3-v4/prior-revalidation.json')
assert all(sha(ROUND/'baseline-original10-v2'/n)==h for n,h in prior['immutable_files'].items())
assert read(ROUND/'reviews/expert_b-local-pilot-v4/final-review-manifest.json')
DEST.mkdir(parents=True)
origins={}
def cp(src,target):
    assert src.is_file() and not src.is_symlink()
    dest=DEST/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    origins[str(dest.relative_to(DEST))]={'original':str(src),'sha256':sha(src)}
def top(src,target):
    for p in sorted(src.iterdir()):
        if p.is_file() and not p.is_symlink() and p.suffix in {'.py','.json','.log','.md','.patch','.stdout','.stderr'}:cp(p,Path(target)/p.name)
def all_files(src,target):
    for p in sorted(src.rglob('*')):
        if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts:cp(p,Path(target)/p.relative_to(src))
for name in ['baseline-original10-v2','remaining3-v4']:
    all_files(ROUND/name,name)
for name in ['baseline-original10','remaining3-v3']:
    top(ROUND/name,name)
for n in ['local_pilot.py','local_pilot_v2.py','local_pilot_v3.py','local_pilot_v4.py','checkpoint_pilot.py']:
    cp(ROUND/n,Path('controllers')/n)
for n in ['expert_b-local-pilot','expert_b-local-pilot-v3','expert_b-local-pilot-v4','expert_a-worker-busy','expert_a-canary-job-protocol-plan','expert_a-readguard-port-plan']:
    top(ROUND/'reviews'/n,Path('reviews')/n)
top(ROUND/'worker-busy-proposal','worker-busy-proposal')
top(ROUND/'walker-stop-next','walker-stop-next')
all_files(ROUND/'reviews/expert_b-baseline-funnel','reviews/expert_b-baseline-funnel')
b=ROOT/'work/search-loop-round4/reviews/expert_b-readguard-v2'
top(b,'reviews/expert_b-readguard-v2')
for n in ['original','proposed']:all_files(b/n,Path('reviews/expert_b-readguard-v2')/n)
a=ROOT/'work/search-loop-round4/reviews/expert_a-readguard-v2-pg-plan/execution-v2'
top(a,'reviews/expert_a-readguard-v2-pg')
for p in [a,ROUND/'reviews/expert_a-worker-busy']:
    target='expert_a-readguard-v2-pg' if p==a else 'expert_a-worker-busy'
    for folder in ['raw','worker-pinned','candidate-pinned']:
        if (p/folder).exists():
            for f in (p/folder).rglob('*'):
                if f.is_file() and not f.is_symlink() and f.suffix in {'.py','.json','.log','.md','.patch','.stdout','.stderr'} and '__pycache__' not in f.parts:cp(f,Path('reviews')/target/folder/f.relative_to(p/folder))
prep=BUNDLE/'runs/20261007T220539Z-live-6d0aa77b'
for n in ['live-plan.json','source-manifest.json','summary.json']:cp(prep/n,Path('package-preparation')/n)
secrets=[]
for line in (REPO/'backend/.env').read_text().splitlines():
    m=re.match(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)',line)
    if m and re.search('KEY|TOKEN|SECRET|PASSWORD',m[1]):
        v=m[2].strip().strip('\"\'')
        if len(v)>=12 and not v.startswith(('#','${')):secrets.append(v.encode())
for p in DEST.rglob('*'):
    if p.is_file():assert not any(v in p.read_bytes() for v in secrets),'Configured secret detected'
rows=[]
for case in first['case_results']+last['case_results']:
    p=Path(case['capture_path']);c=read(p);o=c['observations'][0];b=c['config']['case_budgets'][case['case']]
    rows.append({'case':case['case'],'reads':b['fetcher_calls'],'queries':b['search_queries'],'active_ms':b['elapsed_ms'],'programme_urls_unscored':len(o['programme_urls']),'predictions_unscored':len(o['predictions']),'error':o['error'],'full_raw_available':(p.parent/(case['case']+'.raw.json')).exists(),'provider_failure':b['provider_failure']})
assert len(rows)==10 and len({r['case'] for r in rows})==10
assert all(r['reads']<=60 and r['queries']<=6 and r['active_ms']<=120000 and r['provider_failure'] is None for r in rows)
receipt={'created_at':datetime.now(timezone.utc).isoformat(),'kind':'selected immutable original10 local baseline and offline budget review checkpoint','source_head':EXPECTED,'snapshot_sha256':'b18f63fe7bf47773ffd6f97ef0cea45967a4fa061dd616da0aafa5723389826b','source_application_head':'5472a8337e38aecf55addacf5e02fa057477cb51','source_matches_full_checked_executable_files':True,'source_changed_during_capture':False,'cases':rows,'algorithm_case_count':10,'fetcher_calls':sum(r['reads'] for r in rows),'search_queries':sum(r['queries'] for r in rows),'provider_refusals':0,'quality_status':'UNSCORED','exact_programme_accuracy':'UNMEASURED','fact_precision_recall':'UNMEASURED','blind_expert_40_of_62':'NOT PERFORMED','all_old_trial_states_unchanged':True,'readguard_v2_applied':False,'worker_busy_fix_applied':False,'readguard_peer_tests':92,'independent_pg_passed':27,'independent_pg_retained_failed':1,'worker_original_failed':4,'worker_proposal_passed':12,'new_genuine_job_protocol':'PLAN ONLY, 11 grouped offline controls not run','controller_v3_rejected_tests':2,'controller_v4_passed_tests':61,'configured_secret_matches':0,'selected_files':origins,'excluded':'All runtime DB/PGDATA/WAL/socket/credentials/private Git; full omitted dependencies remain hash-pinned in original external work folders.'}
(DEST/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
(ROUND/'pilot-final-progress.json').write_text(json.dumps({k:v for k,v in receipt.items() if k!='selected_files'},ensure_ascii=False,indent=2)+'\n')
(DEST/'README.md').write_text('''# Fresh LOCAL original10 baseline and budget review\n\nTen universities were captured once each on the frozen7277c154 snapshot (application5472a833). The original seven-case v2 queue remains CLOSED PROTOCOL_STOP_UNSCORED; Toronto was a bounded page-cap outcome. Offline protocol repair did not rewrite it. Rejected v3 was never executed; independently61-pass v4 ran only HKU/NTU/KAIST. The combined cohort remains UNSCORED: returned URL/prediction counts are not correct facts or precision/recall. No model calls, HELDOUT150, resumed old experts or production changes.\n\nReadguard v2 passed92 offline controls; independent realPG27pass/1preservedWorker.fail red. Separate typedWorker-busy proposal12pass, original4red retained. No application source changes/default promotion from those proposals. Future genuineJob experiment and actual-module test port are plans, not executed evidence.\n\nFetcher calls count cache/failed/get admissions; network HTTP requests are different. Active120s strict envelope includes setup, cancellation and persistence, with117s source-work +3s reserve; parentstartup/cleanup135s cap is separate. Local location does not establish Fly accessibility or production120s protection. Full terminal raw is absent for bounded source-deadline cases and stays marked missing.\n\nReceipt pins every selected copied file. Runtime databases, sockets, credentials and privateGit are excluded. Original local-runner snapshot and external review folders remain the complete source of omitted dependencies.\n''')
print(json.dumps({'archived_files':len(origins),'bytes':sum(p.stat().st_size for p in DEST.rglob('*') if p.is_file()),'receipt_sha256':sha(DEST/'receipt.json'),'reads':receipt['fetcher_calls'],'queries':receipt['search_queries'],'cases':rows},indent=2))

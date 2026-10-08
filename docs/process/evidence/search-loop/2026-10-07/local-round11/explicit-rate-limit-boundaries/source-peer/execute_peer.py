"""Own finite executor; no app imported here, one fresh denied-transport process/case."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import subprocess

B=Path(__file__).resolve().parent
PYTHON=B.parents[1]/'ashyq-apply/backend/.venv/bin/python'
plan=json.loads((B/'REPLAY-PLAN.json').read_text())
tasks=[('on',s) for s in plan['ON_scenarios']]+[('off',s) for s in plan['OFF_comparators']]
tasks += [('independent',s) for s in ['native-precreated','native-429-to-meta','native-meta-to-429','local-retrieval-charge','synthetic-status500']]

def run(task):
    mode,case=task
    env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
    args=[str(PYTHON),str(B/('peer_control.py' if mode=='independent' else 'run_control.py'))]
    args += [case] if mode=='independent' else [mode,case,'native-replay']
    proc=subprocess.run(args,cwd=B,env=env,text=True,capture_output=True,timeout=30)
    path=B/'process-logs'/f'{case.replace(":","-")}.{mode}.log'
    path.parent.mkdir(exist_ok=True);assert not path.exists();path.write_text(proc.stdout+proc.stderr)
    result=B/'independent-controls'/f'{case}.json' if mode=='independent' else B/'native-replay'/f'{case.replace(":","-")}.{mode}.json'
    return {'mode':mode,'scenario':case,'exit':proc.returncode,'log':str(path.relative_to(B)),'log_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'result':str(result.relative_to(B)) if result.exists() else None}

with ThreadPoolExecutor(max_workers=3) as pool:
    executions=list(pool.map(run,tasks))
summary={'execution':executions,'counts':{},'whole_output_equality':[]}
for mode in ['on','off','independent']:
    records=[e for e in executions if e['mode']==mode]
    checks=[c for e in records if e['result'] for c in json.loads((B/e['result']).read_text())['checks']]
    summary['counts'][mode]={'PASS':sum(c['status']=='PASS' for c in checks),'RED':sum(c['status']=='RED' for c in checks),'exceptions':sum(e['result'] is None or e['exit'] not in [0,1] for e in records),'scenarios':len(records),'assertions':len(checks)}
for case in plan['normal_equality']:
    old,new=[json.loads((B/'native-replay'/f'{case.replace(":","-")}.{mode}.json').read_text()) for mode in ['off','on']]
    keys=['outputs','query_seam_attempts','mock_HTTP_events','mock_HTTP_counts','fake_clock_sleeps']
    summary['whole_output_equality'].append({'scenario':case,'status':'PASS' if all(old[k]==new[k] for k in keys) else 'RED','keys':keys})
path=B/'peer-execution.json';assert not path.exists();path.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'counts':summary['counts'],'equality':summary['whole_output_equality']}))
for row in executions:
    if row['mode']!='off' and row['exit']!=0:
        print(row)

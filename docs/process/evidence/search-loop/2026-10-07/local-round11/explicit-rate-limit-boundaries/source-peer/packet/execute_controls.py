from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import subprocess
import sys

B=Path(__file__).resolve().parent
REPO=B.parents[1]/'ashyq-apply/backend'
SCENARIOS=[
 'factory:meta','factory:no-retry','factory:http429','factory:success','factory:transport','factory:timeout',
 'factory:meta-false','factory:meta-one','factory:meta-string','factory:vendor-text','factory:vendor-error',
 'retrieval:meta','retrieval:no-retry','retrieval:http429','retrieval:success','retrieval:transport','retrieval:timeout','retrieval:vendor-error',
 'caller:single-meta','caller:multi-meta','caller:single-429','caller:multi-429','caller:single-success','caller:multi-success',
 'native:expiry','native:recovery-meta','retrieval:meta-unwrapped',
 'state:stamp','state:expiry','state:isolation','state:stale','state:reset','state:string-reason','state:vendor-text','state:429-untyped','state:500-typed','state:legacy-float'
]

def run(args):
 mode,case=args
 env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
 command=[str(REPO/'.venv/bin/python'),str(B/'run_control.py'),mode,case,sys.argv[1]]
 result=subprocess.run(command,cwd=REPO,env=env,text=True,capture_output=True,timeout=30)
 log=B/sys.argv[1]/(case.replace(':','-')+'.'+mode+'.log')
 log.parent.mkdir(parents=True,exist_ok=True);assert not log.exists();log.write_text(result.stdout+result.stderr)
 return {'mode':mode,'scenario':case,'exit':result.returncode,'stdout':result.stdout,'log':str(log),'sha256':hashlib.sha256(log.read_bytes()).hexdigest()}

assert len(sys.argv)==2
out=B/sys.argv[1]/'execution.json';assert not out.exists()
with ThreadPoolExecutor(max_workers=4) as pool:
 results=list(pool.map(run,[(mode,case) for case in SCENARIOS for mode in ['off','on']]))
summary={'execution':results,'counts':{},'whole_output_equality':[]}
for mode in ['off','on']:
 rows=[]
 for result in results:
  if result['mode']!=mode:continue
  path=B/sys.argv[1]/(result['scenario'].replace(':','-')+'.'+mode+'.json')
  if path.exists():rows.extend(json.loads(path.read_text())['checks'])
 summary['counts'][mode]={'PASS':sum(row['status']=='PASS' for row in rows),'RED':sum(row['status']=='RED' for row in rows),'exceptions':sum(row['exit'] not in [0,1] or not (B/sys.argv[1]/(row['scenario'].replace(':','-')+'.'+mode+'.json')).exists() for row in results if row['mode']==mode),'total':len(rows)}
normal=['native:recovery-meta']+[case for case in SCENARIOS if case.startswith(('factory:','retrieval:','caller:')) and not case.endswith(('meta','429','no-retry','meta-unwrapped'))]
for case in normal:
 paths=[B/sys.argv[1]/(case.replace(':','-')+'.'+mode+'.json') for mode in ['off','on']]
 if all(path.exists() for path in paths):
  old,new=[json.loads(path.read_text()) for path in paths]
  equal=all(old[key]==new[key] for key in ['outputs','query_seam_attempts','mock_HTTP_events','mock_HTTP_counts','fake_clock_sleeps'])
  summary['whole_output_equality'].append({'scenario':case,'status':'PASS' if equal else 'RED','compared':['outputs','query_seam_attempts','mock_HTTP_events','mock_HTTP_counts','fake_clock_sleeps']})
out.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'counts':summary['counts'],'normal_equality':{status:sum(row['status']==status for row in summary['whole_output_equality']) for status in ['PASS','RED']}}))
for row in results:
 if row['mode']=='on' and row['exit']!=0:print(row['stdout'] or row['log'])

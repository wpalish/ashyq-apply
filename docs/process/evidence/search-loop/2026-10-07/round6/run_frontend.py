"""Required local frontend gates; full stdout retained, no hosted jobs."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'ashyq-apply'
OUT=ROOT/'gates'
OUT.mkdir(exist_ok=True)
record={'started_at':datetime.now(timezone.utc).isoformat(),'commands':[]}
for name,args in [('frontend-typecheck',['npm','run','typecheck']),('frontend-lint',['npm','run','lint']),
    ('frontend-tests',['npm','test','--','--run']),('frontend-build',['npm','run','build'])]:
    with (OUT/(name+'.log')).open('w') as log:
        result=subprocess.run(args,cwd=REPO/'frontend',stdout=log,stderr=subprocess.STDOUT)
    record['commands'].append({'name':name,'arguments':args,'exit_code':result.returncode})
    (OUT/'frontend-gates.json').write_text(json.dumps(record,indent=2)+'\n')
    print(name,result.returncode,flush=True)
    if result.returncode:break
record['finished_at']=datetime.now(timezone.utc).isoformat()
(OUT/'frontend-gates.json').write_text(json.dumps(record,indent=2)+'\n')
assert len(record['commands'])==4 and all(c['exit_code']==0 for c in record['commands'])

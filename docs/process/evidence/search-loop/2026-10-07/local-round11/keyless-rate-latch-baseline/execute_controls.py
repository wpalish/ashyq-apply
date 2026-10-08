"""Each control scenario receives a fresh child module/latch state; no reset call."""
import hashlib
import json
import subprocess
from datetime import UTC,datetime
from pathlib import Path

B=Path(__file__).resolve().parent
PY=B.parents[1]/'ashyq-apply/backend/.venv/bin/python'
CASES=['factory-meta-native','factory-meta-no-retry','retrieval-meta-native','retrieval-meta-no-retry',
    'factory-http429','retrieval-http429','factory-success','retrieval-success','factory-transport','factory-timeout','factory-meta-false']


def main():
    plan={'created_utc':datetime.now(UTC).isoformat(),'cases':CASES,'child_source_sha256':hashlib.sha256((B/'run_case.py').read_bytes()).hexdigest(),
        'protocol':'Fresh isolated interpreter per case. Original source failure RED exit codes expected; every raw retained. No source method replacement, real calls, reset or STOP write.'}
    p=B/'execution-plan.json';assert not p.exists();p.write_text(json.dumps(plan,indent=2)+'\n')
    results=[]
    for name in CASES:
        log=B/(name+'.original.log');assert not log.exists()
        with log.open('wb') as output:
            child=subprocess.run([str(PY),str(B/'run_case.py'),name],cwd=B,stdout=output,stderr=subprocess.STDOUT,check=False)
        path=B/(name+'.original.json')
        results.append({'scenario':name,'exit_code':child.returncode,'raw_sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'counts':json.loads(path.read_text())['counts'] if path.exists() else None})
    p=B/'executions.original.json';assert not p.exists();p.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()

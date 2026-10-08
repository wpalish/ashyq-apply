"""Mock-only external controls: pin before and after each invocation, preserve every raw."""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

B=Path(__file__).resolve().parent
PY=B.parents[1]/'ashyq-apply/backend/.venv/bin/python'
manifest=json.loads((B/'source-manifest.final.json').read_text())


def source_hashes():
    return {rel:hashlib.sha256((B/'proposed'/rel).read_bytes()).hexdigest() for rel in manifest['proposed_sources']}


def main():
    original=source_hashes()
    assert original==manifest['proposed_sources']
    commands=[['run_controls.py','controls.pinned.json'],['run_scope_ownership.py','scope-ownership.pinned.json'],
        ['run_boundary_controls.py','boundary-controls.executed-pinned.json'],['run_worker_controls.py','worker.executed-pinned']]
    plan={'created_utc':datetime.now(UTC).isoformat(),'source_sha256_before':original,'commands':commands,
        'protocol':'Denied transports and mock provider/source transports; genuine own SQLite Worker only in last invocation',
        'controls_exit0_is_not_acceptance':'Raw PASS/RED assertions determine status; original unmet assertions preserved.'}
    path=B/'pinned-control-execution.plan.json';assert not path.exists();path.write_text(json.dumps(plan,indent=2)+'\n')
    rows=[]
    for i,args in enumerate(commands):
        before=source_hashes();assert before==original
        log=B/f'pinned-command-{i+1}.log';assert not log.exists()
        with log.open('wb') as output:
            process=subprocess.run([str(PY),*args],cwd=B,stdout=output,stderr=subprocess.STDOUT,check=False)
        after=source_hashes();assert after==original
        rows.append({'argv':[str(PY),*args],'exit_code':process.returncode,'log':log.name,
            'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'source_sha256_before':before,'source_sha256_after':after})
    result={'completed_utc':datetime.now(UTC).isoformat(),'executions':rows,'source_sha256_after_all':source_hashes()}
    path=B/'pinned-control-execution.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{'command':r['argv'][1], 'exit_code':r['exit_code']} for r in rows]))


if __name__=='__main__':
    main()

"""Own isolated pgserver lifecycle; preserve a failed test exit and cleanup evidence."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parent
REPO=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend')
STOP=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/development-STOP.json')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert os.geteuid()!=0
assert sha(BASE/'candidate-pinned/ready-manifest.json')=='236e9a53667c86c0b14a04807492804402604d05a5a32ba670fb97915f84c2a4'
manifest=json.loads((BASE/'candidate-pinned/ready-manifest.json').read_text())
for name,value in manifest['proposed_source_sha256'].items():assert sha(BASE/'candidate-pinned/proposed'/name)==value
for category in ['original_source_sha256','unchanged_dependency_sha256']:
 for name,value in manifest[category].items():assert sha(REPO/name)==value,(name,sha(REPO/name),value)
stop_before=sha(STOP)
assert stop_before==manifest['sticky_stop_sha256']
helper=REPO/'scripts/pg.py'
spec=importlib.util.spec_from_file_location('independent_local_pg_helper',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
data=BASE/'runtime'/'isolated-cluster-01'/'pgdata'
data.parent.mkdir(parents=True,exist_ok=False)
server=None;pid=None;socket_path=None;code=99
record={'started_at':datetime.datetime.now(datetime.UTC).isoformat(),'helper_sha256':sha(helper),'pgdata':str(data),'ready_manifest_sha256':sha(BASE/'candidate-pinned/ready-manifest.json'),'patch_sha256':manifest['patch_sha256'],'stop_before':stop_before,'tests_run':False}
try:
 server,uri=module.start(data)
 info=server.get_postmaster_info();pid=info.pid;socket_path=info.socket_path
 record.update({'own_server_pid':pid,'own_socket_path':str(socket_path),'tcp_hostname':info.hostname,'cleanup_mode':server.cleanup_mode,'tests_run':True})
 assert info.hostname is None and info.socket_dir is not None and info.pgdata.resolve()==data.resolve()
 env={**os.environ,'UNIMATCH_DATABASE_URL':uri,'UNIMATCH_PGDATA':str(data),'PYTHONDONTWRITEBYTECODE':'1','READGUARD_REVIEW_TARGET':'proposal','PYTHONPATH':str(REPO)}
 args=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(BASE/'runtime/pytest'),str(BASE/'test_independent_pg.py')]
 started=time.monotonic()
 with (BASE/'pytest-actual-pg.stdout').open('w') as out,(BASE/'pytest-actual-pg.stderr').open('w') as err:
  result=subprocess.run(args,cwd=BASE,env=env,stdout=out,stderr=err,timeout=90)
  code=result.returncode
 record.update({'pytest_exit_code':code,'pytest_wall_seconds':time.monotonic()-started,'argv':args})
finally:
 if server is not None:
  server.cleanup()
  import psutil
  record['own_pid_gone']=not psutil.pid_exists(pid)
  record['own_socket_absent']=not socket_path.exists()
  assert record['own_pid_gone'] and record['own_socket_absent']
 record['stop_after']=sha(STOP)
 record['finished_at']=datetime.datetime.now(datetime.UTC).isoformat()
 record['PG_12_status']='PASS' if record.get('own_pid_gone') and record.get('own_socket_absent') and record['stop_after']==stop_before else 'FAIL'
 (BASE/'raw/PG-12-lifecycle.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'pytest_exit_code':code,'PG-12':record['PG_12_status'],'own_pid_gone':record.get('own_pid_gone'),'own_socket_absent':record.get('own_socket_absent')},indent=2))
raise SystemExit(code)

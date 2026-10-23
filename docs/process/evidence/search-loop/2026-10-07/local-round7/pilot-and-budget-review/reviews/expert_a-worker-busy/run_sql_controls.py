from pathlib import Path
import datetime,hashlib,importlib.util,json,os,subprocess,sys,time
BASE=Path(__file__).resolve().parent
REPO=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend')
STOP=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/development-STOP.json')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert os.geteuid()!=0
assert sha(BASE/'worker-pinned/worker.proposed.py')=='e6b7561dbb0b4fa950869934dfb68c1787be82d8a454af43de78dc3a7cb944df'
assert sha(BASE/'worker-pinned/worker.original.py')==sha(REPO/'app/jobs/worker.py')=='491f5ccdeadd3556ad4e5bf6bfc2b4578207ef2cce129eb2fcd57b4b4e0e6681'
assert sha(BASE/'candidate-pinned/ready-manifest.json')=='236e9a53667c86c0b14a04807492804402604d05a5a32ba670fb97915f84c2a4'
m=json.loads((BASE/'candidate-pinned/ready-manifest.json').read_text())
for category in ['original_source_sha256','unchanged_dependency_sha256']:
 for name,value in m[category].items():assert sha(REPO/name)==value
for name,value in m['proposed_source_sha256'].items():assert sha(BASE/'candidate-pinned/proposed'/name)==value
stop_before=sha(STOP);assert stop_before==m['sticky_stop_sha256']
helper=REPO/'scripts/pg.py';assert sha(helper)=='4f8f61aafc6e388ddd67eb045a01843814083ec397e7c83cc343529db76d21ab'
spec=importlib.util.spec_from_file_location('own_worker_pg_helper',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
data=BASE/'runtime/cluster-01/pgdata';data.parent.mkdir(parents=True,exist_ok=False)
server=None;record={'started_at_utc':datetime.datetime.now(datetime.UTC).isoformat(),'pgdata':str(data),'source_worker_original_sha256':sha(REPO/'app/jobs/worker.py'),'proposed_worker_sha256':sha(BASE/'worker-pinned/worker.proposed.py'),'STOP_before':stop_before,'suites':[]}
try:
 server,uri=module.start(data);info=server.get_postmaster_info();pid=info.pid;socket_path=info.socket_path
 assert info.hostname is None and info.socket_dir is not None
 record.update({'server_pid':pid,'own_socket':str(socket_path),'listen_addresses':'empty Unix-socket-only'})
 for mode in ['baseline','proposal']:
  env={**os.environ,'UNIMATCH_DATABASE_URL':uri,'UNIMATCH_PGDATA':str(data),'PYTHONDONTWRITEBYTECODE':'1','READGUARD_REVIEW_TARGET':'proposal','WORKER_REVIEW_TARGET':mode,'PYTHONPATH':str(REPO)}
  argv=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(BASE/'runtime'/('pytest-'+mode)),str(BASE/'test_worker_busy.py')]
  started=time.monotonic()
  with (BASE/('pytest-'+mode+'.stdout')).open('w') as out,(BASE/('pytest-'+mode+'.stderr')).open('w') as err:
   result=subprocess.run(argv,cwd=BASE,env=env,stdout=out,stderr=err,timeout=90)
  record['suites'].append({'mode':mode,'exit_code':result.returncode,'wall_seconds':time.monotonic()-started,'argv':argv})
finally:
 if server is not None:
  server.cleanup();import psutil
  record.update({'own_pid_gone':not psutil.pid_exists(pid),'own_socket_absent':not socket_path.exists()})
  assert record['own_pid_gone'] and record['own_socket_absent']
 record['STOP_after']=sha(STOP);assert record['STOP_after']==stop_before
 record['finished_at_utc']=datetime.datetime.now(datetime.UTC).isoformat()
 (BASE/'lifecycle.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'suites':record['suites'],'cleanup':{'pid_gone':record.get('own_pid_gone'),'socket_absent':record.get('own_socket_absent')}},indent=2))
raise SystemExit(next((x['exit_code'] for x in record['suites'] if x['mode']=='proposal'),99))

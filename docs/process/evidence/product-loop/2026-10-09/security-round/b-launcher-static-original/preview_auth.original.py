"""Root-owned finite synthetic auth preview. No worker, seed DB or live provider."""
from pathlib import Path
import fcntl
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
TASK=ROOT/'work/security-round1'
BUNDLE=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
STOP=ROOT/'work/local-round7/provider-STOP.json'
STOP_SHA='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def finish_child(process):
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=4)
    for _ in range(40):
        rows=subprocess.check_output(['ps','-axo','pgid=,stat='],text=True).splitlines()
        live=any(len(parts:=row.split())==2 and int(parts[0])==process.pid and not parts[1].startswith('Z') for row in rows)
        if not live:return
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:return
        time.sleep(.1)
    raise RuntimeError('Owned process group survived cleanup')

go_path=Path(sys.argv[1]).resolve()
assert go_path.parent==TASK
go=json.loads(go_path.read_text())
assert sha(STOP)==STOP_SHA and sha(Path(__file__))==go['launcher_sha256']
helper=(TASK/go['verifier_relative']).resolve()
assert helper.is_relative_to(TASK) and sha(helper)==go['helper_sha256']
launch_peer=TASK/go['launcher_review_relative']
assert sha(launch_peer)==go['launcher_review_sha256']
review=json.loads(launch_peer.read_text())
assert review['status']=='QUALIFIED_ACCEPT' and review['launcher_sha256']==go['launcher_sha256']
assert review['helper_sha256']==go['helper_sha256']
verifier=module(helper,'approved_security_ui_verifier')
assert sha(BUNDLE/'run_local.py')==go['runner_sha256']
runner=module(BUNDLE/'run_local.py','approved_local_runner')
children=[]
with (BUNDLE/'.run.lock').open('r') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    bound=verifier.verify(go)
    runner.check_ports()
    out=Path(bound['fresh_preview_root']);source=Path(bound['source'])
    assert not out.exists();out.mkdir()
    config=json.loads((BUNDLE/'config.json').read_text())
    env=runner.safe_env(Path(config['node_bin']),out)
    env.update({'UNIMATCH_DEMO_MODE':'true','UNIMATCH_AUTH_ENABLED':'true',
        'UNIMATCH_AUTH_REGISTRATION_ENABLED':'true','UNIMATCH_COOKIE_SECURE':'false','PORT':'8099',
        'UNIMATCH_ENABLE_BROWSER_TIER':'false','UNIMATCH_SEARCH_PROVIDER':'none',
        'UNIMATCH_DECISION_PROVIDER':'none','UNIMATCH_PAYMENTS_ENABLED':'false',
        'UNIMATCH_PASSWORD_RESET_ENABLED':'false','UNIMATCH_PASSWORD_SCRYPT_LOG2':'14',
        'UNIMATCH_AUTH_RATE_LIMIT_PER_MINUTE':'60','UNIMATCH_MODERATOR_USER_IDS':''})
    database=out/'runtime/checks.db'
    assert not database.exists() and env['UNIMATCH_DATABASE_URL']=='sqlite:///'+str(database)
    runner.write_json(out/'go-copy.json',go)
    runner.write_json(out/'bound-inputs.json',bound)
    started=time.monotonic()
    try:
        for name,command,cwd in [('api',['bash','run.sh'],source/'backend'),('frontend',['npm','run','dev'],source/'frontend')]:
            log=(out/(name+'.log')).open('wb')
            process=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            children.append((process,log))
        runner.write_json(out/'preview-processes.json',{'owned_pids':[p.pid for p,_ in children],
            'head':go['actual_full_head'],'initial_snapshot_sha256':go['initial_source_tree_sha256'],
            'synthetic':True,'database':str(database),'database_existed_before':False,'database_copied':False,
            'auth_enabled':True,'provider':'none','decision_provider':'none','worker_started':False,
            'max_seconds':900,'lock_held_for_lifetime':True,'child_commands':[['bash','run.sh'],['npm','run','dev']]})
        ready={}
        while time.monotonic()-started<60 and len(ready)<2:
            if any(p.poll() is not None for p,_ in children):raise RuntimeError('Owned preview server exited before readiness')
            for name,url in [('api','http://127.0.0.1:8099/api/health'),('frontend','http://127.0.0.1:5173/')]:
                if name in ready:continue
                try:
                    with urllib.request.urlopen(url,timeout=.5) as response:
                        assert response.status==200
                        ready[name]={'status':response.status}
                except OSError:pass
            time.sleep(.2)
        assert len(ready)==2
        with urllib.request.urlopen('http://127.0.0.1:8099/api/auth/status',timeout=2) as response:
            status=json.load(response)
            assert status['enabled'] is True and status['authenticated'] is False
            assert response.headers.get('cache-control')=='no-store'
            runner.write_json(out/'initial-auth-response.json',{'body':status,'cache_control':response.headers['cache-control'],'synthetic':True})
        print('READY http://127.0.0.1:5173/#/legal HEAD '+go['actual_full_head'],flush=True)
        while all(p.poll() is None for p,_ in children) and time.monotonic()-started<900:
            assert sha(STOP)==STOP_SHA
            time.sleep(.5)
    except KeyboardInterrupt:pass
    finally:
        errors=[]
        for process,log in children:
            try:finish_child(process)
            except BaseException as error:errors.append({'pid':process.pid,'type':type(error).__name__,'message':str(error)})
            finally:log.close()
        runner.write_json(out/'cleanup-receipt.json',{'owned_pids':[p.pid for p,_ in children],
            'errors':errors,'lock_held_during_cleanup':True,'all_owned_cleanup_attempts_complete':True,
            'elapsed_seconds':time.monotonic()-started})
        assert not errors and sha(STOP)==STOP_SHA
        runner.check_ports()

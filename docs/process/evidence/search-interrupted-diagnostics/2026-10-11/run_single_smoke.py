"""Owner-authorized single algorithm smoke. No experts, model, scoring or retry."""
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026')
SOURCE = BASE / 'integration-2026-10-11/source'
ROOT = BASE / 'continuation-2026-10-11/groningen-single-smoke'
PINS = SOURCE / 'docs/process/evidence/product-integration/2026-10-11/final/backend-full/sqlite/source-before.json'
OLD_STOP = BASE / 'local-runner/CURRENT_STATE/provider-STOP.original.json'
OLD_SHA = '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
EXPECTED_HEAD = '7c8e23a723b639a8824d9b9119352e0beff7e514'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def git(*args):
    return subprocess.check_output(['git','-C',str(SOURCE),*args], text=True).strip()

def store(name, value):
    with (ROOT / name).open('x', encoding='utf-8') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')

def main():
    pins = json.loads(PINS.read_text())
    pins_sha = sha(PINS)
    def verify():
        assert git('rev-parse','HEAD') == EXPECTED_HEAD
        assert git('status','--porcelain') == ''
        assert sha(OLD_STOP) == OLD_SHA
        assert sha(PINS) == pins_sha
        assert len(pins) == 585
        assert all(not (SOURCE / name).is_symlink() and sha(SOURCE / name) == digest for name,digest in pins.items())
        assert not (SOURCE / 'backend/.env').exists()
    verify()
    assert sys.version_info[:2] == (3,12)
    assert Path(sys.executable).resolve() == (SOURCE / 'backend/.venv/bin/python').resolve()
    with (BASE / 'local-runner/.run.lock').open('r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verify()
        ROOT.mkdir(exist_ok=False)
        command = [str(SOURCE/'backend/.venv/bin/python'),'-m','evaluation.research.live',
                   '--live','--case','groningen','--search-provider','exa_mcp',
                   '--strict-expert-budget','--shared-query-budget','--fenced-research-job',
                   '--no-university-read-budget','--seconds-per-case','120','--max-pages','60',
                   '--finalization-reserve-ms','1000','--stop-file',str(ROOT/'FIRST-REFUSAL.json'),
                   '--out',str(ROOT/'capture')]
        env = {key:os.environ[key] for key in ('HOME','PATH','TMPDIR','LANG','LC_ALL','SSL_CERT_FILE','SSL_CERT_DIR') if key in os.environ}
        env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',PYTHONIOENCODING='utf-8',
                   UNIMATCH_DEMO_MODE='false',UNIMATCH_ENABLE_BROWSER_TIER='false',
                   UNIMATCH_RESPECT_ROBOTS='true',UNIMATCH_SEARCH_PROVIDER='exa_mcp',
                   UNIMATCH_FETCH_CONTACT='https://github.com/wpalish/ashyq-apply')
        store('launch.original.json', {'time_utc':datetime.now(timezone.utc).isoformat(),
              'authorization_basis':'Human owner replied further do it after the explicit single-Groningen 6-query/60-read/120-second request; not a paired-pilot grant artifact.',
              'source_head':EXPECTED_HEAD,'source_pins_sha256':pins_sha,'source_pins_count':len(pins),
              'retained_stop_sha256':OLD_SHA,'argv':command,'cwd':str(SOURCE/'backend'),
              'comparison_eligible':False,'score':'NOT_MEASURED','experts_or_models_dispatched':False})
        sys.path.insert(0,str(SOURCE/'backend'))
        from evaluation.research.expert.selector import run_owned_process
        error = None
        try:
            completed=run_owned_process(command,cwd=SOURCE/'backend',env=env,timeout=135,text=True)
            process={'stdout':completed.stdout,'stderr':completed.stderr,'returncode':completed.returncode}
        except BaseException as exc:
            error=type(exc).__name__
            process={'error_type':error,'stdout':str(getattr(exc,'stdout','') or ''),
                     'stderr':str(getattr(exc,'stderr','') or ''),
                     'cleanup_incomplete':getattr(exc,'cleanup_incomplete',None)}
        store('process.original.json',process)
        try:
            verify()
            source_unchanged=True
        except BaseException as exc:
            source_unchanged=False
            error=error or type(exc).__name__
        stop=ROOT/'FIRST-REFUSAL.json'
        result={'time_utc':datetime.now(timezone.utc).isoformat(),
                'status':'STOPPED_UNSCORED' if stop.exists() or error or process.get('returncode')!=0 else 'TERMINAL_UNSCORED_REQUIRES_RAW_REVIEW',
                'source_unchanged':source_unchanged,'error_type':error,'process_returncode':process.get('returncode'),
                'first_refusal_present':stop.exists(),'first_refusal_sha256':sha(stop) if stop.exists() else None,
                'retained_stop_unchanged':sha(OLD_STOP)==OLD_SHA,'comparison_eligible':False,
                'no_expert_model_scoring_retry_deploy':True}
        store('TERMINAL.json',result)
        print(json.dumps(result),flush=True)
        return 0 if result['status']=='TERMINAL_UNSCORED_REQUIRES_RAW_REVIEW' else 2

if __name__=='__main__':
    raise SystemExit(main())

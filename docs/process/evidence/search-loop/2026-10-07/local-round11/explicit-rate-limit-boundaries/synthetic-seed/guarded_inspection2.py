"""Finite actual frozen-source commands; socket/DNS denied before app imports."""
from __future__ import annotations
import atexit
import hashlib
import json
import os
import runpy
import socket
import sqlite3
import sys
from pathlib import Path

B=Path(__file__).resolve().parent
PLAN=json.loads((B/'PLAN.json').read_text())
SOURCE=Path(PLAN['snapshot']);BACKEND=SOURCE/'backend'
ACT=sys.argv[1]
assert ACT == 'inspect2'
assert Path.cwd()==BACKEND
assert not (BACKEND/'.env').exists() and not (BACKEND/'.env').is_symlink()
assert os.environ['UNIMATCH_DEMO_MODE']=='true'
assert os.environ['UNIMATCH_ENABLE_BROWSER_TIER']=='false'
assert os.environ['UNIMATCH_SEARCH_PROVIDER']=='none'
DB=B/'runtime/seed.db'
assert os.environ['UNIMATCH_DATABASE_URL']==f'sqlite:///{DB}'
assert os.environ['UNIMATCH_CACHE_DIR']==str(B/'runtime/httpcache')
assert os.environ['UNIMATCH_EXPORT_DIR']==str(B/'runtime/exports')
sys.path.insert(0,str(BACKEND))
ATTEMPTS=[]
def deny(*args,**kwargs):
    ATTEMPTS.append({'kind':'real socket/DNS attempt denied','action':ACT})
    raise RuntimeError('FORBIDDEN_NETWORK_ATTEMPT_ABORT')
socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
socket.getaddrinfo=deny

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
PINS=json.loads((B/'verified-source-prefix.json').read_text())
BEFORE={r:sha(SOURCE/r) for r in PINS}
assert BEFORE==PINS

def finish():
    after={r:sha(SOURCE/r) for r in PINS}
    result={'action':ACT,'network_attempts':ATTEMPTS,'snapshot_prefix_999_before_after_equal':BEFORE==after,'source_manifest_sha256':PLAN['source_manifest_sha256'],'source_tree_sha256':PLAN['source_tree_sha256'],'cwd':str(Path.cwd()),'db':str(DB),'safe_explicit_flags':{'demo':True,'browser':False,'search_provider':'none'},'primaryDB_fullsuiteDB_env_read':False}
    out=B/(ACT+'.execution.json');assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
    if ATTEMPTS or BEFORE!=after:raise RuntimeError('Safety/source invariant violated')
atexit.register(finish)

if ACT in {'heads','migrate'}:
    sys.argv=['alembic','-c',str(BACKEND/'alembic.ini'),'heads'] if ACT=='heads' else ['alembic','-c',str(BACKEND/'alembic.ini'),'upgrade','head']
    runpy.run_module('alembic',run_name='__main__')
elif ACT=='seed':
    sys.argv=[str(BACKEND/'seed_demo.py')]
    runpy.run_path(str(BACKEND/'seed_demo.py'),run_name='__main__')
else:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    config=Config(str(BACKEND/'alembic.ini'));config.set_main_option('script_location',str(BACKEND/'migrations'))
    heads=ScriptDirectory.from_config(config).get_heads()
    assert len(heads)==1
    assert DB.is_file()
    with sqlite3.connect(f'file:{DB}?mode=ro',uri=True) as connection:
        current=[row[0] for row in connection.execute('SELECT version_num FROM alembic_version')]
        assert current==heads
        rows=connection.execute('SELECT university,eligibility,admissions_fit,funding_classification,bucket,user_decision FROM program_results ORDER BY score_total DESC').fetchall()
        run=connection.execute('SELECT stage,pages_checked,pages_failed,claims_recorded FROM research_runs').fetchall()
        assert len(run)==1
        assert rows and rows[0][0]=='University of Groningen'
        ubc=[row for row in rows if row[0]=='University of British Columbia']
        assert len(ubc)==1 and ubc[0][4]=='OUT_OF_BUDGET'
        assert all(row[5]=='undecided' for row in rows)
        result={'heads':heads,'database_revisions':current,'rows':len(rows),'first':rows[0][0],'UBC':{'university':ubc[0][0],'funding_classification':ubc[0][3],'bucket':ubc[0][4]},'run':{'stage':run[0][0],'pages_checked':run[0][1],'pages_failed':run[0][2],'claims_recorded':run[0][3]},'no_approve_all_undecided':True,'ordering_and_classifications':[{'university':r[0],'eligibility':r[1],'admissions_fit':r[2],'funding_classification':r[3],'bucket':r[4]} for r in rows]}
    (B/'inspection2.original.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='ordering_and_classifications'},indent=2))

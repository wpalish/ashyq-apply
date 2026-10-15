from pathlib import Path
import json,hashlib,fcntl,subprocess
s=Path(__file__).resolve().parent;b=s.parents[1];r=b/'work/unimatch-calendar-materials';lab=b/'product-platform/2026-10-12/g3-execution/source';lock=(b/'local-runner/.run.lock').open('r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);h=lambda raw:hashlib.sha256(raw).hexdigest();paths=['backend/app/api/routes_research.py','backend/app/api/routes_results.py','backend/app/pipeline/runner.py','backend/app/domain/profile_input_provenance.py','backend/app/schemas/research_read.py','backend/tests/test_research_input_provenance.py','backend/tests/test_result_read_freshness.py'];rows={}
for p in paths:
 raw=(r/p).read_bytes();assert(lab/p).read_bytes()==raw;rows[p]=h(raw)
 for folder in ['inputs6a-style1-preimages','inputs6a-style1']:
  q=s/folder/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
(s/'INPUTS_6A_STYLE1_GRANT.json').write_text(json.dumps({'paths':rows,'failure':'Native static6a1 Alembicheads PASS; Ruff7 import ordering only. External subset omitted package __init__.py so Ruff classified app/tests as third-party; no test execution.','scope':'Exact7 import order with known-first-party app/tests matching actual native source; whitespace formatting only, no source semantic/assertion change. Raw static failure retained.'},indent=2)+'\n')
f=r/'docs/process/HANDOFF.md';f.write_text(f.read_text().replace('## 5. NEXT STEP — exact and executable\n\n','## 5. NEXT STEP — exact and executable\n\n**[inputs6a style1] First native static headsPASS/Ruff7 import ordering. External subset lacked __init__.py and Ruff classified app/tests as third-party. Exact7 import-order/whitespace style using explicit package classification, no semantics/assertions changed; fresh static6a2. Native tests/full/FE read-warning integration NOT_RUN.**\n\n',1))
python=lab/'backend/.venv/bin/python';style=s/'inputs6a-style1';cmd=[str(python),'-m','ruff','check',str(style/'backend'),'--fix','--config',str(r/'backend/ruff.toml'),'--config','lint.isort.known-first-party=["app","tests"]'];subprocess.run(cmd,check=True,capture_output=True);subprocess.run([str(python),'-m','ruff','format',str(style/'backend'),'--config',str(r/'backend/ruff.toml')],check=True,capture_output=True);post={}
for p in paths:
 raw=(style/p).read_bytes()
 for tree in [r,lab]:assert h((tree/p).read_bytes())==rows[p];(tree/p).write_bytes(raw)
 post[p]={'preimage':rows[p],'postimage':h(raw)}
(s/'INPUTS_6A_STYLE1_APPLICATION.json').write_text(json.dumps({'status':'APPLIED_NOT_EXECUTED','paths':post},indent=2)+'\n');(s/'run_static_inputs6a2.py').write_text((s/'run_static_inputs6a1.py').read_text().replace('inputs-static6a1','inputs-static6a2'));fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

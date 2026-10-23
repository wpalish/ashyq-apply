from pathlib import Path
import hashlib,json,os
import test_worker_busy as tests
from app.pipeline import read_budget
p=Path(tests.wm.__file__).resolve()
expected=tests.BASE/'worker-pinned'/('worker.proposed.py' if tests.MODE=='proposal' else 'worker.original.py')
assert p==expected
modules=[]
manifest=json.loads((tests.BASE/'candidate-pinned/ready-manifest.json').read_text())
import importlib
for name,value in manifest['proposed_source_sha256'].items():
 module=importlib.import_module(name[:-3].replace('/','.'));source=Path(module.__file__).resolve();actual=hashlib.sha256(source.read_bytes()).hexdigest()
 assert actual==value and source==tests.BASE/'candidate-pinned/proposed'/name
 modules.append({'module':module.__name__,'path':str(source),'sha256':actual})
record={'worker_mode':tests.MODE,'worker_path':str(p),'worker_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'exact_proposed_modules':modules,'read_guard_default':read_budget.UNIVERSITY_READ_BUDGET,'control_class_identity_matches':getattr(tests.wm,'UniversityReadStopped',None) is tests.UniversityReadStopped if tests.MODE=='proposal' else 'baseline does not import typed budget control'}
(tests.BASE/'raw'/tests.MODE/'imports.json').write_text(json.dumps(record,indent=2)+'\n')

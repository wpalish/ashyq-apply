from pathlib import Path
import shutil,json,hashlib
O=Path(__file__).resolve().parent;R=O.parents[2]/'work/ashyq-apply';B=O/'runtime/backend';B.mkdir(parents=True)
for group in ('app','evaluation'):
 for p in (R/'backend'/group).rglob('*.py'):
  q=B/p.relative_to(R/'backend');q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
p=R/'backend/app/adapters/search/ontology.json';q=B/'app/adapters/search/ontology.json';q.write_bytes(p.read_bytes())
for p in (O/'proposed/backend').rglob('*.py'):
 q=B/p.relative_to(O/'proposed/backend');q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
(B/'tests').mkdir();(B/'tests/__init__.py').write_text('')
for n in ['ruff.toml','pyproject.toml','mypy.ini']:
 p=R/'backend'/n
 if p.exists():(B/n).write_bytes(p.read_bytes())
q=B/'evaluation/research/data/identity_bindings.reviewed.json';q.parent.mkdir(parents=True,exist_ok=True);q.write_text('{"version":"synthetic","bindings":[]}\n')
print(B)

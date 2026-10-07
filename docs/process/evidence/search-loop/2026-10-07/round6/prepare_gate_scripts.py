from pathlib import Path
root=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work');src=root/'search-loop-round5';dest=root/'search-loop-round6'
paths=['backend/app/adapters/page_classifier.py','backend/app/adapters/scholarship/web_scholarships.py','backend/evaluation/research/live.py','backend/tests/test_programme_funding_scope.py','backend/tests/test_programme_purpose_capture.py','backend/tests/fixtures/programme_funding/scope-controls.json','backend/tests/fixtures/programme_funding/wits-programme.html','backend/tests/fixtures/programme_funding/wits-programme.meta.json']
for name in ('run_gates.py','run_frontend.py','run_demo.py'):
 t=(src/name).read_text().replace('search-loop-round5','search-loop-round6')
 if name=='run_gates.py':
  start=t.index('paths = ');end=t.index('\nhashes',start);t=t[:start]+'paths = '+repr(paths)+t[end:]
 (dest/name).write_text(t)
print('Gate scripts prepared externally, no source changes or gates launched.')

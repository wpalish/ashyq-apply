"""Bind the actual passed full and declared PNG deltas, without running servers."""
from pathlib import Path
import hashlib
import json

TASK=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/security-round1')
BUNDLE=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
execution=json.loads((TASK/'native-queue-final/execution.json').read_text())
assert len(execution)==2 and execution[1]['suite']=='full' and execution[1]['exit_code']==0
assert len(execution[1]['owned_runs'])==1
owned=execution[1]['owned_runs'][0]
run=Path(owned['path'])
assert run.parent==BUNDLE/'runs' and sha(run/'summary.json')==owned['summary_sha256']
summary=json.loads((run/'summary.json').read_text())
manifest=json.loads((run/'source-manifest.json').read_text())
assert summary['status']=='passed' and len(summary['steps'])==13
assert all(row['exit_code']==0 for row in summary['steps']) and summary['source']==manifest
assert manifest['source_head']==(TASK/'final-head.txt').read_text().strip()
assert hashlib.sha256(json.dumps(manifest['files'],sort_keys=True).encode()).hexdigest()==manifest['source_tree_sha256']
source=Path(manifest['snapshot'])
assert source==run/'source'
delta=[]
for name,old in manifest['files'].items():
    path=source/name
    assert path.is_file() and not path.is_symlink(),name
    new=sha(path)
    if new!=old:
        assert name.startswith('docs/screenshots/') and name.endswith('.png'),name
        delta.append({'path':name,'before_sha256':old,'after_sha256':new})
delta_path=TASK/'post-export-view-full-delta.json'
assert not delta_path.exists()
delta_path.write_text(json.dumps({'status':'HASH_BOUND_DECLARED_E2E_PNG_DELTA',
    'source_head':manifest['source_head'],'initial_source_tree_sha256':manifest['source_tree_sha256'],
    'files':delta,'qualification':'Actual differences in initial declared map only; no final physical whole-tree equality claim.'},indent=2)+'\n')
go=json.loads((TASK/'c-export-view-final-ui-plan/binding-template.json').read_text())
static=TASK/'a-export-final-preview-static/receipt.json'
launcher_review=TASK/'a-export-final-preview-static/receipt.json'
go.update({'status':'ROOT_CONFIRMED_SOURCE_BOUND_UI_GO',
    'helper_sha256':sha(TASK/'c-export-view-final-ui-plan/verify_bound_ui_inputs.py'),
    'static_review_path':str(static),'static_review_sha256':sha(static),
    'source20_sha256':sha(TASK/'final-source-pins.json'),
    'applied_head_file_sha256':sha(TASK/'final-head.txt'),
    'execution_sha256':sha(TASK/'native-queue-final/execution.json'),'full_record_index':1,
    'actual_full_head':manifest['source_head'],'actual_full_branch':manifest['source_branch'],
    'full_summary_sha256':sha(run/'summary.json'),'full_manifest_sha256':sha(run/'source-manifest.json'),
    'initial_source_tree_sha256':manifest['source_tree_sha256'],
    'artifact_delta_path':str(delta_path),'artifact_delta_sha256':sha(delta_path),
    'config_input_pins':{name:manifest['files'][name] for name in [
        'frontend/playwright.auth.config.ts','frontend/vite.config.ts','backend/run.sh','backend/app/config.py']},
    'new_preview_root':str(TASK/'preview-auth-export-final'),
    'verifier_relative':'c-export-view-final-ui-plan/verify_bound_ui_inputs.py',
    'launcher_sha256':sha(TASK/'preview_auth_export_view.py'),
    'launcher_review_relative':'a-export-final-preview-static/receipt.json',
    'launcher_review_sha256':sha(launcher_review)})
assert not Path(go['new_preview_root']).exists()
go_path=TASK/'ui-go-export-view.json'
assert not go_path.exists()
go_path.write_text(json.dumps(go,indent=2)+'\n')
print(json.dumps({'source_head':manifest['source_head'],'initial_source_tree_sha256':manifest['source_tree_sha256'],
    'declared_PNG_delta_count':len(delta),'go_path':str(go_path),'go_sha256':sha(go_path)}))

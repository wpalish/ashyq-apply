from pathlib import Path
import hashlib,json,datetime
repo=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply')
dest=repo/'backend/evaluation/research/expert/data/protocol.2026-10-05/v13-source-draft'
dest.mkdir(parents=True,exist_ok=False)
sources=[
'/tmp/unimatch-expert500-v13-year-context-actual-red-original.log',
'/tmp/unimatch-expert500-v13-year-context-actual-focused-original.log',
'/tmp/unimatch-expert500-v13-year-context-actual-focused-v2-original.log',
'/tmp/unimatch-expert500-v13-year-context-actual-focused-v3-original.log',
'/tmp/unimatch-expert500-v13-year-context-initial-mypy-original.log',
'/tmp/unimatch-expert500-v13-mixed-stop-actual-red-original.log',
'/tmp/unimatch-expert500-v13-mixed-stop-actual-green-original.log',
'/tmp/unimatch-expert500-v13-mixed-stop-final-focused-original.log',
'/tmp/unimatch-expert500-v13-stop-ruff-original.log',
'/tmp/unimatch-expert500-v13-stop-mypy-original.log',
'/tmp/unimatch-expert500-v13-stop-mypy-v2-original.log',
'/tmp/unimatch-expert500-v13-completion-clock-red-original.log',
'/tmp/unimatch-expert500-v13-completion-clock-green-original.log',
'/tmp/unimatch-expert500-v13-completion-clock-quality-original.log',
'/tmp/unimatch-expert500-journal-pilot-v13.py',
'/tmp/test_unimatch_expert500_completion_clock_v13.py',
'/tmp/unimatch-expert500-v12-year-context-candidate.patch',
'/tmp/unimatch-expert500-v12-year-context-candidate.md',
'/tmp/unimatch-expert500-controller-mixed-provider-stop.patch',
'/tmp/test_expert_controller_mixed_provider_stop_candidate.py',
'/tmp/unimatch-expert500-v13-source-draft-recorder.py',
]
sourcefiles=['backend/app/adapters/document_ir.py','backend/evaluation/research/expert/models.py','backend/evaluation/research/expert/citations.py','backend/evaluation/research/expert/controller.py','backend/tests/test_document_ir.py','backend/tests/test_expert_citations.py','backend/tests/test_expert_controller_mixed_provider_stop.py']
entries=[]
for original in [Path(s) for s in sources]+[repo/s for s in sourcefiles]:
    data=original.read_bytes(); sha=hashlib.sha256(data).hexdigest()
    relative=('source/'+str(original.relative_to(repo))) if original.is_relative_to(repo) else 'original/'+original.name
    target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assert target.read_bytes()==data and hashlib.sha256(original.read_bytes()).hexdigest()==sha
    entries.append({'original':str(original),'copy':relative,'sha256':sha,'size_bytes':len(data)})
manifest={'status':'prospective_unvalidated_source_draft','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'predecessor_metadata':'b07213d','original_v12_source':'92dfdb6d4f1a4595865ea756f46b176ce0f6d891','primary_acceptance':False,'new_source_model_calls':0,'reviewed_labels_read':0,'v12_frozen_helpers_results_edited':False,'gates':{'stop_actual_red':'24 failed/8 passed','stop_actual_combined_green':'171 passed','year_context_focused_initial':'380 passed/2 unsupported-phrase fixture failures','year_context_focused_corrected':'382 passed','completion_clock_draft':'10 failed/2 passed ->12 passed','full_source_gate':'not run','independent_year_boundary_findings':'pending v2 fix'},'clock_candidate_warning':'filename V13 with embedded V12 identifiers is an isolated clock draft; NOT coherent freeze or live-ready protocol','records':entries}
p=dest/'manifest.json';p.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'archive':str(dest),'records':len(entries),'manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'primary_acceptance':False}))

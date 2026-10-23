import hashlib,json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from dotenv import dotenv_values
root=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20');work=root/'work';repo=work/'ashyq-apply';run=work/'search-loop-round6';out=repo/'docs/process/evidence/search-loop/2026-10-07/round6'
secrets=[v.encode() for k,v in dotenv_values(repo/'backend/.env').items() if v and len(v)>=12 and any(x in k.upper() for x in ('KEY','TOKEN','SECRET','PASSWORD'))]
def archive(src,dst):
 for p in sorted(src.rglob('*')) if src.is_dir() else [src]:
  if not p.is_file() or p.is_symlink():continue
  rel=p.relative_to(src) if src.is_dir() else Path(p.name)
  if any(x.startswith('.') or x=='__pycache__' for x in rel.parts) or p.suffix in ('.pyc','.db','.sqlite'):continue
  data=p.read_bytes();assert not any(s in data for s in secrets),'Known secret detected'
  dest=dst/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
b=json.loads((run/'gates/backend-gates.json').read_text());f=json.loads((run/'gates/frontend-gates.json').read_text());demo=json.loads((run/'gates/demo-comparison.json').read_text())
assert b['source_unchanged'] and b['dotenv_restored'] and len(b['commands'])==5 and all(x['exit_code']==0 for x in b['commands'])
assert len(f['commands'])==4 and all(x['exit_code']==0 for x in f['commands']);assert demo['dotenv_restored']
for p,h in b['source_sha256'].items():assert hashlib.sha256((repo/p).read_bytes()).hexdigest()==h
log=(run/'gates/backend-pytest.log').read_text();count=int(re.search(r'(\d+) passed, 2 warnings',log).group(1));cov=float(re.search(r'Total coverage: ([\d.]+)%',log).group(1));assert count==4077
archive(run/'gates',out/'gates');archive(run/'reviews/expert_a',out/'reviews/expert_a')
for p in sorted(run.iterdir()):
 if p.is_file():archive(p,out)
# App bytes match proposal except import-only reordering in scholarship caller.
proposal=run/'reviews/expert_a/revision3'
diff=subprocess.run(['diff','-u',str(proposal/'proposed_web_scholarships.py'),str(repo/'backend/app/adapters/scholarship/web_scholarships.py')],text=True,stdout=subprocess.PIPE)
(out/'parent-caller-import-only.diff').write_text(diff.stdout)
record=dict(source_sha256=b['source_sha256'],backend_tests=count,coverage_percent=cov,warnings=2,pytest_seconds=549.67,parent_focused=227,external_author_tests=49,semantic_executions=79,unique_semantic_fixtures=70,independent_capture_controls=31,frontend_tests=232,flag='PROGRAMME_IDENTITY_BEFORE_FUNDING',source_default=False,live_pair_run=False,hosted_ci='BLOCKED_BILLING_OR_SPENDING_REFUSAL',live_stop_sha256=hashlib.sha256((work/'development-STOP.json').read_bytes()).hexdigest())
(out/'source-gates.json').write_text(json.dumps(record,indent=2)+'\n')
(out/'README.md').write_text('''# Round6 — opt-in programme identity, preserved subsidiary funding discovery

PF-1 PROGRAMME_IDENTITY_BEFORE_FUNDING=False. Enabled mode delays only the exact existing SCHOLARSHIP_INDEX result when the page identifies its own programme and contains scoped academic courses/modules/projects with at least two years or numeric credits. It rejects funding/support identity, funding URLs/purpose, degree denials and scholarship/eligibility content within that block; semantic section/next heading and chrome bounds are enforced. FAQ/award/UNKNOWN and document/catalogue/unknown-degree fallthrough preserve their exact legacy results. Off full output snapshots are identical on79 executions/70 unique manually reviewed fixtures.

A programme promotion carries SUBSIDIARY_FUNDING_INDEX_SIGNAL in existing signals. The actual scholarship caller treats that marker as index discovery only for programme types, using unchanged index/award/official URL limits. The programme never becomes award proof. ACCEPTS is unchanged. Four prior external candidates are retained as rejected: title-only and heading-only false programmes, academic revision1 section/negation failures, revision2 actual depth1 funding-link loss. A revision3/root review resolves that caller regression; this history explains the narrow marker contract.

Saved Wits body SHA88d1f716.../metadata SHAd54f742c...: real requirements reader PROGRAM_EXISTS off/on/on/off0/1/1/0; verbatim title quote retained, scope year/intakeNone and intake_open notTrue. Real funding reader off/on/on/off preserves same visits in primary/fallback/depth1 routes, including financial-aid administration. Depth1 index is synthetic routing fixture, and target funding body is unavailable/unknown; no scholarship existence/absence or2027 route is inferred. Fullpipeline gain is conditional on reaching the page: SI-1False still blocks early Wits identity; future pair must hold SI-1True fixed or declare combined design.

Two conservative missed gains remain (eligible optional module choice; unrelated master's denial). South Africa citizenship matching is existing PENDING; the domestic URL guard control explicitly uses an already resolved international verdict, not a new citizenship fix. One earlier external domestic fixture mistake/log is preserved. Secondary FAQ programme expectation was deliberately narrowed to legacy FAQ; original B expected output retained. No broad programme/funding completeness claim.

Evaluation BooleanOptional --programme-identity-before-funding/--no-programme-identity-before-funding applies/forwards explicit choice and records ordinary/preSTOP config. Existing SPH/BL-1 metadata unchanged. Independent31 controls cover real parent/child CLI, omitted/last-choice/hostile child defaults, PF×SPH with fixed SI-1, pre/between-case STOP and simulated refusal/missing-budget; no socket/provider/Git calls. Existing preSTOP envelope lacks ordinary harness/mapping SHA, explicitly not repaired here; independent application snapshot pins9files. Applied classifier exactly matches7c74866; caller differs fromb733 only bs4 import ordering (diff saved).

Local final gates:4077passed/2warnings/95.06%/549.67s;Ruff/format/mypy373 clean;227parent focused;49external author controls;frontend232/type/lint/build;demo20rows/stage counts byte-identical/one Alembic head. Eight source/test/fixture hashes unchanged through gates and dotenv restored. A pre-gate wrong-filename attempt did not execute tests and its original log is retained; parent test formatting is routine before final full freeze. No database or known secrets archived.

No live pair/default promotion/hosted CI or launch pass: sticky CI billing/spending refusal remains, pushes are wip[skip ci]. Guard60read production candidate is external/not applied;120s hardwall/renderer/query durability remains unresolved. No owner gold signature, heldout tuning, migration, merge or deployment.
''')
index=[dict(path=str(p.relative_to(out)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='ARCHIVE_INDEX.json']
(out/'ARCHIVE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MUTC');p=repo/'docs/process/HANDOFF.md';t=p.read_text();s=t.index('**Current search-loop holder:');e=t.index('\n\n',s);t=t[:s]+f'**Current search-loop holder: gpt-6-astra, {now}, task/search-programme-purpose.** Round6 local gates4077/95.06%,frontend232/demo unchanged/onehead complete; independent capture31controls pass. Source checkpoint/DraftPR66 next; flagFalse, liveSTOP/hostedCI refusal sticky. Parent alone code/Git; two existing experts continue external read-budget review. No launch claim.'+t[e:]
marker='## 6. Gate status at last run\n';t=t.replace(marker,marker+f'\n**[search-loop] Round6 final local gates {now}:**4077passed,2warnings,95.06%,549.67s;Ruff/format/mypy373 clean;227parent focused;49external author;79semantic executions/70 unique;31independent capture controls;frontend232/type/lint/build;unchanged20-row demo;singlehead d8e412c6a901. Eight code/test/fixture hashes unchanged, dedicated dotenv restored. Originals/source/reviews/conditional scope and rejected predecessors in round6 archive. No live pair/default/hostedCI/launch pass.\n',1)
t=t.replace('**Newest search-loop Round6:** app classifier+funding caller, evaluation CLI, new tests/fixtures and current HANDOFF uncommitted while full source freeze/gates run. Do not edit app/evaluation/tests until recorded gate completion. Previous historical entries below are not current dirty state.','**Newest search-loop Round6:** final locally verified source and archive awaiting source checkpoint/DraftPR66; source freeze completed. Exact pending files from git status; previous historical entries below are not current dirty state.')
t=t.replace('## 8. Contract changes since the brief (append-only; the other agent reads this before coding)\n',f'## 8. Contract changes since the brief (append-only; the other agent reads this before coding)\n\n- {now} [search-loop] off-default PF-1 PROGRAMME_IDENTITY_BEFORE_FUNDING; SUBSIDIARY_FUNDING_INDEX_SIGNAL in existing classifier signals is discovery-only and accepted by funding is_index only on programme types. No dataclass/public schema/ACCEPTS/default change. Evaluation BooleanOptional explicit child/config/preSTOP wiring. Other readers/policies unchanged.\n',1)
p.write_text(t)
print(json.dumps(dict(archived_files=len(index),known_secret_matches=0,**record)))

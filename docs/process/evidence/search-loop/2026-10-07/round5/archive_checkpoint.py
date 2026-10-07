"""Archive the opt-in subject rule after final local gates; no live actions."""
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values

WORK=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work')
REPO=WORK/'ashyq-apply'; ROOT=WORK/'search-loop-round5'
OUT=REPO/'docs/process/evidence/search-loop/2026-10-07/round5'
OUT.mkdir(parents=True,exist_ok=True)
secrets=[v.encode() for k,v in dotenv_values(REPO/'backend/.env').items()
         if v and len(v)>=12 and any(t in k.upper() for t in ('KEY','TOKEN','SECRET','PASSWORD'))]
def archive(src,dst):
    files=sorted(src.rglob('*')) if src.is_dir() else [src]
    for p in files:
        if not p.is_file() or p.is_symlink(): continue
        relative=p.relative_to(src) if src.is_dir() else Path(p.name)
        if any(x.startswith('.') or x=='__pycache__' for x in relative.parts) or p.suffix in ('.pyc','.db','.sqlite'): continue
        data=p.read_bytes(); assert not any(s in data for s in secrets), 'Known secret scan rejected file'
        target=dst/relative; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,target)
backend=json.loads((ROOT/'gates/backend-gates.json').read_text())
frontend=json.loads((ROOT/'gates/frontend-gates.json').read_text())
assert backend['source_unchanged'] and backend['dotenv_restored']
assert len(backend['commands'])==5 and all(c['exit_code']==0 for c in backend['commands'])
assert len(frontend['commands'])==4 and all(c['exit_code']==0 for c in frontend['commands'])
assert (ROOT/'gates/demo-comparison.json').exists()
for p,h in backend['source_sha256'].items(): assert hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h
raw=(ROOT/'gates/backend-pytest.log').read_text()
count=int(re.search(r'(\d+) passed, 2 warnings',raw).group(1))
coverage=float(re.search(r'Total coverage: ([\d.]+)%',raw).group(1))
for name in ('reviews','gates'): archive(ROOT/name,OUT/name)
for p in sorted(ROOT.iterdir()):
    if p.is_file(): archive(p,OUT)
record=dict(source_sha256=backend['source_sha256'],backend_tests=count,coverage_percent=coverage,
    warnings=2,parent_focused=173,expert_tests=141,independent_harness_tests=30,frontend_tests=232,
    flag='SUBJECT_PHRASE_MATCH',source_default=False,live_pair_run=False,
    hosted_ci='BLOCKED_BILLING_OR_SPENDING_REFUSAL',live_stop_present=(WORK/'development-STOP.json').exists())
(OUT/'source-gates.json').write_text(json.dumps(record,indent=2)+'\n')
(OUT/'README.md').write_text(f'''# Round5 — opt-in ordered subject phrase

SPH-1 SUBJECT_PHRASE_MATCH=False preserves legacy behaviour. Enabled mode requires ordered contiguous subject words, retaining precise multiword strong aliases as exact names while keeping the extra-subject guard on ambiguous one-word aliases. No ontology expansion. It repairs saved AUT Data Science Major borrowing computer from its parent degree and science from its major. The initially proposed stricter alias path lost a precise Computing Science Major title; that reviewed defect is repaired and its original failing controls retained.

Actual saved-byte WebRequirements.verify off/on/on/off: wrong Data Science programme-existence claim1/0/0/1, true Computer Science1/1/1/1; CS whole snapshots identical, other Data claims identical. Quote/body hashes and null intake/year are retained. Root rerun against the applied source also reproduces these outcomes. This is offline causal evidence, not a fresh live cohort or a general precision/recall score.

141 expert controls (135new+6existing), 173 parent focused; final full backend{count}/2warnings/{coverage}%, frontend232/type/lint/build, Ruff/format/mypy and unchanged demo20 rows/onehead. Original first root wrong-test-filename run and first full-gate unsorted import failure are retained separately from final successful logs. Parent only sorted test imports; app matches the expert proposal SHA702c67ee3e9c0be0c0f3a249dc8858dd9b6c91ec4a20e63ce3c86e4617640bb6.

Evaluation CLI --subject-phrase-match/--no-subject-phrase-match forwards explicit choice, applies it before child capture, records it in ordinary/pre-start-stop envelopes. shared_query_budget metadata records effective existing BL-1; CLI omission does not meanFalse when source defaultTrue. No provider actions occur in capture tests. Independent harness review30pass (own16+parent14) is retained; omitted/explicit/last-choice modes and stop-before/between-cases are tested. Existing pre-stop envelope lacks ordinary harness/mapping hashes; that nonblocking limitation is explicit.

Known limits: existing raw own-field Computing/Informatics asymmetry and unknown abbreviations are not expanded; requested field whitespace/ASCII tokenization and broader programme scope policies retain their prior limits. No default promotion: DoD live off/on/on/off and owner decision remain required. Global live STOP and hosted CI refusal remain; new pushes skip CI and do not certify release. Production durable60/120 guard is still unresolved. No gold, heldout, Fetcher, migration, deployment or merge changes.
''')
index=[dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
       for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='ARCHIVE_INDEX.json']
(OUT/'ARCHIVE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MUTC')
p=REPO/'docs/process/HANDOFF.md';t=p.read_text();s=t.index('**Current search-loop holder:');e=t.index('\n\n',s)
t=t[:s]+f'**Current search-loop holder: gpt-6-astra, {now}, [search-loop], task/search-subject-phrase from predecessor2ddba99.** Query sourcec6a1bdc is pushed in DraftPR64, local3743/95.01%, hostedCIblocked. Round5 SPH-1 opt-in source locally verified{count}/{coverage}%; flagFalse, pending source checkpoint/DraftPR65. Parent owns code/Git/HANDOFF; two existing experts perform independent offline review. Global live STOP after CI billing/spending refusal remains; no retry/purchase/substitution/reset; new wip[skip ci] source preservation is not hosted gate success. Goal/heartbeatACTIVE; no merge/deployment/launch claim.'+t[e:]
def add(section,paragraph):
    global t
    t=t.replace(section+'\n',section+'\n\n'+paragraph+'\n',1)
add('## 5. NEXT STEP — exact and executable', '**[search-loop] current '+now+': Round5 local gates/retained AUT reader review complete; archive/push source wip[skip ci], open dependent DraftPR65 and record actualhash. SPH-1 remainsFalse until unchanged DoD live pair and owner default decision, prohibited while stickySTOP. Immediately continue offline Round6 Wits primary-purpose classifier: initial title-only and curriculum-heading-only alternatives both have independently proven false programme confirmations, preserved rejected. Require stronger content corroboration and negative controls before source application. Production durable60/120/read-cancellation guard design remains unresolved; preserve its explicit CPU wall-clock limitation. No live/hosted retry/payment/gold/heldout/reset.')
add('## 6. Gate status at last run', f'**[search-loop] Round5 final local gates:** backend{count}passed,2warnings,{coverage}%;173parent focused;expert141;frontend232/type/lint/build pass; Ruff/format/mypy clean; demo20 rows/stage totals byte-identical to preceding source, Groningenfirst, old UBC vocabulary caveat unchanged; singlehead d8e412c6a901. Four source/test hashes unchanged and dotenv restored. Complete originals and first import-format/wrong-filename historical failures in round5. HostedCI remainsBLOCKED, liveSTOPsticky; no paired live score/default promotion.')
add('## 8. Contract changes since the brief (append-only; the other agent reads this before coding)', '- '+now+' [search-loop] off-default SPH-1 live_discovery.SUBJECT_PHRASE_MATCH; evaluation BooleanOptional --subject-phrase-match/--no-subject-phrase-match applies/forwards explicit choice. Ordinary/pre-stop Capture.config adds subject_phrase_match and effective shared_query_budget. No public API/migration/default/gold/provider/Fetcher change. Strong multiword aliases may directly match only as ordered exact phrases in enabled mode; ambiguous one-word alias guard preserved.')
p.write_text(t)
relay=REPO/'docs/process/CLAUDE_SEARCH_RELAY_2026-10-07.md'
relay.write_text(relay.read_text().replace('\n## Current checkpoint',f'\n## Latest Round5 checkpoint {now}\n\nSPH-1 opt-in source locally verified{count}/{coverage}%,frontend232/all local gates/demo unchanged/onehead. Retained AUT production reader removes wrong Data major1/0/0/1 and preserves true CS1/1/1/1 with no invented intake/year. Source task/search-subject-phrase follows DraftPR64 query accounting c6a1bdc; source checkpoint/PR65 next. RuleFalse pending live pair/owner promotion; no live while stickySTOP. Wits alternatives have two independently proven false-positive blockers and are not applied. Continue stronger offline proof/review rather than promoting them. Production durable60/120 remains unresolved. No current cloud CI or launch claim. Newest section supersedes older planned steps below.\n\n## Previous checkpoint',1))
ledger=REPO/'docs/process/SEARCH_LOOP_LEDGER_2026-10-07.md'
ledger.write_text(ledger.read_text().replace('## Next resume\n','## Next resume\n\nLatest '+now+f': Round5 SPH-1 local source{count}/{coverage}% and retained-reader checks complete; sourcecheckpoint/PR65 next. FlagFalse, liveSTOPsticky/cloudblocked. Next Wits stronger programme-purpose proof; first two candidate rules rejected by negative controls, not applied. Query sourcec6a1bdc in DraftPR64; no durable60/120 guarantee.\n',1))
print(json.dumps(dict(archived_files=len(index),secret_matches=0,**record)))

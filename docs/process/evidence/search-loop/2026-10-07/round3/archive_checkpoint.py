"""Preserve offline query repair and exact handoff; no provider calls."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values

WORK = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work')
REPO = WORK/'ashyq-apply'
ROOT = WORK/'search-loop-round3'
OUT = REPO/'docs/process/evidence/search-loop/2026-10-07/round3'
OUT.mkdir(parents=True, exist_ok=True)
secrets = [v.encode() for k,v in dotenv_values(REPO/'backend/.env').items()
           if v and len(v)>=12 and any(t in k.upper() for t in ('KEY','TOKEN','SECRET','PASSWORD'))]
def copy_tree(src, dst):
    for p in src.rglob('*'):
        if not p.is_file() or p.is_symlink() or any(x.startswith('.') or x=='__pycache__' for x in p.relative_to(src).parts):
            continue
        if p.suffix in ('.pyc','.sqlite','.db'):
            continue
        data=p.read_bytes()
        assert not any(s in data for s in secrets), 'Secret scan rejected archival file'
        target=dst/p.relative_to(src); target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,target)
for name in ('gates','reviews','root-review'):
    copy_tree(ROOT/name, OUT/name)
for name in ('parent-focused.log','run_gates.py','run_frontend.py','run_demo.py','archive_checkpoint.py'):
    p=ROOT/name; assert not any(s in p.read_bytes() for s in secrets)
    shutil.copy2(p,OUT/name)
copy_tree(WORK/'search-loop-round4/reviews/expert_a', REPO/'docs/process/evidence/search-loop/2026-10-07/round4/design-only')
readme = '''# Round 3 — shared identity/programme query accounting

Confirmed fake-provider production path previously made one identity plus six programme calls while reporting six. The same red evidence shows both planners ignored a precharged trace. No real provider or university calls were made for this diagnosis or repair.

Existing default-on BL-1 now charges identity attempts after factory resolution, propagates prior charge, and reserves only the remaining slots in both planners. A callback before each seam attempt preserves ordinary errors/cancellation accounting and avoids double-charge. Zero slots never call queries_for(0) or the factory. SHARED_QUERY_BUDGET=False deliberately retains legacy six new programme attempts and reports the truthful larger total.

The telemetry is charged search seam attempts, including local wrapper rejection, not proof of vendor HTTP dispatch. It is in-memory within a discovery episode: durable cancellation/crash/resume guards and production 60-read/120-second enforcement remain unresolved. Free-text multi queries N counts completed reports, so use search_queries_attempted for the charged total. Effective shared flag capture metadata is still a separate follow-up.

Final proposed patch d36a6cd4a815c997d07883edad252913a855dc19851af41ea44d7e53b7516245; four applied source hashes match the proposal. Retained proposal metadata applied_to_repo=false describes the original external proposal, not the parent application. Independent A review has no blocking finding: B50+own18=68 passed; seven old-byte controls fail as expected. Parent focused selection144 passed. Final backend3743 passed/2 warnings/95.01%/416.07s; Ruff/format/mypy369 clean; frontend232/typecheck/lint/build pass; demo20 rows/stage totals identical to preceding green source; one Alembic head d8e412c6a901. Complete original logs and historical failed attempts are retained.

All new hosted CI remains blocked by the preserved billing/spending refusal. Source was tested locally; this archive is not current-head hosted CI success or launch acceptance. Global live STOP remains sticky. No default change, gold/heldout/Fetcher/production mutation, purchase or reset. Round4 design-only is a separate unresolved guard design and explicitly does not meet a hard synchronous wall-clock guarantee.
'''
(OUT/'README.md').write_text(readme)
gates=json.loads((ROOT/'gates/backend-gates.json').read_text())
assert gates['source_unchanged'] and gates['dotenv_restored'] and all(c['exit_code']==0 for c in gates['commands'])
for p,h in gates['source_sha256'].items():
    assert hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h
(OUT/'source-gates.json').write_text(json.dumps(dict(source_sha256=gates['source_sha256'],
    backend_tests=3743,coverage_percent=95.01,warnings=2,focused_tests=144,independent_tests=68,
    frontend_tests=232,alembic_head='d8e412c6a901',hosted_ci='BLOCKED_BILLING_OR_SPENDING_REFUSAL',
    live_stop_present=(WORK/'development-STOP.json').exists(),quality_scored=False),indent=2)+'\n')
index=[dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
       for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='ARCHIVE_INDEX.json']
(OUT/'ARCHIVE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MUTC')
handoff=REPO/'docs/process/HANDOFF.md'; text=handoff.read_text()
start=text.index('**Current search-loop holder:'); end=text.index('\n\n',start)
text=text[:start]+f'**Current search-loop holder: gpt-6-astra, {now}, [search-loop], task/search-query-ledger from predecessor daff483.** Owner authorizes autonomous repeated rounds and two expert subagents. Round3 existing BL-1 correctness repair locally green; exact patch hashes and independent review in round3 evidence. Global live/hosted CI STOP is sticky after billing/spending refusal; no retry/payment/substitution/reset. New source pushes use wip + [skip ci], so final hosted checks remain blocked. Draft PR61/62/63 pending owner merge; no deployment or launch claim. Parent alone owns source/Git/HANDOFF.'+text[end:]
text=text.replace('**[search-loop] in progress:** retain the owner-approved Definition of Done targets and iterate on confirmed DEV losses. Round 2 begins with offline Dalian/Wits/Caltech discovery traces and retained official sources. Do not infer that Dalian\'s news announcement is an exact programme page. Journal:', '**[search-loop] in progress:** Round2 four arms complete; SI-1 remainsFalse because no stable programme/core-fact gain. Round3 query accounting locally verified, source checkpoint next. Two experts prepare disjoint off-by-default AUT subject-phrase and Wits primary-purpose classifier proposals offline. Durable production budget enforcement remains unresolved. Journal:')
def add(section, paragraph):
    global text
    text=text.replace(section+'\n',section+'\n\n'+paragraph+'\n',1)
add('## 5. NEXT STEP — exact and executable', '**[search-loop] current '+now+':** Round3 source/gates complete and frozen: archive, push wip [skip ci], open dependent Draft PR64 and record actual commit. Then explicitly branch next bounded off-by-default subject-matcher rule from task/search-query-ledger despite unmerged predecessors. HANDOFF-before-code for each rule. Follow DoD flags/off-on-on-off/owner promotion; no live while work/development-STOP.json exists. AUT phrase and Wits secondary-funding loss proposals are independently reviewed offline; retain prior wrong outcomes and exact saved body hashes. Production durable read/time design remains unimplemented and must not be claimed as a hard bound. Continue useful offline work and preserve Claude journal after every step.')
add('## 6. Gate status at last run', '**[search-loop] Round3 final local source gates:**3743passed,2warnings,95.01%,416.07s;144parent focused;independent68pass plus7 old-byte negative controls. Ruff/format/mypy369clean;frontend232/type/lint/build pass; demo20 rows/stage counts byte-identical to Round2, Groningenfirst; legacy UBC caveat unchanged; onehead d8e412c6a901. Five source/test hashes frozen and unchanged; dotenv restored. Current hosted CI BLOCKED by billing/spending refusal, original diagnostics in ci-refusal evidence. d669 older source8/8SUCCESS is not current-head acceptance. No new hosted/live retry. Complete originals in round3/gates.')
add('## 8. Contract changes since the brief (append-only; the other agent reads this before coding)', '- '+now+' [search-loop] optional synchronous discover_candidates(on_query_attempt=...) records every charged search seam attempt, including ordinary errors/local wrapper refusal; DiscoveryTrace.as_dict adds search_queries_attempted. _discover_one accepts keyword prior search_queries_used. Default-on BL-1 uses identity+programme shared remaining6; False retains six programme slots with truthful total. No public API/migration/default flag change; durable resume enforcement outside scope.')
add('## 11. Session log', '| '+now+' | gpt-6-astra | daff483 -> locally verified task/search-query-ledger | Round2 reviewed no stable facts gain, SIoff; CI billing refusal stickySTOP. Round3 actual production query accounting fixed, local3743/95.01% and peer68 green; cloudblocked, source checkpoint next. |')
handoff.write_text(text)
relay=REPO/'docs/process/CLAUDE_SEARCH_RELAY_2026-10-07.md'
relay.write_text(relay.read_text().replace('\n## Autonomous loop continuation (newest instruction)', '\n## Current checkpoint '+now+'\n\nRound2 all four arms completed before the CI refusal, 20 terminal observations within unchanged6/60/120000; stable site identity Wits/Caltech, no stable programme/core-fact gain, SI-1 remainsFalse. See round2/PAIRED_REVIEW.md. Original stopped launcher and two bounded outcomes without full raw remain explicit. Round3 default-on BL-1 identity/programme accounting repair locally passes3743/95.01%, frontend232/quality/demo/onehead; source branch task/search-query-ledger checkpoint next. Independent68test review has no blockers. GitHub refused all8 jobs9330929 before steps for billing/spending-limit; d669 previous8/8 is historical source proof. Global live STOP work/development-STOP.json is sticky: no live/provider/model/hosted retry, payment, substitution or reset. New source checkpoints use wip [skip ci], not a CI pass. Next: preserve query checkpoint then off-by-default AUT phrase rule and Wits primary-purpose classifier rule, each review/gates/pair/owner promotion per DoD; live remains blocked. Production durable60/120 guard design exists only as an explicitly incomplete sketch. Goal and hourly heartbeat remain ACTIVE; no merge/deployment/launch claim. Newest paragraph supersedes the historical planned-pair statements below.\n\n## Autonomous loop continuation (historical Round2 start)',1))
ledger=REPO/'docs/process/SEARCH_LOOP_LEDGER_2026-10-07.md'
ledger.write_text(ledger.read_text().replace('## Next resume\n','## Next resume\n\nLatest '+now+': Round3 source locally verified;3743/95.01%,144focused,independent68,frontend232/quality/demo unchanged/singlehead. Branch task/search-query-ledger; archive and push wip[skip ci], then dependent off-by-default AUT phrase/Wits classifier rounds. Live and hostedCI remain blocked by sticky refusal STOP; no retry/purchase/reset. Current source counter is charged seam attempts, not HTTP dispatch or durable guard. Original pending commands below are historical and must not be re-executed.\n',1))
print(json.dumps({'archived_files':len(index),'secret_value_matches':0,'source_unchanged':True,'updated_at':now}))

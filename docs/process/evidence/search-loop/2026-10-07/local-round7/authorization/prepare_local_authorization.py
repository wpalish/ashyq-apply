"""Record direct owner authorization without rewriting historical refusal evidence."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

TASK = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = TASK / 'work/ashyq-apply'
PACKET = Path('/Users/wpalish/.codex/attachments/0d7b3819-024b-4ea5-b740-42f3158322ab/Вставленный текст.txt')
OUT = TASK / 'work/local-round7'
OLD = TASK / 'work/development-STOP.json'
BUNDLE = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner')

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

old_sha = sha(OLD)
assert old_sha == 'dd669c6d73d89ba2586676b46b120e4c8af2ea95e4e15cd7ae75c554f9557cad'
now = datetime.now(UTC).isoformat()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=REPO, text=True).strip()
assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=REPO, text=True) == ''
shutil.copy2(PACKET, OUT / 'owner-local-instructions.txt')
receipt = {
    'recorded_at_utc': now,
    'authority': 'Direct user pasted attachment requesting local checks and fresh local research',
    'owner_instructions_sha256': sha(PACKET),
    'repository': str(REPO), 'source_head_before_metadata': head, 'branch': branch,
    'historical_ci_stop': str(OLD), 'historical_ci_stop_sha256': old_sha,
    'historical_ci_refusal_preserved': True,
    'local_checks_authorized': True, 'new_local_algorithm_pilot_authorized': True,
    'old_closed_expert_trials_resumed': False,
    'new_live_refusal_sentinel': str(OUT / 'provider-STOP.json'),
    'hosted_workflows_or_retries_authorized': False,
    'provider': 'exa_mcp (existing chosen free/keyless DEV search protocol)',
    'pilot_order': ['groningen', 'delft', 'aalto', 'vienna', 'warsaw', 'ubc', 'toronto', 'hku', 'ntu', 'kaist'],
    'network_budget': {'algorithm_seconds': 120, 'fetcher_calls': 60, 'search_attempts': 6},
    'live_execution_preconditions': ['core/full actual results reviewed', 'clean pinned source and plan', 'no new shared provider/model/auth/quota refusal', 'current HANDOFF admission; no old expert controller auto-resume'],
    'doctor_summary': str(BUNDLE / 'runs/20261007T213327Z-doctor-986eb064/summary.json'),
    'unrelated_original_checkout': {'branch': 'task/expert-500-phase1', 'head': 'b41b49ec90d421c3c2e658c7d686282dc557926c', 'existing_changed_paths': 11, 'mutated': False},
}
(OUT / 'local-authorization.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
archive = REPO / 'docs/process/evidence/search-loop/2026-10-07/local-round7/authorization'
archive.mkdir(parents=True, exist_ok=True)
for name in ['owner-local-instructions.txt', 'local-authorization.json', 'handoff-check-original.log', 'git-fetch-original.log', 'prepare_local_authorization.py']:
    shutil.copy2(OUT / name, archive / name)

note = (
    f'**[search-loop] LOCAL EXECUTION AUTHORIZATION {datetime.now(UTC):%Y-%m-%d %H:%M}UTC:** '
    'Owner explicitly switches to prepared local-runner; use --repo for this dedicated clean checkout. '
    'Doctor5PASS. Run core then full (PostgreSQL, sequential demo/auth E2E, security audit) on unchanged '
    'source5472/Draft66; record exact HEAD/snapshot SHA/all logs. Source/eval/tests frozen through these '
    'checks; v2 budget candidate stays external. Original b41b49e dirty11paths untouched; its4451/1fixture '
    'failure is a different source and not presumed present here. Historical CI refusal STOP remains '
    'byte-identical, but this direct instruction authorizes NEW local checks and a separately pinned '
    'fresh algorithm pilot after checks; no hosted workflows/retries/purchase or fake required statuses. '
    'Use existing protocol exa_mcp, original10pilot one-by-one, strict120s/60/6; local IP is not Fly. '
    'New provider/model/auth/quota refusal globally stops live into separate local-round7/provider-STOP.json; '
    'no retry/substitution/reset/effort reduction. OldV9/V13/V14 remainclosed, no expert controller or '
    'HELDOUT150 auto-run, no gold signature. Exact authorization original in local-round7/authorization.\n\n'
)
p = REPO / 'docs/process/HANDOFF.md'
text = p.read_text()
start = text.index('**Current search-loop holder:'); end = text.index('\n\n', start)
text = text[:start] + f'**Current search-loop holder: gpt-6-astra, {datetime.now(UTC):%Y-%m-%d %H:%M}UTC, {branch}.** New owner local-runner authorization supersedes CI-only live prohibition for fresh local route. Source5472/Draft66 unchanged; doctor5PASS, core/full next. OldSTOP immutable; new provider refusal still globally stops live. B v2 external review pending. Goal/heartbeatACTIVE; no launch claim.' + text[end:]
for anchor in ['## 2. Current task\n\n', '## 5. NEXT STEP — exact and executable\n']:
    assert anchor in text
    text = text.replace(anchor, anchor + '\n' + note, 1)
p.write_text(text)
for name in ['CLAUDE_SEARCH_RELAY_2026-10-07.md', 'SEARCH_LOOP_LEDGER_2026-10-07.md']:
    p = REPO / 'docs/process' / name
    text = p.read_text(); split = text.index('\n') + 1
    p.write_text(text[:split] + '\n' + note + text[split:])
for name in ['CLAUDE_CONTINUE.md', 'SEARCH_LOOP_STATUS.md']:
    p = TASK / 'outputs' / name
    text = p.read_text(); split = text.index('\n') + 1
    p.write_text(text[:split] + '\n' + note + text[split:])
(TASK / 'outputs/CLAUDE_SEARCH_RELAY_2026-10-07.md').write_text((REPO / 'docs/process/CLAUDE_SEARCH_RELAY_2026-10-07.md').read_text())
assert sha(OLD) == old_sha
print(json.dumps({'authorization_recorded': True, 'historical_stop_unchanged': True, 'source_before_metadata': head, 'doctor': '5PASS'}))

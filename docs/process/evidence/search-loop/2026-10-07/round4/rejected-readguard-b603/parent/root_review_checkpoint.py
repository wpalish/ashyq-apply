"""Preserve independently reproduced blockers; never edits application source."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

TASK = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = TASK / 'work/ashyq-apply'
ROUND = TASK / 'work/search-loop-round4'
ROOT = ROUND / 'reviews/parent-frozen-readguard-review'
ROOT.mkdir(parents=True, exist_ok=True)

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

pins = {
    'reviews/expert_b-readguard/ready-manifest.json': 'b603fe6a75660679e39b1b59545e21aae3aac79793ef2ae5d84c1ec6dc483a31',
    'reviews/expert_b-readguard/readguard.patch': 'c09219f02f30a89ec083484868586264f91cabb89eb8cb7e80c0e30221b8b0f7',
    'reviews/expert_a-readguard/review.ru.md': '61a8fb486dbc8faec900bed1a3e7b012bcc8346c727062d22f1670c3ad628128',
    'reviews/expert_a-readguard/receipt.json': 'e5abdbc303e9a2abda7984b6460def6eae088ae0c01b2754c3a96720dc3dace5',
    'reviews/expert_a-readguard/bundle-files.json': '86591da0a08acc3587ec3cc8f35de8a0cbd2cda40bd617d0aef08c431827f8e0',
}
for relative, expected in pins.items():
    actual = sha(ROUND / relative)
    if actual != expected:
        raise RuntimeError(f'Changed frozen review: {relative}')

source_paths = [
    'backend/app/jobs/worker.py',
    'backend/app/jobs/store.py',
    'backend/app/api/routes_research.py',
    'backend/app/pipeline/runner.py',
    'backend/evaluation/research/live.py',
    'backend/scripts/canary_discovery.py',
]
receipt = {
    'recorded_at_utc': datetime.now(UTC).isoformat(),
    'source_commit': '5472a8337e38aecf55addacf5e02fa057477cb51',
    'metadata_commit': 'd7c50f23',
    'decision': 'REJECTED_TWO_REVISION_BLOCKERS',
    'review_pins': pins,
    'parent_read_source_sha256': {p: sha(REPO / p) for p in source_paths},
    'confirmed_external_controls': [
        'Two actual SQLite sessions: off save before first namespace can erase on count60 and admit get61; count1 persists.',
        'Actual verification stage under SQLite BEGIN IMMEDIATE: zero original get, prior claim/result intact; OperationalError escapes and durable unknown absent.',
        'Independent actual two-session 80 scope attempts: 60 original get/20 read_cap and durable count60.',
    ],
    'parent_source_observations': [
        'Worker claims each Job, reads attempts once, and fences dispatch/checkpoints/outcome by Job ID, worker ID and attempts.',
        'worker_identity is hostname:pid; reclaims increment attempt and are covered by fresh SQL fence control.',
        'Research retry route rejects any RUNNING Job for this run; collect-documents checks approved rows but has no equivalent running-job exclusion.',
        'Only runner assigns settings_snapshot in application source; run_to_decision currently replaces the entire JSON before stage saves.',
        'Legacy canary constructs direct ResearchRunner with no real Job; enabling fenced read guard in current canary is unsupported and must not fabricate a fence.',
        'Synthetic same-job/same-worker/same-attempt duplicate runner does not prove ordinary worker reachability; erasure remains a revision blocker for broad durable claims.',
    ],
    'unverified': ['Actual PostgreSQL concurrency/crash/lock behavior', 'Durable diagnostic while database remains locked', 'Hard 120-second production cap', 'Durable query cap', 'Guard intent across source-toggle resume'],
    'next': 'Review immutable v2 external candidate before any source application; preserve old candidate and all raw originals.',
    'network_calls': 0,
    'provider_model_calls': 0,
    'stop_sha256': sha(TASK / 'work/development-STOP.json'),
}
(ROOT / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
(ROOT / 'review.ru.md').write_text(
    '# Родительский разбор READ-кандидата\n\n'
    'Pinned b603fe6a/c09219f0 отклонён до переноса исходников: независимые реальные SQLite controls '
    'показали стирание durable count60 и 61-й get; реальный verification caller при занятой БД '
    'теряет typed stop и выходит с OperationalError. ZeroIO и ранее сохранённые факты подтверждены; '
    'durable unknown под удерживаемой блокировкой не подтверждён.\n\n'
    'Обычный Worker не запускает повторно тот же Job/attempt в штатном claim пути; stale takeover '
    'проверен свежим fence. Искусственная mixed-mode гонка не доказывает штатную достижимость. '
    'Это не основание заявлять универсальную сохранность счётчика. Единственный присваиватель '
    'settings_snapshot в app — runner; whole-JSON замена до locked save и autoflush требуют '
    'проверки. Current canary не создаёт Job и не годится для guard-on production evidence.\n\n'
    'B готовит отдельную v2 с сериализацией замены JSON и typed busy propagation. '
    'A receipt/raw/report frozen; файлы SQLite runtime/DB/WAL/SHM не архивировать. '
    'Production PG, source-toggle intent, 120s и durable queries остаются открытыми.\n'
)

notice = (
    f'**[search-loop] {datetime.now(UTC):%Y-%m-%d %H:%M}UTC — readguard b603fe6a/c09219f0 REJECTED before source application.** '
    'Independent A7 controls6pass/1deliberate red reproduced actual SQLite first-namespace erasure: '
    '61original gets/count1 after stale OFF save removes count60. Actual verification busy caller '
    'escapes OperationalError, zeroIO/priorfacts equal, durable unknown empty; borrowed70tests pass. '
    'Ordinary duplicate-worker reachability is not proved and is not assumed safe. A report61a8fb48/receipt '
    'e5abdbc3 and parent source audit preserved externally. B revision in disjoint expert_b-readguard-v2; '
    'no production patch applied. Require A/root review of atomic replacement/no-autoflush/typed busy and '
    'same-job guard-intent preservation before exact write-ahead/new branch. RealPG/120s/query durability '
    'and genuine fenced capture remain unknown. STOP unchanged.\n\n'
)
for name, anchor in [
    ('HANDOFF.md', '## 2. Current task\n\n'),
    ('CLAUDE_SEARCH_RELAY_2026-10-07.md', None),
    ('SEARCH_LOOP_LEDGER_2026-10-07.md', None),
]:
    path = REPO / 'docs/process' / name
    text = path.read_text()
    if anchor:
        assert anchor in text
        text = text.replace(anchor, anchor + notice, 1)
    else:
        split = text.index('\n') + 1
        text = text[:split] + '\n' + notice + text[split:]
    path.write_text(text)

for name in ['CLAUDE_CONTINUE.md', 'SEARCH_LOOP_STATUS.md']:
    path = TASK / 'outputs' / name
    text = path.read_text()
    split = text.index('\n') + 1
    text = text[:split] + '\n' + notice + text[split:]
    path.write_text(text)
(TASK / 'outputs/CLAUDE_SEARCH_RELAY_2026-10-07.md').write_text(
    (REPO / 'docs/process/CLAUDE_SEARCH_RELAY_2026-10-07.md').read_text()
)
print(json.dumps({'decision': receipt['decision'], 'parent_receipt_sha256': sha(ROOT / 'receipt.json'), 'source_edited': False, 'stop_sha256': receipt['stop_sha256']}))

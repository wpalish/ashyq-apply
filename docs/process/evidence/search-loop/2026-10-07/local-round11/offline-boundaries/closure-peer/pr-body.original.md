## Task
[search-genuine-baseline] — worked on by gpt-6-astra. Depends on Draft #68; documents a closed local measurement attempt.

## What changed
The fresh original-ten genuine Job capture stopped at the first Exa MCP refusal on KAIST (`rate limited`, HTTP status unavailable). This preserves the STOP, complete retained failure, all ten physical case captures/logs and controller receipts without retrying or scoring the incomplete cohort. The Claude handoff now directs only saved-source offline work.

01:17:02–01:33:08 UTC on 8 October: 10 attempted; 9 captures admitted before STOP (6 completed Jobs, 3 bounded partial Jobs), plus one unadmitted provider failure. Physical totals: 391 Fetcher.get calls, 56 charged search queries, 108 prediction records and 14 programme URL records across six cases. These are collection counters, not precision, recall or accepted programme/fact counts. Exit 0 in child logs means capture persistence; the parent exited 2 with GLOBAL_PROVIDER_STOP_UNSCORED.

## Acceptance criteria
- [x] Freeze the tested executable source and exact source snapshot.
- [x] Collect fresh cases sequentially within recorded 6/60/120 limits; preserve honest partial Job statuses.
- [x] Stop globally on the first provider refusal; preserve it byte for byte.
- [x] Archive selected originals and update the Claude resume file.
- [ ] Complete a scoreable cohort and evaluate quality — not achieved; stopped cohort remains UNSCORED.

## Contract changes
No application, harness, test, defaults, gold or production change. HANDOFF newest entries supersede old READY --execute instructions. NativeReadBudget remains False. Scoring controller received an external static boundary repair, reviewed 15/15; it was never executed. IELTS v5 was independently rejected (7 PASS / 11 RED) and never integrated.

## Verification
```text
Closure receipt SHA cb6bf01534090ad499e33fb8905cbf61e6531249791ae9e1fb02e17a16d41e20
332 selected original files / 37,160,511 bytes; all SHA matched
STOP SHA 65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d
999 executable source paths reverified unchanged
scripts/handoff_check.py: exit 0
Documentation-only git diff --check: exit 0
Raw archived public HTML/body/log originals retain source whitespace; broad diff --check reports original trailing whitespace, deliberately not normalized.
```

The unchanged executable source 7c74a12d / snapshot19f349 previously passed exact full LOCAL run20261008T004040Z-check-bc90e5dc: 13/13 steps, 4292 unique backend tests on each SQLite/PostgreSQL database, coverage95.25%, mypy383, Ruff/format383, frontend232/type/lint/build, demo79PASS/1skip, auth6, audits0. No rerun on this documentation-only change; these gates are source proof, not quality or production acceptance. Local live capture used isolated SQLite, not PostgreSQL/Fly. No hosted workflow was started.

## Evidence and limits
Canonical receipt: docs/process/evidence/search-loop/2026-10-07/local-round10/provider-stop-closure/receipt.json. Retained evidence includes source-backed Aalto diagnosis: secondary Contact us classification and scoped tuition-row extraction losses; JS/CS/2027 applicability remains unknown. Runtime databases, env, private Git and browser storage are excluded. No score, semantic label read, provider/model switch, quota reset, purchase, old attempt resume, deployment or launch claim.

## Reviewer checklist
- [ ] Recompute receipt file hashes, physical counters and capture status split.
- [ ] Confirm STOP remains unchanged and no scoring is performed.
- [ ] Confirm 999 executable source paths match the tested snapshot.
- [ ] Keep quality acceptance and production checks outstanding.

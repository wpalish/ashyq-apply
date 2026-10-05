# PR #46 — prospective V10 model failure stop

## State

The source correction f4e935235fc7ed901ff1d7a274ec6255163e2823 is pushed and
passed both exact-source CI events, 8 jobs total. No V10 trial, live model/source
request, final protocol freeze, source tag, primary seal or reviewed-label
comparison has been created. V9 remains CLOSED UNSCORED; its original records,
source62efd47, tag and closure manifest are unchanged. The same Codex CLI account
reported its usage limit and displayed a reset on October10 at02:31, with no
display timezone specified. A new pilot requires legitimate free availability.

Main63d92e8 (PR49/50) was integrated at1b429fd after preserving V9. The integrated
fee/deadline/intake fixes are covered by the new backend gates. TOPIC_SEARCH and
NAVIGATION_FIELD_LEADS remain false; WALKER_SIGNAL_LESS_CAP remains None. The
parallel Claude diagnostics are explicitly not blind and do not replace this
pilot's expert comparison.

## Correction

- Recognize only authoritative failed-selector error/turn.failed events. Page,
  agent-message, reasoning and disabled-code-mode startup text cannot establish
  a model-account refusal. An unknown failed process stops with an unknown
  transport cause; it is never relabelled as quota.
- Set the shared STOP immediately on model usage/auth/transport failure. Preserve
  the first immutable model-batch-stop.json and every already-running selector's
  original stream, error and accepted journal prefix. The seven queued experts
  are not dispatched after the stop.
- Reject a persisted first-failure receipt before worker creation when a new
  parent process is started. Clearing in-memory state cannot restart that trial.
- Reject model-failed cohorts before sealing or reading labels, including an
  aggregate falsely reporting stopped=false, a per-case failure marker and an
  original failed stream whose higher-level markers were omitted.
- An ordinary per-case hang guard retains its existing replayed-prefix policy;
  it does not alone become a global model-account failure.

The pure policy is backend/evaluation/research/expert/model_failure.py. The ten
prospective helper/test snapshots and two unchanged historical dispatch helpers
are saved with original hashes in data/protocol.2026-10-05/v10-draft/manifest.json.
The report/freezer contract has21 modules, including the new policy. This draft
manifest is a recovery snapshot, not the final once-only trial freeze.

## Verification

| Gate | Actual result |
| --- | --- |
| Integrated backend full suite |4091 passed,94.85% app coverage |
| App/tests/evaluation Ruff, format, mypy |passed,369 source files |
| Combined parent/report/cohort/workflow/pure-policy mocks |444 passed in82.45s |
| Final actual-parent suite after a test-only style correction |48 passed |
| Report preseal model-refusal negatives |5 passed before combined suite |
| Prospective external helper Ruff/format/mypy |10 files passed |
| Isolated synthetic demo |20 rows, Groningen first, UBC OUT_OF_BUDGET |
| Alembic |one head,d8e412c6a901 |
| Exact-source cloud CI |8/8 jobs onf4e9352; runs37274400981/37274404579 |

The combined444 run includes the real ten-workspace sandbox constructor and
240 harmless cat processes; model/source/network/Git requests are zero. A final
test-only change rewrote set(generator) as a set comprehension; its prior bytes
are retained and the entire48-test actual-parent suite was repeated. No production
or protocol behavior changed after that combined run.

The unchanged frontend/migration/workflow Git trees match fully verified source
1ec0433 exactly. Its232 frontend tests/typecheck/lint/build are explicitly reused
old-source evidence. The fresh f4e9352 cloud events independently passed both
database suites4091 each, SQLite94.84% app coverage, frontend232 plus79 browser
and6 auth scenarios. Their five original full-log/JSON/watch records are saved
separately under protocol.2026-10-05/v10-draft-ci; manifestc7abf990,2060322 bytes.
Subsequent evidence/handoff metadata is not a new-head CI claim. All initial
failed fixture/config/import/style outputs are preserved
alongside the successful logs, rather than removed from the record. The existing
external helper B023 exception applies only to synchronous charge closures, as
in V9; app/tests/evaluation gates retain the repository rules.

## Next live step

After legitimate free Codex availability is established, restore only matching
draft helper bytes, fetch/integrate then-current main, rerun affected source and
actual-parent/OS gates, preserve their raw receipts, and create one final V10
freeze/source/tag. Allocate a fresh whole-ten paired pilot once on that exact
source. Never resume V9 or reuse its baseline captures. Preserve all attempted
actions and stop on provider/model refusal.

Algorithm60 reads/6 queries/120s; expert60 reads/6 queries/default reasoning and
one immutable900s hang guard remain fixed. Model thinking is excluded from
network counters. Seal all ten eligible primary receipts before the unchanged62
reviewed accessible facts. Require40/62 and supported per-fact causes
NOT_DISCOVERED/OTHER_PAGE/EXTRACTOR/CLASSIFIER/SLOT/BUDGET/PDF/JS/SCOPE/ACCESS
before batches of50; outside_policy is separate. HELDOUT150 remains untouched.
No live score, admission or complete-search readiness is claimed.

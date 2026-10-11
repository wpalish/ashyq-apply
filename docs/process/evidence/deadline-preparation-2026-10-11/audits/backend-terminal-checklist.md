# Saved-only backend acceptance checker

Status: **PREPARED / WAITING FOR ROOT TERMINAL SIGNAL**. No current run log,
receipt, app import, database, provider or native gate was read/executed for this
preparation. Source/helper remain unchanged. Expected counts are not results.

## Exact evidence inputs

- Current run (read only after root confirms terminal):
  `deadline-preparation-2026-10-11/evidence/backend-full/20261011T145907489813Z`.
- Corrected accepted predecessor result/JUnit:
  `exam-preparation-2026-10-11/evidence/backend-binding-final/20261011T134306725752Z/`
  with `result.json`, `sqlite/junit.xml`, `postgres/junit.xml`.
- Initial root pointer `backend-full/20261011T124000847599Z` was observed to have
  4653 cases before29 evidence-binding controls, not the final4682. That pointer
  mistake is retained in the partial receipt; it is not used for final carry.
- Root archived the predecessor under source/docs/process/evidence; compare
  duplicate hashes when required, do not treat a different archive as authority.
- Current binding metadata: `deadline-preparation-2026-10-11/evidence/native-binding.json`.
  Root states the required map grew557→563 paths; the runner's broader consumed
  source-before/after map must be checked as a superset, not forced to563 entries.
- Pure reference: `proposals/schedule/evidence/focused-sealed.xml`, SHA256
  `b62430381563460a574b0fb825f22363279158d9df886c49191cbcf9216623de`.
- API expected scenario metadata: `study-schedule-api-expected.json` in this folder;
  derives from the frozen external test AST (not pytest collection/execution).

## Mechanical acceptance checks

1. Confirm the terminal result reports actual complete SQLite **and** PostgreSQL
   phases, exit0, no failed/incomplete gate. Record raw receipt/JUnit/source-map
   hashes before summarising. A missing or unrecognised field is pending, not PASS.
2. Parse JUnit **attributes and outcome element presence only**; never print
   failure bodies, source payloads, historical facts/labels or system-out.
   Compare full `(classname, name)` keys and reject duplicate testcase keys.
3. For each phase compare every accepted predecessor key and outcome. The expected
   predecessor4682 is a sanity check; use its actual XML set as the authority.
   Missing/renamed old cases, extra skips or unexpectedly changed selection block
   acceptance until explained; do not silently exclude them.
4. Require the exact51 pure keys from the pinned focused reference, with zero
   failure/error/skip. Require each of the40 API scenarios (function + fixture
   SQLite/Postgres + explicit parameter), zero failure/error/skip. Confirm their
   module ownership; similarly named cases elsewhere are not substitutes.
5. Compute actual added set `current − predecessor`. It must consist of exactly
   the expected51+40 new keys; report actual total separately. **4773 is predicted,
   not predeclared as a passed count.** Never multiply the two phase totals into
   distinct test coverage: they are two database executions of the selected cases.
6. Independently read actual coverage numerator/denominator/percentage per phase;
   require the unchanged≥92 floor, all native selected tests and no lowering/skips.
   Cross-check terminal receipt, raw log and coverage artifact.
7. Compare consumed before/after source maps for exact equality; each required
   native-binding path must have the expected current hash in both. Extra consumed
   paths are allowed only as the documented wider map. Reconcile import/format-only
   changes with frozen source005ac46b; no carry across unproved semantic drift.
8. Check outside_attempts empty, child guards and owned Unix-PG evidence, source
   unchanged, cluster shutdown, runtime removal and no active-cluster markers.
   Source stability or passing tests alone cannot compensate for a failed guard
   or cleanup. Do not restart, probe ports, import app or run missing gates.

## Required qualifications in the terminal audit

- Saved receipt review is independent of gate execution; reviewer authored the
  API-test proposal and is not a blind test-author-independent acceptance.
- Calendar completion IDs are deterministic settings/calendar identifiers.
  Identical settings can yield identical IDs across cases; they are not credentials,
  globally case-unique provenance, official scores or verified completion.
  Owned profile/revision and frontend identity/intent fences provide isolation.
- Sequential create/update/stale409 tests are not concurrent HTTP race proof.
- Profile HTTP deletion with FKoff is a meaningful API control; account deletion
  with the new calendar needs its own actual receipt if claimed beyond static cascade.
- SQLite/private Unix PostgreSQL under synthetic isolation is not production,
  deployment, live search quality, learner outcome or an official exam score.
- UI/runtime/E2E acceptance and course completeness remain separate gates.

Terminal audit target: `audits/backend-terminal-review.md` plus a metadata-only
JSON receipt. Preserve every failed/incomplete earlier attempt; never replace
its bytes or borrow its PASS for a changed selection/source.

# G3 focused API2 — secondary source diagnosis

Status: **SEALED_SOURCE_ONLY_DIAGNOSIS_NOT_APPLIED_NOT_RUN_NOT_ACCEPTED**. Author: `/root/g3_frontend_foundation`. This note consumes a previously executed root diagnostic; it does not execute/import/collect/format any application, test, provider or database. No source, Git, HANDOFF, settings or privacy policy was changed.

## Recorded result and coverage of this note

Run: `g3-execution/evidence/backend-focused-api2/20261013T053108459965Z`. The actual runner recorded **192 tests, 48 failures, 0 errors, 0 skips**, exit 1 in 72.141 seconds; no coverage figure or full qualification. JUnit and pytest log hashes match the result. Before/after source manifests are identical; every source file used below still matches that actual run's manifest.

| Failure group | Count | Classification | Smallest repair direction |
|---|---:|---|---|
| `saved_unreadable` | 10 | Strong source diagnosis: ambiguous implicit ORM join in evidence-token query | Explicit `ProgramResultRow` query anchor and ResearchRun ON clause |
| Mixed catalogue versions | 2 | New fixture/assertion contradicts native versioned catalogue | Verify exact per-reference versions, including original review and pack lesson |
| `record_not_found` | 4 | New HTTP fixture asks for a forbidden missing dependency | Use an actual owned unreported task; preserve missing-dependency read behavior in a separate projection control |
| Expected 503, got 409 | 4 | Writer classifies every IntegrityError as revision conflict | Unconfirmed fallback for a failed write without a reconciled ACK or established revision conflict |
| `source_unreadable` | 28 | Assigned to root, not diagnosed here | Separate root investigation |

The runner's outer phase is named `sqlite`, but this JUnit contains both `[sqlite]` and `[postgres]` native fixture nodes, and its result records 319 private PostgreSQL connection events. The separate outer PostgreSQL phase was not started (`postgres_if_not_started=NOT_RUN`). Neither fact establishes a full SQLite/PostgreSQL gate.

## 1. Ten saved reads: ambiguous evidence-token join

**Observed:** eight lexical-link controls fail at `tests/test_admissions_actions_api.py:1283`; two selected-origin Today controls fail at `tests/test_today.py:306`. Prior personal/application writes returned accepted receipts. All ten scenarios have an owned selected source and full research access. They fail before testing link redaction or the selected plan's disappearance.

**Source cause:** `app/api/routes_admissions_actions.py:1167–1197` selects columns from `ProgramResultRow`, `ResearchRun`, and the claims/conflicts aggregate subqueries. At line 1183 it uses bare `.join(ResearchRun)` with neither `.select_from(ProgramResultRow)` nor an explicit join condition. Each of `ProgramResultRow.run_id`, `ClaimRow.run_id`, and `ConflictRow.run_id` has a foreign key to `research_runs.id` (`app/models/research.py:124,161,201`); both aggregate subqueries project their run_id columns. The query therefore exposes multiple possible implicit left sides. The SQLAlchemyError handlers at route2133–2134/current and2556–2557/Today convert such a query construction failure to the observed safe `saved_unreadable` response.

This is a **strong static causal diagnosis**, not an observed original exception traceback: the safe HTTP response and short JUnit log intentionally do not expose the underlying SQLAlchemy exception. No diagnostic import/query was run to reveal it. The precise query site and common selected-source path match all ten failures.

**Minimal repair:** only anchor this aggregate evidence query with `.select_from(ProgramResultRow)` and `.join(ResearchRun, ResearchRun.id == ProgramResultRow.run_id)`. Keep the existing explicit aggregate joins, profile/eligible-result/decision filters, 40-ID cap, actual bounded metadata recheck, and the locked-access early return without premium reads. Do not turn the failures into empty evidence or weaken response privacy.

All eight lexical expected results must remain exact: safe public https → `actionable_unverified`; token-bearing, javascript and loopback forms → `blocked` with `href=None`; no synthetic private marker echoed; no DML; native and G3 rows unchanged. Both selected-origin tests must retain the original selected-origin/event-ref and personal summaries when that native plan later becomes unavailable.

## 2. Two catalogue controls: one version is not the native contract

**Observed:** exact saved-slot comparison at Today149–161 succeeds. The later assertion166 fails because actual version set is `{starter-2026-10-11-v1, learning-pack-2026-10-11-v1}`, while the test demands only the attempt's starter version.

**Source cause:** `app/preparation/catalogue.py:26` defines the original starter content version; `app/preparation/learning_pack.py:41` defines PACK_VERSION. `pack_catalogue()`493–512 explicitly preserves CONTENT_VERSION for original lesson summaries and PACK_VERSION for additions (508). The native shared allocator uses `(lesson_id, content_version)` exact identities, and a starter attempt review retains its original version. A mixed saved allocation is valid. Today is already preserving exact `ref` values, dates, order and minutes from the accepted G2 allocation; normalizing them all to one version would break native identity.

**Minimal repair:** retain the existing complete saved-slot equality and ledger assertions unchanged. Correct the newly authored all-one-version assertion by checking the own review's exact `attempt_id` and CONTENT_VERSION, and the pack lesson's exact PACK_VERSION; the expected mixed version set should remain exact for this fixture. Use the native constants, not an arbitrary new version, a subset/any-version assertion, or copying the current catalogue over the saved refs. No catalogue, allocator, schema or product behavior change is warranted by these two failures.

## 3. Four dependency controls: legitimate HTTP writer must reject missing own IDs

**Observed:** Today fixture410–411 supplies `"f" * 32` as a dependency to `create_personal_task`, and `accepted()` demands HTTP200. The actual command returns the safe `record_not_found`404 before Today is read. The intended assertion441 (`dependency_missing`) is unreachable by this legitimate command sequence.

**Source cause:** `app/domain/admissions_actions.py:349–350` intentionally refuses any dependency ID absent from the current own task map. It prevents foreign/missing references at creation. Separately, the conservative Today read projection1205–1231 can annotate existing supplied read state with `dependency_missing`, `dependency_cycle`, or `dependency_not_reported_ready`. That defensive read behavior is not authorization to create a dangling dependency through HTTP.

**Minimal honest fixture repair:** the HTTP IANA-date/order scenario can depend on the genuine preceding own unreported task returned by `overdue` or `due`; retain the exact current revisions, timezone/date uncertainty, sorting, workload, no-official-closure and row-preservation assertions. Its expected dependency reason is exactly `dependency_not_reported_ready`. Keep a separate negative HTTP command assertion that this nonexistent/foreign dependency returns exact404 and leaves rows unchanged. Preserve the intended exact `dependency_missing` projection assertion in a separate source-domain projection control using explicit saved-input data without presenting it as a legitimately accepted writer history.

There is no repair that preserves both HTTP200 for the missing-ID command and unchanged domain349–350. Do not relax this writer guard, fabricate/re-hash accepted history to launder the dangling request, or simply remove dependency coverage. These recommendations correct new fixture assumptions; they do not weaken the old domain/privacy contracts.

## 4. Four trigger controls: IntegrityError is broader than revision conflict

**Observed:** concurrency test972–1037 creates a real rejecting event-insert trigger (SQLite RAISE ABORT; PostgreSQL SQLSTATE23514), observes actual current INSERT/UPDATE and event INSERT attempt in order, then requires `write_unconfirmed`503 at1008. All four dialect × existing-current variants reach this assertion but return409. Assertions after it, including fresh rollback equality and original UUID retry, have **not** been reached in this failed run; their outcomes cannot be claimed.

**Source cause:** writer route1939–1949 rolls back and performs owned/actor-checked original UUID reconciliation, then maps every `IntegrityError` to `revision_conflict`. A trigger/check rejection is an integrity failure without a competing accepted revision. The generic classification therefore misreports a rejected/unconfirmed write as a version race. The domain/schema need no change.

**Minimal repair:** retain rollback, authority checks, immutable UUID replay and reconciliation ordering. When no accepted original-UUID receipt is found, use `write_unconfirmed` for this unclassified SQL failure; do not infer a revision conflict from the exception's broad Python class. Existing explicit expected-revision mismatch (route1851–1852), conditional-current-update failure (route1800–1801), and domain predecessor check remain exact409 paths. If an additional uniqueness-race classifier is retained, it must establish the exact known competing revision/constraint rather than matching arbitrary exception text or exposing SQL/driver messages. The simplest finite fallback is unconfirmed503 after unsuccessful reconciliation.

Keep all existing trigger, executed-SQL, connection identity/order, private-marker non-echo, rollback, native-row preservation, same UUID/body retry and immutable repeated ACK assertions. Do not change expected503 to409 to make the test pass. Actual rollback/retry must be confirmed by root's authorized native run after the repair.

## Bounded repair and status boundary

Candidate production repair is one API route file: an explicit evidence-query FROM/ON and honest generic SQL-failure fallback. Candidate new-test repair is Today fixture expectations plus additive missing-reference controls. No schema/domain/config/privacy change is justified. Root owns the separate28 source-read diagnosis and all source application, write-ahead authority, static/native execution and acceptance.

The pins file records consumed evidence, exact20 assigned failed nodes/traces and source bytes as they existed in the failed run. Rechecks of those hashes are file integrity checks only. No proposed fix is applied, imported or run; no restored test pass, coverage, product readiness or production/search quality is claimed.

## Exact assigned nodes

### saved_unreadable (10)

- `tests/test_admissions_actions_api.py::test_current_informational_action_links_are_lexical_unverified_and_block_unsafe_forms[sqlite-https://example.edu/synthetic-programme-actionable_unverified]`
- `tests/test_admissions_actions_api.py::test_current_informational_action_links_are_lexical_unverified_and_block_unsafe_forms[sqlite-https://example.edu/synthetic-programme?token=SYNTHETIC_PRIVATE_INPUT_DO_NOT_ECHO-blocked]`
- `tests/test_admissions_actions_api.py::test_current_informational_action_links_are_lexical_unverified_and_block_unsafe_forms[sqlite-javascript:SYNTHETIC_PRIVATE_INPUT_DO_NOT_ECHO-blocked]`
- `tests/test_admissions_actions_api.py::test_current_informational_action_links_are_lexical_unverified_and_block_unsafe_forms[sqlite-http://127.0.0.1/SYNTHETIC_PRIVATE_INPUT_DO_NOT_ECHO-blocked]`
- `tests/test_admissions_actions_api.py::test_current_informational_action_links_are_lexical_unverified_and_block_unsafe_forms[postgres-https://example.edu/synthetic-programme-actionable_unverified]`
- `tests/test_admissions_actions_api.py::test_current_informational_action_links_are_lexical_unverified_and_block_unsafe_forms[postgres-https://example.edu/synthetic-programme?token=SYNTHETIC_PRIVATE_INPUT_DO_NOT_ECHO-blocked]`
- `tests/test_admissions_actions_api.py::test_current_informational_action_links_are_lexical_unverified_and_block_unsafe_forms[postgres-javascript:SYNTHETIC_PRIVATE_INPUT_DO_NOT_ECHO-blocked]`
- `tests/test_admissions_actions_api.py::test_current_informational_action_links_are_lexical_unverified_and_block_unsafe_forms[postgres-http://127.0.0.1/SYNTHETIC_PRIVATE_INPUT_DO_NOT_ECHO-blocked]`
- `tests/test_today.py::test_explicit_selected_origin_wins_and_failed_selected_plan_preserves_personal_summary[sqlite]`
- `tests/test_today.py::test_explicit_selected_origin_wins_and_failed_selected_plan_preserves_personal_summary[postgres]`

### catalogue_versions (2)

- `tests/test_today.py::test_g2_default_retains_exact_saved_slot_order_versions_reviews_and_single_budget[sqlite]`
- `tests/test_today.py::test_g2_default_retains_exact_saved_slot_order_versions_reviews_and_single_budget[postgres]`

### record_not_found (4)

- `tests/test_today.py::test_iana_dates_uncertainty_dependencies_and_stable_personal_id_order[sqlite-Pacific/Kiritimati]`
- `tests/test_today.py::test_iana_dates_uncertainty_dependencies_and_stable_personal_id_order[sqlite-America/Los_Angeles]`
- `tests/test_today.py::test_iana_dates_uncertainty_dependencies_and_stable_personal_id_order[postgres-Pacific/Kiritimati]`
- `tests/test_today.py::test_iana_dates_uncertainty_dependencies_and_stable_personal_id_order[postgres-America/Los_Angeles]`

### write_error_classification (4)

- `tests/test_admissions_actions_concurrency.py::test_real_g3_event_insert_failure_rolls_back_executed_current_sql_and_retries_original_intent[sqlite-False]`
- `tests/test_admissions_actions_concurrency.py::test_real_g3_event_insert_failure_rolls_back_executed_current_sql_and_retries_original_intent[sqlite-True]`
- `tests/test_admissions_actions_concurrency.py::test_real_g3_event_insert_failure_rolls_back_executed_current_sql_and_retries_original_intent[postgres-False]`
- `tests/test_admissions_actions_concurrency.py::test_real_g3_event_insert_failure_rolls_back_executed_current_sql_and_retries_original_intent[postgres-True]`

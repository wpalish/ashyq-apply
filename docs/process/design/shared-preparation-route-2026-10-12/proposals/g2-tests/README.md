# G2 native API and physical transaction test proposal

Status: **SEALED SOURCE PROPOSAL / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**.

Root is the sole application, Git, HANDOFF, source/runtime/helper writer. This packet proposes exactly two new test paths. It grants no execution, imports, fixture widening, provider calls, stopped-pilot work or production changes. Existing immutable designs remain authoritative.

## Exact files

| Application-relative path | SHA-256 |
| --- | --- |
| `backend/tests/test_shared_route_api.py` | `dadff091663ff0e27a386667efc2499e845ebdf51caadfc9db819fff3d0aacd7` |
| `backend/tests/test_preparation_write_concurrency.py` | `f6a10320113a7bfe30dfea42fd70c8d229f8da0463cd349edc66bf481167ab25` |

`SEAL.json` lists all inspected source/design pins. The backend packet was an external mutable draft when these pins were captured; its final `proposals/g2-persistence/SEAL.json` SHA `69d294842d5af3da3c5ee394307e061ec8f9a3a28e0ffd4db71880354a6a15da` declares exactly the same four schema/API/helper/model pins. The source-only reconciliation saw the final export current/latest-history mismatch guard and ID-only legacy row lock. Root must preserve this reconciliation when applying/formatting; a different backend seal requires a fresh source review, not an assumed match.

## Finite contract coverage

| Area | Proposed meaningful controls |
| --- | --- |
| Ownership and ordered selections | Own synthetic case, foreign/missing generic404 before history/UUID/result query; older own runs retained in explicit order; rejected/undecided422; no all-or-nothing premium body leak. |
| Immutable ACK and history | Exact accepted reference-only receipt, canonical UUID/study-day ordering, identical replay after expiry/research lock/legacy tick, different intent409, one atomic current/history revision. |
| Locked reads | Native SQL capture rejects premium column/claim/conflict reads; private poison values cannot enter ACK/current/history; current metadata remains safe and every selected goal survives separately. |
| Integrity and uncertainty | Inner reference/action/budget/catalogue/order corruption with rehashed outer map; absent current + history, behind-latest pointer, missing matching history and metadata mismatch yield explicit safe503 without repair/reset/export omission. |
| Native source/legacy identity | Claim mutation is a per-goal review state, not automatic target/reallocation; technical tick revision invalidates preview but doesn't change structural identity or show mastery; v1/v2 routes stay native. |
| Exact owned review | Beyond newest21 attempts, exact case/UUID/version; missing/foreign404, mismatch422; retired receipt readable without inferred exam association for new import. |
| Date acceptance | Real route clock crosses local Asia/Almaty midnight between preview recomputation and acceptance; old preview409, zero current/history/legacy DML. Only the clock seam is controlled; allocator and storage remain native. |
| Migration and erasure | Native Alembic downgrade/upgrade has no backfill; legacy/attempt/profile survive; additive export contains complete own ordered history; own case removal preserves sibling records. |
| Rollback | Real isolated DB trigger rejects history INSERT after real current SQL, testing absence/update rollback; original intent later succeeds once. Real User DELETE trigger rejects account erase after audit flush, retaining all original rows/auth cookie and zero new audit. |
| Two-delivery CAS | Physical connection pause after real acquired fence, native waiting evidence, same UUID+same intent identical ACK, same UUID+different intent409 and different UUID+same revision409. |
| Present legacy row | Both native legacy-v1 tick/structure and v2 writers in each order against G2; existing child wait, stale unaccepted preview409, no profile timestamp/no extra budget. |
| Absent legacy row | Both orders against real first native INSERT; immediate strong parent FK fence, no placeholder row; PG FOR NO KEY UPDATE negative control really permits the first INSERT while held. |
| Auth and session boundary | Actual native AuthSession cookie/user/membership, clean autobegin and stale last-seen commit before fresh fence; new/dirty/deleted incoming Session rejected before SQL while pending mutations remain intact. |
| Database policy | File SQLite native FK ON/WAL/15000ms policy and BEGIN IMMEDIATE first guarded SQL; PG transaction-local5s wait, fresh READ COMMITTED, strong exact Profile FOR UPDATE then existing child ID. |
| Bounded failure/release | Actual held native lock expires with safe503, no route rows; releasing the lock allows the same original UUID/input once. No new intent is manufactured. |
| Concurrent export | Real save N+1 between exporter captured currentN and all-history read must yield safe503; fresh export returns currentN+1 and complete [N,N+1], no exporter DML. |
| Case/account delete order | Native HTTP both orders versus G2; in-flight deleted case404 and later deleted auth401; sole-owner data erased, other-member organization/case/calendar/G2 receipts survive; PG User→sorted Org→membership→sorted Profile query order asserted. |

## Evidence rules for future root execution

- The SQLAlchemy after-cursor event pauses an already executed holder statement. It does not emulate acquisition or synthesize a refusal. No barrier waits for both writers after their conflicting fence.
- PostgreSQL uses an independent physical connection, `pg_stat_activity`, `pg_blocking_pids` and ungranted `pg_locks` to prove a native lock wait. SQLite uses the waiter's native driver trace plus independent failed BEGIN IMMEDIATE reservation (SQLITE_BUSY), not elapsed time alone. Distinct driver IDs and observation are recorded through native pytest `record_property`.
- The lock-timeout control deliberately waits for existing15s SQLite/5s PG policy. Wall-clock duration is bounded and is supplementary evidence; its native failed response/unchanged rows/release-and-retry outcome is required.
- Existing `prep_lab`/`pg_engine`/migrations/no-IP/no-DNS and no-lifespan TestClient are reused. The SQLite wrapper installs exactly the relevant native app.db pragmas after fixture setup sessions close. It never disables FKs or changes lock limits to create a test-only guarantee.
- The existing pgserver fixture may skip when unavailable. Such a skip means PostgreSQL NOT_QUALIFIED. Collected count, skipped tests, source review or old pure142/static results are not a two-database API/concurrency PASS.
- Tests only use isolated synthetic cases/principals/public fixture payloads. No real credentials, providers, LLMs, auth state, source captures, heldout150/frozen labels, official score or admissions readiness are accessed or claimed.

## Integration limits

These are source proposals, manually read only. Formatter, Ruff, mypy, collection, imports and runtime have NOT_RUN; root must apply/reconcile source under its write-ahead, perform its normal format/static/native gates in the existing approved binding and preserve raw output before claiming any outcome. Root may repair a concrete failed control through a separately recorded source change; sealed external originals stay immutable.

Accepted UUID replay does not assert current programme applicability or current receipt pointer health. Dynamic current views remain separate; expiry does not destroy owned history. The fixed export mixed-read refusal is conservative and does not promise a globally serialized read. No official admissions decision, exam booking/result delivery, score prediction or verified mastery is introduced.

Remaining separate acceptance: API/UI end-to-end owner/case epoch and uncertain-retry controls; release floor92/full native regression; explicit qualified PostgreSQL receipts. They are not established by this packet.

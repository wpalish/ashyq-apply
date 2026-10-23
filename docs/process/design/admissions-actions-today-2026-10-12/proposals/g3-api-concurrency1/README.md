# G3 real API contention — additive test proposal

2026-10-12T16:44:44Z · **EXTERNAL_SOURCE_PROPOSAL / NOT_APPLIED / NOT_IMPORTED / NOT_COLLECTED / NOT_RUN**.

## Scope and authority

One proposed application postimage: `backend/tests/test_admissions_actions_concurrency.py`.
Its preimage is exactly `a8a80fbce0c6f43e883fe2c41f32a4e19300ab9792db1dca232977e5b573211e`.
The root grant is `G3_API_SOURCE_GRANT.json`; concrete transport is the immutable
`proposals/g3-api-wire1/G3_API_WIRE_V1.md`. Root alone applies the source and runs
native gates. No application, laboratory, configuration, guard, dependency,
Git, HANDOFF or runtime helper was edited by this author.

The preimage's seven storage test functions and every existing helper body remain
byte-for-byte unchanged. The only replacement in the diff is the existing
`test_study_schedule_api` import extended with `unchanged_inputs`; other imports
are additions. Everything following the original final assertion is appended.
`PRESERVATION.txt` records the literal whole-body-region comparison. No AST parser,
application import, formatter, linter, test collection or execution was used.

Root's previously recorded 38 storage controls are a separate qualification of
the preimage. They do not qualify these newly proposed API races or this packet.

## Native controls proposed

All new tests use the existing migrated `shared_route_lab`: file SQLite with
foreign keys ON/WAL/native timeout, or the approved private PostgreSQL fixture.
No new skips, mocked commits, fake concurrent results or provider fixtures.

| New test family | Source cases per DB | Concrete oracle |
| --- | ---: | --- |
| Initially absent/present current × equal UUID / changed body / distinct UUID | 6 | Two actual requests contend on independent connections. Equal UUID/body returns the exact original ACK once; changed body returns safe UUID409; different UUID at the old CAS returns safe revision409. Fresh complete state/event validation, original replay and every native row unchanged. |
| Existing native legacy tick ↔ personal G3 write | 2 | Executed legacy DML and G3's existing-child lock contend in both orders. Both valid personal writes succeed; legacy revision/tick survive, no G3 selector or second budget, applicant/subscription/research/payment inputs unchanged. |
| Physical event INSERT rejection, current absent/present | 2 | A database trigger rejects the real event INSERT after current INSERT/UPDATE actually executes. Safe write_unconfirmed503, fresh old pair/all native rows unchanged. Removing the test trigger permits the exact original UUID/body once; its next replay does not mutate the pair. |
| Native case erase ↔ G3 write | 2 | Both orders wait on the native strong Profile fence. Write-first200/delete204, delete-first204/write404, no resurrection on retry; sibling's complete G3 rows and native export unchanged. |
| Authenticated account erase ↔ G3 write | 2 | Actual native password/session request, both orders and native lock ordering. Sole case/User/org erased; another member's workspace retains exact own G3 receipt/state bytes and original full-principal actor digest without a User FK. Later old cookie401. |
| Union cap19→20 | 1 | Actual HTTP setup of 18 applications plus one case-personal source binding. Withdraw and delete one original result; it still counts. Two competing new applications at one CAS accept one, reject the loser409. Reviewed new intent to distinct21 returns422 while application count is only19. Another binding to the already-counted target is allowed at20. |

Six new test functions; 15 parameter cases per DB by literal source arithmetic,
30 proposed additional cases across the two fixtures. Together with the 38
preimage storage cases, 68 is an **expected collection count**, not an observed
collection, result or PASS claim. Actual root collection is authoritative.

## Why the contention evidence is physical

The unchanged approved `NativeSqlRace` and `ordered_race` are imported from
`test_preparation_write_concurrency.py`. Holder pauses only after its native SQL
has executed. Waiter has a different driver connection. SQLite evidence includes
an actual driver trace and a third connection's SQLITE_BUSY reservation; PG
evidence includes `pg_locks`, `pg_blocking_pids` and the observed native wait.
The inherited `physical_write_wait` JUnit property records these observations.

No new sleep is introduced to arrange a race. The existing approved PG observer
uses bounded 0.01-second polling to observe the native lock; its predicate and
implementation are unchanged. Reuse is a proposal, not proof that a new G3
writer reached the fence. A test fails if that real guard/wait evidence is absent.

The event failure control uses the approved G2 physical-trigger pattern on the
new isolated table, and an `after_cursor_execute` callback proves current SQL
actually completed. It records a separate `g3_executed_current_rollback` property
only after all rollback/retry assertions succeed. No transaction exception or
API result is monkeypatched. Trigger and callback cleanup are unconditional.

## Exact wire expectations and failure meaning

- POST `/api/profiles/{id}/admissions-actions/commands` accepts the existing
  closed `ActionRequestV1` directly; first acceptance and exact replay return
  the immutable `ActionWriteReceiptV1`, status200.
- Safe fixed errors come from the unchanged `domain.admissions_actions.ActionError`:
  `admissions_actions_uuid_conflict`409, `admissions_actions_revision_conflict`409,
  `admissions_actions_write_unconfirmed`503 and `admissions_actions_limit_exceeded`422.
- A deleted case keeps native404. An erased account's subsequent cookie keeps
  native401. Database exception text is never a client error payload.
- The cap source binding obtains a **real API source preview**, then copies its
  exact reference-only selection/digest. It does not reuse the original storage
  helper's test-only digest. Native synthetic selected columns remain authority,
  despite deliberately rejected copied payload decisions.
- All accepted sequences undergo the original fresh-session complete header,
  state/self-hash/request-digest/affected-ref/export validation. This is personal
  storage integrity, not official programme applicability, receipt verification,
  admissions readiness or score proof.

A missing route, an implementation that never acquires the required fence, a
duplicate accepted event, an unsafe error, a half-committed pair, lost native
ticks, case resurrection, erased sibling or freed withdrawn target makes these
tests fail. Do not weaken an oracle to turn a genuine failure into a pass.

## Deliberately finite coverage and next executor work

This packet covers the requested **real Profile/existing-child wait** alternative.
It does not introduce a new five-second timeout/reconcile experiment. It also
does not add absent legacy first-insert contention, structural/v2 calendar
writer variants, all 12 command races, entitlement-change interleavings, mixed
Today reads or frontend recovery. Original native controls for their existing
families remain intact; new API/Today contract coverage is authored separately.

The new tests do not import `test_admissions_actions_api` or `test_today`; local
payload/ACK helpers avoid a reciprocal import cycle if those modules reuse the
existing storage helpers.

Root must read the diff/postimage and check the exact preimage first, reconcile
the source with the sealed route proposal, then apply only this test file and
run the authorized native static/focused/full gates. No new helper, network
exception, DB policy or runtime scope is requested here. Formatting/type/runtime
status remains **NOT_RUN** until a source-bound executor receipt exists.

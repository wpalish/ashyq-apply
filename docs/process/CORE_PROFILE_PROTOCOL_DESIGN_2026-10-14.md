# C / N09 — profile concurrency and unknown-response protocol

Status: DESIGN_ONLY; not applied, not tested. Baseline source e58e5415 plus green metadata36bb824e. No independent agent/model or stopped security review.

## Writer matrix from source

- api/routes_profile.py:create_profile allocates ApplicantProfileRow, scalar display_name and full normalized payload, then audit/commit. No create replay today.
- api/routes_profile.py:update_profile replaces the entire payload/name. Missing precondition is confirmed; old two clients may lose independent fields.
- api/routes_results.py:rerank (persist=False by default; only explicit persisted rerank writes the profile) reads profile, modifies preferences/funding/weights, replaces full payload in the same transaction as result reranking. It is a second profile writer and must adopt the same revision precondition. Do not close N09 by fixing PUT alone.
- jobs/worker.py:319–326 reads normalized accepted payload; profile is not written here. research profile-input provenance must remain actual normalized accepted state, no fabricated accepted version.
- api/routes_profile.py delete and routes_account.py organization/account erase delete profiles. Preserve their current actor/parent order; profile command metadata must cascade even when SQLite FK enforcement is absent.
- Profile GET/list/cases/export are readers. G2/G3/preparation operations lock the profile parent but do not rewrite applicant payload; do not change their receipt classes/digests to store profile commands.
- ProgramResult identified writers are notes/decision, rerank, runner upsert/_update_result/store_result and refresh/reextract through Runner. Their shared concurrency strategy is D, still OPEN.

## Proposed server contract

1. Add one positive profile row revision (initial1) on current head a0d94e902027; conditional UPDATE against exact expected revision and owner. Increment on every actual profile write, including persisted rerank. Name and JSON come from the same accepted normalized payload in that transaction.
2. Use a required If-Match strong numeric profile ETag for PUT and persisted rerank. Expose revision in read DTO; exact current profile response ETag can be derived from it. Missing precondition428, malformed strong tag400, stale precondition412 with safe typed code/current revision only (no raw profile/PII in the error). No wildcard/weak/multiple tags, no legacy unsafe last-write-wins fallback. Old clients must upgrade/reload; update their request fixtures without weakening existing assertions. Nonpersisted rerank does not write profile, still needs D result-writer protection.
3. Use a client UUID Idempotency-Key for profile creation/update/persisted rerank. Original UUID/body/expected revision is held until confirmation. Same UUID+same normalized binding replays its immutable acceptance; different body/kind/target/expected revision rejects. Owner is principal user+org and profile, not a body identifier.
4. Add separate profile-command receipt metadata, not a third admissions progress model: request UUID/kind/owner/profile/normalized command digest/expected and accepted revision, safe response metadata where necessary. No duplicate full applicant payload/essay/passport copy. Profile receipt is immutable; export own metadata and cascade on profile/account erase, including ORM cascade for SQLite. Creation is atomic with its receipt; a duplicate unique key rolls back its new row and re-reads only the matching owned receipt.
5. Reply includes current profile plus original command acceptance revision. If a replay acceptedR1 but current profile isR3, preserve the local draft and display accepted-but-changed context; do not publishR3 as the normalizedR1 submission or restart a research with an invented accepted body. Research uses actual current server state, and conflict prevents start.
6. Reuse fresh bounded write transaction primitive: discard only clean dependency reads; SQLite BEGIN IMMEDIATE before owner/receipt reads; PostgreSQL READ COMMITTED and bounded lock wait. Atomic revision UPDATE remains the final precondition. Required lock/authority ordering for create/put/rerank and account erase must be explicitly checked before applying; no late new global Organization/User mutex. Retry identity remains the same; automatic retry is not permitted.

## Proposed client contract

- StoredProfile gains revision and typed command receipt metadata; toDraft strips both. Every profile writer sends the current accepted revision; no updated_at-based authority.
- Reuse owner-scoped case drafts/pointers and synchronous currentAdmissionsCase/currentProfileDraft. Keep at most one unresolved profile intent per case in a versioned bounded owned slot; persist original UUID/body/expected revision before dispatch. Fail closed on corrupt/unavailable recovery instead of promising durability. Never allocate a replacement create key after an unknown response; manual retry reuses the original intent. Case changes synchronously fence UI callbacks and retain only their own command state.
- saveProfile/autosave/startRun/rerank use one profile write path. Primary accepted response remains published before optional reads. Newer typing is retained. Unknown/confirmed failure/stale precondition are separate; no unbounded automatic retry.
- Conflict stores base, local draft and freshly authorized current profile. Offer explicit three-way field review: independent local/server edits are proposed for review, same-field conflicts undecided; no write or silent overwrite. Apply selected merge changes only the local draft and accepted current revision; require explicit Save/start, keep original rejected intent as conflict rather than ACK.
- A replay whose current profile advanced beyond the original accepted revision reconciles through the same review state. Profile input notices continue to compare actual saved normalized data; no research starts after a failed/conflicted save.
- Case export/delete remain usable without research. Receipt/draft cleanup occurs only with exact accepted command/case deletion acknowledgement, never by discarding unresolved entries for capacity.

## Tests-first acceptance / bounded steps

C1: source/lock matrix plus finite server schema/model/migration/transaction/API grant. Native OFF counterexample should send the existing valid profile body with a precondition header to old endpoints (ignored there), so it demonstrates real overwrite, not an import error. Two real clients/Sessions readP0 then contend; both field orders, SQLite/PostgreSQL, same field/different fields, stale/missing/malformed precondition, owner isolation, UUID same/different binding, committed ACK loss/replay, delete cascade/export and migrated legacy rows. Do not fake Session/store sinks or weaken originals.

C2: finite typed client/Store/recovery/conflict form grant after C1 contract is sealed. Deferred callbacks, preserved budget/GPA/local text, no start after conflict, exact create retry, reload/case/owner isolation/corrupt storage, accepted ACK before optional failures and newer typing.

C3: exact source shared native path and race browser controls, static/type/lint/full frontend, full native SQLite/privatePG floor92/one head/upgrade/guarded downgrade, unchanged seed if pipeline consumer was altered. Full gates serialized/frozen; retain first failures. C cannot be called locally accepted until both server and client are qualified together.

All prior STOP/refusal/history/heldout150 boundaries remain unchanged. No live quality/provider/model/production/main/cloud/secrets/payments or deployment. D/E/F/G and launch gates remain pending.


## Root review correction / smaller reuse

Actual source confirms rerank persist defaultsFalse; the earlier proposed defaultTrue assumption was wrong and has not reached code. Persisted rerank is nevertheless a real second profile writer. Existing profile deletion preserves ID/action audit metadata and has explicit Organization key-share→Profile order before audit FK insertion; do not introduce a late organization lock.

Prefer reusing immutable AuditEvent metadata as profile command acceptance storage with nullable canonical UUID/full actor lookup columns and a bounded unique org/actor/key index, rather than creating another private payload/receipt table. Keep digest/kind/expected/accepted revision in safe structured detail, never full input; existing own export already carries these events. Deleted profiles retain only existing audit-style opaque command metadata and reject creation replay via a missing owned profile instead of allocating a duplicate. Organization/account erase removes its audit namespace. This is a DESIGN proposal, requires exact migration/old migration-test compatibility review before source, and does not alter G3 receipt classes or frozen digests.

A required explicit `X-Expected-Profile-Revision` integer header is a simpler alternative to strong ETag parsing: same atomic compare-and-swap semantics, stale409, missing428, with revision in the typed response. Final choice is not applied yet. Old unsafe writes cannot silently stay enabled. Modern frontend persists the original UUID/body/revision before dispatch; legacy profile creation compatibility must be explicitly bounded and never treated as safe unknown-response recovery.

First C0 diagnostic: new tests/test_profile_write_concurrency.py only; actual approved native migrated SQLite/privatePG lab, two separate Sessions readP0 before valid HTTP PUTs with the proposed revision header. Both field orders must reject the stale request and retain first change; old endpoints ignore the header and overwrite. No Session or API storage mocks, no new model/server API code yet. This is a tests-first counterexample, not a full acceptance gate. Backend-native14 focus runner is a fresh external clone of13 with only target list/output binding and fresh646source pins; original13 and full24 proof untouched. No closed queue rerun.

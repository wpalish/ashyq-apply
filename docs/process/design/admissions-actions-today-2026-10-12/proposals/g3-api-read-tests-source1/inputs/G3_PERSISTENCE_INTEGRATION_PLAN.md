# G3 persistence integration plan

2026-10-12 · **DESIGN_ONLY · NOT_APPLIED · NOT_IMPORTED · NOT_RUN**  
Writer/executor authority remains root only. This plan assigns no migration ID and grants no source or runtime authority.

## 1. Scope, inputs and disposition

This bounded read reviewed G3_INITIAL_SOURCE_GRANT, its eight hash-pinned accepted design/contract documents, ROOT_G3_INITIAL_IMPLEMENTATION_DISPOSITIONS.md, and only the native shared-route model/API/wire, preparation transaction/plan-read, profile export/delete and account-delete seams listed below. All nine observed native source hashes match the source grant's baseline. All eight accepted design hashes and the supplied implementation-disposition hash match. No unsealed producer packet was read.

The separate three-path schema/pure/test proposal is a dependency handled by root. This plan neither reviews nor adopts that packet and does not infer its current application or gate status. The initial grant authorizes only that proposal; it does not authorize this persistence/API/migration stage.

**No frozen-contract/native-seam mapping blocker was found.** Usable G3 persistence remains a future root-owned implementation with separately qualified physical/API/export/delete controls. A design mapping is not execution, database readiness, release, production or full-product acceptance.

Source root:

`/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`

External artifact root:

`/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12`

The grant records branch `task/admissions-actions-today`, released parent `e58443ef1d8909e3b4faecd5b0bba52114cdd925` and predecessor Draft87. Those identities are metadata, not a Git observation made here.

### Precedence that the integration must retain

1. Frozen V2 + final-v2 define exactly one selector policy, `follow_current_accepted`, for g2/legacy_v2/legacy_v1.
2. ROOT_G3_INITIAL_IMPLEMENTATION_DISPOSITIONS clarifies **no clear/none command**. None is a derived no-saved-plan read state. The earlier conditional root-acceptance phrase about selector clearing is not a command grant.
3. EventRef addendum replaces the older finite-document receipt-digest wording: every hashed-state EventRef is **exactly event_id/revision/kind**, with role/record association checked through affected_refs metadata.
4. Rebind keeps the durable task and original report, including nullable `binding_digest_at_report`. It never replaces that value with the new binding or silently resets/transfers reported fulfillment. Earlier-binding reports are separately labeled for review.
5. Validate original finite values before serialization/normalization. Trusted context, IDs, time and prevalidated source/plan observations are explicit server inputs. Client body never supplies actor, allocated ID, official verification or whole state.

## 2. Exact prospective source boundary

The following are **candidate paths for a later root write-ahead**, not granted edits. All paths are relative to the source root above.

| Prospective path | Necessary change |
|---|---|
| `backend/app/models/admissions_actions.py` (new) | Only two profile-owned current/event tables and their metadata/constraints. |
| `backend/app/api/routes_admissions_actions.py` (new) | Route-local fixed validation/error handling, current/event/history reads, unsaved binding/import previews, closed UUID+CAS command, validated reference-only export helper and own Today read/adapters. No new transport/command outside the frozen API map. |
| `backend/app/models/applicant.py` | Exactly two G3 `all, delete-orphan`, `passive_deletes=False` relationships and type references. |
| `backend/app/models/__init__.py` | Explicit registration of the two new model classes only. |
| `backend/app/main.py` | Explicit new router registration only. |
| `backend/app/api/routes_profile.py` | Add validated G3 reference-only current/events/submission sections, counts and note to existing owned export. Preserve delete status/body and existing erase transaction. |
| `backend/tests/test_admissions_actions_api.py` (new) | Meaningful real-API owner/replay/head/reference/privacy/export/delete controls. |
| `backend/tests/test_admissions_actions_concurrency.py` (new) | Migrated physical SQLite/private PostgreSQL two-connection races, rollback and erasure controls. |
| `backend/tests/test_today.py` (new) | Selected-plan identity, read bounds, independent permissions and actual interleaving/mixed-read controls. |

The sole intentionally unassigned migration path is:

`backend/migrations/versions/<ROOT_ASSIGNED_AFTER_FRESH_SINGLE_HEAD_OBSERVATION>_admissions_actions.py`

A concrete filename, revision and down_revision cannot be fixed by this task. Root must replace this placeholder with an exact absence-checked path in a later grant. No candidate migration file was created.

Dependencies already separately proposed under the initial three-path grant:

- `backend/app/schemas/admissions_actions.py`
- `backend/app/domain/admissions_actions.py`
- `backend/tests/test_admissions_actions.py`

They are dependencies, not extra edits authorized by this plan. If integration needs their changes, root must issue the corresponding exact amended preimages/allowlist.

**Native dependencies remain read-only:** shared_route model/schema/API/domain; preparation_transactions; native schedule/preparation routes and models; G1/result/source/security/tenancy/payments; routes_account; native export/calendar and deadline behavior. No private G1/G2 loader import/refactor, global exception change, new account/auth/reset workflow, extra ledger or helper change is proposed.

Frontend Documents/Application/Today recovery and exact navigation are a subsequent vertical-path stage described by the frozen source boundary. Their source was not inspected or edited by this persistence task. Persistence alone must not be reported as finished UI delivery.

## 3. Fresh head observation before assigning migration identity

Root's future sequence must be recorded under a separate bounded authority:

1. Resolve the exact source snapshot and accepted pure dependency bytes. Re-pin the migration directory/source, model/API preimages and accepted design/disposition hashes in the isolated lab copied from that snapshot.
2. Obtain a **fresh isolated Alembic heads observation** immediately before migration assignment. It must enumerate exactly one source migration head, with raw output/time/source binding recorded. No old G2 receipt or filename ancestry substitutes for this observation.
3. Root chooses a fresh unused revision and exact migration filename, checks absence/collision, and explicitly sets down_revision to that observed single head. Multiple heads, an unreadable observation or changed source stops assignment rather than inventing an ancestry/merge.
4. Authorize only the exact model/migration/integration/test paths under a new write-ahead. This plan's three-path predecessor grant is insufficient.
5. Later, root separately qualifies physical migration state: a fresh synthetic database at that observed parent, additive upgrade to the proposed head, exact head/table/constraint checks, preserved old rows and downgrade/re-upgrade controls on both supported dialects. Any existing lab DB head must be observed rather than assumed.

Frozen source-boundary documents mention `c3e71d902023 → b5c81d9e2022`; this is historical document information only. This task ran no Alembic/interpreter/import/database command and assigns neither identifier as the next migration parent.

## 4. Two-table storage and erase invariants

Follow G2's concrete model pattern (`models/shared_route.py:27–75`) while retaining G3's different state/receipt semantics.

### Current aggregate

- One profile PK/FK with ON DELETE CASCADE; positive bounded revision, literal wire schema, complete bounded typed personal/reference-only state, state_digest and accepted updated_at.
- State holds at most20 applications/400 tasks plus the nullable accepted selector. Durable application/task IDs are server supplied; targets/intake/route/purpose/award remain their creation identity.
- No source-result, User or additional Organization FK. Source disappearance must not cascade personal history.
- No profile payload/score/quota/updated_at, native schedule/sidecar/tick, G2 current/history or research mutation.

### Immutable event

- Stable server event ID, profile FK/cascade, unique(profile,revision), unique(profile,client UUID), ordered profile/revision access; schema/kind/UUID/request digest/receipt digest/accepted UTC metadata.
- Full safe immutable receipt plus finite `affected_refs` metadata duplicated from the same server-applied delta. Application IDs≤20, task IDs≤400; actual selector create/replace alone sets active_selector_changed.
- A submission that merely mentions task refs does not mark those tasks mutated. Header association comes from the applied delta, not client mentions.
- No per-task/application ledger, third table, extra AuditEvent or actor-account lookup.
- Event's acceptance fields are immutable; created/updated timestamps, if the native base supplies them, must be tied to the accepted time rather than independently ticking an event on replay.
- Two ApplicantProfile relationships use ORM delete-orphan with passive_deletes=False, as native `models/applicant.py:43–61` does. ORM erase remains meaningful under SQLite FK-policy variation; physical concurrency controls still need real FK enforcement.

ActorRef uses the server-derived canonical full native user_id+organization_id digest and actor_kind. Raw actor IDs/name/email/role are not stored in the new ACK. Replay by a different currently authorized workspace member returns the original actor/ACK. Shared-member account removal retains the shared case's pseudonymous event references; this is not anonymous history or a physical-student attribution.

## 5. Write/replay/lock protocol

Use released `begin_fresh_preparation_write` / `lock_owned_preparation_profile` / `begin_owned_preparation_write` unchanged. Concrete native observations: `preparation_transactions.py:22–107`, shared-route UUID/reconciliation `:232–267` and write `:832–963`.

1. Closed route-local body validation uses only fixed safe errors. Reject nonfinite/forged actor/official/whole-state input without echo. A dirty/new/deleted/nested incoming session is refused; never commit/discard unrelated changes. Clean dependency reads may be rolled back to reserve the fresh command view.
2. Verify the native own case/current actor before any case UUID, record or source access. Any optional clean pre-fence UUID read is rechecked under the fresh fence.
3. SQLite uses BEGIN IMMEDIATE as the first guarded SQL. PostgreSQL uses fresh READ COMMITTED and the existing local5s lock timeout. Keep strong owned Profile lock, fresh active-user/member check and existing legacy child **ID-only** lock. No placeholder child, late User/Organization write lock or JSON decode before UUID replay.
4. Under that fence, look up the exact own UUID and fully validate its original saved receipt. Equal canonical request returns the original200 body/time/actor/hash; changed intent fixed409. Replay does not inspect mutable current/source/plan/access or require preparation/research entitlement. Deleted/unowned case cannot replay.
5. For genuinely new intent only, validate the current exact head and expected G3 revision. Revision0 creates the first state/event; later writes advance exactly once. Existing personal actions use owned G3 records/frozen refs even if the target is gone/rejected/locked. New target/bind/award branches enforce their separate current owned/approved-or-maybe/research guards.
6. Validate requested source preview/plan tokens, then the **prospective** current target union≤20. Replacing a case-personal binding frees an old ID only if no other current record retains it. Withdrawn/disappeared applications still count. At20 another binding to an existing ID can succeed; a distinct21st cannot.
7. Derive trusted actor, IDs, accepted time and authoritative observations. Apply the closed pure transition; preallocate event ID → three-field EventRefs → state_digest → receipt with after_state_digest → receipt self-hash → atomic current/event/header write.
8. Flush/commit current and exactly one event together. Any event/flush/commit/CAS/unique failure rolls back **everything**. Never return mutable current view as the ACK.
9. A losing/uncertain transaction reconciles in a fresh owned read after full rollback. Same intent replays original ACK; changed UUID body conflicts; absent accepted event after a genuine revision/unique loss is ordinary revision409. Unreadable reconciliation/unknown lock or commit result gives fixed write_unconfirmed503, not claimed absence.
10. Unknown response retains exact UUID/body for user-reviewed identical retry. Revised intent/preview uses a new UUID. No quota, charge, lesson/attempt, allocator or G2/legacy save occurs.

Do not copy shared-route's `_require_preparation` / native preview-allocation policy into G3 personal commands or selector. Native save requires preparation permission; G3 personal recording/selection is expressly independent.

## 6. Read/query/current-head integrity

All G3 read/preview/export helpers operate within the caller-owned session and own profile predicate, using no_autoflush. No new GET DML, repair, backfill, placeholder or transition. This is a G3 application contract; existing native authentication bookkeeping is not falsely advertised as globally write-free.

| Read role | Required observation/bound |
|---|---|
| Current presence | One own current + scalar latest accepted event metadata statement, patterned on shared-route `:200–228`. Neither present ⇒genuine revision0; history-only/current-latest disagreement ⇒fixed503. |
| Exact head | One full own event identified by state.head_event_id and exact revision. Validate typed body, request/self-hashes, copied schema/kind/UUID/time/header, request revision advance and actual applied-delta association. |
| State/head equality | Exact profile throughout; state.revision=current.revision=head.revision; recomputed state_digest=current.digest=head.after_state_digest; current.updated_at=head.accepted_at; exact head ID. G2 snapshot_digest is not substituted for G3 state_digest. |
| Inner state | Closed finite constraints; unique/bounded own IDs; task/application/binding target association; union cap; report/status provenance; selector policy; role-compatible event references. Outer JSON rehash cannot bypass these checks. |
| Older EventRefs | Exactly ID/revision/kind, ≤1662 distinct refs; own metadata chunks≤200/max9. Validate role/kind and relevant affected application/task/selector association. Do not deserialize all old bodies or claim their self-hash was verified. |
| History/event | Own ordered page default20/max100 or exact own event; fully validate each returned receipt/header/hash. Missing/foreign identifiers use the same safe404. No current source lookup is required for safe accepted history. |
| Correction | Read and validate only the exact own prior declaration needed by that closed command, under the write fence. Correcting a declaration appends history; no receipt overwrite or replacement target. |

Corrupt current/head/reference metadata yields fixed admissions_actions_saved_unreadable503, not empty/reset, omitted record, best-effort reconstruction or an automatic selector fallback. Current checks do not claim to validate unreferenced old history gaps or protect against coherent malicious rewriting of both rows. Full history/export provides its separate checks.

### Source and privacy bounds

- Own run/decision metadata first; G3 current target union≤20 includes every current application target plus case-personal bindings.
- Only currently owned eligible target + current research grant can load premium source/claims/checklist. New binding is strict; existing self-report/date/note/correction/declaration does not need a G1 read.
- At most one G3 source observation per target for that role, reused across its records, and one separately bounded authoritative raw-checklist observation per target for the comparison role.
- Native G2 remains its public≤20-goal reader, with its own source roles. Composite Today≤40 distinct result IDs. These are role/target bounds, **not a claim of20/40 SQL queries**.
- G3 raw occurrence binding retains all original list/index refs, duplicate/scope omission, exact raw URL absent/present identity, independent proof/item/procedure digests and actual G1 link only when unambiguous. Native G1 private loader/body is unchanged.
- Locked source emits fixed research_locked plus old own accepted refs. No new URL/presence/block reason/proof hash/source digest/revision/name/prompt/scope/claim refs/count or cached-card enrichment.
- Observed revocation at the final recheck clears all earlier new premium slices and contradictory joins. History outside current union is safe not_evaluated, not a historical source scan.
- Action links use the separate frozen raw-authority-first lexical G3 rule. No raw blocked authoritative fallback/ACK/error, parser repair, note-to-link extraction or destination verification.

All route-local fixed error codes/messages must retain the frozen dictionary; existing native401/404 and billing contracts are unchanged. Personal replay/read/export/selector adds no402 or entitlement mutation.

## 7. Native selector and Today integration

Selected plan observation and G3 expected revision are distinct CAS identities. New selector stores only reference tokens, not plan/settings/allocation copies. Replay retains the original observation even if the native plan advances/disappears.

- Stored selector wins and remains g2/legacy_v2/legacy_v1 with follow_current_accepted. No implicit clear or alternate origin on failure.
- Genuinely absent selector derives by G2 current **or history presence**, else raw non-null saved v2 sidecar, else saved v1 row, else none. Metadata/database failure is unavailable, not absence.
- New selection requires a valid own persisted chosen plan and matching observed tokens, without preparation/research entitlement as a prerequisite. It does not create a blank plan.
- Use public in-process `read_shared_route`, `read_schedule`, `read_learning_path` and native access with explicit session/principal/profile arguments; no HTTP self-call/second Session/private G2 loader.
- Raw v2 identity needs a narrow G3 adapter because `routes_preparation.py:203` uses truthiness. Recorded `{}` is present/malformed ⇒legacy_v2/unavailable, never no-plan/v1 fallback. Persisted sidecar digest is not refreshed GET-output digest.
- Native v1 remains its today-based projection with saved settings/ticks; full settings digest/technical revision differs from structural fingerprint. No exact version is invented for bare v1 lesson IDs.
- G2 head consumes exact accepted saved slot array/order/ref versions/minutes; saving a newer G2 head never rewrites a G3 legacy selector. Preparation access is observed separately from research access and exact-content/review availability.
- One bounded fresh scalar/token recheck after component assembly covers G3 head/selector, chosen plan and relevant owned decisions/access over≤40 refs. Changed token ⇒mixed_revision/needs_refresh with observed origins; retain safe own records/receipts and withhold contradictory joins. No loop, fresh allocation or coherent-snapshot claim.
- Personal records survive selected-plan/source failure. One selected study workload is counted once; documents remain unallocated/not_estimated. No new deadline/certificate/official readiness inference.

## 8. Additive export and deletion

### Export

Add a caller-owned validated `export_admissions_actions_records` helper within the new route module. Existing profile export has already checked owner (`routes_profile.py:292–293`). New names/section structure must be frozen in the later API/source grant.

Return complete reference-only current state and **all ordered accepted receipts**, including applicant declarations/corrections, with exact counts and a provenance/privacy note. Preserve all existing profile/results/claims/conflicts/attempts/legacy/G2 fields and their owner-export policy. No premium current-source status joins or historical research access requirement is introduced.

Validation must cover full revision sequence1..N, first-event and predecessor/before-digest links, full per-row receipt/header hashes, and actually loaded current/head versus loaded latest event/state digest/time. An observed intervening accepted write/malformed/gapped row gives safe503 rather than a mixed complete export, omitted history or the UI page limit. A final bounded scalar head observation may reconcile observed inputs; no retry loop or atomic all-product export guarantee.

### Case/account deletion

Keep native lifecycle transactions unchanged:

- Profile erase: fresh transaction →Organization key-share →current actor/member reads →strong own Profile/existing-child fence →ORM delete plus native audit →one commit (`routes_profile.py:428–475`).
- Account erase: fresh transaction →User →sorted Organizations →sorted memberships →sorted sole-member Profiles →existing audit/ORM erase →one commit (`routes_account.py:370–461`).
- New G3 writes lock own Profile and only existing child ID, add no late Org/User FK/extra AuditEvent; this preserves the native lock order.
- New ORM descendants erase with the same profile transaction. No write may reinsert orphan state/event or replay after acknowledged case deletion.
- Shared-member account deletion preserves shared workspace/cases/history; sole-member confirmed erasure removes its cases/G3 rows. A pseudonymous historical actor is not resolved through a deleted User.
- Event/write or erase failure rolls back its whole transaction. Database cascade alone is not concurrent-erasure proof.

Browser cleanup/import remains a separate later UI gate: only matching DELETE ACK tombstones the exact case family; no owner-wide wipe, raw legacy import-key deletion at ACK or complete browser-erasure promise. This server plan cannot certify those behaviors.

## 9. Meaningful future controls — all NOT_AUTHORED / NOT_RUN by this task

| Control family / prospective test path | Required observable proof |
|---|---|
| Additive migration / concurrency file | Fresh parent single-head input; only two tables/expected FKs/unique/check/index metadata; real migrated file SQLite and private PG upgrade/downgrade/re-upgrade; populated native rows unchanged, no backfill/second head. |
| First/present head races / concurrency | Two real connections, absent then present current: same UUID equal intent returns one event/revision and identical original ACK; different body same UUID409; distinct UUID same revision yields exactly one ACK. Preserve accepted state/event/header equality. |
| Real lock waits / concurrency | Actual Profile/existing-child contention, observed wait before release or native5s PG timeout, bounded failure and fresh UUID reconciliation. No mocked Session concurrency or fake elapsed-time inference. |
| Dirty session / API+concurrency | Pending unrelated new/dirty/deleted/nested state remains uncommitted/undiscarded; fixed write_session_unavailable. Clean dependency reads can be restarted. No unrelated DML accepted. |
| Atomic event failure / API+concurrency | Physical event insert/flush/commit failure leaves prior state/head and native tables unchanged; original unknown intent stays retryable, no partial ACK. |
| Case erase both orders / concurrency | Write commits before erase ⇒all G3 rows subsequently removed; erase wins ⇒write/replay refuses deleted/unowned case; no orphan insert, sibling untouched, FK/ORM effects observed on real connections. |
| Account erase / concurrency | Sole-member erase versus write in both orders; shared-member removal retains shared cases/history, removed actor cannot write/replay; event/erase rollback and lock order remain safe. Use existing synthetic principal fixtures, no live accounts/reset activity. |
| Cap race / concurrency | At19 two concurrent distinct new targets cannot commit21; at20 existing-ID binding allowed; withdrawn/disappeared target still counts; rebind computes prospective removal only when no current association remains. |
| Current/head corruption / API | History-only/no current, wrong head ID/revision/time/digest/profile, rehashed outer state with invalid inner task/binding, same-head extra receipt hash ⇒fixed503 and zero G3 GET DML. |
| Metadata association / API | Valid own ID/revision/kind for another record/role fails; mention-only submission task refs cannot become mutated header association. Copied full header mismatch fails on head/history/export. |
| Metadata bounds / API | At20 applications/400 tasks instrument queries:≤1662 refs, chunks≤200/max9; no older-body deserialize/history-wide G1 load. Distinguish metadata checks from full self-hash validation. |
| Replay actor/privacy / API | Member B repeats A's same intent after source lock/expiry/deleted target/plan advance/corrupt mutable head and receives exact A ACK; different full actor IDs with shared prefix differ; no email/name/User lookup or rewritten accepted fields. |
| Personal versus strict source / API | Existing task/application update/declaration/correction survives missing/rejected/locked target without premium SELECT; new target/bind/award validates owned current selection and access before payload. Missing/foreign404 indistinguishable. |
| Rebind report / API | Stable task/history/report and nullable original binding_digest_at_report preserved; earlier-binding annotation requires review; no silent fulfillment transfer/reset; new explicit report records then-current binding. |
| Fixed errors/locked loads / API | Forged actor/official/raw URL/nonfinite/SQL fault has constant code/message with no raw input/identifier/title; instrument forbidden premium tables/columns and no new source metadata under lock; native billing/errors unchanged. |
| Export completeness / API | >100 events exported in full, exact counts/sequence/headers/digests; missing/corrupt old row or real accepted write between loaded head/events gives safe503. Existing export fields preserved; no current-source join. |
| Delete ORM policy / API | Physical FK-on plus native SQLite FK-policy variation: new current/events removed through ORM; sibling preserved. Do not use FK-off tests as the only concurrency proof. |
| Selector/Today / test_today.py | Exact observed tokens conflict; immutable old selector replay; g2 follows accepted head, legacy choice survives new G2 save; corrupt G2 history-only/empty v2 sidecar remains selected/unavailable; no DML/fallback/blank save. |
| Today interleaving/read roles | Real writer commits between component reads and one scalar recheck: mixed/lock labels, cleared earlier premium slices and withheld contradictory joins;≤20 G3 roles/≤20 G2 goals/≤40 composite refs; no allocator/provider/quota activity. |
| Regression / root later gates | Preserve native G1/G2/preparation/account/profile export/calendar contracts and existing controls. Exact new bytes/helper/source binding must qualify before native/full gate; no skip, guard/timeout/floor/network relaxation or inherited G2 PASS. |
| Later vertical acceptance | Separate synthetic real-API browser reload/second-context persistence, exact Today version/review handoff and owner/case/epoch recovery/deletion controls. A backend test suite alone does not prove this UI path. |

## 10. Current evidence and remaining prerequisites

Observed read-only native files, all matching appbaseline772:

| Source path | SHA256 |
|---|---|
| backend/app/models/shared_route.py | a1cf969acfde2dea68c42c98edd8ad99fa8ebc5b18633f6bf1bdbf0bc9ab8e20 |
| backend/app/models/applicant.py | 613cdd1db26bf5dd9bc4af39af310b8720a6edec5e2e68a6090a95d59c8d6c28 |
| backend/app/models/study_schedule.py | 087ccef37010f3eeddce5329856832de1d4aeea796cba48a52e439cf0ca03626 |
| backend/app/api/preparation_transactions.py | ecbf9c12c95d6a178bf6d1c8c2aca8dcc3b5522e8b0aa4da64e465c99c68d2d7 |
| backend/app/api/routes_shared_route.py | fec7d50d7e29cbebea1d1d46bb2245ccb129f216974ba281fd2550013bbe37f9 |
| backend/app/api/routes_profile.py | b12a3a301829cc4f4eed5d8df53c2315efa11e5fb0e05e3ba2d9ead25d5202a3 |
| backend/app/api/routes_account.py | 50c4bf6cc7da8d72596dd87c9acff858894a12fce441ea2273a3b6c460697521 |
| backend/app/api/routes_preparation.py | 11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2 |
| backend/app/schemas/shared_route.py | 50c2dca8ad250f3d12fc9645a6307ac4dd05bf05a61c79c17bbf925b4c8042e2 |

Before source opens: root must independently accept the pure packet, observe a fresh isolated single migration head, assign an exact migration path, and issue an explicit persistence allowlist/preimage write-ahead. Any new helper/runtime binding and physical/native/full execution needs its later authority.

Only this external plan and its seal were written. No migration ID, application/helper/HANDOFF/Git change, interpreter/import/test/database/network/provider/auth or stopped-workflow activity occurred. All old provider/model/quota/security/reset/live/expert/heldout/controller STOP boundaries remain unchanged.


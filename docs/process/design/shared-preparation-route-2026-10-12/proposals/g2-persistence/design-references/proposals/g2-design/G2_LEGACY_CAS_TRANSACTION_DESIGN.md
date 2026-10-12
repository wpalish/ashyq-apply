# G2 legacy revision CAS — transaction design

**2026-10-12 · EXTERNAL DESIGN ONLY · NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** This proposes how a future G2 command can protect its legacy-calendar anchor on the current SQLite/PostgreSQL seams. No application/source/test/helper/Git/HANDOFF bytes, runtime, database or configuration were changed. No test, provider, source capture or benchmark was run. The accepted v2 documents remain unchanged. Root must approve a new write-ahead and verify the controls below before claiming implementation or concurrency proof.

Read-only checkout: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`.

## 1. Recommended decision

Use a **new-command transaction fence in the G2 router**, keeping existing v1/v2 calendar PUT code, schemas, UUID attempts and calendar JSON unchanged:

- **PostgreSQL:** a fresh `READ COMMITTED` command transaction; acquire `SELECT ... FOR UPDATE` on the existing, currently owned applicant-profile row; then select any `StudyScheduleRow` for that profile `FOR UPDATE`, and compare its technical revision plus validated structural anchor. Hold both locks through the single G2 current/history commit.
- **SQLite:** a fresh command transaction whose **first SQL statement is `BEGIN IMMEDIATE`**; perform owned-case, accepted-UUID and anchor checks inside it. SQLite's writer reservation protects the absent-row case as well as existing-row writes. `FOR UPDATE` is not a substitute on SQLite.
- Do not create a placeholder `StudyScheduleRow`, issue a no-op profile `UPDATE`, touch `profile.updated_at`, increment legacy revision, consume quota or change legacy settings/ticks merely to serialize G2. A lock-only `SELECT` does not invoke `TimestampedBase.updated_at.onupdate`.
- For clean case-deletion ordering, separately approve a small companion change at the start of native `delete_profile`: take the same owned parent lock before cascade work on PostgreSQL. The route is already in the planned G2 wiring set, but this locking behavior is an **additional explicit decision**, not merely an export addition. Its concurrency controls are a gate below. Do not claim all-writer ordering while leaving deletion uncoordinated.

The legacy guarantee is specific: a legacy update/create committed before G2 acquires and checks its fence cannot be missed; a legacy write attempting to proceed while G2 holds the fence cannot commit a conflicting legacy change before that G2 transaction ends. A write that is blocked until after G2 commits is ordered **after** the G2 acceptance. A request having started earlier is not itself a committed revision change and does not automatically imply 409. This distinction makes accepted v2's interleaving rule testable without rejecting a valid serialized order.

## 2. What the actual source establishes

| Native seam | Observed behavior and consequence |
| --- | --- |
| `api/routes_preparation.py:116–163` | v1 `expected_revision=0` inserts revision 1 and relies on unique `profile_id`; an existing-row write is `UPDATE ... WHERE profile_id AND revision=expected`, sets settings/revision/updated_at, commits or rolls back with 409. There is no parent/profile coordination lock. |
| `api/routes_preparation.py:342–422` | v2 checks the same legacy row/revision and structural fingerprint, then CAS-updates only `learning_path`, revision and updated_at. G2 must preserve this shared v1/v2 revision contract. |
| `models/study_schedule.py:16–29`; migration `a9e5c14d2021:18–27` | One positive-revision child per profile. Native FK to `applicant_profiles.id`, `ON DELETE CASCADE`, no `deferrable`/deferred option specified. This existing FK is the proposed PostgreSQL first-insert fence; no new legacy column is required. |
| `domain/learning_schedule.py:22–25` | `settings_fingerprint` excludes `completed_task_ids` and sorts study days. Technical revision is a preview→save guard; a later tick-only increment must not turn an accepted G2 receipt into structural `needs_review`. |
| `db.py:30–53,169–175` | Session uses autobegin, no global isolation override, no explicit SQLite `BEGIN` event, `autoflush=False` in production. SQLite connection hook enables FK, WAL and 15,000 ms busy timeout. `get_session` yields one Session and closes it; it does not establish an immediate transaction. |
| `security.py:191–239` | The same dependency can already have performed auth SELECTs. It may commit expired-session deletion or a last-seen change before producing the frozen `Principal`. Native local principal setup also commits (`:116–148`). Thus `session.in_transaction()` at G2 entry does not prove that an appropriate command fence exists. |
| `api/tenancy.py:12–24` | Authority is exact profile ID plus principal organization; missing and foreign are the same 404. An accepted UUID never substitutes for this owner check. |
| `models/applicant.py:38–52`; `routes_profile.py:404–427` | Native case deletion uses ORM child cascades (`passive_deletes=False`) before its final parent delete. Adding parent→child locks only in G2 can create an opposite-order wait with a child-first deletion. |
| `models/base.py:35–42` | `updated_at` is an SQLAlchemy DML `onupdate` default, not a side effect of a row lock. Do not turn a lock into DML or attach unrelated dirty profile fields to a G2 commit. |

An early revision read plus a final identical read **without a fence** is insufficient: a legacy writer can still commit between the last check and the G2 commit. Locking only a nonexistent child, locking only G2's new current row, or an advisory lock taken only by G2 does not protect the first v1 insert. PostgreSQL `FOR NO KEY UPDATE` on the parent is also insufficient for the proposed FK-based absent-row fence because it is compatible with the referencing key-share lock. The strong `FOR UPDATE` choice is intentional.

## 3. Exact new-command transaction boundary

These are protocol steps, not an applied helper or runnable proposal.

### A. Owner-first preflight and accepted replay

1. Validate the strict write DTO and compute its versioned canonical request digest without DB writes. Preserve exact ordered IDs, expected shared revision, full legacy anchor, preview/source identity and UUID; do not normalize away meaningful intent differences.
2. With the actual dependency Session and frozen principal, call native `owned_profile` before lookup of own `(profile_id, client_write_uuid)`. If a history row already exists, equal digest returns its exact immutable reference-only receipt; changed digest returns 409. This happens before preparation/research access, current revision or mutable content/source gates. No allocator or old premium payload is needed for an accepted replay.
3. For a still-new command, end only this read-only preflight transaction. Check that the Session has no pending `new`, `dirty` or `deleted` state; unexpected pending mutation is an internal integration error, **not** permission to commit or silently discard it. Roll back the clean read-only transaction to release snapshots/connections and expire loaded ORM state. Do not roll back uncommitted auth mutations: native auth commits its own accepted changes before returning a principal, and that assumption must be covered by an actual authenticated-route control.
4. Retain the primitive frozen principal and parsed request/digest, not stale ORM objects or values from the preflight. Recheck owner and accepted UUID inside the command transaction after acquiring the fence. This avoids a replay being incorrectly denied because a competing delivery committed while this one waited.

### B. Start the command on the same Session

- SQLite: after the clean boundary, acquire the transaction using `BEGIN IMMEDIATE` **before owned-profile SELECT, history SELECT, G1 call or any other guarded DB read**. Inspecting the dialect without SQL is harmless. Do not use the catalogue-importer's `elif not session.in_transaction()` pattern as the route guarantee: an auth/read dependency may have autobegun and would otherwise skip the fence. Nested transactions/savepoints do not upgrade a previously read SQLite snapshot into an immediate writer safely.
- PostgreSQL: choose/assert `READ COMMITTED` at the **fresh connection/transaction boundary**, before the first SQL statement. This can be route-local rather than a global engine/isolation change. Do not set isolation after SQL has started or assume the deployment's default merely from `create_engine` lacking an override. Later controls must record/assert the actual command isolation. The same Session is supplied explicitly to the existing in-process G1 route adapter; no second hidden Session is used for its source assembly.
- Under either dialect, no external network, provider, LLM or HTTP self-call is allowed while holding the fence. Only bounded native DB reads and the existing pure allocator/content functions are involved. No process-wide mutex is an adequate multi-process substitute.

### C. PostgreSQL parent then legacy child

The PostgreSQL lock selector must filter **both** `ApplicantProfileRow.id == profile_id` and `organization_id == principal.organization_id`, use a real `FOR UPDATE`, and produce native generic 404 if no owned parent remains. It is a lock-only selector; do not alter `owned_profile`'s normal guard semantics or write profile payload/timestamps to implement it.

After this parent lock is acquired, recheck own accepted UUID **before** any mutable gate. An accepted equal replay releases the read/lock transaction and returns the old receipt; unequal digest releases it and returns 409.

For a still-new UUID, read the legacy child in a **new SQL statement after parent-lock acquisition**, using `FOR UPDATE` when it exists, fresh scalar values or `populate_existing` rather than a stale identity-map row. Then:

- no row means exactly `(technical_revision=0, structural_fingerprint=null, imported_learning_refs_fingerprint=null)` in the first increment;
- a row means its actual positive technical revision plus native validated `settings_fingerprint`; malformed persisted settings is an explicit unavailable/correction state, not a fabricated absent anchor;
- compare the complete captured anchor to the current anchor. A mismatch yields 409 and no G2 mutation, including tick-only or v2-only revision changes;
- the first increment imports no legacy refs automatically, so the imported-ref component stays null. Do not infer it from the existence of a v2 sidecar.

**Present-row ordering:** native v1/v2 UPDATE/DELETE obtains a conflicting child-row lock. If it already won, G2 waits for its transaction and then reads the actual resulting revision at `READ COMMITTED`; otherwise it cannot change the locked child before G2 ends.

**Absent-row ordering:** PostgreSQL's normal immediate FK check on a first legacy child INSERT takes a key-share lock on the referenced profile. That conflicts with G2's parent `FOR UPDATE` and is retained to the inserter's transaction end. If the insert/check already won, G2 waits and, in the later child-read statement, sees its committed revision 1. If G2 won, the inserter cannot complete its FK check/commit until G2 ends. An uncommitted child tuple can already exist when it waits; G2 is allowed to see absence and accept revision 0 **before** that later commit. Do not mistake invisibility for an absence oracle or claim the insert can commit through the strong parent lock.

This absent-row mechanism depends on the actual enforced immediate FK and `READ COMMITTED`, not only Python model declarations. A later migration/control must inspect native PostgreSQL FK enforcement/non-deferral and demonstrate the block with separate physical connections. If those prerequisites cannot be established, the absent-row guarantee is not qualified; do not fall back to a no-op profile UPDATE or weaken the contract.

### D. SQLite ordering

Once `BEGIN IMMEDIATE` succeeds, other connections cannot begin/complete a conflicting SQLite write until G2 commits or rolls back. This covers a first legacy INSERT, existing v1/v2 UPDATE, G2 current/history creation and a case DELETE, without a placeholder row or reliance on SQLite's ignored `FOR UPDATE`. Read the owner, replay and anchor fresh inside this transaction.

If a legacy writer already holds the SQLite write reservation, G2 waits within the configured busy limit or receives a known busy failure; after acquiring a **fresh** immediate transaction it observes that writer's committed row/revision. Never continue using a pre-lock read snapshot after a busy/snapshot failure. With the production connection hook, normal wait is bounded at 15 seconds; test fixtures must deliberately establish the same relevant connection pragmas and transaction behavior rather than assume the freshly constructed test engine inherited the application engine's event listener.

This serializes writers across the SQLite database, not only one case. Keep it limited to the explicit short G2 PUT command; do not start `BEGIN IMMEDIATE` on GET, history or unsaved preview. It does not mutate settings, produce a legacy row or allocate a second planning budget.

## 4. Save, UUID and rollback semantics retained

Inside the held fence, for a still-unaccepted command:

1. Check the started preparation term and separate research visibility before premium G1 data; perform strict full ordered G1 selection, own exact reviews and source/content/preview comparisons using the existing in-process seams. Do not reuse a preflight source payload as authoritative after waiting. Establish the G2 planning date in the requested IANA zone after acquiring the fence; a stale planning-day fingerprint returns 409. Native G1 retains its own explicit freshness observation. None of this proves atomicity against independent research/entitlement writers.
2. Validate the shared current revision, even though the per-case parent lock also orders G2 commands. Keep the explicit unique create/CAS update and `(profile_id, revision)`/`(profile_id, client_write_uuid)` history constraints. Locks are coordination, not a replacement for revision or UUID semantics.
3. Recheck the observed source/decision manifest near the write as accepted v2 requires, using fresh SQL/identity-map refresh where relevant. Construct only the safe reference-only receipt and exact immutable allocation. Do not modify existing `StudyScheduleRow`, profile payload/updated_at, attempts, official scores, result verdicts, subscription terms or research quota. Construct new G2 rows by `profile_id`, without attaching unrelated mutable profile state to the commit.
4. CAS-create/update G2 current and insert its matching history in **one transaction**, followed by one commit. A history insertion failure must roll back the current change. Return the persisted immutable ACK; do not rebuild a dynamic G1 view after commit and call that the save receipt.
5. On current CAS/uniqueness/history conflict: roll back the **entire** command transaction, release its locks, and re-read owner plus own UUID in a **fresh** read transaction. Same digest returns the exact accepted receipt; different digest returns UUID 409; absent UUID returns ordinary revision 409. A deleted/foreign case still returns owner 404 first. Do not catch the exception and keep using an aborted PostgreSQL transaction or an old snapshot.
6. On known lock timeout/deadlock/SQLite busy: fully roll back, perform the same safe own-UUID reconciliation where the DB is available, and otherwise return an explicit safe concurrency/unavailable outcome preserving the client's original UUID/draft. Do not silently retry with new UUID/intent or rerun a provider. A connection loss around commit is an **unknown outcome**, not proof that no receipt exists: reconcile by the same UUID before reporting success or offering a new write.

Different UUIDs using the same shared revision retain one accepted revision and one conflict. Same UUID/same digest retains one history row and identical ACK bytes even if the second delivery waits until preparation expiry, independent research lock or a legacy revision change. No receipt is mutated by later ticks, source supersession or content retirement.

## 5. Explicit deletion lock-order decision

The preferred PostgreSQL order for G2, future personal-command writers and case deletion is **owned parent → legacy child/current child → history/other child work → commit**. A new G2 parent lock does not make the current child-first `delete_profile` follow that order automatically.

Concrete possible wait with unchanged deletion:

1. delete transaction obtains a legacy or new G2 child-row delete lock;
2. G2 obtains the parent `FOR UPDATE` and waits on that child;
3. deletion eventually waits for the parent needed by its final DELETE.

PostgreSQL must break the cycle. Relying on it choosing G2 as victim cannot protect the unchanged deletion route from a new 500. Therefore the future source gate should require the owned parent lock before `delete_profile` enumerates/cascades children, preserving 204/generic 404, audit semantics and sibling isolation. This is within an already named file but must be recorded as an additional behavior/preimage/acceptance change. It needs no profile DML and does not change v1/v2 route bodies.

If root does **not** adopt that companion ordering, this proposal can still describe the legacy update/create fence, but its status remains **not qualified for concurrent case deletion**. Do not report “all case writes serialized.” Do not expand auth/account-deletion or other bulk-parent writers silently; inspect their real order and either coordinate them explicitly in a later write-ahead or document a bounded failure limitation. Existing `owned_profile` privacy guards must remain exact. SQLite busy/upgrade behavior of a delete already in a read transaction is also a required control, not a promise that a PostgreSQL row-lock call fixes it.

## 6. Required real two-session controls — proposed, not run

Use migrated file-backed SQLite plus real migrated local PostgreSQL; no in-memory shared-connection substitute. Use two independently created native request Sessions/physical connections, record distinct driver connection identities (and PG backend PIDs where available), bounded Events/futures and the actual native legacy HTTP PUT. A controller may inspect lock state read-only. Install/remove test synchronization only around the relevant actual SQL boundary; never wait for both writers to pass a fence that intentionally blocks the second. No outbound provider/network is needed; preserve existing native test network refusal.

| Control | Forced ordering and acceptance assertion |
| --- | --- |
| C1 present v1 wins before fence | Seed legacy revision N; G2 preview captures N. Session B commits a native v1 tick-only PUT N→N+1 while session A is held **before** acquiring its fence. A then begins/acquires, sees N+1 and returns 409, with no G2 current/history row. Structural fingerprint unchanged; do not substitute a structural mismatch for this technical control. Repeat with a structural v1 edit. |
| C2 present G2 wins | A acquires fence and reads N, pauses before G2 commit. B attempts the actual native v1 UPDATE with expected N on its separate connection; verify it is blocked, not merely unscheduled. A commits one G2 receipt anchored at N; B then commits native legacy N+1. G2 receipt/history stays exact. A later G2 GET has no structural review for tick-only; structural edit yields its separate reason. Both successes are the intended G2-before-v1 serialized order, not a CAS failure. |
| C3 present v2 sidecar | Repeat C1/C2 using the native v2 learning-path PUT with valid exact refs and the same shared revision. G2 never rewrites either legacy JSON; sidecar-only revision change invalidates an unaccepted preview, but with no import it does not create an accepted-plan structural change. |
| C4 absent first v1 wins | Begin with **no** legacy row and preview anchor 0/null/null. B's first native v1 INSERT/FK check owns the relevant PG key-share/write reservation; pause before B commit. Start A's fence and demonstrate the wait. B commits revision 1; A's fresh locked child read returns 1 and G2 save is 409, no G2 receipt. Native legacy row exists exactly once. |
| C5 absent G2 wins | Begin with no legacy row. A holds the strong parent/immediate fence and confirms absence; B attempts a first native v1 INSERT on another connection. Demonstrate that B cannot complete/commit until A ends. A commits its G2 receipt with anchor 0, and **does not** create a legacy row; only then B commits exactly one revision-1 legacy row. Check profile payload/updated_at unchanged by G2, receipt exact, no stale pre-lock snapshot. This is the key absent-row control. |
| C6 PG weak-lock negative control | On isolated synthetic rows/connections, show why parent `FOR NO KEY UPDATE` is not the production fence: its compatibility with a referencing key-share lock lets the first legacy INSERT commit. Then prove C5 uses actual `FOR UPDATE`, enforced nondeferred FK and `READ COMMITTED`. Negative control is not an alternate product path or a permissive fallback. |
| C7 duplicate UUID while waiting | Two G2 native commands both initially miss one UUID. A accepts while B waits on its fence. Before B proceeds, expire preparation and change legacy revision or research visibility. B rechecks UUID before those mutable gates and returns byte-identical safe receipt, one current revision/history event. With changed digest B returns UUID 409. No allocator/write on replay. |
| C8 different UUID and history failure | Two different UUIDs with the same expected shared revision give one ACK/one 409. Separately inject an actual history-insert DB failure after G2 current SQL; verify full rollback, old current/history unchanged, no legacy/profile/attempt/quota mutation. A new connection re-read is required to assert persistence. |
| C9 read-autobegin and authenticated dependency | Exercise a real owned auth dependency that has already read the shared Session; also cover the native last-seen commit path. Assert the new command obtains its fresh `BEGIN IMMEDIATE`/PG isolation before guarded reads and does not issue nested-BEGIN errors or commit/discard pending unrelated changes. A deliberately dirty incoming Session must fail closed in the command boundary. Existing auth receipt/session semantics remain unchanged. |
| C10 case delete both orders | With the reviewed companion ordering, (a) delete wins parent, then A sees generic 404/no resurrection; (b) A wins parent, delete waits, A returns its committed receipt, then deletion erases current/history/legacy/attempts and returns 204. A sibling remains exact. Repeat SQLite with a delete whose owner read occurred before A's immediate fence; verify no unhandled busy-snapshot/500 or document and fix that boundary before qualification. No sleeps/one-connection mocks may stand in for the ordering. |
| C11 bounded lock failure / release | Hold the native fence in B past A's explicitly bounded wait. A fully rolls back/reconciles UUID and reports safe contention without any current/history change. Release B; a later delivery of the **same** original intent/UUID has normal semantics. Verify locks/connections are not leaked and unrelated owner/case reads remain possible. Do not mistake timeout for source absence. |

The existing `test_learning_schedule_api.py:438–546` is a useful harness pattern: two native HTTP clients, Events around the real calendar UPDATE and recorded driver identities, plus exact legacy JSON assertions. It currently controls v1-versus-v2, **not** the new G2 absent-row fence. Existing `prep_lab` is parameterized SQLite/PG (`test_preparation_api.py:38–112`), but its SQLite test engine is freshly constructed without the production `db.py` connect event; explicitly establish/record relevant test pragmas and driver transaction mode. The local PG fixture can skip when unavailable (`tests/conftest.py:37–85`): a skip is **NOT QUALIFIED**, not a substitute PASS for C4/C5.

For PG C4/C5, record native FK `condeferrable=false`/`condeferred=false`, command isolation and real block relationship, not just a timing-based `future.done()` assertion. For SQLite record `journal_mode`, `foreign_keys`, `busy_timeout` and that the first guarded transaction SQL is actually `BEGIN IMMEDIATE`. Assertions about physical connections, block state, final native HTTP outcomes and a new-session stored-state read are all needed. Test timeout/release phases must be bounded and shorter than a forced permanent hang.

In every successful/failing G2 control, compare the synthetic profile payload and `updated_at`, legacy row ID/created_at/settings/learning_path/revision, attempts, subscriptions and research/payment/audit inputs to their expected native-writer effects. A SQL listener should specifically reject G2-origin `UPDATE applicant_profiles`, `UPDATE study_schedules`, new legacy INSERTs and unrelated DML. Native v1/v2's own intended writes are not falsely classified as G2 mutation.

## 7. Scope, performance and adoption limits

- The profile lock can delay native first inserts and profile updates for **one case** on PG. SQLite has database-wide writer serialization. Keep write transactions short, no provider calls; timeout outcomes remain explicit. A global table lock would unnecessarily block unrelated cases and is not the proposed fallback.
- The held legacy fence proves no undetected legacy commit through that command; it does **not** prove fresh official admissions requirements. Existing result/claim/source-supersession, membership, subscription and entitlement writers do not all take this fence. Retain accepted v2's observed-source-manifest caveat and read-time `source_changed`, independent expiry/locks and unknown applicability.
- After acceptance, compare native structural fingerprint, not merely technical revision, for legacy review state. Preserve immutable full allocation/history/UUID ACK; do not change dates/refs/minutes on GET, do not import old ticks, do not allocate a second Today workload, and do not infer numeric minima or waiver/edition proof.
- No new legacy schema/backfill/profile sentinel is needed for this protocol. G2 adds only its already designed current/history migration and ORM deletion relationships. Existing v1/v2 source remains read-only; a broader coordinated advisory-lock strategy would require a separate explicit legacy-writer allowlist expansion and real controls, not a hidden alternative.
- Current status: **transaction protocol proposed; implementation absent; C1–C11 NOT_RUN; native two-dialect concurrency NOT_QUALIFIED.** Before source adoption: terminal G1 release/new baton; fresh preimages; root decision on the delete companion/transaction-start boundary; ordinary source review; focused controls on both dialects including absent row; then the required native/full gates. No previous gate receipt is evidence for this new protocol.

## 8. Exact read pins

| File relative to checkout or stage | SHA-256 |
| --- | --- |
| Stage `ROOT_G2_INTEGRATION_DECISIONS.md` | `e9d51228d38316f650d057207fd933437600564e53007e4733b052b391d5cbf5` |
| Stage `proposals/g2-design/G2_IMPLEMENTATION_DEPENDENCY_MAP.md` | `47b21ed69e2ab087bae7d6d8820e316cba852e35d089f2d64db6876aa57a7210` |
| Stage `proposals/g2-design/SHARED_ROUTE_PERSISTENCE_SPEC_V2.md` | `27bc906301708c604c723e1a1d2fdb6ae79f454750871b4d6f82a98cd4728de3` |
| Stage `proposals/g2-design/TYPED_CONTRACT_DESIGN_V2.md` | `3916138d910830dfb0b484f2a562a488889798985f11ac2abdb2ffcd7282f37c` |
| `AGENTS.md` | `a28ea0f3c275f54e431169082e27aec5f156d048d30ad617c8a21d0021cc2f69` |
| `backend/app/db.py` | `e3fcdebae0e284e9a2ac7e1ef539c58054d4f12210d9683511b99dcb826bc319` |
| `backend/app/security.py` | `e8359112da7f35d7952049ed3e01066e0b6f41cd051052f5654ac740458bc816` |
| `backend/app/api/tenancy.py` | `34557c1bae4f9cc36413cfd952a001342df9a35a1c5ecf5ad19bd83cf121363f` |
| `backend/app/api/routes_preparation.py` | `11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2` |
| `backend/app/api/routes_profile.py` | `d9bd87d528f7c8545c3b6e1875d7924f09bb4bb2e63f5cf18db022e0fe0c235a` |
| `backend/app/models/applicant.py` | `54086f053fbf2db1b4a1471b9dac5595191f425ae2d6c6fe61d7744f1397caeb` |
| `backend/app/models/study_schedule.py` | `087ccef37010f3eeddce5329856832de1d4aeea796cba48a52e439cf0ca03626` |
| `backend/app/models/base.py` | `dfab71868df728ce3dc74d01f9d547512eb8076795207e113425a1eb1b786b62` |
| `backend/app/domain/learning_schedule.py` | `f5fb507796e5c7f6d4704ffff6f218fb8a59a35b79bf1fc659212544628e2e62` |
| `backend/migrations/versions/a9e5c14d2021_study_schedule.py` | `0502ab5e4660372dcb20cd79a2a14779cbc59086b7a363545cd2628ccb733c3d` |
| `backend/migrations/versions/b5c81d9e2022_learning_calendar.py` | `2c9e19365c4ca2835b48094191916667360fe2af94142148c36f60f9e921cad9` |
| `backend/tests/test_preparation_api.py` | `fde8e742aabc908f807937241f7480b9a1260e88faa9465045c874b258e79437` |
| `backend/tests/test_study_schedule_api.py` | `52204a8c5c897b3a327d1f74a6e8225a84614c89e519c31ef31a124650b7b194` |
| `backend/tests/test_learning_schedule_api.py` | `57261dcbf27f483dcf90616d9b646cbbd1997c4aa2709e599ba6d167a258f1f1` |
| `backend/tests/conftest.py` | `218c446f7edc6ec18c82407f24ed3fc40e179777351202602796b6c6049820d6` |
| `backend/requirements.txt` | `4d98978db7324e2a4529fdae5a51130375fb6e5417b2324d42a5b04d69601267` |

These pins locate the inspected seams; they are not a current Git/head, migration, import, test or deployment proof. Accepted typed v2's older G1 route hash is not reused as a current source pin here.

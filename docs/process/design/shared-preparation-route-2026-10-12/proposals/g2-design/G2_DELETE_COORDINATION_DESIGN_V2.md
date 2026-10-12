# G2 deletion coordination v2 — finite companion transaction design

**2026-10-12 · EXTERNAL DESIGN_ONLY · NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

This separate decision closes F1–F3 of `G2_CAS_INDEPENDENT_DESIGN_REVIEW.md` for the proposed G2 legacy CAS fence. The original `G2_LEGACY_CAS_TRANSACTION_DESIGN.md` and review remain unchanged. It authorizes no source change or deletion run. Scope is limited to the native `DELETE /api/profiles/{profile_id}` and `POST /api/auth/me/delete` transaction boundaries needed so a future G2 profile-parent lock does not invert their ORM child-deletion order. It does not serialize research/source writers, alter session authentication, reset a stopped workflow, or claim production concurrency proof.

## 1. Native facts that control the decision

- G2 proposes PostgreSQL `ApplicantProfileRow FOR UPDATE` before the legacy child lock, and SQLite `BEGIN IMMEDIATE` before guarded reads. The PostgreSQL parent lock is necessary for the first legacy child INSERT's immediate FK key-share conflict; changing it to a weaker profile lock would lose that absent-row fence (`G2_LEGACY_CAS_TRANSACTION_DESIGN.md` §§1–3).
- Native case deletion currently does an ordinary `owned_profile` SELECT, then run-ID SELECT, `session.delete(profile)`, an `AuditEvent` insert, and commit (`routes_profile.py:404–427`). ORM `ApplicantProfileRow` relationships delete runs, attempts and schedule children (`models/applicant.py:38–52`). A late parent lock after any child work is not a lock-order repair.
- Native account deletion validates password and `confirm_delete_data`, commits `account_deleted` audit rows, then in a second transaction marks User, each sole-owner profile, and each sole-owner Organization for deletion (`routes_account.py:352–433`). User has ORM delete-orphan memberships/sessions/social children (`models/auth.py:36–67`). The audit commit releases locks before actual erasure and can leave a false committed deletion record if the final transaction fails.
- `AuditEvent.organization_id` is an FK with `ON DELETE CASCADE` (`models/research.py:209–224`). A sequential SQLite fixture with FK enforcement off can retain an orphan audit row after org deletion; PostgreSQL and SQLite with FK enforcement on delete that organization-scoped row. Neither the current two-commit sequence nor this v2 promises a durable account-deletion audit after the organization is erased.
- Auth uses the same dependency Session, can autobegin with SELECTs, and may commit last-seen/session cleanup before returning a frozen principal (`security.py:191–239`, `db.py:169–175`). A later `session.in_transaction()` check does not establish a fresh deletion fence. Native `get_session` closes the Session but does not start `BEGIN IMMEDIATE`.

## 2. Common clean command boundary

Keep the existing native auth dependency and public route/status/response shapes. For each deletion command, after parsing input and receiving the frozen `Principal`, treat any early password/count/owner SELECT as **preflight only**. Before the first destructive/guarded SQL:

1. Verify the Session has no unexpected pending `new`, `dirty` or `deleted` ORM state. Fail closed on unexpected state; do not commit it or silently roll it back. Native auth's own accepted mutations must already have been committed by its dependency. Retain only primitive principal/route/payload values, not preflight ORM objects or snapshots.
2. Roll back only a clean read-only preflight transaction to release its snapshot/connection. Begin a fresh deletion transaction on the same request Session. SQLite's first SQL is explicit `BEGIN IMMEDIATE`; PostgreSQL starts a fresh transaction with real row locks. No nested `BEGIN`, savepoint-as-upgrade or stale identity-map value qualifies.
3. Recheck current authority and intended target **inside** the held boundary. For `delete_profile`, query exact `profile_id` plus `principal.organization_id` and keep generic 404 for missing/foreign. For `delete_account`, re-read/lock the current User, active state, password authority and relevant membership; a stale frozen principal alone cannot select another person's account. Do not invent a cookie/session-auth revalidation protocol here.
4. Commit only after the existing ORM cascades and audit insert have succeeded. A lock timeout, busy snapshot, FK/cascade failure, deadlock or lost connection gives full rollback/unknown outcome handling; never return 204 or clear the session cookie on an unconfirmed delete. No automatic new request, provider call or unsafe retry is implied.

This is a **new deletion-route boundary**. It does not change G2's accepted UUID replay rule or put `BEGIN IMMEDIATE` on GET/history/preview. A same-case G2 save and deletion order according to who obtained the fence; after successful deletion, a prior G2 UUID cannot resurrect the case and owner lookup remains 404.

## 3. PostgreSQL lock order and both deletion routes

**Chosen order:** account deletion locks **User → relevant Organization rows in exact ID order → membership rows used to classify ownership → ApplicantProfileRow parents in exact ID order → existing child/cascade work → commit**. Case deletion locks **own Organization → exact owned ApplicantProfileRow → child/cascade work → commit**. G2 retains **exact owned ApplicantProfileRow → legacy/G2 child → commit**. Account deletion uses strong `FOR UPDATE` on User/Organization/Profile rows; case deletion needs only `FOR KEY SHARE` on its Organization before `FOR UPDATE` on its Profile. The Organization key-share lock conflicts with account deletion's strong Organization lock and prevents its deletion, while remaining compatible with ordinary FK key-share references from other writers. This reduces, but does not prove absence of, inversions with research/audit writers. This is a finite coordination boundary for these routes, not a global ordering claim.

Account deletion details:

- After the clean boundary, lock `User` by frozen principal ID with `FOR UPDATE`, recheck that the user is active and the supplied password still verifies against the current hash. A cheap preflight password check may reject obviously wrong input before locks, but only the in-fence check authorizes erasure. Preserve wrong-password 400.
- Re-read current organization memberships. Lock each Organization in the user's **current membership set** in sorted ID order, not only the preliminary sole-owner subset: a shared-to-sole transition must not escape the classification boundary. Lock the membership rows needed to classify every such Organization in stable `(organization_id,user_id)` order. A strong Organization `FOR UPDATE` conflicts with new membership inserts' FK key-share; member-row locks prevent concurrent deletion/role changes of observed members. Recompute the sole-owner set and exact profile count after these locks. If membership or target set cannot be stably established, abort safely rather than erase a now-shared workspace. Only the resulting sole-owner organizations are deleted; shared ones remain.
- For every resulting sole-owner organization, lock all its `ApplicantProfileRow` parents in globally sorted exact profile-ID order, and re-read the set/count under the locks. Organization `FOR UPDATE` blocks new profile INSERTs through their FK; profile locks order G2 and ORM deletion. The held profile set, not a stale preflight count, supplies the existing `confirm_delete_data` decision and `profiles_removed` detail. Missing confirmation with held cases stays 409 and writes nothing. This makes the confirmation reflect the actual set about to be erased.
- **Before** `session.delete(user)` or any profile/organization delete marking, all parent locks must be held. Then perform native ORM cascades for the current User, only the selected sole-owner profiles, and their organizations. A profile that became missing is a conflict/abort, not an invitation to delete by a raw client ID. Preserve shared-organization cases and sibling users. A successful commit alone clears the cookie and returns 204.

Case deletion details:

- Lock the caller's current Organization `FOR KEY SHARE` first, then select/lock the exact owned profile `FOR UPDATE`, then count its runs, mark that profile deleted, insert the current `profile_deleted` audit event and commit. The organization lock matters: account deletion locks Organization `FOR UPDATE` before profile, and case deletion's audit INSERT references Organization. If case deletion locked Profile first and later requested an Organization FK key-share while account deletion held Organization and waited for Profile, a **new** inversion would remain. The Organization-first order removes that cycle for these two routes without taking a stronger Organization lock than needed. It does not certify arbitrary worker lock order.
- Do not use the native plain `owned_profile` before the locks in the final transaction and then trust that earlier object. Preserve generic 404 and `runs_removed` semantics. No profile no-op UPDATE, legacy placeholder row, changed study revision or profile `updated_at` is introduced.

G2 reads and writes no Organization row in this proposed fenced command; its in-process entitlement/source checks use bounded reads, not an Organization row lock or audit INSERT. If later G2 work acquires an Organization/User write or lock while holding Profile, this order must be reviewed again. Existing worker/research/member writers are **not** declared serialized by this contract.

## 4. SQLite boundary

SQLite has no useful row-level `FOR UPDATE`; use a fresh `BEGIN IMMEDIATE` as the first SQL of each deletion's guarded transaction, after clean auth/preflight rollback. Then re-read User/organization/memberships/profiles or exact case owner, run the current ORM cascades and audit, and commit once. Its writer reservation prevents a G2 write or native legacy/profile creation from committing across the protected deletion transaction. Normal contention is bounded by the configured busy timeout; a busy/snapshot failure is rolled back and surfaced safely, not upgraded from an old read transaction. A file-backed migrated SQLite control must record actual FK, WAL, busy-timeout and transaction behavior; test engines may not inherit production hooks.

## 5. Account audit in the same guarded erase transaction

**Chosen v2 change:** remove the separate pre-delete audit commit. After fresh password/ownership/confirmation checks and parent locks, add the existing `account_deleted` event for each sole-owner organization with its current `profiles_removed` count. Flush those inserts **while their Organizations still exist**, then mark User/profiles/organizations for ORM deletion and commit the audit plus erase atomically. On any failure, roll back both the audit and deletion; a failed guarded erase cannot leave a newly committed `account_deleted` assertion. This changes transaction placement, not the event's kind/actor/entity/detail, password rule, route response or scope of organizations erased.

Retention is dialect/FK-dependent, and the design must say so plainly:

| Database state | Successful sole-owner organization deletion | Failed deletion |
| --- | --- | --- |
| PostgreSQL, enforced `AuditEvent.organization_id ON DELETE CASCADE` | Organization-scoped `account_deleted` row is cascaded away; **no surviving audit row is promised**. | Whole transaction rolls back; no newly committed `account_deleted` row. |
| SQLite with `PRAGMA foreign_keys=ON` | The same FK cascade removes that audit row. | Whole transaction rolls back. |
| Existing SQLite-style fixture with FK enforcement off | ORM deletes User/Profile/Organization but has no AuditEvent ORM cascade, so the inserted audit row may survive as an orphan, matching the current sequential test's observed expectation. This is **not** PostgreSQL proof or desired universal semantics. | Whole transaction rolls back; no newly committed row. |

If the owner later requires a durable audit after an organization is deleted, that needs a separately reviewed noncascading audit store/identity policy and migration; the G2 lock fix must not fabricate retention by weakening privacy or foreign keys. For a surviving shared organization, native account deletion creates no `account_deleted` event for that organization under the current behavior; do not add one silently.

## 6. Finite controls for later implementation — all NOT_RUN

| Control | Required observation |
| --- | --- |
| D1 wrong password / missing confirmation | Native wrong password remains 400; case-bearing sole-owner deletion without `confirm_delete_data` remains 409. No delete, account audit, cookie clear, billing or research change. |
| D2 case delete, G2 first and delete first | Two physical PG connections and migrated file-backed SQLite; G2-first commits exact receipt then delete returns 204 and removes current/history/legacy/attempts; delete-first makes G2 owner recheck 404 and cannot reinsert. Profile audit detail, sibling case and generic foreign 404 stay native. |
| D3 account delete, G2 first and delete first | Real native account route with password+confirmation; record PG User→Org→membership→Profile lock sequence and waits, with no child-first deadlock. Successful deletion returns 204, clears cookie, subsequent auth is 401, sole-owner cases/G2 rows disappear, shared organizations/cases survive. G2 after deletion gets 404. |
| D4 account scope drift | Membership add/remove, profile creation, and a second case deletion straddling preflight/fence; guarded revalidation derives actual sole-owner set/count, never deletes newly shared data or omits a held own profile, and either commits correct scope or safely aborts without an audit event. Stable sorted multi-org/multi-profile locking avoids opposite-order waits. |
| D5 audit and rollback | Inject final ORM/FK failure after audit flush: no committed `account_deleted`, no partial erasure, no 204/cookie clear. On success explicitly inspect PostgreSQL and SQLite FK-on cascade versus FK-off fixture retained-row behavior; do not copy one dialect's audit assertion to another. |
| D6 auth/transaction start | Real authenticated dependency with both ordinary SELECT autobegin and last-seen commit; clean rollback only, then correct fresh PG lock/SQLite `BEGIN IMMEDIATE`. Deliberately dirty incoming Session fails closed. No nested BEGIN, busy-snapshot 500 or session-auth mutation. |
| D7 legacy/privacy preservation | Old v1/v2 PUT and exact receipt shapes unchanged; no profile no-op DML, legacy row placeholder, score/billing/quota mutation, owner-wide deletion, cross-case access, new research-writer guarantee or stopped security collector action. |

The existing sequential `test_account_flows.py:630–687` establishes 400/409/204/shared-workspace behavior on its fixture, not the two-connection lock order or PostgreSQL audit retention. Real native concurrency/migration gates and a fresh source write-ahead remain mandatory before adopting this design.

## 7. Pins and remaining limit

| Read-only artifact/source | SHA-256 |
| --- | --- |
| Original `G2_LEGACY_CAS_TRANSACTION_DESIGN.md` | `0fac39aa833050cba9819c4531707acb84eaf89577e61434d2d9995beab48f4f` |
| Independent `G2_CAS_INDEPENDENT_DESIGN_REVIEW.md` | `f9a33cf2293e274c7b3ff7520375e41a35550c06550ddbd683f5dc6ecc7f276f` |
| `backend/app/api/routes_account.py` | `e7ec09868bbe8c61b6ea97c05b65ca15f96843427bf09002af6bed36f4f4f1d9` |
| `backend/app/api/routes_profile.py` | `d9bd87d528f7c8545c3b6e1875d7924f09bb4bb2e63f5cf18db022e0fe0c235a` |
| `backend/app/models/auth.py` | `ab24284d515dbff52159818f32aa4d3b80863ab023b12cdc51bc2a9da9aa2004` |
| `backend/app/models/applicant.py` | `54086f053fbf2db1b4a1471b9dac5595191f425ae2d6c6fe61d7744f1397caeb` |
| `backend/app/models/research.py` | `03bc5f07438456d08e412ac2c0ed615464253a1a1bb9ecf3e548ff72d7aeef12` |
| `backend/app/security.py` | `e8359112da7f35d7952049ed3e01066e0b6f41cd051052f5654ac740458bc816` |
| `backend/app/db.py` | `e3fcdebae0e284e9a2ac7e1ef539c58054d4f12210d9683511b99dcb826bc319` |

The proposed coordination only orders these deletion routes with the future G2 profile/legacy fence. Independent research/claim/source/entitlement writers, concurrent membership policies outside the guarded routes and actual database deadlock behavior remain separate qualifications. No PASS, rollout, production privacy proof or all-writer serializability follows from this external document.

# G2 deletion coordination v2 — independent self-check receipt

**2026-10-12 · STATIC READ ONLY · DESIGN_ONLY / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

Checked `G2_DELETE_COORDINATION_DESIGN_V2.md` (SHA-256 `23b43feb144033ce0c7dc83e28012cbd5954a38784c7009648b50beef8b9874b`) against the preserved `G2_CAS_INDEPENDENT_DESIGN_REVIEW.md` F1–F3 and the ordinary native deletion/auth/model source. This is a review of proposed ordering, not transaction execution or a PASS. No application/Git/HANDOFF/helper/test/runtime/database/network/collector action occurred.

## F1–F3 closure check

| Prior finding | Design v2 status | Source-bound qualification |
| --- | --- | --- |
| F1 account deletion child-first versus G2 parent-first | **Addressed in protocol, not proven.** V2 adds the account route and requires User → sorted Organization → membership → sorted Profile parent locks before any `session.delete`. | Native account route currently has a separate audit commit and then marks User/profiles/orgs for deletion (`routes_account.py:399–429`); `User` and Profile ORM relationships cascade children (`models/auth.py:36–67`, `models/applicant.py:38–52`). Only real two-connection PG/SQLite controls can qualify the new order. |
| F2 case deletion fresh fence | **Addressed in protocol, not proven.** V2 starts a clean command transaction, SQLite `BEGIN IMMEDIATE` before reads, or PG Organization key-share then exact Profile update lock before run/child/audit work. | Current route reads owner and run IDs before ORM delete (`routes_profile.py:404–427`); auth dependency may have autobegun or committed last-seen (`security.py:191–239`). No implementation exists. |
| F3 false account audit across two commits | **Addressed for failure atomicity.** V2 inserts and flushes the existing event inside the final guarded transaction, before deleting its Organization; rollback erases both event and attempted deletion. | `AuditEvent.organization_id` has `ON DELETE CASCADE` (`models/research.py:209–224`). Success does **not** promise a retained event on PG or SQLite FK-on. SQLite FK-off test fixture can retain an orphan. |

## Concrete corrections/assumptions for root before source work

1. **In-flight 404 versus new-request 401 must be explicit.** V2 §2/§6 says a G2 call after account deletion gets owner 404. That is true for an **already authenticated in-flight** G2 call carrying a frozen `Principal` while it waits for the deletion fence; its fresh owned-profile probe then sees no case. A **new** call using the deleted account's cookie reaches `get_principal` first and should be 401 (`security.py:206–239`, `test_account_flows.py:657`). Split control D3 accordingly; do not weaken the auth dependency or claim every post-delete request is 404.
2. **Case deletion needs a current membership decision, not only a frozen org ID.** V2 §2 says “recheck current authority,” but its §3 case sequence names only Organization and exact Profile locks. `owned_profile` checks profile ID plus `principal.organization_id`; it does not verify that `principal.user_id` still belongs to that organization (`tenancy.py:12–24`). Since auth's membership check occurred before the clean rollback and a potentially long lock wait (`security.py:215–229`), the source proposal should re-read and hold the exact `(user_id, organization_id)` membership after the Organization key-share lock and before the Profile lock, or state and qualify a deliberate stale-principal window. Choose the missing-membership failure response explicitly while preserving generic 404 for foreign/missing profile IDs. The account route already calls for in-fence membership revalidation; the case route needs the same authority decision. This does not create a new session-auth mechanism.
3. **Assert PG isolation before claiming fresh post-wait revalidation.** V2 does not name a deletion-command PostgreSQL isolation level. `db.py:30–53` sets no override. A source stage should select/assert `READ COMMITTED` on the fresh transaction before its first SQL, as the parent CAS design does, or prove the chosen isolation's after-wait visibility. Do not assume the engine default or reuse a pre-lock identity-map object. SQLite requires evidence that `BEGIN IMMEDIATE` was actually the first guarded SQL after clean auth/preflight rollback.
4. **Membership/profile-set stability is conditional on physical locks and FK behavior.** Native memberships have a User FK and Organization FK with composite primary key (`models/auth.py:71–87`); profiles reference Organization (`models/applicant.py:24–34`). V2's strong Organization lock is intended to block new member/profile FK inserts, while locked member rows block observed removals and Profile parent locks order G2. The precise FK deferrability/enforcement, SQLAlchemy lock syntax (`FOR KEY SHARE` for case Org, `FOR UPDATE` for account Org/Profile), actual ORM flush ordering and dialect lock waits remain unverified. Keep the claim limited to the specified native routes, with forced membership-add/remove, case-create, G2-save and delete interleavings.
5. **Audit survival is fixture-dependent.** Native sequential `test_account_flows.py:630–656` expects one `account_deleted` row after Organization deletion. Its `auth_client` constructs a separate SQLite engine without the production `db.py` connect PRAGMA listener (`test_account_flows.py:25–64`), so that assertion does not establish enforced-FK behavior. V2 correctly says PG and SQLite FK-on cascade the organization-scoped audit away; SQLite FK-off may retain it. The same-transaction change fixes false committed events on failure, not durable retention on success. Root must decide if that existing cross-dialect inconsistency is acceptable in this bounded stage; do not change FK/privacy policy by inference.

## Exact static pins

| Artifact/source | SHA-256 |
| --- | --- |
| `G2_DELETE_COORDINATION_DESIGN_V2.md` | `23b43feb144033ce0c7dc83e28012cbd5954a38784c7009648b50beef8b9874b` |
| `G2_CAS_INDEPENDENT_DESIGN_REVIEW.md` | `f9a33cf2293e274c7b3ff7520375e41a35550c06550ddbd683f5dc6ecc7f276f` |
| `backend/app/api/routes_account.py` | `e7ec09868bbe8c61b6ea97c05b65ca15f96843427bf09002af6bed36f4f4f1d9` |
| `backend/app/api/routes_profile.py` | `d9bd87d528f7c8545c3b6e1875d7924f09bb4bb2e63f5cf18db022e0fe0c235a` |
| `backend/app/models/auth.py` | `ab24284d515dbff52159818f32aa4d3b80863ab023b12cdc51bc2a9da9aa2004` |
| `backend/app/models/applicant.py` | `54086f053fbf2db1b4a1471b9dac5595191f425ae2d6c6fe61d7744f1397caeb` |
| `backend/app/models/research.py` | `03bc5f07438456d08e412ac2c0ed615464253a1a1bb9ecf3e548ff72d7aeef12` |
| `backend/app/security.py` | `e8359112da7f35d7952049ed3e01066e0b6f41cd051052f5654ac740458bc816` |
| `backend/app/db.py` | `e3fcdebae0e284e9a2ac7e1ef539c58054d4f12210d9683511b99dcb826bc319` |
| `backend/tests/test_account_flows.py` | `429bbbce0a776dfcfff6fc93e7aee65c5f40080f77b9b1dab9278c679bb9b030` |

**Disposition:** V2 gives a finite design response to F1–F3. The three concrete source-stage decisions are in-flight/new-request status, exact in-fence case membership authority, and explicit PG isolation/physical-lock qualification; audit retention remains an acknowledged pre-existing dialect difference. No G2 code, deletion coordination, migration, concurrency proof, privacy gate or implementation PASS is established.

# G2 deletion coordination — root design decision

2026-10-12. **DESIGN_ACCEPTED / NOT_APPLIED / NOT_IMPORTED / NOT_RUN.**

Root read the complete original CAS design, independent review and separate deletion v2. This is a finite design decision for the later G2 implementation. The current source allowlist remains the three new schema/allocator/test files; neither deletion route is authorised for application editing yet.

Accepted artifact: `proposals/g2-design/G2_DELETE_COORDINATION_DESIGN_V2.md`, SHA-256 `23b43feb144033ce0c7dc83e28012cbd5954a38784c7009648b50beef8b9874b`. Independent finding artifact remains `G2_CAS_INDEPENDENT_DESIGN_REVIEW.md`, SHA-256 `f9a33cf2293e274c7b3ff7520375e41a35550c06550ddbd683f5dc6ecc7f276f`. Originals are preserved.

## Decision

The proposed strong profile parent fence must include both native case and sole-owner account deletion before a G2 concurrency/privacy claim. Root accepts the clean read-only auth/preflight rollback boundary, a fresh SQLite `BEGIN IMMEDIATE` as the first guarded SQL, and PostgreSQL parent locks before child work. Account order is User → sorted relevant Organizations → sorted observed memberships → sorted affected Profiles. Case order is own Organization key-share → exact owned Profile update lock. G2 retains Profile → legacy/G2 child, with bounded plain reads only and no later Organization/User lock or audit insert. These are reviewed constraints, not a proof about every worker or membership writer.

Root accepts moving the existing account audit insert/flush into the same final guarded erase transaction. Wrong password, actual held case count/confirmation, sole-owner/shared-workspace distinction, event payload, 204 and cookie clearing remain native. A rollback cannot commit a new false deletion event. Enforced organization FK cascade removes its organization-scoped account audit on success; the FK-off SQLite fixture may retain an orphan. No durable cross-dialect audit-retention claim is made, and no noncascading audit store is introduced.

Current User active/password authority and membership/target sets must be read under the new boundary; unexpected pending ORM state fails closed. No silent auth mutation is discarded. Missing/foreign case stays generic 404. If native membership/profile-set stability cannot be established under the proposed locks, abort with a bounded safe conflict; do not erase based on the preliminary count.

Root also read the separate self-check receipt (`G2_DELETE_COORDINATION_SELF_CHECK.md`, SHA-256 `932c78fd661f8790f2d44c7ffc993a9756f5003230779d41333cc8e1ad9635e2`) and fixes its three open inspection decisions before source: (a) an already authenticated in-flight G2 request which loses to deletion rechecks missing ownership and returns generic 404; a new request using a deleted account's cookie fails native auth with 401; (b) case deletion must read the current active User and exact `(principal.user_id, principal.organization_id)` membership inside its fresh Organization/Profile boundary, rejecting missing/inactive authority with native 401 before child work; these are plain reads, never a late User lock or a new token/session protocol, and independent membership writers remain outside the serialization claim; (c) the PostgreSQL commands require verified fresh READ COMMITTED and immediate nondeferred FKs before any revalidation claim.

## Before source adoption

1. A separate HANDOFF write-ahead must name the two deletion routes and actual finite concurrency tests, alongside the G2 integration files.
2. Real migrated file-backed SQLite and private Unix PostgreSQL must demonstrate both race orders, absent/present legacy row fencing, actual transaction/row-lock order, auth autobegin/last-seen boundaries, rollback after audit flush, shared-workspace preservation and no false 204/ACK.
3. Record actual PostgreSQL immediate FK and isolation, SQLite FK/WAL/busy behavior, physical connections and observed wait relationships. Sleeps, a same-session mock or an unchanged sequential fixture are insufficient.
4. Any G2 later Organization/User write-lock or new audit insert invalidates this reviewed order and requires another design review.

No stopped collector/reset/model/provider/search/expert evaluation is resumed. No main, production, user database, secret, workflow or setting change is authorised by this file.

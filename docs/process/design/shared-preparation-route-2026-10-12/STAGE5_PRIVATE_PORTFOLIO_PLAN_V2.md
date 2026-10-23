# Stage 5: private portfolio plan v2

**2026-10-12 · EXTERNAL DESIGN_ONLY / NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** This is a new version of the bounded future design. The [root original](STAGE5_PRIVATE_PORTFOLIO_PLAN.md) and [independent review](G5_PRIVATE_PORTFOLIO_DESIGN_REVIEW.md) remain byte exact. This document supplies no application/schema/test proposal, transaction proof, UI, migration, release or production privacy acceptance.

## 1. Decisions and actual authority

Root requested these exact corrections: compare the source fingerprint under a fresh strong Profile write fence; preserve the selected typed source observation in immutable private history/export; reject an entire new import when any evidence link is unsafe; keep the legacy profile unchanged; allow bounded personal create/edit after subscription expiry. A user may correct the profile explicitly or manually enter a new personal item. None of those actions grants research or paid learning access.

Native `owned_profile` is an **organization + case** boundary, not exclusive individual-user ownership ([tenancy.py](../../work/unimatch-calendar-materials/backend/app/api/tenancy.py:12)). Here “owned/private” means authorized through that existing workspace/case authority and never publicly/socially exposed. This stage does not invent a new counselor/member permission model. Missing/foreign case/item/event IDs retain generic 404 without existence disclosure. Current active User and exact membership are re-read inside new command boundaries using bounded plain reads; no new cookie/session protocol or late User lock is introduced. Independent membership writers are outside the lock-serialization claim.

Native [Activity/Achievement](../../work/unimatch-calendar-materials/backend/app/schemas/profile.py:189) arrays have at most 30 entries each and no stable per-entry ID. Their links are bounded ordinary strings; they need not be URLs. Native profile PUT replaces the whole payload and commits without a revision/CAS ([routes_profile.py](../../work/unimatch-calendar-materials/backend/app/api/routes_profile.py:105)). A new portfolio import therefore cannot trust only a preflight preview or an ORM value retained across a lock wait.

## 2. Finite personal records and provenance

The first increment is a private factual workspace for `activity`, `achievement` and manually entered `project` items. It has stable server item IDs, item revisions, entered title/role/text, optional dates/year/outcome/workload and at most five evidence-reference strings of at most 200 characters. Native text ceilings can be reused: 200 for title, 80 for short role/category, 2000 for description/outcome/impact. Proposed initial case ceiling is **60 current items** across all kinds, including explicitly imported and manual records; root must confirm that ceiling in the future source write-ahead. Immutable events are paginated rather than silently dropped when that current-item ceiling is reached. No retention duration is invented.

New fields are strict native types, finite and bounded. Missing facts remain missing. Imported Activity does not supply start/end dates; `duration_months`, `hours_per_week`, `weeks_per_year` or the `annual_hours` convenience property cannot establish calendar dates or a verified impact. Achievement retains its entered year/level/placement/criterion. There is no native Project source shape: a project is manual unless a later mapping is separately approved. Equal titles do not merge items.

All records remain `applicant_reported` / `not_independently_verified`. Entered responsibility such as `founder` is visibly the applicant's claim, never a verified label. Saving, having a URL or opening a page cannot authenticate an award, hours, rank, selection, certificate or impact. Subjective impact and a stated measurable outcome stay distinct. No admission probability, requirement verdict, official score, profile test, ranking, G1 cover edge or automatic recommendation is derived here.

## 3. Exact import source identity — F1 and F2

A new explicit import selects **one** current source observation per command: owned case ID, `array_kind=activity|achievement`, exact zero-based index, preview source fingerprint and selected semantic digest. Index is a locator within the observed ordered array, not a durable item identity. A duplicate name at another index is a different observation and may create a different stable portfolio item.

The versioned source fingerprint binds the exact case and the current **ordered raw activities/achievements arrays**, including presence of each array, their complete values and order. Canonical JSON sorts object keys, preserves array/string/numeric intent and rejects nonfinite/raw unsupported values before hashing; it does not hash only names, ignore reorder, trim links or use `updated_at` as a substitute. This is the portfolio source projection, not all unrelated profile fields. The selected semantic digest separately binds its bounded typed Activity/Achievement representation and source schema version. Validate raw finite values before native typing and typed Python values before JSON serialization; numeric-string coercion must not launder nonfinite values. An unparseable observation/source view is an explicit correction state, not an empty array or a trimmed import.

An accepted import event retains a **full bounded typed snapshot of that selected record**, with the exact original evidence strings, its source kind/index/fingerprint/semantic digest, schema version and server acceptance timestamp. It does not copy the full profile or the other 59 records. The typed selected snapshot is verified against the same raw source observation held under the command fence; URL validation must run on original strings before a coercive/stripping native model can alter them. If any link changes through normalization, reject rather than accept a rewritten source.

The first accepted event is the durable import-origin record. Later edits retain its immutable event ID/digest and produce new full accepted personal-item snapshots. They do not mutate the original source snapshot. After any profile reorder/edit/removal, current personal fields and the original imported source observation can still be distinguished in owned history and export. No profile write-back occurs. References without the selected snapshot are insufficient for this contract.

## 4. New-command transaction and replay — F1

Follow the fresh-command mechanics in [accepted G2 deletion coordination](ROOT_G2_DELETE_DESIGN_ACCEPTANCE.md) and [its finite design](proposals/g2-design/G2_DELETE_COORDINATION_DESIGN_V2.md). These are future dependencies, currently not implementation proof.

1. Parse the strict command and canonical request digest. Bind case, operation, edit item ID/expected revision or import source kind/index/fingerprint/digest, entered personal fields and the client's original write UUID. No server acceptance time or mutable source value is silently added to request intent.
2. Owner check precedes own `(profile_id, client_write_uuid)` lookup. An already accepted equal request returns its **exact immutable receipt** before current source, item revision, subscription or link checks; same UUID with changed intent is 409. An accepted UUID is not authority for a foreign/deleted case.
3. For a still-new command, inspect the incoming Session for unexpected pending `new/dirty/deleted` state and fail closed if present. Native auth's accepted mutations must already be committed. Roll back only clean read-only preflight state, release its snapshot and retain primitive principal/request values. Do not discard dirty auth work, nest a BEGIN or use a savepoint as a SQLite snapshot upgrade.
4. **SQLite:** first guarded SQL in the fresh command is `BEGIN IMMEDIATE`, before owner/history/source reads. **PostgreSQL:** explicitly assert/select fresh `READ COMMITTED`, then lock exactly `ApplicantProfileRow.id + principal.organization_id FOR UPDATE`. No weak parent lock, no-op UPDATE, profile timestamp touch or placeholder is allowed.
5. Re-read current authority and accepted UUID after acquiring the fence. A delivery that became accepted while waiting takes the replay path **first**. For a still-new import, read fresh scalar source payload in a new statement or with `populate_existing`; do not reuse the earlier identity-map object. Recompute the exact full source fingerprint, reselect that index and recompute the selected typed digest under the held Profile lock. Any mismatch is typed 409 `profile_source_changed`; no item/current/event is created.
6. Validate original evidence strings, source shape and the item/collection ceiling; for edits compare the actual item revision. Write only the new portfolio current state and matching immutable event, then commit **once**. Do not flush unrelated Profile mutations. Unique own UUID plus per-item revision CAS remain necessary even when the parent lock orders writes. A failed event insert rolls back the current item update.
7. On conflict/busy/deadlock/timeout, roll back the entire transaction. Reconcile owner plus original UUID in a fresh read if available; accepted same request returns its exact old ACK. Otherwise retain the original input/UUID and report conflict or unknown outcome without a new automatic intent. A lost commit connection is not proof that nothing was accepted.

**Legacy PUT remains unchanged.** If it commits before import wins the fence, the new fingerprint is read and a stale preview rejects. If import holds the strong fence first, legacy UPDATE waits and is ordered after the accepted import; the stored selected snapshot remains the valid observation at acceptance. This design does not add CAS to legacy PUT, prevent later profile changes or claim all writers are globally serialized. Real physical two-connection controls remain mandatory.

## 5. Lock order with case/account deletion

New portfolio commands use **Profile FOR UPDATE → portfolio current/event children → commit**, as G2 does. They may perform bounded plain User/Organization/membership reads, but acquire **no later User/Organization/membership write locks**, insert no Organization-scoped AuditEvent and perform no research/billing/source writer work while holding Profile.

Portfolio current/event rows have immediate case/Profile FKs. A stored actor identifier is opaque receipt metadata, **not a new User FK** that would request a late User key-share lock. Tenant/case body identifiers must match the authoritative case; adding another Organization FK or an org audit insert is outside this reviewed shape. If such a dependency is later needed, root must review an Organization-first command order before source; it cannot be added after a Profile lock silently.

This fits the accepted deletion order: account User → sorted Organizations → observed memberships → sorted Profile parents → children; case own Organization key-share → Profile update lock → children. The portfolio command neither waits for a late Organization/User lock nor creates a child-first cycle. SQLite's fresh immediate writer reservation is the equivalent coordination boundary. Actual FK enforcement, isolation, ORM flush order and waits still need PG/SQLite evidence; no general deadlock-freedom claim follows.

Portfolio events/current must be added to both case FK cascade and explicit `ApplicantProfileRow` ORM delete-orphan relationships, independent of SQLite FK-off fixture behavior. Profile-first portfolio wins → accepts exact receipt, then successful deletion erases it; delete-first → in-flight owner recheck returns generic 404 and cannot resurrect the case. A new request after account deletion fails native auth with 401. Account deletion removes sole-owner cases and leaves shared-workspace cases intact. Accepted G2 audit rollback/retention rules remain unchanged; Stage 5 invents no durable deletion audit.

## 6. Evidence URL admission — F3

**Chosen import behavior: any invalid/unsafe evidence string rejects the entire new import.** No current item or accepted event is written; no link is stripped, shortened, decoded, scheme-converted, dropped or silently made non-actionable to rescue the command. The unchanged legacy profile retains its original input. The visible correction reason identifies source kind/index and evidence-link ordinal plus a safe reason code, without echoing a credential/token URL into generic logs. The applicant may explicitly correct the profile and obtain a new preview, or manually enter an item with different chosen evidence. An accepted prior UUID replay does not rerun this gate against a changed profile.

Native public network policy is available, but its entry points are not all pure:

- [network_policy.py:22](../../work/unimatch-calendar-materials/backend/app/adapters/network_policy.py:22) provides scheme/port constants; [is_blocked_address:79](../../work/unimatch-calendar-materials/backend/app/adapters/network_policy.py:79) is a pure literal-address rejection function, including private/loopback/link-local/metadata/reserved and extra blocked ranges.
- [resolve_target:108](../../work/unimatch-calendar-materials/backend/app/adapters/network_policy.py:108), `check_url` and `is_allowed` call DNS for hostnames through `socket.getaddrinfo` ([line 148](../../work/unimatch-calendar-materials/backend/app/adapters/network_policy.py:148)). They cannot be called and presented as an offline validator. A fake resolver/public address would be false DNS proof.

The first private increment uses **offline evidence-reference admission only**, at the API boundary, reusing native pure address checks/constants without making `domain/private_portfolio.py` import an adapter or perform I/O. A later source proposal must show the exact helper seam rather than weaken or clone the crawler's active egress guard. No DNS, HTTP, redirects, browser, URL preview, metadata fetch or background fetch occurs on preview/create/edit/import/read/export.

Exact conservative input rules for that future admission helper:

| Input | Decision for the new whole command |
| --- | --- |
| Native string, 1–200 characters, absolute `http` or `https`, syntactically valid host/port | Candidate only; preserve the exact stored string. |
| Leading/trailing whitespace, control characters, backslash, malformed authority/port/bracket syntax, percent-encoded authority or ambiguous noncanonical literal-IP spelling | Reject `url_shape_invalid`; never repair parser/browser differences. |
| Username/password, including empty credential markers | Reject `url_credentials`. |
| Query or fragment delimiters, even an empty query/fragment | Reject `url_query_or_fragment`; no token-name allowlist or automatic removal. |
| Known native blocked hostname; single-label/internal host; reserved local/test/invalid/internal suffix; literal IP rejected by native `is_blocked_address` | Reject `url_non_public_destination`. |
| Unsupported scheme/port; inline/data/file/javascript/fixture reference | Reject `url_scheme_or_port`. Use native public scheme/port limits, not a looser portfolio rule. |
| Known login/private-document/session/signed-share destination or applicant cannot explicitly confirm the reference is public and contains no private access token | Reject `url_private_reference` / `public_reference_unconfirmed`. Manual entry does not bypass these gates. |
| Ordinary hostname with accepted syntax and explicit applicant public-reference confirmation | Store as `applicant_reported_public_reference`; DNS/reachability/permissions/truth remain `not_checked`. |

Hostname comparisons may lowercase ASCII/IDNA for validation, but cannot rewrite the saved URL. Unicode authority requires the applicant to explicitly supply its ASCII IDNA spelling; the importer does not silently convert it. Link array length/order and duplicates remain the selected source snapshot's original values; do not sort/deduplicate links. Confirmation is a personal reference assertion, not legal consent, verification, permission to fetch or a premium grant.

**Conservative limit:** static parsing cannot establish whether an arbitrary hostname resolves privately, whether an opaque path contains an access capability, or whether a syntactically public document requires login. This design therefore does not label stored hostnames `verified_public`, promise DNS safety/reachability or make URLs evidence of truth. Suspected/private references are refused with correction guidance. Any future server fetch would require a separate authorized Fetcher/native DNS+pin/redirect policy stage outside this task; no such feature is proposed here. This limit must remain visible when the future UI is designed.

## 7. Exact immutable event/history/export

The future owned accepted event contains: versioned event schema, stable event/item/case IDs, item revision, operation, original client write UUID, canonical request digest, accepted full bounded personal item snapshot, origin kind, import-origin event reference and its selected typed source snapshot/fingerprint/index/digest when applicable, server UTC acceptance timestamp and bounded opaque actor identity. It excludes another case, full profile copy, source claims/premium evidence, credentials, attachment bytes or verified-achievement assertion.

Unique `(profile_id, client_write_uuid)` enforces accepted command identity across create/edit/import; equal replay returns that event's persisted exact ACK, never a view rebuilt from current profile. Later item edits append events; old snapshots/timestamps/digests never change. Current/history reads do not auto-import, auto-create rows, revalidate into a different accepted item or copy dynamic premium fields. Malformed stored events fail closed as explicit unavailable/correction state rather than being reconstructed from a mutable profile index.

Owned history is cursor-paginated with stable accepted-time/event-ID order. Own complete profile export must add current portfolio items and **all retained accepted events**, including original selected source snapshots, independent of subscription. Paging/streaming may bound memory but cannot silently truncate or rename a summary “complete record.” The native existing export contract at [routes_profile.py:269](../../work/unimatch-calendar-materials/backend/app/api/routes_profile.py:269) stays unchanged outside these additive fields. Case/account erase removes current and immutable history with sibling/foreign preservation; immutability does not override an authorized privacy deletion.

## 8. Subscription and scope boundary

Root's policy is explicit: **new bounded private create, edit and explicit profile import remain available after subscription expiry**, as do private current/history/replay/export/delete. Existing authentication/case authority and all strictness/CAS/link/limit guards still apply. No learning-access gate is borrowed; no subscription row, preparation term, research entitlement/unit, attempt, score or payment is modified. Existing paid learning and premium research remain governed by their own routes.

There is no public sharing, SocialProfile/post/message integration, UI implementation, PDF/CV/essay generation, review credential, attachment upload/storage, private document/portal access, AI feedback, provider call or outbound applicant data in this design task. Exact source paths, migration and controls require a later HANDOFF write-ahead. The future backend seam may use `schemas/domain/models/api private_portfolio`, additive Profile ORM/export wiring and one migration; it is not authorized by this file. A private screen/localization/native acceptance comes later, not from a design-only document.

## 9. Future finite acceptance controls — all NOT_RUN

| Control | Required actual observation before implementation qualification |
| --- | --- |
| P1 same UUID / conflict / expiry | Same UUID+same digest returns identical persisted event/ACK after profile reorder, item edit or subscription expiry; changed intent returns 409; owner check precedes UUID. One immutable event, no new mutation or premium/quota grant. |
| P2 profile wins import race | Two physical migrated PG connections/file-backed SQLite Sessions; native legacy profile PUT commits changed/reordered arrays before importer fence; fresh source comparison returns typed 409 and creates zero current/event rows. Record real source re-read and lock/BEGIN order. |
| P3 import wins profile race | Import holds strong Profile fence, native PUT's actual UPDATE waits; exact held typed snapshot/event commits once, later PUT succeeds unchanged, owned history/export still shows original snapshot. No invented CAS guarantee for legacy PUT. |
| P4 transaction boundaries | Actual auth SELECT autobegin and last-seen commit variants; clean rollback then SQLite first `BEGIN IMMEDIATE` / verified PG READ COMMITTED+FOR UPDATE; deliberately dirty Session fails closed. No nested BEGIN or stale identity-map read qualifies. |
| P5 source snapshots / duplicates | Two equal names at different indexes stay distinct; source array change/reorder invalidates an unaccepted preview; accepted selected typed snapshot survives source removal and later portfolio edits; no profile/write-back/score/source verdict changes. |
| P6 whole-command link refusal | A valid native Activity/Achievement with one unsafe link among safe links rejects preview/new import and produces zero rows/events, safe visible ordinal/reason, original profile/string/list unchanged. No strip/convert/drop/dedup; manual unsafe create/edit also rejects. Cover credentials, query/fragment, private literal IP/metadata, malformed port/authority, path ambiguity, private/unconfirmed reference and valid asserted-but-unchecked hostname. Instrument no DNS/fetch/browser calls. |
| P7 strict finite facts | Native strings/ints/dates/bools, raw nested NaN/±Inf and numeric strings producing typed nonfinite values, missing dates/outcomes, unsupported source shape; no measured hours/date/impact inferred. No clipping silently changes an accepted record. |
| P8 current/event atomicity | Real separate-session same-item CAS winner/loser, different UUID same revision, duplicate accepted UUID; event failure after current change rolls back both; lost ACK reconciles original UUID. No half update or reconstructed replay. |
| P9 deletion coordination | Both portfolio-versus-case/account delete orders on PG/SQLite; exact accepted G2 parent order with no late Org/User locks/FKs/audit; generic in-flight 404 and new-auth 401; ORM/FK-on and FK-off behavior; current/history erased only for intended sole-owner cases, sibling/shared/foreign preserved. No resurrection/false 204. |
| P10 complete own export | Current and complete immutable history/source observations match persisted accepted fields/IDs/digests after edits/profile reorder and expiry; no foreign event/whole profile duplication and no silent truncation. Source immutability yields to authorized case erase. |
| P11 scope conservation | Public social routes cannot expose private records; premium/learning/billing/research/attempt/profile payload+updated_at remain unchanged after portfolio commands and failures. Later UI/network/production gates explicitly remain NOT_RUN. |

No test source or runtime was created here. In-memory/same-session mocks, sequential legacy tests or old G1/G2 receipts cannot prove these new transaction/link/export/privacy requirements.

## 10. F1–F3 disposition and unresolved facts

| Peer finding | V2 response | Status |
| --- | --- | --- |
| F1 source fence versus legacy PUT | Fresh strong Profile transaction, source re-read under fence, accepted UUID first, both serialized race orders explicitly defined. | Addressed in design; physical concurrency NOT_RUN. |
| F2 source index cannot reconstruct history | Full bounded selected typed source snapshot in accepted import origin/event, retained across edits and complete own export. | Addressed in design; persistence/export NOT_IMPLEMENTED. |
| F3 legacy links can violate new contract | Whole new import refusal with safe visible reason, no profile mutation or silent sanitization/fetch; exact offline policy and unresolved DNS/truth limits stated. | Addressed in design; URL helper and controls NOT_IMPLEMENTED. |

Operator identity, actual hosting/storage subprocessors, region, minors/consent, legal basis, retention, real evidence-link policy review and production deletion/backup facts remain pending. This plan neither fabricates human signoff nor upgrades draft legal pages to published facts. Portfolio history policy is a proposed current-system behavior, not a claim that backups/external copies have been erased or that any statutory retention rule is satisfied. Overall platform/search/course/product release remains unfinished; stopped workflows are unchanged.

## 11. Full read-only pins at this design seal

No application module was imported or executed. These exact ordinary source/artifact bytes were read and hashed. The adjacent [seal](STAGE5_PRIVATE_PORTFOLIO_PLAN_V2.SEAL.json) records this file's SHA, all inputs and the NOT_APPLIED/NOT_IMPORTED/NOT_RUN boundary.

| Native source | SHA-256 |
| --- | --- |
| `backend/app/schemas/profile.py` | `b15ba3a8b4ee3519cee207caf2eb8504f22e1cb4b1039436ba4ce792850beff1` |
| `backend/app/api/routes_profile.py` | `d9bd87d528f7c8545c3b6e1875d7924f09bb4bb2e63f5cf18db022e0fe0c235a` |
| `backend/app/api/tenancy.py` | `34557c1bae4f9cc36413cfd952a001342df9a35a1c5ecf5ad19bd83cf121363f` |
| `backend/app/models/applicant.py` | `54086f053fbf2db1b4a1471b9dac5595191f425ae2d6c6fe61d7744f1397caeb` |
| `backend/app/adapters/network_policy.py` | `221d53b18aac4c11388a589204817a29eb6e0c705f50724bda3b3e10e8c80f8f` |
| `backend/app/api/routes_account.py` | `e7ec09868bbe8c61b6ea97c05b65ca15f96843427bf09002af6bed36f4f4f1d9` |
| `backend/app/models/auth.py` | `ab24284d515dbff52159818f32aa4d3b80863ab023b12cdc51bc2a9da9aa2004` |
| `backend/app/models/research.py` | `03bc5f07438456d08e412ac2c0ed615464253a1a1bb9ecf3e548ff72d7aeef12` |
| `backend/app/security.py` | `e8359112da7f35d7952049ed3e01066e0b6f41cd051052f5654ac740458bc816` |
| `backend/app/db.py` | `e3fcdebae0e284e9a2ac7e1ef539c58054d4f12210d9683511b99dcb826bc319` |
| `backend/app/models/base.py` | `dfab71868df728ce3dc74d01f9d547512eb8076795207e113425a1eb1b786b62` |

| Preserved design/review input | SHA-256 |
| --- | --- |
| `STAGE5_PRIVATE_PORTFOLIO_PLAN.md` | `6df8f5b870d87bcb32b0f63d45b77277686cf759ee5adddd862985561c407906` |
| `G5_PRIVATE_PORTFOLIO_DESIGN_REVIEW.md` | `abc32b5680661dca8dad8e60073e1382d082c5eddab08230f641d9749fef9fa3` |
| `ROOT_G2_DELETE_DESIGN_ACCEPTANCE.md` | `f56730f3a28d81f3344cbb6fd40552b7fafc101abc8fcf65adaa0db7f6a1a287` |
| `ROOT_G2_INTEGRATION_DECISIONS.md` | `e9d51228d38316f650d057207fd933437600564e53007e4733b052b391d5cbf5` |
| `proposals/g2-design/G2_DELETE_COORDINATION_DESIGN_V2.md` | `23b43feb144033ce0c7dc83e28012cbd5954a38784c7009648b50beef8b9874b` |
| `proposals/g2-design/G2_DELETE_COORDINATION_SELF_CHECK.md` | `932c78fd661f8790f2d44c7ffc993a9756f5003230779d41333cc8e1ad9635e2` |
| `proposals/g2-design/SHARED_ROUTE_PERSISTENCE_SPEC_V2.md` | `27bc906301708c604c723e1a1d2fdb6ae79f454750871b4d6f82a98cd4728de3` |

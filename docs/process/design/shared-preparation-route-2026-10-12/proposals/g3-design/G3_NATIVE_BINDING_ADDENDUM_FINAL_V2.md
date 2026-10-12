# G3 native binding addendum — final v2

2026-10-12 · **SEALED EXTERNAL DESIGN_ONLY / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

This is a finite clarification of accepted `G3_CONTRACT_DESIGN_V2.md` and `G3_IMPLEMENTATION_DEPENDENCY_MAP.md`. Those files and all G2 packets remain unchanged. Root is the sole application/source/Git/HANDOFF/runtime writer. G3 implementation is **NOT_AUTHORIZED until G2 release and a new bounded root source write-ahead**. No import, test, database/runtime operation, network request, provider call or source edit supports this document; the controls below are proposed future controls, not PASS results.

Source root: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`. Paths below are relative to it. This addendum grants no new course, crawler, calendar allocator, quota, official score, admissions readiness, portal verification or URL-reachability claim.

## Final-v2 delta — raw source URL is proof identity

This separate final-v2 closes the finite clarification in `G3_NATIVE_BINDING_INDEPENDENT_REVIEW.md` (SHA-256 `5c53608b06923f528af469d977e2b6f127aa1d2c9da98935c44b8ec672ec6605`). The prior sealed addendum (SHA-256 `d38e1fa08697f866a22ebf59a20046608eddc79865286874851f79542840a72c`), its receipt, accepted V2, dependency map, peer review and all inherited native source pins remain unchanged. This file supersedes only the proof/reference field-list ambiguity: the raw recorded `DocumentItem.source_url`, including no recorded URL versus a present exact recorded string, participates in proof identity. Item semantics still excludes it. No URL fetch, resolution, redirect, portal verification or new source applicability is implied. The remaining selector, cap, Today and ownership contracts are unchanged.

## 1. Contradictions resolved by root before sealing

| Earlier ambiguity or actual boundary | Root design decision recorded in this addendum |
| --- | --- |
| Map §2 left pinned G2 revision versus following a head open; V2 §9 requires frozen accepted slots. | The selector policy is explicitly `follow_current_accepted` for **g2, legacy_v2 and legacy_v1**. G2 receipts stay immutable; saved v2 dates/refs stay frozen until an explicit native save. Legacy v1 remains its native mutable settings/current projection, with no invented legacy history. The selector ACK records its immutable original observation; Today reads the currently accepted head of the chosen origin and labels its later revision. G2/v2 are never reallocated on GET; native v1 projection behavior is preserved. |
| A corrupt G2 pointer could otherwise look absent and activate legacy. | With no stored G3 selection, owned G2 current **or** accepted-history metadata establishes derived g2, including an unreadable/missing pointer. Explicit sidecar presence establishes legacy_v2 next; a saved legacy row establishes legacy_v1 next; no saved rows establishes none. Corruption/unavailability never authorizes fallback. |
| “Reject a new binding at20” could prohibit another task for an already counted programme, or disappearance could free capacity. | Count the union of **current ApplicationRecord target IDs, including withdrawn/disappeared targets**, and **current case-personal source-binding result IDs**. A task/binding to an already counted ID remains allowed at20; adding a distinct21st ID is rejected atomically. History outside that union is not current-evaluated. |
| Selecting a saved plan could accidentally become a new-practice entitlement check. | Selection is an own personal-planning command, available after preparation expiry or research lock. A new selection still requires a valid own persisted native plan. Existing selection survives plan failure as selected/unavailable. No clear/none command is added. |
| G3's20 targets do not bound the independent20 goals saved in G2; a public G2 read already evaluates its own source roles. | Keep separate native bounds: G3 current-source target union≤20 and selected native G2 goals≤20; composite Today references≤40 distinct result IDs. Do not claim20 SQL queries or one atomic observation. Each role stays bounded; no private G2 loader refactor or fake deduplication claim. The final metadata/token recheck is one bounded pass across both sets≤40. |

These decisions clarify only the named seams. G3 V2 personal/source authority, declaration provenance, privacy, history, CAS, import, erasure and uncertainty rules remain in force. None of the design decisions is an integration or release receipt.

## 2. One durable selector command

Add only the finite `select_active_preparation` command kind to the future versioned G3 command union. It carries the existing typed `client_write_uuid`, exact `expected_revision` of the **G3 current aggregate**, chosen origin `g2 | legacy_v2 | legacy_v1`, literal policy `follow_current_accepted`, and an **observed native head identity** from an own read. Neither a lesson array nor an allocation/settings body is accepted as the selection target. `none` is only the derived no-saved-plan read state; it is not a new command.

Canonical request identity includes the command kind, original typed UUID, expected G3 revision, origin, policy and all observed-head tokens. Preserve that exact UUID/body after a lost response. A reviewed changed intent uses a new UUID. A selected native revision is a different field from expected G3 revision; never use one as the other's CAS value.

### Observed native head identity

The stable identity is own `profile_id + origin + native schema/version`, with the following exact reference tokens. Native row IDs need not be exposed; own profile+origin identifies the native singleton. Do not fabricate a native acceptance UUID for legacy writes, which have none.

| Origin | Observation stored in immutable selection ACK | Today head and display behavior |
| --- | --- | --- |
| g2 | Native accepted `SharedRouteWriteReceiptV1.revision`, `client_write_uuid`, `snapshot_digest`, `allocation_digest`, accepted time and native schema version. | Read the current accepted native head, validate its current/history binding, and retain its full saved slot array/order/refs/minutes. Show original selection-observed revision separately from the newly observed accepted revision. Do not load all revision history. |
| legacy_v2 | Own `StudyScheduleRow.revision`, canonical **persisted typed sidecar** digest, `draft.fingerprint`, saved `legacy_fingerprint`, and currently observed native structural settings fingerprint. | Read the current saved sidecar and exact dated refs. Its technical row revision can change because the same row also serves v1. Preserve saved sidecar dates/refs; native `needs_review` and availability remain separate. A digest of refreshed GET metadata is not the persisted sidecar digest. |
| legacy_v1 | Own `StudyScheduleRow.revision`, full typed saved-settings digest, and unchanged native `settings_fingerprint` that excludes self-ticks. | Use native `read_schedule` current projection with original IDs and self-ticks. Its projection can depend on today. A tick may advance technical revision/full settings digest without changing structural fingerprint; this is not a new official requirement or immutable G2 allocation. |

New reference digests use a versioned finite-JSON canonical form over validated native persisted values: deterministic object keys, unchanged array order and scope omission, no NaN/infinity or stringification of malformed objects. They are own plan-reference identities, not current official-source digests. Native G2 digests and `settings_fingerprint` are used exactly, not redefined. Neither raw settings nor sidecar/allocation content is duplicated in G3 immutable selector ACK.

### Acceptance/replay protocol

1. Fresh transaction and current owned case/actor fence, following the accepted G3 V2 protocol and released native `preparation_transactions.py` boundary. Its profile/existing-child locks serialize competing native writes without a parent timestamp update or placeholder legacy row.
2. Own accepted UUID lookup precedes mutable plan, source or entitlement checks. Equal canonical intent returns the identical saved200 ACK, including the original native observation, even after the plan advances/disappears or access expires. Changed intent409; no dynamic Today/current-source fields enter replay.
3. For a new command, compare exact expected G3 revision. Read and validate the own persisted chosen native head and compare the requested observation tokens. An intervening accepted native head requires review/conflict; do not silently accept a different plan than the reviewed target. No source entitlement or preparation-term requirement is added merely for selection.
4. Missing chosen plan cannot create a blank plan. Preserve native unreadable503/legacy malformed422 semantics where applicable; a finite new-selection validation error leaves the existing G3 choice untouched. An application implementation must freeze the exact safe error mapping before source sealing, without premium error details.
5. Atomically persist one G3 current revision/event and immutable reference-only ACK, including selector origin/policy and observed tokens, resulting G3 head identity and existing V2 request/receipt links. Event failure rolls back the current mutation. A CAS/unique loser rolls back completely, then rereads owned UUID in a fresh transaction for identical replay/conflict/ordinary revision loss.

The selector never saves G2, changes legacy settings/ticks, allocates work or submits an attempt. Explicit return to legacy uses this same versioned command and a valid saved `legacy_v1` or `legacy_v2` target. Saving a newer G2 head **never rewrites an existing G3 selector/event**: a g2 selector naturally follows it; a legacy selector keeps the chosen legacy origin. No migration/backfill infers a selector.

## 3. Today follows one chosen native origin

First observe a valid own G3 current aggregate. A stored selector wins. If that aggregate is unreadable, report an unavailable G3 component; do not treat it as no selector and derive a replacement. Only a genuinely absent stored selection permits the read-only backward default:

1. Owned G2 current or accepted-history presence ⇒derived g2. Validate/read the current head; missing pointer or corruption ⇒g2/unavailable, never legacy.
2. Otherwise, an explicitly present persisted v2 sidecar marker ⇒derived legacy_v2. Presence is non-null storage identity, not truthiness of a parsed object; a malformed/empty recorded object remains selected/unavailable.
3. Otherwise, own saved v1 row ⇒derived legacy_v1; malformed settings remain selected/unavailable.
4. No saved rows ⇒derived none. No fabricated workload, dates or allocation.

Use a bounded owned metadata query for presence/current-head tokens, including a scalar G2 accepted-history maximum rather than deserializing/exporting history. A database/metadata failure is unavailable/unknown, not proven absence. Read the chosen native public in-process route using explicit session/principal/profile arguments; no HTTP self-call or second Session. Do not refactor or privately reuse the G2 loader. A narrow new own persisted-reference adapter may observe raw sidecar identity without changing native route bodies; reconcile its token with the native read in the one recheck.

No stored selection has been accepted in the derived case: label `selection_source=derived_backward_default`, do not manufacture a selection event/revision/accepted time. A stored selection is `selection_source=accepted_g3_event` and includes the exact immutable selection receipt reference. Derived origin can change only when another writer explicitly saves a native plan; show the next observation/revision, never a GET write. A G2 save is its existing explicit opt-in; mere preview/browser draft does not establish G2 presence.

For a stored selector, include both **selection-observed head** and **current-observed head**. The selected origin and policy do not change on a read. New native head content is used only as that already accepted head, with its own native self-report/completion semantics. Do not transfer an old origin/head's ticks into other slot identities or infer compatibility. Selected missing/unreadable/stale content retains origin and safe availability/review state. Personal applications/tasks remain independently readable. Returning to a different origin requires an explicit selector command.

Native G2 own accepted reference-only receipt is distinguished from current research verification. Existing accepted receipt/baseline references remain readable under their native contract; current premium evidence and newly observed source manifests require current research authorization. A new accepted-plan digest is not evidence that its official requirements are current. Preparation permission separately controls new lesson/attempt/schedule actions; own review remains readable after expiry.

After component reads, perform at most one bounded scalar/token recheck of G3 head, chosen origin/head and relevant owned target/access tokens. If changed, mark `mixed_revision/needs_refresh`, keep independently safe own receipts and withhold contradictory joined next actions. No loop, fresh G2/v2 allocation, alternate plan, falsely atomic snapshot or zero workload assertion on failure. Native v1's existing today-based read projection is preserved. No second document/practice minute ledger is added: documents remain `unallocated/not_estimated`.

## 4. Raw checklist occurrence and proof binding

The source input is the authoritative, validated native `DocumentChecklist`: six **ordered** lists (`admission_documents`, `scholarship_documents`, `applicant_actions`, `school_actions`, `recommender_actions`, `certification_actions`), original duplicate items, `ordered_steps`, unresolved/completeness, result/university/program identity and deliberately omitted unrecorded scope. Native column/payload disagreement, malformed/nonfinite content or wrong identity is unknown/error; never normalize it to an empty successful checklist. `generated_at` alone is excluded from content identity.

Each bound raw occurrence retains `result_id + exact list name + zero-based original index + full item/reference digest`. The index refers to the accepted original ordered list, not to a displayed filtered/sorted name list. Stable G3 task IDs are independent of that source identity. A task bound to a unique cross-list owner projection retains **all** accepted original occurrence refs. Same-list duplicates stay separate; name/actor/purpose alone cannot choose an occurrence.

Maintain separate versioned identities:

- Full checklist/reference digest: all validated native fields except `generated_at`; ordering, duplicates, proof links, scope omission and procedure/unresolved/completeness remain.
- Item semantics digest: all original native item constraints except `claim_ids` and `source_url`. Preserve name, actor/purpose/required, prompt/limits, dependency order, date/timezone, scope omission and all other constraints. This is a comparison identity, not document validity.
- Proof/reference digest: original declared claim IDs, **raw recorded `DocumentItem.source_url` with explicit absent/present state and exact present string**, exact resolved native authoritative proof references/manifests where actually available, scope/evidence state and explicitly missing/unresolved proof IDs. Native omitted/None means no recorded URL; a recorded string is retained exactly, without reconstruction or URL normalization. Do not invent proof objects for missing claims. A URL-only change, including absent→present or present→absent, changes proof/reference identity while item semantics can remain equal, so it carries `proof_changed_item_same`. Hashing a recorded URL does not fetch it, establish reachability, verify an official portal or certify applicability.
- Procedure digest: exact original `ordered_steps` array. Its order is not an applicant-entered workflow or proof that dependencies were completed.

G1's native document key excludes `claim_ids` but retains `source_url`; it is **not** the G3 semantics digest. G1 DTO exposes `source_locations` and `original_items`, but not numeric source indices. Attach an accepted G1 action/reference only when the actual native projection unambiguously covers the exact raw occurrence set. Preserve the native action ID and manifest/proof identity exactly. Duplicate ambiguity or no real projection leaves the optional G1 link absent with a reason; raw occurrence refs still exist. Do not synthesize an action ID or bind by a guessed hash/name. G1 remains unchanged.

An authorized current adapter compares accepted refs with current raw occurrences and actual G1 observations; keep all applicable reasons (`proof_changed_item_same`, `item_changed`, `procedure_order_changed`, `ambiguous_occurrence`, stale/scope/conflict/proof gaps). Reorder/removal means the old accepted index is historical; do not silently move it or transfer prepared/sent/not-needed state. Explicit rebind records old/new refs under G3 CAS while preserving personal history. Scholarship purpose alone does not establish a named award relation; retain `award_relation_unknown` and `document_predicate_not_projected` as applicable.

Immutable G3 binding ACK stores refs/digests/IDs and own entered context, not source names/prompts/excerpts/URLs/scope bodies. On a research lock, do not load raw premium checklist/claims/conflicts or expose a NEW current digest, revision, count, name or source relation. Preserve the safe locked envelope and old own accepted references without claiming current comparison.

## 5. Distinct target cap and honest read bounds

Let G3 current union be the unique result IDs from all current own ApplicationRecord targets (including withdrawn/disappeared/rejected historical targets) plus current case-personal source-bound tasks. Tasks inside an application use that application's target; no hidden alternate target bypasses the union. Append-only event/binding references outside the current union are retained as history with `not_evaluated` and a safe envelope, not joined into a current graph. Source change or disappearance does not erase a counted application.

Within each new-application/new/replacement-binding transaction, after owner/UUID replay and G3 CAS, calculate the **prospective** union including replacement/removal semantics. Require≤20 distinct IDs and strict current own/approved-or-maybe authority for the newly bound target. Already counted IDs may receive more bounded tasks; reject a21st distinct target before any current/event commit. Two simultaneous new distinct binds at19 must not both reach21. Existing personal observations, date/note/correction/withdrawal/submission declarations do not depend on target availability or current source/selection eligibility and do not need a G1 read.

| Read role | Finite bound / allowed reuse |
| --- | --- |
| G3 current-target metadata/source observations | One owned metadata batch over≤20 distinct current union IDs; at most one G3 source observation per target for this role, reused across its applications/tasks. Own/selection/access before premium load. Missing/foreign is the same safe unavailable status. |
| G3 raw checklist comparison | Separately bounded by that same≤20 target set; read one authoritative checklist observation per distinct authorized target for this comparison role, reused across all its bound occurrences. No whole historical selection load. |
| Selected native G2 read | Unchanged native≤20 saved goals and public in-process current route behavior, including its required ownership/access guards and final redaction. The native reader's source probes are not claimed to be one SQL query. |
| Composite Today / recheck |≤40 distinct reference result IDs across G3 and selected G2. One bounded metadata/token recheck pass, not an unbounded per-history retry. Same ID can have observations for distinct roles; report component reads/mixed state, not atomicity. |
| History/replay/export | Accepted own reference-only history/ACK reads; no current-source observation of historical refs outside the current union. Native bounded event pages and complete reference-only export are preserved; export is not a graph read. |

Reuse public G2 per-result observations only if the exact required native manifest/provenance is sufficient for the G3 comparison in question. A G2 status alone is not a raw checklist, item proof digest or document-validity predicate. Otherwise keep the separate bounded G3 role; do not claim deduplication or refactor a private loader. Document current-source comparison remains evaluated when authorized, with unknown/error reasons if incomplete; it is not globally replaced with `not_evaluated` merely to hide a necessary role.

Case ownership/metadata/access is rechecked before authorized joins; an observed lock removes all current premium slices, including earlier loaded ones, without changing old ACKs. There are no external fetches, provider/LLM calls, quotas or reads of stored source history to find a more convenient target. These are finite application read bounds, not measured performance/latency results.

## 6. Exact Today learning target through App.tsx

The actual navigation seam is `frontend/src/App.tsx`, not bootstrap `main.tsx`. Keep existing `ScreenId` navigation. Add only a finite typed learning-target handoff from Today to `PreparationScreen` that carries **the exact native `LearningTaskRef`**, selected origin/head observation, saved occurrence/task ID, captured applicant owner/profile/caseEpoch and a distinct navigation intent generation. It is an in-memory navigation intent, not a new durable schedule, saved progress or submit command.

1. Today renders only the matching captured own case and current read generation. Click captures the exact saved ref and current owner/profile/epoch. Do not replace it with a programme-derived lesson ID or look up latest content from the catalogue. A mixed/unavailable plan does not offer a falsely current joined action; safe independently available own review/history remains separately reachable.
2. App validates the capture against its current owner/profile/caseEpoch before changing screen/adopting the pending target. Revalidate before passing/painting it and consume each intent at most once. Ordinary navigation away, a newer click, auth/logout/case replacement/deletion and A→B→A invalidate it. Do not persist it into owner-level storage or revive it automatically on remount.
3. `PreparationScreen` keeps its existing owner/profile/caseEpoch keyed case boundary. Exact dispatch is the existing `openLearningTarget` seam: lesson ⇒`startLesson(lesson_id, content_version)`; review ⇒own `attempt_id + lesson_id + content_version` through `openReview`. Validate native response identity before display, with current owner/epoch/mounted/intent fences. Never route a different case's task because the visible ScreenId is the same.
4. Native `LearningTaskRef` also contains assessment/external_resource variants. They remain explicitly unsupported/not implemented unless the already existing native contract supplies an executable target; do not reinterpret them as a lesson or introduce a new course/resource fetch. A v1 bare `lesson_id` without an exact native version has no exact Today lesson handoff; its ordinary legacy calendar/navigation remains available without fabricating a `LessonRef`.
5. The pending exact target waits for the required native preparation/access state; it is not consumed when existing `startLesson` would silently return during loading or locked access. On expiry, show the native new-practice lock; never fall back to another version. Own exact review is separately permitted by its native endpoint after expiry, including an unavailable historical lesson receipt. A catalogue/progress read failure leaves a retryable exact intent/error state, not a generic lesson substitution or an automatically submitted attempt.
6. Native request owner checks and preparation exact lesson/review checks remain the authorization boundary. Click navigation grants no entitlement, changes no official score, submits no answer and marks no slot complete. Retry retains the same exact target; choosing a different target is a new navigation intent.

Current source has an internal exact dispatcher, but Home passes only `onNavigate(ScreenId)` and preparation accepts no target prop. The new handoff is a future source seam, not functionality already present. Native `startLesson` currently allows catalogue fallback for its ordinary internal call path; the Today path must always supply exact `content_version` and must not broaden that fallback into this handoff.

## 7. Focused future controls — NOT_RUN

1. Selector g2/v2/v1 exact expected G3 revision and observed head tokens: one accepted event; stale observed native head conflict; wrong owned case rejected without premium load.
2. Same UUID and identical intent after native head advance/disappearance, research lock or prep expiry ⇒byte-identical original ACK; changed intent409; event-insert rollback preserves prior selector.
3. Physical SQLite/PG concurrent selector/native save and initially absent legacy row: serialize or conflict, no placeholder/backfill/parent timestamp; concurrent case/account delete leaves no orphan G3 current/event.
4. Selected g2 advances after a new accepted G2 save: Today shows the new native revision/exact saved slots, original selector ACK unchanged. Selected legacy remains legacy after the same G2 save. Explicit return-to-legacy records a distinct G3 event.
5. Derived defaults: absent G3 selector+valid G2; history-only broken pointer; corrupt sidecar `{}`; valid v1 only; no rows; metadata failure. Assert no fallback, no DML/backfill and no all-history deserialize.
6. Corrupt G3 current aggregate cannot be interpreted as absent selection. Selected unavailable plan still exposes independent personal tasks/declarations with safe component failure.
7. V1 tick advances technical revision/full settings digest while structural fingerprint stays equal; v2 follows raw sidecar identity without hashing refreshed GET metadata. Saved v2 dates/ref versions remain unchanged across day advance.
8. Raw duplicate same-list/cross-list occurrences preserve original zero-based indices; reorder/proof-only/item/procedure change have different reasons. Missing/ambiguous G1 projection never gets a fabricated G1 action link. Award relation remains unknown absent real projection. URL-only absent/present/value changes leave item semantics equal, change proof/reference identity and yield `proof_changed_item_same`; the control must assert zero URL fetches/portal-verification calls.
9. At19 two real concurrent new distinct bindings cannot both commit21; at20 binding to existing ID succeeds within task cap,21st distinct fails. Withdrawn/disappeared application still counts; rebind prospectively removes an old case-personal ID only if no current record still uses it.
10. One G3 target with many tasks produces one current source observation and one raw-checklist comparison for their respective roles; disjoint G2/G3 goals reach at most40 distinct references. Assert no history-wide G1 call, private loader refactor, external fetch or quota mutation.
11. Personal self-report/correction/submission still succeeds when its original result is missing/rejected/foreign/locked; new binding remains strict. Own historic ACK refs outside current union show safe `not_evaluated` and no current metadata/premium source.
12. Access revocation/head change between component reads and single recheck ⇒locked/mixed with earlier premium slices cleared and no contradictory join; no allocator/second ledger/retry loop.
13. Today lesson click requests exactly its saved version even when catalogue latest differs; review click requests exact own attempt UUID/version. Wrong response identity, late response after owner/case/epoch replacement and A→B→A are rejected before paint.
14. Loading/copy click is consumed once only when dispatched; leaving preparation/newer click cancels it. Expired new lesson cannot silently substitute content; own review stays readable. Unsupported assessment/resource and bare v1 lesson ID create no fabricated lesson call.
15. Selector/binding references remain additive in complete owner export and native case/account erasure. Browser cleanup/import retains accepted V2 case-local tombstone/index, non-destructive legacy-mark ACK and honest historical residuals; no source-name leakage in locked ACK/current.

These controls require root's future source application and separately authorized local gates. They are neither proposed executable test files nor proof of production/academic quality.

## 8. Inspected source pins and preserved documents

| Read-only source/document | SHA-256 |
| --- | --- |
| `ROOT_G3_DESIGN_ACCEPTANCE.md` (external stage) | `81fc914fd0756436ebd3974ad7847131e90c5e19b64121fb2733b5fd36d8f70d` |
| `proposals/g3-design/G3_CONTRACT_DESIGN_V2.md` (external stage) | `7b3857d7a273e3bbb3b38644101a03fd41159bbc121b406b3a76ef929f3edbbb` |
| `proposals/g3-design/G3_IMPLEMENTATION_DEPENDENCY_MAP.md` (external stage) | `81171a86f90c11e19438efe760ad9e0cd4fcbc394c036a3ec7f9bb1143537bdb` |
| `backend/app/models/study_schedule.py` | `087ccef37010f3eeddce5329856832de1d4aeea796cba48a52e439cf0ca03626` |
| `backend/app/api/preparation_transactions.py` | `ecbf9c12c95d6a178bf6d1c8c2aca8dcc3b5522e8b0aa4da64e465c99c68d2d7` |
| `backend/app/api/routes_shared_route.py` | `fec7d50d7e29cbebea1d1d46bb2245ccb129f216974ba281fd2550013bbe37f9` |
| `backend/app/api/routes_preparation.py` | `11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2` |
| `backend/app/schemas/shared_route.py` | `50c2dca8ad250f3d12fc9645a6307ac4dd05bf05a61c79c17bbf925b4c8042e2` |
| `backend/app/schemas/learning_schedule.py` | `a5c26ea689d67aa68cf46936adc5057c854613a99691259282ba5ca64ea684b6` |
| `backend/app/domain/learning_schedule.py` | `f5fb507796e5c7f6d4704ffff6f218fb8a59a35b79bf1fc659212544628e2e62` |
| `backend/app/schemas/result.py` | `f4eab02362d8bcdcec72bc1f16e2636f7abe7c0844b72b18bb4eac94f3927974` |
| `backend/app/api/routes_preparation_graph.py` | `7ddff09f9ef9601571568d51c3701e901166193de1801280b2901d067a0ef7c9` |
| `backend/app/domain/preparation_graph.py` | `2ba1488a582a4a8e4a37d747a5a4e4d1d44ceb70c980ad50195438dae3b35c09` |
| `backend/app/schemas/preparation_graph.py` | `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249` |
| `frontend/src/App.tsx` | `5cd7408024f9732cfd661a78e3a8f2f45c01267117a6d50dee9b24a1f9328e26` |
| `frontend/src/screens/PreparationScreen.tsx` | `3de3a2a2ed36dc7e2cc840e947b2c4c91a21c5729af468ed8c40611bb85c41fb` |
| `frontend/src/api/client.ts` | `f667d2f3b89d64ea42392f9e5bba3a30d04a1a76b2203fa2b4a337a7a8cc6789` |
| `frontend/src/lib/store.tsx` | `5f7d2fd0c93c3125442aaa1f2e271748dc25528f39266603735270ec2b8343a3` |

Concrete inspected lines: native v1 read/CAS `routes_preparation.py:81–163`; native v2 read `:196–277`; structural fingerprint `domain/learning_schedule.py:22–31`; native ref union `schemas/learning_schedule.py:14–49`; fresh owned transaction fences `preparation_transactions.py:22–107`; G2 current/history metadata/read `routes_shared_route.py:200–228,764–804`; raw checklist and omission `schemas/result.py:259–313`; authoritative reconciliation `routes_preparation_graph.py:109–145`; G1 occurrences `domain/preparation_graph.py:361–408` and DTO `schemas/preparation_graph.py:219–231`; owner/epoch mount and exact response/dispatcher `PreparationScreen.tsx:45–57,103–119,176–190,212–248`; navigation seam `App.tsx:437–454`.

Before any later source proposal, re-pin the released native bytes and freeze safe selector error mapping/canonical reference type with root. Current runtime source is frozen and this addendum changes none of it. Seal covers this file only and records preserved input hashes; it does not seal independently authored root decisions or claim G3 implementation acceptance.

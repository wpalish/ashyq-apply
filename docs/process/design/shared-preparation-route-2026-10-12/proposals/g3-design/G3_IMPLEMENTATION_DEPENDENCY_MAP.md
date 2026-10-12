# G3 implementation dependency map — documents, declarations and Today

2026-10-12 · **EXTERNAL READ-ONLY MAP / DESIGN_ONLY / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

Root is the sole source, Git, HANDOFF and runtime writer. This file contains an implementation map and proposed future acceptance controls, not application code. G2 source/gates are frozen under root. G3 source work requires G2 release and a new bounded root write-ahead; this map does not grant either. Existing STOP, no-provider/no-label/no-network boundaries remain unchanged. No application/helper import, test, runtime, Git operation or source edit was performed for this map. No sealed G2 member was changed.

Source root: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`. Paths below are relative to this root. The current source bytes, rather than an assumed deployment or gate outcome, support the observations. G2 source application acceptance expressly separates source application from runtime qualification; this map does not claim G2 release, CI success, deployment, live search quality or admissions readiness.

## 1. Accepted boundary and concrete gaps

Authority: `ROOT_G3_DESIGN_ACCEPTANCE.md` accepts the sealed `G3_CONTRACT_DESIGN_V2.md` as **design only**. The independent v2 review closes F1–F5/R1–R3 at that level. Preserve those documents. This map replaces the design's future-G2 placeholders with the actual native G2 types without changing G1/G2 wire contracts.

| Actual source and seam | What exists now | Required G3 increment |
| --- | --- | --- |
| `frontend/src/screens/DocumentsScreen.tsx:25–61,190–201` | Owner browser map `ashyq.docsDone`; a checkbox is keyed by `result_id::name`. No server command or accepted event. Equal names share a tick, irrespective of purpose/actor/occurrence. | Stable own document-task ID, case CAS/UUID commands and accepted self-report history. Raw marks become explicitly labeled import candidates, never authoritative server progress. |
| `frontend/src/screens/DocumentsScreen.tsx:37–46` | Findings come from `useStore().results`, the loaded run; selected checklists are not an exhaustive historical case inventory. | Own G3 records are fetched by profile, independently of the current run. Do not erase old tasks or claim all old marks are attributable from these rows. |
| `frontend/src/screens/ApprovedScreen.tsx:14–23,89–119` | approved/maybe/rejected is the shortlist decision ledger. It contains no submitted/withdrawn application records. | Separate `ApplicationRecord` and declaration event. `approved` never becomes an admission offer or a submitted state. |
| `frontend/src/screens/HomeScreen.tsx:18–55` | Research/navigation next step; no Today read projection. | Case-owned Today component, with independent personal, saved-plan, permission and source observations. Keep existing research navigation available. |
| `backend/app/schemas/result.py:259–313` | Native full document constraints and six ordered lists, `ordered_steps`, unresolved/completeness; item scope omission is deliberately preserved. No task or self-report ID. | Use read-only as source input. Generate a separate reference-only binding receipt, not fields/backfill in `DocumentItem` or `ProgramResult`. |
| `backend/app/schemas/preparation_graph.py:220–231`; `domain/preparation_graph.py:361–398` | G1 document actions retain original items and list names; unique cross-list projections may be grouped, same-list duplicates remain distinct. Original numeric occurrence indices are not exposed in the DTO. | New G3 server-selected occurrence ref includes original list and index, item digest and native G1 action ref where applicable. A graph ID/list name alone is not a complete persisted occurrence ref. |
| `backend/app/models/shared_route.py:27–75`; `api/routes_shared_route.py:759–802` | G2 current and immutable history receipts, with separate dynamic status and evidence. | Reuse the public in-process read contract. Today never calls preview/save/allocator to reconstruct its workload. |
| `frontend/src/screens/PreparationScreen.tsx:78,125–136,312–327` | Presence of a saved G2 view sets local `sharedActive`; legacy controls become history. This is not a separately persisted active-plan selector and no return-to-legacy event exists. | Freeze a G3 selection command and reference semantics before source work; keep the choice in the new G3 case aggregate/event, not a second schedule or a change to G2 receipt. |
| `frontend/src/App.tsx:441,454`; `PreparationScreen.tsx:243–248` | Home hands off only `ScreenId`; exact lesson/review dispatch is internal to preparation. | Add a finite owner/case/epoch-fenced typed target handoff so a Today action opens its exact version/review rather than a generic catalogue screen. Navigation does not submit anything. |
| `frontend/src/lib/applicantStorage.ts:99–108`; `lib/store.tsx:889–927` | A matching case DELETE ACK clears its draft and marks for current loaded result IDs. Historical unknown prefixes may remain. | Add best-effort exact G3 case-family cleanup/tombstone; preserve existing known-prefix cleanup and explicitly report old unindexed residuals. No owner-wide case wipe. |

These are factual absent seams or identity limitations; they do not establish a new live-search or G2 allocation defect.

## 2. Exact native G2 adapter

Use `read_shared_route(profile_id=..., principal=..., session=...)` explicitly in process; historical selection uses `read_shared_route_revision(..., revision=...)` when the chosen reference is pinned. No HTTP self-call, new Session, request to a provider, allocator or hidden save. Both native routes validate ownership and deserialize the full typed immutable receipt. Their dynamic evidence remains separate and subject to current research access.

| Native field/type | G3/Today use | Boundary |
| --- | --- | --- |
| `SharedRouteCurrentOutV1.profile_id`, `revision`, `view` | Exact own observed head, or revision 0 + null; capture component read time. | A failed/corrupt selected read is unavailable, not an empty plan or alternate legacy budget. |
| `SharedRouteViewV1.receipt: SharedRouteWriteReceiptV1` | Accepted reference-only identity. Capture `revision`, `snapshot_digest`, `allocation_digest`, `accepted_at`, `accepted_planned_on`. | Do not persist `current_status` or `visible_evidence` into G3 ACK. |
| `receipt.selected_result_ids` and `source_reference_digests` | Preserve exact ordered saved goals/baselines, including older runs. | `eligible` means an owned approved/maybe selection with native current-reference checks, not admissions eligibility or document compliance. |
| `receipt.allocation.slots: list[DatedSlot]` | Exact array order, `occurrence_id`, `action_id`, `ref`, `exam`, `kind`, `local_date`, `planned_minutes`. | No new date, version, occurrence, minimum, shared-document estimate or slot sort that destroys accepted relative order. |
| `DatedSlot.ref` | Native `LessonRef` or exact `AttemptReviewRef`, including recorded content version/attempt UUID. | Open through existing preparation lesson/review APIs; never infer exam/version from spelling or substitute latest content. |
| `allocation.capacity`, `unallocated`, `exam_timing`, `timezone` | One accepted minute ledger and accepted personal timing choices. Unallocated remains visible. | A documents card has workload `unallocated/not_estimated`; it does not consume another weekly limit. Unknown plan data is unknown, not zero. |
| `allocation.readiness='not_assessed'`, `programme_applicability='unknown'`; `DatedSlot.completion='not_projected'` | Preserve literal native uncertainty. | Do not call saved slots completed, official score targets, mastery or admission readiness. |
| `current_status.goal_statuses` | Per saved goal: eligible / decision_changed / result_unavailable / research_locked / source_changed / evidence_unknown. Preserve order and exact safe reason. | Do not replace an entire saved selection when one goal disappeared; no foreign premium lookup. |
| `current_status.content_statuses`, `preparation_access`, `needs_review`, `review_reasons`, `as_of` | Independently displayed current availability/review, observed at native read. | Content availability does not authorize new practice; own review remains readable after preparation expiry. |
| `view.visible_evidence` | Optional current authorized source envelope only. | Never enrich locked output from cached frontend `ProgramResult` names, old premium card data or G3 receipt refs. |

Native source: `schemas/shared_route.py:326–347,735–756,888–896`; route read/current/revision: `routes_shared_route.py:692–802`. Full receipt validation at `shared_route.py:767–885` binds original inputs, exact refs, the allocation and receipt digests. G3 should consume that validation rather than write a weaker receipt parser. Native `_goal_statuses` already checks own metadata before source access and clears visible slices on an observed lock (`routes_shared_route.py:576–655`). Reuse public read behavior; do not refactor/private-import G2 loaders merely to save a few lines.

### One plan selector — freeze before code

The design requires an explicit G2 opt-in and explicit return to legacy, but neither existing model has a durable discriminator. The new G3 current aggregate may hold a small `ActivePreparationSelection` reference with its selection event ID/revision; no lesson arrays, schedule copies or third ledger. The finite command must bind expected G3 revision and observed own selected-plan identity. **Root must choose whether G2 selection pins a revision+snapshot/allocation digest or explicitly follows a current head.** If it follows a head, that is an explicit typed policy with later observed revisions, not silent replacement. A stale/malformed selected route stays selected and produces review/unavailable, never fallback. Selection does not grant practice access or rewrite a G2/legacy row.

For a case with no G3 selection, freeze backward-compatible initialization: existing explicit G2 save opt-in versus saved v2 sidecar versus v1, without a GET backfill. Current native UI treats G2 presence as active; silently ignoring that on upgrade would produce two differing active views. Exact initial selection and return-to-legacy semantics belong in the subsequent root source contract.

Legacy v1 remains `read_schedule` / `StudyScheduleOut`: own row technical revision, settings fingerprint and **native current projection**, with original self-ticks (`routes_preparation.py:81–113`). Do not relabel its projection as immutable. Legacy v2 remains `read_learning_path` / `LearningPathOut`: saved sidecar dates and exact learning refs; GET refreshes display metadata/availability, not saved dated refs (`routes_preparation.py:196–277`). A raw persisted sidecar digest is distinct from a digest of refreshed GET output. Structural fingerprint excludes completed_task_ids (`domain/learning_schedule.py:22–25`); technical revision still catches concurrent writes.

## 3. Bounded source path map for the next write-ahead

This is a proposed finite allowlist, not permission to apply it now. Pin actual preimages again after G2 release. Keep legacy/G1/G2 source read-only except explicit integration surfaces below.

| Path | Future change / reused primitive |
| --- | --- |
| **NEW** `backend/app/schemas/admissions_actions.py` | Closed versioned commands, own records/binding/event ACK/current view, bounded explicit import preview and discriminated Today components/targets. Keep receipt separate from dynamic source/access. Root freezes transport and selector bodies first. |
| **NEW** `backend/app/domain/admissions_actions.py` | Pure canonical checklist/item/procedure identities, finite state transitions, personal/reference-only current mutation and Today ordering. Accept already validated native inputs; no Session, network, allocator, lesson replacement or inferred official predicate. |
| **NEW** `backend/app/models/admissions_actions.py` | Two profile-owned tables: current aggregate and append-only accepted event. Stable own application/task IDs remain inside bounded aggregate; no third per-programme planner. Profile FK/cascade; no source-result FK that would erase personal history when a result disappears. |
| **NEW** `backend/app/api/routes_admissions_actions.py` | Own GET current/events, unsaved POST binding/import preview, one finite UUID+CAS command endpoint, read-only `/api/profiles/{profile_id}/today`; exact public native G2/v1/v2/permission reads. No route collection rewrite. |
| **NEW** `backend/migrations/versions/<new_revision>_admissions_actions.py` | Add only two G3 tables, constraints/indexes and profile FKs, descending from the actual released G2 head. Current source G2 ancestry is `c3e71d902023 → b5c81d9e2022`; do not claim the released head until root verifies it. No backfill/data correction. |
| `backend/app/models/applicant.py` | Add two `all, delete-orphan`, `passive_deletes=False` relationships, following existing shared_route_current/history. No parent updated_at/score/quota write for G3 commands. |
| `backend/app/models/__init__.py`, `backend/app/main.py` | Explicit new ORM/router registration only; no other route body change. |
| `backend/app/api/routes_profile.py` | Add reference-only G3 current/events/submission export, exact counts and note; call a caller-owned validated export helper. Existing results/claims/schedules/attempt export policy and delete response remain. New ORM descendants enter existing case erasure transaction. |
| `frontend/src/screens/DocumentsScreen.tsx` | Own durable tasks/self-report controls and binding detail/source status; explicit old-mark preview/confirmation. Server ACK is progress authority. Retain raw marks separately; a pending browser mark is not server completion. Load own records even without current-run checklists. |
| `frontend/src/screens/ApprovedScreen.tsx` | Separate own application planning/submission/withdrawal/correction controls and immutable declaration summary. Keep shortlist `decide` and rejected reasons intact. Missing current result does not hide an own application. |
| `frontend/src/screens/HomeScreen.tsx` | Today owned read/render, independently degradable components, exact safe targets and one workload. Existing research next step remains usable if Today fails. No automatic write on mount/click navigation. |
| **NEW** `frontend/src/lib/admissionsActionsRecovery.ts` | Captured owner/profile/epoch/intent fenced G3 case-family index/entries/tombstone, exact UUID pending command recovery and non-destructive import ACK. Reuse currentApplicantOwner/checkApplicantOwner/applicantStorageKey semantics without owner-wide case cleanup or a global storage refactor. |
| `frontend/src/types.ts`, `frontend/src/api/client.ts`, `frontend/src/lib/i18n.ts` | Typed new DTO/client methods/copy. Native requestWithHeaders already checks owner before/after I/O; G3 adds case+epoch/intent response matching. Do not add bare fetch or automatic retry. |
| `frontend/src/App.tsx`, `frontend/src/screens/PreparationScreen.tsx` | Minimal typed Today-target handoff into existing exact startLesson/openReview dispatcher; owner/case/epoch match before paint and response adoption. Existing onNavigate and ScreenId remain supported. Add explicit active-plan choice visibility only after selector schema is frozen. |
| `frontend/src/lib/store.tsx` | Only exact case DELETE-ACK G3 cleanup hook/tombstone coordination and necessary own identity handoff. Existing case pointers/profile drafts/research lifecycle remain. Never source G3 history from latest results or move all G3 server data into the research store. |

Read-only dependencies: `schemas/result.py`, G1 schema/domain/API, G2 schema/model/domain/API, native preparation routes/schedule schemas/domains, `preparation_transactions.py`, tenancy/security/payments and account deletion. Existing `export/calendar.py` and result deadlines routes remain run-based official-source information, not the new personal Today calendar. No new crawler, LMS, calendar allocator, ledger, upload or blob store.

## 4. Source binding and uncertainty adapter

1. Owner case first. Existing personal commands select their own application/task/event from the G3 aggregate only. Do not load historical result premium payload as a prerequisite for self-report, date/note, correction, withdrawal or declared submission.
2. New application target/new binding rechecks exact owned result via ResearchRun.profile_id; approved/maybe only. Named scholarship target validates exact current Scholarship.id after research entitlement. This is selection authority, not a positive admissions requirement verdict.
3. For authorized binding preview, reuse `preparation_graph(profile_id=..., result_id=[...], principal=..., session=...)` with explicit native arguments. G1's whole selection stays strict. Historic unavailable/rejected targets must be excluded from any authorized G1 call, with safe per-target status retained; never call one strict G1 over all historic application IDs.
4. Native authoritative checklist reconciliation is at `routes_preparation_graph.py:109–145`: column versus payload disagreement, foreign result/university/program identity, malformed/nonfinite values cannot become an empty list. G3 needs a narrow owned authoritative-checklist adapter to preserve raw list/index occurrences. Keep G1 helper/private route source unchanged; any deliberately duplicated validation in the new module must be pinned/tested against the native contract, not replaced by client source objects.
5. Full checklist canonical serialization excludes only generated_at, retains six ordered lists, duplicates, ordered_steps, unresolved/completeness and omitted versus recorded scope. Native serializer intentionally omits unrecorded scope (`result.py:286–297`). Stable G3 task ID is distinct from source occurrence identity.
6. Freeze three separate identities: full checklist/native proof reference; bound item constraints excluding claim_ids/source_url; ordered_steps. Bind original occurrence locations/indices, exact G1 document ref if projected, original claim refs, award reference and digests only. Never copy prompts, source names/excerpts/URLs into immutable ACK as premium evidence.
7. Keep all applicable read reasons: proof_changed_item_same, item_changed, procedure_order_changed, stale, scope unknown/mismatch, conflict, ambiguous occurrence, award_relation_unknown. Matching constraints do not prove an old file meets them. No automatic prepared/sent state transfer on reorder/rebind.
8. Native G1 manifests carry result_snapshot_digest, authoritative_evidence_digest and resolved_claim_ids (`preparation_graph.py:282–287`). Their evidence digest excludes age_days, retains is_stale and authoritative source fields (`domain/preparation_graph.py:501–545`). Use the existing native manifest exactly; do not claim a new official comparison or manufacture locked current digests. G3 precise item/procedure comparisons are separately versioned.
9. `DocumentItem` has scholarship purpose, but no named award ID. Binding a task to an own award application preserves award_relation_unknown unless an explicit current source relation exists; do not generalize every scholarship document to every award. No fake AND/OR/waiver or missing predicate completion.
10. Load metadata/access once per bounded distinct target set and reuse authorized per-result observations across its tasks. The native G1 request max is 20. Before source work, freeze the maximum distinct source-target/read fan-out for case-personal source-bound tasks, or restrict their binding to the frozen own application target. The 20-application/400-task caps alone do not establish that every document references at most 20 results. Any deliberately unevaluated slice must say not_evaluated/unknown, not current.

## 5. Persistence, migration, export and erase

- New current row: exact profile PK/FK, schema version, positive revision, full validated bounded personal/reference-only snapshot and digest. Event row: stable ID, profile FK, revision, typed client UUID, canonical request digest, immutable safe receipt, accepted UTC time and kind; unique(profile,revision), unique(profile,UUID), ordered profile/revision history index. No backfill from browser marks or inference from ProgramResult.
- Freeze current/event integrity binding: accepted event should bind the resulting current snapshot digest/head identity; validate current/event profile/revision/digest/UUID/request links. Root must decide exact receipt fields before source proposal. Outer rehash is not sufficient to accept corrupt inner task/binding data. Corruption is an explicit safe error, no GET repair or reset to revision0.
- Reuse `begin_owned_preparation_write` / fresh transaction + owned strong profile fence **after G2 release**. The helper does not grant or require a preparation term: it checks a clean request session, owner/current actor and existing legacy child ID only. G3 personal commands must not accidentally call _require_access. SQLite first guarded SQL BEGIN IMMEDIATE; PG fresh READ COMMITTED + local bounded lock wait + profile FOR UPDATE. No clean-read/auth data is discarded if session is dirty, no no-op parent timestamp, no late Org/User write lock/audit FK.
- Locked owner → accepted UUID lookup → exact replay/conflict precedes mutable G3 head/source/access. Same UUID+canonical intent returns the same persisted 200 ACK. Changed intent409. New command branches by personal versus new-source authority, CAS/create, one event insert, one commit. Event failure rolls back current. CAS/unique loss rolls back the whole transaction, then fresh owned UUID reconciliation; absent event is ordinary409. Unknown response retains original UUID/body for retry.
- New G3 records join the existing erasure fence. Case erasure already takes Organization key-share before owned Profile (`routes_profile.py:428–470`); account erasure preserves remaining shared-member workspaces. Do not add a user/organization FK into a late G3 audit insertion or a result FK that destroys own personal history. Actor provenance is trusted native principal data; exact actor storage/privacy policy must be fixed before migration.
- Additive export uses all ordered accepted events, not the paginated UI subset. Preserve existing owner-only results/claims policy; reference-only G3 sections are distinct from current source redaction. Native G2 export rejects mixed current/history heads (`routes_shared_route.py:965–984`); use an equivalent bounded integrity guard for G3, not private G2-row parsing or silent event omission.
- One additive migration with real SQLite+PG upgrade/downgrade controls, exact no-backfill preserved old rows and no second head. Test new ORM delete-orphan descendants even on SQLite policy variation. FK/cascade alone is not evidence of a concurrent erasure proof; extend the native physical race controls for G3 rows.

## 6. Browser recovery, import and declarations

The new exact family is `ashyq.owner.<encoded-captured-owner>.ashyq.g3.case.<encoded-profile-id>.` with index-v1, entry.<UUID>, deleted-v1. Auth-disabled explicit demo uses a distinct demo binding, never an anonymous authenticated write. Each entry is self-describing; the advisory index records UUID/digest/baseRevision/task/application/sourcePreview/pending-or-ACK/receiptRef. A lost index merge is not ownership; unknown/foreign/mismatched entries are not hydrated.

Every read/write/response/cleanup matches captured owner, saved profile, caseEpoch and intent generation. A→B→A, logout/auth transition and deletion invalidate response adoption before paint. Matching DELETE ACK writes the case tombstone/invalidation and removes only exact G3 family + exact case draft, best effort. Storage/interleaving failure reports residual_unknown; it does not block the acknowledged server deletion or become a complete-browser-purge claim.

Legacy `ashyq.docsDone` import accepts only literal true. Original source version/time stay unknown, including a uniquely matching name. Preview selects current exact owned task/occurrence, current case revision/source identity and explicit present-time self-report confirmation. Ambiguous same name/purpose/actor/award/duplicate requires exact selection. The bounded all-or-nothing import records prepared_reported with explicit_browser_mark_import provenance. ACK records durable state/receipt in new case-local index and **never deletes raw shared legacy keys / calls forgetDocumentMarks**. A newer false→true edit therefore survives an older import ACK. Unknown response retains exact input/UUID; edited intent gets a new UUID after review.

The native known-result-prefix cleanup may continue only after matching profile DELETE ACK. Report separate server_data_deleted, indexed_browser_cleanup and legacy_cleanup residual_unattributed/unknown. Latest loaded run IDs are not a complete case manifest.

Application target/intake/route/purpose/award are frozen at creation. planning/preparing are explicit personal states. submitted_declared requires a stored own applicant-declared submission event; withdrawn_declared and corrections append their own events. Store entered time/channel/short reference separately from accepted server time. `official_verification='not_performed'` persists even if the applicant says a portal displayed a receipt. A saved programme link or checklist cannot certify portal destination, package validity or recipient receipt.

`SourceLink/isSafeHref` currently protects absolute http(s) scheme only (`primitives.tsx:123–154`). G3 needs its own typed action-link policy: no credentials/private tokens/file/internal links; programme_information / requirements_information / applicant_entered_external roles. Preserve fixture-text behavior. Exact lexical URL rules must be frozen/tested before source work; no DNS/fetch/live-destination or verified-portal claim follows. Do not widen/rewrite global native source-link semantics as an incidental G3 change.

## 7. Today assembly and action delivery

1. Own case/no-autoflush read; load validated G3 head (empty0), own personal records and explicit active selection. Keep component observed revision/digest/read time.
2. Read the chosen native plan only. G2 receives immutable typed persisted receipt/slots; v2 receives saved dated refs with structural review; v1 remains native dynamic projection. Selected malformed/unavailable/stale stays selected. Keep personal documents visible if the plan component fails safely. No preview/allocator, DML, fallback or second workload.
3. Read `preparation_access(session, organization_id)` independently of `has_full_access`: native ACTIVE or EXHAUSTED inside started unexpired term allows learning; CASE_FULL alone does not (`payments/preparation.py:15–44`, `entitlements.py:17–36`). Own saved history/review remains readable after expiry; new lesson/attempt keeps native gate. Current authorised source statuses are independent of own declarations.
4. Recheck relevant scalar metadata/tokens once after assembly: G3 head/selection revision, selected plan identity/head policy, owned decisions and access. Use actual scalar reads, not a possibly cached ORM object's old attributes. Changed => mixed_revision/needs_refresh with observed origins; withhold contradictory joined next-action suggestions. No unbounded retry or atomic multi-writer/source snapshot claim. Known observed research lock clears newly read premium slices, not old ref-only ACK.
5. Ordered sections follow accepted G3 v2: notices; overdue entered personal due date; today's saved study slots in original relative order; today's open personal actions; future date ordering with study before personal on same date and accepted relative slot order; undated personal stable IDs. Terminal declarations remain summaries/history, not repeated submit-now cards.
6. Count minutes from one chosen plan only. Personal document minutes stay not_estimated. Source date-only/missing TZ/cycle is uncertain; previous_cycle_deadline remains previous. Known lead-time start advice is advice, not allocated work or a certificate deadline. Use selected entered IANA/display zone; UTC fallback is labeled display-only, not an official deadline.
7. Typed click targets carry exact own task/application or LessonRef/AttemptReviewRef + captured case/epoch. Home→App→Preparation opens the existing dispatcher with the exact version. Clicking an own task opens its action UI; no automatic self-report/submission. Existing native endpoint rechecks owner/access. Expired own review opens; new lesson does not. Do not manufacture a LessonRef for a v1 task that only contains lesson_id without a recorded content version.

## 8. Future meaningful controls — source, not PASS

All proposed below are **NOT_AUTHORED / NOT_RUN** for G3. Reuse existing local synthetic fixtures/policies; no providers, closed labels, extra auth accounts, network exception or new skip to call a gate passed. The listed current test files are patterns, not G3 proof.

| Proposed native test path | Required controls |
| --- | --- |
| **NEW** `backend/tests/test_admissions_actions.py` | Pure canonical full six-list/ordered_steps/scope-omission identities; same-list duplicate occurrence versus cross-list projection; proof-only/constraint/procedure changes separate; malformed/nonfinite source unknown; frozen target/state transitions, terminal declarations/correction, required not_needed_reported never waiver; one-plan Today ordering and document duration unknown. |
| **NEW** `backend/tests/test_admissions_actions_api.py` | Own/new/current/history/preview; generic foreign/missing404 before UUID/source; strict new binding versus personal updates after deleted/rejected/now-foreign result; exact same/different UUID, changed body409, event failure rollback; receipt/current pointer corruption safe error; locked payload query guard and no NEW premium digest/name/proof/count; expiry-independent personal replay/read/export; submission permanently applicant declared; all-or-nothing literal-true explicit import with no server backfill. Additive complete export and sibling erase. |
| **NEW** `backend/tests/test_admissions_actions_concurrency.py` | Physical migrated file SQLite + private PostgreSQL, two real connections: first/present G3 head; same UUID delivery race and distinct UUID CAS race; case/account erase both orders and shared-member sibling; event/erase failure rollback; native lock waiting evidence and release; clean auth read versus dirty incoming session; original intent retry after bounded lock failure. Use native helper policy and real FK/isolation, no mocked concurrent Session. |
| **NEW** `backend/tests/test_today_api.py` | Empty case GET no DML; exact saved G2 refs/slot array/minutes after changed date/catalogue/source; selected corrupt/stale no v1 fallback; one budget; v2 pinned dates vs v1 declared dynamic behavior; term expiry versus research lock; real DB interleaving between component reads gives observed tokens/mixed_revision, not coherent snapshot. Local midnight/DST/date-only/previous cycle and no derived certificate deadline. Own records render on plan failure. |
| **NEW** `frontend/src/lib/admissionsActionsRecovery.test.ts` | Self-describing index/entry mismatch, lost index merge/different UUIDs, storage failure; A→B→A/owner transition/epoch/generation rejection; matching DELETE ACK only exact case family; late tab write after tombstone cannot render deleted data; sibling preserved; raw old import ACK never deletes newer marks, unmatched history remains residual. |
| Bounded new controls alongside Documents/Approved/Home existing screen tests | Pending versus server ACK, exact UUID uncertain retry and revised intent, reload/second browser own API persistence, no source cache leak under lock, no completion-name collision, declared submission versus official receipt copy, personal records with unavailable current result, component failure independence. Exact Today click/version/review handoff; expired own review allowed and new lesson gated. |

Regression dependencies: keep `test_preparation_graph*`, `test_shared_route*`, `test_study_schedule*`, `test_learning_schedule*`, native account/export/calendar tests and Documents/Export owner/case-switch tests. Current G2 two-connection controls live in `test_preparation_write_concurrency.py`; they show which mechanisms require real waiting observations, not inherited G3 success. Any runtime/helper binding requires its own later root write-ahead; this map proposes no runner command, environment expansion or result claim.

## 9. Decisions to freeze and finite implementation order

Before writing G3 source, root should pin:

1. Exact finite command transport/error codes and active-plan selection command: pinned versus explicitly-following G2 reference, upgrade default and explicit return to legacy. Existing G2 save/current bytes stay unchanged.
2. Raw authoritative source occurrence ref and validator choice, proof/item/procedure canonical versions, current-versus-event integrity fields. Do not persist G1 IDs alone or trust client checklists.
3. G3 actor provenance/FK policy, atomic current/event table contract and migration ancestry from the **released** G2 head; native erasure lock order reused.
4. Bounded distinct-target fan-out for personal/source task bindings/Today, safe unevaluated representation, typed exact click handoff and v1 tasks without recorded version.
5. Action-link lexical rule, local case index/tombstone bounds, exact import ACK and privacy residual copy. No official destination verification or complete browser erasure promise.

Then stage: (a) pure closed schema/domain + focused tests; (b) two-table migration/API/CAS/export/erase + actual DB controls; (c) Today public-native adapters/token recheck + read interleaving controls; (d) owner/case recovery and durable Documents/Application/Today UI + focused native controls; (e) root current-source-bound local gates and a separate synthetic real-API reload/second-browser path. A static map/proposal, an applied patch, local tests, active branch integration, deployment and real product acceptance remain separately recorded states.

This G3 increment closes durable actions and next-step navigation. It does not deliver a full exam curriculum, private attachments, authenticated university receipts, search recall improvement or a complete admissions product.

## 10. Source/design pins observed for this map

SHA-256 of actual source files read/hash-reconciled in the root checkout; no import/Git/deployment inference. Root may have later gate repairs; re-pin preimages before adoption. Current test hashes are inspected native-pattern inputs, not test outcomes. `main.tsx` is only bootstrap; actual typed navigation seam is **App.tsx**, avoiding the earlier generic “main” name.

| Design / external input | SHA-256 |
| --- | --- |
| ROOT_G3_DESIGN_ACCEPTANCE.md | 81fc914fd0756436ebd3974ad7847131e90c5e19b64121fb2733b5fd36d8f70d |
| proposals/g3-design/G3_CONTRACT_DESIGN_V2.md | 7b3857d7a273e3bbb3b38644101a03fd41159bbc121b406b3a76ef929f3edbbb |
| proposals/g3-design/G3_INDEPENDENT_DESIGN_REVIEW_V2.md | 9cdeedb1227c1aab708ae17a8018440ae739c6d5163759f2991f05dc4b138e78 |
| ROOT_G2_COMPLETE_SOURCE_ACCEPTANCE.md | e079d3675997e023cc9b92f89f6a2e62c3b612d308739b8ac126a8b42831b5c7 |
| ROOT_G2_PERSISTENCE_INTEGRATION_DECISIONS.md | c664a4c0db76e23b56091cf0cb435b5ed657749eb3f1b31df9526eca668c4465 |

| Source path | SHA-256 |
| --- | --- |
| backend/app/schemas/result.py | f4eab02362d8bcdcec72bc1f16e2636f7abe7c0844b72b18bb4eac94f3927974 |
| backend/app/schemas/preparation_graph.py | 4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249 |
| backend/app/domain/preparation_graph.py | 2ba1488a582a4a8e4a37d747a5a4e4d1d44ceb70c980ad50195438dae3b35c09 |
| backend/app/api/routes_preparation_graph.py | 7ddff09f9ef9601571568d51c3701e901166193de1801280b2901d067a0ef7c9 |
| backend/app/schemas/shared_route.py | 50c2dca8ad250f3d12fc9645a6307ac4dd05bf05a61c79c17bbf925b4c8042e2 |
| backend/app/api/routes_shared_route.py | f6dc485b26b9af6d04ba6e4a83d1da28ff1146b47ac3cab51c16d825d7bfb3d5 |
| backend/app/models/shared_route.py | a1cf969acfde2dea68c42c98edd8ad99fa8ebc5b18633f6bf1bdbf0bc9ab8e20 |
| backend/app/models/study_schedule.py | 087ccef37010f3eeddce5329856832de1d4aeea796cba48a52e439cf0ca03626 |
| backend/app/schemas/study_schedule.py | 259a752f19438af1ce7e72e1659844e314cca3c532ac30e0143649855b63218f |
| backend/app/schemas/learning_schedule.py | a5c26ea689d67aa68cf46936adc5057c854613a99691259282ba5ca64ea684b6 |
| backend/app/domain/learning_schedule.py | f5fb507796e5c7f6d4704ffff6f218fb8a59a35b79bf1fc659212544628e2e62 |
| backend/app/domain/study_schedule.py | a3cf27e10590be233df29b367b811a93cf7942e9776cdee59465a3aef464cb83 |
| backend/app/api/routes_preparation.py | 11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2 |
| backend/app/api/preparation_transactions.py | ecbf9c12c95d6a178bf6d1c8c2aca8dcc3b5522e8b0aa4da64e465c99c68d2d7 |
| backend/app/api/tenancy.py | 34557c1bae4f9cc36413cfd952a001342df9a35a1c5ecf5ad19bd83cf121363f |
| backend/app/payments/preparation.py | ab44ed538177c2ac765cd86ec326bb53c196c01927dc04565a9911fe50150a26 |
| backend/app/payments/entitlements.py | c866a0c548331d8fd7ae5487006dd29c03b89fbd0256183e703cb79bad21190f |
| backend/app/models/applicant.py | 613cdd1db26bf5dd9bc4af39af310b8720a6edec5e2e68a6090a95d59c8d6c28 |
| backend/app/models/__init__.py | 66ac532bca1fe7fd113f03f5b9ce0db1a809be87136197aac108fd2aeba53c40 |
| backend/app/api/routes_profile.py | b12a3a301829cc4f4eed5d8df53c2315efa11e5fb0e05e3ba2d9ead25d5202a3 |
| backend/app/api/routes_account.py | 50c4bf6cc7da8d72596dd87c9acff858894a12fce441ea2273a3b6c460697521 |
| backend/app/api/routes_cases.py | 29ad6875321621f6cd36a6a810b8e73b5007a4c5643cbdb6158a6b8354730f2c |
| backend/app/main.py | 8922a15d1ddb53237b7b1b7795a49cc688bcbe18338088b042695cb5462d8bb2 |
| backend/app/export/calendar.py | 187e6e1d0ec4d1393f5409676e26803497918531bbaa07f4345b8dabc786353a |
| backend/migrations/versions/c3e71d902023_shared_route.py | 309bd8494deb09d2e6afdaa6326809067aac802ce7f77255f64bdb8b2c5afd23 |
| frontend/src/screens/DocumentsScreen.tsx | e7ef0217c19f051c434acb69fb7f2b0ea1883a2228984054747cb8b77abcde9f |
| frontend/src/screens/ApprovedScreen.tsx | 0395dc3be1315f4c09defc2e0be85434fad0848b407220fa2903f26cdbe6b89a |
| frontend/src/screens/HomeScreen.tsx | bda406914a413a5371d5299f48aa5dfe6b0fbf3bcfae9b1613bbf25b4be18517 |
| frontend/src/screens/PreparationScreen.tsx | 3de3a2a2ed36dc7e2cc840e947b2c4c91a21c5729af468ed8c40611bb85c41fb |
| frontend/src/screens/SharedRoutePanel.tsx | a5057f0c6307a863a4b6c7054144682217142400fd4a40a6c8422eaefa9ccd5e |
| frontend/src/screens/ExportScreen.tsx | 4a452cb3c4bf65d2f983dbf8cac8a0edaaff36a0bb5dab83888a423ed4552722 |
| frontend/src/lib/applicantStorage.ts | 0a3230d223e5dbfc1ead6dbece478ce54c9ec6bc557493115716e5709818fd0e |
| frontend/src/lib/caseDrafts.ts | 9447cde514450ec60b79b7ac2182d0819fbd826f3d054c23fd35a493ec9ea058 |
| frontend/src/lib/store.tsx | 5f7d2fd0c93c3125442aaa1f2e271748dc25528f39266603735270ec2b8343a3 |
| frontend/src/api/client.ts | f667d2f3b89d64ea42392f9e5bba3a30d04a1a76b2203fa2b4a337a7a8cc6789 |
| frontend/src/components/primitives.tsx | ef745e6002023398e5d69f6e6227c719d879bc10997c94f179b15d67747a676b |
| frontend/src/types.ts | 472da567fe598b74f9fe43520b925fdfda6401866ef51f994104b2f5afa71511 |
| frontend/src/App.tsx | 5cd7408024f9732cfd661a78e3a8f2f45c01267117a6d50dee9b24a1f9328e26 |
| frontend/src/main.tsx | 528a210de97ed18011c7d79550bff3e37dde25e38f9238136ece285ab59a178b |
| frontend/src/lib/i18n.ts | 09c5b0f19a43cc2bfa6c461691779880460d7b40bd573b50582395150da09576 |
| frontend/src/screens/DocumentsScreen.recovery.test.tsx | c36a17a9af545ca187e7f257e37f5f01538c0085b6b7b027bc39cc071e338643 |
| frontend/src/screens/ExportScreen.caseSwitch.test.tsx | c0f226d1f242682459f254848bd9b9283ec25fe12aa6afa351443b36e74ea4a0 |
| backend/tests/test_shared_route_api.py | 13e04e275e8b3ffd263f513f7e382a53bd736eec4fc687ab8c5f179c209b3636 |
| backend/tests/test_preparation_write_concurrency.py | 0329d49de0bafcd23bebd08b52cd7826bb4836be742b31b7df6b89d6dc387d99 |

### End-of-read reconciliation

Root repaired/rebound two native G2 files while this map was being written. The table above intentionally preserves the initial read pins and their line references. A final read/hash check found the other 42 tabled native paths unchanged. Current read/export functions and strict receipt parsing were reread at the replacement source; public DTO names, typed slots and separated read-versus-ACK adapter remain the same. The current file now compares current/latest-history metadata in one SQL statement (`routes_shared_route.py:200–228`) and still rejects export heads that differ after loading ordered history (`:975–994`). No application import/test/runtime was run by this agent; these new pins are not a gate claim.

| Changed root-owned path | Later observed SHA-256 |
| --- | --- |
| backend/app/api/routes_shared_route.py | fec7d50d7e29cbebea1d1d46bb2245ccb129f216974ba281fd2550013bbe37f9 |
| backend/tests/test_shared_route_api.py | 84c166681851a448e24aaeb14bcdab4587777c47e3e137027760130c9fcfeee8 |

G2 execution copy and root checkout copies of these exact two paths were byte-equal at this later check. This is read reconciliation only; no sealed packet/source/helper metadata was modified. Re-pin all preimages after root's eventual G2 release before authorizing G3 source.

**Disposition:** The accepted G3 boundary can reuse actual native G2 receipt/read/transaction primitives. Durable task/declaration records, raw occurrence bindings, active-plan selection, exact Today click handoff and case-index recovery are still absent and require the finite next source stage. No source change or new qualification is claimed by this artifact.

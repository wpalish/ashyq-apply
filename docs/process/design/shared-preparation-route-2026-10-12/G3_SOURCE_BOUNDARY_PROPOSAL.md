# G3 source boundary proposal — documents, application declarations and Today

**2026-10-12 · IMMUTABLE EXTERNAL READ-ONLY INTEGRATION MAP · SOURCE_CLOSED · NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

Root supplied the current source baseline **45514df3**. No Git command was used to resolve or alter that ref; the independently captured source SHA-256 values below bind this read. Root alone writes application/source/Git/HANDOFF/helpers and executes gates. **G3 SOURCE_CLOSED until G2 release, a new branch/baton and exact root write-ahead.** This document authorizes no source proposal, implementation or execution.

Source root: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`. External stage: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12`. Source/design pin observation: **2026-10-12 04:45:28 UTC**; new-path absence observation immediately afterward. No mutable G2 gate output, application import, test, database, auth payload, network, provider, closed corpus/labels or stopped workflow was read or executed. Memory was used only for the connected admissions product scope, not implementation evidence.

## 1. Disposition and practical first subset

**No frozen-contract mapping blocker found.** The accepted first G3 boundary maps to the current source without another planner, calendar, workload, ledger or additional table. This is a preparation map, not a claim that those capabilities exist.

The finite deliverable remains the accepted versioned case aggregate/event: durable own ApplicationRecord and DocumentTask, applicant declarations/corrections and reference-only source bindings; separate current source/access status; read-only Today consuming exactly one chosen native saved plan. The frozen explicit selector and non-destructive legacy import rules are retained rather than replaced with an implicit “done” or submitted flag. Private documents/versions, attachments, actual recipient receipts, verified decisions, portals, autofill and new courses remain outside this subset.

Two additive G3 tables only: profile-owned current state and immutable accepted events. Applications, tasks, bindings and the active selector live in the bounded current aggregate; the affected_refs header is a metadata column of the same event table. No User/result FK, extra AuditEvent or per-application/task ledger is needed.

Implementation prerequisites, not product ambiguities:
- Root must finish/release G2 and issue the new exact write-ahead; current source hashes are provisional parent observations.
- Root must assign the exact new migration filename/revision after confirming the released single head. Existing source migration `c3e71d902023_shared_route.py` explicitly descends from `b5c81d9e2022`; no Alembic command or deployed-head verification occurred here.
- The closed command/DTO source must faithfully implement the accepted finite fields/errors; this map creates no new transport, command kind or permission.

## 2. Actual seams to extend

| Native seam and verified lines | G3 integration location / preserved behavior |
| --- | --- |
| `models/applicant.py:43–61`, `models/shared_route.py:27–75` | Add two own profile cascade/delete-orphan relationships following G2's pattern. No target-result FK: old result deletion must not erase a personal observation/application. Keep passive_deletes=False for ORM erasure. |
| `api/preparation_transactions.py:22–107` | Reuse the released fresh write + strong owned parent/current member + existing legacy child-ID fence. Clean reads may be rolled back; dirty/new/deleted/nested session is refused, not discarded. SQLite BEGIN IMMEDIATE and PG READ COMMITTED/5s lock boundary remain unchanged. |
| `api/routes_profile.py:276–418,421–476` | Add a validated reference-only G3 export helper, counts and note. Existing export research policy/attempts/G2/legacy keys remain. New profile ORM descendants join the existing erase transaction; organization-first/native authority/audit lock order remains. Account erasure stays a read-only dependency, not a reason to add a G3 actor/audit FK. |
| `schemas/result.py:259–313` | Authoritative raw DocumentChecklist input only. Preserve six original lists, exact zero-based occurrences, duplicates, ordered_steps, unresolved/completeness, scope omission and raw source_url. No worker/result schema backfill. |
| `api/routes_preparation_graph.py:109–145,286–335` | Preserve native column/payload checklist reconciliation and identity/finite guards. New narrow G3 authoritative raw adapter duplicates only necessary validation, with explicit parity controls; do not private-import/refactor G1's loader. G1 is called in process with explicit session/principal/profile/result IDs only for currently owned approved/maybe authorized targets. |
| `domain/preparation_graph.py:361–408`, `schemas/preparation_graph.py:219–231` | Native DocumentAction exposes original items/list names but not numeric source indices; its key excludes claim_ids but retains source_url. G3 cannot guess indices or use that key as its semantics digest. Attach native G1 identity only for the actually unambiguous projected occurrence set. |
| `api/routes_shared_route.py:200–228,764–804,975–998` | Use public read_shared_route/read_shared_route_revision explicitly in process, not an HTTP self-call/private loader/export-sized history scan. Keep native receipt validation, safe status and current/history anti-torn-head behavior. GET/Today must not preview/save/allocate. |
| `api/routes_preparation.py:81–113,196–277,472–479` | Consume public v1/v2/access reads; observe persisted row revision and raw typed sidecar identity separately. V1 remains its native today-based projection. V2 keeps saved refs/dates despite refreshed GET metadata. Access is distinct from research display and own review availability. |
| `DocumentsScreen.tsx:25–61,190–227` | Existing marks are browser-only result::name booleans, not accepted task states. Add own case server records independent of loaded run/checklists. Preserve raw old marks as explicit import candidates; stable task IDs carry server accepted self-reports. |
| `ApprovedScreen.tsx:14–36,89–119` | Shortlist approved/maybe/rejected remains its own decision ledger. Add own applications/declarations separately; the early no-results return must not hide existing own application history. No “approved ⇒ submitted/offer” conversion. |
| `HomeScreen.tsx:7–56,71–98` | Existing next-step research/navigation remains. Add an independently degradable own Today read; failure in saved plan/source must retain own tasks/declarations and the existing research navigation. |
| `App.tsx:106–142,478–495`, `PreparationScreen.tsx:46–58,177–194,213–250` | Add the frozen owner/case/epoch/intent-fenced exact LearningTaskRef handoff through App into existing exact-version startLesson/openReview. Current Home passes only ScreenId. Wait/retry exact intent while preparation loads; do not consume it on startLesson's loading/access early return, infer a version or revive on A→B→A. |
| `PreparationScreen.tsx:313–328` | Current local sharedActive presence controls legacy visibility; it is not a durable selector. Consume the G3 accepted/derived selector view separately. A G2 save must not rewrite an existing G3 legacy choice; no second active budget. |
| `client.ts:104–134,146–187`, `applicantStorage.ts:23–73,99–108`, `store.tsx:890–929` | Add typed G3 client methods, case/epoch/intent response matching and dedicated case recovery family. Reuse native owner checks before/after I/O; no bare fetch/global auth refactor. Matching case DELETE ACK adds G3 tombstone/best-effort case cleanup without owner-wide wipe or false complete-purge claim. |
| `main.py:18–33,90–108`, `models/__init__.py:1–51,53–104` | Register the new route/model only. Existing native G1/G2/preparation/security/payment route bodies remain read-only. |

The API map already permits current/events/unsaved binding/import preview, finite UUID+CAS command and own `/api/profiles/{profile_id}/today`. This document does not pick an additional endpoint/method/body or add a route outside that approved map.

## 3. Exact metadata roles and read bounds

Keep these roles distinct; do not call all history through one strict G1 selection or count them as one SQL query.

| Role | Bound and permitted observation |
| --- | --- |
| G3 current/head consistency | One own current/latest metadata statement; genuine absent current+event is revision0, history-only/broken pointer is fixed503. Then one full exact own head receipt: validate row metadata, accepted time, request/self-hash, state digest and head linkage. |
| Older state refs | Exactly event_id/revision/kind in every hashed-state EventRef. At most1,662 distinct refs, chunks≤200/max9 own metadata batches with server-derived affected_refs: application_ids≤20, document_task_ids≤400, active_selector_changed. Metadata proves the own role/record association; it does not certify an older body's self-hash. Own full event/history/export validates the body separately. |
| G3 current target metadata/source | Current union≤20 includes withdrawn/disappeared ApplicationRecord targets and case-personal source bindings. Own run/decision metadata first; only eligible+current research grant can load one G3 source observation per distinct target for that role, reused across its tasks. |
| Raw checklist comparison | Separately bounded by that same G3≤20 union: one authoritative checklist observation per authorized target for this role. Preserve original list/index; compare checklist/proof, item semantics and ordered procedure independently. G2 status alone cannot replace this observation. |
| Selected G2 | Unchanged native≤20 goals, exact public current read and accepted allocation/slot order/ref versions. Reuse its public observation only when its actual manifest/provenance is sufficient; no private loader or manufactured deduplication. |
| Composite Today | At most40 distinct source/reference result IDs across G3/G2. One metadata/token recheck pass across observed components; change yields mixed_revision/needs_refresh and removes contradictory joins/premium slices. Different roles may read the same ID; label component_reads, not atomicity. |
| Replay/history/export | Reference-only accepted own bodies. Old refs outside current G3 union are not_evaluated with safe envelope, no current-source joins. History page size is default20/max100; complete export validates sequence/head and fails503 on mixed read, never silently omits rows. |

Actor metadata is separately server-derived ActorRefV1 using the exact full native user_id+organization_id canonical digest; no first-eight-character uniqueness or physical-student claim. Replay by another currently authorized member returns the original actor/ACK unchanged. State refs never embed receipt_digest, including refs to the new head: preallocate ID → pure typed state → state_digest → receipt → receipt self-hash → atomic current/event write.

The research-locked source branch exposes no NEW source URL/presence/reason/hash/count/scope/name/claim refs; only fixed lock status and old own accepted references. Safe own plan/event revisions are not new premium source revisions. Current authorized comparison can be unknown/changed; it never certifies the prepared file, named-award applicability, waiver or official readiness.

## 4. Native plan adapter precision

The frozen selector is `follow_current_accepted` for g2/legacy_v2/legacy_v1. Its ACK freezes the original observed native identity, while Today explicitly shows the later accepted native head. It writes no schedule or settings.

No stored selector permits the exact derived backward order: own G2 current OR history presence →g2; otherwise raw **non-null** saved sidecar marker →legacy_v2; otherwise saved v1 row →legacy_v1; otherwise none. Database failure/corruption remains selected/unavailable, never fallback or GET backfill.

Important actual seam: native `_learning_view` at routes_preparation.py:203 uses truthiness and can return no snapshot for an empty recorded sidecar. The new G3 persisted-reference adapter must inspect non-null presence and validate the raw typed sidecar before adopting the native read. An empty/malformed recorded object therefore yields legacy_v2/unavailable; it must not be normalized to no plan. Native v2 code stays unchanged.

A v2 persisted digest is not a refreshed GET-output digest; v1 technical revision/full settings digest is not its structural fingerprint (ticks excluded). G2 Today consumes immutable accepted slots without allocator/catalogue replacement. Documents remain workload unallocated/not_estimated. Unsupported assessment/external_resource and bare v1 lesson IDs do not gain a fabricated lesson/version.

## 5. Candidate paths and exact current preimages

Candidate allowlist only; not a source grant. Re-pin all released parent bytes at the later root write-ahead. “ABSENT” was checked with both file existence and symlink existence. Existing tests may be extended only after their own explicit write-ahead; new controls below avoid weakening/replacing native tests.

| Candidate source/test path | Current preimage |
| --- | --- |
| `backend/app/models/applicant.py` | EXISTING `613cdd1db26bf5dd9bc4af39af310b8720a6edec5e2e68a6090a95d59c8d6c28` |
| `backend/app/models/__init__.py` | EXISTING `66ac532bca1fe7fd113f03f5b9ce0db1a809be87136197aac108fd2aeba53c40` |
| `backend/app/main.py` | EXISTING `8922a15d1ddb53237b7b1b7795a49cc688bcbe18338088b042695cb5462d8bb2` |
| `backend/app/api/routes_profile.py` | EXISTING `b12a3a301829cc4f4eed5d8df53c2315efa11e5fb0e05e3ba2d9ead25d5202a3` |
| `frontend/src/screens/DocumentsScreen.tsx` | EXISTING `e7ef0217c19f051c434acb69fb7f2b0ea1883a2228984054747cb8b77abcde9f` |
| `frontend/src/screens/ApprovedScreen.tsx` | EXISTING `0395dc3be1315f4c09defc2e0be85434fad0848b407220fa2903f26cdbe6b89a` |
| `frontend/src/screens/HomeScreen.tsx` | EXISTING `bda406914a413a5371d5299f48aa5dfe6b0fbf3bcfae9b1613bbf25b4be18517` |
| `frontend/src/screens/PreparationScreen.tsx` | EXISTING `52c8c4df92498e8cbe1f52b135f755ea7329aab34cff9e71b0bc8431a8b64bb1` |
| `frontend/src/App.tsx` | EXISTING `293f8aeccb4286660bd1822a3a914a74218b85c4704be1b4fcdf0fda5b031725` |
| `frontend/src/api/client.ts` | EXISTING `f667d2f3b89d64ea42392f9e5bba3a30d04a1a76b2203fa2b4a337a7a8cc6789` |
| `frontend/src/types.ts` | EXISTING `472da567fe598b74f9fe43520b925fdfda6401866ef51f994104b2f5afa71511` |
| `frontend/src/lib/i18n.ts` | EXISTING `08c9bf1ce7a50d289d27424ad007ee83adca5c2f9f4b111c4faae6b50aa12e58` |
| `frontend/src/lib/store.tsx` | EXISTING `81afb3fbe97ccd015d9755bfd1fe4079e57eae8bfd2a48363c308545842f272a` |
| `backend/app/schemas/admissions_actions.py` | ABSENT, including no dangling symlink; candidate only |
| `backend/app/domain/admissions_actions.py` | ABSENT, including no dangling symlink; candidate only |
| `backend/app/models/admissions_actions.py` | ABSENT, including no dangling symlink; candidate only |
| `backend/app/api/routes_admissions_actions.py` | ABSENT, including no dangling symlink; candidate only |
| `frontend/src/lib/admissionsActionsRecovery.ts` | ABSENT, including no dangling symlink; candidate only |
| `frontend/src/lib/admissionsActionsRecovery.test.ts` | ABSENT, including no dangling symlink; candidate only |
| `backend/tests/test_admissions_actions.py` | ABSENT, including no dangling symlink; candidate only |
| `backend/tests/test_admissions_actions_api.py` | ABSENT, including no dangling symlink; candidate only |
| `backend/tests/test_admissions_actions_concurrency.py` | ABSENT, including no dangling symlink; candidate only |
| `backend/tests/test_today.py` | ABSENT, including no dangling symlink; candidate only |
| `frontend/src/screens/DocumentsScreen.actions.test.tsx` | ABSENT, including no dangling symlink; candidate only |
| `frontend/src/screens/ApprovedScreen.actions.test.tsx` | ABSENT, including no dangling symlink; candidate only |
| `frontend/src/screens/HomeScreen.today.test.tsx` | ABSENT, including no dangling symlink; candidate only |
| `frontend/src/App.today.test.tsx` | ABSENT, including no dangling symlink; candidate only |
| `frontend/src/api/client.admissionsActions.test.ts` | ABSENT, including no dangling symlink; candidate only |

Migration candidate family: `backend/migrations/versions/<root-assigned-revision>_admissions_actions.py`. No matching admissions_actions migration filename currently exists in the inspected directory. A concrete filename/revision was intentionally not invented; it must be fixed and absence-checked after G2 release before becoming an authorized path. Add only the accepted current/event tables and their profile FKs/index/unique constraints, including the bounded affected_refs event metadata; no backfill/third table.

Read-only dependencies, not candidate edits: G1/G2 routes/schemas/domains/models, native preparation/calendar routes, preparation_transactions.py, security/tenancy/payments, source/result models/schema, account deletion and global primitives SourceLink. The separate G3 raw-authority ASCII/lexical action-link rule is implemented within the new bounded G3 module/surfaces; original raw source_url stays proof identity, never an ACK/href/error fallback when blocked. No new URL command or destination fetch is added.

## 6. Minimal dependency order after source opens

1. **Freeze exact source allowlist/preimages and migration identity.** New branch/baton/root HANDOFF write-ahead; preserve all accepted G3 documents and released G1/G2/legacy/native bytes. This report is not that write-ahead.
2. **Closed schema + pure domain.** Implement only accepted finite request/state/receipt/ref/actor/link/error/Today forms; canonical finite JSON and closed transitions, independent proof/semantics/procedure identities, typed uncertainty and deterministic Today order. No Session/I/O in domain.
3. **Two models + one additive migration + profile relations/registrations.** Preserve no User/result FK, ORM erase semantics, no data/browser backfill. Gate additive SQLite/PG migration before adopting API behavior.
4. **Owner-first commands/current/events/export.** Reuse native fresh-write fence; UUID replay before mutable gates, new source versus existing personal authority, expected revision/create CAS, atomic event/current and rollback/fresh reconciliation. Add route-local fixed validation privacy. Head/older-metadata integrity precedes dynamic evidence joins. Profile additive export is complete/safe; erase uses existing transaction.
5. **Bounded source/plan adapters + Today.** Strict new bind/award authority, raw occurrence parity and locked suppression; public native in-process readers and separate persisted plan token adapter; one selected workload, one recheck, component failure/mixed view without fallback. Selector/import protocols are the frozen accepted ones, not shortcuts.
6. **Typed browser surfaces and recovery.** Client/types/copy →own documents/applications independent of run →Home Today →exact App/preparation handoff. G3 case index/tombstone and exact UUID recovery; explicit non-destructive old-mark import; only matching delete/logout ACK cleanup. No auto write/declare on mount/navigation.
7. **Focused →physical/native →full release gates by root.** Qualify actual applied bytes and new migration without widening old provider/label/STOP scope. External source review/proposed tests do not inherit G2's runtime outcome.

These steps can be separately bounded root increments, but the usable release requires all its included vertical-path controls. A schema/model-only increment is not durable document/application/Today delivery.

## 7. Meaningful future acceptance controls — NOT_AUTHORED / NOT_RUN

| Control | Required observable result / native test seam |
| --- | --- |
| Exact identity/source binding | Same-list duplicates and unique cross-list projections retain raw list+index and actual G1 ref only when real; column/payload disagreement or malformed source cannot become empty success. URL absent/present/value, claim-proof-only, item constraints and ordered_steps changes produce separate reasons; unknown named-award relation remains unknown. |
| Personal authority versus new target | Own self-report/correction/declare submission remains accepted with missing/rejected/locked historical result, no foreign premium SELECT. New/replacement target still requires own approved/maybe; source branch checks grant before payload. Prospective union19 race cannot reach21; at20 existing-ID binding remains allowed. |
| Actual states/provenance | Browser tick is not server progress, prepared/sent/received/not-needed remain reported states; planning/preparing do not silently set submitted. Explicit submission/withdrawal/correction creates immutable applicant_declared receipt with official_verification=not_performed. Trusted actor collision/replay controls use full IDs internally. |
| UUID/CAS/transactions | Migrated physical file SQLite/private PG two connections, present/absent head, same UUID equal/different body and different UUID same revision; real event insertion failure rolls back current; dirty incoming session preserved/refused; native bounded lock wait and release; fresh same-UUID replay after uncertain response. Reuse approved prep_lab, SQL capture/race patterns from test_shared_route_api.py/test_preparation_write_concurrency.py, not mocked concurrency or new network exceptions. |
| Current/event corruption | History-only/missing current; wrong head/profile/revision/accepted time/digest; exact own old event reused for another record/role; extra digest in state ref; outer rehash with inner mismatch: fixed503, no repair/GET DML/body omission. Older metadata checks do not assert old self-hash validation; full own history/export does. At-cap1662 uses max9 bounded metadata batches. |
| Additive export and erase | Complete ordered receipts/counts plus unchanged attempts/legacy/G2/research policy; real interleaving accepted write causes safe503 mixed export. Case/sole-member account erase and shared-member retention both orders with write preserve sibling/isolation; no User/audit FK dependency. Migration creates only two tables without backfill. |
| Selector/Today budget and failures | g2/v2/v1 observed token conflict/replay; g2 new head shown with unchanged selection ACK; explicit legacy stays legacy after G2 save. History-only broken G2 pointer and empty v2 sidecar remain selected/unavailable, no fallback. Plan/source failure keeps personal records. One accepted minute ledger, original slot order, entered/uncertain dates and no guessed duration/certificate deadline. |
| Bounded/mixed source reads | One G3 source observation and one raw-checklist role per authorized current target, separate native G2 read≤20/composite≤40; no whole historic G1 call, source history scan, quota/provider/allocator. Access/head change at single recheck clears earlier premium slices and contradictory joins. |
| Browser import/recovery/cleanup | Literal true only, version/time unknown; explicit exact task mapping50 max/all-or-nothing. Import ACK leaves original raw old marks, including false→true concurrent edit. Owner/case/epoch A→B→A/foreign corrupt index/late ACK, exact original UUID/body retry, case tombstone/storage residual and sibling preservation; no automatic hydrate/write or complete legacy-purge claim. |
| Exact Today action/navigation | Saved lesson version differs from latest; click requests exact saved version, own review exact UUID/version after expiry. Waiting/loading intent is not consumed early; wrong/late response/new click/navigation/logout/delete/case change rejected before paint. Unsupported refs/bare v1 lesson ID cannot dispatch a guessed course. Existing research navigation survives Today failure. Real API/browser reload+second context proves durable server state independently of local ticks. |

Native DocumentsScreen recovery/ownerMerge/privacy and App.preparation tests are retained regression anchors. Their current source presence is not a G3 PASS receipt. The first G3 source proposal should add the focused cases listed above rather than mirror implementation or merely count tests.

## 8. Exact read pins and preserved design

### Current native read pins

| Source path | SHA-256 |
| --- | --- |
| `AGENTS.md` | `a28ea0f3c275f54e431169082e27aec5f156d048d30ad617c8a21d0021cc2f69` |
| `backend/app/api/tenancy.py` | `34557c1bae4f9cc36413cfd952a001342df9a35a1c5ecf5ad19bd83cf121363f` |
| `backend/app/security.py` | `e8359112da7f35d7952049ed3e01066e0b6f41cd051052f5654ac740458bc816` |
| `backend/app/api/preparation_transactions.py` | `ecbf9c12c95d6a178bf6d1c8c2aca8dcc3b5522e8b0aa4da64e465c99c68d2d7` |
| `backend/app/models/base.py` | `dfab71868df728ce3dc74d01f9d547512eb8076795207e113425a1eb1b786b62` |
| `backend/app/models/applicant.py` | `613cdd1db26bf5dd9bc4af39af310b8720a6edec5e2e68a6090a95d59c8d6c28` |
| `backend/app/models/shared_route.py` | `a1cf969acfde2dea68c42c98edd8ad99fa8ebc5b18633f6bf1bdbf0bc9ab8e20` |
| `backend/app/models/study_schedule.py` | `087ccef37010f3eeddce5329856832de1d4aeea796cba48a52e439cf0ca03626` |
| `backend/app/models/__init__.py` | `66ac532bca1fe7fd113f03f5b9ce0db1a809be87136197aac108fd2aeba53c40` |
| `backend/app/main.py` | `8922a15d1ddb53237b7b1b7795a49cc688bcbe18338088b042695cb5462d8bb2` |
| `backend/app/api/routes_profile.py` | `b12a3a301829cc4f4eed5d8df53c2315efa11e5fb0e05e3ba2d9ead25d5202a3` |
| `backend/app/api/routes_account.py` | `50c4bf6cc7da8d72596dd87c9acff858894a12fce441ea2273a3b6c460697521` |
| `backend/app/api/routes_preparation.py` | `11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2` |
| `backend/app/api/routes_preparation_graph.py` | `7ddff09f9ef9601571568d51c3701e901166193de1801280b2901d067a0ef7c9` |
| `backend/app/api/routes_shared_route.py` | `fec7d50d7e29cbebea1d1d46bb2245ccb129f216974ba281fd2550013bbe37f9` |
| `backend/app/schemas/result.py` | `f4eab02362d8bcdcec72bc1f16e2636f7abe7c0844b72b18bb4eac94f3927974` |
| `backend/app/schemas/preparation_graph.py` | `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249` |
| `backend/app/domain/preparation_graph.py` | `2ba1488a582a4a8e4a37d747a5a4e4d1d44ceb70c980ad50195438dae3b35c09` |
| `backend/app/schemas/shared_route.py` | `50c2dca8ad250f3d12fc9645a6307ac4dd05bf05a61c79c17bbf925b4c8042e2` |
| `backend/app/schemas/learning_schedule.py` | `a5c26ea689d67aa68cf46936adc5057c854613a99691259282ba5ca64ea684b6` |
| `backend/app/domain/learning_schedule.py` | `f5fb507796e5c7f6d4704ffff6f218fb8a59a35b79bf1fc659212544628e2e62` |
| `backend/migrations/versions/c3e71d902023_shared_route.py` | `309bd8494deb09d2e6afdaa6326809067aac802ce7f77255f64bdb8b2c5afd23` |
| `frontend/src/screens/DocumentsScreen.tsx` | `e7ef0217c19f051c434acb69fb7f2b0ea1883a2228984054747cb8b77abcde9f` |
| `frontend/src/screens/ApprovedScreen.tsx` | `0395dc3be1315f4c09defc2e0be85434fad0848b407220fa2903f26cdbe6b89a` |
| `frontend/src/screens/HomeScreen.tsx` | `bda406914a413a5371d5299f48aa5dfe6b0fbf3bcfae9b1613bbf25b4be18517` |
| `frontend/src/screens/PreparationScreen.tsx` | `52c8c4df92498e8cbe1f52b135f755ea7329aab34cff9e71b0bc8431a8b64bb1` |
| `frontend/src/App.tsx` | `293f8aeccb4286660bd1822a3a914a74218b85c4704be1b4fcdf0fda5b031725` |
| `frontend/src/api/client.ts` | `f667d2f3b89d64ea42392f9e5bba3a30d04a1a76b2203fa2b4a337a7a8cc6789` |
| `frontend/src/types.ts` | `472da567fe598b74f9fe43520b925fdfda6401866ef51f994104b2f5afa71511` |
| `frontend/src/lib/i18n.ts` | `08c9bf1ce7a50d289d27424ad007ee83adca5c2f9f4b111c4faae6b50aa12e58` |
| `frontend/src/lib/store.tsx` | `81afb3fbe97ccd015d9755bfd1fe4079e57eae8bfd2a48363c308545842f272a` |
| `frontend/src/lib/applicantStorage.ts` | `0a3230d223e5dbfc1ead6dbece478ce54c9ec6bc557493115716e5709818fd0e` |
| `frontend/src/components/primitives.tsx` | `ef745e6002023398e5d69f6e6227c719d879bc10997c94f179b15d67747a676b` |
| `backend/tests/test_shared_route_api.py` | `84c166681851a448e24aaeb14bcdab4587777c47e3e137027760130c9fcfeee8` |
| `backend/tests/test_preparation_write_concurrency.py` | `0329d49de0bafcd23bebd08b52cd7826bb4836be742b31b7df6b89d6dc387d99` |
| `frontend/src/App.preparation.test.tsx` | `406ad762023db5f3d55e71024c84ee27563358b622e4ef08da202c6284f3a490` |
| `frontend/src/screens/DocumentsScreen.recovery.test.tsx` | `c36a17a9af545ca187e7f257e37f5f01538c0085b6b7b027bc39cc071e338643` |
| `frontend/src/screens/DocumentsScreen.ownerMerge.test.tsx` | `1d80a170783b8488925b21aa1a10699a102b07fa4a3782348365b5b661f3e308` |
| `frontend/src/screens/DocumentsScreen.privacy.test.tsx` | `d35981bde8c65cb796ed629efadd9f28110a57aeabce62bbb24c95440451c6e5` |

### Accepted frozen references

| External design/reference | SHA-256 |
| --- | --- |
| `ROOT_G3_FINITE_CONTRACT_ACCEPTANCE.json` | `f9ca10267d61139eb0dc5d48a854ff0f639815d75e27f69eaf3b0a8c04073d21` |
| `ROOT_G3_DESIGN_ACCEPTANCE.md` | `81fc914fd0756436ebd3974ad7847131e90c5e19b64121fb2733b5fd36d8f70d` |
| `proposals/g3-design/G3_CONTRACT_DESIGN_V2.md` | `7b3857d7a273e3bbb3b38644101a03fd41159bbc121b406b3a76ef929f3edbbb` |
| `proposals/g3-design/G3_IMPLEMENTATION_DEPENDENCY_MAP.md` | `81171a86f90c11e19438efe760ad9e0cd4fcbc394c036a3ec7f9bb1143537bdb` |
| `proposals/g3-design/G3_NATIVE_BINDING_ADDENDUM_FINAL_V2.md` | `0c15b69b2cdb9347a1f30501822aeff4cf913f3e12d08635bdd1d30a7b525474` |
| `proposals/g3-design/G3_FINITE_CONTRACT_FREEZE_PROPOSAL.md` | `f5acdae226110346798aca2ab8e51a40894e902adc5e2d4eb71b5c85740d839a` |
| `proposals/g3-design/G3_EVENTREF_AND_RAW_AUTHORITY_ADDENDUM.md` | `9292ca3db7edb0a7423a97a8760da579bebf1cc68534d4f7282b2a1a50e51e8e` |

All five sealed V2/map/final-v2/finite/EventRef design hashes matched their retained expected values. This report introduces no changed contract or implementation decision; it identifies the required application seams under that existing freeze.

**Final boundary:** source remains closed until the root's released parent/new branch/baton/exact write-ahead. No source, helper, Git, HANDOFF, database or runtime changes were performed. No production, search recall, pedagogy, official receipt/readiness or product-completion proof is claimed.

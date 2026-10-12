# G2 implementation dependency map — read-only planning

**2026-10-12 · DESIGN/READ-ONLY MAP · NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** This locates existing seams for a later, separately authorized G2 source proposal. It does not amend the accepted-direction [SHARED_ROUTE_PERSISTENCE_SPEC_V2.md](SHARED_ROUTE_PERSISTENCE_SPEC_V2.md) or sealed [TYPED_CONTRACT_DESIGN_V2.md](TYPED_CONTRACT_DESIGN_V2.md), and it does not approve an implementation. Current G1 source/runtime is owned by root. No application source, helper, test, Git or runtime was changed, imported or executed.

Read-only checkout: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`. Design pins: persistence v2 SHA-256 `27bc906301708c604c723e1a1d2fdb6ae79f454750871b4d6f82a98cd4728de3`; typed v2 SHA-256 `3916138d910830dfb0b484f2a562a488889798985f11ac2abdb2ffcd7282f37c`.

## 1. Existing read/write seams to bind, not copy

| Need | Exact existing seam | G2 use and boundary |
| --- | --- | --- |
| Case owner | `api/tenancy.py:12–28` `owned_profile(session, profile_id, principal)`; `security.get_principal` | First operation on every new current/history/preview/save/export route. Generic 404 before UUID, attempt, result or receipt lookup. Do not use a supplied case ID or cached frontend identity as authority. |
| Preparation term | `payments/preparation.py:15–43` `preparation_access(session, organization_id)`; current route's private `_require_access` at `routes_preparation.py:448–457` | New preview/save must check the same started active/exhausted term without consuming research quota. Saved GET/history, accepted UUID replay and own attempt review remain readable after term expiry. Reuse the public payment decision; do not import the route-private `_require_access` or fork term arithmetic. |
| Research display entitlement | `payments/entitlements.py:18–43` `has_full_access(session, organization_id, profile_id)` | Separate from preparation term. Check before any premium G1 result/claim/scope load. Locked G1 projection has only safe result IDs/decisions and null source-manifest digests, so a G2 receipt must not copy names/proofs or compute a new premium digest from hidden rows. |
| G1 ordered owned selection and source identity | `api/routes_preparation_graph.py:60–76` private `_selection`; public `preparation_graph` at `:284–425`; `schemas/preparation_graph.py:283–303` `ProgrammeSourceManifest` and `source_fingerprint` | G1 accepts 1–20 exact ordered owned `approved`/`maybe` IDs; G2 adds its own 2–20 bound. New preview/save needs the **whole** G1 result in order and its manifest/fingerprint recheck; saved GET first probes old IDs individually and calls current G1 projection only for currently owned, eligible, entitled slices. Do not copy `_selection`, `_source_slice`, claim loading or snapshot hashing into G2. The only assembled native source read today is the public route function; a direct in-process adapter versus a reviewed shared-service extraction is a source-proposal choice, not a design claim that a public service helper already exists. |
| Legacy shared technical revision | `models/study_schedule.py:17–36` `StudyScheduleRow` (one row per profile, `revision > 0`, nullable `learning_path`); `routes_preparation.py:105–163` v1 GET/PUT and `:268–422` v2 GET/preview/PUT | Both legacy writers use the **same** row/revision. G2 anchor reads revision `0` when no row, otherwise the actual row revision; an in-flight tick-only legacy PUT can make a new G2 save 409. G2 adds separate tables, never overwrites `settings`, `learning_path` or old task IDs. |
| Legacy structural identity | `domain/learning_schedule.py:22–31` `settings_fingerprint(ScheduleSettings)` sorts study days and excludes `completed_task_ids`; `schemas/study_schedule.py:35–145` strict settings/write bounds | This is the existing normalization for G2's legacy structural fingerprint when the row validates. A tick-only revision changes the technical anchor but not the accepted-plan structural status. If the saved legacy JSON cannot validate, saved G2 GET reports structural `unknown`; it must not erase/rebuild G2 or invent an empty legacy plan. G2 personal optional targets cannot be squeezed through required one-exam `ScheduleSettings.target_scores`. |
| Current exact lessons | `preparation/learning_pack.py:41,469–536` `PACK_VERSION`, `TRACK_ORDER`, `pack_catalogue()` and `lesson_dispatch(id, version)`; `preparation/catalogue.py:26` starter `CONTENT_VERSION`; `schemas/learning_schedule.py:14–51` `LessonRef`, `AttemptReviewRef`, `LearningUnit.planned_minutes=20` | Three tracks, nine real exact-version lessons/39 questions: IELTS Reading 4, SAT Math 3, SAT Reading & Writing 2. Use `pack_catalogue()` summary versions and `TRACK_ORDER`; `lesson_dispatch` checks exact content availability. The 20 minutes is an existing **planning allocation**, not teaching-time evidence. No new content, score or mastery state. Do not call one-exam `build_learning_schedule` to allocate G2's two-exam common budget. |
| Exact own old review | `models/study.py:17–43` unique `(profile_id, client_attempt_id)` with exact lesson/version; `routes_preparation.py:559–594` `review_attempt`; `:426–445` `attempt_view` | Resolve a review by profile + attempt UUID and compare exact lesson ID/content version; the owned review GET has **no new-term gate** and returns the unchanged attempt receipt even if `lesson_dispatch` cannot load its old version (`lesson=None`). An old own review need not match current catalogue lessons. G2 may date that exact review if its own receipt resolver is available; it must not import v2 `save_learning_path`'s `:371–394` validator, which requires a matching current lesson unit. No substitution/new lesson. |
| Export and deletion | `routes_profile.py:268–402` `export_profile`; `:404–427` `delete_profile`; `models/applicant.py:40–53` ORM delete-orphan for runs/attempts/schedules; `models/__init__.py` model registration | Add G2 current/reference-only history to **owned** export with counts/note, preserving existing `study_schedules` and attempts/result/claim shapes and owner-only export policy. New current/history relationships need ORM cascade for SQLite and PG, not only FK `ON DELETE`. Existing profile/account deletion paths should delete the two G2 rows for that case without touching a sibling. |
| Frontend API/case fence | `frontend/src/api/client.ts:134–184` `requestWithHeaders` checks `currentApplicantOwner` before and after responses; `PreparationScreen.tsx:44–121` case-key remount + `isCurrent()` | Add typed G2 calls through existing `request`, never bare `fetch`. New panel captures owner/profile/caseEpoch/intent and verifies body `profile_id`, ordered IDs, revision and preview fingerprint before accepting GET/preview/PUT ACK. The existing callback is `PreparationCase.openLearningTarget(ref)` at `PreparationScreen.tsx:221–228`; exact lesson goes to `startLesson`, exact `attempt_review` to `openReview`, which independently checks own attempt/version and works after term expiry. |

## 2. Exact frontend opening seam

`PreparationScreen.tsx:290–291` mounts `StudySchedulePanel` only in `mode === 'schedule'` and passes `onLearningTarget={openLearningTarget}`. `StudySchedulePanel.tsx:261–262` mounts `LearningSchedulePanel` only when a legacy `record.schedule` exists; its task button calls `onTarget(ref)` (`LearningSchedulePanel.tsx:105–117`). A new G2 panel may reuse **the parent callback** and the existing `LearningTaskRef` discriminant, but it must render independently of `record?.schedule`: a fresh owned case can opt into G2 without a v1 row. `startLesson` (`PreparationScreen.tsx:158–174`) correctly requires preparation access and exact returned lesson/version; `openReview` (`:191–214`) has no term gate and validates own attempt/version. Preserve both behaviors. `validLearningRef` (`LearningSchedulePanel.tsx:13–23`) checks exact reference form, but backend ownership is still required.

The current `PreparationScreen` shortlist prop is `results.filter(approved|maybe)` (`:44–57`), and `store.tsx:363–405` loads only the latest run when switching a case. G1 server selection can cover any run owned by that case (`routes_preparation_graph.py:296–316`). **Integration conflict:** relying only on that prop silently hides an eligible older-run result from G2's 2–20 ordered selection and makes a saved older selection hard to review. A future source proposal must state its owner-verified candidate source/pagination or explicitly scope the UI; it cannot use local labels or export as authority. `listRuns(profileId, limit)` in `client.ts:310–313` supports a bounded run list, with server offset in `routes_research.py:316–360`, while `api.results(runId)` is entitlement-shaped/truncated. Selection remains server verified by G1 regardless of how candidates are shown.

## 3. Concrete integration conflicts to resolve in the later source review

1. **Shared legacy CAS across different tables.** G2 v2 promises technical revision disagreement yields 409 before a new receipt. Legacy v1/v2 update `StudyScheduleRow` while G2 writes a separate current row. A read of revision N followed by a G2 insert/commit is not automatically atomic against an interleaved legacy update, particularly on PG read-committed and when no legacy row exists. The source proposal needs a verified lock/transaction/recheck strategy for both present and absent legacy rows and a two-session SQLite/PG case; do not claim the G1 source recheck establishes this legacy CAS guarantee. Accepted G2 design's broader caveat about non-atomic research source writers remains intact.
2. **No public G1 source-loader service currently exists.** The safe full source assembly lives inside `preparation_graph()` with private `_selection`, `_source_slice`, `_stored_fields` and payment guard. G2 cannot safely rebuild a parallel source snapshot or merely trust the client preview. Later choose an explicit reuse seam and record its source dependency; for saved GET, avoid strict whole-selection G1 on historical rejected/missing IDs. Recheck near commit, report read-time change later, and do not promise one atomic source writer.
3. **Old review versus v2 validator.** V2 `save_learning_path` requires each review to match a current `plan.lessons` unit; G2 typed v2 explicitly permits an own old-version attempt. Use the owned attempt/`review_attempt` semantics, not v2 save validation or latest-20 progress as a complete historical review inventory. `preparationProgress(...limit=20)` is a display sample, not an ownership database query.
4. **Empty legacy case and frontend mounting.** V2 preview requires an existing v1 row/revision ≥1 and `LearningSchedulePanel` is hidden without `record.schedule`. G2 creates its own row/revision 0→1 and may have legacy anchor `(0,null,null)`; do not create a fictional v1 schedule, required scores or completed IDs to open G2. The frontend panel must be independently mounted and its active-budget status must explicitly supersede legacy only after G2 save ACK.
5. **Source and term redaction are independent.** `has_full_access` can stay true after `preparation_access` ends. Conversely a live preparation term cannot authorize premium requirement details. Preview/save uses term + strict G1 owned selection; saved read/replay survives expiry; per-goal current evidence appears only through current research entitlement. Locked G1 `ProgrammeSourceManifest` has null result/evidence digests (`schemas/preparation_graph.py:283–288,411–441`).

These are implementation decisions/gates, not changes to the accepted G2 domain contract. No claim of G2 availability, migration success or test pass follows from this map.

## 4. Finite later path boundary: 17 core paths, then 2 native paths

The typed design's §6 allowlist is **17 core paths** when its seven backend new files (including two tests), two frontend new files (including one test), four existing backend wiring files and four existing frontend wiring files are counted. The two existing native E2E files form a later gate (19 paths total if included). A new write-ahead must pin preimages again; this map has not created any of these files.

| Core path relative to checkout | Planned dependency only |
| --- | --- |
| `backend/app/schemas/shared_route.py` **new** | Strict DTO, exact existing `LearningTaskRef`; no legacy schema edit. |
| `backend/app/domain/shared_route_allocator.py` **new** | Pure shared-capacity allocator over pinned catalogue/owned refs; no DB/clock inside. |
| `backend/app/models/shared_route.py` **new** | Current/history receipt rows, profile FK, revision/UUID uniqueness. |
| `backend/app/api/routes_shared_route.py` **new** | Owned preview/save/GET/history, safe per-goal status probe and CAS. |
| `backend/migrations/versions/<new>_shared_route.py` **new** | Single additive successor to `b5c81d9e2022`, no backfill. |
| `backend/tests/test_shared_route_allocator.py` **new** | Later meaningful pure allocation cases. |
| `backend/tests/test_shared_route_api.py` **new** | Later owner/CAS/replay/expiry/export/delete/SQLite-PG cases. |
| `frontend/src/screens/SharedRoutePanel.tsx` **new** | Opt-in saved route, explicit ordered choices, read/preview/save fences. |
| `frontend/src/screens/SharedRoutePanel.test.tsx` **new** | Later component behavior, not a duplicate of implementation logic. |
| `backend/app/main.py` | Register only new router. |
| `backend/app/models/__init__.py` | Register new ORM rows. |
| `backend/app/models/applicant.py` | Add two delete-orphan relationships. |
| `backend/app/api/routes_profile.py` | Add own current/history export and note/count. |
| `frontend/src/types.ts` | Add G2 DTOs without changing v1/v2/G1 shapes. |
| `frontend/src/api/client.ts` | Add owned G2 methods through existing owner-fenced `request`. |
| `frontend/src/lib/i18n.ts` | RU/EN/KK fields/statuses. |
| `frontend/src/screens/PreparationScreen.tsx` | Mount independent G2 panel, reuse `openLearningTarget` and case key. |

Later native test paths: `frontend/e2e/preparation.spec.ts`, `frontend/e2e/auth-journey.spec.ts`. Existing `routes_preparation.py`, `routes_preparation_graph.py`, `StudySchedulePanel.tsx`, `LearningSchedulePanel.tsx`, `catalogue.py`, `learning_pack.py`, LMS/attempt schemas/domain and payment helpers are **read seams only** for this count. If the G1 service extraction or stronger legacy lock needs one of them changed, it is a concrete allowlist expansion requiring root review/write-ahead, not a hidden edit.

Migration predecessor: static `b5c81d9e2022_learning_calendar.py` has `revision = "b5c81d9e2022"`, `down_revision = "a9e5c14d2021"` and adds only nullable `study_schedules.learning_path`; no source migration in the inspected tree names `b5c81d9e2022` as `down_revision`. Its SHA-256 is `2c9e19365c4ca2835b48094191916667360fe2af94142148c36f60f9e921cad9`. Verify the actual Alembic head again in the later source gate; none was executed here.

## 5. Source pins for later preimage checks

| Source | SHA-256 at this read |
| --- | --- |
| `backend/app/api/tenancy.py` | `34557c1bae4f9cc36413cfd952a001342df9a35a1c5ecf5ad19bd83cf121363f` |
| `backend/app/api/routes_preparation.py` | `11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2` |
| `backend/app/api/routes_preparation_graph.py` | `7ddff09f9ef9601571568d51c3701e901166193de1801280b2901d067a0ef7c9` |
| `backend/app/domain/learning_schedule.py` | `f5fb507796e5c7f6d4704ffff6f218fb8a59a35b79bf1fc659212544628e2e62` |
| `backend/app/models/study.py` | `cd48802f039ef76f507328af22eb27735fab56ea5a25071bdca522053af59acc` |
| `backend/app/models/study_schedule.py` | `087ccef37010f3eeddce5329856832de1d4aeea796cba48a52e439cf0ca03626` |
| `backend/app/preparation/learning_pack.py` | `778b94d392b89406e4ddd13726a25d91a808114e2026064289f12500e02b7aae` |
| `backend/app/schemas/study_schedule.py` | `259a752f19438af1ce7e72e1659844e314cca3c532ac30e0143649855b63218f` |
| `backend/app/schemas/learning_schedule.py` | `a5c26ea689d67aa68cf46936adc5057c854613a99691259282ba5ca64ea684b6` |
| `backend/app/schemas/preparation_graph.py` | `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249` |
| `backend/app/main.py` | `b83563f60e08ccb9ed2522463bca6e1bc94bb31dc2c82f13398cdf59f2f8ad9c` |
| `backend/app/models/__init__.py` | `d5033b970b7ea2f3187789ed079f292b5cf3ba93f1156575c68de09c60db3e14` |
| `backend/app/models/applicant.py` | `54086f053fbf2db1b4a1471b9dac5595191f425ae2d6c6fe61d7744f1397caeb` |
| `backend/app/api/routes_profile.py` | `d9bd87d528f7c8545c3b6e1875d7924f09bb4bb2e63f5cf18db022e0fe0c235a` |
| `frontend/src/screens/PreparationScreen.tsx` | `41cb8a346dac441f536b713ad15d90f150f1398695fc3a37f521eda128c03cf6` |
| `frontend/src/screens/StudySchedulePanel.tsx` | `1d7de8fafb1d36ecdad11b646030f0e21ad7b9a87318def05c235853e9f0ce24` |
| `frontend/src/screens/LearningSchedulePanel.tsx` | `f61dbb1b548e983970ac6cb0d41269e01d806183897274699ecd752ccb633936` |
| `frontend/src/api/client.ts` | `8b27a74a87b1ee46307a6b2c8e24cfb9ddddd96d949377dd20c863c94d5c74e3` |
| `frontend/src/types.ts` | `1db0143b20def355da62687d290f34628b7a0d4f1beeab8415689caf20f60ca1` |
| `frontend/src/lib/i18n.ts` | `9167029fc364fadec35a3ecfd91c690e59bae24749fe29c1c184c72a471dc6f4` |

Contract bounds to preserve at adoption: G2 2–20 ordered result IDs; one or two explicit choices from `ielts_academic`/`digital_sat`; three existing tracks, at most nine exact lessons and 39 questions; 0–400 explicit own reviews; weekly 30–1260 minutes in **one** ledger, daily cap 180, lesson planning allocation 20, review duration explicitly chosen; dates horizon ≤365 days in an IANA timezone; legacy expected revision 0–2,147,483,646; exact lesson ID ≤80 and content version ≤40. These bounds are personal planning limits, not official eligibility, proven workload or mastery.

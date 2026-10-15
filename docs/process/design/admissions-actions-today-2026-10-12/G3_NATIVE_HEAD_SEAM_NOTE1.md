# G3 native preparation-head seam — finite source note 1

Status: **SOURCE_ONLY / PLAN_ONLY / NOT_APPLIED / NOT_IMPORTED / NOT_RUN / NOT_ACCEPTED**.
Inspected 2026-10-13 05:39:24 UTC. Root decides any additional source grant.
No source, Git, runtime, database, provider or stopped-workflow operation was performed.

## Finding: narrow the gap, then finish selection

The earlier UI plan §8 point 4 remains an immutable predecessor. Its gap applies to **alternative legacy origins**, not every native origin. A usable one-selected-plan workflow should expose selection using the existing command; it need not remain read-only.

| Existing response | Exact G3 head already available? | Source-bound limit |
| --- | --- | --- |
| GET /api/profiles/{profile_id}/today | Yes: active_plan.current_observed_head, for the selected/derived origin, when readable. | Does not enumerate alternate origins; unavailable/mixed views are not authority to choose another plan. |
| GET /api/profiles/{profile_id}/admissions-actions | Only state.active_preparation.observed_head from the immutable accepted selector. | This is the originally observed head, not today's current accepted head after later native writes. |
| Native shared-route GET, current.view.receipt | All G2HeadV1 fields are already server supplied: profile_id, revision, client_write_uuid, snapshot_digest, allocation_digest, accepted_at. | Copy those fields plus the fixed existing origin/schema literals; do not compute a new digest. Historical-revision GET is not a current-head replacement. |
| Native schedule GET | No complete LegacyV1HeadV1. | Revision/settings are present; saved_settings_digest and exact server settings_fingerprint are not supplied. UI hashing would duplicate a private contract. |
| Native learning-path GET | No complete LegacyV2HeadV1. | It supplies revision, legacy_fingerprint and draft.fingerprint, but not persisted_sidecar_digest. Its returned snapshot is also a mutable read projection. |
| Current and sealed foundation client APIs | No explicit-origin head GET. | Foundation has NativeHeadV1 and isNativeHeadV1; reuse them. No new head schema or browser validator is needed. |

Native evidence:

- schemas/admissions_actions.py:472–502 declares the existing three discriminated head types.
- routes_admissions_actions.py:1326–1529 constructs the exact heads in _read_plan; 1368–1376 copies G2 fields; 1414–1422 hashes the persisted v2 snapshot; 1472–1477 hashes saved v1 settings.
- routes_preparation.py:90–103 returns v1 settings/generated schedule; 198–264 refreshes v2 as_of, diagnostics, overdue, submitted-attempt evidence and availability. Hashing that returned v2 JSON cannot reproduce the persisted-sidecar digest reliably.
- frontend/src/types.ts:943–947 and 1006–1028 expose legacy and G2 responses; native client.ts:460–496 exposes their GETs.
- Foundation types/admissionsActions.ts:85 and 331–342 already define/validate the exact NativeHeadV1.

## Minimum additive seam for root decision

Add one owned, read-only endpoint **inside the current G3 router**:

GET /api/profiles/{profile_id}/admissions-actions/preparation-head?origin=g2|legacy_v2|legacy_v1

Return the existing **s.NativeHeadV1** directly. No new wrapper/schema, presence enumeration, allocation, mutation, clear/none command or alternate-plan body. Origin is explicit and closed; SafeActionRoute already provides input-safe validation errors. The router is already registered in main.

Reuse:

1. _owned_read at routes_admissions_actions.py:1533 (owned_profile plus current actor/member authority), session.no_autoflush and terminal own authority recheck. Do not commit, rollback, acquire a writer fence or flush unrelated dirty state.
2. _native_markers at965 for one bounded before/after persisted-native metadata token comparison. No loop/coherent-read claim; a changed token refuses the observation with the existing safe plan_head_changed409.
3. The existing exact head constructors and native pure typed snapshot validation. There is **no isolated head-only reader today**: factor only that saved-head portion into a G3-private helper if root permits, sharing the same origin/digest constants with _read_plan rather than duplicating them in UI.
4. For v1/v2, use _legacy_row at1265, raw finite checks and the persisted ScheduleSettings/LearningPathSnapshot. Preserve raw non-null v2 marker semantics: {} is not absent and must not fall back to v1.
5. For G2, retain the native current/latest-history compound observation and exact matching accepted history guards. routes_shared_route.py:149–233 shows those controls. _g2_goal_ids at2246 explicitly says its snapshot/header checks are **not** that full guarded validation; do not treat it alone as an accepted-head oracle. A narrow G3-local head-only reader must preserve those guard semantics without importing/refactoring private G2 loaders or querying source/claim/content bodies. SharedRouteWriteReceiptV1 already validates the immutable reference receipt.

**Do not just call _safe_plan or _read_plan and discard their output.** G2 _read_plan calls public read_shared_route, whose _view reads premium G1 evidence and practice availability (routes_shared_route.py:694–760). Legacy _read_plan calls public read_learning_path/read_schedule, refreshing practice evidence/building a display schedule. Those are unnecessary for a head-only GET and violate the requested no-premium-body/no-allocation seam.

Missing requested saved plan retains existing plan_unavailable422; malformed/inconsistent persisted heads retain existing conservative plan_unavailable/plan_unreadable handling, with no forged revision-zero or fallback. Actor revocation401 and missing/foreign case404 remain native-safe. Own reference-only reads need no active preparation/research term. Reading a valid head is not an applicability/readiness/access claim.

## UI selection remains the existing write contract

The UI obtains the requested-origin exact head, displays the original/current origin and revision, then explicitly journals and posts the existing select_active_preparation command with policy=follow_current_accepted, fresh G3 expected_revision and new UUID. No hash derivation, selector autosave, current-plan fallback, auto-clear, private sidecar copy or second budget.

The native write already re-observes and compares the exact head (routes_admissions_actions.py:1735–1741; domain/admissions_actions.py:537–553), and compares the persisted metadata token before acceptance at1866–1904. A native save/tick between GET and POST is a real plan_head_changed409; review a newly read head as a new intent. Exact previously accepted UUID replay remains before current/source/plan reads. Today follows the selected current accepted native head after later saves.

## Finite meaningful controls for the bounded extension (NOT_AUTHORED / NOT_RUN)

1. Owned v1/v2/G2 exact heads equal the native server constructors; explicit alternate-origin head is readable even when Today follows a different valid origin.
2. v2 display metadata/day/evidence refresh does not change the saved-sidecar head; a native persisted revision/tick does change the observation.
3. Raw v2 {} and G2 history without current pointer refuse safely; no legacy fallback. G2 current/history selfhash/header/latest mismatch also refuses.
4. Valid head GET → explicit existing selector POST → reload Today selects only that origin and one native workload. Explicit return to v1/v2 works; no clear/none.
5. Native revision changes after read → existing409, with original UUID/body journal retained; equal accepted UUID replay remains exact after expiry/corruption.
6. Missing/foreign case404, actor revoked401 and own expired terms; no source/premium/lesson/review/catalogue/allocator loads by the new GET.
7. Real read interception of a native committed save/owner revocation triggers token/authority refusal. No DML, new rows, repair, quota use or unrelated dirty-session autoflush.
8. Frontend uses the already supplied strict NativeHeadV1 validator and owner/profile/epoch fence; late A head must not prepare a B selector.

This is a small additional route/helper plus focused API/client controls for root's next explicit grant. It is not a new contract freeze, source proposal, executed result, full-gate result or acceptance claim. All STOPs remain intact.

## Primary source pin

Current inspected routes_admissions_actions.py SHA256:
31c445bb51eabc2e51f3e9d5f4a8114a748432af33a4f9a6a3b0e03b5329d983

The companion seal records all14 inspected source/proposal hashes. Original UI plan and wire/foundation packet are preserved.


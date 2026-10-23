# G2 typed contract v2 — принятый маршрут и одна ёмкость

**2026-10-12 · SEALED DESIGN ONLY · NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** Отдельная версия [TYPED_CONTRACT_DESIGN_V1.md](TYPED_CONTRACT_DESIGN_V1.md), согласованная с [SHARED_ROUTE_PERSISTENCE_SPEC_V2.md](SHARED_ROUTE_PERSISTENCE_SPEC_V2.md); исходный typed v1 сохранён без правок. Это не разрешение писать код. G1 runtime и source остаются у root. Типы ниже — проект будущей границы, а не существующие DTO. Никакие source/app модули не импортировались и tests/runtime не запускались.

## 1. Замкнутый scope и версия источника

Два **экзамена на выбор**, `ielts_academic` и `digital_sat`, используют три **имеющихся skill tracks**: `ielts_reading` (4), `sat_math` (3), `sat_reading_writing` (2). Всего ровно 9 существующих exact-version lessons / 39 вопросов из `learning-pack-2026-10-11-v1`, включая три starter lessons с `starter-2026-10-11-v1` content version. Максимум два exam choices, максимум девять разных lesson refs, ни одного нового материала/assessment. Порядок внутри track — точный `TRACK_ORDER` из `learning_pack.py`. `LearningTaskRef` и catalogue/lesson dispatch остаются неизменными.

В G2 нет автоматического programme cover edge, approved waiver, общей числовой границы, accepted edition или нового admission verdict. **Unknown official applicability не запрещает явно выбранную личную IELTS/SAT практику.** Отсутствующая/отозванная *content* version делает **точную личную lesson ref недоступной**; это отдельная причина от неизвестной принимаемой вузом exam edition. Пользовательские target scores могут отсутствовать полностью или частично; они никогда не заполняются из `RequirementCheck` и не пишутся в official profile. `ScheduleSettings` нельзя использовать как вход G2: он требует полный `target_scores` и один exam, что заставило бы выдумать значения.

Сверенные read-only source SHA-256: `catalogue.py` `8ca74f40b88df74a27bc5b0d5aa52d5e60ce5b5417f4e37c049690b47d716169`, `learning_pack.py` `778b94d392b89406e4ddd13726a25d91a808114e2026064289f12500e02b7aae`, `schemas/learning_schedule.py` `a5c26ea689d67aa68cf46936adc5057c854613a99691259282ba5ca64ea684b6`, `schemas/study_schedule.py` `259a752f19438af1ce7e72e1659844e314cca3c532ac30e0143649855b63218f`, `api/routes_preparation.py` `11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2`, G1 schema `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249`, route `188fb95ef36a33456145d452af17d1e9d645540731353e791a3bb2f6fbfec239`.

## 2. Предлагаемые request DTO

Общий `Base`: extra fields forbidden; strict strings/ints/booleans; ISO dates parsed without timestamp coercion; UUID parsed canonically; duplicate IDs rejected; no `NaN`/`Inf`; bounded JSON. `ResultId` reuses G1 strict string length 1..32. Names below independent of the existing v1/v2 DTO names.

```text
SharedRouteInputV1 {
  schema_version: "shared-route-v1"
  selected_result_ids: ResultId[2..20]                 // unique, exact, ordered; approved/maybe owned at preview/save
  starts_on: LocalDate
  timezone: IanaZone[1..80]
  study_days: Weekday[1..7]                            // unique, 0=Monday as existing settings
  shared_weekly_minutes: StrictInt[30..1260]           // ONE limit for all selected exams/reviews
  exam_choices: ExamChoiceInput[1..2]                  // unique exam; array order is explicit tie-break order
  own_reviews: OwnReviewInput[0..400]                  // existing v2 cap; unique attempt UUID; explicit only
  confirmed_shared_planning_inputs: true
}

ExamChoiceInput {
  exam: "ielts_academic" | "digital_sat"
  priority: StrictInt[0..1]                            // unique contiguous 0..N-1; same as array order
  first_exam_on: LocalDate                             // user entered, not official deadline
  retake_on: LocalDate | null                          // user entered
  certificate_deadline: LocalDate                      // user entered; never derived from admission closing
  result_wait_days: StrictInt[1..60]
  delivery_days: StrictInt[0..30]
  safety_days: StrictInt[0..30]
  personal_targets: PersonalIeltsTargets | PersonalSatTargets | null
  confirmed_exam_dates_and_buffers: true
}

PersonalIeltsTargets { overall?: HalfBand(0.5..9); listening?: HalfBand(0..9);
  reading?: HalfBand(0..9); writing?: HalfBand(0..9); speaking?: HalfBand(0..9) }
PersonalSatTargets { total?: StrictInt[400..1600]; math?: StrictInt[200..800];
  reading_writing?: StrictInt[200..800] }

OwnReviewInput {
  ref: existing AttemptReviewRef                       // UUID + exact lesson ID/content version
  exam: "ielts_academic" | "digital_sat"               // must be in exam_choices and match lesson track
  planned_minutes: StrictInt[1..1260]                 // explicit applicant allocation, no default estimate
}

LegacyAnchor {
  technical_revision: StrictInt[0..2147483646]
  structural_fingerprint: SHA256 | null                // null only if no legacy row
  imported_learning_refs_fingerprint: SHA256 | null   // null if no explicit sidecar import
}

SharedRoutePreviewIn { input: SharedRouteInputV1; expected_shared_revision: StrictInt[0..2147483646];
  legacy_anchor: LegacyAnchor }
SharedRouteSaveIn { input: SharedRouteInputV1; expected_shared_revision: StrictInt[0..2147483646];
  legacy_anchor: LegacyAnchor; preview_fingerprint: SHA256; source_fingerprint: SHA256;
  client_write_uuid: UUID }
```

Validation rules:

- `starts_on <= first_exam_on < certificate_deadline` **for each choice**; if retake exists, `first_exam_on < retake_on < certificate_deadline`. `max(certificate_deadline) - starts_on <= 365 days` across the full shared plan. Date arithmetic overflow and invalid IANA zone are 422. No automatic deadline from a G1 admission date.
- `latest_safe_exam_on = certificate_deadline - (result_wait + delivery + safety)` is a **planning calculation**, not a rejection if the entered exam is later. The preview returns `timing=at_risk` plus the entered values; user may revise. Neither `result_wait` nor `delivery` is silently set from school text.
- `personal_targets=null` is valid. When supplied, only known keys and native numeric bounds/half-bands are valid; partial maps stay partial. No missing component is inferred. For complete SAT target fields, math + reading/writing must be **at least** the entered total, following the existing planning constraint; partial fields have no inferred total. They remain `origin=applicant_target`, never `published_minimum` or `official_score`. No “target met” status arises from practice correctness.
- `own_reviews` may reference only currently owned `StudyAttempt` with matching `attempt_id`, `lesson_id`, `content_version`, and exam track. An older exact-version attempt **need not match any current catalogue lesson**. Validate availability through the actual owned review resolver for its saved `attempt_id + lesson_id + content_version`; current catalogue membership is not an availability test. If that resolver can still show the historical exact review, it remains a dated review action. If it cannot, keep its exact reference and `version_unavailable` unallocated/status; never create a new lesson or replace the version. Duplicate UUID and same lesson/attempt ref under both exam choices are rejected. The user enters each review's planned minutes; a value larger than current day/week capacity is well typed but reported unallocated rather than silently shortened.
- The server selects only the matching subset of the 9 existing catalogue refs for the chosen exam(s), pins their real per-lesson content version, and never accepts arbitrary client `LessonRef` as authority. It may accept explicit own review refs after own DB validation. No `AssessmentRef` or `ResourceRef` is scheduled as available content.
- Preview/save uses G1's exact whole-selection owner/decision validation; `requested_result_ids`, `selected_result_ids`, programme order, and manifest must agree. Locked source may support only personal practice with `applicability=unknown` and proofless receipt. Save writes the **full accepted reference-only allocation** alongside applicant inputs, action/reference IDs and digests; no premium name/excerpt/scope copy. Missing/rejected selection is not trimmed. A saved-plan GET later uses the separate safe per-goal status probe specified in G2 v2 and reads accepted slots without recomputing them.

## 3. Pure allocator contract and deterministic steps

```text
allocate_shared_v1(
  input: ValidatedSharedRouteInputV1,
  catalogue: FrozenExactCatalogue { version; 9 lesson summaries + exact versions + TRACK_ORDER },
  own_reviews: ValidatedOwnedReviewRefs,
  planned_on: LocalDate,                            // in input.timezone; supplied, never read from clock inside pure function
) -> SharedAllocationV1

SharedAllocationV1 {
  planner_version: "shared-route-allocator-v1"
  planned_on, timezone, ordered_exam_choices
  lessons: exact LessonRef[<=9]                     // stable content identity, not result names
  slots: DatedSlot[0..400]
  capacity: WeekCapacity[]
  unallocated: UnallocatedAction[]
  exam_timing: ExamTiming[]
  readiness: "not_assessed"
  digest: SHA256                                     // canonical output over pinned exact inputs
}

DatedSlot {
  occurrence_id: SHA256; action_id: SHA256; ref: existing LearningTaskRef;
  exam: ExamChoiceInput.exam; kind: "lesson" | "attempt_review";
  local_date: LocalDate; planned_minutes: StrictInt[1..1260];
  origin: "personal_practice"; completion: "not_projected"
}
WeekCapacity {
  iso_week_monday: LocalDate; weekly_budget_minutes: StrictInt[30..1260];
  allocated_minutes: StrictInt[0..1260]; remaining_minutes: StrictInt[0..1260]
}
UnallocatedAction {
  action_id: SHA256; ref: existing LearningTaskRef; exam: ExamChoiceInput.exam;
  requested_minutes: StrictInt[1..1260];
  reason: "insufficient_capacity" | "window_elapsed" | "too_long_for_day" |
          "too_long_for_week" | "slot_limit" | "version_unavailable"
}
ExamTiming {
  exam: ExamChoiceInput.exam; first_exam_on: LocalDate; retake_on: LocalDate | null;
  certificate_deadline: LocalDate; result_wait_days: StrictInt[1..60];
  delivery_days: StrictInt[0..30]; safety_days: StrictInt[0..30];
  latest_safe_exam_on: LocalDate; timing: "within_buffers" | "at_risk" | "deadline_passed"
}
```

**Duration source:** Each of the nine current `LearningUnit` lessons has published planner allocation `planned_minutes=20`; use exactly 20 per lesson, not a forecast of learning time. Own review has **only** the explicit applicant `planned_minutes`; no default. No numerical work unit comes from G1 requirement counts or score gaps. `too_long_for_day` or `too_long_for_week` returns the whole unscheduled unit and its original requested minutes; no arbitrary shrink/split.

**Algorithm:** Freeze the nine summaries in `TRACK_ORDER` and their current exact versions. For IELTS queue use `ielts_reading` order. For Digital SAT, round-robin `sat_math` and `sat_reading_writing` while preserving order within each track; this yields five lessons. For an own review whose exact `lesson_id + content_version` matches a current lesson, append it after that lesson in its exam queue, preserving explicit review input order among reviews of the same lesson. For an older exact-version review with **no current lesson match**, append it **after all current lessons** for its exam, in `own_reviews` input order. Preserve its old exact `AttemptReviewRef`; never invent a matching lesson or silently change version. Determine its executable availability through the actual owned review resolver. Foreign/mismatched attempt input is rejected; an owned review whose exact resolver is unavailable is retained as `version_unavailable` unallocated. Before scheduling, remove a well-typed unit whose duration exceeds the fixed daily cap or whole weekly budget into `too_long_for_day`/`too_long_for_week`, and remove unavailable exact refs with their typed reason; an impossible queue head must not block later valid units. One exact lesson ref appears once even if two selected programmes point to it; this is content reuse, not proof of programme coverage.

Build local calendar dates from `max(starts_on, planned_on)` through the **latest eligible end** among selected exam actions, exclusive; this includes post-first-exam study dates when an explicitly entered retake leaves an own-review window. A lesson's window ends at that exam's `first_exam_on` exclusive. Own review may run until the entered `retake_on` exclusive if there is a retake, else until `first_exam_on` exclusive. Each choice's deadline limits its dates independently, while every slot spends the same shared daily/weekly ledger. Weekly key is local ISO year/week beginning Monday; do not group by UTC hours. If a choice's practice window is already past, its remaining units are visible as `window_elapsed`, not backdated.

At each eligible study date, repeatedly visit exams in a **cyclic order starting with explicit `priority`/input order**. **Before each head-fit check**, compare the head's own window end with that date: if its lesson window ended at the first exam, move that exact lesson whole to `window_elapsed` and pop it; repeat on the next head until an eligible review (possibly with a later retake window) or lesson is reached. If the head review window also ended, move and pop it the same way. This expiration drain runs on a date even when the other exam has no work; an expired lesson cannot block a later own review. Place the first eligible whole unit when it fits remaining daily cap `180`, remaining shared weekly budget and its own exam window; then advance the round-robin cursor to the next exam. If it does not fit this date, try the other exam's head once; defer the first head to the next eligible date without overtaking within its queue. Stop when neither eligible head fits or day capacity is exhausted. The cursor persists across dates, so one stream cannot take every first slot. After the final date, drain any remaining expired heads before classifying remaining units. When all dates are exhausted or the existing 400-slot projection cap is reached, return each remaining unit with `insufficient_capacity`, `window_elapsed`, `too_long_for_day`, `too_long_for_week`, `slot_limit` or `version_unavailable` as applicable. A new review without explicit minutes is invalid request input (422), never an allocator estimate or an unallocated action. Stable IDs include allocator version, exact ref ID, selected exam and deterministic occurrence; never use random IDs inside the pure allocator. Ties do not depend on DB row order, hash-map iteration or wall-clock timing.

No zero-minute fake lessons, no duplicated allocation per programme, no practice on an entered exam date, no implied “all preparation complete” if nine short lessons were placed. `readiness=not_assessed`; submitted attempt, correctness, self tick and mastery remain separate projections. Existing `LearningTaskRef` resolves each dated lesson/review to the same exact content/own receipt route already used in v2.

**Identity/fingerprint rule:** Canonical JSON for applicant input keeps the selected programme/exam/review **array order**, normalizes `study_days` as a set in ascending order, writes local dates as `YYYY-MM-DD`, UUIDs in canonical form, integer minutes only, and rejects nonfinite numbers. `action_id = sha256(["shared-route-action-v1", exam, kind, exact LearningTaskRef identity])`; it does **not** include result IDs, university names, source URLs or currently scheduled date. Thus the same exact lesson/review across programme references is one action; two distinct content versions or attempt UUIDs are never collapsed. `occurrence_id = sha256(["shared-route-slot-v1", action_id, local due date, ordinal])`. `allocation.digest` includes canonical input, catalogue version/exact refs, planned-on date and ordered slots/unallocated reasons. `preview_fingerprint` additionally binds owned ordered result IDs, G1 per-goal source reference digests/overall fingerprint, legacy anchor and current shared revision. A new content version or changed selected order changes the preview; ordinary G1 claim `age_days` alone does not if the authoritative manifest is unchanged. Digests explain *what was read*, not official correctness or learner mastery.

## 4. Preview, receipt, read DTO boundaries

`SharedRoutePreviewOutV1` returns `{profile_id, expected_shared_revision, legacy_anchor, planned_on, expires_on_local_date, requested_result_ids, selected_result_ids, selection_source, source_fingerprint, allocation, preview_fingerprint, review_reasons, saved:false}`. `preview_fingerprint` binds canonical input + source/legacy/catalogue/planned_on + output digest. Save after the local date or after legacy technical revision/source/content changes returns 409 and keeps the client draft. The preview is not a persisted plan.

The accepted PUT body, idempotent replay body, current row and immutable history row all contain the **same full reference-only allocation**, rather than merely enough inputs to recalculate it:

```text
SharedRouteWriteReceiptV1 {
  schema_version: "shared-route-v1"; profile_id: OwnProfileId;
  revision: StrictInt[1..2147483647]; client_write_uuid: UUID;
  canonical_request_digest: SHA256; accepted_at: UtcTimestamp;
  selected_result_ids: ResultId[2..20]; applicant_input: SharedRouteInputV1;
  accepted_planned_on: LocalDate; catalogue_version: StrictString;
  planner_version: "shared-route-allocator-v1";
  allocation: SharedAllocationV1;                 // dated slots, exact refs, IDs, minutes,
                                                   // week capacity, unallocated, exam timing
  allocation_digest: SHA256;                     // equals allocation.digest
  source_fingerprint: SHA256;                     // accepted safe manifest identity
  source_reference_digests: PerGoalDigest[];      // ordered IDs + safe reference digests only
  snapshot_digest: SHA256
}
PerGoalDigest { result_id: ResultId; reference_digest: SHA256 | null }

SharedRouteViewV1 {
  receipt: SharedRouteWriteReceiptV1;            // bytes/semantic fields unchanged from PUT
  current_status: CurrentRouteStatusV1;          // fresh, never persisted into receipt
  visible_evidence: RedactedCurrentG1Slice[];   // only currently owned, eligible, authorized slices
}
CurrentRouteStatusV1 {
  as_of: UtcTimestamp;
  goal_statuses: GoalStatusV1[];                  // one per saved result in original order
  legacy_structure: "unchanged" | "changed" | "unknown";
  imported_refs: "not_used" | "unchanged" | "changed" | "unknown";
  content_statuses: ContentStatusV1[];           // one per saved exact action/ref ID
  preparation_access: "active" | "expired" | "unknown";
  needs_review: StrictBool;
  review_reasons: ReviewReasonV1[];              // deduped deterministic order, no source prose
}
GoalStatusV1 {
  result_id: ResultId;
  state: "eligible" | "decision_changed" | "result_unavailable" |
         "research_locked" | "source_changed" | "evidence_unknown";
  safe_reason_code: "decision_changed" | "result_unavailable" |
                    "research_locked" | "source_changed" |
                    "evidence_unknown" | null  // fixed public code; no premium details
}
ContentStatusV1 {
  action_id: SHA256; state: "available" | "version_unavailable" |
                            "review_unavailable" | "unknown"
}
ReviewReasonV1 {
  code: "goal_decision_changed" | "goal_result_unavailable" |
        "goal_research_locked" | "goal_source_changed" | "goal_evidence_unknown" |
        "legacy_structure_changed" | "legacy_structure_unknown" |
        "imported_refs_changed" | "imported_refs_unknown" |
        "content_version_unavailable" | "own_review_unavailable" | "content_unknown";
  result_id?: ResultId; action_id?: SHA256       // only the applicable safe identifier
}
```

`accepted_planned_on` equals `allocation.planned_on`, and `planner_version` equals `allocation.planner_version`; reject inconsistent writes/rows. `allocation_digest` hashes the complete canonical accepted allocation and equals `allocation.digest`; `snapshot_digest` binds the full receipt body except its own digest. The stored allocation contains every accepted `DatedSlot` with occurrence/action ID, exact `LearningTaskRef`, exam, local date and minutes; every week capacity; each unallocated action/reason; all entered exam timing and the accepted planning date. No G1 names, source excerpts, claims, raw scopes, current status or premium proof enter that snapshot. An idempotent same-UUID/same-request replay returns **the exact persisted receipt**; GET/history/export read its slots and unallocated list without rerunning the allocator, even after the catalogue changes or preparation expires. Reusing the same UUID with a changed request payload is 409. Fresh content availability/status may disable an old link, but cannot rewrite an accepted slot, its minutes/date or its digest.

For each saved result, the owned GET probes current metadata first and supplies exactly one `GoalStatusV1`: `result_unavailable` for missing or foreign with no existence distinction, `decision_changed` for rejected/undecided, `research_locked` before premium loads, and `eligible`/`source_changed`/`evidence_unknown` after allowed per-goal comparison. `review_reasons` and aggregate `needs_review` reflect every non-eligible goal and changed/unknown legacy or content status; a tick-only technical legacy revision is not a structural reason. `ContentStatusV1` uses the exact current lesson dispatcher or owned attempt review resolver as appropriate, without comparing an old review to today's catalogue membership. `preparation_access` is independent of research entitlement and read-time redaction. Each `visible_evidence` slice is supplied only from a fresh owned/current eligible G1 projection and follows its current visibility rules; it is never copied into the receipt or enriched from a local result card. History GET uses the same safe current status projection for its historical receipt, never an old premium view. G2 own export contains reference-only history; existing profile export of existing owned research records follows its existing owner policy. Deletion cascades G2 current/history and old rows without touching another case.

One opt-in saved G2 becomes the **single active shared planning budget** for Today. Legacy v1/v2 read shapes/ticks/UUIDs remain accessible as history and do not create a second Today workload. A tick-only legacy revision can invalidate an in-flight preview/save (technical CAS 409) but **does not** mark an already saved G2 source-stale; read-time structural fingerprint excludes completed-task IDs. If imported v2 refs are used, their separate fingerprint may mark review. Saved GET probes each old selected result safely after checking profile owner: missing/foreign generic unavailable, rejected/undecided decision changed, locked no premium load, eligible/current per-slice comparison only. A current G1 whole-selection 422/404 never erases an old receipt.

## 5. Минимальные UI поля

Один экран «Общий маршрут» с явным opt-in:

1. Saved programmes: two or more chosen own `approved`/`maybe` cards, with current G1 per-programme evidence/status and no presumed shared requirements.
2. «К чему готовиться лично»: IELTS Academic, Digital SAT checkboxes (max 2), drag/order or priority 1/2. Подпись «Выбор для подготовки; требования программ показаны отдельно». Не спрашивать exam edition, которую каталог не умеет подтверждать; official accepted edition остаётся unknown.
3. Global start date, IANA timezone, study days и **one** weekly minutes field. Per selected exam: first exam date, optional retake, certificate deadline, result wait/delivery/safety days, explicit confirmation. Optional personal target scores раскрываются отдельно и помечены как personal inputs; default empty, no inferred fields.
4. Own saved attempts checklist for explicit reviews, each with exact lesson/version and applicant-entered minutes. Unavailable versions/reviews remain explained, not silently replaced.
5. Preview with per-week used/available capacity, exact dated links, unallocated reasons and `not_assessed`; separate button «Сохранить общий маршрут». Unsaved, 409, saved revision and source-needs-review are visibly different states. Case/owner/intent fences cover preview, PUT ACK and history.

## 6. Предлагаемый finite path allowlist (после новой writeahead root)

Новые будущие файлы, **не созданные этим документом**:

| Path relative to checkout | Ограниченная роль |
| --- | --- |
| `backend/app/schemas/shared_route.py` | Только новые G2 input/preview/receipt/view DTO и strict validators; reuse existing `LearningTaskRef` classes without edits. |
| `backend/app/domain/shared_route_allocator.py` | Pure deterministic two-choice/one-budget allocator, no DB/clock/network/provider. |
| `backend/app/models/shared_route.py` | Current/history reference-only rows and uniqueness/FK. |
| `backend/app/api/routes_shared_route.py` | Owned preview/save/CAS/replay/status probe; G1 strict selection for new writes only. |
| `backend/migrations/versions/<one_new_revision>_shared_route.py` | Additive tables, one head, no legacy backfill. |
| `backend/tests/test_shared_route_allocator.py`, `backend/tests/test_shared_route_api.py` | Meaningful pure/native DB cases below. |
| `frontend/src/screens/SharedRoutePanel.tsx`, `frontend/src/screens/SharedRoutePanel.test.tsx` | Opt-in UI + owner/intent/conflict tests. |

Minimal existing-file touchpoints for a later reviewed source patch: `backend/app/main.py` router registration; `backend/app/models/__init__.py` model registration; `backend/app/models/applicant.py` delete-orphan relationships; `backend/app/api/routes_profile.py` owned export/count/note; `frontend/src/types.ts`, `frontend/src/api/client.ts`, `frontend/src/lib/i18n.ts`, `frontend/src/screens/PreparationScreen.tsx`; additive native fragments in `frontend/e2e/preparation.spec.ts` and `frontend/e2e/auth-journey.spec.ts` only after isolated gates. `backend/app/domain/study_schedule.py`, `backend/app/domain/learning_schedule.py`, `backend/app/preparation/catalogue.py`, `backend/app/preparation/learning_pack.py`, legacy schemas/routes, score evaluators, payments ledger, G1 DTO/domain/route, old test assertions and provider/worker paths are **outside this increment**. Any discovered need beyond this allowlist requires a new review before edits.

## 7. Future test matrix (NOT_RUN)

| Case | Required observation |
| --- | --- |
| 2 exams, 9 exact lessons, priority IELTS then SAT and reversed | Four IELTS Reading + five SAT Math/R&W refs, exact versions and within-track order; deterministic round-robin and one ledger. |
| One exam, duplicate exam, third exam, unknown lesson, retired exact version | One-choice valid; duplicates/third/unknown client ref rejected; retired existing ref unavailable without replacement. |
| Weekly 60, daily 180; study days cross ISO year and DST | `sum(all exam minutes per local ISO week) <=60`; daily <=180; no UTC-week or DST double count. |
| Explicit review 200 min; review 100 with weekly 60; missing review duration | Whole typed review unallocated `too_long_for_day`/`too_long_for_week`; absent duration is 422, with no invented 20-minute estimate or partial shrink. |
| Impossible review queue head followed by valid exact lesson or review | Prefilter places impossible whole action in unallocated list; later valid units still receive dates in source order. |
| Narrow first-exam window / retake / late buffers / 366-day horizon | No backdated or exam-day lessons; review can use entered retake window; timing risk visible; horizon rejected. |
| Current lesson window expires while an own review retains an entered retake window | Expired lesson is removed to `window_elapsed` at the head; later exact own review receives a valid post-first-exam date instead of being blocked. |
| Old exact-version owned review absent from current catalogue but available in the actual review resolver | Queued after all current lessons for its exam in input order, dated with the original `AttemptReviewRef`; no synthetic lesson or version substitution. If the resolver fails, exact ref remains with unavailable reason/status. |
| Targets null/partial, SAT complete inconsistent, IELTS invalid half-band | No default target or inferred section; typed bad inputs rejected; saved target never becomes official score/minimum. |
| Two programmes with IELTS and TOEFL minima, unknown OR/waiver/edition | Explicit personal IELTS practice allowed; no TOEFL course/mandatory second workload, numeric max, accepted waiver or applicability assertion. |
| Locked source, source supersession, result rejected/missing after save | Reference-only receipt preserved; locked names/proofs not copied; saved GET per-goal needs-review; new full-selection save refuses. |
| Parallel same UUID same/different payload; different UUID same revision; failed history insert | Exact own replay or 409 as defined; current/history commit or rollback together. |
| Saved GET/history after catalogue change, expiry, or same-UUID replay | Full accepted slots, IDs, dates, minutes, week ledger, unallocated reasons, exam timing and digests exactly match persisted receipt; no allocator call or rebuilt accepted calendar. |
| Saved A/B source change plus legacy structural edit and retired content | One ordered status per goal and exact action, aggregate `needs_review` with separate safe reasons; no previous premium evidence leaked; tick-only revision does not create a review reason. |
| Legacy self-tick vs structural date/budget change; v2 exact-ref change | In-flight technical 409 as applicable; old tick does not stale accepted G2; structural/imported-ref change does. |
| Expiry, owned/foreign case, export/delete, late A→B→A | Own history after expiry, no new mutation; generic foreign 404; owned reference-only export and complete cascade; no stale UI acceptance. |

## 8. Закрытые уточнения к typed v1

1. Принятый receipt/history хранит полное reference-only `allocation`, дату расчёта, IDs, exact refs, даты, минуты, week capacity, unallocated и exam timing. GET/replay не запускают allocator заново.
2. Read DTO имеет отдельные goal/content/legacy/imported statuses, фиксированные безопасные reason codes и aggregate `needs_review`; текущий research access определяет redaction независимо от подготовки.
3. Own review со старой exact version идёт после текущих уроков своего exam в порядке ввода. Доступность определяет own review resolver; новый lesson и новая version не подставляются.
4. Истёкший head удаляется в `window_elapsed` до fit check, чтобы review с ещё открытым retake window получил дату.

Это contract design и тестовые **сценарии**, не выполненные результаты. Source proposal, imports, tests, runtime, Git и provider calls остаются закрыты до отдельного writeahead root после G1 terminal.

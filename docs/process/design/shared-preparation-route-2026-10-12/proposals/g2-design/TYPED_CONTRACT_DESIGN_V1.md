# G2 typed contract v1 — личный маршрут и одна ёмкость

**2026-10-12 · SEALED DESIGN ONLY · NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** Дополнение к принятой по направлению [SHARED_ROUTE_PERSISTENCE_SPEC_V2.md](SHARED_ROUTE_PERSISTENCE_SPEC_V2.md), не разрешение писать код. G1 runtime и source остаются у root. Типы ниже — проект точной будущей границы, а не существующие DTO. Никакие source/app модули не импортировались и tests/runtime не запускались.

## 1. Замкнутый scope и версия источника

Два **экзамена на выбор**, `ielts_academic` и `digital_sat`, используют три **имеющихся skill tracks**: `ielts_reading` (4), `sat_math` (3), `sat_reading_writing` (2). Всего ровно 9 существующих exact-version lessons / 39 вопросов из `learning-pack-2026-10-11-v1`, включая три starter lessons с `starter-2026-10-11-v1` content version. Максимум два exam choices, максимум девять разных lesson refs, ни одного нового материала/assessment. Порядок внутри track — точный `TRACK_ORDER` из `learning_pack.py`. `LearningTaskRef` и catalogue/lesson dispatch остаются неизменными.

В G2 нет автоматического programme cover edge, approved waiver, общей числовой границы, accepted edition или нового admission verdict. **Unknown official applicability не запрещает явно выбранную личную IELTS/SAT практику.** Отсутствующая/отозванная *content* version делает **точную личную lesson ref недоступной**; это отдельная причина от неизвестной принимаемой вузом exam edition. Пользовательские target scores могут отсутствовать полностью или частично; они никогда не заполняются из `RequirementCheck` и не пишутся в official profile. `ScheduleSettings` нельзя использовать как вход G2: он требует полный `target_scores` и один exam, что заставило бы выдумать значения.

Сверенные read-only source SHA-256: `catalogue.py` `8ca74f40b88df74a27bc5b0d5aa52d5e60ce5b5417f4e37c049690b47d716169`, `learning_pack.py` `778b94d392b89406e4ddd13726a25d91a808114e2026064289f12500e02b7aae`, `schemas/learning_schedule.py` `a5c26ea689d67aa68cf46936adc5057c854613a99691259282ba5ca64ea684b6`, `schemas/study_schedule.py` `259a752f19438af1ce7e72e1659844e314cca3c532ac30e0143649855b63218f`, `api/routes_preparation.py` `11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2`, G1 schema `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249`, route `188fb95ef36a33456145d452af17d1e9d645540731353e791a3bb2f6fbfec239`.

## 2. Предлагаемые request DTO

Общий `Base`: extra fields forbidden; strict strings/ints/booleans; ISO dates parsed without timestamp coercion; UUID parsed canonically; duplicate IDs rejected; no `NaN`/`Inf`; bounded JSON. Names below independent of the existing v1/v2 DTO names.

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
- `own_reviews` may reference only currently owned `StudyAttempt` with matching `attempt_id`, `lesson_id`, `content_version`, and exam track. A review whose exact content version is now unavailable remains selectable as **historical own receipt** but receives `version_unavailable`, no new lesson launch or substituted content. Duplicate UUID and same lesson/attempt ref under both exam choices are rejected. The user enters each review's planned minutes; a value larger than current day/week capacity is well typed but reported unallocated rather than silently shortened.
- The server selects exactly the 9 existing catalogue refs for the chosen exam(s), pins their real per-lesson content version, and never accepts arbitrary client `LessonRef` as authority. It may accept explicit own review refs after own DB validation. No `AssessmentRef` or `ResourceRef` is scheduled as available content.
- Preview/save uses G1's exact whole-selection owner/decision validation; `requested_result_ids`, `selected_result_ids`, programme order, and manifest must agree. Locked source may support only personal practice with `applicability=unknown` and proofless receipt. Save writes only applicant inputs, action/reference IDs and digests; no premium name/excerpt/scope copy. Missing/rejected selection is not trimmed. A saved-plan GET later uses the separate safe per-goal status probe specified in G2 v2.

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

**Algorithm:** Freeze the nine summaries in `TRACK_ORDER` and their current exact versions. For IELTS queue use `ielts_reading` order. For Digital SAT, round-robin `sat_math` and `sat_reading_writing` while preserving order within each track; this yields five lessons. Append each selected own review after the lesson it references within that exam queue, preserving explicit review input order. Ref unavailable/foreign never enters an executable queue. Before scheduling, remove a well-typed unit whose duration exceeds the fixed daily cap or whole weekly budget into `too_long_for_day`/`too_long_for_week`, and remove unavailable exact refs with their typed reason; an impossible queue head must not block later valid units. One exact lesson ref appears once even if two selected programmes point to it; this is content reuse, not proof of programme coverage.

Build local calendar dates from `max(starts_on, planned_on)` through each exam's `first_exam_on` **exclusive** for lessons. Own review may run until the entered `retake_on` exclusive if there is a retake, else until `first_exam_on` exclusive. Each choice's deadline limits its dates independently, while every slot spends the same shared daily/weekly ledger. Weekly key is local ISO year/week beginning Monday; do not group by UTC hours. If a choice's practice window is already past, its remaining units are visible as `window_elapsed`, not backdated.

At each eligible study date, repeatedly visit exams in a **cyclic order starting with explicit `priority`/input order**. Consider only the head of that exam queue. Place the whole unit when it fits remaining daily cap `180`, remaining shared weekly budget and its own exam window; then advance the round-robin cursor to the next exam. If it does not fit this date, try the other exam's head once; defer the first head to the next eligible date without overtaking within its queue. Stop when neither head fits or day capacity is exhausted. The cursor persists across dates, so one stream cannot take every first slot. When all dates are exhausted or the existing 400-slot projection cap is reached, return each remaining unit with `insufficient_capacity`, `window_elapsed`, `too_long_for_day`, `too_long_for_week`, `slot_limit` or `version_unavailable` as applicable. A new review without explicit minutes is invalid request input (422), never an allocator estimate or an unallocated action. Stable IDs include allocator version, exact ref ID, selected exam and deterministic occurrence; never use random IDs inside the pure allocator. Ties do not depend on DB row order, hash-map iteration or wall-clock timing.

No zero-minute fake lessons, no duplicated allocation per programme, no practice on an entered exam date, no implied “all preparation complete” if nine short lessons were placed. `readiness=not_assessed`; submitted attempt, correctness, self tick and mastery remain separate projections. Existing `LearningTaskRef` resolves each dated lesson/review to the same exact content/own receipt route already used in v2.

**Identity/fingerprint rule:** Canonical JSON for applicant input keeps the selected programme/exam/review **array order**, normalizes `study_days` as a set in ascending order, writes local dates as `YYYY-MM-DD`, UUIDs in canonical form, integer minutes only, and rejects nonfinite numbers. `action_id = sha256(["shared-route-action-v1", exam, kind, exact LearningTaskRef identity])`; it does **not** include result IDs, university names, source URLs or currently scheduled date. Thus the same exact lesson/review across programme references is one action; two distinct content versions or attempt UUIDs are never collapsed. `occurrence_id = sha256(["shared-route-slot-v1", action_id, local due date, ordinal])`. `allocation.digest` includes canonical input, catalogue version/exact refs, planned-on date and ordered slots/unallocated reasons. `preview_fingerprint` additionally binds owned ordered result IDs, G1 per-goal source reference digests/overall fingerprint, legacy anchor and current shared revision. A new content version or changed selected order changes the preview; ordinary G1 claim `age_days` alone does not if the authoritative manifest is unchanged. Digests explain *what was read*, not official correctness or learner mastery.

## 4. Preview, receipt, read DTO boundaries

`SharedRoutePreviewOutV1` returns `{profile_id, expected_shared_revision, legacy_anchor, planned_on, expires_on_local_date, requested_result_ids, selected_result_ids, selection_source, source_fingerprint, allocation, preview_fingerprint, review_reasons, saved:false}`. `preview_fingerprint` binds canonical input + source/legacy/catalogue/planned_on + output digest. Save after the local date or after legacy technical revision/source/content changes returns 409 and keeps the client draft. The preview is not a persisted plan.

`SharedRouteWriteReceiptV1` is immutable, reference-only as in G2 v2: `{schema_version, profile_id, revision, client_write_uuid, canonical_request_digest, accepted_at, selected_result_ids, applicant_input, exact_refs, allocation_digest, source_reference_digests, snapshot_digest}`. The exact same UUID/request returns this exact own receipt even after preparation expiry; changed payload is 409. No G1 names/proofs/raw scope/current status in it. The own read shape is `SharedRouteViewV1 { receipt: SharedRouteWriteReceiptV1; goal_statuses: GoalStatusV1[one per selected result in receipt order]; visible_evidence: RedactedCurrentG1Slice[]; read_on: LocalDate }`, where `GoalStatusV1 { result_id; state: "current" | "source_changed" | "decision_changed" | "locked" | "unavailable"; safe_reason_code? }`. Each `visible_evidence` slice is supplied only from a fresh owned/current eligible G1 projection and follows its current visibility rules; it is never copied into the receipt. The read does not infer acceptance from absent or locked evidence. G2 own export contains reference-only history; existing profile export of existing owned research records follows its existing owner policy. Deletion cascades G2 current/history and old rows without touching another case.

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
| Targets null/partial, SAT complete inconsistent, IELTS invalid half-band | No default target or inferred section; typed bad inputs rejected; saved target never becomes official score/minimum. |
| Two programmes with IELTS and TOEFL minima, unknown OR/waiver/edition | Explicit personal IELTS practice allowed; no TOEFL course/mandatory second workload, numeric max, accepted waiver or applicability assertion. |
| Locked source, source supersession, result rejected/missing after save | Reference-only receipt preserved; locked names/proofs not copied; saved GET per-goal needs-review; new full-selection save refuses. |
| Parallel same UUID same/different payload; different UUID same revision; failed history insert | Exact own replay or 409 as defined; current/history commit or rollback together. |
| Legacy self-tick vs structural date/budget change; v2 exact-ref change | In-flight technical 409 as applicable; old tick does not stale accepted G2; structural/imported-ref change does. |
| Expiry, owned/foreign case, export/delete, late A→B→A | Own history after expiry, no new mutation; generic foreign 404; owned reference-only export and complete cascade; no stale UI acceptance. |

Это contract design и тестовые **сценарии**, не выполненные результаты. Source proposal, imports, tests, runtime, Git и provider calls остаются закрыты до отдельного writeahead root после G1 terminal.

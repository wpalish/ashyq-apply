# G2 allocator — read-only notes before source authorization

**2026-10-12 · DESIGN NOTES ONLY · SOURCE PROPOSAL NOT_CREATED / NOT_ACCEPTED / NOT_APPLIED / NOT_IMPORTED / NOT_RUN.**

Root corrected the initial delegation before any schema/domain/test source bytes were written. The accepted [typed V2](../g2-design/TYPED_CONTRACT_DESIGN_V2.md), [persistence V2](../g2-design/SHARED_ROUTE_PERSISTENCE_SPEC_V2.md), [root acceptance](../../ROOT_G2_TYPED_DESIGN_ACCEPTANCE.md) and [integration decisions](../../ROOT_G2_INTEGRATION_DECISIONS.md) require a separate G2 HANDOFF write-ahead **after a terminal qualified G1 release**. This note does not substitute for it. Current root-owned G1 native work remains untouched. Only this Markdown note and the adjacent [read-only inspection receipt](READ_ONLY_INSPECTION.json) are written externally. No proposed schema, domain module, test module, patch, helper or migration exists in this package.

## 1. Confirmed finite material seam

Current registry is `learning-pack-2026-10-11-v1`, combining six pack lessons with three exact `starter-2026-10-11-v1` lessons. Source [TRACK_ORDER](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/preparation/learning_pack.py:469) preserves the order inside each of three tracks. The future pure allocator takes a caller-supplied frozen, exact registry; it must not import or call `pack_catalogue`, `lesson_dispatch`, application routes, DB, clock or providers while allocating. An ordinary integration adapter later supplies the validated summaries and availability. This is an input boundary, not an ownership decision inside a pure function.

| Track | Exact lesson ID | Content version | Items | Planning minutes |
| --- | --- | --- | ---: | ---: |
| ielts_reading | `ielts-reading-1` | `starter-2026-10-11-v1` | 3 | 20 |
| ielts_reading | `ielts-reading-headings-1` | `learning-pack-2026-10-11-v1` | 5 | 20 |
| ielts_reading | `ielts-reading-completion-1` | `learning-pack-2026-10-11-v1` | 5 | 20 |
| ielts_reading | `ielts-reading-features-1` | `learning-pack-2026-10-11-v1` | 5 | 20 |
| sat_math | `sat-math-1` | `starter-2026-10-11-v1` | 3 | 20 |
| sat_math | `sat-quadratic-structure-1` | `learning-pack-2026-10-11-v1` | 5 | 20 |
| sat_math | `sat-data-interpretation-1` | `learning-pack-2026-10-11-v1` | 5 | 20 |
| sat_reading_writing | `sat-rw-1` | `starter-2026-10-11-v1` | 3 | 20 |
| sat_reading_writing | `sat-grammar-transitions-1` | `learning-pack-2026-10-11-v1` | 5 | 20 |

Totals: **9 lessons / 39 items**, IELTS Reading 4/18, SAT Math 3/13, SAT Reading & Writing 2/8. Twenty minutes comes from [LearningUnit](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/learning_schedule.py:46), not a claim about sufficient teaching time. Listening, Writing and Speaking still have no local material. Do not add inferred content or diagnostic tasks.

Exam-local queue order before reviews:

- IELTS Academic: `ielts-reading-1`, headings, completion, features.
- Digital SAT: `sat-math-1`, `sat-rw-1`, quadratic-structure, grammar-transitions, data-interpretation. This alternates the two SAT tracks while preserving each track's `TRACK_ORDER`; it is distinct from the catalogue's track-grouped display order.

## 2. Existing types cannot serve as the full G2 request

[ScheduleSettings](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/study_schedule.py:35) requires one exam and all target keys; [LearningPathSettings](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/learning_schedule.py:54) embeds it. Feeding G2 through either would require invented targets or duplicate budgets. Future G2 must have its own strict input shape: 2–20 exact ordered selected result IDs; one or two explicit exam choices with contiguous priorities matching array order; one daily cap 180 and one weekly limit 30–1260; shared start/timezone/days; per-exam entered date/buffers; optional personal targets; 0–400 explicit own reviews. No model/routes/FE/migration expansion is authorized here.

Strict validation details to preserve when source is separately authorized:

- Confirmations require the literal boolean `true`; reject `1`, strings, missing or false. Strict integer bounds exclude booleans. Dates accept only valid local ISO dates, never datetime/epoch coercion. Validate IANA timezone but do not read a clock inside allocator.
- `personal_targets=null` and incomplete known fields are valid. Reject boolean/numeric-string/nonfinite scores and unknown fields; enforce half-bands and SAT native bounds. Enforce SAT section sum only when all three values were supplied. Preserve omission versus explicitly supplied fields in canonical input rather than filling missing components with null/zero. Targets remain `applicant_target`, never official minima/scores or placement priorities derived from a score gap.
- Validate date ordering, <=365-day whole horizon, and calendar arithmetic overflow before allocation. Risk from entered buffers is a reported timing state, not a reason to invent an earlier exam/deadline.
- Pure function accepts a real `date` for planned-on, not `datetime`. It may reject an improperly validated object; it never obtains auth, ownership, evidence or current availability itself.
- Exact catalogue input contains exactly the accepted nine identities/tracks/versions/order. Missing or duplicate summaries, arbitrary client lesson refs or synthetic resource/assessment work are invalid boundary data, not new courses. An exact known ref with supplied unavailable content state is retained unallocated without substitution.

## 3. Exact refs and own reviews

The existing [opening guard](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/LearningSchedulePanel.tsx:12) and [v2 save validator](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation.py:371) require canonical reference IDs: `lesson:{lesson_id}:{content_version}` and `attempt:{canonical UUID}`. Later G2 should bind these same identities. Caller-chosen alias IDs cannot create different semantic actions for one attempt, and two versions/UUIDs must never collapse. Action identity excludes programme IDs/names/source URLs/scheduled date.

[review_attempt](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation.py:563) returns an unchanged owned receipt with `lesson=None` when exact lesson content is unavailable. That receipt is still an openable own review. The pure allocator receives supplied validated UUID + lesson/version + selected personal exam + resolver availability, and does **not** test current catalogue membership to reject a historical review. Match-current-version reviews follow their lesson; old-version reviews follow all current lessons of their exam in explicit input order. Missing/mismatched/foreign UUIDs are rejected upstream, not converted to unavailable content.

**Integration seam to retain as explicit dependency:** [StudyAttempt](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/models/study.py:16) stores lesson/version, not a track/exam. A historical exact reference may match a known lesson ID with a retired version; a future adapter can validate its exam through an authorized known historical identity mapping. If the exact lesson ID itself has no trusted exam association and original content is absent, do not invent its track from spelling. Pure supplied-review types must make validated exam association a caller invariant; root needs a conservative adapter policy before advertising support for that broader historical case. No extra field/migration is proposed now.

Review duration is an explicit integer 1–1260, independent of the lesson's 20 minutes. Missing duration is invalid input. No shrink/split or default estimate. Version-unavailable review keeps its exact ref as unallocated; a receipt with no original lesson is not automatically unavailable if the resolver can show the own receipt.

## 4. Deterministic details to pin before code bytes

These are **interpretations/recommendations awaiting root confirmation**, not edits to sealed V2:

1. **Exam-day exclusion.** V2 says no practice on an entered exam date. Treat the union of all selected first-exam and retake dates as excluded shared-study dates, even when the other exam has an open window. Otherwise IELTS review could be allocated on SAT exam day. Each action still uses its own exclusive first-exam/retake bound.
2. **Final classification boundary.** Drain expired heads against each actual visited study date before fit. After the final visit, retain that date as the classification boundary; when there were no visits, use `max(starts_on, planned_on)`. Do not advance to an invented date after the horizon and relabel every capacity failure as `window_elapsed`. A window already closed at planning start is elapsed; no selected weekday within a still-open window is insufficient capacity.
3. **Reason precedence.** A ref unavailable at the supplied exact resolver is `version_unavailable`; otherwise a whole unit >180 is `too_long_for_day`, then a unit >weekly limit is `too_long_for_week`. Expired otherwise feasible heads drain before day/week fit; `slot_limit` applies to eligible remaining work only after the 400 placed-slot bound. Fix deterministic reason/list ordering in source tests; do not allow collection/dict order to select the reason.
4. **Week ledger.** Prefer ascending local Monday keys for weeks containing eligible shared study dates, including zero-used weeks. Each record reports the entered weekly budget and actual usage/remaining; do not duplicate a budget per exam or silently replace it with `study_days ×180`. No UTC or DST hours are involved in a local-date ledger.
5. **Occurrence ordinal.** There is one whole occurrence per exact action in this increment. Prefer per-action ordinal 0, not a global insertion index, so inserting another action does not change an otherwise identical action/date's occurrence identity. Slot IDs still change with their local date; action IDs never do.
6. **Targets in digest.** Full canonical input preserves selected programme/exam/review array order, sorted study-day set and supplied target fields. Date/UUID/minutes representations are fixed; JSON rejects nonfinite values before serialization. Reordering programmes may change the allocation digest/preview identity while leaving ref action IDs, personal practice applicability and dated workload unchanged.

The cyclic exam cursor survives dates and only advances after a placement. If one head does not fit, try the other selected exam once; no queue overtaking. Impossible/unavailable units are removed before queue scheduling. During each fit loop, pop all expired heads first so an eligible retake-window own review becomes reachable. One empty stream must not suppress expiration drain in the other. Every scheduled minute spends the same daily/week ledger.

## 5. Meaningful future pure/schema test scenarios — NOT_CREATED / NOT_RUN

| Control | Independent required observation |
| --- | --- |
| Literal nine exact refs, one exam and both priority orders | Exact 4/5 subsets and per-track order, no duplicate refs across programme IDs, no new assets. Do not compute expected queue using the function under test. |
| No/partial targets, complete inconsistent SAT, invalid IELTS half-band, bool/string/nonfinite numeric values | Missing targets accepted unchanged; bad provided values rejected; practice correctness never sets target/readiness/official score. |
| `shared_weekly_minutes=60`, study dates across ISO year and a DST transition | Sum all exams/reviews <=60 per local Monday week and <=180 per day; one ledger and exact local dates. |
| Same first-exam/retake dates across two exams and another exam's open window | No slot on any globally excluded entered exam date under the interpretation above. |
| Available owned old-version review whose resolver has `lesson=None` | Preserved UUID/lesson/version, after current lesson queue, personal exam supplied by validated caller; no current-version substitution. |
| Too-long review followed by valid work; two independent over-limit reasons | Whole request duration retained, valid tail still scheduled, >180 day reason vs >weekly week reason deterministic; no shrink/split. |
| Day advance beyond first exam, still-open retake review, expired lesson queue ahead | Expired lessons drain without consuming capacity; reachable review can be dated post-first-exam. |
| Narrow still-open window with no fitting date versus already-past window | `insufficient_capacity` stays distinct from `window_elapsed`; final loop boundary does not falsify reason. |
| 400 one-minute own reviews plus nine lessons, adequate dates/capacity | <=400 slots, each of the <=409 exact actions appears once in slots OR unallocated, no duplicate/missing IDs; genuine capped tail carries `slot_limit` unless independently unavailable/expired. |
| Change programme IDs/order, planning dates, exact version and own UUID independently | Semantic action IDs unaffected by programme/date changes; occurrence/date and canonical digests respond to their bound fields; versions/UUIDs remain distinct. |
| Supplied unavailable exact ref and unknown programme applicability | Exact unavailable work retained with reason; explicitly chosen personal practice proceeds when source applicability is unknown; no cover edge/merged minimum/waiver/admission verdict. |
| Repeated same inputs; study-day array permutations; review array reorder | Byte/semantic deterministic output; equivalent study-day sets canonicalize; review order is preserved when it affects queue ordering. |
| Malformed registry/availability boundary, duplicate UUID, exam mismatch, third exam | Strict rejection before allocation; no app/DB/network resolver call from domain. |

Output invariants should be independently calculated from literal test inputs: unique semantic actions; disjoint slots/unallocated; conservation of all exact actions; whole-duration preservation; cap <=400; every slot before its own bound and >=planning start; no entered exam-day slot; integer minutes; explicit `origin=personal_practice`, `completion=not_projected`, `readiness=not_assessed`. Optional targets do not weight allocation. Unknown official applicability remains unknown.

## 6. Scope and remaining prerequisites

Later schema/domain proposal paths only: `backend/app/schemas/shared_route.py`, `backend/app/domain/shared_route_allocator.py`, `backend/tests/test_shared_route_allocator.py`. They have **not** been created/copied/imported here. Request/receipt/read DTO breadth must be pinned by root's later allowlist; this note authorizes none. Do not create routes/models/migration/UI or change old calendar/material/attempt schemas.

The pure contract can be proposed only after G1 qualified terminal + fresh G2 write-ahead. Then refresh exact preimages and accepted-design hashes, record these deterministic choices, create a separate external sealed source packet, and have root review/apply/run it. Ownership, actual review resolution, persisted allocation, UUID replay/shared CAS, legacy present/absent-row race, premium redaction, export/delete and active Today integration remain separate source/runtime gates. There is no G2 runtime, migration, lock proof, full course, diagnostic score, publication or product-readiness claim from this inspection.

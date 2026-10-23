# Deadline learning follow-through — next finite acceptance gap

**2026-10-11 · READ_ONLY_NEXT_STEP · NOT_IMPLEMENTED.** Root reports applied learning-pack HEAD `68d0c153` and serial native gates in progress. This note pins ordinary source reads; it does not independently verify Git or the ongoing gate outcome. No code/Git/runtime/tests/provider/network, closed labels or old archive mutation. Search STOP/UNSCORED remains unchanged.

## Actual gap after the nine-lesson increment

The lesson catalogue now offers nine original lessons/39 items, exact versions, next-lesson navigation and saved mistake review. The deadline calendar still opens only three starters. Later skill/review dates remain generic even when the relevant next unit exists.

| Current contract | Source evidence |
| --- | --- |
| Only IELTS Reading/SAT Math/SAT RW starter IDs are mapped; each links once | `backend/app/domain/study_schedule.py:22–26,218–233` |
| Calendar buttons admit only those three IDs | `frontend/src/screens/StudySchedulePanel.tsx:25,203` |
| New pack has ordered four-lesson IELTS Reading, three-lesson SAT Math and two-lesson SAT RW paths; summaries carry each exact version | `backend/app/preparation/learning_pack.py:468–521` |
| Current lesson opening resolves its summary's version, next unit and owned saved review | `frontend/src/screens/PreparationScreen.tsx:147–165,185–212,277–298,314–337` |
| Schedule task stores lesson ID without content version/activity reference | `backend/app/schemas/study_schedule.py:147–156` |
| Priority uses entered component score gaps; missing/old baselines remain flagged, readiness stays unassessed | `backend/app/domain/study_schedule.py:30–51,167–190`; `backend/app/schemas/study_schedule.py:167–169` |

This is a concrete learning-calendar connection gap. It is not evidence of a calibrated target-score diagnostic or a model predicting how many days will produce a score.

## Smallest safe follow-up: opt-in versioned calendar activities

Keep the accepted date/buffer and skill-allocation calculations. Add an explicit opt-in calendar revision that resolves appropriate dated skill slots to a frozen curriculum reference: **lesson ID + exact content version + activity (`learn/practise` or `review`)**. Use the pack's ordered paths to link SAT's five local units or IELTS Reading's four; keep the other three IELTS skills as explicitly unavailable local content with external/professional actions. Once a path is exhausted, name a review activity rather than inventing more available lessons or declaring the course complete.

Each task should show its actual date, allocated minutes, named skill/unit and applicant-entered target; “Open lesson” requests that exact version. A review task should open an **owned, submitted, matching-version receipt** selected by the learner, or show that no matching saved attempt exists. It must not invent a review result. Task checkmarks remain reported activity; accepted quiz receipts, assessed feedback and official certificates remain separate. A submission does not automatically advance dates or mark tasks mastered.

Use existing owned-case schedule CAS saves and the new exact-version review GET. Persist or deterministically pin the selected curriculum/planner version on explicit save so later deployment/progress/date changes do not substitute content. Preserve the original calendar until the learner reviews an opt-in rebuild; their accepted attempt history survives it. If allocated time cannot fit the declared activity, split it into bounded dated work or warn about unscheduled work. Do not cram into partial weeks, add exam-day study, exceed existing daily/weekly/365-day/400-task bounds, or imply all units fit a short deadline.

**Concrete compatibility hazard:** `study_schedule.py:138` fingerprints the full settings dump. Adding even a default/null curriculum setting changes the old hash unless the legacy canonical settings projection is preserved. Existing completion IDs then fail the known-ID check on GET (`:284–288`). Require byte-equivalent legacy task identity and an explicit new planner mode; do not silently repair by dropping completions or turning a read into a write. New curriculum changes require explicit revision/reconciliation and retain overdue/past tasks within the saved calendar.

## Target scores and programme evidence remain different contracts

Show applicant-entered IELTS overall/L/R/W/S or SAT total/Math/RW targets alongside their dated baseline and named activities. Raw practice correct/total, a perfect familiar repeat and a submitted week cannot fill official/component `baseline_scores`, clear `diagnostic_required`, predict band/scale growth or change `readiness=not_assessed`. An overall baseline cannot establish section readiness. Automatic performance-based scheduling is a later, separate contract: it needs reviewed skill-tagged/unseen evidence and transparent formative routing, with no official score conversion or learning-time guarantee.

A programme-required minimum must retain the selected owned result, exact check/claim IDs, exam/type/component, programme/intake/population scope, source URL, accessed date and evidence status. Current evidence projection already fails unknown for unresolved legacy URL associations and suppresses actionable lesson links for stale/conflicted/unknown evidence, unresolved alternatives and waiver checks (`domain/preparation.py:112–173,176–208,255–278`). Preserve that behavior.

An explicit learner action may copy a **current, scoped required** minimum into a personal planning target while displaying its provenance; it must not convert a co-published alternative into “take all exams”, confirm a waiver, equate optional/test-blind with required, or mix scholarship and degree minima. A published SAT total does not supply Math/RW minima; missing components require the learner's separately labelled planning choices. Application closing date is still not certificate receipt deadline. Personal practice remains possible while those requirements are unknown; no new provider fetch is needed for this increment.

## Finite acceptance criteria for that follow-up

1. Existing saved calendars/settings produce exactly their original IDs/dates/checkmarks with no new GET writes; opt-in rebuild is explicit and revision conflicts require review, never silent retry/overwrite.
2. A sufficiently long synthetic SAT plan links its five relevant local units in track order; an IELTS plan links its four Reading units and keeps L/W/S unavailable. Short/budget-constrained plans disclose unallocated units rather than claiming coverage.
3. Every local task opens its exact lesson/version; a starter cannot use pack version, an unknown pair cannot fall back to current content, and a later content deployment/date advance does not remap accepted tasks.
4. Review opens only the matching case's submitted UUID/lesson/version; unknown, foreign and another case's UUID disclose nothing. Expired terms retain owned historical review while new unseen lessons/submissions remain gated. Existing account/case late-response fences remain.
5. All entered-buffer milestones/latest-safe date, selected days, integer weekly/daily caps, no exam-day study, past/overdue visibility and maximum horizon/task count remain. Extra learning work cannot quietly shift an exam or certificate deadline.
6. Quiz success, repeats and reported completion leave official Academics, requirements, baseline/diagnostic/readiness and research/case quota unchanged. No provider/LLM/research action starts.
7. Scoped required versus personal target provenance is visible; shared URLs, absent components, stale/conflicted evidence, alternatives, waivers, optional/blind and scholarship-only minima retain their honest states.
8. Real local learner flow opens a dated unit, submits/retries once, reads mistakes, selects its owned historical review, reloads/relogs and returns to the same saved calendar/case/version. Engineering runtime, teacher pedagogy and learner outcomes remain separate acceptances.

**Scope:** additive calendar-to-learning binding, not a full course, calibrated diagnosis, automated score forecast or production readiness claim. Adjacent source metadata records exact file hashes and bounded read coverage. Ongoing native results must be reviewed separately once terminal.

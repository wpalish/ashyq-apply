# Deadline preparation — evidence and scheduling design

**Status: current-source design complete; isolated three-file proposal ready for peer review, NOT_APPLIED.** This audit uses ordinary source from `integration-2026-10-11/source`, with exact hashes/read coverage in `schedule-evidence-source-pins.json`. No source/Git/provider/model/runtime change was made for this evidence audit. The subsequently authorized pure proposal was tested only in isolated offline staging; DB/API/frontend/full gates belong to root. This agent authored the new pure proposal and is not its independent source reviewer.

## What the current evidence can support

| Current contract | Actual source | Scheduling meaning |
|---|---|---|
| Stored numeric requirement comparison, applicant snapshot, status, references and published scope | `schemas/result.py:47`; `domain/eligibility.py:190` | Preserve the original check. Its status is not a learning prediction; a number alone cannot prove the current programme/intake or accepted test route. |
| Programme application date, raw text, timezone, passed flag, previous-cycle date | `schemas/result.py:359`; `domain/eligibility.py:278` | Application-context date only. The source has no typed certificate/result-receipt deadline. Previous-cycle dates cannot become this intake's schedule deadline. |
| Population-specific application dates | `domain/eligibility.py:633` | The displayed check can quote the earliest date and multiple URLs. Do not silently infer the applicant's fee population or use the earliest population date as a personal certificate deadline. |
| Claim IDs or shared page URLs, scope/status/currentness, unresolved conflicts | `schemas/claim.py:26`; `domain/preparation.py:116,159,227`; `api/routes_preparation.py:243` | Exact ID selects its claim; an accompanying URL adds provenance. A URL alone cannot select another exam family/component or resolve ambiguous neighbouring claims. Only current, official, scoped evidence supports a published requirement. |
| IELTS overall plus separate L/R/W/S, test type, taken_on, planned_retake_on and field status | `schemas/profile.py:89,112` | Separate component baselines and targets are possible. Overall does not fill missing components. A planned retake is intention, not a booked appointment or accepted OSR. Applicant-confirmed values are self-report, not an independently verified certificate. |
| SAT total, Math and Reading/Writing | `schemas/profile.py:94`; `domain/eligibility.py:352` | Native admission checks currently publish SAT total/policy. Named Math/RW starter routing is not evidence of a published section minimum; no automatic half-total allocation. |
| TEST_VALIDITY_MONTHS, accepted types, waivers, English alternatives and scholarship minima | `domain/enums.py:130`; `domain/preparation.py:176` | A validity length does not name its reference event or exam family by itself. Co-published alternatives/waivers are unresolved; scholarship and degree targets are separate. A personal schedule cannot settle these decisions. |
| Tiny original reading/math/RW starter catalogue and raw progress | `schemas/preparation.py:14,119`; `preparation/catalogue.py:26,283` | Introductory practice and error review only. No calibrated score, learning-rate estimate or full-course coverage; IELTS Listening/Writing/Speaking are not implemented starters. |
| Owned result binding, research lock and profile/result staleness | `api/routes_preparation.py:203-331` | Scheduling must compose with ownership and existing evidence locks. Changing personal planning preferences must not falsely update academic profile timestamps or unlock/read stale result evidence as current. |

Missing from current structured facts: recipient certificate due date/stage, verified booking/seat, exact release/transmission/processing windows, validity reference event, weekly availability, personal score goals, full-format calibrated diagnostic and a reviewed skill-growth model. Absence is unknown, not zero days or no requirement.

## Narrow additive contract adopted for the first slice

The root's `CONTRACT.md` defines one active **personal exam plan per owned applicant case**, separate from academics and PreparationPlan evidence. The isolated implementation is `proposals/schedule/{REPORT.md,source-pins.json,proposed-schedule.patch}` and only three new schema/domain/test paths. Root owns model/migration/API/CAS/export/cascade/UI changes.

**Inputs:** exam (IELTS Academic/Digital SAT), start/first exam/optional retake/personal certificate deadline, IANA timezone, selected weekdays and one shared weekly budget, complete per-exam target vector, optional partial dated baseline, and explicit result/delivery/safety buffers. All three buffers are required; an entered0 delivery/safety value remains an assumption with a warning. `confirmed_planning_dates:true` confirms the user's plan, not an official university rule.

**Dates and feasibility:**

```
latest planned attempt = retake if entered, otherwise first exam
result estimate = latest attempt + entered result wait
recipient delivery estimate = result estimate + entered delivery wait
buffer end = recipient estimate + entered safety allowance
latest_safe_exam_on = personal certificate deadline - all three entered buffers
```

The backward boundary is a planning calculation. It does not establish actual test availability, retake permission, university processing or deadline time. A last attempt after that boundary produces at_risk and keeps all late events; an already passed date produces deadline_passed without erasing overdue work. Exact time-of-day/institution timezone are not inferred from a date-only field. Server derives `today` in the selected timezone.

**Two distinct conclusions:** calendar logistics may be within_entered_buffers; academic readiness is always **not_assessed**. Neither a completed task nor a baseline already at target yields a guarantee. No rule such as “X hours per IELTS band” or “Y SAT points per week” is invented. Current official timing research is a separate source-backed note; institution receipt remains recipient-specific and is not collapsed into student result availability.

## Targets and requirement safeguards

1. First-slice targets are explicit personal goals. Original checks, academic scores, conflict/stale/unknown states, optional/blind SAT, waivers and alternatives remain unchanged beside the plan. User-entered targets must not be relabelled as published minima.
2. For a future source-backed target suggestion, require a uniquely compatible current claim, exact exam/component/type and intake/programme scope, unresolved-conflict check, and scalar agreement with its original RequirementCheck. A shared URL, bare overall value, date field or generic recognition page cannot establish a target. Suggestions remain editable planning goals with separate provenance.
3. IELTS has overall and four independent component targets. Do not derive component clearance from overall or force component targets to average to the overall minimum. Show missing components and each entered below-target gap, without a growth forecast.
4. SAT has total plus two personal section goals. Target sections must sum to at least the total goal; a complete self-reported baseline must total exactly its two sections. Partial baseline is allowed and requires diagnosis. No section minimum is manufactured from a programme's SAT total.
5. When waiver/alternative choice is unresolved, offer an explicit personal practice choice and a clarification action; do not declare every exam mandatory. Unsupported DET/TOEFL/HSK/CSCA/country/degree exams remain planned/unknown until their own exam/version/component/route adapter and reviewed curriculum exist. No universal China mandate is introduced.
6. Keep application, scholarship, visa/enrolment and certificate-evidence stages distinct. A later implementation needs an explicit typed evidence-due claim/reference stage before using it as an official constraint. The first slice records a personal date and clearly says to confirm the recipient rule.

## Realistic milestones within the current modest content

- Missing baseline components: first selected session is a component diagnostic action, not a band conversion of the starter quiz. Complete but >30-day-old baseline requires reassessment; its dated task is calculated from baseline_on+31 and original available dates so the calendar stays stable as today advances.
- Prioritise weak components by bounded deficits **within the selected exam**, followed by weighted round robin so available skills are not silently dropped. Overall/section values use separate warnings; no cross-exam numerical-gap comparison.
- Use one study task per selected day, integer nominal weekday shares of the **one** weekly budget, and a conservative180-minute daily cap. Exam days and partial weeks leave unused capacity rather than cramming it into the final remaining day. Very short blocks or insufficient future slots require an explicit adjustment warning.
- First IELTS Reading/SAT Math/RW starter introduction links once; subsequent sessions ask for skill practice, error-log review and timed section practice. Unsupported IELTS skills explicitly require professional feedback or suitable official practice.
- A final external full-format mock is reserved only with a conservative180-minute daily block and prior component coverage.180 minutes is an editorial planning reserve, not an official universal duration or an official mock score. If it cannot fit, show the warning and arrange a separate adequately long assessment. Never substitute the tiny starter quiz.
- First exam, optional retake, entered results/delivery/safety and personal submission milestones remain visible, including past/late dates. Self-reported completion indicates an action was marked done; it does not verify a result or recipient receipt.

## Integration and acceptance checklist

The pure proposal has **51 actual synthetic PASS,0F/E/S**, native-config Ruff/format and focused mypy3 PASS. The first50PASS/1FAIL is preserved: partial-week budget compression produced an unexpected mock; nominal weekday shares repaired it without weakening the assertion. This is isolated pure-function proof, not an API/native/full acceptance receipt.

Root's union must prove: owner/case isolation; unknown/cross-case completion rejection; future baseline422; timezone-derived current date; absent versus saved schedule GET; eligible started-term PUT and expired/unstarted writes; optimistic revision/create conflicts; bounded revision IDs; no applicant.updated_at/research/quota changes; export/history/delete/cascade; unchanged PreparationPlan scope/waiver/alternative semantics; UI explicit save/replacement/clear-completion confirmation; late response fences for owner/case/settings revision; mobile views and no false score/readiness text.

Fixed settings produce a stable original calendar independent of today: past tasks are retained, only overdue/remaining/age flags change. Structural setting edits generate different task IDs and require explicitly clearing old completion. This is one current plan, not immutable multi-revision teaching history; starter-attempt history remains a separate contract. No source deployment, full-course completion, pedagogy acceptance, certified score attainability or resumed current search quality is claimed.

## Exact source binding

The full12-file SHA256/read-coverage table is `schedule-evidence-source-pins.json`. Key current files: domain/preparation `07cf2c70355847b76affbe72564b80841bad9009af671056e6b38c2d098295b4`; profile schema `b15ba3a8b4ee3519cee207caf2eb8504f22e1cb4b1039436ba4ce792850beff1`; result schema `f4eab02362d8bcdcec72bc1f16e2636f7abe7c0844b72b18bb4eac94f3927974`; claim schema `109d65d69da8d0d773618b8ff35487d4bea1bb37b8f60acb8895d1baaa9bf794`. All factual observations here are from current ordinary code. Historical memory supplied only the proposal/integration/search-quality boundary; no historical test count or source state was substituted for current evidence.

## Completion namespace qualification (append-only)

Completion IDs are deterministic calendar/settings identifiers, not credentials or globally unique applicant-case identifiers. Identical settings on two owned cases intentionally yield the same task IDs. The checklist phrase “cross-case completion rejection” means rejecting unauthorised/wrong-profile requests and structurally foreign calendar IDs, together with response/case/revision fences; it must not imply impossible raw-ID uniqueness for identical calendars. If case-unique raw IDs are desired, root must explicitly add a profile namespace to the pure-builder contract. No score/evidence or verified completion transfers are established by a task ID. Original v1 text/hash is preserved in `schedule-evidence-design.v1.md`; the three-file source proposal remains unchanged.

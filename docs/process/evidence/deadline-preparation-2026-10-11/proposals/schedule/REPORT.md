# Isolated study schedule proposal

Status: **EXTERNAL_PROPOSAL_NOT_APPLIED; FOCUSED_OFFLINE_PASS**. Three new paths only: schema, pure builder and their synthetic controls. Root owns API/DB/frontend/application/native gates. Source parent from contract: `975482ad` (not Git-queried here); exact current native configuration hashes and ABSENT preimages are recorded in `source-pins.json`.

## Implemented contract

- Entered dates and targets remain personal planning assumptions. Four permanent warnings distinguish application closing dates, certificate/recipient deadlines, result availability, recipient processing, booking, test acceptance and retake permission. No claims, original requirement checks, eligibility/ranking or academics are changed.
- Forward result/delivery/safety arithmetic plus explicit backward `latest_safe_exam_on`; latest_exam_on still means last entered planned attempt. Infeasible timing remains visible as at_risk rather than being rejected/clipped. Passed windows and late milestones are retained.
- Complete IELTS overall/L/R/W/S targets; partial baselines require their date. SAT total/section goals and complete-baseline sum validation. Separate component/overall gap text; bounded deficit-weighted round robin covers available skills. No score-growth, official-score conversion or readiness forecast; readiness is always not_assessed, even at goal.
- One study task per chosen date, nominal integer weekly shares across all skills, daily cap180, no study on either exam day. Partial weeks leave unused capacity. Horizon365; total tasks<=400. Result/delivery events may truthfully extend beyond the entered deadline.
- Missing baselines schedule diagnostic first. Baseline age>30 days sets diagnostic_required; a deterministic dated reassessment derived from baseline_on+31 preserves the calendar when today changes. Baseline dates after starts_on are allowed; future baselines raise ValueError for API422.
- Original starter links attach once only to IELTS Reading/SAT Math/SAT RW introductions. Unsupported IELTS skills explicitly require professional feedback/official practice. A full external mock needs the conservative180-minute daily reserve plus prior component coverage; otherwise an explicit warning requests a separate adequate assessment.180 minutes is a planning reserve, not an official universal test duration.
- Completion IDs bind normalized structural settings, date and task. Today/checkmarks are excluded. Unknown or structurally outdated IDs fail closed; partial progress settings updates require UI-confirmed clearing. Completed tasks do not become verified scores. Overdue means noncompleted and due_on<today.
- Validation bounds IDs and SQL-safe expected revision, rejects ambiguous boolean confirmations/scores, duplicate days/IDs, invalid IANA timezone, unsupported score keys/ranges, calendar over/underflow and oversized inputs. All three timing buffers are required, including an explicitly entered0-day delivery/safety value; no universal default is fabricated.

## Actual isolated verification

**51 distinct synthetic cases PASS; 0 failures/errors/skips**, native JUnit retained. Ruff/check, Ruff/format, focused mypy3 all exit0 using read-only native configuration. Native source conftest, application startup, database and API were excluded from staging; Python socket operations were denied and pytest plugin autoload disabled. This is narrow pure-function evidence, not native/full/backend security acceptance.

First execution was **50 PASS/1 FAIL**: a partial pre-exam week redistributed all180 weekly minutes into its last Monday and created an unexpected full mock. The correction reserves each selected weekday's nominal share; unused/exam-day capacity is not compressed. The failing assertion remains exact in meaning and all51 initial test identities remain. Initial native JUnit/log/hashes are preserved; exact initial pre-format source bytes were not separately retained. A separate first Ruff I001 failure and import-only AST-equal repair are also preserved.

Controls cover reverse/forward buffer arithmetic, late retake events, no invented retake, combined weekly/daily capacity, component diagnostics/priorities, starter/mocks boundaries, baseline-at-goal no readiness claim, stable IDs and overdue/completion across today, baseline aging without rewriting, progress/future baselines, stale/foreign completion IDs, past deadlines, zero slots,365 horizon, score/input bounds, revision overflow and calendar over/underflow.

## Remaining gates and product limits

Root must validate owned case/result access, started-term write checks, optimistic CAS/create races, export/delete/cascade, no profile.updated_at/research/quota mutation, timezone-derived today and frontend owner/case/request fences after applying the union. No source/API/native/full gates were run by this author. Meaningful native API tests are owned by the backend peer. Full official-material courses, calibrated diagnostics, booking/result-delivery integration, teacher-reviewed teaching progression, score attainability and current search quality are not established.

Existing evidence policies (alternatives, waivers, optional/blind SAT, conflict/stale/scope/unknown, scholarship separation) remain in PreparationPlan; this personal schedule does not resolve or bypass them. Supplied targets must not be silently branded as programme minima. Official timing notes may inform manually reviewed entries; they must not replace exact booked-date/recipient evidence with a universal lag.

Packet: `source-pins.json`, `proposed-schedule.patch`, three exact files and retained evidence. Peer source review pending; root sole writer/application owner.

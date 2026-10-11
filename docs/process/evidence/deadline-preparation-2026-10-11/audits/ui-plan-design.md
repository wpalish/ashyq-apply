# Deadline-driven preparation: UI design and proposal

Date: 2026-10-11. Status: **EXTERNAL_PROPOSAL — GATES_NOT_RUN**. Root is the sole source and Git writer.

## Current foundation and narrow addition

The saved foundation provides Goals & evidence, three original starter lessons (nine questions), and saved attempt progress. Its programme evidence is a read-only requirements snapshot; it does not establish a complete course or learner readiness. PreparationScreen uses saved case/owner/caseEpoch isolation (lines35–48), guarded access and evidence reads (98–122), source details, and separate practice/progress. Current root scaffolding additionally imports this proposed panel, adds Study plan mode, two client methods and schedule DTOs. These scaffolding edits are root-owned; this proposal changes none of them.

Production addition: `frontend/src/screens/StudySchedulePanel.tsx`. Synthetic component controls: `StudySchedulePanel.test.tsx`. Both are new files, separate from `PreparationPlan` evidence and official academic/profile scores.

## Learner flow

1. Open **Exam preparation → Study plan** for a saved own case. GET loads only when the panel is mounted. Without a saved case, the parent retains its save/select-case prompt.
2. Choose the one active exam: IELTS Academic or Digital SAT. Enter preparation start, certificate deadline, first exam, optional retake, three explicit timing buffers, total weekly minutes and available weekdays. Time zone starts from the browser environment; dates/buffers require explicit confirmation. No application deadline, booking, result delay or delivery time is invented.
3. Enter all target components. Current scores/date are optional, partial applicant inputs. A newer diagnostic may be after preparation started; the server checks future dates in the selected zone. Missing skills remain unassessed; an old diagnostic remains subject to the server warning/diagnostic requirement.
4. Save explicitly. The server-generated calendar shows the backward-planned latest safe exam separately from the last entered attempt, result/delivery dates, timing risk, warnings and `not_assessed` readiness.
5. See next14 current/future tasks. Native disclosure retains every other task, including overdue tasks. Whitelisted links open only the three existing introductory lessons. Other skills, external practice and mocks remain clearly unavailable course work here rather than fabricated lessons.
6. Save checkmarks as self-reported completion. Update baseline, availability or dates to adapt the remaining calendar; structural changes require explicit confirmation clearing old checkmarks. Starter correctness is not converted into an official score, diagnostic or mastery estimate.

## Evidence and goals stay distinct

| Information | Meaning in UI |
|---|---|
| Programme requirements, components, waivers, scope, source dates/quotes | Retained in Goals & evidence; not copied as automatic official targets/deadlines |
| Target overall + sections | Personal applicant goals |
| Current score + date | Applicant-entered estimate or external diagnostic input; not verified here |
| Weekly minutes and dated tasks | Allocation of the stated total availability for one exam; not a target guarantee |
| Completed task | Applicant-reported activity; not assessed mastery |
| Starter attempts | Separate practice history; no official-score/profile mutation |

## Persistence, conflicts and ownership

- GET is read-only. A started preparation entitlement controls saving/opening practice; an expired term can still read its own calendar.
- PUT carries exact expected revision and typed settings. One in-flight ref denies duplicate writes. No automatic PUT retry, optimistic checkmark or success before acceptance.
- HTTP409 triggers only GET, retaining the form. The latest GET must succeed and the learner must explicitly review it before applying inputs to the new revision. Editing after failed refresh cannot bypass review.
- Structural input changes require a distinct checkmark reset confirmation. Exam replacement clears the old score form and replaces the one active plan only after Save; practice history remains separate.
- All read/write results and lesson callbacks check live parent ownership. Returned profile ID and accepted revision are checked. Case replacement remounts local form/request state. Stale old-owner feedback is hidden.
- Only accepted API saves persist. Leaving the view discards unsaved input; no localStorage durability is promised.

## Proposed acceptance controls (12; not executed)

1. Explicit new-plan dates, buffers, all targets, budget and days required.
2. Double-submit sends one PUT; failed save retains form; explicit retry has identical payload/revision.
3. 409 refreshes revision without PUT retry, retains own inputs and requires review.
4. Failed conflict GET stays blocked after editing; stale overwrite cannot bypass review.
5. Checkmark preserves saved settings/revision, is not optimistic, and retries identical intent.
6. Structural changes clear checkmarks only with confirmation.
7. New partial baseline after start accepted; unknown components are not zero-filled.
8. Exam replacement clears baseline and requires all SAT target components.
9. No access still allows own reads but disables writes/lesson openings.
10. Late A read cannot populate B.
11. Mismatched case and late old-owner write feedback excluded.
12. First14 display retains all remaining/past tasks and overdue warnings.

Typed synthetic fixtures spy the two API methods, deny unexpected fetch and assert no create/update profile or research start. Existing PreparationScreen controls(19) and seven original preparation-client controls were not edited by this agent. Root independently appended two scheduling client controls (currently nine total), outside this proposal.

## Integration verification still required

Root must apply the two files and run native frontend typecheck/lint/tests/build, then actual-source synthetic Demo/Auth tests as appropriate. Root-owned mode navigation, serializer/access guards, server budget/weak-skill allocation, old-baseline warnings, revision persistence and mobile geometry require fresh source-bound gates. This panel renders the server calendar; no runtime, full-course quality, score calibration, production integration or deployment is verified here.

Stable labels and CSS instructions: `../proposals/ui/README.md`. Exact source/contract reads: `../proposals/ui/PINS.json`.

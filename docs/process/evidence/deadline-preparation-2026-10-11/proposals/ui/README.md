# StudySchedulePanel proposal

Status: **READY_FOR_ROOT_REVIEW — NOT_APPLIED_BY_AUTHOR — GATES_NOT_RUN**.

## Exact scope

Only two new repo paths are in `study-schedule-ui.patch`:

- `frontend/src/screens/StudySchedulePanel.tsx` (production component)
- `frontend/src/screens/StudySchedulePanel.test.tsx` (12 synthetic component controls)

No dependencies/config/CSS/API/types/source/Git/server/provider changes by this agent. Existing foundation assertions remain untouched. Root's current DTO/client/mode scaffolding is a pinned input, outside this patch.

## Parent integration contract

`<StudySchedulePanel profileId={profileId} allowed={data.access.allowed} isCurrent={isCurrent} onLesson={startLesson} />`

Mount only in **Study plan** mode. Preserve existing PreparationCase owner/profile/caseEpoch key and saved-case gate. Panel also keys its internal state by profile ID and fences async work with live isCurrent. Only GET/PUT `studySchedule` / `saveStudySchedule`; starter buttons call parent's guarded lesson flow.

Required DTO: `GeneratedSchedule.latest_safe_exam_on` from current root types and explicit additive instruction. If omitted from the contract field list, root should align that documentation before integration freeze. Timing buffers have no default. Future baseline/max-horizon validation remains authoritative server validation.

## Root-owned scoped CSS

- `.study-schedule`: outer wrapper, minimum width zero and long-text wrapping also inline
- `.study-schedule__fields`: date/buffer field groups
- `.study-schedule__score-pair`: each target/current pair

Two desktop columns, one mobile column can be scoped here. Existing `.preparation-choice` supplies checkbox tap areas. No animation/fixed navigation changes here. Root should verify320/390 widths and last-action reachability in actual-source native E2E.

## Stable English accessible labels

- Mode **Study plan** (root-owned); headings **Your deadline study plan**, **Saved dated tasks**
- **Exam**; **Preparation starts**; **Certificate deadline**; **First exam**; **Planned retake (optional)**
- **Result wait (days)**; **Delivery (days)**; **Safety buffer (days)**; **Time zone**
- **Overall target**, **Listening target**, **Reading target**, **Writing target**, **Speaking target**
- SAT: **Total target**, **Math target**, **Reading & Writing target**
- Each **[component] current score (optional)**; **Current-score date (optional)**
- **Weekly study minutes**; **Monday** through **Sunday**
- **I confirm these are my planning dates and buffers, not verified bookings or official deadlines**
- **Save study plan** stays button label pending; live status **Saving study plan…**
- Accepted **Study plan saved.**; failed **Not saved. Your inputs remain in this form.**
- Conflict **I reviewed the latest saved version before replacing it**, **Refresh latest saved plan**
- Reset **Rebuild the calendar and clear previous task checkmarks**
- Task **Completed: [title] ([YYYY-MM-DD])**
- Starter **Open starter lesson: [task title]**
- Disclosure **Other saved tasks (N), including past tasks**
- Safe date **Latest exam under your entered buffers: DATE**

No raw JSON or extra progress DOM markers.

## Verification

12 new tests use native Vitest/testing-library and complete typed synthetic fixtures. **NOT_RUN**: typecheck/lint/test/build/browser/API/server/E2E. Static React checklist: unconditional hooks; primitive resource identity dependencies; lazy form initialization; transient refs; no shared mutable requests; labelled native fieldsets/inputs; mounted/current-owner fences; no heavy dependencies. This is static review, not a gate result.

Root must gate exact applied source. Unsubmitted form is memory only. Progress is self-reported tasks and separate starter attempts, not calibrated mastery/predicted results. See `../../audits/ui-plan-design.md`; `PINS.json`, `MANIFEST.json`, `READY.json` bind this packet. Earlier foundation receipts do not validate this component.

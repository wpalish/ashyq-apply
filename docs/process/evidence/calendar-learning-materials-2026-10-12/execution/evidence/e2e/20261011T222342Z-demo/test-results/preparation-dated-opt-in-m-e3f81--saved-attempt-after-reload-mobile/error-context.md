# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: preparation.spec.ts >> dated opt-in materials preserve legacy settings and reopen the exact saved attempt after reload
- Location: ../../../../source/frontend/e2e/preparation.spec.ts:364:1

# Error details

```
Test timeout of 120000ms exceeded.
```

```
Error: page.waitForResponse: Target page, context or browser has been closed
```

```
Error: locator.click: Target page, context or browser has been closed
Call log:
  - waiting for getByRole('button', { name: 'Preview updated learning path' })
    - locator resolved to <button disabled class="btn" type="button">Preview updated learning path</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is not enabled
    - retrying click action
      - waiting 100ms
    232 × waiting for element to be visible, enabled and stable
        - element is not enabled
      - retrying click action
        - waiting 500ms

```

# Page snapshot

```yaml
- generic [ref=f2e3]:
  - complementary [ref=f2e4]:
    - navigation "Main navigation" [ref=f2e5]:
      - button "Home" [ref=f2e6] [cursor=pointer]
      - button "Find" [ref=f2e10] [cursor=pointer]
      - button "Plan" [ref=f2e14] [cursor=pointer]
      - button "Exam preparation" [ref=f2e18] [cursor=pointer]:
        - generic [ref=f2e21]: Prepare
      - button "Documents" [ref=f2e22] [cursor=pointer]:
        - generic [ref=f2e25]: Docs
      - button "Community" [ref=f2e26] [cursor=pointer]:
        - generic [ref=f2e29]: People
  - generic [ref=f2e30]:
    - banner [ref=f2e31]:
      - generic [ref=f2e32]: Unimatch
      - generic [ref=f2e33]: Demo data
      - group [ref=f2e34]:
        - generic "Explore⌄" [ref=f2e35] [cursor=pointer]
      - generic [ref=f2e36]:
        - text: Applicant
        - combobox "Applicant" [ref=f2e37]:
          - option "New applicant"
          - option "Demo Applicant (synthetic) · 1 run" [selected]
          - option "Demo Applicant (synthetic) · 1 run"
          - option "Demo Applicant (synthetic) · 1 run"
          - option "Demo Applicant (synthetic) · 1 run"
          - option "New applicant · 0 runs"
          - option "New applicant · 0 runs"
          - option "New applicant · 0 runs"
          - option "Demo Applicant (synthetic) · 1 run"
          - option "Demo Applicant (synthetic) · 1 run"
          - option "Demo Applicant (synthetic) · 1 run"
          - option "Demo Applicant (synthetic) · 1 run"
      - button "New case" [ref=f2e38] [cursor=pointer]
      - button "Settings" [ref=f2e39] [cursor=pointer]
    - main "Exam preparation" [ref=f2e40]:
      - generic [ref=f2e41]:
        - generic [ref=f2e42]:
          - paragraph [ref=f2e43]: ORIGINAL PRACTICE · YOUR CASE
          - heading "Prepare for your next step." [level=1] [ref=f2e44]
          - paragraph [ref=f2e45]: Programme requirements, original practice and saved attempts. Practice does not change your official scores or establish admission readiness.
        - note [ref=f2e46]:
          - generic [ref=f2e47]:
            - strong [ref=f2e48]: Development starter access
            - paragraph [ref=f2e49]: Original IELTS Reading, SAT Math and SAT Reading & Writing practice units. This is not a full exam course or an official mock test.
            - paragraph [ref=f2e50]: Local preview access
        - navigation "Preparation views" [ref=f2e51]:
          - button "Goals & evidence" [ref=f2e52] [cursor=pointer]
          - button "Study plan" [pressed] [ref=f2e53] [cursor=pointer]
          - button "Practice" [ref=f2e54] [cursor=pointer]
          - button "Progress" [ref=f2e55] [cursor=pointer]
        - paragraph [ref=f2e56]: Unsubmitted answers stay only in this form. Leaving a lesson clears them.
        - generic [ref=f2e57]:
          - generic [ref=f2e58]:
            - heading "Your deadline study plan" [level=2] [ref=f2e60]
            - paragraph [ref=f2e61]: One active exam plan per applicant case. Your entered goals and dates are separate from programme requirements and official scores.
            - status [ref=f2e62]: The plan changed elsewhere. Your form inputs remain here. Review the latest saved version before an explicit save.
            - note [ref=f2e63]:
              - generic [ref=f2e64]:
                - paragraph [ref=f2e65]: Review the latest saved plan below before applying your form inputs. Nothing is overwritten automatically.
                - generic [ref=f2e66] [cursor=pointer]:
                  - checkbox "I reviewed the latest saved version before replacing it" [ref=f2e67]
                  - text: I reviewed the latest saved version before replacing it
            - generic [ref=f2e68]:
              - group "Exam and planning dates" [ref=f2e69]:
                - generic [ref=f2e71]:
                  - generic [ref=f2e72]: Exam
                  - combobox "Exam" [ref=f2e73]:
                    - option "IELTS Academic"
                    - option "Digital SAT" [selected]
                - paragraph [ref=f2e74]: Changing the exam replaces this single plan when saved. It clears current-score inputs and old task checkmarks, but does not delete your practice history.
                - generic [ref=f2e75]:
                  - generic [ref=f2e76]:
                    - generic [ref=f2e77]: Preparation starts
                    - textbox "Preparation starts" [ref=f2e78]: 2026-10-11
                  - generic [ref=f2e79]:
                    - generic [ref=f2e80]: Certificate deadline
                    - textbox "Certificate deadline" [ref=f2e81]: 2027-01-03
                  - generic [ref=f2e82]:
                    - generic [ref=f2e83]: First exam
                    - textbox "First exam" [ref=f2e84]: 2026-12-30
                  - generic [ref=f2e85]:
                    - generic [ref=f2e86]: Planned retake (optional)
                    - textbox "Planned retake (optional)" [ref=f2e87]
                - paragraph [ref=f2e88]: Enter when you need the certificate, your intended exam dates and explicit timing buffers. These dates do not book an exam or verify an application deadline.
                - generic [ref=f2e89]:
                  - generic [ref=f2e90]:
                    - generic [ref=f2e91]: Result wait (days)
                    - spinbutton "Result wait (days)" [ref=f2e92]: "5"
                  - generic [ref=f2e93]:
                    - generic [ref=f2e94]: Delivery (days)
                    - spinbutton "Delivery (days)" [ref=f2e95]: "2"
                  - generic [ref=f2e96]:
                    - generic [ref=f2e97]: Safety buffer (days)
                    - spinbutton "Safety buffer (days)" [ref=f2e98]: "7"
                - paragraph [ref=f2e99]: No universal result or delivery time is assumed. Verify these buffers for your actual exam and receiving institution.
                - generic [ref=f2e100]:
                  - generic [ref=f2e101]: Time zone
                  - textbox "Time zone" [ref=f2e102]:
                    - /placeholder: e.g. Asia/Almaty
                    - text: UTC
                - generic [ref=f2e103] [cursor=pointer]:
                  - checkbox "I confirm these are my planning dates and buffers, not verified bookings or official deadlines" [checked] [ref=f2e104]
                  - text: I confirm these are my planning dates and buffers, not verified bookings or official deadlines
              - group "Your target and current scores" [ref=f2e105]:
                - paragraph [ref=f2e107]: Targets are your goals. Current scores are optional inputs from you, not a diagnosis or a verified certificate. Starter correctness does not become a band or scaled score.
                - generic [ref=f2e108]:
                  - generic [ref=f2e109]:
                    - generic [ref=f2e110]: Total target
                    - spinbutton "Total target" [ref=f2e111]: "1400"
                  - generic [ref=f2e112]:
                    - generic [ref=f2e113]: Total current score (optional)
                    - spinbutton "Total current score (optional)" [ref=f2e114]: "1200"
                - generic [ref=f2e115]:
                  - generic [ref=f2e116]:
                    - generic [ref=f2e117]: Math target
                    - spinbutton "Math target" [ref=f2e118]: "700"
                  - generic [ref=f2e119]:
                    - generic [ref=f2e120]: Math current score (optional)
                    - spinbutton "Math current score (optional)" [ref=f2e121]: "600"
                - generic [ref=f2e122]:
                  - generic [ref=f2e123]:
                    - generic [ref=f2e124]: Reading & Writing target
                    - spinbutton "Reading & Writing target" [ref=f2e125]: "700"
                  - generic [ref=f2e126]:
                    - generic [ref=f2e127]: Reading & Writing current score (optional)
                    - spinbutton "Reading & Writing current score (optional)" [ref=f2e128]: "600"
                - generic [ref=f2e129]:
                  - generic [ref=f2e130]: Current-score date (optional)
                  - textbox "Current-score date (optional)" [ref=f2e131]: 2026-10-11
                - paragraph [ref=f2e132]: A newer current-score entry can update an existing plan. The server checks that its date is not in the future in your selected time zone.
              - group "Your available study time" [ref=f2e133]:
                - generic [ref=f2e135]:
                  - generic [ref=f2e136]: Weekly study minutes
                  - spinbutton "Weekly study minutes" [ref=f2e137]: "180"
                - paragraph [ref=f2e138]: This is the total budget for this one exam, shared across skills. Allocated hours are a schedule, not a promise to reach your target.
                - group "Study days" [ref=f2e139]:
                  - generic [ref=f2e140] [cursor=pointer]:
                    - checkbox "Monday" [checked] [ref=f2e141]
                    - text: Monday
                  - generic [ref=f2e142] [cursor=pointer]:
                    - checkbox "Tuesday" [ref=f2e143]
                    - text: Tuesday
                  - generic [ref=f2e144] [cursor=pointer]:
                    - checkbox "Wednesday" [checked] [ref=f2e145]
                    - text: Wednesday
                  - generic [ref=f2e146] [cursor=pointer]:
                    - checkbox "Thursday" [ref=f2e147]
                    - text: Thursday
                  - generic [ref=f2e148] [cursor=pointer]:
                    - checkbox "Friday" [checked] [ref=f2e149]
                    - text: Friday
                  - generic [ref=f2e150] [cursor=pointer]:
                    - checkbox "Saturday" [ref=f2e151]
                    - text: Saturday
                  - generic [ref=f2e152] [cursor=pointer]:
                    - checkbox "Sunday" [ref=f2e153]
                    - text: Sunday
              - paragraph [ref=f2e154]: Only a successful save persists this form. Leaving this view discards unsaved inputs. Practice attempts and official profile scores are kept separately.
              - button "Save study plan" [disabled] [ref=f2e155]
          - generic [ref=f2e156]:
            - heading "Learning calendar" [level=2] [ref=f2e158]
            - status
            - paragraph [ref=f2e159]: Save or discard the original form changes before previewing this path.
            - paragraph [ref=f2e160]: At least twenty minutes per unit is a planning allocation. Tasks and saved submissions do not establish mastery, official scores or exam readiness.
            - button "Preview updated learning path" [disabled] [ref=f2e161]
          - generic [ref=f2e162]:
            - heading "Saved dated tasks" [level=2] [ref=f2e164]
            - paragraph [ref=f2e165]: Revision 4 · calendar evaluated 2026-10-11 in UTC
            - paragraph [ref=f2e166]:
              - strong [ref=f2e167]: "Readiness: not assessed."
              - text: This plan does not establish that you will reach your target.
            - paragraph [ref=f2e168]: "Timing: at risk · 34 remaining study days · 2720 allocated minutes remaining."
            - paragraph [ref=f2e169]:
              - strong [ref=f2e170]: "Latest exam under your entered buffers: 2026-12-20."
              - text: This is the backward-planned limit, not an available booking.
            - paragraph [ref=f2e171]: "Latest planned exam: 2026-12-30; expected results: 2027-01-04; expected delivery: 2027-01-06. These depend on your entered buffers."
            - list [ref=f2e172]:
              - listitem [ref=f2e173]: Dates, score targets and buffers are applicant-entered planning assumptions, not verified programme requirements or certificate deadlines.
              - listitem [ref=f2e174]: Application closing dates do not establish when exam evidence must be received. Confirm the recipient's evidence deadline, accepted test type and delivery method.
              - listitem [ref=f2e175]: Results available to the student do not prove recipient receipt or processing. Exam dates do not prove a booking, available seat or permitted retake.
              - listitem [ref=f2e176]: Study completion and starter correct/total never establish an official score, readiness or admission eligibility.
              - listitem [ref=f2e177]: "Entered planning gaps: math 600 to 700; reading writing 600 to 700; total 1200 to 1400. Time to close these gaps has not been assessed; an overall value cannot establish component readiness."
              - listitem [ref=f2e178]: The latest entered exam is later than the buffer-based latest safe planning date 2026-12-20; entered result, delivery and safety buffers overrun the certificate deadline.
              - listitem [ref=f2e179]: No full-format external mock fits the final daily reserve; arrange an adequately long assessment separately. Timed practice is not a score estimate.
            - paragraph [ref=f2e180]: Original Reading / SAT Math / SAT Reading & Writing units are available. The opt-in learning calendar connects their exact versions. Other skills, timed mocks and professional feedback need suitable external or future course work; a calendar entry does not create that course.
            - paragraph [ref=f2e181]: Save or discard your form changes before editing saved task checkmarks.
            - paragraph [ref=f2e182]: 0 past-due unchecked tasks. Checkmarks report activity, not mastery.
            - heading "Next dated tasks" [level=3] [ref=f2e183]
            - list [ref=f2e184]:
              - listitem [ref=f2e185]:
                - paragraph [ref=f2e186]:
                  - strong [ref=f2e187]: "2026-10-12 · Math: introductory starter, followed by error review; target 700 is a planning goal"
                  - text: · math · 80 minutes
                - generic [ref=f2e188]:
                  - 'checkbox "Completed: Math: introductory starter, followed by error review; target 700 is a planning goal (2026-10-12)" [disabled] [ref=f2e189]'
                  - text: Reported done by me — not an assessed score
                - 'button "Open starter lesson: Math: introductory starter, followed by error review; target 700 is a planning goal" [ref=f2e190] [cursor=pointer]'
              - listitem [ref=f2e191]:
                - paragraph [ref=f2e192]:
                  - strong [ref=f2e193]: "2026-10-14 · Reading Writing: introductory starter, followed by error review; target 700 is a planning goal"
                  - text: · reading writing · 80 minutes
                - generic [ref=f2e194]:
                  - 'checkbox "Completed: Reading Writing: introductory starter, followed by error review; target 700 is a planning goal (2026-10-14)" [disabled] [ref=f2e195]'
                  - text: Reported done by me — not an assessed score
                - 'button "Open starter lesson: Reading Writing: introductory starter, followed by error review; target 700 is a planning goal" [ref=f2e196] [cursor=pointer]'
              - listitem [ref=f2e197]:
                - paragraph [ref=f2e198]:
                  - strong [ref=f2e199]: "2026-10-16 · Math: review and error log; planning goal 700"
                  - text: · math · 80 minutes
                - generic [ref=f2e200]:
                  - 'checkbox "Completed: Math: review and error log; planning goal 700 (2026-10-16)" [disabled] [ref=f2e201]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e202]:
                - paragraph [ref=f2e203]:
                  - strong [ref=f2e204]: "2026-10-19 · Reading Writing: skill and error log; planning goal 700"
                  - text: · reading writing · 80 minutes
                - generic [ref=f2e205]:
                  - 'checkbox "Completed: Reading Writing: skill and error log; planning goal 700 (2026-10-19)" [disabled] [ref=f2e206]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e207]:
                - paragraph [ref=f2e208]:
                  - strong [ref=f2e209]: "2026-10-21 · Math: timed practice and error log; planning goal 700"
                  - text: · math · 80 minutes
                - generic [ref=f2e210]:
                  - 'checkbox "Completed: Math: timed practice and error log; planning goal 700 (2026-10-21)" [disabled] [ref=f2e211]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e212]:
                - paragraph [ref=f2e213]:
                  - strong [ref=f2e214]: "2026-10-23 · Reading Writing: review and error log; planning goal 700"
                  - text: · reading writing · 80 minutes
                - generic [ref=f2e215]:
                  - 'checkbox "Completed: Reading Writing: review and error log; planning goal 700 (2026-10-23)" [disabled] [ref=f2e216]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e217]:
                - paragraph [ref=f2e218]:
                  - strong [ref=f2e219]: "2026-10-26 · Math: skill and error log; planning goal 700"
                  - text: · math · 80 minutes
                - generic [ref=f2e220]:
                  - 'checkbox "Completed: Math: skill and error log; planning goal 700 (2026-10-26)" [disabled] [ref=f2e221]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e222]:
                - paragraph [ref=f2e223]:
                  - strong [ref=f2e224]: "2026-10-28 · Reading Writing: skill and error log; planning goal 700"
                  - text: · reading writing · 80 minutes
                - generic [ref=f2e225]:
                  - 'checkbox "Completed: Reading Writing: skill and error log; planning goal 700 (2026-10-28)" [disabled] [ref=f2e226]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e227]:
                - paragraph [ref=f2e228]:
                  - strong [ref=f2e229]: "2026-10-30 · Math: review and error log; planning goal 700"
                  - text: · math · 80 minutes
                - generic [ref=f2e230]:
                  - 'checkbox "Completed: Math: review and error log; planning goal 700 (2026-10-30)" [disabled] [ref=f2e231]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e232]:
                - paragraph [ref=f2e233]:
                  - strong [ref=f2e234]: "2026-11-02 · Reading Writing: timed practice and error log; planning goal 700"
                  - text: · reading writing · 80 minutes
                - generic [ref=f2e235]:
                  - 'checkbox "Completed: Reading Writing: timed practice and error log; planning goal 700 (2026-11-02)" [disabled] [ref=f2e236]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e237]:
                - paragraph [ref=f2e238]:
                  - strong [ref=f2e239]: "2026-11-04 · Math: skill and error log; planning goal 700"
                  - text: · math · 80 minutes
                - generic [ref=f2e240]:
                  - 'checkbox "Completed: Math: skill and error log; planning goal 700 (2026-11-04)" [disabled] [ref=f2e241]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e242]:
                - paragraph [ref=f2e243]:
                  - strong [ref=f2e244]: "2026-11-06 · Reading Writing: review and error log; planning goal 700"
                  - text: · reading writing · 80 minutes
                - generic [ref=f2e245]:
                  - 'checkbox "Completed: Reading Writing: review and error log; planning goal 700 (2026-11-06)" [disabled] [ref=f2e246]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e247]:
                - paragraph [ref=f2e248]:
                  - strong [ref=f2e249]: "2026-11-09 · Math: skill and error log; planning goal 700"
                  - text: · math · 80 minutes
                - generic [ref=f2e250]:
                  - 'checkbox "Completed: Math: skill and error log; planning goal 700 (2026-11-09)" [disabled] [ref=f2e251]'
                  - text: Reported done by me — not an assessed score
              - listitem [ref=f2e252]:
                - paragraph [ref=f2e253]:
                  - strong [ref=f2e254]: 2026-11-11 · Arrange a component diagnostic and record its dated baseline; starter totals are not official scores
                  - text: · 80 minutes
                - generic [ref=f2e255]:
                  - 'checkbox "Completed: Arrange a component diagnostic and record its dated baseline; starter totals are not official scores (2026-11-11)" [disabled] [ref=f2e256]'
                  - text: Reported done by me — not an assessed score
            - group [ref=f2e257]:
              - generic "Other saved tasks (25), including past tasks" [ref=f2e258] [cursor=pointer]
```

# Test source

```ts
  274 | test('deadline plan persists dated targets, task completion and backward timing without changing official scores', async () => {
  275 |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  276 |   await expect(page.getByRole('heading', { name: 'Your deadline study plan', exact: true })).toBeVisible();
  277 |   await page.getByLabel('Exam', { exact: true }).selectOption('digital_sat');
  278 |   await page.getByLabel('Preparation starts', { exact: true }).fill(scheduleDate(0));
  279 |   await page.getByLabel('Certificate deadline', { exact: true }).fill(scheduleDate(84));
  280 |   await page.getByLabel('First exam', { exact: true }).fill(scheduleDate(56));
  281 |   await page.getByLabel('Result wait (days)', { exact: true }).fill('5');
  282 |   await page.getByLabel('Delivery (days)', { exact: true }).fill('2');
  283 |   await page.getByLabel('Safety buffer (days)', { exact: true }).fill('7');
  284 |   await page.getByLabel('Time zone', { exact: true }).fill('UTC');
  285 |   for (const [field, value] of [['Total', '1400'], ['Math', '700'], ['Reading & Writing', '700']]) {
  286 |     await page.getByLabel(`${field} target`, { exact: true }).fill(value!);
  287 |   }
  288 |   for (const [field, value] of [['Total', '1200'], ['Math', '600'], ['Reading & Writing', '600']]) {
  289 |     await page.getByLabel(`${field} current score (optional)`, { exact: true }).fill(value!);
  290 |   }
  291 |   await page.getByLabel('Current-score date (optional)', { exact: true }).fill(scheduleDate(0));
  292 |   await page.getByLabel('Weekly study minutes', { exact: true }).fill('180');
  293 |   for (const day of ['Monday', 'Wednesday', 'Friday']) await page.getByRole('checkbox', { name: day, exact: true }).check();
  294 |   await page.getByRole('checkbox', { name: /I confirm these are my planning dates/ }).check();
  295 |   const saved = page.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/preparation/schedule'));
  296 |   await page.getByRole('button', { name: 'Save study plan', exact: true }).click();
  297 |   const reply = await saved; expect(reply.status()).toBe(200);
  298 |   const calendar = await reply.json() as StudyScheduleOut;
  299 |   expect(calendar.profile_id).toBe(savedProfileId); expect(calendar.revision).toBe(1);
  300 |   expect(calendar.schedule).toMatchObject({ readiness: 'not_assessed', latest_safe_exam_on: scheduleDate(70), timing: 'within_entered_buffers' });
  301 |   expect(calendar.settings?.target_scores).toEqual({ total: 1400, math: 700, reading_writing: 700 });
  302 |   const tasks = calendar.schedule!.tasks;
  303 |   const totals: Record<string, number> = {};
  304 |   for (const task of tasks.filter(item => item.minutes > 0)) {
  305 |     expect(task.due_on).not.toBe(scheduleDate(56));
  306 |     const weekday = new Date(`${task.due_on}T00:00:00Z`).getUTCDay(); expect([1, 3, 5]).toContain(weekday);
  307 |     const monday = new Date(`${task.due_on}T00:00:00Z`); monday.setUTCDate(monday.getUTCDate() - (weekday + 6) % 7);
  308 |     const week = monday.toISOString().slice(0, 10); totals[week] = (totals[week] ?? 0) + task.minutes;
  309 |   }
  310 |   expect(Object.keys(totals).length).toBeGreaterThan(4);
  311 |   for (const minutes of Object.values(totals)) expect(minutes).toBeLessThanOrEqual(180);
  312 |   await page.reload();
  313 |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  314 |   await expect(page.getByLabel('Total target', { exact: true })).toHaveValue('1400');
  315 |   await expect(page.getByText('Readiness: not assessed.', { exact: true })).toBeVisible();
  316 |   const firstTask = page.getByRole('checkbox', { name: /^Completed:/ }).first();
  317 |   const checked = page.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/preparation/schedule'));
  318 |   await firstTask.click(); expect((await checked).status()).toBe(200); await expect(firstTask).toBeChecked();
  319 |   const history = await page.request.get(`/api/profiles/${savedProfileId}/preparation/schedule`); expect(history.ok()).toBeTruthy();
  320 |   const receipt = await history.json() as StudyScheduleOut; expect(receipt.revision).toBe(2); expect(receipt.settings?.completed_task_ids).toHaveLength(1);
  321 |   const exported = await page.request.get(`/api/profiles/${savedProfileId}/export`); expect(exported.ok()).toBeTruthy();
  322 |   const document = await exported.json(); expect(document.counts.study_schedules).toBe(1); expect(document.study_schedules[0].settings).toEqual(receipt.settings);
  323 |   const profile = await page.request.get(`/api/profiles/${savedProfileId}`); expect(profile.ok()).toBeTruthy(); expect((await profile.json()).academics).toEqual(officialScores);
  324 |   const viewport = page.viewportSize();
  325 |   try {
  326 |     for (const width of [320, 390]) {
  327 |       await page.setViewportSize({ width, height: 844 });
  328 |       await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  329 |       const button = page.getByRole('button', { name: 'Save study plan', exact: true }); await button.scrollIntoViewIfNeeded();
  330 |       await expect.poll(() => button.evaluate(element => { const box = element.getBoundingClientRect(); const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2); return hit === element || Boolean(hit && element.contains(hit)); })).toBe(true);
  331 |       await page.screenshot({ path: shot(`study-schedule-mobile-${width}.png`), fullPage: false });
  332 |     }
  333 |   } finally { if (viewport) await page.setViewportSize(viewport); }
  334 |   await page.getByRole('heading', { name: 'Saved dated tasks', exact: true }).scrollIntoViewIfNeeded();
  335 |   await page.screenshot({ path: shot('study-schedule-timeline.png'), fullPage: false });
  336 | });
  337 | 
  338 | test('deadline risk and concurrent saved calendar remain explicit through the real UI and API', async () => {
  339 |   await page.getByLabel('First exam', { exact: true }).fill(scheduleDate(80));
  340 |   await page.getByRole('checkbox', { name: /I confirm these are my planning dates/ }).check();
  341 |   await page.getByRole('checkbox', { name: 'Rebuild the calendar and clear previous task checkmarks', exact: true }).check();
  342 |   const saved = page.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/preparation/schedule'));
  343 |   await page.getByRole('button', { name: 'Save study plan', exact: true }).click();
  344 |   expect((await saved).status()).toBe(200);
  345 |   await expect(page.getByText(/Timing: at risk/)).toBeVisible();
  346 |   const current = await page.request.get(`/api/profiles/${savedProfileId}/preparation/schedule`);
  347 |   const record = await current.json() as StudyScheduleOut;
  348 |   expect(record.schedule?.delivery_expected_on).toBe(scheduleDate(87));
  349 |   expect(record.schedule?.tasks.some(task => task.kind === 'delivery' && task.due_on > record.settings!.certificate_deadline)).toBe(true);
  350 |   const other = await page.request.put(`/api/profiles/${savedProfileId}/preparation/schedule`, { data: { expected_revision: record.revision, settings: { ...record.settings, weekly_minutes: 240, completed_task_ids: [] } } });
  351 |   expect(other.ok()).toBeTruthy();
  352 |   const conflict = page.waitForResponse(response => response.request().method() === 'PUT' && new URL(response.url()).pathname.endsWith('/preparation/schedule'));
  353 |   const rejectedTask = page.getByRole('checkbox', { name: /^Completed:/ }).first();
  354 |   await rejectedTask.click();
  355 |   expect((await conflict).status()).toBe(409);
  356 |   await expect(rejectedTask).not.toBeChecked();
  357 |   await expect(page.getByRole('checkbox', { name: 'I reviewed the latest saved version before replacing it', exact: true })).toBeVisible();
  358 |   await expect(page.getByLabel('Weekly study minutes', { exact: true })).toHaveValue('180');
  359 |   const unchanged = await page.request.get(`/api/profiles/${savedProfileId}/preparation/schedule`); expect((await unchanged.json()).settings.weekly_minutes).toBe(240);
  360 |   await expect(page.getByRole('button', { name: 'Save study plan', exact: true })).toBeDisabled();
  361 |   await page.screenshot({ path: shot('study-schedule-conflict.png'), fullPage: false });
  362 | });
  363 | 
  364 | test('dated opt-in materials preserve legacy settings and reopen the exact saved attempt after reload', async () => {
  365 |   await page.goto('/#/preparation');
  366 |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  367 |   const endpoint = `/api/profiles/${savedProfileId}/preparation/schedule`;
  368 |   const legacy = await page.request.get(endpoint); expect(legacy.ok()).toBeTruthy();
  369 |   const before = await legacy.json() as StudyScheduleOut;
  370 |   const calendarUrl = endpoint + '/learning-path';
  371 |   const initial = await page.request.get(calendarUrl); expect((await initial.json()).learning_path).toBeNull();
  372 |   await page.getByRole('button', { name: 'View learning calendar' }).click();
  373 |   const prepared = page.waitForResponse(reply => reply.request().method() === 'POST' && new URL(reply.url()).pathname.endsWith('/learning-path/preview'));
> 374 |   await page.getByRole('button', { name: 'Preview updated learning path' }).click();
      |                                                                             ^ Error: locator.click: Target page, context or browser has been closed
  375 |   const previewReply = await prepared; expect(previewReply.ok()).toBeTruthy();
  376 |   const preview = await previewReply.json() as import('../src/types').LearningPathOut;
  377 |   expect((await (await page.request.get(calendarUrl)).json()).learning_path).toBeNull();
  378 |   const dated = preview.learning_path!.schedule.tasks.filter(task => task.due_on >= preview.learning_path!.schedule.as_of).slice(0, 14)
  379 |     .find(task => task.learning_ref?.kind === 'lesson' && task.availability === 'available');
  380 |   const ref = dated?.learning_ref;
  381 |   if (!dated || !ref || ref.kind !== 'lesson') throw new Error('No visible dated exact lesson');
  382 |   const saved = page.waitForResponse(reply => reply.request().method() === 'PUT' && new URL(reply.url()).pathname.endsWith('/learning-path'));
  383 |   await page.getByRole('button', { name: 'Use this updated path' }).click();
  384 |   expect((await saved).ok()).toBeTruthy();
  385 |   const row = page.locator(`li[data-learning-task="${dated.id}"]`);
  386 |   const opened = page.waitForResponse(reply => reply.request().method() === 'GET' && new URL(reply.url()).pathname.endsWith(`/preparation/lessons/${ref.lesson_id}`));
  387 |   await row.getByRole('button', { name: 'Open lesson', exact: true }).click();
  388 |   const response = await opened; expect(response.ok()).toBeTruthy();
  389 |   expect(new URL(response.url()).searchParams.get('version')).toBe(ref.content_version);
  390 |   const lesson = await response.json() as import('../src/types').PreparationLesson;
  391 |   expect(lesson).toMatchObject({ id: ref.lesson_id, version: ref.content_version });
  392 |   for (const [index, question] of lesson.questions.entries()) {
  393 |     if ('answer_format' in question) await page.getByRole('textbox', { name: `Answer ${index + 1}`, exact: true }).fill('sample');
  394 |     else await page.locator('.preparation-question').nth(index).getByRole('radio').first().check();
  395 |   }
  396 |   const submitted = page.waitForResponse(reply => reply.request().method() === 'POST' && new URL(reply.url()).pathname.endsWith('/preparation/attempts'));
  397 |   await page.getByRole('button', { name: 'Submit practice', exact: true }).click();
  398 |   const submitReply = await submitted; expect(submitReply.ok()).toBeTruthy();
  399 |   const attempt = await submitReply.json() as import('../src/types').StudyAttempt;
  400 |   expect(attempt).toMatchObject({ profile_id: savedProfileId, lesson_id: ref.lesson_id, version: ref.content_version });
  401 |   await page.reload();
  402 |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  403 |   await page.getByRole('button', { name: 'View learning calendar' }).click();
  404 |   const restored = page.locator(`li[data-learning-task="${dated.id}"]`);
  405 |   await expect(restored.getByText('Saved submission — not mastery')).toBeVisible();
  406 |   const reviewed = page.waitForResponse(reply => reply.request().method() === 'GET' && new URL(reply.url()).pathname.endsWith(`/attempts/${attempt.attempt_id}/review`));
  407 |   await restored.getByRole('button', { name: 'Review my saved attempt' }).click();
  408 |   expect((await reviewed).ok()).toBeTruthy();
  409 |   await expect(page.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', attempt.attempt_id);
  410 |   expect((await (await page.request.get(endpoint)).json()).settings).toEqual(before.settings);
  411 |   expect((await (await page.request.get(`/api/profiles/${savedProfileId}`)).json()).academics).toEqual(officialScores);
  412 |   await page.screenshot({ path: shot('learning-calendar-exact-review.png'), fullPage: true });
  413 | });
  414 | 
```
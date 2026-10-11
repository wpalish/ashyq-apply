# Auth native test: saved tick setup review

**Read-only diagnosis; repair not applied or run by this reviewer.** First Auth terminal `execution/evidence/e2e/20261011T223420Z-auth/test.log` reports 8 passed, one failed at new `frontend/e2e/auth-journey.spec.ts:275`: `locator.check: Clicking the checkbox did not change its state`. The locator was visible and enabled; the test's `finally` closed its browser context after the failure, so its saved sign-in snapshot is cleanup state.

`StudySchedulePanel.tsx:189-204` renders the task checkbox from `task.completed`. Its change handler starts an asynchronous legacy schedule PUT; `write` replaces the record only after a successful response (`:157-168`). Playwright `.check()` demands a checked state immediately after its click, before that server-controlled state has been acknowledged. The existing Demo task-completion test uses `.click()`, waits for the real PUT, then expects the checkbox checked.

Narrow new Auth test adjustment: replace only `await firstTick.check()` with `await firstTick.click()`; retain the existing real PUT response and `ok()` assertion, then assert `await expect(firstTick).toBeChecked()` after the response (outside the conditional so an already-saved tick is covered). Keep the following server GET and `completed_task_ids.length > 0` assertion. Do not force a click, increase timeouts, mock the API, or change the production completion guard.

The first terminal did not reach calendar preview, explicit save, exact lesson, receipt, reload or second clean browser assertions. Their outcome remains unknown until a fresh complete Auth receipt is saved.

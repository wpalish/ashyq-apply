# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: preparation.spec.ts >> one shared route saves an exact real receipt and opens its own versioned materials after reload
- Location: ../../../../source/frontend/e2e/preparation.spec.ts:575:1

# Error details

```
Error: locator.click: Error: strict mode violation: getByRole('region', { name: 'Plan a shared route', exact: true }).locator('details').filter({ has: getByText('My saved attempt reviews', { exact: true }) }).locator('summary') resolved to 3 elements:
    1) <summary>My saved attempt reviews</summary> aka getByText('My saved attempt reviews')
    2) <summary>Show exact ID</summary> aka getByText('Show exact ID').nth(2)
    3) <summary>Show exact ID</summary> aka getByText('Show exact ID').nth(3)

Call log:
  - waiting for getByRole('region', { name: 'Plan a shared route', exact: true }).locator('details').filter({ has: getByText('My saved attempt reviews', { exact: true }) }).locator('summary')

```

# Page snapshot

```yaml
- generic [ref=f7e3]:
  - complementary [ref=f7e4]:
    - generic [ref=f7e5]: Unimatch
    - navigation "Main navigation" [ref=f7e7]:
      - button "Home" [ref=f7e8] [cursor=pointer]
      - button "Find" [ref=f7e12] [cursor=pointer]:
        - generic [ref=f7e16]: "20"
      - button "Plan" [ref=f7e17] [cursor=pointer]:
        - generic [ref=f7e21]: "2"
      - button "Exam preparation" [ref=f7e22] [cursor=pointer]
      - button "Documents" [ref=f7e26] [cursor=pointer]
      - button "Community" [ref=f7e30] [cursor=pointer]
    - generic [ref=f7e34]:
      - paragraph [ref=f7e35]:
        - text: Same students.
        - strong [ref=f7e36]: Bigger horizons.
      - group [ref=f7e37]:
        - generic "Preferences" [ref=f7e38] [cursor=pointer]
        - option "Match system"
        - option "Light" [selected]
        - option "Dark"
        - option "English" [selected]
        - option "Русский"
        - option "Қазақша"
  - generic [ref=f7e39]:
    - banner [ref=f7e40]:
      - generic [ref=f7e41]: Demo data
      - group [ref=f7e42]:
        - generic "Explore⌄" [ref=f7e43] [cursor=pointer]
      - generic [ref=f7e44]:
        - text: Applicant
        - combobox "Applicant" [ref=f7e45]:
          - option "New applicant"
          - option "Demo Applicant (synthetic) · 1 run" [selected]
          - option "Demo Applicant (synthetic) · 1 run"
          - option "Demo Applicant (synthetic) · 1 run"
          - option "Demo Applicant (synthetic) · 1 run"
      - button "New case" [ref=f7e46] [cursor=pointer]
      - button "Settings" [ref=f7e47] [cursor=pointer]
      - button "Sign out" [ref=f7e48] [cursor=pointer]
    - main "Exam preparation" [ref=f7e49]:
      - generic [ref=f7e50]:
        - generic [ref=f7e51]:
          - paragraph [ref=f7e52]: ORIGINAL PRACTICE · YOUR CASE
          - heading "Prepare for your next step." [level=1] [ref=f7e53]
          - paragraph [ref=f7e54]: Programme requirements, original practice and saved attempts. Practice does not change your official scores or establish admission readiness.
        - note [ref=f7e55]:
          - generic [ref=f7e56]:
            - strong [ref=f7e57]: Development starter access
            - paragraph [ref=f7e58]: Original IELTS Reading, SAT Math and SAT Reading & Writing practice units. This is not a full exam course or an official mock test.
            - paragraph [ref=f7e59]: Local preview access
        - navigation "Preparation views" [ref=f7e60]:
          - button "Goals & evidence" [ref=f7e61] [cursor=pointer]
          - button "Study plan" [ref=f7e62] [cursor=pointer]
          - button "Shared route" [pressed] [ref=f7e63] [cursor=pointer]
          - button "Practice" [ref=f7e64] [cursor=pointer]
          - button "Progress" [ref=f7e65] [cursor=pointer]
        - paragraph [ref=f7e66]: Unsubmitted answers stay only in this form. Leaving a lesson clears them.
        - generic [ref=f7e68]:
          - heading "Shared preparation route" [level=2] [ref=f7e70]
          - paragraph [ref=f7e71]: Choose your own programmes and exam dates. This route uses one weekly study budget for your selected exams.
          - region "Shared preparation route" [ref=f7e72]:
            - paragraph [ref=f7e73]: One shared weekly budget
            - status [ref=f7e74]: Browser draft restored or changed — it is not a server save. This tab keeps your personal inputs.
            - button "Reset this local route draft" [ref=f7e75] [cursor=pointer]
            - button "Refresh saved route" [ref=f7e76] [cursor=pointer]
            - group [ref=f7e77]:
              - generic "Earlier saved revisions" [ref=f7e78] [cursor=pointer]
            - region "Plan a shared route" [ref=f7e79]:
              - heading "Plan a shared route" [level=3] [ref=f7e80]
              - paragraph [ref=f7e81]: Select 2–20 of your own approved or maybe results in your preferred order. Suggestions below come only from the latest loaded run; an older saved result can be entered by ID. The server verifies every selection.
              - list [ref=f7e82]:
                - listitem [ref=f7e83]:
                  - text: Saved programme 1
                  - group [ref=f7e84]:
                    - generic "Show exact ID" [ref=f7e85] [cursor=pointer]
                    - text: e69a3e7079194c7bbcc058b537d65c9a
                  - button "Remove" [ref=f7e86] [cursor=pointer]
                  - button "Move earlier" [disabled] [ref=f7e87]
                - listitem [ref=f7e88]:
                  - text: Saved programme 2
                  - group [ref=f7e89]:
                    - generic "Show exact ID" [ref=f7e90] [cursor=pointer]
                    - text: bafa33483e82458a96816112630f227c
                  - button "Remove" [ref=f7e91] [cursor=pointer]
                  - button "Move earlier" [ref=f7e92] [cursor=pointer]
              - generic [ref=f7e93]:
                - generic [ref=f7e94]: Older saved result ID
                - textbox "Older saved result ID" [ref=f7e95]
                - paragraph [ref=f7e96]: Enter the exact ID from your own saved result. It is not assumed eligible until the server checks it.
                - button "Add saved ID" [disabled] [ref=f7e97]
              - generic [ref=f7e98]:
                - generic [ref=f7e99]:
                  - generic [ref=f7e100]: Planning starts on
                  - textbox "Planning starts on" [ref=f7e101]: 2026-10-13
                - generic [ref=f7e102]:
                  - generic [ref=f7e103]: Your time zone
                  - textbox "Your time zone" [ref=f7e104]: UTC
                - generic [ref=f7e105]:
                  - generic [ref=f7e106]: Minutes available each week across all exams
                  - spinbutton "Minutes available each week across all exams" [ref=f7e107]: "240"
              - group "Study days" [ref=f7e108]:
                - generic [ref=f7e110]:
                  - generic [ref=f7e111]:
                    - checkbox "Mon" [checked] [ref=f7e112]
                    - text: Mon
                  - generic [ref=f7e113]:
                    - checkbox "Tue" [checked] [ref=f7e114]
                    - text: Tue
                  - generic [ref=f7e115]:
                    - checkbox "Wed" [checked] [ref=f7e116]
                    - text: Wed
                  - generic [ref=f7e117]:
                    - checkbox "Thu" [checked] [ref=f7e118]
                    - text: Thu
                  - generic [ref=f7e119]:
                    - checkbox "Fri" [checked] [ref=f7e120]
                    - text: Fri
                  - generic [ref=f7e121]:
                    - checkbox "Sat" [ref=f7e122]
                    - text: Sat
                  - generic [ref=f7e123]:
                    - checkbox "Sun" [ref=f7e124]
                    - text: Sun
              - group "Digital SAT" [ref=f7e125]:
                - generic [ref=f7e127]:
                  - checkbox "Include this personal exam" [checked] [ref=f7e128]
                  - text: Include this personal exam
                - generic [ref=f7e129]:
                  - generic [ref=f7e130]:
                    - generic [ref=f7e131]: First exam date
                    - textbox "First exam date" [ref=f7e132]: 2026-12-11
                  - generic [ref=f7e133]:
                    - generic [ref=f7e134]: Retake date, if planned
                    - textbox "Retake date, if planned" [ref=f7e135]
                  - generic [ref=f7e136]:
                    - generic [ref=f7e137]: Date by which you want the certificate
                    - textbox "Date by which you want the certificate" [ref=f7e138]: 2027-01-10
                  - generic [ref=f7e139]:
                    - generic [ref=f7e140]: Days for results
                    - spinbutton "Days for results" [ref=f7e141]: "5"
                  - generic [ref=f7e142]:
                    - generic [ref=f7e143]: Delivery days
                    - spinbutton "Delivery days" [ref=f7e144]: "2"
                  - generic [ref=f7e145]:
                    - generic [ref=f7e146]: Safety buffer days
                    - spinbutton "Safety buffer days" [ref=f7e147]: "7"
                - group [ref=f7e148]:
                  - generic "Optional personal targets" [ref=f7e149] [cursor=pointer]
                - generic [ref=f7e150]:
                  - checkbox "I entered these personal dates and buffers myself" [checked] [ref=f7e151]
                  - text: I entered these personal dates and buffers myself
              - group "IELTS Academic" [ref=f7e152]:
                - generic [ref=f7e154]:
                  - checkbox "Include this personal exam" [checked] [ref=f7e155]
                  - text: Include this personal exam
                - button "Make this exam first in the allocation order" [ref=f7e156] [cursor=pointer]
                - generic [ref=f7e157]:
                  - generic [ref=f7e158]:
                    - generic [ref=f7e159]: First exam date
                    - textbox "First exam date" [ref=f7e160]: 2026-12-11
                  - generic [ref=f7e161]:
                    - generic [ref=f7e162]: Retake date, if planned
                    - textbox "Retake date, if planned" [ref=f7e163]
                  - generic [ref=f7e164]:
                    - generic [ref=f7e165]: Date by which you want the certificate
                    - textbox "Date by which you want the certificate" [ref=f7e166]: 2027-01-10
                  - generic [ref=f7e167]:
                    - generic [ref=f7e168]: Days for results
                    - spinbutton "Days for results" [ref=f7e169]: "5"
                  - generic [ref=f7e170]:
                    - generic [ref=f7e171]: Delivery days
                    - spinbutton "Delivery days" [ref=f7e172]: "2"
                  - generic [ref=f7e173]:
                    - generic [ref=f7e174]: Safety buffer days
                    - spinbutton "Safety buffer days" [ref=f7e175]: "7"
                - group [ref=f7e176]:
                  - generic "Optional personal targets" [ref=f7e177] [cursor=pointer]
                - generic [ref=f7e178]:
                  - checkbox "I entered these personal dates and buffers myself" [checked] [ref=f7e179]
                  - text: I entered these personal dates and buffers myself
              - group [ref=f7e180]:
                - generic "My saved attempt reviews" [ref=f7e181] [cursor=pointer]
              - generic [ref=f7e182]:
                - checkbox "I chose these programmes, study capacity and personal exam plans explicitly" [ref=f7e183]
                - text: I chose these programmes, study capacity and personal exam plans explicitly
              - paragraph [ref=f7e184]: Preview is unsaved. The lesson allocation is planning time, not a course completion or admission verdict.
              - button "Preview route" [ref=f7e185] [cursor=pointer]
```

# Test source

```ts
  516 |   await expect(requirement).toBeVisible();
  517 |   if (atom.original_check.explanation) {
  518 |     await expect(requirement.getByText(atom.original_check.explanation, { exact: true })).toBeVisible();
  519 |   }
  520 |   if (atom.unresolved_reasons.length) await expect(requirement.getByText('Unresolved evidence')).toBeVisible();
  521 |   await requirement.getByText('Source evidence', { exact: true }).click();
  522 |   if (atom.proofs.length) {
  523 |     await expect(requirement.getByText(atom.proofs[0]!.claim.original_text_excerpt, { exact: true })).toBeVisible();
  524 |     await expect(requirement.locator('a, code').filter({ hasText: atom.proofs[0]!.claim.source_url }).first()).toBeVisible();
  525 |     expect(atom.proofs[0]!.scope.requested).toEqual(graph.programmes[0]!.requested_scope);
  526 |   } else {
  527 |     await expect(requirement.getByText('No exact linked proof establishes this requirement.')).toBeVisible();
  528 |   }
  529 |   await expect(requirement.getByText(/Original stored references:/)).toBeVisible();
  530 |   await expect(requirement.getByText(/Exact resolved claim IDs:/)).toBeVisible();
  531 | 
  532 |   const viewport = page.viewportSize();
  533 |   try {
  534 |     for (const width of [320, 768, 1024, 1440]) {
  535 |       await page.setViewportSize({ width, height: 900 });
  536 |       await expect.poll(() => page.evaluate(() =>
  537 |         document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  538 |       await firstCard.scrollIntoViewIfNeeded();
  539 |       await page.screenshot({ path: shot(`g1-own-graph-${width}.png`), fullPage: true });
  540 |     }
  541 |   } finally { if (viewport) await page.setViewportSize(viewport); }
  542 | 
  543 |   let graphReadsAfterReload = 0;
  544 |   const observe = (request: import('@playwright/test').Request) => {
  545 |     if (request.method() === 'GET' && new URL(request.url()).pathname ===
  546 |       `/api/profiles/${savedProfileId}/preparation/graph`) graphReadsAfterReload += 1;
  547 |   };
  548 |   page.on('request', observe);
  549 |   try {
  550 |     await page.reload();
  551 |     await expect(page.getByRole('heading', { name: 'Compare programme requirements' })).toBeVisible();
  552 |     await expect(page.getByRole('group', { name: 'Programmes to compare' })
  553 |       .getByRole('checkbox', { checked: true })).toHaveCount(0);
  554 |     await expect(page.getByRole('button', { name: 'View combined evidence' })).toBeDisabled();
  555 |     expect(graphReadsAfterReload).toBe(0);
  556 |   } finally { page.off('request', observe); }
  557 | 
  558 |   const afterScheduleReply = await page.request.get(scheduleUrl);
  559 |   const afterSidecarReply = await page.request.get(sidecarUrl);
  560 |   const afterProgressReply = await page.request.get(progressUrl);
  561 |   expect(afterScheduleReply.ok()).toBeTruthy();
  562 |   expect(afterSidecarReply.ok()).toBeTruthy();
  563 |   expect(afterProgressReply.ok()).toBeTruthy();
  564 |   const afterSchedule = await afterScheduleReply.json() as import('../src/types').StudyScheduleOut;
  565 |   const afterSidecar = await afterSidecarReply.json() as import('../src/types').LearningPathOut;
  566 |   const afterProgress = await afterProgressReply.json() as import('../src/types').PreparationProgress;
  567 |   expect(afterSchedule.revision).toBe(beforeSchedule.revision);
  568 |   expect(afterSchedule.settings).toEqual(beforeSchedule.settings);
  569 |   expect(afterSidecar.revision).toBe(beforeSidecar.revision);
  570 |   expect(afterSidecar.learning_path?.draft.fingerprint).toBe(beforeSidecar.learning_path?.draft.fingerprint);
  571 |   expect(afterProgress.attempts.some(item => item.attempt_id === savedAttemptId)).toBe(true);
  572 | });
  573 | 
  574 | 
  575 | test('one shared route saves an exact real receipt and opens its own versioned materials after reload', async () => {
  576 |   await page.reload();
  577 |   const endpoint = `/api/profiles/${savedProfileId}/preparation/shared-route`;
  578 |   const before = await page.request.get(`/api/profiles/${savedProfileId}/export`);
  579 |   expect(before.ok()).toBeTruthy();
  580 |   const baseline = await before.json();
  581 |   expect(baseline.shared_route_current).toBeNull();
  582 |   expect(baseline.shared_route_history).toEqual([]);
  583 |   await page.goto('/#/shortlist');
  584 |   const savedCards = page.locator('.find-card').filter({ has: page.getByRole('button', { name: 'Saved', exact: true }) });
  585 |   await expect(savedCards.nth(1)).toBeVisible();
  586 |   const selectedIds: string[] = [];
  587 |   for (const card of [savedCards.nth(0), savedCards.nth(1)]) {
  588 |     const id = await card.getAttribute('data-testid');
  589 |     expect(id).toMatch(/^card-\S+$/); selectedIds.push(id!.slice(5));
  590 |   }
  591 |   await page.goto('/#/preparation');
  592 |   const nav = page.getByRole('navigation', { name: 'Preparation views' });
  593 |   await nav.getByRole('button', { name: 'Shared route', exact: true }).click();
  594 |   await expect(page.getByRole('heading', { name: 'Shared preparation route' })).toBeVisible();
  595 |   const form = page.getByRole('region', { name: 'Plan a shared route', exact: true });
  596 |   for (const id of selectedIds) {
  597 |     await form.getByLabel('Older saved result ID', { exact: true }).fill(id);
  598 |     await form.getByRole('button', { name: 'Add saved ID', exact: true }).click();
  599 |   }
  600 |   const date = (offset: number) => { const value = new Date(); value.setUTCDate(value.getUTCDate() + offset); return value.toISOString().slice(0, 10); };
  601 |   await form.getByLabel('Planning starts on', { exact: true }).fill(date(1));
  602 |   await form.getByLabel('Your time zone', { exact: true }).fill('UTC');
  603 |   await form.getByLabel('Minutes available each week across all exams', { exact: true }).fill('240');
  604 |   for (const exam of ['IELTS Academic', 'Digital SAT']) {
  605 |     const group = form.getByRole('group', { name: exam, exact: true });
  606 |     await group.getByLabel('Include this personal exam', { exact: true }).check();
  607 |     await group.getByLabel('First exam date', { exact: true }).fill(date(60));
  608 |     await group.getByLabel('Date by which you want the certificate', { exact: true }).fill(date(90));
  609 |     await group.getByLabel('Days for results', { exact: true }).fill('5');
  610 |     await group.getByLabel('Delivery days', { exact: true }).fill('2');
  611 |     await group.getByLabel('Safety buffer days', { exact: true }).fill('7');
  612 |     await group.getByLabel('I entered these personal dates and buffers myself', { exact: true }).check();
  613 |   }
  614 |   await form.getByRole('group', { name: 'Digital SAT', exact: true }).getByRole('button', { name: 'Make this exam first in the allocation order', exact: true }).click();
  615 |   const reviews = form.locator('details').filter({ has: page.getByText('My saved attempt reviews', { exact: true }) });
> 616 |   await reviews.locator('summary').click();
      |                                    ^ Error: locator.click: Error: strict mode violation: getByRole('region', { name: 'Plan a shared route', exact: true }).locator('details').filter({ has: getByText('My saved attempt reviews', { exact: true }) }).locator('summary') resolved to 3 elements:
  617 |   await reviews.locator('.row').filter({ hasText: savedAttemptId }).getByRole('button', { name: 'Add own review', exact: true }).click();
  618 |   await reviews.getByLabel('Exam stream', { exact: true }).selectOption('ielts_academic');
  619 |   await reviews.getByLabel('Minutes for this review', { exact: true }).fill('30');
  620 |   await form.getByLabel('I chose these programmes, study capacity and personal exam plans explicitly', { exact: true }).check();
  621 |   const previewPromise = page.waitForResponse(reply => reply.request().method() === 'POST' && new URL(reply.url()).pathname === `${endpoint}/preview`);
  622 |   await form.getByRole('button', { name: 'Preview route', exact: true }).click();
  623 |   const previewReply = await previewPromise;
  624 |   expect(previewReply.ok()).toBeTruthy();
  625 |   const preview = await previewReply.json() as import('../src/types').SharedRoutePreviewOutV1;
  626 |   expect(preview.saved).toBe(false); expect(preview.requested_result_ids).toEqual(selectedIds);
  627 |   expect(preview.allocation.ordered_exam_choices.map(item => item.exam)).toEqual(['digital_sat', 'ielts_academic']);
  628 |   expect(preview.allocation.slots.some(item => item.ref.kind === 'attempt_review' && item.ref.attempt_id === savedAttemptId)).toBe(true);
  629 |   for (const week of preview.allocation.capacity) expect(week.allocated_minutes).toBeLessThanOrEqual(240);
  630 |   const unsaved = await page.request.get(endpoint); expect(unsaved.ok()).toBeTruthy();
  631 |   expect((await unsaved.json()).revision).toBe(0);
  632 |   const savedPromise = page.waitForResponse(reply => reply.request().method() === 'PUT' && new URL(reply.url()).pathname === endpoint);
  633 |   await form.getByRole('button', { name: 'Save this exact preview', exact: true }).click();
  634 |   const savedReply = await savedPromise; expect(savedReply.ok()).toBeTruthy();
  635 |   const receipt = await savedReply.json() as import('../src/types').SharedRouteWriteReceiptV1;
  636 |   expect(receipt.profile_id).toBe(savedProfileId); expect(receipt.revision).toBe(1);
  637 |   expect(receipt.allocation_digest).toBe(preview.allocation.digest);
  638 |   const replay = await page.request.put(endpoint, { data: savedReply.request().postDataJSON() });
  639 |   expect(replay.ok()).toBeTruthy(); expect(await replay.json()).toEqual(receipt);
  640 |   await page.reload();
  641 |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Shared route', exact: true }).click();
  642 |   const current = page.getByRole('region', { name: 'Current saved route', exact: true });
  643 |   await expect(current).toContainText('Revision 1');
  644 |   const loaded = await page.request.get(endpoint); expect(loaded.ok()).toBeTruthy();
  645 |   expect((await loaded.json()).view.receipt).toEqual(receipt);
  646 |   const earlier = page.locator('details').filter({ has: page.getByText('Earlier saved revisions', { exact: true }) });
  647 |   await earlier.locator('summary').click();
  648 |   await earlier.getByLabel('Revision', { exact: true }).fill('1');
  649 |   await earlier.getByRole('button', { name: 'Open revision', exact: true }).click();
  650 |   await expect(page.getByRole('region', { name: 'Earlier saved route', exact: true })).toContainText('Revision 1');
  651 |   const viewport = page.viewportSize();
  652 |   try {
  653 |     for (const width of [320, 768, 1024, 1440]) {
  654 |       await page.setViewportSize({ width, height: 900 });
  655 |       await current.scrollIntoViewIfNeeded();
  656 |       await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  657 |       await page.screenshot({ path: shot(`g2-shared-route-${width}.png`), fullPage: true });
  658 |     }
  659 |   } finally { if (viewport) await page.setViewportSize(viewport); }
  660 |   const reviewReplyPromise = page.waitForResponse(reply => reply.request().method() === 'GET' && new URL(reply.url()).pathname.endsWith(`/preparation/attempts/${savedAttemptId}/review`));
  661 |   await current.getByRole('button', { name: 'Open my exact review', exact: true }).click();
  662 |   const reviewReply = await reviewReplyPromise; expect(reviewReply.ok()).toBeTruthy();
  663 |   expect((await reviewReply.json()).attempt.attempt_id).toBe(savedAttemptId);
  664 |   await expect(page.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', savedAttemptId);
  665 |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Study plan', exact: true }).click();
  666 |   const oldPlan = page.locator('details').filter({ has: page.getByText('Earlier personal study plan', { exact: true }) }).first();
  667 |   await oldPlan.locator('summary').click();
  668 |   await expect(oldPlan.getByRole('button', { name: 'Save study plan', exact: true })).toBeDisabled();
  669 |   const after = await page.request.get(`/api/profiles/${savedProfileId}/export`); expect(after.ok()).toBeTruthy();
  670 |   const exported = await after.json();
  671 |   expect(exported.shared_route_current).toEqual(receipt); expect(exported.shared_route_history).toEqual([receipt]);
  672 |   expect(exported.study_schedules).toEqual(baseline.study_schedules);
  673 |   expect(exported.study_attempts).toEqual(baseline.study_attempts);
  674 |   expect(exported.profile.academics).toEqual(baseline.profile.academics);
  675 | });
  676 | 
  677 | 
  678 | /** One lost browser ACK only: the loopback API really commits, then the route is aborted. */
  679 | test('an original lost-ACK command survives guarded navigation and same-tab reload without a second write', async () => {
  680 |   const endpoint = `/api/profiles/${savedProfileId}/preparation/shared-route`;
  681 |   const before = await page.request.get(`/api/profiles/${savedProfileId}/export`); expect(before.ok()).toBeTruthy();
  682 |   const baseline = await before.json();
  683 |   expect(baseline.shared_route_current.revision).toBe(1);
  684 |   await page.goto('/#/preparation');
  685 |   await page.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Shared route', exact: true }).click();
  686 |   const form = page.getByRole('region', { name: 'Plan a shared route', exact: true });
  687 |   await expect(form.getByLabel('Minutes available each week across all exams', { exact: true })).toHaveValue('240');
  688 |   await form.getByLabel('Minutes available each week across all exams', { exact: true }).fill('250');
  689 |   const previewPromise = page.waitForResponse(reply => reply.request().method() === 'POST' && new URL(reply.url()).pathname === `${endpoint}/preview`);
  690 |   await form.getByRole('button', { name: 'Preview route', exact: true }).click();
  691 |   const previewResponse = await previewPromise; expect(previewResponse.ok()).toBeTruthy();
  692 |   const preview = await previewResponse.json() as import('../src/types').SharedRoutePreviewOutV1;
  693 |   expect(preview.expected_shared_revision).toBe(1); expect(preview.saved).toBe(false);
  694 |   let original: import('../src/types').SharedRouteWriteV1 | null = null;
  695 |   let accepted: import('../src/types').SharedRouteWriteReceiptV1 | null = null;
  696 |   let faults = 0; let writesAfterPreview = 0; let previewsAfterPreview = 0;
  697 |   const observe = (request: import('@playwright/test').Request) => {
  698 |     const url = new URL(request.url());
  699 |     if (url.pathname === endpoint && request.method() === 'PUT') ++writesAfterPreview;
  700 |     if (url.pathname === `${endpoint}/preview` && request.method() === 'POST') ++previewsAfterPreview;
  701 |   };
  702 |   const intercepted = (url: URL) => url.pathname === endpoint;
  703 |   page.on('request', observe);
  704 |   await page.route(intercepted, async route => {
  705 |     if (route.request().method() !== 'PUT' || faults !== 0) { await route.continue(); return; }
  706 |     const url = new URL(route.request().url());
  707 |     expect(['127.0.0.1', 'localhost', '[::1]']).toContain(url.hostname);
  708 |     ++faults;
  709 |     original = route.request().postDataJSON() as import('../src/types').SharedRouteWriteV1;
  710 |     const real = await route.fetch(); // Native own synthetic API, no invented receipt or response fulfillment.
  711 |     expect(real.ok()).toBeTruthy();
  712 |     accepted = await real.json() as import('../src/types').SharedRouteWriteReceiptV1;
  713 |     await test.info().attach('g2-recovery-forwarded-native-ack.json', {
  714 |       body: JSON.stringify({ url: url.pathname, status: real.status(), original_command: original, actual_receipt: accepted }, null, 2),
  715 |       contentType: 'application/json',
  716 |     });
```
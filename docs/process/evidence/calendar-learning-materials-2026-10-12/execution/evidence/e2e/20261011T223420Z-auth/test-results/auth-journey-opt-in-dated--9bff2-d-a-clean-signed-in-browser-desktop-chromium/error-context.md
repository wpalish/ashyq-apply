# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth-journey.spec.ts >> opt-in dated material and own receipt persist through reload and a clean signed-in browser
- Location: ../../../../source/frontend/e2e/auth-journey.spec.ts:230:1

# Error details

```
Error: locator.check: Clicking the checkbox did not change its state
Call log:
  - waiting for getByRole('checkbox', { name: /^Completed:/ }).first()
    - locator resolved to <input type="checkbox" aria-label="Completed: Arrange a component diagnostic and record its dated baseline; starter totals are not official scores (2026-10-12)"/>
  - attempting click action
    - waiting for element to be visible, enabled and stable
    - element is visible, enabled and stable
    - scrolling into view if needed
    - done scrolling
    - performing click action
    - click action done
    - waiting for scheduled navigations to finish
    - navigations have finished

```

# Page snapshot

```yaml
- main [ref=f2e3]:
  - generic [ref=f2e4]:
    - generic [ref=f2e5]:
      - img "A small Unimatch robot overlooks a university and a mountain lake" [ref=f2e6]
      - generic [ref=f2e7]:
        - generic [ref=f2e8]: SAME STUDENTS. BIGGER HORIZONS.
        - heading [level=1] [ref=f2e9]:
          - text: Global opportunitiesstart with
          - emphasis [ref=f2e10]: you.
        - paragraph [ref=f2e11]: Personalized research. Real information. A clearer path.
    - generic [ref=f2e12]:
      - generic [ref=f2e13]:
        - link "Unimatch" [ref=f2e14] [cursor=pointer]:
          - /url: "#/welcome"
        - tablist "Account" [ref=f2e15]:
          - tab "Sign in" [selected] [ref=f2e16] [cursor=pointer]
          - tab "Create account" [ref=f2e17] [cursor=pointer]
        - heading "Welcome back." [level=1] [ref=f2e18]
        - paragraph [ref=f2e19]: Applicant records belong to your workspace. University searches can use your degree, subject and intake preferences. Your name, contacts, grades and budget are excluded from those search queries.
      - generic [ref=f2e20]:
        - generic [ref=f2e21]: Email
        - textbox "Email" [ref=f2e22]
      - generic [ref=f2e23]:
        - generic [ref=f2e24]: Password
        - textbox "Password" [ref=f2e25]
      - button "Sign in" [ref=f2e26] [cursor=pointer]
      - button "I forgot my password" [disabled] [ref=f2e27]
      - button "Create a new workspace" [ref=f2e28] [cursor=pointer]
      - link "Privacy & terms · Drafts awaiting legal review" [ref=f2e29] [cursor=pointer]:
        - /url: "#/legal"
```

# Test source

```ts
  175 |     const response = await first.request.get(`/api/preparation/catalogue?catalogue_version=${packVersion}`);
  176 |     expect(response.ok()).toBeTruthy();
  177 |     const pack = await response.json();
  178 |     const completion = pack.lessons.find((lesson: { id: string }) => lesson.id === 'ielts-reading-completion-1');
  179 |     expect(completion.version).toBe(packVersion);
  180 |     await first.goto('/#/preparation');
  181 |     await first.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Practice', exact: true }).click();
  182 |     const opened = first.waitForResponse(item => item.request().method() === 'GET' && new URL(item.url()).pathname.endsWith('/preparation/lessons/ielts-reading-completion-1'));
  183 |     await first.getByRole('button', { name: `Start ${completion.title}`, exact: true }).click();
  184 |     const lesson = await opened; expect(lesson.ok()).toBeTruthy();
  185 |     profileId = new URL(lesson.url()).pathname.split('/')[3]!;
  186 |     const profile = await first.request.get(`/api/profiles/${profileId}`); expect(profile.ok()).toBeTruthy();
  187 |     academics = (await profile.json()).academics;
  188 |     const schedule = await first.request.get(`/api/profiles/${profileId}/preparation/schedule`); expect(schedule.ok()).toBeTruthy();
  189 |     calendar = await schedule.json();
  190 |     for (const [index, answer] of ['dividers', '36', 'SHEET.', 'briefing', 'code'].entries()) {
  191 |       await first.getByRole('textbox', { name: `Answer ${index + 1}`, exact: true }).fill(answer);
  192 |     }
  193 |     const saved = first.waitForResponse(item => item.request().method() === 'POST' && new URL(item.url()).pathname.endsWith('/preparation/attempts'));
  194 |     await first.getByRole('button', { name: 'Submit practice', exact: true }).click();
  195 |     const submitted = await saved; expect(submitted.ok()).toBeTruthy();
  196 |     const attempt = await submitted.json();
  197 |     expect(attempt).toMatchObject({ profile_id: profileId, version: packVersion, lesson_id: 'ielts-reading-completion-1', correct: 5, total: 5 });
  198 |     savedAttemptId = attempt.attempt_id;
  199 |     await expect(first.getByTestId('practice-result')).toHaveText('5 / 5 correct — practice only');
  200 |   } finally { await first.context().close(); }
  201 | 
  202 |   const second = await newSession(browser);
  203 |   try {
  204 |     await signIn(second);
  205 |     await second.goto('/#/preparation');
  206 |     await second.getByRole('navigation', { name: 'Preparation views' }).getByRole('button', { name: 'Progress', exact: true }).click();
  207 |     await second.locator(`[data-testid="review-attempt"][data-attempt-id="${savedAttemptId}"]`).click();
  208 |     await expect(second.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', savedAttemptId);
  209 |     const review = second.getByRole('region', { name: 'Saved attempt review' });
  210 |     await expect(review.getByText('Your answer: SHEET.', { exact: true })).toBeVisible();
  211 |     await expect(review.getByTestId('feedback-item')).toHaveCount(5);
  212 |     const progress = await second.request.get(`/api/profiles/${profileId}/preparation/progress?catalogue_version=${packVersion}`);
  213 |     expect(progress.ok()).toBeTruthy();
  214 |     const history = await progress.json();
  215 |     expect(history.completed_lessons).toContainEqual({ lesson_id: 'ielts-reading-completion-1', version: packVersion });
  216 |     expect(history.attempts.some((attempt: { attempt_id: string }) => attempt.attempt_id === savedAttemptId)).toBe(true);
  217 |     const profile = await second.request.get(`/api/profiles/${profileId}`); expect((await profile.json()).academics).toEqual(academics);
  218 |     const schedule = await second.request.get(`/api/profiles/${profileId}/preparation/schedule`); expect(await schedule.json()).toEqual(calendar);
  219 |     await second.screenshot({ path: shot('auth-learning-path-second-session.png'), fullPage: true });
  220 |   } finally { await second.context().close(); }
  221 | });
  222 | 
  223 | /*
  224 |  * Proposal: append this test to frontend/e2e/auth-journey.spec.ts after its
  225 |  * existing tests. It uses that file's expect, test, Page, newSession and shot
  226 |  * imports, serial account EMAIL/PASSWORD, and the auth-enabled Playwright config.
  227 |  * It is intentionally not a standalone spec because playwright.auth.config.ts
  228 |  * matches only auth-journey.spec.ts. No route stubs or provider calls are used.
  229 |  */
  230 | test('opt-in dated material and own receipt persist through reload and a clean signed-in browser', async ({ browser }) => {
  231 |   test.setTimeout(180_000);
  232 |   const first = await newSession(browser);
  233 |   const signIn = async (session: Page) => {
  234 |     await session.goto('/#/sign-in');
  235 |     await session.getByTestId('auth-email').fill(EMAIL);
  236 |     await session.getByTestId('auth-password').fill(PASSWORD);
  237 |     await session.getByTestId('auth-submit').click();
  238 |     await expect(session.getByRole('heading', { name: 'Good to see you.' })).toBeVisible();
  239 |   };
  240 |   const showSavedTask = async (session: Page, id: string) => {
  241 |     const row = session.locator(`li[data-learning-task="${id}"]`);
  242 |     await expect(row).toBeAttached();
  243 |     if (!(await row.isVisible())) {
  244 |       await session.locator('summary').filter({ hasText: 'Other dated tasks, including past dates' }).click();
  245 |     }
  246 |     await expect(row).toBeVisible();
  247 |     return row;
  248 |   };
  249 |   let profileId = '';
  250 |   let savedRevision = 0;
  251 |   let receiptUuid = '';
  252 |   let datedTaskId = '';
  253 |   let exactLessonId = '';
  254 |   let exactVersion = '';
  255 |   let originalSettings: import('../src/types').ScheduleSettings | null = null;
  256 |   let originalScores: unknown;
  257 |   try {
  258 |     await signIn(first);
  259 |     await first.goto('/#/preparation');
  260 |     const legacyLoaded = first.waitForResponse(reply => reply.request().method() === 'GET'
  261 |       && /\/preparation\/schedule$/.test(new URL(reply.url()).pathname));
  262 |     await first.getByRole('navigation', { name: 'Preparation views' })
  263 |       .getByRole('button', { name: 'Study plan', exact: true }).click();
  264 |     const legacyReply = await legacyLoaded;
  265 |     expect(legacyReply.ok()).toBeTruthy();
  266 |     profileId = new URL(legacyReply.url()).pathname.split('/')[3]!;
  267 | 
  268 |     // The earlier serial auth test saves this synthetic account's legacy plan.
  269 |     // Add a self-reported tick so the v2 path must preserve visible v1 history.
  270 |     const firstTick = first.getByRole('checkbox', { name: /^Completed:/ }).first();
  271 |     await expect(firstTick).toBeVisible();
  272 |     if (!(await firstTick.isChecked())) {
  273 |       const tickSaved = first.waitForResponse(reply => reply.request().method() === 'PUT'
  274 |         && /\/preparation\/schedule$/.test(new URL(reply.url()).pathname));
> 275 |       await firstTick.check();
      |                       ^ Error: locator.check: Clicking the checkbox did not change its state
  276 |       expect((await tickSaved).ok()).toBeTruthy();
  277 |     }
  278 |     const before = await first.request.get(`/api/profiles/${profileId}/preparation/schedule`);
  279 |     expect(before.ok()).toBeTruthy();
  280 |     const legacy = await before.json() as import('../src/types').StudyScheduleOut;
  281 |     originalSettings = legacy.settings;
  282 |     expect(originalSettings?.completed_task_ids.length).toBeGreaterThan(0);
  283 |     const profile = await first.request.get(`/api/profiles/${profileId}`);
  284 |     expect(profile.ok()).toBeTruthy(); originalScores = (await profile.json()).academics;
  285 | 
  286 |     const sidecarUrl = `/api/profiles/${profileId}/preparation/schedule/learning-path`;
  287 |     const emptyRead = await first.request.get(sidecarUrl);
  288 |     expect(emptyRead.ok()).toBeTruthy();
  289 |     expect((await emptyRead.json()).learning_path).toBeNull();
  290 |     await first.getByRole('button', { name: 'View learning calendar' }).click();
  291 |     await expect(first.getByRole('heading', { name: 'Learning calendar' })).toBeVisible();
  292 |     await expect(first.getByRole('button', { name: 'Use this updated path' })).toHaveCount(0);
  293 | 
  294 |     const previewed = first.waitForResponse(reply => reply.request().method() === 'POST'
  295 |       && /\/preparation\/schedule\/learning-path\/preview$/.test(new URL(reply.url()).pathname));
  296 |     await first.getByRole('button', { name: 'Preview updated learning path' }).click();
  297 |     const previewReply = await previewed;
  298 |     expect(previewReply.ok()).toBeTruthy();
  299 |     const preview = await previewReply.json() as import('../src/types').LearningPathOut;
  300 |     expect(preview.profile_id).toBe(profileId);
  301 |     expect(preview.revision).toBe(legacy.revision);
  302 |     expect(preview.learning_path?.legacy_settings).toEqual(originalSettings);
  303 |     const upcoming = preview.learning_path!.schedule.tasks
  304 |       .filter(task => task.due_on >= preview.learning_path!.schedule.as_of).slice(0, 14);
  305 |     const dated = upcoming.find(task => task.learning_ref?.kind === 'lesson' && task.availability === 'available');
  306 |     expect(dated).toBeDefined();
  307 |     const ref = dated?.learning_ref;
  308 |     if (!dated || !ref || ref.kind !== 'lesson') throw new Error('No visible exact dated lesson in preview');
  309 |     datedTaskId = dated.id; exactLessonId = ref.lesson_id; exactVersion = ref.content_version;
  310 |     expect(ref.id).toBe(`lesson:${exactLessonId}:${exactVersion}`);
  311 |     await expect(first.locator(`li[data-learning-task="${datedTaskId}"]`)).toContainText(dated.due_on);
  312 |     const stillEmpty = await first.request.get(sidecarUrl);
  313 |     expect((await stillEmpty.json()).learning_path).toBeNull();
  314 | 
  315 |     const saved = first.waitForResponse(reply => reply.request().method() === 'PUT'
  316 |       && /\/preparation\/schedule\/learning-path$/.test(new URL(reply.url()).pathname));
  317 |     await first.getByRole('button', { name: 'Use this updated path' }).click();
  318 |     const saveReply = await saved;
  319 |     expect(saveReply.ok()).toBeTruthy();
  320 |     const accepted = await saveReply.json() as import('../src/types').LearningPathOut;
  321 |     expect(accepted.profile_id).toBe(profileId);
  322 |     expect(accepted.revision).toBe(legacy.revision + 1);
  323 |     expect(accepted.learning_path?.draft.fingerprint).toBe(preview.learning_path?.draft.fingerprint);
  324 |     savedRevision = accepted.revision;
  325 |     const legacyAfterSave = await first.request.get(`/api/profiles/${profileId}/preparation/schedule`);
  326 |     expect((await legacyAfterSave.json()).settings).toEqual(originalSettings);
  327 | 
  328 |     const row = await showSavedTask(first, datedTaskId);
  329 |     const lessonOpened = first.waitForResponse(reply => reply.request().method() === 'GET'
  330 |       && new URL(reply.url()).pathname.endsWith(`/preparation/lessons/${exactLessonId}`));
  331 |     await row.locator(`button[data-learning-ref="lesson:${exactLessonId}:${exactVersion}"]`).click();
  332 |     const lessonReply = await lessonOpened;
  333 |     expect(lessonReply.ok()).toBeTruthy();
  334 |     expect(new URL(lessonReply.url()).searchParams.get('version')).toBe(exactVersion);
  335 |     const lesson = await lessonReply.json() as import('../src/types').PreparationLesson;
  336 |     expect(lesson).toMatchObject({ id: exactLessonId, version: exactVersion });
  337 |     await expect(first.getByRole('heading', { name: lesson.title, exact: true })).toBeVisible();
  338 |     for (const [index, question] of lesson.questions.entries()) {
  339 |       if ('answer_format' in question) {
  340 |         await first.getByRole('textbox', { name: `Answer ${index + 1}`, exact: true }).fill('sample');
  341 |       } else {
  342 |         await first.locator('.preparation-question').nth(index).getByRole('radio').first().check();
  343 |       }
  344 |     }
  345 |     const submitted = first.waitForResponse(reply => reply.request().method() === 'POST'
  346 |       && /\/preparation\/attempts$/.test(new URL(reply.url()).pathname));
  347 |     await first.getByRole('button', { name: 'Submit practice', exact: true }).click();
  348 |     const submitReply = await submitted;
  349 |     expect(submitReply.ok()).toBeTruthy();
  350 |     const attempt = await submitReply.json() as import('../src/types').StudyAttempt;
  351 |     expect(attempt).toMatchObject({ profile_id: profileId, lesson_id: exactLessonId, version: exactVersion });
  352 |     receiptUuid = attempt.attempt_id;
  353 |     await expect(first.getByTestId('practice-result')).toHaveAttribute('data-attempt-id', receiptUuid);
  354 | 
  355 |     await first.getByRole('navigation', { name: 'Preparation views' })
  356 |       .getByRole('button', { name: 'Study plan', exact: true }).click();
  357 |     await first.getByRole('button', { name: 'View learning calendar' }).click();
  358 |     const receiptRow = await showSavedTask(first, datedTaskId);
  359 |     await expect(receiptRow.getByText('Saved submission — not mastery')).toBeVisible();
  360 |     const reviewed = first.waitForResponse(reply => reply.request().method() === 'GET'
  361 |       && new URL(reply.url()).pathname.endsWith(`/preparation/attempts/${receiptUuid}/review`));
  362 |     await receiptRow.getByRole('button', { name: 'Review my saved attempt' }).click();
  363 |     const reviewReply = await reviewed;
  364 |     expect(reviewReply.ok()).toBeTruthy();
  365 |     const ownReview = await reviewReply.json() as import('../src/types').PreparationAttemptReview;
  366 |     expect(ownReview.attempt).toMatchObject({ profile_id: profileId, attempt_id: receiptUuid,
  367 |       lesson_id: exactLessonId, version: exactVersion });
  368 |     await expect(first.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', receiptUuid);
  369 | 
  370 |     await first.reload();
  371 |     await first.getByRole('navigation', { name: 'Preparation views' })
  372 |       .getByRole('button', { name: 'Study plan', exact: true }).click();
  373 |     await first.getByRole('button', { name: 'View learning calendar' }).click();
  374 |     await expect((await showSavedTask(first, datedTaskId))
  375 |       .getByRole('button', { name: 'Review my saved attempt' })).toBeVisible();
```
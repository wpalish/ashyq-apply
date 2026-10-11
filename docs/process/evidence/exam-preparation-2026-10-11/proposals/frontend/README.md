# Exam preparation frontend — proposed, not applied

Status: **READY for root review/application; runtime/typecheck/lint/build/Vitest/browser NOT_RUN by this author.**

Source boundary: `integration-2026-10-11/source`, app base `1d5a622d`; root reported `11091904` as documentation-only. No Git, source edits, preview/runtime, browser, provider, real account or gate action. Original native assertions were not changed. `CURRENT_SOURCE_CHECK.json` verifies the seven original source paths remained byte-exact at seal; `SOURCE_INPUTS.json` pins the copied originals. New test/support files are additions only. Root remains the sole integration writer.

## Proposed production paths

1. `frontend/src/App.tsx`: new `#/preparation` address and primary navigation; Home/Plan/Billing callbacks use the native screen state/focus behavior.
2. `frontend/src/screens/HomeScreen.tsx`: preparation entry under Explore your path; real research next-step logic unchanged.
3. `frontend/src/screens/ApprovedScreen.tsx`: preparation entry for chosen/considering programmes, with a safe empty-plan entry. Document collection semantics stay unchanged.
4. `frontend/src/screens/BillingScreen.tsx`: bounded inclusion claim only from optional current-case server `preparation_access`; no inferred access from quota or research entitlement; explicit development wording.
5. `frontend/src/screens/PreparationScreen.tsx`: Goals & evidence / Practice / Progress in one saved-case screen. Available original lessons first, six exam information cards below. Planned TOEFL/DET/HSK/CSCA are external metadata with no fictional local practice.
6. `frontend/src/api/client.ts`: six preparation methods through existing cookie/owner request wrapper; encoded identifiers/version. Nested preparation 402 message/code is retained; it is not a case-unlock checkout.
7. `frontend/src/types.ts`: exact preparation DTOs, optional Billing access, optional recorded ClaimScope matching native backend dimensions. Absent or unstated scope does not cover everyone.
8. `frontend/src/lib/i18n.ts`: route label in existing EN/RU/KK dictionaries. New screen body follows the existing English product flow; complete new-body localization is not claimed.

No dependency, package/config, CSS, store, ownership-storage or privacy-reset changes. Existing motion/reduced-motion and native main focus are inherited. No independent search/official evidence engine is introduced.

## Functionality and limits

- Goals shows stored evidence for a chosen/considering programme, including unknown/locked/stale/conflicted, waiver/optional/alternatives, original excerpts, source URLs, published scope and recorded applicant qualifications. A locked response never reveals its checks. It does not fetch/reassess evidence, fabricate requirements, collapse component thresholds, or create a persistent numeric goal. Source/check references stay internal.
- Preparation access comes from a saved-case API response independently of `full_access` or remaining research cases. Valid ACTIVE/EXHAUSTED started terms may grant bounded starters. Payments-disabled access says Development. Case-unlock is not a preparation solution.
- The three original starter tracks are IELTS Reading, SAT Math, SAT Reading & Writing. Server-delivered question count/content/version/answer feedback are used; no official questions, full course, official mock, scaled score, admission probability or readiness guarantee.
- The API saves **submitted attempts**, not unsubmitted drafts. Answers are only in the current form until submit succeeds. Leaving/restarting clears that form. The screen does not promise refresh retention for unsubmitted answers.
- UUID and immutable full payload are captured before the first await; a ref excludes double submit. Network retry retains the UUID/payload; explicit restart/new lesson resets the attempt. Successful feedback requires matching profile/lesson/version/UUID. API progress is refreshed after accepted submit, on Progress entry, or explicitly; newest same-case refresh wins.
- Account/profile/caseEpoch remount and case-loading entry remove old case content. Async success/catch/finally check the live captured storage owner, including the pre-remount microtask window. Programme/lesson replacement rejects stale intent. Old case submits may persist on the server, but cannot reveal their questions/feedback/history in the new case.
- Signed-out context and unsaved case make no preparation requests. History remains available after term expiry. Server error is shown without fabricated success. Personal practice without programme evidence is labelled unknown.

Backend contract is frozen here in `inputs/backend-CONTRACT.md` (SHA `681cca32ae0ed6d96e0e149d379ec3916e65b639f55a29ad51c81bd0ad6c3809`), agreed with backend author. Exact client obligations are in `CLIENT_CONTRACT.md`.

## Retained new native controls — 32, NOT_RUN

| New path | Explicit test cases | Meaningful scope |
|---|---:|---|
| `frontend/src/screens/PreparationScreen.test.tsx` | 16 | Missing case/principal, access/quota independence, expired readable history, locked defense, waiver/scoped evidence, readable components, programme race, planned metadata, immutable UUID/double submit/retry/new attempt, case-loading + late lesson, late case submit, storage-owner change before remount, stale access failure, newer lesson intent, mixed-case history, latest history refresh |
| `frontend/src/api/client.preparation.test.ts` | 7 | Exact encoded URLs/version/limit, cookie mode, immutable POST body replay, nested education 402 vs retained native case-paywall contract, stale owner before fetch/after response, null result query |
| `frontend/src/App.preparation.test.tsx` | 5 | Native nav/hash/focus/current marker, deep link without research, Home next-step preservation, Plan selected programme + document control, empty-plan safe entry |
| `frontend/src/screens/BillingScreen.preparation.test.tsx` | 4 | Missing prep metadata does not advertise, quota exhausted yet explicit education access, honest development wording, A→B entitlement isolation |

`frontend/src/screens/preparationFixtures.ts` is synthetic typed unit support, using `example.test` links and one-question controls to test component state. It is not the actual three-question backend content and does not count as native end-to-end validation. Component tests mock only stated API calls; unexpected fetch throws and is asserted unused. Client tests use fake fetch explicitly. Actual API→database→reload Playwright acceptance is owned by root separately.

## Stable native E2E selectors

- `data-testid="nav-preparation"`, English primary label **Exam preparation**, route `#/preparation`.
- h1 **Prepare for your next step.**; main accessible name **Exam preparation** on a normal route change.
- nav `aria-label="Preparation views"`; button names **Goals & evidence**, **Practice**, **Progress**, with `aria-pressed`.
- select **Programme evidence**, ID `preparation-programme`; options keep university/programme/intake.
- Server-backed lesson button names:
  - **Start Reading: stated evidence and inference**
  - **Start Math: linear relations and proportional reasoning**
  - **Start Reading and Writing: evidence and sentence clarity**
- Native fieldset legends `${index + 1}. ${question.prompt}` and radio names equal server choice text. All questions must be answered.
- **Submit practice**, pending **Submitting…**, error **Retry same submission**; status **Practice saved.** only on accepted response.
- section accessible name **Practice feedback**; `data-testid="practice-result"` and `data-attempt-id` (internal automation marker), text `${correct} / ${total} correct — practice only`.
- **Start a new attempt** after success, or **Restart lesson with a new attempt** before success.
- Progress h2 **Your saved practice**, `data-testid="progress-summary"`, **Refresh saved history**.

## Static React review

Applied `vercel:react-best-practices` by source inspection: parallel independent reads, primitive effect dependencies, guarded transient refs, functional state updates, separate case/session children, native buttons/select/fieldset/legend/radios/status/alert, no raw HTML or new dependencies. Existing screen main focus is retained. No lint/type/runtime PASS is asserted; root must execute native gates on applied exact bytes.

## Handoff

Root can review `preparation-frontend.patch` and apply the exact `files/` paths against the pinned originals. Do not replace unrelated trees or tests. Root should run native typecheck/lint/build/Vitest and real synthetic local Playwright preparation attempt→reload, followed by existing demo/auth controls. This proposal is not primary integration, deployment, production access verification, legal acceptance or course completeness.

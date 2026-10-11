# Original learning path — isolated frontend proposal

**PROPOSED_FOR_ROOT_REVIEW_AND_APPLY.** Ten paths; no primary/source/Git writes, real accounts, browser, server, provider or network operation. Root is the only source writer. These focused offline receipts do not qualify a whole product, native E2E, deployed UI, pedagogy, diagnosis or search quality.

## Behaviour

- Opt into the nine-lesson catalogue/progress `learning-pack-2026-10-11-v1`. Request each summary's exact version, preserving the old starter versions and no-argument client URLs. Render track order from `lesson_ids`, not the summary array. Saved indicators are version-qualified submissions; incorrect attempts are still submissions, never mastery.
- Keep existing Start button labels and `Original starter lessons` heading. Describe the sequence as original practice units, explicitly not full IELTS/SAT courses. A server-accepted attempt enables `Next lesson: <title>`; an explicit new lesson/attempt clears old answers, feedback and UUID.
- Add bounded accessible short-text input alongside unchanged radios. Preserve all original words/case/spacing in the immutable request; normalization/grading stays on the server. Double submit and failed-response retry reuse the same complete UUID/payload. Match accepted case/lesson/version/UUID/ordered answer IDs and values before announcing saved results.
- Show selected answer, accepted/correct answer and explanation, with incorrect feedback first. History reads the owned `/attempts/{attempt_uuid}/review` endpoint after expiry. Use its exact immutable lesson or explicitly show missing original metadata with stored IDs/feedback; never substitute current-version question text. Same pending/resolved review selection is a no-op; failure allows explicit retry. Case/mount/shared-owner/newer-intent fences guard all late data.
- `TeachingText` safely renders the finite actual student-text subset: headings, paragraphs, lists, pipe tables, bold/emphasis/code via escaped React. No HTML/URL execution, general Markdown engine, dependency or answer-key handling. Unsupported syntax remains literal. Short inputs retain ≥44px height; tables scroll within a keyboard-accessible region and long words wrap.
- StudySchedulePanel, pure calendar/task IDs/manual dates/buffers/checkmarks, official Academics, research quota and billing are unchanged. Existing dated starter links enter the ordered unit; practice never auto-completes a dated task or claims a target band.

## Exact files

Five production paths:

- `frontend/src/types.ts` — additive legacy/short unions, optional opt-in summary/progress metadata and owned review DTO.
- `frontend/src/api/client.ts` — optional catalogue query and owned review read; original transport/privacy code remains intact.
- `frontend/src/screens/PreparationScreen.tsx` — ordered path, per-summary versions, inputs/receipts/review/fences.
- `frontend/src/components/TeachingText.tsx` — dependency-free finite renderer.
- `frontend/src/styles/unimatch.css` — scoped input/list/contained table styles only.

Five test/support paths:

- `frontend/src/screens/preparationFixtures.ts`
- `frontend/src/screens/PreparationScreen.test.tsx`
- `frontend/src/screens/PreparationScreen.learningPath.test.tsx`
- `frontend/src/api/client.learningPath.test.ts`
- `frontend/src/components/TeachingText.test.tsx`

The patch and original/proposed SHA256 pairs are in `frontend-learning-path.patch` and `PROPOSED_PINS.json`. `originals/` preserves the exact seventeen captured code/config/control inputs. `INPUT_PINS.json` identifies the source and initial backend contract; `BACKEND_CONTRACT_FINAL.md` captures final authority SHA256 **fa13b5868a1af9987ccbf398e51d924508f6a5e6af5989bbacbc685ba16a32df**. `CLIENT_CONTRACT.md` records DTO/selector agreements. Compare source pins before applying; do not overwrite drift.

## Original assertions preserved

- Original PreparationScreen has all nineteen controls retained. Its file is byte-exact after reversing only the declared import/mock precondition additions and **one** approved assertion: `preparationProgress` for `case-b` now requires the explicit learning catalogue argument. The existing old-starter lesson argument assertion remains unchanged and still requires starter version. No assertion was removed/skipped/weakened.
- Catalogue mocks explicitly opt into the pack while retaining the old synthetic three lessons/versions. The compatible synthetic progress helper adds catalogue/version-qualified completion fields; the attempt helper handles short/choice unions.
- Original nine client controls remain byte-exact, including no-argument legacy URLs. Original StudySchedulePanel component and its twelve controls, and native E2E copies, remain byte-exact in the isolated tree/proposal controls. No native spec is proposed.
- Read-only `SOURCE_READ_AFTER.json` reports relevant production inputs still equal to the captured source. Root independently appended native Auth controls after input capture; that source file's drift is recorded, not copied or overwritten by this proposal.

## Focused offline checks on exact final bytes

Terminal accepted receipts: `evidence/accepted/steps.json`, raw logs and JUnit. Source-before/source-after maps are equal. Installed frontend dependencies were copied from the same source without installation/downloads. Node/runtime/package-lock pin is `evidence/final/runtime.json`; configs/package/lock originals are preserved.

| Check | Actual result |
| --- | --- |
| Native typecheck (`tsc --noEmit`) | exit 0 |
| Native lint (`eslint src e2e --ext .ts,.tsx`) | exit 0, 0 errors; three existing warnings outside changed code |
| Six selected native Vitest files | **68 PASS, 0 FAIL/ERROR/SKIP** |
| Native build commands (`tsc -b`, then `vite build`) | both exit 0 |

Selected count is **28 new controls** (20 learning-path, 4 additive API, 4 renderer) plus **40 retained controls** (19 PreparationScreen, 9 client, 12 StudySchedulePanel). Component controls deny/assert zero fetch transport; API controls use synthetic Response factories. No new whole-suite/native-browser pass is claimed.

Build emits the existing 500kB chunk advisory at the expanded main chunk (510.68kB, gzip148.92kB); no threshold/config/dependency adjustment was made. This is a build observation, not measured responsiveness. Inherited React test act warnings remain in raw output; they are not runtime acceptance evidence.

## Preserved first failures

`evidence/` retains all setup/type/test runs. Initial capture used nonexistent `auth.spec.ts` (actual `auth-journey.spec.ts`); initial TeachingText writes lacked the owned components directory. First typecheck caught new testing-library `ByRoleOptions.exact` misuse, corrected without changing string-name matching. Next selected run had two harness failures from reusing consumed Response objects; fresh Response factories fixed them. These are recorded harness/type failures, not claimed product RED controls. The successful precursor run before TeachingText/ref cleanup also remains intact. Stable ref-object capture removes the newly introduced cleanup lint warning while preserving latest-generation invalidation; no lint rule suppression was added.

## React/accessibility static review

Unconditional hooks and isolated per-mount refs; primitive request dependencies; concurrent independent access/catalogue/progress reads; no shared mutable request globals; explicit native labels/fieldset controls and status/error states. No dangerous HTML, embedded URLs or private keys rendered by the text parser. All old owner/case guards and receipt/retry invariants retained. Visual/mobile/native API acceptance and broader regression gates belong to root after review/application.

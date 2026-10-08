# Narrow E2E repair and revalidation

The first full is **FAILED, 12/13**, not green. The only failed stage is demo E2E: desktop/mobile stop at unchanged `journey.spec.ts:199`, expecting `2 approved` after the UI label became `2 chosen by you`. Replacing only that literal preserves the downstream document collection/export assertions. The app uses the approved decision enum internally; the human label intentionally describes the applicant's choice.

**The proposed carry-forward of all 12 stages plus two fresh E2E stages is insufficient under the requested input-boundary rule.** `frontend/package.json` lint targets `src e2e`; `tsconfig.json` includes `e2e`; typecheck uses `tsc --noEmit` and build starts with `tsc -b`. Thus lint/typecheck/build consume the repaired file too. A fresh full is required for one final `13/13` result. A composite of prior/fresh steps must be described as composite, never one full green run.

The original backend/JUnit and unchanged unit/dependency stages remain truthful saved evidence: 4369 unique tests in each DB, exact same IDs as the saved core; frontend 282 passes. Those results do not turn the failed original full into success. No revalidation, source edit, runtime or port action ran in this review.

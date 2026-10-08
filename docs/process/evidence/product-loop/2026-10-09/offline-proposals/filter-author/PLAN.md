# External filter and user-choice proposal

2026-10-09. Parent owns primary source/Git and current full validation. This folder is the only write target.

Change copied ShortlistScreen.tsx: active query/country/eligibility/funding/hide-rejected/list-context buttons outside collapsed Filters; remove one; clear all local filter state; showing filtered/total results. Preserve ordering, compare selection, existing Save/Undo, notes, data and backend enums. Whitespace-only query is inactive. Unknown eligibility/cost/funding remains unknown.

Change copied ApprovedScreen.tsx: Approved=Chosen by you, Maybe=Considering, Rejected=Ruled out, including row decision chip. State these are user choices, not admission offers. Do not alter decisions, collection routes, timestamps, or Undo arguments.

Add meaningful cases to the two existing copied test files, keeping existing tests/expectations. Isolated frontend copies reuse installed dependencies, redirect Vite cache to owned folders, deny outbound network, mock store/API, and run only these two files. Typecheck and selected-file ESLint are permitted, no server/build/full. Run new controls on unchanged app first (RED), then proposed app (GREEN); preserve originals/logs and fixture errors if any. No account/provider/model/university/SQL/primary edits.

No new CSS if row/btn classes suffice. Source-confirmed empty-Find recovery and ResultDetail approve-only wording remain separate observations, no patch expansion.

Before/after hash primary selected files and sticky provider STOP. Seal exact proposed files, patch, commands, tests, limits, report and files sha256/byte manifest. External proposal is reviewable, not applied or product quality proof.

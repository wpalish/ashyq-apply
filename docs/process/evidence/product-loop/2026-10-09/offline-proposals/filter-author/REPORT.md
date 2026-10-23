# External Find filters / Plan choice proposal

9 October 2026. Ready for parent review; **not applied** to the primary repository. The patch changes two screen copies and adds controls to two existing test files. CSS, backend enums, API routes and dependencies are unchanged.

Find shows active Search, Country, Eligibility, Funding, Hide rejected and selected List context **outside** collapsed Filters. Each has an accessible removal button. Clear all filters resets only those six local states. Sorting, comparison selection, notes and decisions remain intact. Whitespace-only search has no active chip. The count reads `Showing N of M results from this research run`, where M includes every already-held result. The existing no-match Clear filters action calls the same reset.

Plan names the choices **Chosen by you**, **Considering** and **Ruled out**, including DecidedRow chips. It states `These are your choices, not admission offers.` Stored approved/maybe/rejected/undecided values, grouping, collection and Undo arguments remain unchanged. Unknown requirements and costs still use the original StatusChip/format helpers. The implementation uses existing row/btn classes.

| Check | Result |
|---|---|
| Original app + final proposed tests | 37 PASS / 15 expected RED / 0 ERROR / 0 SKIP |
| Proposed app + same tests | **52 PASS / 0 FAIL / 0 ERROR / 0 SKIP** |
| Original expanded cases | All 34 PASS in both modes |
| New expanded cases | 18: 13 Find + 5 Plan; 3 Undo controls pass already on original app |
| TypeScript `tsc --noEmit` | PASS |
| ESLint of the four changed files | PASS |
| Original test bodies | All 27 templates unchanged, expanding to 34 cases |
| Native `rows`, `decideRow`, `renderTable` expressions | Exact text equality |
| Outbound network / server listen | Denied; final process receipts show 0 attempts |
| Primary source and STOP | All 97 frontend source hashes plus selected dependencies/STOP unchanged |

Tests use ordinary React/Vitest imports in owned frontend copies and mocked store/API. Native UniversityCatalogue remains mounted: its initial catalogue load is answered by the mock. The all-clear control waits for that load, then proves clearing causes no second load or decide/saveNotes/rerank/startRun/collectDocuments/refreshResults call. Vite cache is owned; installed dependencies are reused without installing or starting a server.

New controls cover removal of each filter while keeping the other five; buttons outside closed details; local all-clear preserving sort/compare/notes and unknown evidence; no-match reset; whitespace-only query; removable Priority/Saved/Exploring context; all three Plan group labels and chosen/considering row chips; no admission-offer claim; unchanged Undo for each decision; disabled collection before choosing. Existing Save and document collection acceptance controls remain intact.

The first TypeScript run exposed three new-test typing errors: ByRoleOptions does not accept `exact`, and two guaranteed fixture rows need a non-null assertion under noUncheckedIndexedAccess. The original log is preserved. Only test annotations changed; app bytes and expectations did not. Final focused replay and static checks bind the final files. Initial and final RED/GREEN logs are retained separately. One inline report generator failed to parse its text before executing; execution.json records that packaging error without treating it as an app failure.

Base hashes are in `base-source.json`; final hashes in `proposed-source.json`. `filter-choice.patch` is the exact four-file proposal. `compatibility.json`, `focused-results.json`, XML and `execution.json` preserve the case and command evidence. Sticky provider STOP remains `65b5ff0e...`.

This verifies local UI logic. Browser appearance, viewport/E2E, API persistence, build/full suites, production, user metrics and recommendation quality were not tested. No server, backend, university/provider/model calls, account operations or primary Git actions occurred. The parent owns application and integration validation.

Two source-confirmed observations are **outside this patch**:

- [ShortlistScreen.tsx](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/screens/ShortlistScreen.tsx:100): an empty research run shows Start research but does not read current run state or offer Review research. This differs from a filter-produced empty list, which has Clear filters.
- [ResultDetail.tsx](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/components/ResultDetail.tsx:355): `Documents are collected only for programmes you approve` does not describe the existing Plan collection contract for both approved and maybe. That file remains unchanged.

# Mobile navigation addition — external proposal only

**READY for root review/application after the active full-backend run ends. No source/Git edits, browser, runtime or gates executed.** Existing frontend, backend and native receipts do not transfer to these proposed bytes.

## Observed source mismatch

Current App has six primary destinations; `src/styles/unimatch.css:393` still allocates five mobile columns, and line397 reserves an independent4.5rem. The sixth destination therefore starts another row without a matching content reserve. Exact originals/current CSS, App, native spec and root-authored spec pins are in SOURCE_INPUTS.json. The original CSS SHA is73a37964ea1e186f89e05682f58b8157267cedf4119fc4828980a5f9c257a035. No browser reproduction is claimed here.

## Deliberate small layout

One row of six destinations at max900px, with minimum44px columns and52px rows at default16px root size. Mobile visible labels are Home / Find / Plan / Prepare / Docs / People; explicit accessible names remain Home / Find / Plan / Exam preparation / Documents / Community. Full desktop text remains unchanged. No ellipsis, hidden destinations, horizontal nav scrolling or extra menu.

With default font and zero safe area, the bar is52px +12.8px padding +1px border =65.8px. At320px there are304px after8px side padding; five2.4px gaps leave six48.67px targets. At390px the targets are60.33px. These are CSS arithmetic, **not measured browser results**. Compact12px labels retain their full accessible names. `--mobile-nav-height` is shared by the fixed bar, main bottom reserve and document scroll-padding. Bottom padding includes safe-area-inset-bottom; left and right safe insets are independent. Main reserve adds0.75rem to the actual declared bar height. Mobile screen buttons receive a44px minimum (a0.8px increase over the former2.7rem minimum at default root size), including practice actions.

Production paths are only App.tsx + styles/unimatch.css. No PreparationScreen, types, format, social, store, DTO, server, config or dependency change. Existing motion and reduced-motion rules stay byte-identical outside the layout hunks. App labels retain root's Exam preparation accessible selector.

## Native E2E proposal

`files/frontend/e2e/preparation.spec.ts` preserves the entire original spec prefix and all three existing test bodies byte-exact (PRESERVATION.json). Root's exact original spec is copied separately as ROOT-preparation.spec.ts; that metadata copy must not be integrated.

Two appended native controls run on each existing project, using the same real synthetic local API session; they introduce no mocks or new skips:

1. At390px and320px, measure six columns/one row, viewport/nav edges, >=44px width/height, >=12px labels, unclipped single-line visible text, full accessible names, actual fixed-bar padding and main reserve. Attach measured JSON to native evidence. Nonzero hardware safe-area is not emulated; CSS formula + observed native padding are checked without claiming a physical-notch run.
2. At390px and320px, open the real IELTS starter, answer the three existing original choices, then scroll to the document end. Assert enabled Submit and the final Restart button fit above the fixed bar with8px clearance; the final action's centre hit-test must reach that button and its target height must be>=44px. Attach JSON and a screenshot. This adds only lesson GET reads; it does not create a second saved attempt or change the three retained persistence/official-score/export assertions.

Both controls restore the original project viewport. No timing deadline or existing assertion is weakened. The new tests are **NOT_RUN**. They are proposed measurable acceptance, not evidence of passing layout or full accessibility/200% text zoom.

## Root handoff

Review mobile-layout.patch or the exact three files/ paths. Apply only after source freeze is released and review confirms original hashes. Rerun frontend typecheck/lint/build/Vitest against applied bytes, then full native demo/auth/E2E source bindings as required. Backend full gate only carries if its exact consumed source mapping remains unchanged; frontend/App/CSS/native E2E receipt requires a fresh binding. No production/integration claim is made.

# Table readability correction — finite static review

**QUALIFIED_STATIC_ACCEPT_PENDING_FRESH_UI_GATES.** Reviewed only the exact two-path correction, its containment/keyboard context and unchanged renderer/screen/helper pins. No gate, test, browser, runtime, provider, Git or source edit was performed.

## Exact delta

- CSS `frontend/src/styles/unimatch.css:319`: adds only `min-inline-size: 30rem` to `.preparation-teaching table`. Before `23d4e9dcecb94e3cc97f57dd65201f7dc09cf7fdf36b7cef54666bad366585a6`; after/current `6820400b329f9096aae2b7b507ea20d2746200f77f291ebbb44f9f4761b68530`.
- New native `frontend/e2e/learning-path.spec.ts:95–98`: adds ArrowRight → poll the **table region's** scrollLeft positive, ArrowLeft → poll it back to0. Before `1f9e159319c4f94e6557f89019fefa10231e8db3506c1bd392656d0db7e46e7e`; after/current `bd34f2efb619f1096d24cc18829399876fccf1c0aa9424f663d10e85e0e5dca3`.
- Both supplied unified patches reconstruct their postimages exactly in memory. Removing those four added native lines reconstructs the entire prior new spec byte-exactly. Thus every original assertion, real API call, viewport, timeout, screenshot and click remains intact; no mock, forced click, relaxed check or retry increase is introduced.
- Both preimages match the source map consumed by closed Demo97PASS+skip/Auth8PASS. Those closed receipts remain preserved and do not qualify this new postimage.

## Containment and interaction reasoning

The minimum width belongs to the original-teaching table only. Its existing `.preparation-teaching__table` wrapper retains `max-inline-size:100%` and `overflow-x:auto`, rounded border and the renderer's native focusable region (`tabIndex=0`, `role=region`, accessible Lesson table name). The TeachingText parent keeps `min-inline-size:0; max-inline-size:100%`, with existing scoped mobile containment. A narrow viewport can therefore scroll the wider teaching table within its own region instead of compressing each formula into a very narrow cell. This is a targeted readability correction, not an assumption that every formula will now fit a single line.

The native additions are meaningful keyboard behavior checks: focus is still asserted before sending real arrow keys; scrolling is measured on that exact contained element rather than the page. Default `expect.poll` waits for actual browser scrolling without weakening the original no-global-overflow assertion. Return-to0 is explicitly checked before the saved screenshot. Browser acceptance and root's renewed image inspection must still establish actual readable cells/working scroll on these bytes.

The TeachingText renderer, PreparationScreen `bc84b35a426d654bdb541cfcd303d7165cc5bc0bb8d667668ddc73fde28c1e3a` and project-namespaced screenshot helper are byte-identical to the closed native source. No content, answer key, API, entitlement, ownership, retry, calendar task or diagnostic code is changed by the reviewed two-path delta. This review is not an independent comparison of every backend file; the backend receipt carry requires root/peer's separate consumed-source binding.

## Qualification

Root's first saved visuals showed fragmented formulas even though prior focus/global-width assertions passed. The fix and stronger retained native control address that concrete gap. Fresh complete static/frontend and Demo/Auth gates are still required. This finite static accept is not current visual/runtime PASS, a full course, target-score diagnosis, whole-product readiness or production proof.

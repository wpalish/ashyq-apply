# Open Path visual refinement — review candidate

23 September 2026. This branch starts at `task/frontend-redesign@e679432` (open PR #10). It retains that branch's app shell, profile wizard, data contracts and interactions. The owner liked the UX direction but rejected the visual contrast and some typography; the changes below address that feedback in the real React UI.

## Decision

- Keep the exact brandbook v1.1 colors as `--ds-color-brand-*` references. Product surfaces use quieter semantic values: light canvas `#F4F5F3`, text `#243044`, action `#3C5985`; dark canvas `#202B35`, text `#E9EEF0`, action `#B0C7EB`.
- Use locally hosted Onest for headings, body and user-facing data. Data uses tabular numerals. Keep IBM Plex Mono for technical identifiers and code. Remove Prata from the app and catalogue so the working flow no longer mixes a serif display face with a geometric UI face.
- Let the next-action panel use a pale blue surface. Its content and control retain the stronger contrast required for reading and focus.
- Write the product wordmark as lowercase `ashyq apply`, consistent with the catalogue and brandbook.

## Visual evidence

| View | Screenshot |
|---|---|
| Case, light, desktop | [open-path-case-light.png](screenshots/open-path-case-light.png) |
| Case, dark, desktop | [open-path-case-dark.png](screenshots/open-path-case-dark.png) |
| Case, light, mobile viewport | [open-path-case-mobile.png](screenshots/open-path-case-mobile.png) |
| Profile wizard, desktop/mobile | [profile-wizard-desktop.png](screenshots/profile-wizard-desktop.png), [profile-wizard-mobile.png](screenshots/profile-wizard-mobile.png) |

## Reference decisions

The CLI search on 21st.dev is authenticated. [Configuration Stepper](https://21st.dev/@shadcnspace/components/stepper-02) supports named short tasks, and [Feature Comparison Table](https://21st.dev/@7ovr/components/comparison-3) supports aligned desktop comparison. Neither is installed: PR #10 already has purpose-built navigation and comparison components. [Headspace onboarding on Mobbin](https://mobbin.com/explore/flows/7cdc08c0-3bcb-4882-90dd-5cf92019616f) supports calmer pacing; its illustrations and outcome language do not fit evidence-backed admissions research. Mobbin MCP search requires a paid plan, so only the public flow page was inspected.

## Adversarial review and engineering loop

1. **Concern: softer colors may fail accessibility.** We changed surfaces and text together, kept visible focus and semantic labels, then ran axe on the case dashboard, profile and design catalogue in both themes on desktop/mobile. The first catalogue run caught colors during a theme transition; the test now waits for settled styles before checking. No axe violations remain in those scenarios.
2. **Concern: a single font may erase data structure.** We retained source/date labels, aligned numbers with `tabular-nums`, and left mono available for technical identifiers. The profile wizard and case screen still separate headline, explanation, evidence and action.
3. **Concern: new colors could break PR #10's token contract.** Brand primitives remain exact; component CSS consumes Layer 2 aliases. `npm run audit:tokens` reports 0 errors and warnings. `21st review` of changed component CSS reports 0 findings; its generic hardcoded-color notices on the primitive token file are expected because that file defines the color values.
4. **Concern: screenshots can look right while behavior regresses.** The redesign E2E checks navigation, profile persistence, ru/kk/en switching, keyboard behavior, 320px overflow, and the actual catalogue. It passes 19 executed scenarios, with one intentionally skipped desktop-only 320px scenario. Unit tests, lint, typecheck and production build pass.
5. **Concern: future component work could restore the rejected fonts.** A post-integration review found stale Prata and mono-as-data instructions in `frontend/.21st` and several specs, although the actual tokens use Onest. PR #19 now aligns those instructions with the working candidate and keeps the earlier font choice as superseded history. Nested 21st source paths were verified, and `21st review` of the case component and changed component CSS reports 0 findings.
6. **Concern: long screenshots showed a floating skip link.** Chromium's full-page capture painted a transform-hidden skip link in stitched images even after the link lost focus. The link now also uses opacity while hidden, and remains visible and actionable on keyboard focus. Desktop/mobile profile and mobile exam screenshots were regenerated without the artifact; a focused keyboard E2E scenario guards the behavior.

The original backend gate on PR #10 reached 93.80% coverage (above the 92% floor) with one Windows-specific fixture decoding failure: `tests/test_live_extraction.py::TestKztTuitionVocabulary::test_a_tenge_fees_page_yields_a_tuition_breakdown`. The fixture is UTF-8, but its helper used the Windows default encoding. The helper now requests UTF-8 explicitly (`547d32d`), and the targeted extraction file passes under the ordinary Windows locale. No backend production behavior changed.

The branch now includes `origin/main@07de4d9` (merge commit `5180437`). Only the handoff journal conflicted; its main history was retained and the current task was placed at the top. The integrated frontend gate passes token audit (5 files, 0 findings), typecheck, lint, 251 unit tests, build, and redesign Playwright (19 passed, 1 intentional skip). Backend Ruff check/format and mypy pass across 198 source files; one Alembic head and the targeted extraction file pass. Full `pytest --cov=app --cov-fail-under=92 -q` previously passed with 94.56% coverage; the post-screenshot rerun is in progress.

The current screenshots are a candidate for the owner's visual review, not evidence that every page and state is approved. The inherited PR #10 screens still mix Russian and English in some navigation and account copy; a separate localization pass is needed before release.

# Frontend redesign — first slice

Status: implemented, scoped checks passed; full product redesign remains in progress.
Basis: `epics.md` section 5, E00/E04/E16; `specs/design-system.md`; brandbook v1.1.

## Implemented

- Default `#/case`: next action derived from hydrated profile/run/results, not invented readiness.
- Five stable destinations: Case, Shortlist, Plan, Community, More. Existing screens and hashes remain.
- Desktop sidebar; mobile bottom navigation and scrollable context tabs. Mobile account/theme/language controls in More.
- Running research remains visible outside the progress screen. Failure/cancellation takes priority over partial results.
- Multiple-case selector only when there are multiple cases. New case and unsaved-change confirmation retained.
- Russian, Kazakh and English dashboard copy. Existing screens retain their existing localization coverage.
- Project Layer 2 tokens only; light/dark and reduced motion supported.

## Verification

- Typecheck, lint, 195 unit tests, production build pass.
- `npm run audit:tokens`: 5 CSS/SCSS files, zero errors and warnings.
- `npm run e2e:redesign`: 4 isolated browser tests (1440px desktop / 390px mobile, light/dark). Checks routing, locked sections, locale change, history, zero horizontal page overflow, navigation touch targets, and zero axe WCAG A/AA violations on the dashboard. API fixtures are mocked; this is not a live backend smoke.
- Screenshots: `docs/screenshots/redesign-{desktop,mobile}-{light,dark}.png`; mobile viewport captures also saved.
- Existing E2E helpers updated for primary/context navigation; full ordinary/auth backend-dependent E2E not rerun in this slice.
- Backend Ruff/format/mypy pass. The pre-existing KZT tuition extraction test still fails in an isolated rerun. No backend code changed; full backend coverage suite was not rerun. See HANDOFF section 7.

## Next slices

1. E02 remaining: sufficiency feedback, test picker, step-position restore, evidence-link rows, localization and server autosave; retain import/validation and unsaved-change guarantees.
2. E03 preferences and budget in plain language; preserve ranking and privacy contracts.
3. Shortlist/programme detail, source/freshness presentation, then Plan/documents.
4. Community and More screen interiors; finish shared localization and end-to-end integration gates.

This slice does not claim that deadlines, readiness scoring, a full document timeline, or all R1 epics have been implemented.

## 2026-09-09 continuation

Owner clarified the exact font set: **Prata + Onest + IBM Plex Mono**. This overrides the earlier
brandbook/synthesis font mapping. `64826f6` uses self-hosted fonts, Prata native 400 weight, and
synchronized tokens/specs/catalogue. Four light/dark desktop/mobile checks assert font families.

E02 now has six-step navigation, previous/next, and Show all fields review mode. Existing panels,
transcript suggestions, explicit grade conversions, draft storage and server-save behavior remain.
Three unit tests verify visibility, retained edits and review mode; two additional mocked browser
tests verify those interactions, accessibility and mobile overflow. Total: 198 unit / 6 browser tests.
The internal form's existing English copy is not fully localized yet; new navigation has RU/KK/EN.
No backend/schema or server-autosave change. No completed-E02 claim.

Dependency check: production npm audit is clean. Full npm audit reports two moderate entries for
the existing Vitest/mocker development dependency (GHSA-82fw-gwwq-j7x9); a major test-tool upgrade
was not forced into this UI change. Repository-wide integration and KZT limitations above remain.

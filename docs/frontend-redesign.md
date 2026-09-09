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

## E02 exam picker

English now owns IELTS/TOEFL/Duolingo; standardised Tests owns SAT/ACT. Score/date data reveals
existing exams automatically; empty metadata does not. Manual collapse and review mode never alter
scores. Clearing the last score leaves its block open, preserving keyboard focus. Duolingo dates
survive score editing, with an explicit incomplete-draft warning because the API requires a score.
A separate confirmed removal clears the entire Duolingo result; no API/schema change was made.

Verification: 208 unit tests / 8 mocked browser scenarios pass, including keyboard toggles, retained
scores/dates, axe and overflow; typecheck/lint/build/token audit pass (0 errors, 0 warnings). Backend
Ruff/format/mypy and `tests/test_scoring_and_profile.py` pass. Full backend coverage/ordinary-auth E2E
not rerun. Screenshots: `docs/screenshots/exam-picker-{desktop,mobile}.png`.
Dashboard browser screenshots now use per-test output paths: an open Windows preview can lock a
shared documentation image, which must not fail otherwise valid UI assertions.

Readiness follow-up must distinguish the current API's `can_proceed` from the stronger proposed E02
threshold: current validation blocks only a missing subject area. Planned-only Duolingo is not yet
accepted by the schema. Do not invent a stronger frontend gate or claim planned scores are achieved.

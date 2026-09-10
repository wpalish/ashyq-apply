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

## E02 current-draft validation

StoreProvider now uses a debounced, race-safe validation hook: draft edits immediately hide the
previous report; cancelled requests cannot overwrite a newer success or failure. Hydration and retry
invalidate readiness. ProfileScreen uses the existing Notice styling for RU/KK/EN checking, invalid
input, unavailable/retry, blocked count and server-eligible feedback. Eligibility is explicitly not
completeness. No backend gate or schema changed; detailed server gap text remains server-provided.

Verified: 215 unit tests (24 files), 10 mocked desktop/mobile browser scenarios, typecheck, lint,
build, token audit (0 errors/0 warnings), Ruff check/format, mypy (164 files), and 43 focused profile
backend tests. Full backend coverage and ordinary/auth integration E2E were not rerun. Existing
KZT baseline and dev dependency caveats remain. 21st CLI unavailable; reused project Notice/token
contracts and inspected the mobile browser capture instead. Next: localize the remaining profile
labels and gap presentation without changing backend field keys or server validation rules.

## E02 profile localization

ProfileScreen-owned headings, labels, hints, actions, options and gap severity now have typed RU/KK/EN
copy. ExamPicker score/auxiliary labels follow the locale while official exam variant names remain
recognizable. Locale switching preserves draft data, API enum values, field ids and the mounted step.
Server-authored validation/conversion messages, transcript quotes and user content stay verbatim.
This is profile localization, not a claim that the surrounding shell or all other screens are translated.

All-fields browser coverage exposed hint contrast 4.45 on sunken panels; Field now uses the existing
muted token. Light and settled dark axe checks pass. The theme test waits for finite animations before
measuring contrast, avoiding intermediate transition colors. Prata/Onest/IBM Plex Mono unchanged.
Checks: 217 unit/24 files, 12 mocked browser scenarios, typecheck/lint/build, token audit 0/0,
Ruff check/format, mypy 164 files and 43 focused backend profile tests. Full backend coverage and
ordinary/auth integration suites not rerun; inherited KZT/dev dependency caveats remain.
Next E02 slice: restore wizard step per case without leaking navigation between profiles.

## E02 case-scoped step restoration

`2785d82` adds per-tab, per-case step storage (validated indices 0–5), gated by hydration. Local-case
steps migrate to the server id on first save/start; a save uses the latest step even if navigation
changed during the request. Stale saves cannot migrate onto a newer case. New cases start at 0;
clear/demo resets the current step, deletion removes its slot. Before a case has an identity navigation
is ephemeral. Review mode remains temporary and clears on case change. No profile API change.

Checks: 232 unit tests/25 files, 14 mocked browser scenarios including reload/review reset/new-case
isolation on desktop/mobile, typecheck/lint/build and token audit 0/0. Ruff/format/mypy and 43 focused
backend tests pass. Full backend coverage and ordinary/auth integration are not rerun; inherited
KZT and dev dependency caveats remain. The mobile test uses More to access the existing New case
action; it does not force-click hidden controls. Next: separate evidence-link rows for activities and
achievements while preserving the existing string-array API and user-entered links.

## PR #10 integration regression repair

The concurrent WIP checkpoint `49c961b` and the follow-up implementation were reconciled
without dropping either change set. This remains one bounded PR-repair slice, not E02 completion.

Shortlist chips wrap inside their columns and Decision has enough room for Onest controls.
Expanded funding details and validation messages use shrinkable grid tracks and wrap long
URLs/API keys without truncation. Mobile BottomNav is a direct AppShell child, owns its fixed
hit area above long content and keeps focused controls clear of it. Community tests follow the
documented horizontal context strip and the real primary/context destinations, including My
community profile under More; no forced clicks remain.

Completed progress stages no longer fade their text/chips. Accent badges and chips use the
existing darker interactive foreground; inset university metadata and validation captions use
muted text. Prata + Onest + IBM Plex Mono and all API contracts are unchanged.

Fresh verification: ordinary integration E2E **77 passed / 1 intentional desktop skip**;
auth integration **6 passed**; typecheck/lint/build and **232 unit tests / 25 files** pass;
token audit **5 CSS/SCSS files, 0 errors / 0 warnings**. Ordinary tests used an isolated
temporary SQLite database plus real API/worker. Auth used the same committed test suite and
auth settings with bundled Python and a separate temporary database. Application data was not
deleted or changed. Generated workflow screenshots are refreshed. Backend Ruff/format and mypy
(164 files) pass; **1358 backend tests pass at 93.80% coverage** against the 92% threshold, and
the single Alembic head is `d9c4e7a21b83`. Existing React `act(...)` and Starlette/httpx
deprecation warnings remain visible. The integration regressions are repaired; E02 and the wider
redesign remain partial.

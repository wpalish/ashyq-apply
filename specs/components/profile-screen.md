# ProfileScreen

## 1. Metadata

Name: ProfileScreen. Category: form/wizard. Status: E02 first implementation slice.

## 2. Overview

Use six steps to edit an applicant profile: Application, Grades, English, Tests, Activities, Achievements.
Use Show all fields for review/import or editing across sections. Optional sections do not block navigation.
Do not equate visiting a step with data completeness or admission readiness.

## 3. Anatomy

Page heading, step navigation, existing draft/source notices, active section panels, validation gaps,
previous/next controls, explicit save and preferences action. Hidden steps stay mounted to preserve inputs.
English groups IELTS/TOEFL/Duolingo; Tests groups SAT/ACT plus existing other/curriculum forms.
ExamPicker controls visibility only. Collapsing an exam never clears scores or excludes them from research.
Activity and achievement cards use EvidenceLinksField: one independently labelled URL per row, with add
and remove actions. A blank row created in the UI is not profile data until the applicant types into it.

## 4. Tokens

`--font-family-brand`, `--font-family-ui`, `--font-family-mono`, `--font-size-sm`, `--font-size-xl`,
`--space-2`, `--space-3`, `--space-4`, `--space-5`, `--space-6`, `--size-touch-target`,
`--color-interactive-soft`, `--color-interactive-hover`, `--color-border`, `--radius-md`.
Reuse Panel, Field, Notice and Button contracts. Display headings use Prata 400; controls and body use Onest.

## 5. Props/API

Profile-owned copy uses a typed RU/KK/EN dictionary. Locale changes must not reset step, draft,
selected enum value or field ids. Translated options always retain explicit API values. User-entered
names, transcript excerpts and server-authored messages remain verbatim, never machine-translated.

`ProfileScreen({ onNext })`. Store exposes activeCaseKey, profileStep and setProfileStep. Step 0–5
persists in per-tab sessionStorage under a versioned per-case key, after hydration only. New cases
start at 0; first save migrates the local-case step to the server id. Clear/demo reset to 0; deletion
removes that case's step. An unidentified pre-case draft has ephemeral navigation only. Invalid or
unavailable storage falls back safely. Review mode is not persisted and resets on case change.
Existing case-scoped draft persistence stays in StoreProvider. No server autosave is added.

Activity and achievement evidence remains the existing `evidence_links: string[]` API, with at most five
200-character values. Existing arrays render in their original order and are never split, trimmed,
normalized or fetched by the frontend. Adding a blank row leaves the draft unchanged; editing or removing
one row preserves every sibling value verbatim. Local feedback accepts complete HTTP(S) URL shapes only,
but describes format rather than verification and does not create a new save or research gate.

## 6. States

Validation belongs to the exact current draft only. While hydration or debounced validation is pending,
hide previous reports. Ignore late successes and failures after draft replacement or unmount.
Show localized checking, invalid input, unavailable, blocked, or eligible feedback with a retry action
for unavailable checks. Eligibility uses server can_proceed and blocking_count; it is not completeness.
Validation never adds a new client-side save or research gate.

Validation paths and messages wrap without truncation in narrow layouts. Review mode
must not expand the page viewport or displace the fixed primary navigation.

One active step or all fields; next/back; empty/partial draft; loading/save; conversion error;
transcript read/review/apply. Focus moves to the section container after next/back. Step navigation
is keyboard-operable with native buttons and aria-current. No false completion rings.

Evidence-link add moves focus into the new row. Remove moves focus to the following row, then the previous
row, or the add action when none remain. Each input has a native label, local format feedback is associated
with `aria-describedby`, and invalid non-empty values use `aria-invalid`. At 320 px rows collapse to one
column without horizontal page overflow. Locale switching changes copy only and keeps rows and values.

## 7. Example

```tsx
<ProfileScreen onNext={() => setScreen('preferences')} />
```

## 8. Cross-references

[Field](field.md), [EvidenceLinksField](evidence-links-field.md), [Panel](panel.md), [Notice](notice.md), [AppShell](app-shell.md).
Remaining E02 after exam picker: completeness rule including planned English, per-field errors, step restore,
evidence-link rows and server autosave. These require separate tested follow-up, not a completed-epic label.

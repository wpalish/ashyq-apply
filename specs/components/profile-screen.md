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

## 4. Tokens

`--font-family-brand`, `--font-family-ui`, `--font-family-mono`, `--font-size-sm`, `--font-size-xl`,
`--space-2`, `--space-3`, `--space-4`, `--space-5`, `--space-6`, `--size-touch-target`,
`--color-interactive-soft`, `--color-interactive-hover`, `--color-border`, `--radius-md`.
Reuse Panel, Field, Notice and Button contracts. Display headings use Prata 400; controls and body use Onest.

## 5. Props/API

`ProfileScreen({ onNext })`. Existing store/API unchanged. Wizard position is local UI state;
existing case-scoped draft persistence stays in StoreProvider. No new server autosave in this slice.

## 6. States

Validation belongs to the exact current draft only. While hydration or debounced validation is pending,
hide previous reports. Ignore late successes and failures after draft replacement or unmount.
Show localized checking, invalid input, unavailable, blocked, or eligible feedback with a retry action
for unavailable checks. Eligibility uses server can_proceed and blocking_count; it is not completeness.
Validation never adds a new client-side save or research gate.

One active step or all fields; next/back; empty/partial draft; loading/save; conversion error;
transcript read/review/apply. Focus moves to the section container after next/back. Step navigation
is keyboard-operable with native buttons and aria-current. No false completion rings.

## 7. Example

```tsx
<ProfileScreen onNext={() => setScreen('preferences')} />
```

## 8. Cross-references

[Field](field.md), [Panel](panel.md), [Notice](notice.md), [AppShell](app-shell.md).
Remaining E02 after exam picker: completeness rule including planned English, per-field errors, step restore,
evidence-link rows and server autosave. These require separate tested follow-up, not a completed-epic label.

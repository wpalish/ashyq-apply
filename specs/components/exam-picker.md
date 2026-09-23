# ExamPicker

## 1. Metadata

Name: ExamPicker. Category: form/progressive disclosure. Status: E02.

## 2. Overview

Reveal fields for the exams the applicant wants to enter. English: IELTS, TOEFL, Duolingo.
Standardised: SAT, ACT. Existing other-exam and AP/IB/A-Level forms remain available in Tests.
Do not interpret a collapsed block as no exam, or alter matching inputs based on visibility.

## 3. Anatomy

Named button group; toggle buttons with aria-expanded/aria-controls; retained-score notice;
per-exam fieldset with legend, numeric fields and taken/planned dates. IELTS includes its test type.

## 4. Tokens

Existing Button/Field/Panel aliases plus `--space-3`, `--space-4`, `--space-5`, `--color-border`,
`--color-interactive-soft`, `--color-interactive-hover`, `--radius-md`.

## 5. Props/API

Score labels and auxiliary controls follow RU/KK/EN locale. Official exam and test-type names
stay recognizable; locale changes never alter stored scores, test_type values, ids or visibility.

`ExamPicker({ group, draft, update, showAll })`. Data stays in the existing academics schema.
Initial visibility derives from any numeric score (including zero) or date, but not default max-score
or IELTS test-type metadata. Late hydration also reveals entered exams unless manually collapsed.
Manual choices are component-local; profile identity changes reset them via the parent key.
Show-all mode reveals all fields without mutating data or manual selections.

## 6. States

Empty, expanded, collapsed with stored data, show-all; native keyboard focus and numeric/date controls.
Collapsing does not delete scores. Clear a score explicitly in its input. Duolingo score clearing
preserves its max-score and dates. Planned-retake dates remain dates, not claims of achieved scores.
The current API requires a numeric Duolingo score. A scoreless Duolingo object is an incomplete local
draft, not a savable planned-only exam; the UI explains this. A separate confirmed remove action
sets the entire Duolingo result to null, including its dates. Hiding never invokes that action.

## 7. Example

```tsx
<ExamPicker group="english" draft={profileDraft} update={setProfileDraft} showAll={showAll} />
```

## 8. Cross-references

[ProfileScreen](profile-screen.md), [Field](field.md), [Button](button.md), [Panel](panel.md).

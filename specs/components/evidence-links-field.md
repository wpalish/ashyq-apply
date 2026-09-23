# EvidenceLinksField

## 1. Metadata

- Name: EvidenceLinksField
- Category: Form/repeater
- Status: E02 first implementation slice

## 2. Overview

Use for optional activity and achievement evidence URLs. It makes each value independently editable while
preserving the current `string[]` profile contract. It checks URL shape locally; it never visits a URL and
never presents applicant-provided evidence as verified.

## 3. Anatomy

Native fieldset and legend, concise format/non-verification hint, zero to five rows, one Field-labelled URL
input and remove action per row, local error text, and an add action. Rows stay mounted while their profile
wizard section is hidden.

## 4. Tokens used

`--space-1`, `--space-2`, `--space-3`, `--font-size-xs`, `--color-danger`, `--size-touch-target`.
Reuse Field and Button visual contracts; controls and copy remain Onest through inherited typography.

## 5. Props/API

`EvidenceLinksField({ idPrefix, value, onChange, copy })`, where `value` and `onChange` use `string[]`.
The component supports the existing maximum of five values and maximum length of 200 characters. It emits
non-empty row values in visible order and does not trim, normalize, deduplicate or otherwise rewrite them.
Existing values round-trip verbatim. An added empty row is local presentation state and does not call
`onChange` until it contains text.

## 6. States

Empty; one or more stored rows; added blank row; invalid non-empty HTTP(S) shape; five-row limit. Invalid
feedback uses `aria-invalid` and `aria-describedby`, but does not claim server rejection or verification.
Add focuses the new input. Remove focuses the following row, previous row, or add action. RU/KK/EN copy can
change without resetting values. At 320 px input and action stack without horizontal page overflow.

## 7. Code example

```tsx
<EvidenceLinksField
  idPrefix="activity-0-evidence"
  value={activity.evidence_links}
  onChange={(links) => updateActivity(0, { evidence_links: links })}
  copy={localizedEvidenceCopy}
/>
```

## 8. Cross-references

[Field](field.md), [ProfileScreen](profile-screen.md), [Button](button.md).

# Field

## 1. Metadata

- Name: Field
- Category: Form
- Status: Stable

## 2. Overview

Use to bind a visible label and optional hint to an input, select, or textarea. Do not rely on placeholder text as the label.

## 3. Anatomy

Field stack, label, native control child, and optional hint.

## 4. Tokens used

`--space-1`, `--space-control-block`, `--space-control-inline`, `--font-size-sm`, `--font-size-xs`, `--font-weight-semibold`, `--color-text`, `--color-text-subtle`, `--color-surface`, `--color-border-strong`, `--color-interactive`, `--radius-md`, `--border-width-hairline`, `--motion-duration-fast`, `--shadow-focus-ring`.

## 5. Props/API

`Field({ label, hint?, children, htmlFor? })`. The child's `id` must match `htmlFor` when supplied.

## 6. States

Default uses the strong border; hover increases border contrast; focus uses interactive border plus focus-ring shadow; disabled is native-control behavior; error must add an accessible message/Notice and `aria-invalid` at the call site.

## 7. Code example

```tsx
<Field label="Country" htmlFor="country" hint="Where the programme is based">
  <select id="country">…</select>
</Field>
```

## 8. Cross-references

[Button](button.md), [Composer](composer.md), [Notice](notice.md).

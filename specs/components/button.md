# Button

## 1. Metadata

- Name: Button
- Category: Action
- Status: Stable CSS pattern (native `button` + `.btn`)

## 2. Overview

Use for actions and form submission. Do not use for navigation; use a link or `.linkish` control when the action changes location.

## 3. Anatomy

Native button, base `.btn` class, optional size/tone modifier, label, and optional busy/disabled state.

## 4. Tokens used

`--space-button-block`, `--space-button-inline`, `--space-1`, `--space-button-compact-inline`, `--radius-md`, `--border-width-hairline`, `--color-surface`, `--color-border-strong`, `--color-text`, `--color-interactive`, `--color-interactive-hover`, `--color-text-inverse`, `--color-danger`, `--font-size-sm`, `--font-size-xs`, `--font-weight-medium`, `--font-weight-semibold`, `--motion-duration-fast`, `--shadow-sm`, `--shadow-none`, `--transform-pressed`.

## 5. Props/API

CSS API: `.btn`; modifiers `.btn--primary`, `.btn--danger`, `.btn--ghost`, and `.btn--sm`. Use native `type`, `disabled`, and ARIA attributes.

## 6. States

Default uses a bordered surface. Hover adds border emphasis/shadow; active shifts one tokenized pixel; focus uses the global focus ring; disabled lowers opacity and blocks pointer input; danger uses danger color; errors belong in a nearby Notice.

## 7. Code example

```tsx
<button className="btn btn--primary" type="submit" disabled={busy}>
  {busy ? 'Saving…' : 'Save'}
</button>
```

## 8. Cross-references

[Field](field.md), [Notice](notice.md), [PaymentModal](payment-modal.md).

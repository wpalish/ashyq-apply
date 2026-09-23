# Stat

## 1. Metadata

- Name: Stat
- Category: Data display
- Status: Stable

## 2. Overview

Use inside a `.statband` to summarize a small set of comparable metrics. Do not use for editable values or status without a label.

## 3. Anatomy

Value and uppercase label inside one stat-band cell.

## 4. Tokens used

`--space-4`, `--border-width-hairline`, `--color-border`, `--font-family-display`, `--font-size-stat`, `--font-size-xs`, `--font-weight-bold`, `--line-height-flat`, `--letter-spacing-wide`, `--color-text-subtle`.

## 5. Props/API

`Stat({ value, label })` where value is a React node and label is readable text.

## 6. States

Display-only: default is the only intrinsic state. Loading, error, and empty behavior are owned by the surrounding section.

## 7. Code example

```tsx
<Stat value={run.claims_recorded} label="Claims recorded" />
```

## 8. Cross-references

[Panel](panel.md), [Loading](loading.md), [Empty](empty.md).

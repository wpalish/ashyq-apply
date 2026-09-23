# Empty

## 1. Metadata

- Name: Empty
- Category: Feedback
- Status: Stable

## 2. Overview

Use when a successfully loaded collection has no items. Do not use while loading or when a request failed.

## 3. Anatomy

Centered container, title, and optional explanatory/action content.

## 4. Tokens used

`--space-8`, `--space-4`, `--space-2`, `--color-text-muted`, `--color-text`, `--color-border-strong`, `--color-surface-sunken`, `--radius-lg`, `--border-width-hairline`, `--font-family-display`, `--font-size-md`.

## 5. Props/API

`Empty({ title, children? })`.

## 6. States

Default is the only intrinsic state. Loading uses Loading; error uses Notice. Actions inside receive their own hover, active, focus, and disabled states.

## 7. Code example

```tsx
<Empty title="No results yet">Run the research first.</Empty>
```

## 8. Cross-references

[Loading](loading.md), [Notice](notice.md), [Panel](panel.md).

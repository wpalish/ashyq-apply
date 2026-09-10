# Loading

## 1. Metadata

- Name: Loading
- Category: Feedback
- Status: Stable

## 2. Overview

Use for indeterminate work with a visible status label. Do not use it to replace determinate progress when progress data exists.

## 3. Anatomy

Live status row, decorative spinner, and text label.

## 4. Tokens used

`--size-icon`, `--border-width-medium`, `--color-border-strong`, `--color-interactive`, `--radius-round`, `--motion-duration-spin`, `--motion-ease-linear`, `--font-size-sm`, `--color-text-muted`.

## 5. Props/API

`Loading({ label })`; the root uses `role="status"` and `aria-live="polite"`.

## 6. States

Default spins continuously; reduced motion uses the global reduced duration token. Hover/active/focus/disabled/error do not apply; switch to Notice for failure.

## 7. Code example

```tsx
<Loading label="Checking official sources…" />
```

## 8. Cross-references

[Empty](empty.md), [Notice](notice.md), [Stat](stat.md).

# Notice

## 1. Metadata

- Name: Notice
- Category: Feedback
- Status: Stable

## 2. Overview

Use for persistent contextual feedback. Do not use for transient decoration or hide blocking errors in neutral copy.

## 3. Anatomy

Semantic container with `role="note"`, message content, and optional inline actions supplied as children.

## 4. Tokens used

`--space-3`, `--radius-md`, `--border-width-hairline`, `--font-size-sm`, `--color-info*`, `--color-warning*`, `--color-danger*`, and `--color-demo*`.

## 5. Props/API

`Notice({ kind?, children })`; kinds: info, warn, risk, demo. Existing CSS also supports `.notice--ok` for success messages.

## 6. States

Default/info explains; warn calls attention; risk communicates an error or destructive consequence; demo marks synthetic content; ok communicates success. Hover/active/focus/disabled are not intrinsic.

## 7. Code example

```tsx
<Notice kind="risk">The source could not be verified.</Notice>
```

## 8. Cross-references

[ErrorBoundary](error-boundary.md), [PaywallNotice](paywall-notice.md), [Panel](panel.md).

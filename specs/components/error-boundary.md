# ErrorBoundary

## 1. Metadata

- Name: ErrorBoundary
- Category: Failure containment
- Status: Stable

## 2. Overview

Wrap render regions where an exception would otherwise blank the application. Do not use it for expected API errors that can be handled inline.

## 3. Anatomy

Boundary wrapper, risk Notice fallback, reassurance copy, technical error text, and reload Button.

## 4. Tokens used

Indirectly consumes Notice, Button, stack, row, `--font-size-sm`, `--font-size-xs`, `--font-family-mono`, `--color-text-subtle`, and danger-state tokens.

## 5. Props/API

`ErrorBoundary({ children, label? })`; class component logs the error and component stack, then renders fallback UI.

## 6. States

Normal renders children. Error renders the alert fallback and reload action. Hover/active/focus apply to reload; disabled is not used. Recovery occurs through page reload.

## 7. Code example

```tsx
<ErrorBoundary label="the shortlist"><ShortlistScreen /></ErrorBoundary>
```

## 8. Cross-references

[Notice](notice.md), [Button](button.md), [Empty](empty.md).

# PaywallNotice

## 1. Metadata

- Name: PaywallNotice
- Category: Entitlement feedback
- Status: Stable

## 2. Overview

Use when the API reports a locked case. It chooses school quota unlock when quota exists and B2C payment otherwise. Do not charge a school user while eligible quota remains.

## 3. Anatomy

Outer inset, explanatory Notice, quota or price action, dismiss action, and conditional PaymentModal.

## 4. Tokens used

`--space-4`, `--space-6`, `--space-0`, plus Notice, Button, and PaymentModal tokens.

## 5. Props/API

`PaywallNotice({ testPaywall? })`; production state comes from `useStore()`. The test seam accepts `profileId`, `priceKzt`, and nullable `casesLeft`.

## 6. States

Hidden when no paywall; quota available; payment offer; payment modal open; paid/refreshing; API errors are handled by the underlying flows. Buttons retain hover, active, focus, and disabled behavior.

## 7. Code example

```tsx
<PaywallNotice />
```

## 8. Cross-references

[PaymentModal](payment-modal.md), [Notice](notice.md), [Button](button.md).

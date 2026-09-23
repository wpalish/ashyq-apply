# PaymentModal

## 1. Metadata

- Name: PaymentModal
- Category: Commerce dialog
- Status: Stable

## 2. Overview

Use only to unlock one applicant case through a Kaspi phone invoice or QR fallback. Do not use for school quota consumption or imply payment success before the provider confirms it.

## 3. Anatomy

Modal overlay, dialog panel, price summary, payment-method segmented control, optional phone Field, primary action, pending/paid/error Notice, and close action.

## 4. Tokens used

`--z-modal`, `--space-6`, `--color-overlay`, and all tokens consumed by Panel, Button, Field, Notice, and decision controls.

## 5. Props/API

`PaymentModal({ profileId, priceKzt, onClose, onPaid })`. Phone numbers must match the existing `8XXXXXXXXXX` contract; provider status is polled until paid, closed, or expired.

## 6. States

Default method selection; phone/QR active choice; busy/disabled submit; pending invoice; paid; expired/closed/error. Dialog focus styles use global focus-visible behavior. Closing does not report payment.

## 7. Code example

```tsx
<PaymentModal profileId={id} priceKzt={price} onClose={close} onPaid={refresh} />
```

## 8. Cross-references

[PaywallNotice](paywall-notice.md), [Field](field.md), [Notice](notice.md), [Button](button.md).

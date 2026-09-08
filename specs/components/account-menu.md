# AccountMenu

## 1. Metadata

- Name: AccountMenu
- Category: Account management
- Status: Stable

## 2. Overview

Use in the application header for workspace switching, password changes, and account deletion. Do not reuse it as general navigation.

## 3. Anatomy

Toggle button, conditional panel, workspace selector, password form, destructive confirmation form, success notice, and error alert.

## 4. Tokens used

Consumes Button, Panel, Field, Notice, row, and stack tokens: spacing aliases, surface/border/text/interactive/danger colors, radius, typography, focus shadow, and fast motion.

## 5. Props/API

`AccountMenu({ onSignedOut })`. It loads organizations on open and calls `onSignedOut` after successful deletion.

## 6. States

Closed/open; neutral/password/delete subpanels; idle/busy; success; error. Native controls supply hover, active, focus, and disabled states. Delete state must retain its irreversible-action warning and explicit data checkbox.

## 7. Code example

```tsx
<AccountMenu onSignedOut={() => setSession(null)} />
```

## 8. Cross-references

[Button](button.md), [Field](field.md), [Notice](notice.md), [Panel](panel.md).

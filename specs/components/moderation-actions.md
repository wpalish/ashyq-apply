# Moderation actions

## 1. Metadata

- Name: ReportButton / BlockButton
- Category: Safety and moderation
- Status: Stable

## 2. Overview

Use ReportButton beside reportable content and BlockButton on another person's profile. Reporting requests human review; blocking takes effect immediately. Do not imply that a report instantly stops contact.

## 3. Anatomy

Report trigger/form/reason/note/actions/status and block trigger/confirmation/actions. Both include busy handling and explicit cancel paths.

## 4. Tokens used

Consumes Button, Field, Notice, stack, row, and linkish aliases: spacing, text/surface/border, interactive/danger colors, typography, radii, focus shadow, and fast motion.

## 5. Props/API

`ReportButton({ subjectType, subjectId })`. `BlockButton({ userId, blocked, onChanged })`.

## 6. States

Report: closed, editing, sending/disabled, sent, duplicate/error. Block: unblocked, confirming, busy/disabled, blocked/unblock. All triggers retain hover, active, and focus states.

## 7. Code example

```tsx
<ReportButton subjectType="post" subjectId={post.id} />
<BlockButton userId={person.user_id} blocked={person.blocked} onChanged={reload} />
```

## 8. Cross-references

[Post](post.md), [PersonTile](person-tile.md), [Notice](notice.md), [Button](button.md).

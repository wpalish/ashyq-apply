# PersonTile

## 1. Metadata

- Name: PersonTile
- Category: Community navigation
- Status: Stable

## 2. Overview

Use in the people discovery grid to open a public profile. Do not use it for the compact author identity inside a Post.

## 3. Anatomy

Button root, large Avatar, display name, target city/major, status Chip, and university Chips.

## 4. Tokens used

`--size-person-card`, `--space-1`, `--space-3`, `--space-4`, `--color-surface`, `--color-surface-raised`, `--color-border`, `--color-border-strong`, `--radius-lg`, `--border-width-hairline`, `--font-weight-semibold`, `--font-size-sm`, and `--motion-duration-fast`.

## 5. Props/API

`PersonTile({ person: PersonCard, onOpen })`.

## 6. States

Default; hover raises surface/border contrast; active is native button behavior; focus uses global focus-visible; no intrinsic disabled/error state; missing aim uses translated fallback; avatar image failure falls back to initials.

## 7. Code example

```tsx
<PersonTile person={person} onOpen={setSelectedUserId} />
```

## 8. Cross-references

[Post](post.md), [Chip](chip.md), [Moderation actions](moderation-actions.md).

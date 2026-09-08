# Post

## 1. Metadata

- Name: Post
- Category: Community content
- Status: Stable

## 2. Overview

Use for published feed entries and replies. The feed remains a ruled editorial list rather than a card stack. Do not use Post for private-message bubbles.

## 3. Anatomy

Article root, Byline/Avatar, tagged Body, optional footer, retract action, report action, and optional child thread.

## 4. Tokens used

`--space-1` through `--space-4`, `--size-avatar`, `--color-border`, text/interactive/status colors, `--border-width-hairline`, avatar radius/size/type tokens, and linkish action tokens.

## 5. Props/API

`Post({ post, onOpenPerson?, onDelete?, reportable?, footer?, children? })`.

## 6. States

Default; own-post retract confirmation; other-post reportable; reply nesting; avatar accepted/waitlist/unstated/photo fallback. Links/buttons provide hover, active, focus, and disabled states; reporting errors appear inside ReportButton.

## 7. Code example

```tsx
<Post post={post} reportable onOpenPerson={openPerson} />
```

## 8. Cross-references

[Chip](chip.md), [PersonTile](person-tile.md), [Composer](composer.md), [Moderation actions](moderation-actions.md).

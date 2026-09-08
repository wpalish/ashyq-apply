# Composer

## 1. Metadata

- Name: Composer
- Category: Community form
- Status: Stable

## 2. Overview

Use to create posts, replies, or messages with a visible character budget and parsed tags. Do not submit blank or over-limit content.

## 3. Anatomy

Visually hidden label, textarea, detected-tag preview, live character count, and submit Button.

## 4. Tokens used

`--space-2`, `--space-3`, `--font-size-base`, `--font-size-xs`, `--font-family-mono`, `--font-weight-semibold`, `--line-height-compact`, surface/text/border/interactive/danger colors, `--radius-md`, `--border-width-hairline`, `--motion-duration-fast`, and `--shadow-focus-ring`.

## 5. Props/API

`Composer({ placeholder, submitLabel, max?, busy?, onSubmit })`. Default max is `POST_MAX_CHARS`; successful submission clears the textarea.

## 6. States

Default; hover; focus; detected tags; valid; over-limit error; busy/disabled submit; submission failure is owned by the parent. Character count is live but polite.

## 7. Code example

```tsx
<Composer placeholder="Share an update" submitLabel="Post" onSubmit={createPost} />
```

## 8. Cross-references

[Field](field.md), [Button](button.md), [Chip](chip.md), [Post](post.md).

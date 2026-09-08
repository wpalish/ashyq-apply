# Chip and StatusChip

## 1. Metadata

- Name: Chip / StatusChip
- Category: Status and metadata
- Status: Stable

## 2. Overview

Use Chip for compact metadata and StatusChip for domain statuses with a human label and explanatory tooltip. Do not use chips as unlabeled buttons or as the only carrier of state.

## 3. Anatomy

Inline container, label, optional title, optional monospace treatment, and one semantic tone modifier.

## 4. Tokens used

`--space-check`, `--space-table-block`, `--radius-sm`, `--border-width-hairline`, `--font-size-xs`, `--font-weight-semibold`, `--font-family-mono`, and all `--color-*-soft`, `--color-*-border`, and semantic foreground aliases.

## 5. Props/API

`Chip({ tone?, children, title?, mono? })`. Tones: neutral, ok, info, warn, risk, demo, accent. `StatusChip({ status, tone })` maps domain status to readable label and tooltip.

## 6. States

Default is neutral. Semantic tones change border/background/text together. Hover/active/disabled/error are not interactive states; wrap an actual control when interaction is required. Focus is handled by that control.

## 7. Code example

```tsx
<StatusChip status={result.eligibility} tone={eligibilityTone[result.eligibility]} />
```

## 8. Cross-references

[Notice](notice.md), [ResultDetail](result-detail.md), [Post](post.md).

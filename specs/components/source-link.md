# SourceLink

## 1. Metadata

- Name: SourceLink
- Category: Evidence navigation
- Status: Stable

## 2. Overview

Use for evidence URLs. Fixture URLs render as non-clickable text plus a demo marker; real URLs open safely in a new tab. Do not create a clickable fixture URL.

## 3. Anatomy

Real-source anchor or fixture text, monospace URL, and optional demo Chip.

## 4. Tokens used

`--color-link`, `--color-link-hover`, `--font-family-mono`, `--font-size-xs`, `--space-0-5`, plus Chip semantic tokens.

## 5. Props/API

`SourceLink({ url })`. Values beginning with `fixture://` use the fixture branch.

## 6. States

Real links have default, hover, and global focus-visible states. Active follows native anchor behavior. Fixture text is non-interactive. Disabled/error are represented by surrounding evidence status, not this component.

## 7. Code example

```tsx
<SourceLink url={claim.source_url} />
```

## 8. Cross-references

[Chip](chip.md), [ResultDetail](result-detail.md), [Notice](notice.md).

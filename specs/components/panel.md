# Panel

## 1. Metadata

- Name: Panel
- Category: Container
- Status: Stable

## 2. Overview

Use to group related evidence or controls. Use `sunken` for inset/supporting content. Do not turn every section into a card; ruled lists remain flat.

## 3. Anatomy

Section root, optional title row, optional hint, optional actions, and child content.

## 4. Tokens used

`--space-5`, `--space-6`, `--color-surface`, `--color-surface-sunken`, `--color-border`, `--border-width-hairline`, `--radius-lg`, `--font-family-display`, `--font-size-md`, `--font-size-sm`, `--color-text-muted`.

## 5. Props/API

`Panel({ title?, hint?, children, sunken?, actions? })`.

## 6. States

Default is a raised paper surface; sunken uses an inset surface. Hover/active/focus/disabled/error are not intrinsic because Panel is not interactive; place stateful controls or Notice inside it.

## 7. Code example

```tsx
<Panel title="Sources" hint="Official evidence used for this result">
  <SourceList />
</Panel>
```

## 8. Cross-references

[Notice](notice.md), [ResultDetail](result-detail.md), [Empty](empty.md).

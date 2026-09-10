# ResultDetail

## 1. Metadata

- Name: ResultDetail
- Category: Evidence detail
- Status: Stable

## 2. Overview

Use inline beneath an expanded shortlist row to explain requirements, funding, costs, documents, ranking, and evidence. Do not show every section at once or detach it from its result row.

## 3. Anatomy

Tablist, selected tab, tabpanel, key/value groups, claims, status Chips, source links, notices, and ranking-axis explanation.

## 4. Tokens used

Tab spacing/borders/interactive colors and motion; claim surface/border/status colors; `--radius-md`; typography aliases; `--space-2` through `--space-5`; and tokens consumed by Chip, StatusChip, Notice, and SourceLink.

## 5. Props/API

`ResultDetail({ result: ProgramResult })`. Internal tab IDs are requirements, funding, costs, documents, score, and sources.

## 6. States

Default requirements tab; hover/focus/active tab states; verified/stale/conflicting/unverified claim states; incomplete-data notices; empty lists; ranking-v2 and legacy-score branches. Disabled does not apply to tabs.

Expanded panels must fit the mobile viewport, including long evidence URLs and
monospace values. Grid tracks may shrink and text may wrap; do not hide overflow.
The bottom navigation must remain visible and accept normal pointer activation
while a funding or cost panel is expanded.

## 7. Code example

```tsx
{open && <ResultDetail result={result} />}
```

## 8. Cross-references

[Chip](chip.md), [Notice](notice.md), [SourceLink](source-link.md), [Panel](panel.md).

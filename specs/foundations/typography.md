# Typography

## Families

- `--font-family-display`: Fraunces for page titles, panel headings, brand, and large statistics.
- `--font-family-ui`: Inter/system UI for controls and body copy.
- `--font-family-mono`: JetBrains Mono/system monospace for sources, identifiers, timestamps, and numeric evidence.

## Scale and hierarchy

Use `--font-size-xs` and `--font-size-sm` for metadata and dense controls, `--font-size-base` for body copy, `--font-size-md` through `--font-size-display` for hierarchy. Brand/stat/micro aliases are reserved for their named roles.

Weights are limited to `--font-weight-medium`, `--font-weight-semibold`, and `--font-weight-bold`. Body text inherits the browser's normal weight. Line-height aliases separate flat numerals, compact UI copy, and normal reading copy.

## Rules

- Component CSS uses `--font-*`, `--line-height-*`, and `--letter-spacing-*` aliases only.
- Display type provides structure; do not use it for long paragraphs or dense tables.
- Monospace indicates machine-originated or source-like content, not emphasis.
- Keep responsive heading behavior inside the upstream fluid size primitives.

## Related

See [spacing](spacing.md) and [token-reference](../tokens/token-reference.md).

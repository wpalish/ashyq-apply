# Typography

## Families

- `--font-family-brand`: Manrope for the wordmark, controls, navigation, and short product headings.
- `--font-family-display`: Fraunces for editorial page titles and narrative section openings only.
- `--font-family-ui`: Inter/system UI for controls and body copy.
- `--font-family-mono`: IBM Plex Mono/system monospace for sources, identifiers, timestamps, and numeric evidence.

## Scale and hierarchy

The product scale is 12 / 14 / 16 / 18 / 22 / 28 / 36 / 48 px. Use `--font-size-xs` and `--font-size-sm` for metadata and dense controls, `--font-size-base` for 16 px body copy, and `--font-size-md` through `--font-size-display` for hierarchy. Brand/stat/micro aliases are reserved for their named roles.

Weights are limited to `--font-weight-medium`, `--font-weight-semibold`, and `--font-weight-bold`. Body text inherits the browser's normal weight. Line-height aliases separate flat numerals, compact UI copy, and normal reading copy.

## Rules

- Component CSS uses `--font-*`, `--line-height-*`, and `--letter-spacing-*` aliases only.
- Display type provides structure; do not use it for long paragraphs or dense tables.
- Brand type and display type are deliberately separate: Manrope keeps actions modern and direct, while Fraunces preserves the editorial strength required by E00.
- Monospace indicates machine-originated or source-like content, not emphasis.
- Keep responsive heading behavior inside the upstream fluid size primitives.
- Test every loaded weight with Kazakh letters `Ә Ғ Қ Ң Ө Ұ Ү Һ І` before release.

## Related

See [spacing](spacing.md) and [token-reference](../tokens/token-reference.md).

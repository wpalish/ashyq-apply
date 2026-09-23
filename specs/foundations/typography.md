# Typography

## Families

- `--font-family-brand`: Onest for the wordmark, controls, navigation, and short product headings.
- `--font-family-display`: Onest for page titles and section openings, using weight and scale for hierarchy.
- `--font-family-ui`: Onest/system UI for controls and body copy.
- `--font-family-data`: Onest with tabular numerals for user-facing amounts, dates, scores and other evidence values.
- `--font-family-mono`: IBM Plex Mono/system monospace for code and technical identifiers.

## Scale and hierarchy

The product scale is 12 / 14 / 16 / 18 / 22 / 28 / 36 / 48 px. Use `--font-size-xs` and `--font-size-sm` for metadata and dense controls, `--font-size-base` for 16 px body copy, and `--font-size-md` through `--font-size-display` for hierarchy. Brand/stat/micro aliases are reserved for their named roles.

Weights are limited to `--font-weight-medium`, `--font-weight-semibold`, and `--font-weight-bold`. Body text inherits the browser's normal weight. Line-height aliases separate flat numerals, compact UI copy, and normal reading copy.

## Rules

- Component CSS uses `--font-*`, `--line-height-*`, and `--letter-spacing-*` aliases only.
- Display type provides structure; do not use it for long paragraphs or dense tables.
- Open Path PR #19 proposes Onest for all user-facing typography after the owner's later feedback about unwanted fonts. The earlier 2026-09-09 Prata/mono choice is superseded in this working UI candidate; final visual approval remains pending. `--font-weight-display` is 600.
- Monospace indicates machine-originated or source-like content, not emphasis.
- Keep responsive heading behavior inside the upstream fluid size primitives.
- Test every loaded weight with Kazakh letters `Ә Ғ Қ Ң Ө Ұ Ү Һ І` before release.

## Related

See [spacing](spacing.md) and [token-reference](../tokens/token-reference.md).

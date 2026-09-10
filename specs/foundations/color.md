# Color

## Intent

ASHYQ Apply uses brandbook v1.1's Open Chapter palette: Paper and Ashyq Ink form the base; Academic Blue carries interaction; Scholar Teal, Library Burgundy, Parchment Gold, and Deadline Coral support named product meanings. Status color is semantic evidence, never decoration. Light and dark themes change Layer 1 primitives while Layer 2 names remain stable.

## Rules

- Component CSS uses only `--color-*` aliases from `tokens.css`; never use `--ds-*` or a raw color.
- Use `--color-text`, `--color-text-muted`, and `--color-text-subtle` in descending emphasis order.
- Use `--color-background` for the page, `--color-surface` for content, `--color-surface-sunken` for inset regions, and `--color-surface-raised` for expanded detail.
- Use `--color-link` for links and `--color-interactive` for controls/focus. Use their hover, soft, and border partners for states.
- Success means verified/met, info means explanatory/plausible, warning means pending/stale, danger means failure/blocking, neutral means unknown, and demo marks synthetic fixtures.
- Exact brand swatches remain primitive tokens. When an exact accent fails 4.5:1 as small text on Paper, use its darker semantic text alias and keep the exact swatch for the border, icon, or large surface.
- Deadline Coral is reserved for time-sensitive information; Parchment Gold is an accent, never body text on Paper.
- Never communicate a status by color alone; pair it with text, shape, or an accessible name.
- Do not reduce opacity on completed research stages: it weakens text and status-chip contrast. Use the named Done status and success dot without fading their container.
- Use muted rather than subtle text on sunken university cards and colored validation gaps; verify the actual surface pair, not only text on Paper. Accent chips/badges use the darker interactive-hover foreground.

## Theme behavior

Dark mode overrides the `--ds-color-*` primitives. Do not add dark-mode component selectors. New semantic colors require a light and dark primitive plus a stable project alias.

## Related

See [token-reference](../tokens/token-reference.md), [elevation](elevation.md), and [motion](motion.md).

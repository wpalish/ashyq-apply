# Color

## Intent

ASHYQ Apply uses an editorial research-dossier palette: warm paper surfaces, deep ink text, and one blue interaction accent. Status color is semantic evidence, never decoration. Light and dark themes change Layer 1 primitives while Layer 2 names remain stable.

## Rules

- Component CSS uses only `--color-*` aliases from `tokens.css`; never use `--ds-*` or a raw color.
- Use `--color-text`, `--color-text-muted`, and `--color-text-subtle` in descending emphasis order.
- Use `--color-background` for the page, `--color-surface` for content, `--color-surface-sunken` for inset regions, and `--color-surface-raised` for expanded detail.
- Use `--color-link` for links and `--color-interactive` for controls/focus. Use their hover, soft, and border partners for states.
- Success means verified/met, info means explanatory/plausible, warning means pending/stale, danger means failure/blocking, neutral means unknown, and demo marks synthetic fixtures.
- Never communicate a status by color alone; pair it with text, shape, or an accessible name.

## Theme behavior

Dark mode overrides the `--ds-color-*` primitives. Do not add dark-mode component selectors. New semantic colors require a light and dark primitive plus a stable project alias.

## Related

See [token-reference](../tokens/token-reference.md), [elevation](elevation.md), and [motion](motion.md).

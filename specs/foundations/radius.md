# Radius

## Scale

| Token | Use |
|---|---|
| `--radius-none` | joined edges and square boundaries |
| `--radius-xs` | tiny swatches |
| `--radius-sm` | chips and compact indicators |
| `--radius-md` | controls, avatars, notices, and documents |
| `--radius-lg` | panels, cards, dialogs, and table cards |
| `--radius-xl` | large product surfaces used sparingly |
| `--radius-page` | 24 px editorial Open Page containers and photography only |
| `--radius-full` | pills and counters |
| `--radius-round` | circular spinners and dots |

## Rules

The product scale is 4 / 8 / 12 px. Radius communicates containment, not decoration. Larger containers receive larger radii; nested elements should not exceed their parent. The 24 px page radius is a brand motif, not a default card radius. Joined controls use `--radius-none` on shared corners. Do not introduce raw percentages or pixel radii in component CSS.

## Related

See [elevation](elevation.md) and [token-reference](../tokens/token-reference.md).

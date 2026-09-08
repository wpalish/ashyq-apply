# Radius

## Scale

| Token | Use |
|---|---|
| `--radius-none` | joined edges and square boundaries |
| `--radius-xs` | tiny swatches |
| `--radius-sm` | chips and compact indicators |
| `--radius-md` | controls, avatars, notices, and documents |
| `--radius-lg` | panels, cards, dialogs, and table cards |
| `--radius-full` | pills and counters |
| `--radius-round` | circular spinners and dots |

## Rules

Radius communicates containment, not decoration. Larger containers receive larger radii; nested elements should not exceed their parent. Joined controls use `--radius-none` on shared corners. Do not introduce raw percentages or pixel radii in component CSS.

## Related

See [elevation](elevation.md) and [token-reference](../tokens/token-reference.md).

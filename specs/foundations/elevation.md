# Elevation

## Levels

- `--shadow-none`: explicitly flat elements and pressed controls.
- `--shadow-sm`: hover lift for controls.
- `--shadow-md`: reserved medium surface lift.
- `--shadow-lg`: dialogs or exceptional overlays.
- `--shadow-focus-ring`: accessible input focus treatment.
- `--shadow-nav-active` / `--shadow-nav-active-mobile`: selected navigation edge.

## Rules

The product is layered primarily with paper tones and borders, not card shadows. Use elevation sparingly. Dark theme swaps the underlying shadow primitives for stronger black-alpha values. Stack order is semantic: base content, sticky cells, sticky edges, header, then modal.

## Related

See [color](color.md), [radius](radius.md), and [token-reference](../tokens/token-reference.md).

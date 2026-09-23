# Motion

## Durations and easing

- `--motion-duration-fast`: hover, border, color, and compact control feedback.
- `--motion-duration-normal`: progress and larger state changes.
- `--motion-duration-pulse`: running-stage pulse cycle.
- `--motion-duration-spin`: loading spinner cycle.
- `--motion-duration-reduced`: near-instant fallback under reduced-motion preferences.
- `--motion-ease-out-expo`: responsive state changes; `--motion-ease-linear` for continuous rotation.

## Rules

Motion explains state change and must not delay work. Interaction feedback stays at or below 200 ms; the spinner/pulse cycle is the only longer continuous exception. Prefer animating color, border, opacity, and transform. Never animate evidence into existence or rely on motion as the only status signal. The global reduced-motion query replaces animation and transition durations with the reduced token.

## Related

See [elevation](elevation.md) and [token-reference](../tokens/token-reference.md).

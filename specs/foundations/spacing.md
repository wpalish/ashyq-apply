# Spacing

## Scale

The core rhythm is `--space-1` through `--space-9`, with `--space-0` for intentional zero. The first eight non-zero steps cover compact controls through major section separation; `--space-9` is fluid page rhythm. Optical tokens such as `--space-control-block` preserve deliberate control geometry where the core scale is too coarse.

## Rules

- Prefer core `--space-*` steps for padding, margin, and gap.
- Use named optical spacing only for the purpose in its name; do not reuse control inset as general layout spacing.
- Use `--space-auto` and `--space-negative-hairline` instead of raw keywords/negative lengths in audited properties.
- Layout dimensions use `--size-*`, borders use `--border-width-*`, and spacing uses `--space-*`.
- Preserve the existing uneven editorial rhythm; do not normalize every component to one padding value.

## Core steps

| Token | Typical use |
|---|---|
| `--space-1` | icon/text micro gap |
| `--space-2` | compact group gap |
| `--space-3` | standard internal gap |
| `--space-4` | standard component inset |
| `--space-5` | medium separation |
| `--space-6` | generous component inset |
| `--space-7` | section separation |
| `--space-8` | large section separation |
| `--space-9` | responsive page rhythm |

## Related

See [radius](radius.md) and [token-reference](../tokens/token-reference.md).

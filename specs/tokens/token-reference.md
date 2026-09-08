# Token reference

> Source of truth: `frontend/src/styles/tokens.css`. Layer 1 variables define upstream primitives. Layer 2 variables are the only variables component CSS may reference. Values shown are the light/default declaration; dark overrides are listed where present.

## Layer 1 — upstream design-system primitives

| Variable | Default value | Dark override | When to use |
|---|---|---|---|
| `--ds-color-paper` | `oklch(97.8% 0.008 85)` | `oklch(17.5% 0.018 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-surface` | `oklch(100% 0 0)` | `oklch(21% 0.020 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-surface-sunken` | `oklch(95.4% 0.010 85)` | `oklch(14.5% 0.016 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-surface-raised` | `oklch(99.2% 0.005 85)` | `oklch(25% 0.022 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-surface-inverse` | `oklch(24% 0.020 265)` | `oklch(93% 0.008 85)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-ink` | `oklch(23% 0.018 265)` | `oklch(93% 0.010 85)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-ink-muted` | `oklch(45% 0.016 265)` | `oklch(74% 0.012 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-ink-subtle` | `oklch(45% 0.012 265)` | `oklch(72% 0.012 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-ink-inverse` | `oklch(96% 0.006 85)` | `oklch(18% 0.018 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-rule` | `oklch(89% 0.010 85)` | `oklch(30% 0.018 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-rule-strong` | `oklch(80% 0.014 85)` | `oklch(40% 0.020 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-accent` | `oklch(42% 0.135 258)` | `oklch(76% 0.115 250)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-accent-hover` | `oklch(39% 0.140 258)` | `oklch(84% 0.110 250)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-accent-soft` | `oklch(94% 0.030 258)` | `oklch(28% 0.055 255)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-accent-border` | `oklch(78% 0.070 258)` | `oklch(45% 0.080 255)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-success` | `oklch(40% 0.115 152)` | `oklch(78% 0.120 152)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-success-soft` | `oklch(94.5% 0.038 152)` | `oklch(27% 0.050 152)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-success-border` | `oklch(80% 0.070 152)` | `oklch(42% 0.070 152)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-info` | `oklch(40% 0.115 245)` | `oklch(78% 0.100 245)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-info-soft` | `oklch(94.5% 0.035 245)` | `oklch(27% 0.045 245)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-info-border` | `oklch(80% 0.062 245)` | `oklch(42% 0.065 245)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-warning` | `oklch(39% 0.125 72)` | `oklch(81% 0.115 78)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-warning-soft` | `oklch(95% 0.045 72)` | `oklch(29% 0.055 70)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-warning-border` | `oklch(82% 0.080 72)` | `oklch(45% 0.080 72)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-danger` | `oklch(42% 0.165 27)` | `oklch(74% 0.140 27)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-danger-soft` | `oklch(95% 0.040 27)` | `oklch(28% 0.060 27)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-danger-border` | `oklch(82% 0.075 27)` | `oklch(45% 0.090 27)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-neutral` | `oklch(42% 0.008 265)` | `oklch(70% 0.008 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-neutral-soft` | `oklch(94% 0.005 265)` | `oklch(26% 0.010 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-neutral-border` | `oklch(84% 0.006 265)` | `oklch(38% 0.010 265)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-demo` | `oklch(40% 0.115 320)` | `oklch(80% 0.105 320)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-demo-soft` | `oklch(95% 0.035 320)` | `oklch(28% 0.055 320)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-demo-border` | `oklch(83% 0.070 320)` | `oklch(45% 0.080 320)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-overlay` | `rgb(0 0 0 / 60%)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-white` | `oklch(99% 0 0)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-transparent` | `transparent` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-color-inherit` | `inherit` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-family-display` | `'Fraunces', 'Iowan Old Style', Georgia, serif` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-family-ui` | `'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-family-mono` | `'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-2xs` | `0.68rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-micro` | `0.7rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-xs` | `0.75rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-sm` | `0.8125rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-base` | `0.9375rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-md` | `1.0625rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-lg` | `clamp(1.25rem, 1.1rem + 0.5vw, 1.5rem)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-xl` | `clamp(1.6rem, 1.3rem + 1.2vw, 2.25rem)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-display` | `clamp(2.1rem, 1.4rem + 3vw, 3.5rem)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-brand` | `1.45rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-stat` | `1.9rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-size-code` | `0.92em` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-weight-medium` | `500` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-weight-semibold` | `600` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-font-weight-bold` | `700` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-line-height-flat` | `1` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-line-height-tight` | `1.15` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-line-height-caption` | `1.3` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-line-height-snug` | `1.35` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-line-height-compact` | `1.55` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-line-height-normal` | `1.6` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-letter-spacing-tight` | `-0.015em` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-letter-spacing-display` | `-0.03em` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-letter-spacing-avatar` | `0.02em` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-letter-spacing-label` | `0.05em` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-letter-spacing-medium` | `0.07em` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-letter-spacing-wide` | `0.08em` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-letter-spacing-wider` | `0.09em` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-letter-spacing-widest` | `0.12em` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-0` | `0` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-auto` | `auto` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-negative-hairline` | `-1px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-hairline` | `1px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-0-5` | `2px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-0-75` | `3px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-1` | `0.25rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-1-25` | `5px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-1-5` | `0.375rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-2` | `0.5rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-2-5` | `0.625rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-3` | `0.75rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-4` | `1rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-5` | `1.25rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-6` | `1.5rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-7` | `2rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-8` | `3rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-9` | `clamp(3rem, 2rem + 4vw, 5.5rem)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-control-block` | `0.42rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-control-inline` | `0.6rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-control-compact` | `0.35rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-dot-offset` | `0.42rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-checkbox-offset` | `0.2rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-panel-inset` | `0.18rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-button-block` | `0.44rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-button-inline` | `0.9rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-button-compact-inline` | `0.6rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-table-block` | `0.45rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-table-inline` | `0.3rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-table-wide-inline` | `0.5rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-stage-dot` | `0.7rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-space-check` | `0.1rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-border-width-hairline` | `1px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-border-width-medium` | `2px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-border-width-strong` | `3px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-radius-sm` | `3px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-radius-xs` | `2px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-radius-none` | `0` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-radius-md` | `6px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-radius-lg` | `10px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-radius-full` | `999px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-radius-round` | `50%` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-shadow-none` | `none` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-shadow-sm` | `0 1px 2px oklch(23% 0.018 265 / 0.06)` | `0 1px 2px oklch(0% 0 0 / 0.30)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-shadow-md` | `0 2px 6px oklch(23% 0.018 265 / 0.08), 0 1px 2px oklch(23% 0.018 265 / 0.05)` | `0 2px 8px oklch(0% 0 0 / 0.38), 0 1px 2px oklch(0% 0 0 / 0.25)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-shadow-lg` | `0 12px 32px oklch(23% 0.018 265 / 0.13), 0 2px 8px oklch(23% 0.018 265 / 0.07)` | `0 14px 38px oklch(0% 0 0 / 0.48), 0 2px 8px oklch(0% 0 0 / 0.30)` | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-shadow-focus` | `0 0 0 3px var(--ds-color-accent-soft)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-shadow-nav-active` | `inset 3px 0 0 var(--ds-color-accent)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-shadow-nav-active-mobile` | `inset 0 -2px 0 var(--ds-color-accent)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-z-base` | `1` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-z-sticky-cell` | `2` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-z-sticky-edge` | `3` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-z-header` | `20` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-z-modal` | `50` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-duration-reduced` | `0.01ms` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-duration-fast` | `120ms` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-duration-normal` | `220ms` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-duration-pulse` | `1.4s` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-duration-spin` | `0.8s` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-ease-standard` | `ease` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-ease-linear` | `linear` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-ease-out-expo` | `cubic-bezier(0.16, 1, 0.3, 1)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-sidebar` | `15.5rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-measure` | `68ch` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-auth-card` | `30rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-content` | `52rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-reading-column` | `46rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-profile-bio` | `62ch` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-table-default` | `64.25rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-table-ranked` | `69.75rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-column-xs` | `4.5rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-column-sm` | `6rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-column-md` | `6.5rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-column-lg` | `6.75rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-column-xl` | `7.5rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-badge-min` | `1.1rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-stage-track` | `1.5rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-control-min` | `9.5rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-grid-sm` | `9rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-grid-md` | `11rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-grid-lg` | `13rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-person-card` | `19rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-university-min` | `10rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-university-max` | `18rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-bubble-max` | `34rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-icon` | `1rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-avatar` | `2rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-avatar-lg` | `3rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-fund-bar` | `1.4rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-stage-dot` | `0.7rem` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-meter` | `6px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-swatch` | `10px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-size-visually-hidden` | `1px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-blur-header` | `8px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-translate-pressed` | `1px` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-background-none` | `none` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-background-app-texture` | `radial-gradient(circle at 12% 8%, oklch(from var(--ds-color-accent) l c h / 0.030), transparent 42%), radial-gradient(circle at 88% 4%, oklch(from var(--ds-color-demo) l c h / 0.022), transparent 38%)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-background-meter` | `linear-gradient(90deg, var(--ds-color-accent), oklch(from var(--ds-color-accent) calc(l + 0.12) c calc(h + 22)))` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |
| `--ds-background-unknown-pattern` | `repeating-linear-gradient(45deg, var(--ds-color-neutral-soft), var(--ds-color-neutral-soft) 5px, var(--ds-color-surface-sunken) 5px, var(--ds-color-surface-sunken) 10px)` | — | Upstream primitive. Define or theme at the design-system boundary; never reference directly from component CSS. |

## Layer 2 — ASHYQ Apply project aliases

| Variable | Value | When to use |
|---|---|---|
| `--color-background` | `var(--ds-color-paper, #f8f6f1)` | Use for background color semantics; choose by meaning, not visual similarity. |
| `--color-surface` | `var(--ds-color-surface, #ffffff)` | Use for surface color semantics; choose by meaning, not visual similarity. |
| `--color-surface-sunken` | `var(--ds-color-surface-sunken, #f1eee8)` | Use for surface sunken color semantics; choose by meaning, not visual similarity. |
| `--color-surface-raised` | `var(--ds-color-surface-raised, #fdfcf9)` | Use for surface raised color semantics; choose by meaning, not visual similarity. |
| `--color-surface-inverse` | `var(--ds-color-surface-inverse, #252733)` | Use for surface inverse color semantics; choose by meaning, not visual similarity. |
| `--color-text` | `var(--ds-color-ink, #292a2e)` | Use for text color semantics; choose by meaning, not visual similarity. |
| `--color-text-muted` | `var(--ds-color-ink-muted, #656770)` | Use for text muted color semantics; choose by meaning, not visual similarity. |
| `--color-text-subtle` | `var(--ds-color-ink-subtle, #6a6b72)` | Use for text subtle color semantics; choose by meaning, not visual similarity. |
| `--color-text-inverse` | `var(--ds-color-ink-inverse, #f4f2ed)` | Use for text inverse color semantics; choose by meaning, not visual similarity. |
| `--color-border` | `var(--ds-color-rule, #dedbd4)` | Use for border color semantics; choose by meaning, not visual similarity. |
| `--color-border-strong` | `var(--ds-color-rule-strong, #c6c2b9)` | Use for border strong color semantics; choose by meaning, not visual similarity. |
| `--color-link` | `var(--ds-color-accent, #315f9d)` | Use for link color semantics; choose by meaning, not visual similarity. |
| `--color-link-hover` | `var(--ds-color-accent-hover, #29568f)` | Use for link hover color semantics; choose by meaning, not visual similarity. |
| `--color-interactive` | `var(--ds-color-accent, #315f9d)` | Use for interactive color semantics; choose by meaning, not visual similarity. |
| `--color-interactive-hover` | `var(--ds-color-accent-hover, #29568f)` | Use for interactive hover color semantics; choose by meaning, not visual similarity. |
| `--color-interactive-soft` | `var(--ds-color-accent-soft, #e9eff8)` | Use for interactive soft color semantics; choose by meaning, not visual similarity. |
| `--color-interactive-border` | `var(--ds-color-accent-border, #9eb7d8)` | Use for interactive border color semantics; choose by meaning, not visual similarity. |
| `--color-focus-ring` | `var(--ds-color-accent, #315f9d)` | Use for focus ring color semantics; choose by meaning, not visual similarity. |
| `--color-success` | `var(--ds-color-success, #28754c)` | Use for success color semantics; choose by meaning, not visual similarity. |
| `--color-success-soft` | `var(--ds-color-success-soft, #e7f4eb)` | Use for success soft color semantics; choose by meaning, not visual similarity. |
| `--color-success-border` | `var(--ds-color-success-border, #9fcbb0)` | Use for success border color semantics; choose by meaning, not visual similarity. |
| `--color-info` | `var(--ds-color-info, #2c6e91)` | Use for info color semantics; choose by meaning, not visual similarity. |
| `--color-info-soft` | `var(--ds-color-info-soft, #e6f1f6)` | Use for info soft color semantics; choose by meaning, not visual similarity. |
| `--color-info-border` | `var(--ds-color-info-border, #9ec7d9)` | Use for info border color semantics; choose by meaning, not visual similarity. |
| `--color-warning` | `var(--ds-color-warning, #8a5b12)` | Use for warning color semantics; choose by meaning, not visual similarity. |
| `--color-warning-soft` | `var(--ds-color-warning-soft, #f8efd9)` | Use for warning soft color semantics; choose by meaning, not visual similarity. |
| `--color-warning-border` | `var(--ds-color-warning-border, #d8bb7c)` | Use for warning border color semantics; choose by meaning, not visual similarity. |
| `--color-danger` | `var(--ds-color-danger, #a43b34)` | Use for danger color semantics; choose by meaning, not visual similarity. |
| `--color-danger-soft` | `var(--ds-color-danger-soft, #f8e9e6)` | Use for danger soft color semantics; choose by meaning, not visual similarity. |
| `--color-danger-border` | `var(--ds-color-danger-border, #dda5a0)` | Use for danger border color semantics; choose by meaning, not visual similarity. |
| `--color-neutral` | `var(--ds-color-neutral, #66666c)` | Use for neutral color semantics; choose by meaning, not visual similarity. |
| `--color-neutral-soft` | `var(--ds-color-neutral-soft, #efeff0)` | Use for neutral soft color semantics; choose by meaning, not visual similarity. |
| `--color-neutral-border` | `var(--ds-color-neutral-border, #d0d0d2)` | Use for neutral border color semantics; choose by meaning, not visual similarity. |
| `--color-demo` | `var(--ds-color-demo, #845493)` | Use for demo color semantics; choose by meaning, not visual similarity. |
| `--color-demo-soft` | `var(--ds-color-demo-soft, #f4eaf5)` | Use for demo soft color semantics; choose by meaning, not visual similarity. |
| `--color-demo-border` | `var(--ds-color-demo-border, #cfacd4)` | Use for demo border color semantics; choose by meaning, not visual similarity. |
| `--color-overlay` | `var(--ds-color-overlay, rgb(0 0 0 / 60%))` | Use for overlay color semantics; choose by meaning, not visual similarity. |
| `--color-on-interactive` | `var(--ds-color-white, #ffffff)` | Use for on interactive color semantics; choose by meaning, not visual similarity. |
| `--color-transparent` | `var(--ds-color-transparent, transparent)` | Use for transparent color semantics; choose by meaning, not visual similarity. |
| `--color-inherit` | `var(--ds-color-inherit, inherit)` | Use for inherit color semantics; choose by meaning, not visual similarity. |
| `--font-family-display` | `var(--ds-font-family-display, Georgia, serif)` | Use for display typography. |
| `--font-family-ui` | `var(--ds-font-family-ui, system-ui, sans-serif)` | Use for ui typography. |
| `--font-family-mono` | `var(--ds-font-family-mono, ui-monospace, monospace)` | Use for mono typography. |
| `--font-size-2xs` | `var(--ds-font-size-2xs, 0.68rem)` | Use for the 2xs text role. |
| `--font-size-micro` | `var(--ds-font-size-micro, 0.7rem)` | Use for the micro text role. |
| `--font-size-xs` | `var(--ds-font-size-xs, 0.75rem)` | Use for the xs text role. |
| `--font-size-sm` | `var(--ds-font-size-sm, 0.8125rem)` | Use for the sm text role. |
| `--font-size-base` | `var(--ds-font-size-base, 0.9375rem)` | Use for the base text role. |
| `--font-size-md` | `var(--ds-font-size-md, 1.0625rem)` | Use for the md text role. |
| `--font-size-lg` | `var(--ds-font-size-lg, 1.5rem)` | Use for the lg text role. |
| `--font-size-xl` | `var(--ds-font-size-xl, 2.25rem)` | Use for the xl text role. |
| `--font-size-display` | `var(--ds-font-size-display, 3.5rem)` | Use for the display text role. |
| `--font-size-brand` | `var(--ds-font-size-brand, 1.45rem)` | Use for the brand text role. |
| `--font-size-stat` | `var(--ds-font-size-stat, 1.9rem)` | Use for the stat text role. |
| `--font-size-code` | `var(--ds-font-size-code, 0.92em)` | Use for the code text role. |
| `--font-weight-medium` | `var(--ds-font-weight-medium, 500)` | Use for medium emphasis. |
| `--font-weight-semibold` | `var(--ds-font-weight-semibold, 600)` | Use for semibold emphasis. |
| `--font-weight-bold` | `var(--ds-font-weight-bold, 700)` | Use for bold emphasis. |
| `--line-height-flat` | `var(--ds-line-height-flat, 1)` | Use for flat text rhythm. |
| `--line-height-tight` | `var(--ds-line-height-tight, 1.15)` | Use for tight text rhythm. |
| `--line-height-caption` | `var(--ds-line-height-caption, 1.3)` | Use for caption text rhythm. |
| `--line-height-snug` | `var(--ds-line-height-snug, 1.35)` | Use for snug text rhythm. |
| `--line-height-compact` | `var(--ds-line-height-compact, 1.55)` | Use for compact text rhythm. |
| `--line-height-normal` | `var(--ds-line-height-normal, 1.6)` | Use for normal text rhythm. |
| `--letter-spacing-tight` | `var(--ds-letter-spacing-tight, -0.015em)` | Use for tight tracking. |
| `--letter-spacing-display` | `var(--ds-letter-spacing-display, -0.03em)` | Use for display tracking. |
| `--letter-spacing-avatar` | `var(--ds-letter-spacing-avatar, 0.02em)` | Use for avatar tracking. |
| `--letter-spacing-label` | `var(--ds-letter-spacing-label, 0.05em)` | Use for label tracking. |
| `--letter-spacing-medium` | `var(--ds-letter-spacing-medium, 0.07em)` | Use for medium tracking. |
| `--letter-spacing-wide` | `var(--ds-letter-spacing-wide, 0.08em)` | Use for wide tracking. |
| `--letter-spacing-wider` | `var(--ds-letter-spacing-wider, 0.09em)` | Use for wider tracking. |
| `--letter-spacing-widest` | `var(--ds-letter-spacing-widest, 0.12em)` | Use for widest tracking. |
| `--space-0` | `var(--ds-space-0, 0)` | Use for 0 spacing; prefer core numbered steps for general layout. |
| `--space-auto` | `var(--ds-space-auto, auto)` | Use for auto spacing; prefer core numbered steps for general layout. |
| `--space-negative-hairline` | `var(--ds-space-negative-hairline, -1px)` | Use for negative hairline spacing; prefer core numbered steps for general layout. |
| `--space-hairline` | `var(--ds-space-hairline, 1px)` | Use for hairline spacing; prefer core numbered steps for general layout. |
| `--space-0-5` | `var(--ds-space-0-5, 2px)` | Use for 0 5 spacing; prefer core numbered steps for general layout. |
| `--space-0-75` | `var(--ds-space-0-75, 3px)` | Use for 0 75 spacing; prefer core numbered steps for general layout. |
| `--space-1` | `var(--ds-space-1, 0.25rem)` | Use for 1 spacing; prefer core numbered steps for general layout. |
| `--space-1-25` | `var(--ds-space-1-25, 5px)` | Use for 1 25 spacing; prefer core numbered steps for general layout. |
| `--space-1-5` | `var(--ds-space-1-5, 0.375rem)` | Use for 1 5 spacing; prefer core numbered steps for general layout. |
| `--space-2` | `var(--ds-space-2, 0.5rem)` | Use for 2 spacing; prefer core numbered steps for general layout. |
| `--space-2-5` | `var(--ds-space-2-5, 0.625rem)` | Use for 2 5 spacing; prefer core numbered steps for general layout. |
| `--space-3` | `var(--ds-space-3, 0.75rem)` | Use for 3 spacing; prefer core numbered steps for general layout. |
| `--space-4` | `var(--ds-space-4, 1rem)` | Use for 4 spacing; prefer core numbered steps for general layout. |
| `--space-5` | `var(--ds-space-5, 1.25rem)` | Use for 5 spacing; prefer core numbered steps for general layout. |
| `--space-6` | `var(--ds-space-6, 1.5rem)` | Use for 6 spacing; prefer core numbered steps for general layout. |
| `--space-7` | `var(--ds-space-7, 2rem)` | Use for 7 spacing; prefer core numbered steps for general layout. |
| `--space-8` | `var(--ds-space-8, 3rem)` | Use for 8 spacing; prefer core numbered steps for general layout. |
| `--space-9` | `var(--ds-space-9, 5.5rem)` | Use for 9 spacing; prefer core numbered steps for general layout. |
| `--space-control-block` | `var(--ds-space-control-block, 0.42rem)` | Use for control block spacing; prefer core numbered steps for general layout. |
| `--space-control-inline` | `var(--ds-space-control-inline, 0.6rem)` | Use for control inline spacing; prefer core numbered steps for general layout. |
| `--space-control-compact` | `var(--ds-space-control-compact, 0.35rem)` | Use for control compact spacing; prefer core numbered steps for general layout. |
| `--space-dot-offset` | `var(--ds-space-dot-offset, 0.42rem)` | Use for dot offset spacing; prefer core numbered steps for general layout. |
| `--space-checkbox-offset` | `var(--ds-space-checkbox-offset, 0.2rem)` | Use for checkbox offset spacing; prefer core numbered steps for general layout. |
| `--space-panel-inset` | `var(--ds-space-panel-inset, 0.18rem)` | Use for panel inset spacing; prefer core numbered steps for general layout. |
| `--space-button-block` | `var(--ds-space-button-block, 0.44rem)` | Use for button block spacing; prefer core numbered steps for general layout. |
| `--space-button-inline` | `var(--ds-space-button-inline, 0.9rem)` | Use for button inline spacing; prefer core numbered steps for general layout. |
| `--space-button-compact-inline` | `var(--ds-space-button-compact-inline, 0.6rem)` | Use for button compact inline spacing; prefer core numbered steps for general layout. |
| `--space-table-block` | `var(--ds-space-table-block, 0.45rem)` | Use for table block spacing; prefer core numbered steps for general layout. |
| `--space-table-inline` | `var(--ds-space-table-inline, 0.3rem)` | Use for table inline spacing; prefer core numbered steps for general layout. |
| `--space-table-wide-inline` | `var(--ds-space-table-wide-inline, 0.5rem)` | Use for table wide inline spacing; prefer core numbered steps for general layout. |
| `--space-stage-dot` | `var(--ds-space-stage-dot, 0.7rem)` | Use for stage dot spacing; prefer core numbered steps for general layout. |
| `--space-check` | `var(--ds-space-check, 0.1rem)` | Use for check spacing; prefer core numbered steps for general layout. |
| `--border-width-hairline` | `var(--ds-border-width-hairline, 1px)` | Use for hairline borders and outlines. |
| `--border-width-medium` | `var(--ds-border-width-medium, 2px)` | Use for medium borders and outlines. |
| `--border-width-strong` | `var(--ds-border-width-strong, 3px)` | Use for strong borders and outlines. |
| `--radius-sm` | `var(--ds-radius-sm, 3px)` | Use for sm corner treatment. |
| `--radius-xs` | `var(--ds-radius-xs, 2px)` | Use for xs corner treatment. |
| `--radius-none` | `var(--ds-radius-none, 0)` | Use for none corner treatment. |
| `--radius-md` | `var(--ds-radius-md, 6px)` | Use for md corner treatment. |
| `--radius-lg` | `var(--ds-radius-lg, 10px)` | Use for lg corner treatment. |
| `--radius-full` | `var(--ds-radius-full, 999px)` | Use for full corner treatment. |
| `--radius-round` | `var(--ds-radius-round, 50%)` | Use for round corner treatment. |
| `--shadow-none` | `var(--ds-shadow-none, none)` | Use for none elevation or focus treatment. |
| `--shadow-sm` | `var(--ds-shadow-sm, none)` | Use for sm elevation or focus treatment. |
| `--shadow-md` | `var(--ds-shadow-md, none)` | Use for md elevation or focus treatment. |
| `--shadow-lg` | `var(--ds-shadow-lg, none)` | Use for lg elevation or focus treatment. |
| `--shadow-focus-ring` | `var(--ds-shadow-focus, 0 0 0 3px var(--color-interactive-soft))` | Use for focus ring elevation or focus treatment. |
| `--shadow-nav-active` | `var(--ds-shadow-nav-active, inset 3px 0 0 var(--color-interactive))` | Use for nav active elevation or focus treatment. |
| `--shadow-nav-active-mobile` | `var(--ds-shadow-nav-active-mobile, inset 0 -2px 0 var(--color-interactive))` | Use for nav active mobile elevation or focus treatment. |
| `--z-base` | `var(--ds-z-base, 1)` | Use for the base stack layer. |
| `--z-sticky-cell` | `var(--ds-z-sticky-cell, 2)` | Use for the sticky cell stack layer. |
| `--z-sticky-edge` | `var(--ds-z-sticky-edge, 3)` | Use for the sticky edge stack layer. |
| `--z-header` | `var(--ds-z-header, 20)` | Use for the header stack layer. |
| `--z-modal` | `var(--ds-z-modal, 50)` | Use for the modal stack layer. |
| `--motion-duration-reduced` | `var(--ds-duration-reduced, 0.01ms)` | Use for duration reduced motion behavior. |
| `--motion-duration-fast` | `var(--ds-duration-fast, 120ms)` | Use for duration fast motion behavior. |
| `--motion-duration-normal` | `var(--ds-duration-normal, 220ms)` | Use for duration normal motion behavior. |
| `--motion-duration-pulse` | `var(--ds-duration-pulse, 1.4s)` | Use for duration pulse motion behavior. |
| `--motion-duration-spin` | `var(--ds-duration-spin, 0.8s)` | Use for duration spin motion behavior. |
| `--motion-ease-standard` | `var(--ds-ease-standard, ease)` | Use for ease standard motion behavior. |
| `--motion-ease-linear` | `var(--ds-ease-linear, linear)` | Use for ease linear motion behavior. |
| `--motion-ease-out-expo` | `var(--ds-ease-out-expo, cubic-bezier(0.16, 1, 0.3, 1))` | Use for ease out expo motion behavior. |
| `--size-sidebar` | `var(--ds-size-sidebar, 15.5rem)` | Use for the named sidebar layout dimension only. |
| `--size-measure` | `var(--ds-size-measure, 68ch)` | Use for the named measure layout dimension only. |
| `--size-auth-card` | `var(--ds-size-auth-card, 30rem)` | Use for the named auth card layout dimension only. |
| `--size-content` | `var(--ds-size-content, 52rem)` | Use for the named content layout dimension only. |
| `--size-reading-column` | `var(--ds-size-reading-column, 46rem)` | Use for the named reading column layout dimension only. |
| `--size-profile-bio` | `var(--ds-size-profile-bio, 62ch)` | Use for the named profile bio layout dimension only. |
| `--size-table-default` | `var(--ds-size-table-default, 64.25rem)` | Use for the named table default layout dimension only. |
| `--size-table-ranked` | `var(--ds-size-table-ranked, 69.75rem)` | Use for the named table ranked layout dimension only. |
| `--size-column-xs` | `var(--ds-size-column-xs, 4.5rem)` | Use for the named column xs layout dimension only. |
| `--size-column-sm` | `var(--ds-size-column-sm, 6rem)` | Use for the named column sm layout dimension only. |
| `--size-column-md` | `var(--ds-size-column-md, 6.5rem)` | Use for the named column md layout dimension only. |
| `--size-column-lg` | `var(--ds-size-column-lg, 6.75rem)` | Use for the named column lg layout dimension only. |
| `--size-column-xl` | `var(--ds-size-column-xl, 7.5rem)` | Use for the named column xl layout dimension only. |
| `--size-badge-min` | `var(--ds-size-badge-min, 1.1rem)` | Use for the named badge min layout dimension only. |
| `--size-stage-track` | `var(--ds-size-stage-track, 1.5rem)` | Use for the named stage track layout dimension only. |
| `--size-control-min` | `var(--ds-size-control-min, 9.5rem)` | Use for the named control min layout dimension only. |
| `--size-grid-sm` | `var(--ds-size-grid-sm, 9rem)` | Use for the named grid sm layout dimension only. |
| `--size-grid-md` | `var(--ds-size-grid-md, 11rem)` | Use for the named grid md layout dimension only. |
| `--size-grid-lg` | `var(--ds-size-grid-lg, 13rem)` | Use for the named grid lg layout dimension only. |
| `--size-person-card` | `var(--ds-size-person-card, 19rem)` | Use for the named person card layout dimension only. |
| `--size-university-min` | `var(--ds-size-university-min, 10rem)` | Use for the named university min layout dimension only. |
| `--size-university-max` | `var(--ds-size-university-max, 18rem)` | Use for the named university max layout dimension only. |
| `--size-bubble-max` | `var(--ds-size-bubble-max, 34rem)` | Use for the named bubble max layout dimension only. |
| `--size-icon` | `var(--ds-size-icon, 1rem)` | Use for the named icon layout dimension only. |
| `--size-avatar` | `var(--ds-size-avatar, 2rem)` | Use for the named avatar layout dimension only. |
| `--size-avatar-lg` | `var(--ds-size-avatar-lg, 3rem)` | Use for the named avatar lg layout dimension only. |
| `--size-fund-bar` | `var(--ds-size-fund-bar, 1.4rem)` | Use for the named fund bar layout dimension only. |
| `--size-stage-dot` | `var(--ds-size-stage-dot, 0.7rem)` | Use for the named stage dot layout dimension only. |
| `--size-meter` | `var(--ds-size-meter, 6px)` | Use for the named meter layout dimension only. |
| `--size-swatch` | `var(--ds-size-swatch, 10px)` | Use for the named swatch layout dimension only. |
| `--size-visually-hidden` | `var(--ds-size-visually-hidden, 1px)` | Use for the named visually hidden layout dimension only. |
| `--effect-header-blur` | `var(--ds-blur-header, 8px)` | Use for the header blur visual effect. |
| `--transform-pressed` | `var(--ds-translate-pressed, 1px)` | Use for the pressed transform. |
| `--background-none` | `var(--ds-background-none, none)` | Use for the none background treatment. |
| `--background-app-texture` | `var(--ds-background-app-texture, none)` | Use for the app texture background treatment. |
| `--background-meter` | `var(--ds-background-meter, var(--color-interactive))` | Use for the meter background treatment. |
| `--background-unknown-pattern` | `var(--ds-background-unknown-pattern, var(--color-neutral-soft))` | Use for the unknown pattern background treatment. |

## Consumption contract

1. Components in `global.css` and `components.css` reference Layer 2 only.
2. Theme changes override Layer 1; aliases and components remain unchanged.
3. Add a primitive and a semantic alias together. Document the alias here and in the relevant foundation/component spec.
4. Run `node scripts/token-audit.js`; zero errors are required.

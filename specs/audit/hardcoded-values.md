# Hardcoded visual values: pre-migration audit

> Baseline captured from `frontend/src/styles/*.css` before token migration. This report is historical evidence; run `node scripts/token-audit.js` for current enforcement.

## Scope and method

- Files scanned: **3** CSS/SCSS files.
- Hardcoded occurrences: **303** total (**297 errors**, **6 warnings**).
- Counts are occurrences, not unique literals. A complete shadow is one shadow occurrence; each standalone color or length is one occurrence.
- Existing OKLCH colors are included because they are hardcoded colors even though the requested examples named hex/RGB formats.
- Dependency, generated-output, virtual-environment, and nested-worktree directories are excluded.

## Totals by category

| Category | Count | Severity |
|---|---:|---|
| color | 103 | error |
| spacing | 127 | error |
| font-size | 11 | error |
| font-weight | 24 | error |
| line-height | 6 | error |
| border-radius | 8 | error |
| box-shadow | 13 | error |
| z-index | 5 | error |
| motion | 6 | warning |

## Files with the most hardcoded values

| Rank | File | Count |
|---:|---|---:|
| 1 | `frontend/src/styles/tokens.css` | 131 |
| 2 | `frontend/src/styles/components.css` | 118 |
| 3 | `frontend/src/styles/global.css` | 54 |

## color

- `frontend/src/styles/components.css:127` — `color: oklch(99% 0 0)`
- `frontend/src/styles/components.css:423` — `background: rgb(0 0 0 / 60%)`
- `frontend/src/styles/components.css:610` — `color: oklch(99% 0 0)`
- `frontend/src/styles/global.css:224` — `color: oklch(99% 0 0)`
- `frontend/src/styles/tokens.css:15` — `--paper: oklch(97.8% 0.008 85)`
- `frontend/src/styles/tokens.css:16` — `--surface: oklch(100% 0 0)`
- `frontend/src/styles/tokens.css:17` — `--surface-sunken: oklch(95.4% 0.010 85)`
- `frontend/src/styles/tokens.css:18` — `--surface-raised: oklch(99.2% 0.005 85)`
- `frontend/src/styles/tokens.css:19` — `--surface-inverted: oklch(24% 0.020 265)`
- `frontend/src/styles/tokens.css:21` — `--ink: oklch(23% 0.018 265)`
- `frontend/src/styles/tokens.css:22` — `--ink-muted: oklch(45% 0.016 265)`
- `frontend/src/styles/tokens.css:23` — `--ink-faint: oklch(45% 0.012 265)`
- `frontend/src/styles/tokens.css:24` — `--ink-inverted: oklch(96% 0.006 85)`
- `frontend/src/styles/tokens.css:26` — `--rule: oklch(89% 0.010 85)`
- `frontend/src/styles/tokens.css:27` — `--rule-strong: oklch(80% 0.014 85)`
- `frontend/src/styles/tokens.css:30` — `--accent: oklch(42% 0.135 258)`
- `frontend/src/styles/tokens.css:31` — `--accent-hover: oklch(39% 0.140 258)`
- `frontend/src/styles/tokens.css:32` — `--accent-soft: oklch(94% 0.030 258)`
- `frontend/src/styles/tokens.css:33` — `--accent-border: oklch(78% 0.070 258)`
- `frontend/src/styles/tokens.css:36` — `--ok: oklch(40% 0.115 152)`
- `frontend/src/styles/tokens.css:37` — `--ok-soft: oklch(94.5% 0.038 152)`
- `frontend/src/styles/tokens.css:38` — `--ok-border: oklch(80% 0.070 152)`
- `frontend/src/styles/tokens.css:40` — `--info: oklch(40% 0.115 245)`
- `frontend/src/styles/tokens.css:41` — `--info-soft: oklch(94.5% 0.035 245)`
- `frontend/src/styles/tokens.css:42` — `--info-border: oklch(80% 0.062 245)`
- `frontend/src/styles/tokens.css:44` — `--warn: oklch(39% 0.125 72)`
- `frontend/src/styles/tokens.css:45` — `--warn-soft: oklch(95% 0.045 72)`
- `frontend/src/styles/tokens.css:46` — `--warn-border: oklch(82% 0.080 72)`
- `frontend/src/styles/tokens.css:48` — `--risk: oklch(42% 0.165 27)`
- `frontend/src/styles/tokens.css:49` — `--risk-soft: oklch(95% 0.040 27)`
- `frontend/src/styles/tokens.css:50` — `--risk-border: oklch(82% 0.075 27)`
- `frontend/src/styles/tokens.css:52` — `--unknown: oklch(42% 0.008 265)`
- `frontend/src/styles/tokens.css:53` — `--unknown-soft: oklch(94% 0.005 265)`
- `frontend/src/styles/tokens.css:54` — `--unknown-border: oklch(84% 0.006 265)`
- `frontend/src/styles/tokens.css:56` — `--demo: oklch(40% 0.115 320)`
- `frontend/src/styles/tokens.css:57` — `--demo-soft: oklch(95% 0.035 320)`
- `frontend/src/styles/tokens.css:58` — `--demo-border: oklch(83% 0.070 320)`
- `frontend/src/styles/tokens.css:112` — `--paper: oklch(17.5% 0.018 265)`
- `frontend/src/styles/tokens.css:113` — `--surface: oklch(21% 0.020 265)`
- `frontend/src/styles/tokens.css:114` — `--surface-sunken: oklch(14.5% 0.016 265)`
- `frontend/src/styles/tokens.css:115` — `--surface-raised: oklch(25% 0.022 265)`
- `frontend/src/styles/tokens.css:116` — `--surface-inverted: oklch(93% 0.008 85)`
- `frontend/src/styles/tokens.css:118` — `--ink: oklch(93% 0.010 85)`
- `frontend/src/styles/tokens.css:119` — `--ink-muted: oklch(74% 0.012 265)`
- `frontend/src/styles/tokens.css:120` — `--ink-faint: oklch(72% 0.012 265)`
- `frontend/src/styles/tokens.css:121` — `--ink-inverted: oklch(18% 0.018 265)`
- `frontend/src/styles/tokens.css:123` — `--rule: oklch(30% 0.018 265)`
- `frontend/src/styles/tokens.css:124` — `--rule-strong: oklch(40% 0.020 265)`
- `frontend/src/styles/tokens.css:126` — `--accent: oklch(76% 0.115 250)`
- `frontend/src/styles/tokens.css:127` — `--accent-hover: oklch(84% 0.110 250)`
- `frontend/src/styles/tokens.css:128` — `--accent-soft: oklch(28% 0.055 255)`
- `frontend/src/styles/tokens.css:129` — `--accent-border: oklch(45% 0.080 255)`
- `frontend/src/styles/tokens.css:131` — `--ok: oklch(78% 0.120 152)`
- `frontend/src/styles/tokens.css:132` — `--ok-soft: oklch(27% 0.050 152)`
- `frontend/src/styles/tokens.css:133` — `--ok-border: oklch(42% 0.070 152)`
- `frontend/src/styles/tokens.css:135` — `--info: oklch(78% 0.100 245)`
- `frontend/src/styles/tokens.css:136` — `--info-soft: oklch(27% 0.045 245)`
- `frontend/src/styles/tokens.css:137` — `--info-border: oklch(42% 0.065 245)`
- `frontend/src/styles/tokens.css:139` — `--warn: oklch(81% 0.115 78)`
- `frontend/src/styles/tokens.css:140` — `--warn-soft: oklch(29% 0.055 70)`
- `frontend/src/styles/tokens.css:141` — `--warn-border: oklch(45% 0.080 72)`
- `frontend/src/styles/tokens.css:143` — `--risk: oklch(74% 0.140 27)`
- `frontend/src/styles/tokens.css:144` — `--risk-soft: oklch(28% 0.060 27)`
- `frontend/src/styles/tokens.css:145` — `--risk-border: oklch(45% 0.090 27)`
- `frontend/src/styles/tokens.css:147` — `--unknown: oklch(70% 0.008 265)`
- `frontend/src/styles/tokens.css:148` — `--unknown-soft: oklch(26% 0.010 265)`
- `frontend/src/styles/tokens.css:149` — `--unknown-border: oklch(38% 0.010 265)`
- `frontend/src/styles/tokens.css:151` — `--demo: oklch(80% 0.105 320)`
- `frontend/src/styles/tokens.css:152` — `--demo-soft: oklch(28% 0.055 320)`
- `frontend/src/styles/tokens.css:153` — `--demo-border: oklch(45% 0.080 320)`
- `frontend/src/styles/tokens.css:164` — `--paper: oklch(17.5% 0.018 265)`
- `frontend/src/styles/tokens.css:165` — `--surface: oklch(21% 0.020 265)`
- `frontend/src/styles/tokens.css:166` — `--surface-sunken: oklch(14.5% 0.016 265)`
- `frontend/src/styles/tokens.css:167` — `--surface-raised: oklch(25% 0.022 265)`
- `frontend/src/styles/tokens.css:168` — `--surface-inverted: oklch(93% 0.008 85)`
- `frontend/src/styles/tokens.css:170` — `--ink: oklch(93% 0.010 85)`
- `frontend/src/styles/tokens.css:171` — `--ink-muted: oklch(74% 0.012 265)`
- `frontend/src/styles/tokens.css:172` — `--ink-faint: oklch(72% 0.012 265)`
- `frontend/src/styles/tokens.css:173` — `--ink-inverted: oklch(18% 0.018 265)`
- `frontend/src/styles/tokens.css:175` — `--rule: oklch(30% 0.018 265)`
- `frontend/src/styles/tokens.css:176` — `--rule-strong: oklch(40% 0.020 265)`
- `frontend/src/styles/tokens.css:178` — `--accent: oklch(76% 0.115 250)`
- `frontend/src/styles/tokens.css:179` — `--accent-hover: oklch(84% 0.110 250)`
- `frontend/src/styles/tokens.css:180` — `--accent-soft: oklch(28% 0.055 255)`
- `frontend/src/styles/tokens.css:181` — `--accent-border: oklch(45% 0.080 255)`
- `frontend/src/styles/tokens.css:183` — `--ok: oklch(78% 0.120 152)`
- `frontend/src/styles/tokens.css:184` — `--ok-soft: oklch(27% 0.050 152)`
- `frontend/src/styles/tokens.css:185` — `--ok-border: oklch(42% 0.070 152)`
- `frontend/src/styles/tokens.css:187` — `--info: oklch(78% 0.100 245)`
- `frontend/src/styles/tokens.css:188` — `--info-soft: oklch(27% 0.045 245)`
- `frontend/src/styles/tokens.css:189` — `--info-border: oklch(42% 0.065 245)`
- `frontend/src/styles/tokens.css:191` — `--warn: oklch(81% 0.115 78)`
- `frontend/src/styles/tokens.css:192` — `--warn-soft: oklch(29% 0.055 70)`
- `frontend/src/styles/tokens.css:193` — `--warn-border: oklch(45% 0.080 72)`
- `frontend/src/styles/tokens.css:195` — `--risk: oklch(74% 0.140 27)`
- `frontend/src/styles/tokens.css:196` — `--risk-soft: oklch(28% 0.060 27)`
- `frontend/src/styles/tokens.css:197` — `--risk-border: oklch(45% 0.090 27)`
- `frontend/src/styles/tokens.css:199` — `--unknown: oklch(70% 0.008 265)`
- `frontend/src/styles/tokens.css:200` — `--unknown-soft: oklch(26% 0.010 265)`
- `frontend/src/styles/tokens.css:201` — `--unknown-border: oklch(38% 0.010 265)`
- `frontend/src/styles/tokens.css:203` — `--demo: oklch(80% 0.105 320)`
- `frontend/src/styles/tokens.css:204` — `--demo-soft: oklch(28% 0.055 320)`
- `frontend/src/styles/tokens.css:205` — `--demo-border: oklch(45% 0.080 320)`

## spacing

- `frontend/src/styles/components.css:7` — `border: 1px`
- `frontend/src/styles/components.css:19` — `min-width: 52rem`
- `frontend/src/styles/components.css:31` — `letter-spacing: 0.07em`
- `frontend/src/styles/components.css:37` — `border-bottom: 1px`
- `frontend/src/styles/components.css:48` — `border-bottom: 1px`
- `frontend/src/styles/components.css:57` — `gap: 2px`
- `frontend/src/styles/components.css:57` — `max-width: 18rem`
- `frontend/src/styles/components.css:64` — `min-width: 64.25rem`
- `frontend/src/styles/components.css:66` — `min-width: 69.75rem`
- `frontend/src/styles/components.css:68` — `width: 11rem`
- `frontend/src/styles/components.css:69` — `width: 6rem`
- `frontend/src/styles/components.css:70` — `width: 6.75rem`
- `frontend/src/styles/components.css:71` — `width: 6.5rem`
- `frontend/src/styles/components.css:72` — `width: 7.5rem`
- `frontend/src/styles/components.css:73` — `width: 6.5rem`
- `frontend/src/styles/components.css:74` — `width: 4.5rem`
- `frontend/src/styles/components.css:75` — `width: 6rem`
- `frontend/src/styles/components.css:76` — `width: 6rem`
- `frontend/src/styles/components.css:77` — `width: 9rem`
- `frontend/src/styles/components.css:88` — `border-left: 1px`
- `frontend/src/styles/components.css:116` — `border: 1px`
- `frontend/src/styles/components.css:118` — `padding: 0.18rem`
- `frontend/src/styles/components.css:118` — `padding: 0.5rem`
- `frontend/src/styles/components.css:135` — `border-bottom: 2px`
- `frontend/src/styles/components.css:141` — `border-bottom: 1px`
- `frontend/src/styles/components.css:150` — `border-bottom: 2px`
- `frontend/src/styles/components.css:151` — `margin-bottom: -1px`
- `frontend/src/styles/components.css:164` — `border: 1px`
- `frontend/src/styles/components.css:165` — `border-left: 3px`
- `frontend/src/styles/components.css:186` — `border-left: 2px`
- `frontend/src/styles/components.css:196` — `grid-template-columns: 1.5rem`
- `frontend/src/styles/components.css:201` — `border: 1px`
- `frontend/src/styles/components.css:208` — `width: 0.7rem`
- `frontend/src/styles/components.css:224` — `height: 6px`
- `frontend/src/styles/components.css:224` — `border: 1px`
- `frontend/src/styles/components.css:235` — `grid-template-columns: 9rem`
- `frontend/src/styles/components.css:236` — `border: 1px`
- `frontend/src/styles/components.css:254` — `letter-spacing: 0.08em`
- `frontend/src/styles/components.css:267` — `padding: 0.42rem`
- `frontend/src/styles/components.css:267` — `padding: 0.6rem`
- `frontend/src/styles/components.css:268` — `border: 1px`
- `frontend/src/styles/components.css:289` — `border-left: 3px`
- `frontend/src/styles/components.css:303` — `grid-template-columns: 1.4rem`
- `frontend/src/styles/components.css:306` — `border: 1px`
- `frontend/src/styles/components.css:312` — `margin-top: 2px`
- `frontend/src/styles/components.css:313` — `width: 1rem`
- `frontend/src/styles/components.css:313` — `margin-top: 0.2rem`
- `frontend/src/styles/components.css:319` — `grid-template-columns: 6.5rem`
- `frontend/src/styles/components.css:322` — `border-bottom: 1px`
- `frontend/src/styles/components.css:334` — `background: 5px`
- `frontend/src/styles/components.css:334` — `background: 5px`
- `frontend/src/styles/components.css:334` — `background: 10px`
- `frontend/src/styles/components.css:338` — `gap: 5px`
- `frontend/src/styles/components.css:339` — `width: 10px`
- `frontend/src/styles/components.css:347` — `border: 1px`
- `frontend/src/styles/components.css:354` — `width: 1rem`
- `frontend/src/styles/components.css:355` — `border: 2px`
- `frontend/src/styles/components.css:364` — `min-width: 9.5rem`
- `frontend/src/styles/components.css:374` — `border: 1px`
- `frontend/src/styles/components.css:381` — `grid-template-columns: 7.5rem`
- `frontend/src/styles/components.css:388` — `border-bottom: 1px`
- `frontend/src/styles/components.css:397` — `letter-spacing: 0.05em`
- `frontend/src/styles/components.css:437` — `max-width: 46rem`
- `frontend/src/styles/components.css:443` — `padding-left: 2rem`
- `frontend/src/styles/components.css:449` — `padding-left: 2rem`
- `frontend/src/styles/components.css:453` — `gap: 1px`
- `frontend/src/styles/components.css:462` — `width: 2rem`
- `frontend/src/styles/components.css:465` — `border: 1px`
- `frontend/src/styles/components.css:470` — `letter-spacing: 0.02em`
- `frontend/src/styles/components.css:474` — `width: 3rem`
- `frontend/src/styles/components.css:486` — `margin: 2rem`
- `frontend/src/styles/components.css:488` — `border-left: 2px`
- `frontend/src/styles/components.css:491` — `padding-left: 2rem`
- `frontend/src/styles/components.css:499` — `border: 1px`
- `frontend/src/styles/components.css:524` — `grid-template-columns: 19rem`
- `frontend/src/styles/components.css:534` — `border: 1px`
- `frontend/src/styles/components.css:587` — `border-bottom: 1px`
- `frontend/src/styles/components.css:594` — `gap: 2px`
- `frontend/src/styles/components.css:606` — `min-width: 1.4rem`
- `frontend/src/styles/components.css:607` — `padding: 0.35rem`
- `frontend/src/styles/components.css:620` — `max-width: 34rem`
- `frontend/src/styles/components.css:622` — `border: 1px`
- `frontend/src/styles/global.css:29` — `width: 30rem`
- `frontend/src/styles/global.css:35` — `letter-spacing: -0.015em`
- `frontend/src/styles/global.css:48` — `text-underline-offset: 2px`
- `frontend/src/styles/global.css:54` — `outline: 2px`
- `frontend/src/styles/global.css:55` — `outline-offset: 2px`
- `frontend/src/styles/global.css:64` — `height: 1px`
- `frontend/src/styles/global.css:64` — `margin: -1px`
- `frontend/src/styles/global.css:77` — `border-right: 1px`
- `frontend/src/styles/global.css:89` — `gap: 2px`
- `frontend/src/styles/global.css:94` — `letter-spacing: -0.03em`
- `frontend/src/styles/global.css:104` — `gap: 1px`
- `frontend/src/styles/global.css:108` — `letter-spacing: 0.09em`
- `frontend/src/styles/global.css:129` — `transform: 1px`
- `frontend/src/styles/global.css:141` — `min-width: 1.1rem`
- `frontend/src/styles/global.css:147` — `padding: 1px`
- `frontend/src/styles/global.css:147` — `padding: 5px`
- `frontend/src/styles/global.css:151` — `border: 1px`
- `frontend/src/styles/global.css:161` — `border-bottom: 1px`
- `frontend/src/styles/global.css:163` — `backdrop-filter: 8px`
- `frontend/src/styles/global.css:176` — `letter-spacing: 0.12em`
- `frontend/src/styles/global.css:193` — `border: 1px`
- `frontend/src/styles/global.css:209` — `padding: 0.44rem`
- `frontend/src/styles/global.css:209` — `padding: 0.9rem`
- `frontend/src/styles/global.css:211` — `border: 1px`
- `frontend/src/styles/global.css:220` — `transform: 1px`
- `frontend/src/styles/global.css:231` — `padding: 0.25rem`
- `frontend/src/styles/global.css:231` — `padding: 0.6rem`
- `frontend/src/styles/global.css:238` — `gap: 0.3rem`
- `frontend/src/styles/global.css:239` — `padding: 0.1rem`
- `frontend/src/styles/global.css:239` — `padding: 0.45rem`
- `frontend/src/styles/global.css:243` — `letter-spacing: 0.02em`
- `frontend/src/styles/global.css:244` — `border: 1px`
- `frontend/src/styles/global.css:275` — `border: 1px`
- `frontend/src/styles/global.css:305` — `border-bottom: 1px`
- `frontend/src/styles/tokens.css:78` — `--space-1: 0.25rem`
- `frontend/src/styles/tokens.css:79` — `--space-2: 0.5rem`
- `frontend/src/styles/tokens.css:80` — `--space-3: 0.75rem`
- `frontend/src/styles/tokens.css:81` — `--space-4: 1rem`
- `frontend/src/styles/tokens.css:82` — `--space-5: 1.5rem`
- `frontend/src/styles/tokens.css:83` — `--space-6: 2rem`
- `frontend/src/styles/tokens.css:84` — `--space-7: 3rem`
- `frontend/src/styles/tokens.css:85` — `--space-8: 3rem`
- `frontend/src/styles/tokens.css:85` — `--space-8: 2rem`
- `frontend/src/styles/tokens.css:85` — `--space-8: 5.5rem`
- `frontend/src/styles/tokens.css:99` — `--sidebar-width: 15.5rem`

## font-size

- `frontend/src/styles/components.css:245` — `font-size: 1.9rem`
- `frontend/src/styles/global.css:92` — `font-size: 1.45rem`
- `frontend/src/styles/global.css:139` — `font-size: 0.7rem`
- `frontend/src/styles/global.css:146` — `font-size: 0.68rem`
- `frontend/src/styles/tokens.css:65` — `--text-xs: 0.75rem`
- `frontend/src/styles/tokens.css:66` — `--text-sm: 0.8125rem`
- `frontend/src/styles/tokens.css:67` — `--text-base: 0.9375rem`
- `frontend/src/styles/tokens.css:68` — `--text-md: 1.0625rem`
- `frontend/src/styles/tokens.css:69` — `--text-lg: clamp(1.25rem, 1.1rem + 0.5vw, 1.5rem)`
- `frontend/src/styles/tokens.css:70` — `--text-xl: clamp(1.6rem, 1.3rem + 1.2vw, 2.25rem)`
- `frontend/src/styles/tokens.css:71` — `--text-display: clamp(2.1rem, 1.4rem + 3vw, 3.5rem)`

## font-weight

- `frontend/src/styles/components.css:28` — `font-weight: 600`
- `frontend/src/styles/components.css:97` — `font-weight: 600`
- `frontend/src/styles/components.css:120` — `font-weight: 600`
- `frontend/src/styles/components.css:148` — `font-weight: 500`
- `frontend/src/styles/components.css:155` — `font-weight: 600`
- `frontend/src/styles/components.css:176` — `font-weight: 600`
- `frontend/src/styles/components.css:221` — `font-weight: 600`
- `frontend/src/styles/components.css:246` — `font-weight: 700`
- `frontend/src/styles/components.css:311` — `font-weight: 600`
- `frontend/src/styles/components.css:395` — `font-weight: 600`
- `frontend/src/styles/components.css:454` — `font-weight: 600`
- `frontend/src/styles/components.css:469` — `font-weight: 700`
- `frontend/src/styles/components.css:479` — `font-weight: 600`
- `frontend/src/styles/components.css:544` — `font-weight: 600`
- `frontend/src/styles/components.css:612` — `font-weight: 700`
- `frontend/src/styles/global.css:33` — `font-weight: 600`
- `frontend/src/styles/global.css:93` — `font-weight: 700`
- `frontend/src/styles/global.css:110` — `font-weight: 600`
- `frontend/src/styles/global.css:133` — `font-weight: 600`
- `frontend/src/styles/global.css:178` — `font-weight: 600`
- `frontend/src/styles/global.css:215` — `font-weight: 500`
- `frontend/src/styles/global.css:226` — `font-weight: 600`
- `frontend/src/styles/global.css:242` — `font-weight: 600`
- `frontend/src/styles/global.css:284` — `font-weight: 700`

## line-height

- `frontend/src/styles/components.css:180` — `line-height: 1.55`
- `frontend/src/styles/components.css:247` — `line-height: 1`
- `frontend/src/styles/components.css:445` — `line-height: 1.6`
- `frontend/src/styles/components.css:497` — `line-height: 1.55`
- `frontend/src/styles/components.css:557` — `line-height: 1.6`
- `frontend/src/styles/global.css:100` — `line-height: 1.3`

## border-radius

- `frontend/src/styles/components.css:208` — `border-radius: 50%`
- `frontend/src/styles/components.css:339` — `border-radius: 2px`
- `frontend/src/styles/components.css:357` — `border-radius: 50%`
- `frontend/src/styles/components.css:608` — `border-radius: 99px`
- `frontend/src/styles/global.css:148` — `border-radius: 99px`
- `frontend/src/styles/tokens.css:87` — `--radius-sm: 3px`
- `frontend/src/styles/tokens.css:88` — `--radius: 6px`
- `frontend/src/styles/tokens.css:89` — `--radius-lg: 10px`

## box-shadow

- `frontend/src/styles/components.css:279` — `box-shadow: 0 0 0 3px var(--accent-soft)`
- `frontend/src/styles/components.css:510` — `box-shadow: 0 0 0 3px var(--accent-soft)`
- `frontend/src/styles/global.css:134` — `box-shadow: inset 3px 0 0 var(--accent)`
- `frontend/src/styles/global.css:319` — `box-shadow: inset 0 -2px 0 var(--accent)`
- `frontend/src/styles/tokens.css:91` — `--shadow-sm: 0 1px 2px oklch(23% 0.018 265 / 0.06)`
- `frontend/src/styles/tokens.css:92` — `--shadow: 0 2px 6px oklch(23% 0.018 265 / 0.08), 0 1px 2px oklch(23% 0.018 265 / 0.05)`
- `frontend/src/styles/tokens.css:93` — `--shadow-lg: 0 12px 32px oklch(23% 0.018 265 / 0.13), 0 2px 8px oklch(23% 0.018 265 / 0.07)`
- `frontend/src/styles/tokens.css:155` — `--shadow-sm: 0 1px 2px oklch(0% 0 0 / 0.30)`
- `frontend/src/styles/tokens.css:156` — `--shadow: 0 2px 8px oklch(0% 0 0 / 0.38), 0 1px 2px oklch(0% 0 0 / 0.25)`
- `frontend/src/styles/tokens.css:157` — `--shadow-lg: 0 14px 38px oklch(0% 0 0 / 0.48), 0 2px 8px oklch(0% 0 0 / 0.30)`
- `frontend/src/styles/tokens.css:207` — `--shadow-sm: 0 1px 2px oklch(0% 0 0 / 0.30)`
- `frontend/src/styles/tokens.css:208` — `--shadow: 0 2px 8px oklch(0% 0 0 / 0.38), 0 1px 2px oklch(0% 0 0 / 0.25)`
- `frontend/src/styles/tokens.css:209` — `--shadow-lg: 0 14px 38px oklch(0% 0 0 / 0.48), 0 2px 8px oklch(0% 0 0 / 0.30)`

## z-index

- `frontend/src/styles/components.css:25` — `z-index: 2`
- `frontend/src/styles/components.css:89` — `z-index: 1`
- `frontend/src/styles/components.css:91` — `z-index: 3`
- `frontend/src/styles/components.css:419` — `z-index: 50`
- `frontend/src/styles/global.css:166` — `z-index: 20`

## motion

- `frontend/src/styles/components.css:215` — `animation: 1.4s`
- `frontend/src/styles/components.css:358` — `animation: 0.8s`
- `frontend/src/styles/global.css:290` — `animation-duration: 0.01ms`
- `frontend/src/styles/global.css:292` — `transition-duration: 0.01ms`
- `frontend/src/styles/tokens.css:95` — `--duration-fast: 120ms`
- `frontend/src/styles/tokens.css:96` — `--duration-normal: 220ms`

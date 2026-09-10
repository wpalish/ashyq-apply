# ASHYQ Apply design context

This project uses a calm editorial system for evidence-backed admissions decisions. The visual idea is **Open Chapter**: warm paper, open negative space, a visible route, and real-world photography. The product must feel human and globally ambitious without resembling a university crest or a generic SaaS dashboard.

## Source order

1. `../../ashyq_brand/ashyq_brandbook_v1-1.md` for brand identity. Version 1.1 supersedes the lime-based v1.0 direction.
2. `../epics.md` sections 3, E00, E16, and 7 for product behavior, trust, accessibility, and component inventory.
3. `src/styles/tokens.css` for implementation values and semantic aliases.
4. `../specs/design-system.md` for the reconciliation and usage rules.
5. `src/design-system/DesignSystem.tsx` for the living visual catalogue.

## Visual decisions

- Exact brand primitives: Ink `#111827`, Paper `#F7F3EA`, Academic Blue `#526DA6`, Library Burgundy `#8E3F4C`, Scholar Teal `#437A78`, Parchment Gold `#C5A66B`, Deadline Coral `#E47A6A`.
- Owner-confirmed typography (2026-09-09, overrides brandbook): Prata 400 for display headings; Onest for brand/actions/UI/body; IBM Plex Mono for evidence, sums, dates, scores, identifiers and freshness.
- Product radius scale is 4 / 8 / 12 px. The 24 px radius is reserved for large editorial page/image containers.
- Product motion stays at or below 200 ms and has a reduced-motion path. Continuous spinner cycles are the only longer repeating motion.
- Light and dark themes preserve the same meanings. Exact accent swatches are not used for small text when they miss 4.5:1; accessible semantic derivatives are used instead.

## Trust contract

- **Fact:** mono value + `EvidenceLink` + `FreshnessBadge`.
- **Assessment:** descriptive fit label + named axes + the permanent disclaimer. Never a probability.
- **AI opinion:** `AIGeneratedLabel` + quote-like form + distinct surface.
- **Unknown:** explicit sentence + reason + action. Never a dash, blank, or zero.
- **Mode:** Demo or Live is global and visible on every screen.

Every semantic state combines color, icon, and text. Every material value has a source within one action. Mobile starts at 360 px; desktop tables become card lists rather than compressed tables.

## Avoid

Lime, neon, decorative gradients, glass, 3D, shields, laurels, globes, literal books/doors, fake acceptance material, stock-smile photography, more than three chips per row, guarantee language, and any visual or verbal admission probability.

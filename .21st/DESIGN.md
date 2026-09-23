# ashyq apply design context

Proposal pending owner review, 2026-09-23. The working UI retains PR #10's navigation and profile UX. Its evidence contract is defined by the product README and `epics.md`.

## Visual system

- React/Vite with three token layers in `frontend/src/styles/tokens.css`: brand and UI primitives (`--ds-*`), semantic aliases, then component CSS. Brandbook colors remain in `--ds-color-brand-*`; the working surfaces use softer neutrals.
- Light: canvas `#F4F5F3`, text `#243044`, action `#3C5985`. Dark: canvas `#202B35`, text `#E9EEF0`, action `#B0C7EB`.
- Onest is the heading, body, and user-facing data font. Data uses tabular numerals. IBM Plex Mono is for technical identifiers and code. Prata is removed from the working UI.
- Use 4px spacing steps, at least 44px targets, clear focus, reduced motion, and responsive layouts. Keep source and date attached to material facts; label uncertainty in words.

## Reference decisions

- [21st.dev Configuration Stepper](https://21st.dev/@shadcnspace/components/stepper-02): short, named tasks for profile entry; no ready-made SaaS styling.
- [21st.dev Feature Comparison Table](https://21st.dev/@7ovr/components/comparison-3): aligned rows for desktop comparison; no promotional ranking badge.
- [Mobbin Headspace onboarding](https://mobbin.com/explore/flows/7cdc08c0-3bcb-4882-90dd-5cf92019616f): calm pacing and one clear next step; no illustrations or promises about outcomes.

The source references and token decisions here are the project-local context for future 21st searches and UI work.

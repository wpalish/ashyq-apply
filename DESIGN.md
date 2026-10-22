---
name: Unimatch
visual-authority: owner22October2026, Apple website base with selected Eleken inspiration
colors:
  primary: "#0951FF"
  primary-text: "#1349D3"
  paper: "#F5F6F8"
  surface: "#FFFFFF"
  ink: "#172138"
  muted: "#5C6577"
  rule: "#E0E4EB"
---

# Unimatch — Apple foundation, evidence-first product

## Current authority

On22October2026 the owner explicitly requested the Apple website as the base and the Eleken website-design collection as inspiration. This replaces strict book-only visual fidelity for this increment. The18October UI book remains historical context for the connected product and its navigation; the old yellow robot and earlier unrelated Apple/V2 concept are not the new target. The new implementation is an original Unimatch design derived from the references below.

- Apple: clear hierarchy, short product chapters, large visual focus, restrained materials and two levels of navigation.
- Adidas Arena via Eleken: oversized type and a few layered hero elements, adapted to the existing orbit/globe identity.
- Pitch: explain a product through its own journey. The public four-step tour is a labelled guide, not fabricated applicant or research data.
- UNITED24 via Eleken: source transparency and visible uncertainty. No decorative achievement metrics or admissions probability.
- Stripe Press: a strong relationship between an object and its detail, interpreted through the existing programme identity and return navigation.

Source links and observed/proposed boundaries: docs/design/apple-editorial-2026-10-22/RESEARCH.md.

## Roles and typography

- Marketing: Persuade. Spacious opening, one primary action to the editable search, interactive product guide, evidence explanation, a dark route chapter, readable FAQ and sign-up.
- Workspace: Operate. Stable form/command layout; stronger grouping, calm neutral surfaces and less decoration around requirements and financial data.
- Native Apple system font on Apple devices; existing self-hosted Inter is the cross-platform fallback. No redistributed SF webfont. Optical sizing enabled. Existing mono remains reserved for IDs/actual data.
- Display36–78px, tracking−.03 to−.035em, leading1.065–1.1. Workspace section titles remain compact and font weight650–700. Body15–20px, leading1.5–1.6. Small dense research metadata raised to12px.
- Brand remains orbit wordmark/cobalt. Blue is for action/selection; evidence colours retain semantic meaning.

## Surfaces and layout

- Full-width public site with1200px content measure and20–32px gutters. Desktop public header68px, compact64px. No framed screenshot-like outer chrome.
- White and neutral gray distinguish chapters. One fixed navy content chapter is deliberately dark; it does not override user theme or evidence colours.
- Workspace is at most1440px, horizontal desktop navigation and existing labelled mobile bottom navigation. No form/provider identity changes.
- Cards/panels use12–16px radii. Pills are controls. No nested glass content. Only the public sticky navigation has12px backdrop blur with solid, reduced-transparency and high-contrast fallbacks.
- Desktop product tour has a rail and one stable presentation surface. Mobile uses four native buttons in a2×2grid above the surface.
- Narrow layouts stack search, story and evidence. Interactive mobile search topics and primary actions have44px+targets. No horizontal story scroller or drag-only navigation.

## Motion

Keep one motion language from frontend/src/styles/motion.css. Composite-only CSS/WAAPI, finite entrances and interruptible feedback. Keyboard actions are immediate; reduced motion disables displacement. Tab surfaces do not rekey forms or stores; animations never send commands or imply an ACK. Exact16interaction matrix in docs/design/ui-book/fidelity/motion-contract.md.

## Product truth and integration

Preserve source scopes, degree/intake, unknowns, sample/demo labels, currency and period. No admission probabilities, scholarship guarantees, fake completed documents, fake uploads/payments, invented achievements or current-coverage claims.

The public tour and hero layers explain concepts. The form keeps the existing tab-scoped search-intent contract; availability of storage is conditional, and applying preferences to a personal profile is explicit. Preparation remains optional.

StoreProvider, immutable original commands, dirty draft,409and uncertain accepted outcome retain their existing lifecycle. No new backend/API/schema/provider/evaluation changes belong to this design increment.

## Verification

Current evidence and limitations live in docs/design/apple-editorial-2026-10-22/REVIEW.md. Previous80book viewport comparisons qualify their original snapshot only. This change does not inherit those as new visual evidence. Production remains the separately recorded19October deployment until an explicitly authorised future deployment.

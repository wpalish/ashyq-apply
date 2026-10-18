---
name: Unimatch
visual-authority: original UNIMATCH_UI_BOOK.pdf, owner18October2026
colors:
  primary: "#0951FF"
  primary-text: "#1349D3"
  primary-soft: "#EAF0FF"
  paper: "#F6F8FC"
  surface: "#FFFFFF"
  ink: "#0A153D"
  muted: "#536D99"
  rule: "#E2EAF5"
---

# Unimatch — original book implementation

The owner's original41page PDF (cover plus40contexts), SHA3339016d022229212739ea7f7444216fe838e27c7403e5581b09e401d3ad9145, is the visual authority. The earlier18October implementation was rejected and its visual acceptance is superseded. Do not use the Apple/V2 concept or the old yellow mascot direction.

## Layout and typography

- Cool porcelain paper, white panels, navy Inter, cobalt primary actions, circular orbit mark and airy dotted globe. No alternative identity.
- Desktop window max1392px with24px side gutters and28px outer margin at1440×1024. Horizontal navigation and72px header. Route content generally28–32px padding; dense source/result rows and profile rail follow the book.
- At900px and below: compact header and five labelled bottom destinations with safe-area padding. At640px:20px route padding, stacked forms, source cards and two-programme comparison fitting the viewport. Three-programme comparison scrolls in a labelled local region.
- Inter400/500/600/700/800 is self-hosted with Latin/Cyrillic/extended coverage. Caveat400 is confined to short handwritten annotations; JetBrains Mono is retained for actual IDs/data. No display serif.
- Route headings roughly42–54px desktop and29–36px mobile, body14–17px, dense metadata11–13px. Tracking-0.035em, clear focus and spacing. Native date inputs retain their semantics; editable mobile text fields use16px.
- Panels12–16px radius, native fields9–11px, source primary actions are pill-shaped. Fine tonal borders; broad menu shadows only. Phosphor icons are consistent with the source.

## Component inventory

BookUI: orbit/wordmark, static globe, intake, help, footer, workflow and profile progress. BookAuthShell:02–05stable forms. BookAcademics/Activities/Preferences preserve existing editing. BookProgramme/Comparison/Funding/Sources present owned result evidence. Plan/Today/Calendar/Documents/Applications present personal actions and exact internal targets. BookPracticeView/SavedReview preserve immutable attempts. Export/Share/Settings/Billing reuse original controllers. Community/Legal/Recovery retain original permissions and recovery semantics. Full40route/component/API matrix:docs/design/ui-book/fidelity/inventory.json.

## Truth and state

The book is illustrative, not university, price, legal or API truth. Preserve actual source scopes, unknowns, demo labels, costs/currencies and personal versus institutional state. DOB/gender examples are explicitly read-only because the current API does not persist them. No admissions probabilities, fake file uploads, payments, complete courses or university decisions. Registration keeps the required workspace field even though the source omits it.

StoreProvider and forms remain mounted and unkeyed by route/animation. ACK, current dirty draft, immutable original operation,409and unknown accepted outcome are distinct. Adoption applies a comparison to the draft; saving remains explicit. Public cards exclude applicant identity by default and cancel stale rendering when disclosure/case changes.

## Motion and performance

Motion14.3.0 with LazyMotion/domAnimation and reducedMotion=user. Programme tab content alone uses180ms opacity/y4; useReducedMotion removes displacement and duration. Buttons use120ms colour feedback. Focus is immediate. No route transition controls persistence or research timing. The globe is an illustrative raster with zero canvas/WebGL/RAF loop, so hidden/offscreen/unmount has no ongoing globe renderer to stop. PDF.js uses a finite local lazy worker and explicit cleanup.

Current bundle: public478.84KB/140.87KB gzip; private188.04KB/53.35KB gzip; preparation125.44KB/34.95KB gzip; lazy PDF486.27KB/146.10KB gzip. CPU/GPUtrace,OSreducedmotion and screenreader are not native-qualified through the available tool. See motion-contract.md for exact scope.

## Accessibility and language

Labelled navigation, source regions, native form labels, immediate visible focus, Escape/focus restoration for menus, and semantic status colours with words. Profile source actions form a compact two-button mobile group; Back/save feedback are outside it and fields scroll clear of it. Mobile rules contents collapse. Native76axe snapshots have0violations; manual focus/contrast checks complement them. This is not a WCAGconformance claim.

The selected book is Russian. Kazakh has partial RU/ENfallback, and English retains existing analytical presentations. Switching all three locales at360px was checked without horizontal clipping. Do not describe this as a complete three-language translation.

## Verification and handoff

Current local review:docs/design/ui-book/fidelity/REPORT.html,80native viewport baselines and their source pairs. Source images are losslessWebP equivalents of the exact PNGcrops, not regenerated UI screenshots. No numerical pixel-perfect claim. Separate API/corpus deviations and tool-unavailable checks from visual defects. Frontend999tests pass; backend unchanged with its documented inherited golden failure. No main merge, production deployment, hosted workflow or external message belongs to this UI handoff.

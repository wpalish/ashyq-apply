---
name: Unimatch
description: Evidence and next steps for international admissions
colors:
  primary: "#1454FF"
  primary-hover: "#0C42D4"
  primary-text: "#1249D7"
  primary-soft: "#EAF0FF"
  paper: "#F5F9FF"
  surface: "#FFFFFF"
  sunken: "#EDF3FC"
  ink: "#0B1739"
  muted: "#526582"
  rule: "#E2EAF5"
typography:
  display:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "clamp(38px, 4.5vw, 62px)"
    fontWeight: 700
    lineHeight: 1.03
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "clamp(30px, 3.5vw, 46px)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.035em"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "16px"
    lineHeight: 1.6
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.35
rounded:
  field: "8px"
  panel: "12px"
spacing:
  small: "8px"
  medium: "16px"
  panel: "24px"
  section: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.field}"
    padding: "10px 17px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "24px"
---

# Design System: Unimatch

## Overview

**Creative North Star: "A clear route to study"**

The owner-selected UNIMATCH_UI_BOOK.pdf establishes cool blue paper, precise navy type, blue actions and a cartographic globe. The interface connects programme selection, evidence and practical admissions work. The book's illustrative admissions figures are replaced by actual API records, visible unknowns and labelled synthetic fixtures.

**Key Characteristics:**

- Cool, legible surfaces and a restrained cartographic signature.
- Horizontal desktop navigation and five-item mobile bottom navigation.
- Evidence status, saving and private versus public data remain distinguishable.

The implementation is an adaptation of the book to the existing product. It is not a pixel reproduction or an approval of legal, pricing or admissions examples.

## Colors

Royal blue carries actions; navy carries reading. Cool white separates panels from the page. The source of truth is `frontend/src/styles/tokens.css`, with the final visual layer in `book.css`.

### Primary

- **Royal Blue** (`#1454FF`): primary buttons, selected navigation, focus and globe connections.
- **Blue Text** (`#1249D7`): links and selected text on light surfaces.
- **Blue Wash** (`#EAF0FF`): selected control surfaces.

### Neutral

- **Cool Paper** (`#F5F9FF`), **White Panel** (`#FFFFFF`), **Sunken Blue** (`#EDF3FC`).
- **Navy Ink** (`#0B1739`), **Muted Ink** (`#526582`), **Fine Rule** (`#E2EAF5`).

**The Evidence Colour Rule.** Keep the existing semantic OKLCH status families for met, missing, unknown, stale and synthetic records. A blue brand accent never changes a fact's status. Dark mode uses the existing semantic palette and `#A3BEFF` link text.

## Typography

**Display and Body Font:** Inter 400/500/600/700, self-hosted. JetBrains Mono remains for actual identifiers, source excerpts and numeric evidence where inherited; it is not the display face.

Headlines use the frontmatter scale. Body copy is 16px with 1.6 line height; explanatory text is usually 13–14px. Section titles are 18px. The mobile screen title becomes 31px below640px. Reading copy normally stays within68–70ch. Tracking never goes beyond-0.04em.

## Layout

Main screen container:1248px including24px side padding, so usable desktop content is1200px. Desktop navigation is78px high. At900px and below, navigation moves to the bottom and a68px topbar remains. Below640px, content padding is16px and forms stack. Safe-area padding protects bottom controls.

The spacing rhythm uses4/8/12/16/24/32/48px. Profile steps scroll locally on narrow screens. True tables and dense calendars may scroll inside labelled regions; the document itself must not overflow horizontally. Paired captured widths are1440 and390px, with additional320/768px samples.

## Elevation & Depth

Most panels use a fine border and tonal separation. Menus alone use the large diffuse shadow from`--shadow-lg`. Avoid adding another elevation layer to ordinary evidence records. Nested source sections use the sunken surface without another shadow.

## Shapes

Panels use12px corners, fields and buttons8px. Pills are limited to compact tags and filters. The circular orbit mark and raster globe are the signature geometry; functional cards stay rectangular. Icons use the existing Phosphor library, not Unicode substitutes.

## Components

### Buttons

Primary controls are at least44px high, blue with white text. Hover uses the darker blue. Press shifts1px; focus is a3px visible ring with3px offset. Compact secondary controls may be36px high. Disabled controls retain readable labels and never imply a completed action.

### Inputs

Native inputs keep their labels, editing semantics and browser date pickers. Caret and selection use the accent palette. Local draft, acknowledged save, conflict and unknown outcome are different states.

### Panels and evidence

White panel, fine rule,24px padding. Evidence uses explicit status chips plus text and source links. Thick decorative side borders were removed during final review. Long raw research notes are available through disclosure rather than preceding the entire evidence workflow.

### Navigation

Desktop: inline labels with a blue active underline. Mobile: five labelled icon destinations and safe-area spacing. Explore holds secondary destinations; the account menu keeps case switching, new case, settings and sign out available on small screens.

### Motion

A600ms globe arrival on the public landing page uses`--ease-out-expo`. Ordinary button feedback is160ms. No repeated page entrance, fake research progress or compulsory parallax. Reduced-motion disables authored entrance and press transforms. This is verified in CSS; an OS-level reduced-motion browser session was not captured.

### Assets

`frontend/public/brand/unimatch-orbit.svg` is geometric. `unimatch-globe.webp` is an AI-generated raster illustration,265KB, replacing the old robot in this selected direction. It does not claim real university coverage or destinations.

## Do's and Don'ts

### Do:

- Do retain visible unknowns, source limitations and synthetic labels.
- Do keep private case content out of public previews and default exports.
- Do preserve keyboard focus and native form semantics.
- Do let content reflow without document-level horizontal scrolling.

### Don't:

- Don't turn a saved selection into an admission probability or completed application.
- Don't publish example prices, legal approval or complete-course claims from the mockups.
- Don't animate a research state independently of server progress.
- Don't substitute a new visual concept for the selected blue book without owner direction.

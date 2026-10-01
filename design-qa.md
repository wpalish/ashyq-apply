# Unimatch visual QA — 2026-10-02

final result: passed

This is a visual and local interaction gate for the Find and Community views inspected here; public live search and deployment require separate acceptance.

## Evidence and normalization

- Source visual truth: user supplied `Изображение ChatGPT 2 окт. 2026 г., 01_00_14.png` (Find) and `Изображение ChatGPT 2 окт. 2026 г., 01_01_50.png` (Community), each 1448 × 1086 px.
- Browser rendered implementation: isolated local Vite/FastAPI demo at `http://127.0.0.1:5173/`, captured at 1448 CSS px width, 1086 CSS px viewport height and device pixel ratio 1. The first 1086 px of each full-page capture are preserved in [Find comparison](docs/design/qa/find-comparison.jpg) and [Community comparison](docs/design/qa/community-comparison.jpg). The paired reference and implementation crops were placed into the same image before review; each half was scaled from 1448 × 1086 to 900 × 675 for the saved contact sheet.
- The Find reference contains illustrative universities, prices, scores and deadlines. The implementation uses the actual isolated synthetic research response and visibly labels the `fixture://` data. The Community reference is populated; the local capture contains one explicitly synthetic QA post created in the throwaway local database. Counts and user photos were not copied from the mockups.
- [Mobile Find capture](docs/design/qa/find-mobile.jpg): 390 × 844 CSS px, device pixel ratio 1. `scrollWidth` equaled 390 px. Settings, Billing and student discovery were also inspected at 390 px without horizontal overflow.
- Focused checks: Find hero, first result controls, Community compose/empty and post states, mobile search placement, dark theme selected navigation, and the generated mascot crop. Browser console errors: zero in the checked local tab.

## Findings and comparison history

- **P2 — Community unused desktop space, resolved.** The first local empty feed occupied a narrow column while the reference uses a second editorial region. Added a real generated mascot panel with a working **Find students** action. The populated local QA post and resulting desktop layout are visible in the Community comparison.
- **P2 — Mobile search below the first viewport, resolved.** The first Find hero kept too much illustration height. Reduced mobile title, copy and image height. The search field and filter controls are visible in the 390 × 844 capture without overflow.
- **P3 — Institution photos and numerical match rings differ by design.** The reference uses illustrative campus imagery and scores. The product has no verified media for each programme and must not imply that a generated scene is its real campus. The implementation gives each result clear status, funding, deadline and evidence, with the original detailed evidence table still reachable.
- **P3 — Mixed localization in the synthetic QA state, resolved.** The app documents partial Russian and Kazakh translations and falls back to English. English was selected for the reference comparison. `when()` now uses that selected locale for relative and exact post times; the browser and a focused regression confirmed English and Russian.
- **P2 — Responsive detailed evidence, resolved after cloud E2E.** The 320 px top bar and its Explore menu stayed within the viewport after a compact grid correction. The disclosed evidence table is constrained to the Find container at 768 px; at phone widths the same data becomes cards. The browser test checks 320, 768, 1024 and 1440 px without page overflow.
- **P2 — Text contrast, resolved after axe audit.** Yellow remains the action/background accent. Text uses a darker gold on light surfaces and yellow on dark surfaces; completed research rows retain full opacity. The desktop axe pass found no serious or critical violations across the reachable workflow screens.

## Required fidelity surfaces

- **Typography:** Inter-based UI, navy display type and hierarchy match the reference's direction. The local page uses fewer decorative handwritten phrases to keep product claims readable.
- **Spacing/layout:** Five-area navigation, a two-column Community region, cards, tabs and side illustration follow the reference hierarchy. The mobile search field remains above the bottom navigation.
- **Colors/tokens:** Light white/ivory canvas, navy ink and warm yellow accent are coherent. Dark mode was checked after paint settled; selected navigation text and backgrounds remain legible.
- **Imagery:** The generated Unimatch mascot scene is sharp and placed in Find and Community. The icon and scene share the same palette. Institution imagery is omitted where no verified media exists.
- **Copy/content:** Actual API data replaces mockup numbers; synthetic data is explicitly labeled. University evidence, unknowns and conflicts remain available without suggesting an admission probability.

## Interactions and limitations

Local browser verified profile → synthetic research → Find query → save → compare → detail → Plan → document collection. It also verified Community profile creation, a synthetic test post and **Find students** navigation. The post and profile exist only in the isolated `/tmp` QA database. Public provider capacity, live official-page results and production release are outside this visual pass.

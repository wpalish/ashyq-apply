# Apple-led design increment — 22 October 2026

Status: IMPLEMENTED LOCALLY / OWNER REVIEW PENDING / NOT DEPLOYED.

The explicit owner direction changes the visual authority to Apple, with selected Eleken inspiration. [Reference evidence](RESEARCH.md) distinguishes directly observed presentation from interpretation. The source increment starts at `57fff2df`; the final logo-return polish follows it. This is an integrated frontend change on `task/unimatch-ui-book`, carried by [PR89](https://github.com/wpalish/ashyq-apply/pull/89).

## What changed

- A centred public opening, original globe composition, two action levels and compact sticky navigation.
- Editable search preserves the existing public-intent contract and leads to account creation. Applying preferences to a personal case remains explicit.
- A four-step interactive product guide: profile, programmes, sources and personal plan. It is clearly an explanation, never fabricated research.
- Asymmetric evidence chapter, dark plan chapter, factual FAQ and a final registration action. Preparation remains optional; there is no admissions guarantee.
- Shared native-system typography, neutral surfaces, quieter panels and larger dense research labels. Removed decorative globe overlap from the search action area.
- Existing bounded motion is reused; no new dependency, global animation loop or provider/API command. Stable forms and command stores remain intact.
- Native review repairs: accessible tour region/live announcement; conditional tab-storage wording; one clear grouped field-focus ring; logo returns to the top even when already on the welcome route.

## Verification

| Gate | Current outcome |
| --- | --- |
| Full frontend | **113 files / 1057 tests passed**, final source including logo-return polish |
| TypeScript and production build | PASS; `tsc -b` in build. Existing large-chunk warning remains, including the catalogue chunk (~601kB). |
| ESLint | 0 errors / 9 inherited warnings; full raw log alongside this review |
| Mechanical design detector | Run once on new/changed UI targets; returned `[]`. Logo scroll handler was added afterwards; no visual token/layout change. This is not accessibility or visual acceptance. |
| Read-only source review | No confirmed P1/P2 in the scoped components; two small accessibility/copy suggestions addressed. Root remained sole code writer. |
| Browser | Manual native IAB review at 1280×720 and 390×844, using owned synthetic local state. No external submissions or new account creation. |

Raw [tests](logs/frontend-tests.log), [build](logs/build.log), [lint](logs/lint.log), [detector](logs/mechanical-detector.json). Source and proof hashes are finite in the adjacent manifests.

## Native coverage

| Surface/action | Observed result | Proof |
| --- | --- | --- |
| Public RU desktop | Hierarchy, globe layers, navigation, entire story | [First viewport](screenshots/landing-desktop.jpg), [full page](screenshots/landing-full-desktop.jpg) |
| Public RU mobile | 390px layout, readable actions; scroll width equals viewport | [Mobile](screenshots/landing-mobile.jpg) |
| Mobile search | CTA focuses the real subject field; stacked inputs and grouped focus, no horizontal overflow | [Search](screenshots/search-mobile.jpg) |
| Search → registration | Engineering / Germany / USD20000 submitted locally; account-creation form appeared. No account submitted. Exact intent preservation separately covered by tests. | Manual observation; no saved registration image |
| Tour fast reversals | Programmes → Plan → Sources; one selected button/region, focus remains on control, live status matches | [Desktop](screenshots/product-tour-desktop.jpg) |
| Mobile tour | Four buttons in 2×2 rail, readable plan detail | [Mobile](screenshots/product-tour-mobile.jpg) |
| Public anchors/FAQ | How-it-works and evidence hashes retained public content. No-guarantee answer opened. | Full-page image above |
| English mobile | Hero and translated tour readable, no horizontal overflow | [English](screenshots/landing-mobile-en.jpg) |
| Logo return | Same welcome URL returned scroll position to0 | Native DOM readback |
| Synthetic workspace | Home, Find, programme detail/tabs, Documents, Profile observed; no applicant field edits/saves | [Home](screenshots/workspace-desktop.jpg), [Find](screenshots/find-desktop.jpg), [programme](screenshots/programme-desktop.jpg), [documents](screenshots/documents-desktop.jpg), [profile](screenshots/profile-desktop.jpg) |
| Mobile profile | 390px layout with fields and bottom navigation, no horizontal overflow | [Profile mobile](screenshots/profile-mobile.jpg) |
| Workspace menu | Escape closed it and returned focus to its summary | Manual native observation |
| Local sign-out | First403 was an omitted explicit dev origin for18140. Runtime was restarted with exact loopback18140 origins; second attempt completed and sign-in appeared. Auth remained enabled. | Browser console and local API observed; no protection code change |

Temporary viewport override was reset; the public RU desktop preview remains open. The old unrelated data-URL service-error tab was not operated. Native captures qualify only these surfaces and synthetic state; the previous40-screen book review is not inherited as current evidence.

## Limits

This is a design increment, not full product or search-quality acceptance. No production deployment, backend/schema change, real provider run, external application, real applicant save, payment, new account, benchmark/gold edit or held-out evaluation. Dark mode, Kazakh copy, OS reduced-motion/transparency settings, physical touch/keyboard devices, frame-rate profiling and a complete new40-screen visual matrix were not freshly exercised. Existing automated motion tests cover reduced-motion/focus/lifecycle behaviour, without establishing real-device animation performance. Build-size and inherited lint warnings remain explicit.

Apple supplies the hierarchy and restraint; Eleken contributes selected composition and product-story ideas. Original Unimatch identity and evidence meanings remain. No Apple assets, SF webfont or competitor content were copied.

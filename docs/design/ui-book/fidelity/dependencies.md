# Dependency decision,18October2026

Existing React18.3/Vite6/TypeScript/CSS architecture is retained. Add exactly motion14.3.0 (MIT): npm metadata confirms React/ReactDOM^18 or^19 peers. Use MotionConfig reducedMotion=user for local state feedback; no identity/layout boundary around StoreProvider/forms. No React19/Next APIs.

No COBE dependency in the static fidelity slice: the reference's dotted globe is an illustration. A generated transparent raster plate matches the source; imposing a generic WebGL globe first would change its artwork. No new continuous rendering loop is needed for this slice. Reassess only if rotation can preserve the selected image and passes hidden/reduced/offscreen cleanup gates.

No Radix or Storybook needed until an actual current control gap is observed. Existing native details/forms/icons/test tools retained. No bulk update.

Official motion references:https://motion.dev/docs/react-motion-config and https://motion.dev/docs/react-use-reduced-motion. Exact dependency diff and bundle measurements follow verification.

Add @fontsource/caveat5.3.0 (OFL-1.1), metadata verified18Oct. It reproduces the book's small handwritten annotation; Inter remains the reading and display face. Official university favicons, fetched from public root URLs, are local assets; no invented institution marks.

## Local PDF preview decision · 2026-10-18

Observed native proof21-document-desktop-pass1 shows an empty sandboxed PDF iframe in IAB. Replace it with lazy client-side PDF.js, using only selected local bytes, without a backend upload or external document URL.

Before install, official npm registry reported pdfjs-dist6.4.299, Apache-2.0, Node>=22.13.0||>=24, integrity sha512-AVl138zALtfaAPvADulE0PZThbYzCBS79nL4pOSL/6Sm/4AH5A21BD9VHt97OlCuzJuCpmeZtAtkinisF4Vb1g==. Local Node24.15.0 satisfies it; existing CI Node22 setup uses current22. No framework migration. Pin exact. Worker and rendering module remain lazy, selected file capped at10MB; canvas bounded, no PDF scripting/form actions. Error fallback keeps the original local-open link. Record actual chunks after build.

Sources: https://mozilla.github.io/pdf.js/getting_started/ and https://mozilla.github.io/pdf.js/api/draft/api.js.html; official registry metadata via npm view.

Installed exact pdfjs-dist6.4.299; npm audit reported0 vulnerabilities at install (291packages). Native IAB canvas/text/125%zoom succeeded on synthetic-transcript.pdf. Build: lazy reader487.48KB, worker1264.34KB; no reader in entry457.03KB. Private chunk554.50KB has a size warning; optimisation remains open. Main user data bytes are passed to a local worker, never to an external URL/API.

## Route splitting checkpoint ·20:59UTC

No new packages after PDF.js. Existing React.lazy/Suspense now splits private pages at route boundaries while StoreProvider remains stable. Private chunk567.72KB→190.03KB (53.92KB gzip), entry470.94KB/138.96KB gzip, PDF486.27KB/146.10KB gzip, preparation121.10KB/33.95KB gzip. Build no longer warns about >500KB route chunks. Interaction tests now await actual lazy screen readiness before exercising unchanged case/export/collection behavior; no assertion was removed. Native route and ownership verification remains in progress.

## Browser accessibility control ·19October local

Use the already installed axe-core4.13.0 (from @axe-core/playwright4.13.0) directly as an exact dev dependency, MPL-2.0, Node>=4. An opt-in loopback-only Vite dev control is justified by40 real rendered screens and CUA's read-only evaluate boundary. The button runs the existing library on the current DOM; it does not inject browser scripts via automation, send data, or call application APIs. Exclude only the development tool itself, never app regions. Route/unmount checks fence stale output. Production import is compiled out. No new library version or runtime package.

## Final exact diff and production scan ·19October

Relative toc2565ad6: direct runtime additions@fontsource/caveat5.3.0(OFL-1.1),motion14.3.0(MIT),pdfjs-dist6.4.299(Apache-2.0); direct dev pinaxe-core4.13.0(MPL-2.0), already transitively present. React18/Vite6/TSarchitecture and existing fonts/icons are retained. NoReact19,Next,GSAP,COBE,Storybook,Radixornewhostingdependency. Package-lock records356added lines, no bulk refresh. RUGandKU are clearly local word tiles/fallbacks, not newly claimed official university logos; Tokyo's available icon is a local file.

Current build: public478.84KB/140.87KB gzip; private188.04KB/53.35KB gzip; prep125.44KB/34.95KB gzip; lazyPDF486.27KB/146.10KB gzip. No>500KBroute warning. Opt-in local axe and labelled moderation fixture strings/chunks are absent from production executable JS. GPU/CPUtrace and constrained-device profiling are NOT_RUN; bundle size alone is not performance acceptance. Exact four-package diff is in Git and package-lock.

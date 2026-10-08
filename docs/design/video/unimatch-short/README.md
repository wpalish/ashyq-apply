# Unimatch — 30-second vertical short (HyperFrames)

`unimatch-short-30s.mp4` — 1080 × 1920, 30 s, with sound (a lighter re-encode; the full-quality
render is `npx hyperframes render` from this folder).

**What it is.** A repurpose of a 30 s horizontal SaaS promo (a ClimbX launch video) into a fresh
vertical short for Unimatch. Kept: the core idea — a nagging question answered by the product in
fast, confident beats — and the pacing (a new beat every 2–4 s, a dark "why it matters" beat two
thirds in, an end card with one button). Original: the visuals (Unimatch's night globe, passes in
country colours, the money line by line, the three answers, deadline tickets), the script and the
structure. Nothing is taken from the source — not a frame, a line or a sound.

| Time | Frame | On screen |
|---|---|---|
| 0–3 s | 01-hook | "where can i study — and what will it cost?" typed under a pile of browser tabs |
| 3–5 s | 02-logo | the tabs pulled into one point — the dot of the i — and the wordmark opens out of it |
| 5–9 s | 03-routes | routes from Astana on the night globe; "to 15 countries" (demo run) |
| 9–11 s | 04-passes | three passes stack, each in its country's colour |
| 11–15 s | 05-money | price − grant = 1,848 left to pay, *if awarded*, with its source |
| 15–19 s | 06-answers | requirements · profile · money; "answers, not odds." |
| 19–22 s | 07-decide | Keep / Maybe, one pass at a time |
| 22–25 s | 08-plan | dated tickets and the week's first document |
| 25–30 s | 09-end | "know what's left to pay — before you apply."; the button |

**Honesty.** Every figure is the demo corpus's and is labelled on screen (Example · demo data,
demo fixture, deadlines from demo data); no chance, probability or percentage appears; "if
awarded" stays beside the grant-reduced price; no users, reviews, ratings or URL are invented.

**Built with** the HyperFrames `product-launch-video` workflow (CLI 0.8.137), autonomous mode, no
public URL (no-capture path; brand tokens from `frontend/src/styles/tokens.css`).

- `BRIEF.md`, `STORYBOARD.md` (the time-coded shot plan), `frame.md` (the broadside preset remixed
  onto palette E, with Unimatch overrides).
- `compositions/frames/*.html` — written by `tools/gen_frames.py <this folder>`.
- `assets/images/globe-night.svg` + `capture/assets/images/routes.json` — `tools/make_globe.py
  <out dir>`, from the app's own land dots (`frontend/src/lib/globe-land.ts`).
- `assets/audio/unimatch-bed.mp3` — `tools/make_music.py <out.wav>`: an original 120 BPM bed in
  A minor synthesized with numpy (no samples, no library), then `ffmpeg … loudnorm=I=-14`;
  accents land on the animation's cues. `tools/add_music.py` mounts it in `index.html` after
  `assemble-index`.
- The logo is the owner's wordmark (`docs/design/brand/unimatch-logo.svg`, traced from
  `unimatch-logo-source.jpg`), inlined by `gen_frames.py` so it takes the text colour.
- Fonts: Inter (SIL OFL), from `@fontsource/inter`.

Rebuild: `python3 tools/gen_frames.py .` → `node <product-launch-video>/scripts/assemble-index.mjs
--storyboard ./STORYBOARD.md --hyperframes .` → `python3 tools/add_music.py .` →
`npx hyperframes@0.8.137 check` → `npx hyperframes@0.8.137 render --quality high`.
Checks at delivery: lint 0, layout 0, contrast 58/58 WCAG AA, motion 0.

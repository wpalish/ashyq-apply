# Short video «Горизонт»

A 30-second vertical promo for Reels, Shorts and TikTok, in the «Горизонт» design with the
«Солнце» palette (PR #20). It repurposes a reference promo; `PLAN.md` has the reference's beat map,
what was kept and changed, the beat sheet and the loop report.

**The file:** `ashyq-horizon-ru.mp4`: 1080 × 1920, 30 fps, 30 s, H.264 + AAC, in Russian. The poster frame is `poster.jpg` (8 s in).

## Render it again

```bash
cd marketing/short-video
npm ci
npm run render            # → out/ashyq-horizon-ru.mp4, about 4 minutes
npm run sheet             # → out/sheet-*.png, a frame every 0.5 s
node render.mjs --preview 8.4 12.1   # → out/frame-8.40.png, out/frame-12.10.png
```

It needs:

- **Chromium.** It uses `PLAYWRIGHT_CHROMIUM`, or Playwright's own build, or any
  `chromium-*` in `PLAYWRIGHT_BROWSERS_PATH`.
- **An ffmpeg with libx264.** It uses `FFMPEG`, or `ffmpeg` on `PATH`.

It reads the globe's land dots and city table from `frontend/src/lib/`, so run it inside the
repository.

## How it works

| File | Role |
|---|---|
| `index.html` | The stage at 1080 × 1920 and the «Солнце» tokens, copied by value from `frontend/src/styles/tokens.css` |
| `video.js` | All copy in one `COPY` table, the scenes, and `render(t)`: every element's state is a pure function of time |
| `render.mjs` | Builds `build/data.js`: the land dots and the 20 result cities from `globe-places.json`, with the counts asserted. Then it steps time, screenshots each frame and pipes the PNGs to ffmpeg |
| `sound.mjs` | Synthesises the soundtrack (pad, ticks, air and a bell), seeded and deterministic. No third-party audio |

### Guards that fail the render

- A copy word from the invariants' banned list appears on screen: шанс, %, вероятн, гарант,
  поступишь, «покрывает всё» and their English equivalents.
- A font does not load.
- The money rows do not add up to the corpus's €30 050.
- A result city is missing from PR #20's table.
- The results are not 20 in 15 countries.
- The hero globe's markers and edge chips do not add up to 20.
- The page logs an error.

## Changing the words

- The copy is in `COPY` at the top of `video.js`.
- Headlines fit themselves to 880 px, so a longer line only gets smaller.
- The status labels follow the concept's proposed vocabulary
  (`docs/design/redesign-concepts.md` §17). That vocabulary is not yet live in `i18n.ts`: it is an
  open owner decision.
- A Kazakh or English cut is a copy of `COPY` and a second render.

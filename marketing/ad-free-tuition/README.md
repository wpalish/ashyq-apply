# Ad «Бесплатно — это сколько?»

A 22–27 s vertical awareness ad for school students (TikTok, Reels, Shorts), built with
[HyperFrames](https://hyperframes.heygen.com) in the «Горизонт» design (PR #20).

| File | Contents |
|---|---|
| `BRIEF.md` | The goal, the audience and the rules |
| `SCRIPT.md` | The script, second by second, and why each figure is honest |
| `lines.json` | The voice lines: the text sent to TTS, the caption text and the accent words |
| `prepare.mjs` | Writes the globe data, the timing from the real voice lengths, the joined voice track and a synthesised music bed |
| `index.html` | The composition: one paused GSAP timeline, and the canvas, counters and captions drawn from its time |

## Build

```bash
cd marketing/ad-free-tuition
node prepare.mjs                          # after putting assets/vo/line-1.wav … line-7.wav in place
npx --yes hyperframes@0.8.91 check        # lint, runtime, layout, contrast
npx --yes hyperframes@0.8.91 render -o renders/ad.mp4
```

`prepare.mjs` reads the land dots and city table from `frontend/src/lib/`, so run it inside the
repository. GSAP and the fonts are vendored in `assets/`: the render makes no network request.

## The voice

There are two voices:

- **The draft**, for timing and review only, from **fish-speech 1.5** run locally.
  - Its weights are licensed CC BY-NC-SA 4.0 (non-commercial).
  - The draft voice is therefore git-ignored and must not run in an ad.
- **The final voice**, from the **Fish Audio API** (paid, commercial use).
  - It needs API credit on the account, which is separate from platform credit.
  - The key is read from `FISH_AUDIO_API_KEY` and is never committed.
  - The final lines go in the same `assets/vo/line-N.wav` files. Then run `node prepare.mjs` again:
    every scene follows the real line lengths.

Avoid voice clones of real people for an ad.

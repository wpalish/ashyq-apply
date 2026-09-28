# Short video «Горизонт» — plan

A 30-second vertical video (1080 × 1920, 30 fps) for Reels, Shorts and TikTok. It repurposes a
reference promo (`shownotover`, 30 s, 1920 × 1080, a product for X creators) for ASHYQ Apply. It keeps
the reference's idea and pacing. The visuals, script and structure are new, in the «Горизонт» design
system with the «Солнце» palette (PR #20).

## 1. What the reference does (beat map)

Timings come from frames sampled every 0.5 s.

| Time | Beat | Form |
|---|---|---|
| 0.0–1.5 | "Find creators in your niche." | Kinetic headline. Words rise; the full stop is an accent dot |
| 1.5–5.5 | Pick niches → "Discover" → Searching / Finding / Scraping / Validating → list | UI card, cursor, blur-through transitions |
| 5.5–6.5 | "See what's working for them." | Headline |
| 6.5–9.0 | A line chart spikes to "12.4x" and becomes a post card | Data → object morph |
| 9.0–10.5 | "Make it yours." | Headline |
| 10.5–12.0 | The editor rewrites the post | Typing |
| 12.0–13.0 | "Score it before you post." | Headline |
| 13.0–15.0 | The coach scores 69 → 92, with a reach range labelled "not a forecast" | Counters and bars |
| 15.0–17.0 | Schedule → a calendar slot fills | UI |
| 17.0–20.0 | Circle wipe to green: 3 → 500 followers, "or a full refund" | Hero moment, colour flip |
| 20.0–21.0 | "Learn what actually moves views." | Headline |
| 21.5–25.5 | Guide cards tilt and scroll in 3D | Depth |
| 25.5–30.0 | Logo burst → wordmark + URL | End card |

**The core idea** is four verb headlines, each followed by the product doing that verb. After them
come a colour-flip hero moment with the promise, a "learn more" beat and the logo. **The pacing** is
about 1 s per headline and 2.5–4 s per demo, with one long moment at about 60 % of the runtime.

## 2. What we keep, what we change

| Keep | Change |
|---|---|
| The rhythm: headline ↔ demo, four times | The product and the script: our flow is search → research → programme → money → source → plan → share |
| A hero colour flip at about 60 % | Green becomes the night palette. The wipe is a horizon (a globe's limb) rising, not a circle |
| An accent full stop | The full stop is the brand's sun. It becomes the next scene's element (the button, the route's start) |
| A data → object morph | A route arc on the dotted globe lands on a price pill, which becomes the programme card (instead of a spike becoming a post) |
| Depth near the end | Our three share-story cards fan out in 3D (instead of guide cards) |
| An end card with a brand burst | The sun mark with rays → «ASHYQ Apply» → tagline, and the university disclaimer instead of a URL (there is no public domain) |
| 30 s | 9:16 instead of 16:9. Russian instead of English |

**Dropped on purpose: the reference's promise** ("500 followers in 30 days or a full refund"). The
product's equivalent would be an outcome promise, which the invariants forbid (see §4). Our hero
moment promises method instead: *414 facts, each with a link and a date; where there is no data, we
say so*.

## 3. Beat sheet

The copy is Russian, in the product's voice ("ты", plain words). The status labels come from the
concept's proposed vocabulary (`docs/design/redesign-concepts.md` §2 and §17). It is not live in
`i18n.ts` yet (an open owner decision), so all copy sits in one table in `index.html`.

| # | Time (s) | Scene | On screen |
|---|---|---|---|
| 1 | 0.0–1.6 | Headline | «Найди, где учиться**.**» The sun dot drops away to become the button |
| 2 | 1.6–5.2 | Start → research | The search card over the rising globe types «Computer Science · Весь мир · до $6 000». The sun button is pressed and the night rises. «Поиск идёт»: four steps (сайты вузов · требования · деньги после гранта · даты), counting 96 pages and 414 facts. Then «Нашли 20 программ в 15 странах» |
| 3 | 5.2–6.4 | Headline | «Сверь себя с требованиями**.**» |
| 4 | 6.4–9.0 | Globe → programme | The globe turns from Kazakhstan. A gold route draws Astana → Groningen. The pill «Гронинген · $1 848 в год» becomes the card. Three rows arrive one at a time: Требования «Ждём: оценка по математике» · Профиль «Выше требований» + «отбор всё равно конкурсный» · Деньги «Грант: учёба и проживание» |
| 5 | 9.0–10.2 | Headline | «Посчитай настоящую цену**.**» |
| 6 | 10.2–12.6 | Money as arithmetic | €16 500 + €600 + €7 200 + €3 600 + €2 150 = €30 050 − Talent Grant €28 350 = **€1 700 ≈ $1 848 в год**. «$1 = €0.92 на 1 августа 2026». «В бюджете до $6 000» |
| 7 | 12.6–13.6 | Headline | «Проверь каждый факт**.**» |
| 8 | 13.6–15.6 | Source | The grant quote is highlighted. The stamp reads «rug.nl · страница гранта · проверено 14 сентября». A dashed card follows: «Вена · итог не посчитан: нет цены за питание» |
| 9 | 15.6–17.6 | Plan | The split-flap flips to **1 ДЕК** (Токио · PEAK). Then the rows: Токио 1 декабря · Торонто 15 января · Гронинген 1 мая |
| 10 | 17.6–21.0 | Hero (night) | The horizon rises. The night globe lights the 20 result cities. **414** counts up: «фактов — у каждого ссылка на сайт вуза и дата». Then: «Нет данных — так и скажем. Угадывать не будем.» |
| 11 | 21.0–22.2 | Headline | The horizon sets. «Поделись своим маршрутом**.**» |
| 12 | 22.2–25.6 | Stories | Three cards fan out in 3D: «Мой маршрут» (night), «Требования выполнены» (sun, Tokyo, with «Решение о приёме — за университетом»), «Моя карта поступления» (white) |
| 13 | 25.6–30.0 | End card | The sun with rays → «ASHYQ Apply» → «Вузы и гранты — с источником у каждой цифры» · «Решение о приёме и гранте — за университетом» |

## 4. Rules the video must pass (from the skills and invariants)

- **`applicant-fit-scoring`**:
  - no "шанс", no "%", no probability anywhere near the list;
  - the three judgements are three separate rows, never one verdict;
  - «Выше требований» always carries «отбор всё равно конкурсный»;
  - no "поступишь", "гарантия" or "получишь грант".
- **`scholarship-audit`**:
  - the Talent Grant is «учёба и проживание», never «покрывает всё» (concept defect R8);
  - the price is arithmetic, per year and after the grant;
  - the conversion shows its rate and the rate's date (R10).
- **Unknown is a state.** Scene 8 shows a dashed «итог не посчитан» with its reason, and scene 10
  says so aloud.
- **A source and a date** sit next to the facts (scenes 4, 6 and 8).
- **Demo data is labelled.** Every UI scene carries «Демо-данные»: the corpus is synthetic, and only
  the institution names are real (`backend/app/corpus/data.py`, line 3).
- **Only numbers from the demo run**
  (`ai-team/outputs/c1-t18-a1/logs/qa_t18_a3_seed.log`) and the corpus: 20 programmes, 15
  countries, 96 pages, 414 claims, 9 meeting the requirements, and Groningen $1 848. Globe markers
  are the 20 result cities from `globe-places.json`. None is typed by hand.
- **Design system:**
  - «Солнце» tokens only;
  - Montserrat 800 for headings, Onest for text, tabular figures;
  - the sun yellow is the button only;
  - "warn" is a pale amber pill;
  - the night palette is for moments only (research, hero, the night story).
- **Legibility on a phone:**
  - text at least 30 px at 1080 w (≈ 11 pt on a phone);
  - contrast at least 4.5:1;
  - nothing important inside the platform UI zones (top 220 px, bottom 380 px, right 140 px).

## 5. How it is built

- `index.html` is a single page with a deterministic `render(t)`. Every element's state is a pure
  function of time, so frame N is identical on every run. There are no CSS transitions and no
  `requestAnimationFrame` in the render path.
- The globe is PR #20's projection (`frontend/src/lib/globe.ts`: orthographic, the 8 441 Natural
  Earth dots, great-circle routes), on a canvas.
- `render.mjs` opens the page in Playwright's Chromium, steps `t` frame by frame, captures PNGs and
  pipes them to ffmpeg (H.264, yuv420p, +faststart).
- `sound.mjs` synthesises an original bed: a soft pad in the product's calm register, with a tick
  on every beat and a swell under the hero. No third-party audio is used.
- Fonts come from `@fontsource/montserrat` and `@fontsource/onest`, the same packages the app ships.

## 6. Definition of done (`loop-engineering`)

- [ ] `npm ci && npm run render` produces `out/ashyq-horizon-ru.mp4` from the README alone
- [ ] 30.0 s, 1080 × 1920, 30 fps, H.264 + AAC, under 12 MB
- [ ] Every beat in §3 is on screen at its time. Checked on a contact sheet at 2 fps
- [ ] A grep of the copy table finds no forbidden word: шанс, %, вероятност, гарант, поступишь,
      «покрывает всё»
- [ ] Every UI scene shows «Демо-данные»; every figure next to a fact has its source or rate date
- [ ] The Kazakh-safe fonts load: no fallback glyphs (checked with `document.fonts.check`)
- [ ] At least two critique cycles, each recorded in §7 with the root cause of each defect

## 7. Loop report

Filled in while building.

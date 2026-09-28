#!/usr/bin/env node
/*
 * Renders index.html frame by frame into out/ashyq-horizon-ru.mp4.
 *
 *   node render.mjs              the video (900 frames at 30 fps, with sound)
 *   node render.mjs --preview 7.9 [8.4 …]   single frames as out/frame-<t>.png
 *   node render.mjs --sheet      a contact sheet every 0.5 s, out/sheet-*.png
 *
 * Needs Chromium (PLAYWRIGHT_CHROMIUM or Playwright's default) and an ffmpeg
 * with libx264 (FFMPEG or `ffmpeg` on PATH).
 */
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from 'playwright-core';
import { writeSound } from './sound.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..');
const OUT = join(HERE, 'out');
const FPS = 30;
const FFMPEG = process.env.FFMPEG || 'ffmpeg';

/*
 * The demo run's 20 results (ai-team/outputs/c1-t18-a1/logs/qa_t18_a3_seed.log),
 * each at its campus city in the demo corpus (backend/app/corpus/pages/catalog.json).
 * The globe places a city only from PR #20's checked table; a missing one fails here.
 */
const RESULTS = [
  ['University of Groningen', 'Groningen'], ['KU Leuven', 'Leuven'], ['University of Tokyo', 'Tokyo'],
  ['University of Toronto', 'Toronto'], ['McGill University', 'Montreal'], ['University of Amsterdam', 'Amsterdam'],
  ['Eindhoven University of Technology', 'Eindhoven'], ['University of Vienna', 'Vienna'],
  ['National University of Singapore', 'Singapore'], ['Aalto University', 'Espoo'],
  ['University of British Columbia', 'Vancouver'], ['University of Oslo', 'Oslo'], ['Arizona State University', 'Tempe'],
  ['Technical University of Munich', 'Munich'], ['University of Edinburgh', 'Edinburgh'],
  ['Trinity College Dublin', 'Dublin'], ['University of Warsaw', 'Warsaw'], ['Delft University of Technology', 'Delft'],
  ['University of Melbourne', 'Melbourne'], ['EPFL', 'Lausanne'],
];
// Region words for the edge chips, and the side of the screen each lies towards
// from a view centred on Central Asia.
const REGION = { 'United States': 'Америка', Canada: 'Америка', Australia: 'Австралия', Japan: 'Азия', Singapore: 'Азия' };
const SIDE = { 'Америка': 'left', 'Австралия': 'right', 'Азия': 'right', 'Европа': 'left' };

function buildData() {
  const land = readFileSync(join(ROOT, 'frontend/src/lib/globe-land.ts'), 'utf8').match(/LAND_DOTS = '([^']+)'/)[1];
  const table = JSON.parse(readFileSync(join(ROOT, 'frontend/src/lib/globe-places.json'), 'utf8'));
  const places = {};
  const results = RESULTS.map(([uni, city]) => {
    const row = table.cities.find((p) => p.city === city);
    if (!row) throw new Error(`${city} is not in globe-places.json; the globe would have to guess`);
    places[city] = { lat: row.lat, lon: row.lon };
    return { uni, city, country: row.country, region: REGION[row.country] ?? 'Европа' };
  });
  const home = table.homes.find((p) => p.country === 'Kazakhstan');
  if (!home) throw new Error('Kazakhstan has no home point in globe-places.json');
  places.Astana = { lat: home.lat, lon: home.lon };
  // The copy says «20 программ в 15 странах»: count, do not trust the sentence.
  const countries = new Set(results.map((r) => r.country)).size;
  if (results.length !== 20 || countries !== 15) throw new Error(`results: ${results.length} in ${countries} countries`);
  mkdirSync(join(HERE, 'build'), { recursive: true });
  writeFileSync(join(HERE, 'build/data.js'), `window.GLOBE = ${JSON.stringify({ land, places, results, side: SIDE })};\n`);
}

// The env var, then Playwright's own build, then any Chromium already in the
// browsers folder (a pinned playwright-core may expect a build that is not there).
function chromiumPath() {
  if (process.env.PLAYWRIGHT_CHROMIUM) return process.env.PLAYWRIGHT_CHROMIUM;
  try { const p = chromium.executablePath(); if (existsSync(p)) return p; } catch { /* fall through */ }
  const dir = process.env.PLAYWRIGHT_BROWSERS_PATH;
  if (!dir || !existsSync(dir)) return undefined;
  for (const name of readdirSync(dir).filter((d) => /^chromium-\d+$/.test(d)).sort().reverse()) {
    for (const sub of ['chrome-linux/chrome', 'chrome-linux64/chrome', 'chrome-mac/Chromium.app/Contents/MacOS/Chromium']) {
      if (existsSync(join(dir, name, sub))) return join(dir, name, sub);
    }
  }
  return undefined;
}

async function openPage() {
  const executablePath = chromiumPath();
  const browser = await chromium.launch({ executablePath });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(pathToFileURL(join(HERE, 'index.html')).href);
  const ready = await page.evaluate(() => window.__ready);
  if (ready.missing.length) throw new Error(`fonts missing: ${ready.missing.join(', ')}`);
  // The invariants' words (AGENTS.md §6, applicant-fit-scoring, scholarship-audit): none may reach the screen.
  const words = await page.evaluate(() => JSON.stringify(window.COPY) + document.body.innerText);
  const banned = words.match(/шанс|вероятн|гарант|поступишь|получишь грант|покрывает вс|%|chance|probab|guarantee|full ride/gi);
  if (banned) throw new Error(`forbidden wording on screen: ${[...new Set(banned)].join(', ')}`);
  return { browser, page, errors };
}

async function frame(page, t) {
  await page.evaluate((tt) => window.render(tt), t);
  return page.screenshot({ type: 'png' });
}

function run(cmd, args, input) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: [input ? 'pipe' : 'ignore', 'inherit', 'inherit'] });
    p.on('error', reject);
    p.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`${cmd} exited ${code}`))));
    if (input) input(p.stdin);
  });
}

async function main() {
  const args = process.argv.slice(2);
  mkdirSync(OUT, { recursive: true });
  buildData();
  const { browser, page, errors } = await openPage();
  const duration = await page.evaluate(() => window.DURATION);
  try {
    if (args[0] === '--preview') {
      for (const t of args.slice(1).map(Number)) {
        writeFileSync(join(OUT, `frame-${t.toFixed(2)}.png`), await frame(page, t));
      }
    } else if (args[0] === '--sheet') {
      const dir = join(OUT, 'sheet');
      mkdirSync(dir, { recursive: true });
      let i = 0;
      for (let t = 0.25; t < duration; t += 0.5) writeFileSync(join(dir, `s_${String(i++).padStart(3, '0')}.png`), await frame(page, t));
      await run(FFMPEG, ['-hide_banner', '-loglevel', 'error', '-y', '-i', join(dir, 's_%03d.png'), '-vf', 'scale=270:480,tile=10x2:padding=6:color=white', join(OUT, 'sheet-%d.png')]);
    } else {
      const wav = join(OUT, 'sound.wav');
      writeSound(wav, duration);
      const mp4 = join(OUT, 'ashyq-horizon-ru.mp4');
      const frames = Math.round(duration * FPS);
      const started = Date.now();
      await run(FFMPEG, [
        '-hide_banner', '-loglevel', 'error', '-y',
        '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
        '-i', wav,
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
        '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', mp4,
      ], async (stdin) => {
        for (let f = 0; f < frames; f += 1) {
          const png = await frame(page, f / FPS);
          if (!stdin.write(png)) await new Promise((r) => stdin.once('drain', r));
          if (f % 60 === 0) process.stdout.write(`\rframe ${f}/${frames}`);
        }
        stdin.end();
      });
      process.stdout.write(`\rrendered ${frames} frames in ${((Date.now() - started) / 1000).toFixed(0)} s → ${mp4}\n`);
    }
  } finally {
    await browser.close();
  }
  if (errors.length) {
    console.error(errors.join('\n'));
    process.exit(1);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });

#!/usr/bin/env node
/*
 * Prepares everything index.html reads, so the composition itself stays static and deterministic:
 *
 *   assets/globe-data.js  land dots + result cities from PR #20's globe table (counts asserted)
 *   assets/timing.js      when each voice line starts and ends, from the real clip lengths
 *   assets/vo.wav         the voice lines joined with fixed gaps
 *   assets/bgm.wav        a quiet synthesised bed with cues on the scene cuts (no third-party audio)
 *
 * Voice lines are assets/vo/line-<n>.wav, one per entry of lines.json. When a line is missing the
 * timing falls back to an estimate (2.7 words/s) so the picture can be built before the voice.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..', '..');
const LEAD = 0.35;   // silence before the first word
const GAP = 0.22;    // between lines
const TAIL = 1.6;    // after the last line, for the end card to breathe
const SR = 48000;

const lines = JSON.parse(readFileSync(join(HERE, 'lines.json'), 'utf8'));

// --- globe ---------------------------------------------------------------
// The demo run's 20 results (ai-team/outputs/c1-t18-a1/logs/qa_t18_a3_seed.log) at their cities.
const CITIES = ['Groningen', 'Leuven', 'Tokyo', 'Toronto', 'Montreal', 'Amsterdam', 'Eindhoven', 'Vienna', 'Singapore', 'Espoo',
  'Vancouver', 'Oslo', 'Tempe', 'Munich', 'Edinburgh', 'Dublin', 'Warsaw', 'Delft', 'Melbourne', 'Lausanne'];
const land = readFileSync(join(ROOT, 'frontend/src/lib/globe-land.ts'), 'utf8').match(/LAND_DOTS = '([^']+)'/)[1];
const table = JSON.parse(readFileSync(join(ROOT, 'frontend/src/lib/globe-places.json'), 'utf8'));
const results = CITIES.map((city) => {
  const row = table.cities.find((p) => p.city === city);
  if (!row) throw new Error(`${city} is not in globe-places.json; the globe would have to guess`);
  return { city, country: row.country, lat: row.lat, lon: row.lon };
});
const countries = new Set(results.map((r) => r.country)).size;
if (results.length !== 20 || countries !== 15) throw new Error(`results: ${results.length} in ${countries} countries, the copy says 20 in 15`);
const home = table.homes.find((p) => p.country === 'Kazakhstan');
writeFileSync(join(HERE, 'assets/globe-data.js'), `window.GLOBE = ${JSON.stringify({ land, results, home: { lat: home.lat, lon: home.lon } })};\n`);

// --- timing and voice ----------------------------------------------------
const probe = (f) => Number(execFileSync('ffprobe', ['-v', '0', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).toString().trim());
let t = LEAD;
let real = 0;
const timing = lines.map((line, i) => {
  const file = join(HERE, `assets/vo/line-${i + 1}.wav`);
  const has = existsSync(file);
  if (has) real += 1;
  const dur = has ? probe(file) : line.tts.split(/\s+/).length / 2.7;
  const out = { start: +t.toFixed(3), dur: +dur.toFixed(3), caption: line.caption, accent: line.accent };
  t += dur + GAP;
  return out;
});
const total = +(t - GAP + TAIL).toFixed(2);
writeFileSync(join(HERE, 'assets/timing.js'), `window.TIMING = ${JSON.stringify({ total, lines: timing, voiced: real === lines.length }, null, 1)};\n`);

if (real === lines.length) {
  // Place each line at its start on a silent track of the full length.
  const inputs = [];
  const parts = [];
  timing.forEach((l, i) => {
    inputs.push('-i', join(HERE, `assets/vo/line-${i + 1}.wav`));
    parts.push(`[${i}:a]aresample=${SR},aformat=channel_layouts=mono,adelay=${Math.round(l.start * 1000)}[a${i}]`);
  });
  const mix = `${parts.join(';')};${timing.map((_, i) => `[a${i}]`).join('')}amix=inputs=${timing.length}:normalize=0,apad=whole_dur=${total},loudnorm=I=-16:TP=-1.5:LRA=7[out]`;
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...inputs, '-filter_complex', mix, '-map', '[out]', '-ar', String(SR), '-ac', '1', join(HERE, 'assets/vo.wav')]);
} else {
  // No voice yet: a silent track of the full length keeps the composition checkable.
  execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', `anullsrc=r=${SR}:cl=mono`, '-t', String(total), join(HERE, 'assets/vo.wav')]);
}

// The composition's clips last as long as the voice: patch every data-duration in index.html.
const html = join(HERE, 'index.html');
writeFileSync(html, readFileSync(html, 'utf8').replace(/data-duration="[0-9.]+"/g, `data-duration="${total}"`));

// --- music bed -----------------------------------------------------------
writeBed(join(HERE, 'assets/bgm.wav'), total, timing);

console.log(`timing: ${timing.length} lines, ${total}s, ${real}/${lines.length} voiced`);
timing.forEach((l, i) => console.log(`  ${i + 1}  ${l.start.toFixed(2)}–${(l.start + l.dur).toFixed(2)}  ${l.caption}`));

function writeBed(path, duration, cues) {
  const n = Math.ceil(duration * SR);
  const L = new Float32Array(n), R = new Float32Array(n);
  let seed = 20260929;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const midi = (m) => 440 * Math.pow(2, (m - 69) / 12);
  const add = (i, l, r = l) => { if (i >= 0 && i < n) { L[i] += l; R[i] += r; } };
  // A pulsing low pad: D → Bm → G → A, a bar each, looped; brighter from the product beat on.
  const chords = [[50, 57, 62, 66], [47, 54, 59, 62], [43, 50, 55, 59], [45, 52, 57, 61]];
  const bar = 2.2;
  for (let i = 0; i < n; i += 1) {
    const s = i / SR;
    const ci = Math.floor(s / bar) % chords.length;
    const within = (s % bar) / bar;
    const env = Math.min(1, s / 0.6) * Math.min(1, (duration - s) / 1.2);
    const pulse = 0.75 + 0.25 * Math.cos(2 * Math.PI * within * 4);
    let v = 0;
    chords[ci].forEach((m, k) => { const f = midi(m); v += Math.sin(2 * Math.PI * f * s + k) * (k === 0 ? 1.2 : 0.7); });
    const bright = s > (cues[2]?.start ?? 5) ? 1 : 0.6;
    add(i, v * 0.02 * env * pulse * bright);
  }
  const tick = (at, f, g) => { const i0 = Math.floor(at * SR); for (let k = 0; k < SR * 0.07; k += 1) { const e = Math.exp(-k / (SR * 0.012)); add(i0 + k, (Math.sin(2 * Math.PI * f * k / SR) * 0.8 + (rnd() * 2 - 1) * 0.2) * e * g); } };
  const whoosh = (at, len, g) => { const i0 = Math.floor(at * SR); let lp = 0; for (let k = 0; k < SR * len; k += 1) { const x = k / (SR * len); lp += (0.02 + 0.2 * x) * ((rnd() * 2 - 1) - lp); add(i0 + k, lp * Math.sin(Math.PI * x) * g); } };
  const thud = (at, g) => { const i0 = Math.floor(at * SR); for (let k = 0; k < SR * 0.35; k += 1) { const s = k / SR; add(i0 + k, Math.sin(2 * Math.PI * (90 - 50 * s) * s) * Math.exp(-s / 0.09) * g); } };
  const bell = (at, f0, g) => { const i0 = Math.floor(at * SR); for (let k = 0; k < SR * 2.2; k += 1) { const s = k / SR; let v = 0; for (const [m, a] of [[1, 1], [2, 0.4], [3.01, 0.2]]) v += a * Math.sin(2 * Math.PI * f0 * m * s) * Math.exp(-s / (1.4 / m)); add(i0 + k, v * g); } };
  thud(cues[0].start + 0.9, 0.5);                            // the «Бесплатно?» stamp
  cues.forEach((c, i) => { if (i) whoosh(c.start - 0.25, 0.4, 0.12); tick(c.start, 2300, 0.08); });
  for (let k = 0; k < 6; k += 1) tick(cues[1].start + 0.3 + k * 0.14, k < 4 ? 2600 : 900, 0.06);  // the receipt rows
  bell(cues[2].start + cues[2].dur * 0.7, midi(81), 0.06);   // the remainder lands
  bell(cues[6].start, midi(62), 0.12); bell(cues[6].start + 0.02, midi(69), 0.07);
  const buf = Buffer.alloc(44 + n * 4);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + n * 4, 4); buf.write('WAVEfmt ', 8); buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22); buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 4, 28);
  buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34); buf.write('data', 36); buf.writeUInt32LE(n * 4, 40);
  for (let i = 0; i < n; i += 1) {
    buf.writeInt16LE(Math.round(Math.tanh(L[i] * 2) * 0.9 * 32767), 44 + i * 4);
    buf.writeInt16LE(Math.round(Math.tanh(R[i] * 2) * 0.9 * 32767), 46 + i * 4);
  }
  writeFileSync(path, buf);
}

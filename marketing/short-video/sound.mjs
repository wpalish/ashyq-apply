/*
 * The soundtrack, synthesised here so the video carries no third-party audio.
 *
 * A soft pad moves through the product's calm register (D → Bm → G → A → G → D).
 * The cues sit on the beat sheet's cuts (PLAN.md §3): a tick for each headline,
 * air for the night rising and closing, clicks for the split-flap, a swell
 * under the hero, and a bell when the sun rises on the end card. The noise is
 * seeded, so the file is the same on every run.
 */
import { writeFileSync } from 'node:fs';

const SR = 48000;

function mulberry32(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const midi = (n) => 440 * Math.pow(2, (n - 69) / 12);
// [start, end, notes] — voiced low and open so the pad sits under speech if one is added.
const CHORDS = [
  [0.0, 7.6, [50, 57, 62, 66, 69]],   // D add9 colour: D A D F# A
  [7.4, 15.2, [47, 54, 59, 62, 66]],  // Bm7
  [15.0, 17.8, [43, 50, 55, 59, 62]], // Gmaj
  [17.6, 21.2, [45, 52, 57, 61, 64]], // A — the night
  [21.0, 25.8, [43, 50, 55, 59, 66]], // Gmaj7
  [25.6, 30.5, [50, 57, 62, 64, 69]], // D add2 — home
];

export function writeSound(path, duration) {
  const n = Math.ceil(duration * SR);
  const L = new Float32Array(n), R = new Float32Array(n);
  const rnd = mulberry32(20260928);
  const add = (i, l, r = l) => { if (i >= 0 && i < n) { L[i] += l; R[i] += r; } };

  // Pad: three slightly detuned sines per note, slow attack, overlapping chords.
  for (const [a, b, notes] of CHORDS) {
    const i0 = Math.floor(a * SR), i1 = Math.min(n, Math.floor(b * SR));
    notes.forEach((note, v) => {
      const f = midi(note), pan = (v / (notes.length - 1)) * 0.6 - 0.3;
      const amp = 0.028 * (note < 48 ? 1.3 : 1);
      for (let i = i0; i < i1; i += 1) {
        const t = (i - i0) / SR, len = (i1 - i0) / SR;
        const env = Math.min(1, t / 0.9) * Math.min(1, (len - t) / 0.7);
        const ph = 2 * Math.PI * f * (i / SR);
        const s = Math.sin(ph) + 0.6 * Math.sin(ph * 1.0017) + 0.6 * Math.sin(ph * 0.9983) + 0.12 * Math.sin(2 * ph);
        const breathe = 0.85 + 0.15 * Math.sin(2 * Math.PI * 0.18 * (i / SR) + v);
        add(i, s * amp * env * breathe * (1 - pan), s * amp * env * breathe * (1 + pan));
      }
    });
  }

  const tick = (at, f = 2200, gain = 0.16) => {
    const i0 = Math.floor(at * SR);
    for (let k = 0; k < SR * 0.08; k += 1) {
      const t = k / SR, e = Math.exp(-t / 0.012);
      add(i0 + k, (Math.sin(2 * Math.PI * f * t) * 0.8 + (rnd() * 2 - 1) * 0.2) * e * gain);
    }
  };
  const whoosh = (at, len, up = true, gain = 0.22) => {
    const i0 = Math.floor(at * SR);
    let lp = 0;
    for (let k = 0; k < SR * len; k += 1) {
      const x = k / (SR * len);
      const e = Math.sin(Math.PI * (up ? Math.pow(x, 0.7) : 1 - Math.pow(1 - x, 0.7)));
      const cut = 0.02 + 0.2 * (up ? x : 1 - x);
      lp += cut * ((rnd() * 2 - 1) - lp);
      add(i0 + k, lp * e * gain * (1 - 0.3 * x), lp * e * gain * (0.7 + 0.3 * x));
    }
  };
  const bell = (at, f0, gain = 0.12, decay = 1.6) => {
    const i0 = Math.floor(at * SR);
    const partials = [[1, 1], [2.0, 0.45], [3.01, 0.25], [4.2, 0.12]];
    for (let k = 0; k < SR * decay * 2.5; k += 1) {
      const t = k / SR;
      let s = 0;
      for (const [m, a] of partials) s += a * Math.sin(2 * Math.PI * f0 * m * t) * Math.exp(-t / (decay / m));
      add(i0 + k, s * gain * Math.min(1, t / 0.004));
    }
  };
  const click = (at, gain = 0.08) => {
    const i0 = Math.floor(at * SR);
    let lp = 0;
    for (let k = 0; k < SR * 0.03; k += 1) {
      lp += 0.35 * ((rnd() * 2 - 1) - lp);
      add(i0 + k, lp * Math.exp(-k / (SR * 0.006)) * gain);
    }
  };
  const swell = (at, len, gain = 0.2) => {
    const i0 = Math.floor(at * SR);
    for (let k = 0; k < SR * len; k += 1) {
      const t = k / SR, x = t / len;
      const f = 55 + 18 * x;
      const e = Math.sin(Math.PI * Math.min(1, x * 1.4)) * (x < 0.7 ? 1 : 1 - (x - 0.7) / 0.3);
      add(i0 + k, Math.sin(2 * Math.PI * f * t) * e * gain);
    }
  };

  // Headlines: a tick as the first word lands.
  for (const at of [0.12, 5.4, 9.1, 12.7, 19.6, 21.2]) tick(at, 2300);
  // The sun dot drops into the button; the button is pressed; the night opens and closes.
  tick(1.62, 1600, 0.1); tick(3.12, 900, 0.18);
  whoosh(3.15, 0.65, true); whoosh(5.1, 0.55, false, 0.18);
  // Typing.
  for (let k = 0; k < 16; k += 1) click(2.05 + k * 0.04, 0.05);
  // Research steps and the find.
  for (let k = 0; k < 4; k += 1) tick(3.92 + k * 0.2, 3000, 0.07);
  bell(4.62, midi(74), 0.07, 0.9);
  // The route lands; the card arrives with its three rows.
  bell(7.48, midi(81), 0.08, 1.0); whoosh(7.8, 0.45, true, 0.12);
  for (let k = 0; k < 3; k += 1) tick(8.2 + k * 0.16, 2600, 0.07);
  // Money: rows, then the grant subtracts.
  for (let k = 0; k < 5; k += 1) tick(10.4 + k * 0.09, 2800, 0.05);
  whoosh(11.05, 0.5, true, 0.14); bell(11.85, midi(78), 0.07, 0.8);
  // The source is stamped; the unknown slides up.
  tick(14.58, 500, 0.3); whoosh(14.85, 0.4, true, 0.1);
  // The split-flap.
  for (let tt = 15.6; tt < 16.55; tt += 0.055) click(tt, 0.06);
  for (let k = 0; k < 5; k += 1) tick(15.9 + k * 0.13, 1400, 0.1);
  // The horizon: night rises with a swell, markers plink, then it sets.
  whoosh(17.5, 0.8, true, 0.2); swell(17.6, 3.4, 0.16);
  for (let k = 0; k < 14; k += 1) bell(18.2 + k * 0.045, midi(86 + (k % 3) * 3), 0.018, 0.4);
  whoosh(20.7, 0.7, false, 0.18);
  // The stories fly in.
  whoosh(22.1, 0.7, true, 0.16);
  // The sun rises: a bell, and the name.
  bell(25.72, midi(62), 0.16, 2.4); bell(25.75, midi(69), 0.09, 2.2); bell(26.8, midi(74), 0.07, 2.0);

  // Master: gentle saturation, fade in and out, 16-bit stereo.
  const out = Buffer.alloc(44 + n * 4);
  const write = (s, o) => out.write(s, o, 'ascii');
  write('RIFF', 0); out.writeUInt32LE(36 + n * 4, 4); write('WAVE', 8); write('fmt ', 12);
  out.writeUInt32LE(16, 16); out.writeUInt16LE(1, 20); out.writeUInt16LE(2, 22); out.writeUInt32LE(SR, 24);
  out.writeUInt32LE(SR * 4, 28); out.writeUInt16LE(4, 32); out.writeUInt16LE(16, 34); write('data', 36); out.writeUInt32LE(n * 4, 40);
  for (let i = 0; i < n; i += 1) {
    const t = i / SR;
    const fade = Math.min(1, t / 0.25) * Math.min(1, (duration - t) / 1.4);
    const l = Math.tanh(L[i] * 2.8) * 0.9 * fade, r = Math.tanh(R[i] * 2.8) * 0.9 * fade;
    out.writeInt16LE(Math.round(Math.max(-1, Math.min(1, l)) * 32767), 44 + i * 4);
    out.writeInt16LE(Math.round(Math.max(-1, Math.min(1, r)) * 32767), 46 + i * 4);
  }
  writeFileSync(path, out);
}

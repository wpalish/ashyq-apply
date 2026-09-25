/**
 * A story card drawn on the device: 1080 × 1920, the app's fonts and colours,
 * and the globe from the same land dots and projection as the app's globe.
 *
 * Nothing is uploaded to draw it. Facts sit inside Instagram's safe area
 * (§15): below the top 14 % (profile bar) and above the bottom 18 % (reply
 * bar); only the globe and the brand band reach into those zones.
 */

import { REGION_LABEL, regionOf } from '@/lib/regions';
import {
  centroidOf, greatCircle, loadLandDots, project, projectRad, type LatLon,
} from '@/lib/globe';
import type { StoryModel } from '@/lib/story';

export const STORY_W = 1080;
export const STORY_H = 1920;
const SAFE_TOP = Math.round(STORY_H * 0.14);
const SAFE_BOTTOM = Math.round(STORY_H * 0.82);
const M = 96;

const DISPLAY = "'Montserrat', system-ui, sans-serif";
const UI = "'Onest', system-ui, sans-serif";

interface Palette {
  bg: string;
  ink: string;
  muted: string;
  accent: string;
  land: string;
  route: string;
  panel: string;
  chipBg: string;
  chipInk: string;
  link: string;
}

const PALETTES: Record<StoryModel['tone'], Palette> = {
  night: {
    bg: '#0B1628', ink: '#FFFFFF', muted: '#A7B1C2', accent: '#FFC23D', land: '#C9D3E3', route: '#FFC23D',
    panel: '#16263F', chipBg: 'rgba(107, 227, 164, 0.16)', chipInk: '#6BE3A4', link: '#8FD3F4',
  },
  sun: {
    bg: '#FFC23D', ink: '#0F1E36', muted: '#3F3217', accent: '#0F1E36', land: '#0F1E36', route: '#0F1E36',
    panel: 'rgba(255, 255, 255, 0.6)', chipBg: '#0F1E36', chipInk: '#FFC23D', link: '#0F1E36',
  },
  day: {
    bg: '#F6F7F9', ink: '#0F1E36', muted: '#5A6578', accent: '#E8A317', land: '#7C8BA3', route: '#E8A317',
    panel: '#FFFFFF', chipBg: '#FFFFFF', chipInk: '#0F1E36', link: '#0B6F93',
  },
};

async function fontsReady(): Promise<void> {
  if (typeof document === 'undefined' || !document.fonts) return;
  try {
    await Promise.all([
      document.fonts.load(`800 120px ${DISPLAY}`),
      document.fonts.load(`700 40px ${UI}`),
      document.fonts.load(`600 40px ${UI}`),
      document.fonts.load(`400 40px ${UI}`),
    ]);
  } catch {
    /* a fallback face is still a readable card */
  }
}

function wrap(ctx: CanvasRenderingContext2D, text: string, width: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = '';
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (ctx.measureText(next).width > width && line) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** Draws wrapped text and returns the y below it. */
function text(
  ctx: CanvasRenderingContext2D, value: string, x: number, y: number, font: string, color: string,
  width = STORY_W - 2 * M, lineHeight = 1.25, align: CanvasTextAlign = 'left',
): number {
  ctx.font = font;
  ctx.fillStyle = color;
  ctx.textAlign = align;
  ctx.textBaseline = 'alphabetic';
  const size = Number(/(\d+)px/.exec(font)?.[1] ?? 40);
  let at = y;
  for (const line of wrap(ctx, value, width)) {
    ctx.fillText(line, x, at);
    at += size * lineHeight;
  }
  ctx.textAlign = 'left';
  return at;
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** The brand's sun and door, as in the app's header. */
function brandMark(ctx: CanvasRenderingContext2D, x: number, y: number, size: number, sun: string, door: string) {
  const s = size / 32;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.beginPath();
  ctx.arc(16, 16, 16, 0, Math.PI * 2);
  ctx.fillStyle = sun;
  ctx.fill();
  ctx.fillStyle = door;
  ctx.fill(new Path2D('M10.5 32V22.5a5.5 5.5 0 0 1 11 0V32Z'));
  ctx.restore();
}

function header(ctx: CanvasRenderingContext2D, model: StoryModel, p: Palette) {
  const y = SAFE_TOP + 24;
  const onSun = model.tone === 'sun';
  brandMark(ctx, M, y - 44, 56, onSun ? '#0F1E36' : '#FFC23D', onSun ? '#FFC23D' : '#0F1E36');
  text(ctx, 'ASHYQ', M + 72, y, `800 44px ${DISPLAY}`, p.ink);
  if (model.who) text(ctx, model.who, STORY_W - M, y, `600 34px ${UI}`, p.muted, 600, 1.25, 'right');
  if (model.demo) {
    // Demo data says so on the card itself, inside the safe area.
    const label = 'DEMO DATA · not real university pages';
    ctx.font = `700 28px ${UI}`;
    const w = ctx.measureText(label).width + 40;
    roundRect(ctx, M, y + 30, w, 52, 26);
    ctx.fillStyle = '#F3E8FF';
    ctx.fill();
    text(ctx, label, M + 20, y + 66, `700 28px ${UI}`, '#6B21A8');
  }
}

interface Frame { cx: number; cy: number; r: number; center: LatLon }

/** The land as dots and the routes from home, clipped to the frame. */
function globe(
  ctx: CanvasRenderingContext2D, f: Frame, dots: Float32Array | null, p: Palette,
  home: LatLon | null, places: LatLon[], clip: [number, number, number, number],
) {
  ctx.save();
  ctx.beginPath();
  ctx.rect(clip[0], clip[1], clip[2] - clip[0], clip[3] - clip[1]);
  ctx.clip();
  ctx.beginPath();
  ctx.arc(f.cx, f.cy, f.r, 0, Math.PI * 2);
  ctx.fillStyle = p.bg === '#0B1628' ? 'rgba(255, 255, 255, 0.04)' : 'rgba(15, 30, 54, 0.04)';
  ctx.fill();
  const lat0 = (f.center.lat * Math.PI) / 180;
  const lon0 = (f.center.lon * Math.PI) / 180;
  const size = Math.max(3, f.r / 110);
  ctx.fillStyle = p.land;
  for (let i = 0; dots && i < dots.length; i += 2) {
    const q = projectRad(dots[i] ?? 0, dots[i + 1] ?? 0, lat0, lon0);
    if (q.z <= 0) continue;
    ctx.globalAlpha = 0.18 + q.z * 0.5;
    ctx.fillRect(f.cx + q.x * f.r - size / 2, f.cy - q.y * f.r - size / 2, size, size);
  }
  ctx.globalAlpha = 1;
  const at = (point: LatLon, lift = 0) => {
    const q = project(point, f.center, lift);
    return { x: f.cx + q.x * f.r, y: f.cy - q.y * f.r, seen: q.z > 0.02 };
  };
  if (home) {
    for (const place of places) {
      if (!at(place).seen) continue;
      ctx.beginPath();
      let pen = false;
      for (const { point, lift } of greatCircle(home, place, 64, 0.14)) {
        const q = project(point, f.center, lift);
        const seen = q.z >= 0 || q.x * q.x + q.y * q.y > 1;
        const x = f.cx + q.x * f.r;
        const y = f.cy - q.y * f.r;
        if (seen && pen) ctx.lineTo(x, y);
        else if (seen) ctx.moveTo(x, y);
        pen = seen;
      }
      ctx.strokeStyle = p.route;
      ctx.lineWidth = 5;
      ctx.stroke();
    }
  }
  // Places closer than a ring's width fold into one disc with their count,
  // as the app's globe does: thirteen rings on one spot read as a smudge.
  const seen = places.map((place) => at(place)).filter((m) => m.seen);
  const groups: { x: number; y: number; n: number }[] = [];
  for (const m of seen) {
    const near = groups.find((g) => Math.hypot(g.x - m.x, g.y - m.y) < 40);
    if (near) {
      near.x = (near.x * near.n + m.x) / (near.n + 1);
      near.y = (near.y * near.n + m.y) / (near.n + 1);
      near.n += 1;
    } else {
      groups.push({ x: m.x, y: m.y, n: 1 });
    }
  }
  for (const g of groups) {
    ctx.beginPath();
    if (g.n >= 3) {
      ctx.arc(g.x, g.y, 34, 0, Math.PI * 2);
      ctx.fillStyle = p.route;
      ctx.fill();
      ctx.lineWidth = 6;
      ctx.strokeStyle = p.bg;
      ctx.stroke();
      text(ctx, String(g.n), g.x, g.y + 12, `800 34px ${DISPLAY}`, '#0F1E36', 80, 1.25, 'center');
    } else {
      ctx.arc(g.x, g.y, 13, 0, Math.PI * 2);
      ctx.fillStyle = p.bg;
      ctx.fill();
      ctx.lineWidth = 7;
      ctx.strokeStyle = p.route;
      ctx.stroke();
    }
  }
  if (home) {
    const h = at(home);
    if (h.seen) {
      ctx.beginPath();
      ctx.arc(h.x, h.y, 14, 0, Math.PI * 2);
      ctx.fillStyle = p.ink;
      ctx.fill();
    }
  }
  ctx.restore();
}

/**
 * What the globe hides, by region: concept N's rule, and defect Q6 ("6
 * programmes", 5 routes), said as chips at the globe's edges.
 */
function hiddenChips(ctx: CanvasRenderingContext2D, f: Frame, places: (LatLon & { country?: string })[], p: Palette) {
  const sides: Record<'left' | 'right', Map<string, number>> = { left: new Map(), right: new Map() };
  for (const place of places) {
    if (project(place, f.center).z > 0.02) continue;
    let d = place.lon - f.center.lon;
    if (d > 180) d -= 360;
    if (d < -180) d += 360;
    const region = REGION_LABEL[regionOf(place.country)];
    const side = d < 0 ? sides.left : sides.right;
    side.set(region, (side.get(region) ?? 0) + 1);
  }
  ctx.font = `700 30px ${UI}`;
  // In the frame's top corners, which the round globe leaves empty; the
  // middle of its rim is where the markers are.
  (['left', 'right'] as const).forEach((side) => {
    let y = f.cy - f.r + 30;
    for (const [region, n] of sides[side]) {
      const label = side === 'left' ? `← ${region} · ${n}` : `${region} · ${n} →`;
      const w = ctx.measureText(label).width + 44;
      const x = side === 'left' ? M - 24 : STORY_W - M + 24 - w;
      roundRect(ctx, x, y - 38, w, 56, 28);
      ctx.fillStyle = p.panel;
      ctx.fill();
      ctx.strokeStyle = 'rgba(15, 30, 54, 0.14)';
      ctx.lineWidth = 2;
      ctx.stroke();
      text(ctx, label, x + 22, y, `700 30px ${UI}`, p.ink);
      y += 68;
    }
  });
}

function route(ctx: CanvasRenderingContext2D, model: StoryModel, p: Palette, dots: Float32Array | null) {
  let y = SAFE_TOP + (model.demo ? 190 : 130);
  y = text(ctx, model.eyebrow.toUpperCase(), M, y, `800 32px ${UI}`, p.accent);
  y += 40;
  // From the country, never the city; the arc between the two names.
  if (model.from) y = text(ctx, model.from, M, y + 60, `800 116px ${DISPLAY}`, p.ink);
  const arcTop = y - 10;
  ctx.setLineDash([2, 18]);
  ctx.lineCap = 'round';
  ctx.lineWidth = 8;
  ctx.strokeStyle = p.accent;
  ctx.beginPath();
  ctx.moveTo(M + 30, arcTop + 10);
  ctx.quadraticCurveTo(STORY_W / 2, arcTop + 150, STORY_W - M - 30, arcTop + 30);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.arc(STORY_W - M - 30, arcTop + 30, 16, 0, Math.PI * 2);
  ctx.lineWidth = 7;
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(M + 30, arcTop + 10, 11, 0, Math.PI * 2);
  ctx.fillStyle = p.accent;
  ctx.fill();
  y = arcTop + 150;
  y = text(ctx, model.to ?? '', STORY_W - M, y + 60, `800 116px ${DISPLAY}`, p.ink, STORY_W - 2 * M, 1.1, 'right');
  y += 30;
  model.lines.forEach((line, i) => {
    y = text(ctx, line, M, y, i === 0 ? `700 44px ${UI}` : `400 38px ${UI}`, i === 0 ? p.ink : p.muted) + 8;
  });
  if (model.chip) {
    ctx.font = `700 32px ${UI}`;
    const lines = wrap(ctx, model.chip, STORY_W - 2 * M - 56);
    const h = lines.length * 42 + 36;
    const w = Math.min(STORY_W - 2 * M, Math.max(...lines.map((l) => ctx.measureText(l).width)) + 56);
    roundRect(ctx, M, y + 10, w, h, 28);
    ctx.fillStyle = p.chipBg;
    ctx.fill();
    lines.forEach((line, i) => text(ctx, line, M + 28, y + 60 + i * 42, `700 32px ${UI}`, p.chipInk));
    y += h + 40;
  }
  ctx.beginPath();
  ctx.arc(M + 8, y + 18, 8, 0, Math.PI * 2);
  ctx.fillStyle = p.link;
  ctx.fill();
  y = text(ctx, model.source, M + 30, y + 30, `600 32px ${UI}`, p.link, STORY_W - 2 * M - 30);

  // The globe on the horizon, with the route from home, below the text: a
  // long grant name pushes it down rather than under the words.
  if (model.globe) {
    const places = model.globe.places;
    const middle = centroidOf([...(model.globe.home ? [model.globe.home] : []), ...places]);
    const top = Math.max(y + 20, SAFE_BOTTOM - 150);
    // The top of a large globe, turned so the route's middle sits just under
    // its rim, where the arc can be seen whole.
    const ends = [...(model.globe.home ? [model.globe.home] : []), ...places];
    // The largest horizon that keeps both ends of the route on the card,
    // turned as high on the rim as it allows: Astana to Groningen fits the
    // big one, Astana to Tokyo runs south and needs a smaller globe.
    const fit = (r: number) => {
      const cy = top + 10 + r;
      const inFrame = (tilt: number) => ends.every((point) => {
        const q = project(point, { lat: middle.lat - tilt, lon: middle.lon });
        const x = STORY_W / 2 + q.x * r;
        const y2 = cy - q.y * r;
        return q.z > 0.05 && x > 60 && x < STORY_W - 60 && y2 > top + 50 && y2 < STORY_H - 70;
      });
      for (let tilt = (Math.asin(Math.min(0.99, (r - 180) / r)) * 180) / Math.PI; tilt >= 0; tilt -= 2) {
        if (inFrame(tilt)) return { cy, r, tilt };
      }
      return null;
    };
    const frame = [760, 640, 540, 460, 400, 340].map(fit).find(Boolean)
      ?? { cy: top + 10 + 340, r: 340, tilt: 0 };
    globe(ctx, { cx: STORY_W / 2, cy: frame.cy, r: frame.r, center: { lat: middle.lat - frame.tilt, lon: middle.lon } },
      dots, p, model.globe.home, places, [0, top, STORY_W, STORY_H]);
  }
}

function requirements(ctx: CanvasRenderingContext2D, model: StoryModel, p: Palette) {
  // Rings in the corner, as in the concept: decoration outside the text.
  ctx.save();
  ctx.strokeStyle = 'rgba(15, 30, 54, 0.07)';
  ctx.lineWidth = 60;
  for (const r of [260, 420, 580]) {
    ctx.beginPath();
    ctx.arc(STORY_W - 60, STORY_H - 200, r, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.restore();

  let y = SAFE_TOP + (model.demo ? 200 : 140);
  ctx.beginPath();
  ctx.arc(M + 64, y + 64, 64, 0, Math.PI * 2);
  ctx.fillStyle = p.ink;
  ctx.fill();
  ctx.strokeStyle = p.bg;
  ctx.lineWidth = 12;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(M + 36, y + 66);
  ctx.lineTo(M + 56, y + 86);
  ctx.lineTo(M + 94, y + 44);
  ctx.stroke();
  y += 200;
  y = text(ctx, model.eyebrow, M, y, `700 38px ${UI}`, p.ink);
  for (const line of model.lines) y = text(ctx, line, M, y, `400 34px ${UI}`, p.muted);
  y += 70;
  for (const line of model.title) y = text(ctx, line, M, y + 20, `800 120px ${DISPLAY}`, p.ink, STORY_W - 2 * M, 1.0);
  y += 20;
  if (model.honesty) y = text(ctx, model.honesty, M, y + 10, `700 36px ${UI}`, p.ink);
  y += 30;
  const rowH = 96;
  const h = model.rows.length * rowH + 24;
  roundRect(ctx, M, y, STORY_W - 2 * M, h, 32);
  ctx.fillStyle = p.panel;
  ctx.fill();
  model.rows.forEach((row, i) => {
    const ry = y + 12 + i * rowH + 60;
    text(ctx, `✓ ${row.label}`, M + 36, ry, `700 36px ${UI}`, p.ink, 480);
    text(ctx, row.detail, STORY_W - M - 36, ry, `400 34px ${UI}`, p.ink, 420, 1.25, 'right');
  });
  y += h + 50;
  text(ctx, model.source, M, y, `400 30px ${UI}`, p.muted);
}

function map(ctx: CanvasRenderingContext2D, model: StoryModel, p: Palette, dots: Float32Array | null) {
  // Laid out from the bottom of the safe area up, so the deadline and the
  // source never slide under the brand band.
  ctx.font = `400 30px ${UI}`;
  const sourceLines = wrap(ctx, model.source, STORY_W - 2 * M).length;
  const sourceY = SAFE_BOTTOM - 10 - (sourceLines - 1) * 38;
  const noteY = model.note ? sourceY - 56 : sourceY;
  const statsY = noteY - 110;
  let y = SAFE_TOP + (model.demo ? 190 : 130);
  for (const line of model.title) y = text(ctx, line, M, y + 30, `800 92px ${DISPLAY}`, p.ink, STORY_W - 2 * M, 1.05);
  const home = model.globe?.home ?? null;
  const places = model.globe?.places ?? [];
  const room = statsY - 110 - y;
  const r = Math.min(330, room / 2 - 20);
  const f: Frame = { cx: STORY_W / 2, cy: y + 20 + r, r, center: { lat: 30, lon: home ? home.lon - 20 : 20 } };
  globe(ctx, f, dots, p, home, places, [0, y, STORY_W, f.cy + f.r + 10]);
  hiddenChips(ctx, f, places, p);
  const colW = (STORY_W - 2 * M) / Math.max(3, model.stats.length);
  model.stats.forEach((s, i) => {
    text(ctx, s.value, M + i * colW, statsY - 40, `800 104px ${DISPLAY}`, p.ink, colW);
    text(ctx, s.label, M + i * colW, statsY + 8, `600 32px ${UI}`, p.muted, colW - 20);
  });
  if (model.note) text(ctx, model.note, M, noteY, `700 36px ${UI}`, p.ink);
  text(ctx, model.source, M, sourceY, `400 30px ${UI}`, p.muted);
  // The brand band, in the reply-bar zone where nothing needs reading.
  ctx.fillStyle = '#0F1E36';
  ctx.fillRect(0, STORY_H - 230, STORY_W, 230);
  ctx.font = `800 48px ${DISPLAY}`;
  const brandW = ctx.measureText('ASHYQ Apply').width;
  const bx = (STORY_W - brandW - 76) / 2;
  brandMark(ctx, bx, STORY_H - 150, 60, '#FFC23D', '#0F1E36');
  text(ctx, 'ASHYQ Apply', bx + 76, STORY_H - 102, `800 48px ${DISPLAY}`, '#FFFFFF', 600);
}

/** Draws the card; resolves once fonts and land dots are in. */
export async function drawStory(canvas: HTMLCanvasElement, model: StoryModel): Promise<void> {
  const ctx = canvas.getContext?.('2d');
  if (!ctx) return;
  await fontsReady();
  const dots = model.globe ? await loadLandDots().catch(() => null) : null;
  canvas.width = STORY_W;
  canvas.height = STORY_H;
  const p = PALETTES[model.tone];
  ctx.fillStyle = p.bg;
  ctx.fillRect(0, 0, STORY_W, STORY_H);
  header(ctx, model, p);
  if (model.kind === 'route') route(ctx, model, p, dots);
  else if (model.kind === 'requirements') requirements(ctx, model, p);
  else map(ctx, model, p, dots);
}

/** The card as a PNG file, for the share sheet or a download. */
export function storyFile(canvas: HTMLCanvasElement, name: string): Promise<File | null> {
  return new Promise((resolve) => {
    if (typeof canvas.toBlob !== 'function') {
      resolve(null);
      return;
    }
    canvas.toBlob((blob) => resolve(blob ? new File([blob], name, { type: 'image/png' }) : null), 'image/png');
  });
}

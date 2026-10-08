/**
 * The landing's scroll story (docs/design/redesign-concepts.md §33; source
 * docs/design/landing/landing_concept.py, approved as a video concept).
 *
 * One sticky stage, scrubbed by scroll: the track's height is the distance,
 * and a smoothed playhead follows the scroll both ways. It is drawn live on a
 * canvas rather than played from a video, because every frame is our own
 * globe and our own numbers - there is no footage to make:
 *
 *   0.00-0.18  the question, over a turning night globe with Astana lit
 *   0.18-0.44  routes leave Astana one by one, each in its country's tint
 *   0.44-0.62  the globe rises and dims; three passes fly in and stack
 *   0.62-0.82  the top pass opens a line at a time: price, grant, what is left
 *   0.82-1.00  the three separate answers, the source line, the way in
 *
 * Honesty (review I105-I107): no figure is counted up or down - every number
 * shown is one a page states; the pass says it is an example from demo data;
 * "if awarded" stays next to the price; nothing is a chance.
 *
 * Still (reduced motion, or a screen too short to stack the last scene - a
 * phone held sideways): nothing scrubs. The question, the opened pass with
 * all its lines and the way in stand in the page's flow over the globe.
 *
 * Scenes fade by opacity only, so a screen reader reads the whole story in
 * order wherever the page is scrolled. The loop runs only while the stage is
 * on screen and the playhead is still moving.
 */

import { useEffect, useRef } from 'react';
import { greatCircle, loadLandDots, project, type LatLon } from '@/lib/globe';

const HOME: LatLon = { lat: 51.17, lon: 71.45 };
/** Six of the demo run's routes; the slot is the country's pass colour. */
const ROUTES: { city: string; at: LatLon; slot: number }[] = [
  { city: 'Groningen', at: { lat: 53.2, lon: 6.6 }, slot: 1 },
  { city: 'Leuven', at: { lat: 50.9, lon: 4.7 }, slot: 2 },
  { city: 'Vienna', at: { lat: 48.2, lon: 16.4 }, slot: 8 },
  { city: 'Tokyo', at: { lat: 35.7, lon: 139.7 }, slot: 3 },
  { city: 'Singapore', at: { lat: 1.35, lon: 103.8 }, slot: 7 },
  { city: 'Toronto', at: { lat: 43.7, lon: -79.4 }, slot: 5 },
];

/** Where the story stops scrubbing and stands still; landing.css has the same query. */
export const STILL = '(prefers-reduced-motion: reduce), (max-height: 639px)';

/** The concept's dot spacing on the globe, about 2.2 degrees (some 1,900 dots of land). */
const SPACING = 0.039;

const clamp = (x: number) => Math.max(0, Math.min(1, x));
const seg = (p: number, a: number, b: number) => clamp((p - a) / (b - a));
const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export function LandingStory() {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const track = root.current;
    if (!track) return undefined;
    const canvas = track.querySelector<HTMLCanvasElement>('canvas');
    const ctx = canvas?.getContext?.('2d');
    if (!canvas || !ctx) return undefined; // jsdom: the words still read
    const el = (name: string) => track.querySelector<HTMLElement>(`[data-ls="${name}"]`);
    const css = getComputedStyle(track);
    // What does not change with the scroll, worked out once: the routes' arcs
    // and tints, and each land dot's own trigonometry.
    const tints = ROUTES.map(({ slot }) => css.getPropertyValue(`--pass-tint-${slot}`).trim() || '#9DBAD3');
    const arcs = ROUTES.map(({ at }) => greatCircle(HOME, at, 64, 0.22));
    const stillQuery = typeof window.matchMedia === 'function' ? window.matchMedia(STILL) : null;
    let still = Boolean(stillQuery?.matches);

    let W = 0;
    let H = 0;
    let dpr = 1;
    /** Per dot: sin and cos of its latitude, then of its longitude. */
    let land: Float32Array | null = null;
    let bands: Float32Array[] = [];
    const prepare = (dots: Float32Array) => {
      // The app's land is four times as dense as the approved concept's; keep
      // a dot only if none kept lies within SPACING (radians on the sphere).
      const kept: number[] = [];
      const cells = new Map<string, number[]>();
      const cell = (v: number) => Math.floor(v / SPACING);
      for (let i = 0; i < dots.length; i += 2) {
        const lat = dots[i] ?? 0;
        const lon = dots[i + 1] ?? 0;
        const x = Math.cos(lat) * Math.cos(lon);
        const y = Math.cos(lat) * Math.sin(lon);
        const z = Math.sin(lat);
        const [cx, cy, cz] = [cell(x), cell(y), cell(z)];
        let near = false;
        for (let dx = -1; dx <= 1 && !near; dx += 1) {
          for (let dy = -1; dy <= 1 && !near; dy += 1) {
            for (let dz = -1; dz <= 1 && !near; dz += 1) {
              const there = cells.get(`${cx + dx},${cy + dy},${cz + dz}`) ?? [];
              for (let k = 0; k < there.length && !near; k += 3) {
                near = ((there[k] ?? 0) - x) ** 2 + ((there[k + 1] ?? 0) - y) ** 2 + ((there[k + 2] ?? 0) - z) ** 2 < SPACING ** 2;
              }
            }
          }
        }
        if (near) continue;
        const key = `${cx},${cy},${cz}`;
        cells.set(key, [...(cells.get(key) ?? []), x, y, z]);
        kept.push(lat, lon);
      }
      const n = kept.length >> 1;
      const t = new Float32Array(n * 4);
      for (let i = 0; i < n; i += 1) {
        const lat = kept[2 * i] ?? 0;
        const lon = kept[2 * i + 1] ?? 0;
        t[4 * i] = Math.sin(lat);
        t[4 * i + 1] = Math.cos(lat);
        t[4 * i + 2] = Math.sin(lon);
        t[4 * i + 3] = Math.cos(lon);
      }
      bands = [0, 1, 2].map(() => new Float32Array(n * 2));
      land = t;
    };
    // Once the globe holds still (the late scenes), the disc and its land are
    // kept on a layer of their own and reused frame after frame.
    const layer = document.createElement('canvas');
    const lctx = layer.getContext('2d');
    let layerKey = '';
    let lastKey = '';
    const size = () => {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const SHADES = ['#3A3A46', '#55556A', '#7A7A90'];
    const paintLand = (g: CanvasRenderingContext2D, cx: number, cy: number, R: number, center: LatLon, dim: number) => {
      const disc = g.createRadialGradient(cx, cy - R * 0.4, R * 0.1, cx, cy, R);
      disc.addColorStop(0, '#20202A');
      disc.addColorStop(1, '#101014');
      g.globalAlpha = 1;
      g.fillStyle = disc;
      g.beginPath();
      g.arc(cx, cy, R, 0, Math.PI * 2);
      g.fill();
      g.strokeStyle = 'rgba(255,255,255,.08)';
      g.lineWidth = 1;
      g.stroke();
      if (!land) return;
      // The land in three depth bands, one colour each: no trigonometry per
      // dot (angle addition on the sines kept from prepare), one fill style per band.
      const lat0 = (center.lat * Math.PI) / 180;
      const lon0 = (center.lon * Math.PI) / 180;
      const sLat0 = Math.sin(lat0);
      const cLat0 = Math.cos(lat0);
      const sLon0 = Math.sin(lon0);
      const cLon0 = Math.cos(lon0);
      const count = [0, 0, 0];
      for (let i = 0; i < land.length; i += 4) {
        const sLat = land[i] ?? 0;
        const cLat = land[i + 1] ?? 0;
        const sLon = land[i + 2] ?? 0;
        const cLon = land[i + 3] ?? 0;
        const cosDl = cLon * cLon0 + sLon * sLon0;
        const z = sLat0 * sLat + cLat0 * cLat * cosDl;
        if (z <= 0.02) continue;
        const x = cx + cLat * (sLon * cLon0 - cLon * sLon0) * R;
        const y = cy - (cLat0 * sLat - sLat0 * cLat * cosDl) * R;
        if (y < -4 || y > H + 4 || x < -4 || x > W + 4) continue;
        const b = z > 0.55 ? 2 : z > 0.25 ? 1 : 0;
        const band = bands[b];
        if (!band) continue;
        band[count[b]!] = x;
        band[count[b]! + 1] = y;
        count[b]! += 2;
      }
      g.globalAlpha = dim;
      bands.forEach((band, b) => {
        g.fillStyle = SHADES[b] ?? '#3A3A46';
        g.beginPath();
        const n = count[b] ?? 0;
        for (let i = 0; i < n; i += 2) g.rect((band[i] ?? 0) - 1.2, (band[i + 1] ?? 0) - 1.2, 2.4, 2.4);
        g.fill();
      });
      g.globalAlpha = 1;
    };

    const draw = (p: number, now: number) => {
      ctx.clearRect(0, 0, W, H);
      const wide = W >= 900;
      const rise = ease(seg(p, 0.44, 0.6));
      const R0 = wide ? Math.min(W, H) * 0.52 : Math.min(W, H) * 0.62;
      const R = lerp(R0, R0 * 0.78, rise);
      const cx = wide ? lerp(W * 0.36, W * 0.3, rise) : W / 2;
      const cy = lerp(H * (wide ? 0.78 : 0.86), H * (wide ? 0.55 : 0.42), rise);
      const center: LatLon = { lat: 34, lon: lerp(20, 58, ease(seg(p, 0, 0.44))) };
      const dim = 1 - 0.55 * rise;

      const key = [W, H, center.lon.toFixed(3), R.toFixed(2), cx.toFixed(2), cy.toFixed(2), land ? 1 : 0].join('|');
      const moving = key !== lastKey;
      lastKey = key;
      if (!lctx || moving) {
        // Turning or rising: straight onto the stage, no layer to keep up.
        paintLand(ctx, cx, cy, R, center, dim);
      } else {
        if (key !== layerKey) {
          if (layer.width !== canvas.width || layer.height !== canvas.height) {
            layer.width = canvas.width;
            layer.height = canvas.height;
          }
          lctx.setTransform(dpr, 0, 0, dpr, 0, 0);
          lctx.clearRect(0, 0, W, H);
          paintLand(lctx, cx, cy, R, center, dim);
          layerKey = key;
        }
        ctx.globalAlpha = 1;
        ctx.drawImage(layer, 0, 0, W, H);
      }

      // The routes, one at a time.
      arcs.forEach((path, i) => {
        const t = ease(seg(p, 0.2 + i * 0.035, 0.3 + i * 0.035));
        if (t <= 0) return;
        const upto = Math.max(1, Math.round(path.length * t));
        ctx.beginPath();
        let pen = false;
        let end: { x: number; y: number; z: number } | null = null;
        for (const { point, lift } of path.slice(0, upto)) {
          const v = project(point, center, lift);
          if (v.z < -0.15) { pen = false; continue; }
          const x = cx + v.x * R;
          const y = cy - v.y * R;
          if (pen) ctx.lineTo(x, y); else ctx.moveTo(x, y);
          pen = true;
          end = { x, y, z: v.z };
        }
        ctx.globalAlpha = dim;
        ctx.strokeStyle = tints[i] ?? '#9DBAD3';
        ctx.lineWidth = 2.4;
        ctx.lineCap = 'round';
        ctx.stroke();
        if (t >= 1 && end && end.z > 0) {
          ctx.fillStyle = tints[i] ?? '#9DBAD3';
          ctx.beginPath();
          ctx.arc(end.x, end.y, 5, 0, Math.PI * 2);
          ctx.fill();
        }
      });

      // Home.
      const h = project(HOME, center);
      if (h.z > 0) {
        const hx = cx + h.x * R;
        const hy = cy - h.y * R;
        const pulse = still || now < 0 ? 12 : 10 + 6 * Math.sin(now / 380);
        ctx.globalAlpha = dim * 0.35;
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(hx, hy, pulse, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = dim;
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.arc(hx, hy, 6.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.font = '700 10.5px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('ASTANA', hx, hy + 24);
      }
      ctx.globalAlpha = 1;
    };

    // Opacity only: a faded scene stays in the reading order, and only the
    // scene in view takes a tap.
    const fade = (node: HTMLElement | null, a: number) => {
      if (!node) return;
      node.style.opacity = String(a);
      node.style.transform = `translateY(${(1 - a) * 18}px)`;
      node.style.pointerEvents = a < 0.5 ? 'none' : 'auto';
    };
    const MOVED = ['opacity', 'transform', 'pointer-events', 'max-height', 'padding-top', 'padding-bottom', 'border-top-color'];
    const settle = () => {
      track.querySelectorAll<HTMLElement>('[data-ls]').forEach((node) => MOVED.forEach((k) => node.style.removeProperty(k)));
      const big = el('big');
      const bigsub = el('bigsub');
      if (big && bigsub) {
        big.textContent = '1,848';
        bigsub.textContent = 'USD a year left, if awarded';
        (big.parentElement as HTMLElement).style.removeProperty('opacity');
      }
    };

    // Where each scene's words end and how tall the pass is, so the cards
    // stack under the words on any height instead of at fixed fractions.
    const m = { mid: 0, end: 0, pass: 150, cta: 0 };
    const bottom = (name: string) => {
      const node = el(name);
      return node ? node.offsetTop + node.offsetHeight : 0;
    };
    const measure = () => {
      m.mid = Math.max(bottom('s3'), bottom('s4'));
      m.end = bottom('s5');
      m.pass = el('pass-nl')?.offsetHeight || 150;
      m.cta = el('s6')?.offsetTop || H;
    };

    const layout = (p: number) => {
      const wide = W >= 900;
      // Read before this frame writes anything: last frame's layout is clean.
      const sheet = el('sheet');
      const sheetNow = sheet?.offsetHeight ?? 0;
      fade(el('s1'), 1 - seg(p, 0.11, 0.17));
      fade(el('s2'), Math.min(seg(p, 0.16, 0.22), 1 - seg(p, 0.41, 0.46)));
      fade(el('s3'), Math.min(seg(p, 0.46, 0.5), 1 - seg(p, 0.6, 0.64)));
      fade(el('s4'), Math.min(seg(p, 0.64, 0.68), 1 - seg(p, 0.8, 0.84)));
      fade(el('s5'), seg(p, 0.84, 0.88));
      const hint = el('hint');
      if (hint) hint.style.opacity = String(1 - seg(p, 0.02, 0.08));

      // The passes fly in and stack; the other two leave when the top one opens.
      const fin = ease(seg(p, 0.84, 0.9));
      // 26 px: the back pass sits that far above the front one.
      const mid = Math.max(wide ? H * 0.3 : H * 0.42, m.mid + 44);
      const base = lerp(mid, wide ? Math.max(H * 0.3, m.end + 16) : m.end + 12, fin);
      const open = ease(seg(p, 0.62, 0.7));
      ([['pass-jp', 0, 26, 5], ['pass-be', 1, 13, -4], ['pass-nl', 2, 0, 0]] as const).forEach(([name, i, off, rot]) => {
        const node = el(name);
        if (!node) return;
        const t = ease(seg(p, 0.48 + i * 0.03, 0.58 + i * 0.03));
        const top = name === 'pass-nl';
        const y = lerp(H + 40, base - off * (1 - open * (top ? 0 : -1)), t);
        const r = lerp(rot * 3, top ? 0 : rot, t);
        const a = top ? t : t * (1 - open);
        node.style.opacity = String(a);
        node.style.transform = `translateY(${y}px) rotate(${r}deg)`;
      });

      // The top pass: the price, then - once the total row is there - what is
      // left. No figure in between: every number shown is one a page states.
      const g = ease(seg(p, 0.77, 0.8));
      const big = el('big');
      const bigsub = el('bigsub');
      if (big && bigsub) {
        big.textContent = g < 0.5 ? '32,663' : '1,848';
        bigsub.textContent = g < 0.5 ? 'USD a year, price' : 'USD a year left, if awarded';
        (big.parentElement as HTMLElement).style.opacity = String(g > 0 && g < 1 ? Math.abs(2 * g - 1) : 1);
      }

      if (sheet) {
        // Under the pass; on a short screen it rises over the pass's lower
        // edge rather than run into the way in - never above the city and price.
        const floor = lerp(H - 16, wide ? H - 16 : m.cta - 12, fin);
        const sTop = Math.max(base + 72, Math.min(base + m.pass + 8, floor - sheetNow));
        const so = ease(seg(p, 0.64, 0.7));
        const a = seg(p, 0.64, 0.655);
        sheet.style.opacity = String(a);
        sheet.style.transform = `translateY(${lerp(sTop + 40, sTop, so)}px)`;
      }
      // The sheet grows a line at a time instead of opening empty.
      ([['r1', 0.645], ['r2', 0.71], ['r3', 0.77]] as const).forEach(([name, at]) => {
        const node = el(name);
        if (!node) return;
        const t = seg(p, at, at + 0.03);
        // On a phone the arithmetic gives way to the three answers; the total stays.
        const keep = !wide && name !== 'r3' ? 1 - fin : 1;
        fade(node, Math.min(t, keep));
        node.style.maxHeight = `${80 * Math.min(t, keep)}px`;
        node.style.paddingTop = node.style.paddingBottom = `${10 * Math.min(t, keep)}px`;
      });
      const r3 = el('r3');
      if (r3) r3.style.borderTopColor = !wide && fin > 0.5 ? 'transparent' : '';
      const answers = el('answers');
      if (answers) {
        const t = seg(p, 0.86, 0.9);
        answers.style.maxHeight = `${200 * t}px`;
        fade(answers, t);
      }
      fade(el('s6'), seg(p, 0.92, 0.96));
    };

    const progress = () => {
      const box = track.getBoundingClientRect();
      const distance = track.offsetHeight - window.innerHeight;
      return distance > 0 ? clamp(-box.top / distance) : 1;
    };

    let target = progress();
    let current = target;
    let last = performance.now();
    let frame = 0;
    let onScreen = true;
    const paint = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      current += (target - current) * (1 - Math.exp(-dt * 9));
      draw(current, now);
      layout(current);
    };
    // Settled, the loop stops (the home ring stops pulsing with it); a scroll starts it again.
    const loop = (now: number) => {
      paint(now);
      if (Math.abs(target - current) < 0.0005) {
        current = target;
        draw(current, -1);
        layout(current);
        frame = 0;
        return;
      }
      frame = onScreen && !still ? requestAnimationFrame(loop) : 0;
    };
    const start = (snap = false) => {
      if (still || frame || !onScreen) return;
      last = performance.now();
      target = progress();
      if (snap) current = target;
      frame = requestAnimationFrame(loop);
    };
    // Still: every route drawn, the globe not yet risen, the pass as CSS lays it out.
    const stand = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      settle();
      draw(0.48, 0);
    };
    const resize = () => {
      size();
      measure();
      if (still) stand();
      else if (!frame) {
        draw(current, -1);
        layout(current);
      }
    };
    const onScroll = () => {
      target = progress();
      start();
    };
    const onMode = () => {
      still = Boolean(stillQuery?.matches);
      resize();
      if (!still) start();
    };

    resize();
    if (!still) layout(current);
    loadLandDots().then((d) => {
      prepare(d);
      if (still) draw(0.48, 0);
      else if (!frame) draw(current, -1);
    }).catch(() => undefined);
    document.fonts?.ready.then(resize).catch(() => undefined);

    const watch = typeof IntersectionObserver === 'function'
      ? new IntersectionObserver(([entry]) => {
        onScreen = Boolean(entry?.isIntersecting);
        // Back on screen from far away: start where the page is, not where it was.
        if (onScreen) start(true);
      })
      : null;
    watch?.observe(track);
    start();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', resize);
    stillQuery?.addEventListener?.('change', onMode);
    return () => {
      cancelAnimationFrame(frame);
      watch?.disconnect();
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', resize);
      stillQuery?.removeEventListener?.('change', onMode);
    };
  }, []);

  return (
    <div className="ls" ref={root} data-testid="landing-story">
      <div className="ls__stage">
        <canvas className="ls__globe" aria-hidden="true" />

        <section className="ls__layer" data-ls="s1" aria-labelledby="landing-title">
          <p className="ls__eb ls__eb--1">Study abroad, read for you</p>
          <h1 className="ls__h1" id="landing-title">Where can you study — and what will it cost?</h1>
          <p className="ls__sub">We read the official pages, and every fact keeps its source and the date it was read.</p>
        </section>
        <section className="ls__layer" data-ls="s2">
          <p className="ls__eb ls__eb--2">From your city</p>
          <h2 className="ls__h1">From Astana to 15 countries</h2>
          <p className="ls__sub">In the demo run, 20 programmes for one applicant from Astana. Six of the routes are drawn here.</p>
        </section>
        <section className="ls__layer" data-ls="s3">
          <p className="ls__eb ls__eb--3">Each programme, a pass</p>
          <h2 className="ls__h1">One card per programme, in its country&apos;s colour</h2>
        </section>
        <section className="ls__layer" data-ls="s4">
          <p className="ls__eb ls__eb--4">The price that matters</p>
          <h2 className="ls__h1">What is left to pay — and the word <i>if</i> stays</h2>
        </section>
        <section className="ls__layer ls__layer--tight" data-ls="s5">
          <p className="ls__eb ls__eb--5">Requirements · profile · money</p>
          <h2 className="ls__h1 ls__h1--sm">Three answers, never one score</h2>
        </section>

        <div className="ls__pass" data-ls="pass-jp" style={{ ['--pass' as string]: 'var(--pass-3)' }} aria-hidden="true">
          <p className="ls__c">JAPAN</p><p className="ls__n">Tokyo</p><p className="ls__s">University of Tokyo · PEAK</p>
          <p className="ls__p"><b>1,986</b><span>USD a year, if awarded</span></p>
        </div>
        <div className="ls__pass" data-ls="pass-be" style={{ ['--pass' as string]: 'var(--pass-2)' }} aria-hidden="true">
          <p className="ls__c">BELGIUM</p><p className="ls__n">Leuven</p><p className="ls__s">KU Leuven · BSc Informatics</p>
          <p className="ls__p"><b>7,554</b><span>USD a year, if awarded</span></p>
        </div>
        <div className="ls__card">
          <div className="ls__pass" data-ls="pass-nl" style={{ ['--pass' as string]: 'var(--pass-1)' }}>
            <p className="ls__c">NETHERLANDS · FALL 2027</p><p className="ls__n">Groningen</p>
            <p className="ls__s">University of Groningen · BSc Computing Science</p>
            {/* It changes with the scroll; the lines below read the same figures in order. */}
            <p className="ls__p" aria-hidden="true"><b data-ls="big">32,663</b><span data-ls="bigsub">USD a year, price</span></p>
            <span className="ls__demo">Example · demo data</span>
          </div>

          <div className="ls__sheet" data-ls="sheet">
            <div className="ls__row" data-ls="r1"><span><b>Price a year</b><small>tuition, housing, living, fees</small></span><b>32,663</b></div>
            <div className="ls__row" data-ls="r2"><span><b>Groningen Talent Grant</b><small>competitive · if awarded</small></span><b className="ls__minus">− 30,815</b></div>
            <div className="ls__row ls__row--total" data-ls="r3"><span><b>Left to pay a year</b><small>if the grant is awarded</small></span><b>1,848</b></div>
            <div className="ls__answers" data-ls="answers">
              <p className="ls__j"><em>Requirements</em><i className="tone-warn">Pending</i>waiting on minimum GPA</p>
              <p className="ls__j"><em>Your profile</em><i className="tone-info">Stronger</i>above the minimums</p>
              <p className="ls__j"><em>Money</em><i className="tone-info">Competitive</i>Talent Grant, if awarded</p>
              <p className="ls__src">rug.nl · demo fixture · read Oct 05</p>
            </div>
          </div>
        </div>

        <div className="ls__layer ls__layer--bottom" data-ls="s6">
          <a className="ls__cta" href="#/sign-in?create=1">Start with your profile <span aria-hidden="true">→</span></a>
          <p className="ls__fine">Free to start. None of this predicts an admission decision — that is the university&apos;s.</p>
        </div>
        <p className="ls__hint" data-ls="hint" aria-hidden="true">Scroll</p>
      </div>
    </div>
  );
}

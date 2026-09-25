/**
 * The globe: the land as dots, the applicant's home, the programmes at their
 * cities, and the routes between them (round 7, concepts M and N).
 *
 * Built for a budget Android phone, where the list stays the main path:
 * - one <canvas> for the dots and the routes, drawn only when something
 *   changes - there is no animation loop while it is still;
 * - the programme markers are ordinary buttons over it, but hidden from the
 *   keyboard and screen readers, because every one of them is a card in the
 *   list below; the figure's caption says what the globe shows instead;
 * - turning to a region eases over 650 ms, or jumps under reduced motion.
 *
 * Every point is a fact: a result at its city from a checked table, home at
 * the capital of the country of residence. Nothing is placed by guess.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  greatCircle, interpolateCenter, isVisible, loadLandDots, project, projectRad, type LatLon,
} from '@/lib/globe';

export interface GlobeMarker extends LatLon {
  id: string;
  /** Shown beside the marker when it is the selected one. */
  label: string;
}

export interface GlobeProps {
  markers: GlobeMarker[];
  home?: (LatLon & { city: string }) | null;
  /** The place to bring into the middle of the visible part. */
  focus: LatLon;
  /** Day on a light page; night inside the navy panels. */
  tone: 'day' | 'night';
  /** Horizon: the top of a large globe rising from the bottom. Band: most of a smaller one. */
  layout: 'horizon' | 'band';
  height: number;
  /** Bring the globe closer: a region's cities spread apart instead of overlapping. */
  zoom?: number;
  routes?: boolean;
  selected?: string | null;
  onSelect?: (id: string) => void;
  /** What the globe shows, for a screen reader. */
  caption: string;
  testId?: string;
}

interface Geometry {
  width: number;
  height: number;
  radius: number;
  cx: number;
  cy: number;
  /** Where the focus should land, as a fraction of the height from the top. */
  focusY: number;
}

function geometryOf(layout: GlobeProps['layout'], width: number, height: number, zoom = 1): Geometry {
  if (layout === 'horizon') {
    const radius = Math.max(200, Math.min(560, width * 0.52));
    const cap = height * 0.94;
    return { width, height, radius, cx: width / 2, cy: height - cap + radius, focusY: 0.5 };
  }
  const base = Math.max(110, Math.min(width * 0.36, height * 0.72));
  const radius = base * zoom;
  // Zoomed in, the centre drops so the region stays in the band.
  return { width, height, radius, cx: width / 2, cy: height * 0.5 + base * 0.3 + (radius - base) * 0.6, focusY: 0.46 };
}

/** The view centre that puts `focus` at the geometry's focus height. */
function viewCenter(focus: LatLon, g: Geometry): LatLon {
  const yUnit = (g.cy - g.focusY * g.height) / g.radius;
  const dLat = (Math.asin(Math.max(-0.95, Math.min(0.95, yUnit))) * 180) / Math.PI;
  return { lat: Math.max(-80, Math.min(80, focus.lat - dLat)), lon: focus.lon };
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function cssVar(el: Element, name: string, fallback: string): string {
  const value = getComputedStyle(el).getPropertyValue(name).trim();
  return value || fallback;
}

function draw(
  canvas: HTMLCanvasElement, g: Geometry, center: LatLon, props: GlobeProps, dots: Float32Array | null,
) {
  const ctx = canvas.getContext?.('2d');
  if (!ctx) return; // jsdom, or a browser without canvas: the list still works
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  if (canvas.width !== Math.round(g.width * dpr) || canvas.height !== Math.round(g.height * dpr)) {
    canvas.width = Math.round(g.width * dpr);
    canvas.height = Math.round(g.height * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, g.width, g.height);

  const land = cssVar(canvas, '--globe-land', '#9aa6b8');
  const sea = cssVar(canvas, '--globe-sea', 'transparent');
  const limb = cssVar(canvas, '--globe-limb', 'rgba(0,0,0,0.1)');
  const route = cssVar(canvas, '--globe-route', '#E8A317');
  const homeInk = cssVar(canvas, '--globe-home', '#0F1E36');

  // The sphere.
  ctx.beginPath();
  ctx.arc(g.cx, g.cy, g.radius, 0, Math.PI * 2);
  ctx.fillStyle = sea;
  ctx.fill();
  ctx.lineWidth = 1;
  ctx.strokeStyle = limb;
  ctx.stroke();

  // The land: four passes by depth, so the edge fades without a per-dot alpha.
  const lat0 = (center.lat * Math.PI) / 180;
  const lon0 = (center.lon * Math.PI) / 180;
  const size = Math.max(1.2, Math.min(2.6, g.radius / 170));
  const buckets: number[][] = [[], [], [], []];
  for (let i = 0; dots && i < dots.length; i += 2) {
    const p = projectRad(dots[i] ?? 0, dots[i + 1] ?? 0, lat0, lon0);
    if (p.z <= 0) continue;
    const x = g.cx + p.x * g.radius;
    const y = g.cy - p.y * g.radius;
    if (x < -2 || y < -2 || x > g.width + 2 || y > g.height + 2) continue;
    const bucket = buckets[Math.min(3, Math.floor(p.z * 4))];
    bucket?.push(x, y);
  }
  ctx.fillStyle = land;
  buckets.forEach((points, depth) => {
    ctx.globalAlpha = 0.28 + depth * 0.22;
    for (let i = 0; i < points.length; i += 2) {
      ctx.fillRect((points[i] ?? 0) - size / 2, (points[i + 1] ?? 0) - size / 2, size, size);
    }
  });
  ctx.globalAlpha = 1;

  // Routes from home to the programmes on this side of the globe; a route to
  // a city out of sight would only be a line into empty space.
  if (props.routes && props.home) {
    const lift = props.layout === 'horizon' ? 0.07 : 0.14;
    for (const m of props.markers) {
      if (project(m, center).z <= 0.02) continue;
      const path = greatCircle(props.home, m, 48, lift);
      const on = props.selected === m.id;
      ctx.beginPath();
      let pen = false;
      for (const { point, lift } of path) {
        const p = project(point, center, lift);
        const seen = p.z >= 0 || p.x * p.x + p.y * p.y > 1;
        const x = g.cx + p.x * g.radius;
        const y = g.cy - p.y * g.radius;
        if (seen && pen) ctx.lineTo(x, y);
        else if (seen) ctx.moveTo(x, y);
        pen = seen;
      }
      ctx.lineWidth = on ? 2.5 : 1.4;
      ctx.strokeStyle = route;
      ctx.globalAlpha = on ? 1 : props.selected ? 0.35 : 0.75;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  // Home.
  if (props.home) {
    const p = project(props.home, center);
    if (isVisible(p)) {
      const x = g.cx + p.x * g.radius;
      const y = g.cy - p.y * g.radius;
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = homeInk;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, 8.5, 0, Math.PI * 2);
      ctx.strokeStyle = homeInk;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
  }
}

const MARKER_GAP = 22;

/**
 * Nudges a marker that sits on top of another, so every one can be tapped:
 * Toronto and Montreal are 500 km apart, a marker's width at this scale.
 * The nudge is a few pixels round the true place, never across a region.
 */
function declutter<T extends { x: number; y: number }>(points: T[]): T[] {
  const out: T[] = [];
  for (const point of points) {
    let { x, y } = point;
    for (let attempt = 0; attempt < 6; attempt += 1) {
      const clash = out.find((o) => Math.hypot(o.x - x, o.y - y) < MARKER_GAP);
      if (!clash) break;
      const angle = (attempt * Math.PI) / 3 + Math.PI / 6;
      x = point.x + Math.cos(angle) * MARKER_GAP;
      y = point.y + Math.sin(angle) * MARKER_GAP;
    }
    out.push({ ...point, x, y });
  }
  return out;
}

export function Globe(props: GlobeProps) {
  const { markers, home, focus, tone, layout, height, zoom = 1, selected, onSelect, caption, testId } = props;
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [width, setWidth] = useState(360);
  // The zoom eases with the turn, so a region chip reads as one movement.
  const [shownZoom, setShownZoom] = useState(zoom);
  const g = useMemo(() => geometryOf(layout, width, height, shownZoom), [layout, width, height, shownZoom]);
  // Keyed on the numbers, not the object: a caller that builds a new focus on
  // every render must not restart the turn - that looped, redrawing the reveal
  // twenty times a second while it sat still.
  const target = useMemo(
    () => viewCenter({ lat: focus.lat, lon: focus.lon }, geometryOf(layout, width, height, zoom)),
    [focus.lat, focus.lon, layout, width, height, zoom],
  );
  const [center, setCenter] = useState<LatLon>(target);
  const centerRef = useRef(center);
  centerRef.current = center;
  const [themeTick, setThemeTick] = useState(0);
  const [dots, setDots] = useState<Float32Array | null>(null);

  useEffect(() => {
    let live = true;
    loadLandDots().then((loaded) => { if (live) setDots(loaded); }).catch(() => {});
    return () => { live = false; };
  }, []);

  // Width follows the container.
  useEffect(() => {
    const el = wrap.current;
    if (!el) return undefined;
    const measure = () => { if (el.clientWidth > 0) setWidth(el.clientWidth); };
    measure();
    if (typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Colours come from CSS; redraw when the appearance changes.
  useEffect(() => {
    const bump = () => setThemeTick((n) => n + 1);
    const media = typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    media?.addEventListener?.('change', bump);
    const observer = typeof MutationObserver === 'undefined' ? null : new MutationObserver(bump);
    observer?.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => { media?.removeEventListener?.('change', bump); observer?.disconnect(); };
  }, []);

  // Turning: ease to the new centre and zoom, or jump when motion is reduced.
  const zoomRef = useRef(shownZoom);
  zoomRef.current = shownZoom;
  // Only a new focus or zoom is a turn worth watching; a new width (the first
  // measurement, a rotated phone) moves the view at once. Animating that made
  // every globe spin for 650 ms as it appeared.
  const asked = useRef({ lat: focus.lat, lon: focus.lon, zoom });
  useEffect(() => {
    const from = centerRef.current;
    const fromZoom = zoomRef.current;
    const still = Math.abs(from.lat - target.lat) < 0.01 && Math.abs(from.lon - target.lon) < 0.01
      && Math.abs(fromZoom - zoom) < 0.001;
    const turned = asked.current.lat !== focus.lat || asked.current.lon !== focus.lon || asked.current.zoom !== zoom;
    asked.current = { lat: focus.lat, lon: focus.lon, zoom };
    if (prefersReducedMotion() || still || !turned) {
      setCenter(target);
      setShownZoom(zoom);
      return undefined;
    }
    let frame = 0;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 650);
      setCenter(interpolateCenter(from, target, t));
      const e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
      setShownZoom(fromZoom + (zoom - fromZoom) * e);
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, zoom]);

  useEffect(() => {
    if (canvas.current) draw(canvas.current, g, center, props, dots);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [g, center, markers, home, selected, themeTick, props.routes, dots]);

  const placed = declutter(markers
    .map((m) => ({ m, p: project(m, center) }))
    .filter(({ p }) => p.z > 0.04)
    .map(({ m, p }) => ({ m, x: g.cx + p.x * g.radius, y: g.cy - p.y * g.radius }))
    .filter(({ x, y }) => x >= 0 && x <= g.width && y >= 0 && y <= g.height));
  const label = placed.find(({ m }) => m.id === selected);

  return (
    <figure className={`globe globe--${tone} globe--${layout}`} style={{ height }} ref={wrap} data-testid={testId}>
      <canvas ref={canvas} className="globe__canvas" style={{ width: '100%', height }} aria-hidden="true" />
      <div className="globe__markers" aria-hidden="true">
        {placed.map(({ m, x, y }) => (
          <button
            key={m.id}
            type="button"
            tabIndex={-1}
            className={`globe__marker${m.id === selected ? ' is-selected' : ''}`}
            style={{ left: x, top: y }}
            onClick={() => onSelect?.(m.id)}
            title={m.label}
            data-testid={`globe-marker-${m.id}`}
          />
        ))}
        {label && (
          <span
            className={`globe__label${label.x > g.width * 0.62 ? ' is-left' : ''}`}
            style={{ left: label.x, top: label.y }}
          >
            {label.m.label}
          </span>
        )}
      </div>
      <figcaption className="visually-hidden">{caption}</figcaption>
    </figure>
  );
}

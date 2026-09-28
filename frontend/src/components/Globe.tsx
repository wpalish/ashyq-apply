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
  centroidOf, greatCircle, interpolateCenter, isVisible, loadLandDots, project, projectRad, type LatLon,
} from '@/lib/globe';

export interface GlobeMarker extends LatLon {
  id: string;
  /** Shown beside the marker when it is the selected one. */
  label: string;
  /** The city, shown beside every marker once the globe is close in. */
  name?: string;
  /** The region: markers the globe hides are named at its edge by region. */
  group?: string;
}

export interface GlobeProps {
  markers: GlobeMarker[];
  home?: (LatLon & { city: string }) | null;
  /** The place to bring into the middle of the visible part. */
  focus: LatLon;
  /**
   * Places that must all be in view - home and a programme's city: the globe
   * turns to their middle and comes as close as it can. Replaces focus and zoom.
   */
  fit?: LatLon[];
  /** Name every place on the globe, home included, whatever the zoom. */
  names?: boolean;
  /** Pixels at the bottom that something sits over (a card): the view keeps above them. */
  covered?: number;
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
  /** A crowd of markers was tapped: zoom in on them. Without it, crowds still show their count. */
  onCluster?: (members: GlobeMarker[]) => void;
  /** A chip at the edge was tapped: turn to what it names. Without it, the chips only say. */
  onEdge?: (members: GlobeMarker[]) => void;
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

function geometryOf(layout: GlobeProps['layout'], width: number, height: number, zoom = 1, covered = 0): Geometry {
  if (layout === 'horizon') {
    const radius = Math.max(200, Math.min(560, width * 0.52));
    const cap = height * 0.94;
    return { width, height, radius, cx: width / 2, cy: height - cap + radius, focusY: 0.5 };
  }
  // The band is the part left in view; the globe carries on under a card.
  const band = height - covered;
  const base = Math.max(110, Math.min(width * 0.36, band * 0.72));
  const radius = base * zoom;
  // Zoomed in, the centre drops so the region stays in the band.
  return { width, height, radius, cx: width / 2, cy: band * 0.5 + base * 0.3 + (radius - base) * 0.6, focusY: (0.46 * band) / height };
}

/** The view centre that puts `focus` at the geometry's focus height. */
function viewCenter(focus: LatLon, g: Geometry): LatLon {
  const yUnit = (g.cy - g.focusY * g.height) / g.radius;
  const dLat = (Math.asin(Math.max(-0.95, Math.min(0.95, yUnit))) * 180) / Math.PI;
  return { lat: Math.max(-80, Math.min(80, focus.lat - dLat)), lon: focus.lon };
}

/** Closest first: the fit takes the first of these that shows every place. */
const FIT_ZOOMS = [6, 4.5, 3.4, 2.6, 2, 1.6, 1.3, 1.1, 1];

/**
 * How close the globe can come with every one of `points` in the frame, room
 * left for their names, and the route from the first to each other one.
 */
function fitZoom(
  points: LatLon[], layout: GlobeProps['layout'], width: number, height: number, lift: number, covered = 0,
): number {
  const middle = centroidOf(points);
  const inside = (g: Geometry, view: LatLon, p: LatLon, rise = 0, room = true) => {
    const q = project(p, view, rise);
    if (q.z < 0.1 && rise === 0) return false;
    const x = g.cx + q.x * g.radius;
    const y = g.cy - q.y * g.radius;
    return room
      ? x >= 44 && x <= width - 44 && y >= 12 && y <= height - covered - 30
      : x >= 4 && x <= width - 4 && y >= 6;
  };
  // A place alone would fill the frame with sea: close enough to see where it is.
  for (const zoom of points.length > 1 ? FIT_ZOOMS : FIT_ZOOMS.filter((z) => z <= 3)) {
    const g = geometryOf(layout, width, height, zoom, covered);
    const view = viewCenter(middle, g);
    const [from, ...to] = points;
    const top = from ? to.every((p) => {
      const path = greatCircle(from, p, 8, lift);
      return path.every(({ point, lift: rise }) => inside(g, view, point, rise, false));
    }) : true;
    if (top && points.every((p) => inside(g, view, p))) return zoom;
  }
  return 1;
}

type Side = 'left' | 'right' | 'bottom' | 'top';
const ARROW: Record<Side, string> = { left: '←', right: '→', bottom: '↓', top: '↑' };

/**
 * Which edge a hidden place lies towards: where it falls off the frame, or,
 * behind the globe, the way the globe would turn to bring it round.
 */
function sideOf(m: LatLon, center: LatLon, g: Geometry): Side {
  const p = project(m, center);
  if (p.z > 0.04) {
    const x = g.cx + p.x * g.radius;
    const y = g.cy - p.y * g.radius;
    if (x < 0) return 'left';
    if (x > g.width) return 'right';
    if (y > g.height) return 'bottom';
    if (y < 0) return 'top';
  }
  let dLon = m.lon - center.lon;
  if (dLon > 180) dLon -= 360;
  if (dLon < -180) dLon += 360;
  if (Math.abs(dLon) >= 20) return dLon < 0 ? 'left' : 'right';
  return m.lat < center.lat ? 'bottom' : 'top';
}

interface Edge {
  side: Side;
  key: string;
  text: string;
  members: GlobeMarker[];
  /** Where along a top or bottom edge the places left the frame. */
  at?: number;
}

/**
 * One chip per region on each edge: "← Americas · 4", or the city when it is
 * the only one. Concept N's rule: what the globe hides is said at its edge,
 * never left to look like a smaller list.
 */
function edgesOf(hidden: GlobeMarker[], center: LatLon, g: Geometry): Edge[] {
  const bySide = new Map<string, Edge>();
  for (const m of hidden) {
    const side = sideOf(m, center, g);
    const key = `${side}|${m.group ?? ''}`;
    const edge = bySide.get(key) ?? { side, key, text: '', members: [] };
    edge.members.push(m);
    bySide.set(key, edge);
  }
  return [...bySide.values()]
    .map((e) => {
      const only = e.members.length === 1 ? e.members[0] : undefined;
      const xs = e.members.map((m) => project(m, center)).filter((p) => p.z > 0).map((p) => g.cx + p.x * g.radius);
      const at = (e.side === 'bottom' || e.side === 'top') && xs.length
        ? xs.reduce((a, b) => a + b, 0) / xs.length
        : undefined;
      const what = only
        ? only.name ?? only.label
        : e.members[0]?.group ? `${e.members[0].group} · ${e.members.length}` : `${e.members.length} more`;
      return { ...e, at, text: `${ARROW[e.side]} ${what}` };
    })
    .sort((a, b) => b.members.length - a.members.length);
}

/** A chip's size, near enough to keep a stack of them off the markers. */
const chipWidth = (text: string) => text.length * 6.8 + 24;
const CHIP_HEIGHT = 28;

/**
 * Where a side's stack of chips sits along its edge: the spot that covers the
 * fewest markers, clusters and home, preferring the middle. A fixed spot put
 * "→ Asia & Oceania" over Astana on the reveal.
 */
function stackAt(side: Side, here: Edge[], obstacles: { x: number; y: number }[], g: Geometry): number {
  const w = Math.max(...here.map((e) => chipWidth(e.text)));
  const h = side === 'left' || side === 'right' ? here.length * CHIP_HEIGHT : CHIP_HEIGHT;
  // Below or above the frame, first try under where the places went out of it.
  const hint = here.find((e) => e.at !== undefined)?.at;
  const along = side === 'left' || side === 'right'
    ? [0.42, 0.24, 0.62, 0.8].map((f) => f * g.height)
    : [...(hint !== undefined ? [hint] : []), ...[0.5, 0.28, 0.72].map((f) => f * g.width)];
  const cost = (at: number) => obstacles.filter(({ x, y }) => {
    const box = side === 'left' ? [8, at - h / 2, 8 + w, at + h / 2]
      : side === 'right' ? [g.width - 8 - w, at - h / 2, g.width - 8, at + h / 2]
        : side === 'bottom' ? [at - w / 2, g.height - 8 - h, at + w / 2, g.height - 8]
          : [at - w / 2, 8, at + w / 2, 8 + h];
    return x > box[0]! - 14 && x < box[2]! + 14 && y > box[1]! - 14 && y < box[3]! + 14;
  }).length;
  let best = along[0]!;
  for (const at of along) if (cost(at) < cost(best)) best = at;
  if (side === 'left' || side === 'right') return Math.max(h / 2 + 6, Math.min(g.height - h / 2 - 6, best));
  return Math.max(w / 2 + 6, Math.min(g.width - w / 2 - 6, best));
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

/** A marker's tap target; two closer than this would cover each other. */
const MARKER_GAP = 26;
/** From this many crowded markers up, they show as one cluster to zoom into. */
const CLUSTER_FROM = 4;

interface Placed { m: GlobeMarker; x: number; y: number }

/** Markers whose tap targets touch, grouped (single link). */
function crowds(points: Placed[]): Placed[][] {
  const groups: Placed[][] = [];
  const seen = new Set<number>();
  points.forEach((_, start) => {
    if (seen.has(start)) return;
    const group: Placed[] = [];
    const queue = [start];
    seen.add(start);
    while (queue.length) {
      const i = queue.pop()!;
      const p = points[i]!;
      group.push(p);
      points.forEach((q, j) => {
        if (!seen.has(j) && Math.hypot(p.x - q.x, p.y - q.y) < MARKER_GAP) {
          seen.add(j);
          queue.push(j);
        }
      });
    }
    groups.push(group);
  });
  return groups;
}

/**
 * Two or three markers that touch are set one step apart round their true
 * place, so each can be tapped. Never further: a marker a long way from its
 * city would be a wrong fact, which is why a bigger crowd becomes a cluster.
 */
function spread(group: Placed[]): Placed[] {
  if (group.length === 1) return group;
  const cx = group.reduce((n, p) => n + p.x, 0) / group.length;
  const cy = group.reduce((n, p) => n + p.y, 0) / group.length;
  return group.map((p, i) => {
    const angle = (i / group.length) * Math.PI * 2 - Math.PI / 2;
    const r = MARKER_GAP / (2 * Math.sin(Math.PI / group.length));
    return { ...p, x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
  });
}

/**
 * The city names that fit without covering one another; a name that would
 * overlap one already shown is left to its marker's own label on tap.
 */
function namesThatFit(points: Placed[]): Placed[] {
  const boxes: [number, number, number, number][] = [];
  return points.filter(({ m, x, y }) => {
    const w = (m.name?.length ?? 0) * 6.4 + 4;
    const box: [number, number, number, number] = [x + 10, y - 8, x + 10 + w, y + 8];
    const hit = boxes.some((b) => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1]);
    if (!hit) boxes.push(box);
    return !hit;
  });
}

export function Globe(props: GlobeProps) {
  const {
    markers, home, focus, fit, names, covered = 0, tone, layout, height, selected, onSelect, onCluster, onEdge,
    caption, testId,
  } = props;
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [width, setWidth] = useState(360);
  // What was asked for, as numbers: a caller that builds a new focus (or a
  // new fit list) on every render must not restart the turn - that looped,
  // redrawing the reveal twenty times a second while it sat still.
  const fitKey = fit?.map((p) => `${p.lat},${p.lon}`).join('|') ?? '';
  const request = fit?.length ? `fit:${fitKey}` : `${focus.lat},${focus.lon},${props.zoom ?? 1}`;
  const lift = layout === 'horizon' ? 0.07 : 0.14;
  const view = useMemo(
    () => (fit?.length
      ? { focus: centroidOf(fit), zoom: fitZoom(fit, layout, width, height, props.routes ? lift : 0, covered) }
      : { focus: { lat: focus.lat, lon: focus.lon }, zoom: props.zoom ?? 1 }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [request, layout, width, height, props.routes, lift, covered],
  );
  const zoom = view.zoom;
  // The zoom eases with the turn, so a region chip reads as one movement.
  const [shownZoom, setShownZoom] = useState(zoom);
  const g = useMemo(() => geometryOf(layout, width, height, shownZoom, covered), [layout, width, height, shownZoom, covered]);
  const target = useMemo(
    () => viewCenter(view.focus, geometryOf(layout, width, height, zoom, covered)),
    [view.focus, layout, width, height, zoom, covered],
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
  // Said on the figure while it turns, so a test (or anything else) can wait
  // for it to settle instead of guessing a delay.
  const [turning, setTurning] = useState(false);
  // The request the view last answered. Until the effect below has taken a
  // new one, the globe is about to turn: said from the render that carries
  // the request, not a frame later, or a test that waits for "not turning"
  // right after a tap passes before the turn has begun (it read a cluster
  // mid-turn in CI).
  const [settled, setSettled] = useState(request);
  const moving = turning || settled !== request;
  const zoomRef = useRef(shownZoom);
  zoomRef.current = shownZoom;
  // Only a new request is a turn worth watching; a new width (the first
  // measurement, a rotated phone) moves the view at once, even when a fit's
  // zoom changes with it. Animating that made every globe spin for 650 ms as
  // it appeared.
  const asked = useRef(request);
  useEffect(() => {
    const from = centerRef.current;
    const fromZoom = zoomRef.current;
    const still = Math.abs(from.lat - target.lat) < 0.01 && Math.abs(from.lon - target.lon) < 0.01
      && Math.abs(fromZoom - zoom) < 0.001;
    const turned = asked.current !== request;
    asked.current = request;
    setSettled(request);
    if (prefersReducedMotion() || still || !turned) {
      setCenter(target);
      setShownZoom(zoom);
      return undefined;
    }
    let frame = 0;
    const start = performance.now();
    setTurning(true);
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 650);
      setCenter(interpolateCenter(from, target, t));
      const e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
      setShownZoom(fromZoom + (zoom - fromZoom) * e);
      if (t < 1) frame = requestAnimationFrame(step);
      else setTurning(false);
    };
    frame = requestAnimationFrame(step);
    return () => { cancelAnimationFrame(frame); setTurning(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, zoom]);

  useEffect(() => {
    if (canvas.current) draw(canvas.current, g, center, props, dots);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [g, center, markers, home, selected, themeTick, props.routes, dots]);

  const inView: Placed[] = markers
    .map((m) => ({ m, p: project(m, center) }))
    .filter(({ p }) => p.z > 0.04)
    .map(({ m, p }) => ({ m, x: g.cx + p.x * g.radius, y: g.cy - p.y * g.radius }))
    .filter(({ x, y }) => x >= 0 && x <= g.width && y >= 0 && y <= g.height);
  const shown = new Set(inView.map(({ m }) => m.id));
  // Said once the globe has settled: mid-turn, chips would flicker in and out.
  const edges = moving ? [] : edgesOf(markers.filter((m) => !shown.has(m.id)), center, g);

  const groups = crowds(inView);
  // Close enough in, a step of 26 px is a few kilometres: a crowd is then
  // set round its place rather than folded into a cluster that cannot open.
  const closeIn = shownZoom >= 10;
  const clusters = closeIn ? [] : groups.filter((group) => group.length >= CLUSTER_FROM);
  const placed = groups.filter((group) => closeIn || group.length < CLUSTER_FROM).flatMap(spread);
  const label = placed.find(({ m }) => m.id === selected);
  const homeSeen = home ? (() => {
    const p = project(home, center);
    return isVisible(p) ? { x: g.cx + p.x * g.radius, y: g.cy - p.y * g.radius } : null;
  })() : null;
  const obstacles = [
    ...placed,
    ...clusters.map((group) => ({
      x: group.reduce((n, p) => n + p.x, 0) / group.length,
      y: group.reduce((n, p) => n + p.y, 0) / group.length,
    })),
    ...(homeSeen ? [homeSeen] : []),
  ];

  return (
    <figure
      className={`globe globe--${tone} globe--${layout}`}
      style={{ height }}
      ref={wrap}
      data-testid={testId}
      data-turning={moving ? 'true' : undefined}
    >
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
        {clusters.map((group) => {
          const x = group.reduce((n, p) => n + p.x, 0) / group.length;
          const y = group.reduce((n, p) => n + p.y, 0) / group.length;
          return (
            <button
              key={group.map((p) => p.m.id).join('|')}
              type="button"
              tabIndex={-1}
              className="globe__cluster"
              style={{ left: x, top: y }}
              onClick={() => onCluster?.(group.map((p) => p.m))}
              title={`${group.length} programmes here`}
              data-testid="globe-cluster"
              data-count={group.length}
            >
              {group.length}
            </button>
          );
        })}
        {/* Close in, the land is too sparse to say where you are: the
            cities name themselves instead. A route names both its ends. */}
        {names
          ? placed.filter(({ m }) => m.id !== selected && m.name).map(({ m, x, y }) => (
            <span key={`name-${m.id}`} className="globe__name globe__name--below" style={{ left: x, top: y }}>{m.name}</span>
          ))
          : shownZoom >= 4 && namesThatFit(placed.filter(({ m }) => m.id !== selected && m.name)).map(({ m, x, y }) => (
            <span key={`name-${m.id}`} className="globe__name" style={{ left: x, top: y }}>{m.name}</span>
          ))}
        {names && homeSeen && home && (
          <span className="globe__name globe__name--below globe__name--home" style={{ left: homeSeen.x, top: homeSeen.y }}>
            {home.city}
          </span>
        )}
        {label && (
          <span
            className={`globe__label${label.x > g.width * 0.62 ? ' is-left' : ''}`}
            style={{ left: label.x, top: label.y }}
          >
            {label.m.label}
          </span>
        )}
        {(['left', 'right', 'bottom', 'top'] as Side[]).map((side) => {
          const here = edges.filter((e) => e.side === side);
          if (here.length === 0) return null;
          const at = stackAt(side, here, obstacles, g);
          return (
            <div
              key={side}
              className={`globe__edges globe__edges--${side}`}
              style={side === 'left' || side === 'right' ? { top: at } : { left: at }}
            >
              {here.map((e) => (onEdge ? (
                <button
                  key={e.key}
                  type="button"
                  tabIndex={-1}
                  className="globe__edge"
                  onClick={() => onEdge(e.members)}
                  title={e.members.map((m) => m.name ?? m.label).join(', ')}
                  data-testid="globe-edge"
                  data-count={e.members.length}
                >
                  {e.text}
                </button>
              ) : (
                <span
                  key={e.key}
                  className="globe__edge"
                  title={e.members.map((m) => m.name ?? m.label).join(', ')}
                  data-testid="globe-edge"
                  data-count={e.members.length}
                >
                  {e.text}
                </span>
              )))}
            </div>
          );
        })}
      </div>
      <figcaption className="visually-hidden">{caption}</figcaption>
    </figure>
  );
}

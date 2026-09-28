/**
 * The globe's arithmetic: where a place is, whether it faces the viewer, and
 * the great-circle route between two places.
 *
 * Round 7's globe (concepts M and N) is decoration that carries facts: the
 * programmes on it are the results, at their cities, and the routes start at
 * the applicant's own country. Nothing here guesses. A city is placed only if
 * the fixed table in globe-places.json has it (each entry checked against its
 * country's outline by scripts/gen-globe.mjs); a result whose city is not in
 * the table is left off and counted, so the screen can say so.
 *
 * An orthographic projection of our own, so the app carries no geometry
 * library: the land is 8 441 precomputed dots, and a frame is a few thousand
 * multiplications.
 */

import PLACES from '@/lib/globe-places.json';
import { money } from '@/lib/format';
import { REGION_LABEL, regionOf } from '@/lib/regions';
import type { ProgramResult } from '@/types';

export interface LatLon {
  lat: number;
  lon: number;
}

/** A point in view space: x right, y up, z towards the viewer; radius 1. */
export interface ViewPoint {
  x: number;
  y: number;
  z: number;
}

const RAD = Math.PI / 180;

let landCache: Float32Array | null = null;
let landLoading: Promise<Float32Array> | null = null;

/** Decodes the packed dots into [lat, lon, lat, lon, …] in radians. */
export function decodeLand(base64: string): Float32Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const packed = new Int16Array(bytes.buffer);
  const out = new Float32Array(packed.length);
  for (let i = 0; i < packed.length; i += 1) out[i] = ((packed[i] ?? 0) / 100) * RAD;
  return out;
}

/**
 * The land dots, loaded on first use as a chunk of their own: the globe is
 * never on the path to the list, so its ~60 KB must not delay the first
 * screen on a slow phone. The globe draws its markers without them meanwhile.
 */
export function loadLandDots(): Promise<Float32Array> {
  if (landCache) return Promise.resolve(landCache);
  landLoading ??= import('@/lib/globe-land').then(({ LAND_DOTS }) => {
    landCache = decodeLand(LAND_DOTS);
    return landCache;
  });
  return landLoading;
}

/** Where a place is, seen from above `center`, on a unit sphere. */
export function project(point: LatLon, center: LatLon, lift = 0): ViewPoint {
  return projectRad(point.lat * RAD, point.lon * RAD, center.lat * RAD, center.lon * RAD, lift);
}

export function projectRad(lat: number, lon: number, lat0: number, lon0: number, lift = 0): ViewPoint {
  const cosLat = Math.cos(lat);
  const dl = lon - lon0;
  const r = 1 + lift;
  return {
    x: r * cosLat * Math.sin(dl),
    y: r * (Math.cos(lat0) * Math.sin(lat) - Math.sin(lat0) * cosLat * Math.cos(dl)),
    z: r * (Math.sin(lat0) * Math.sin(lat) + Math.cos(lat0) * cosLat * Math.cos(dl)),
  };
}

/** A point faces the viewer when it is on the near half of the sphere. */
export function isVisible(p: ViewPoint): boolean {
  return p.z > 0;
}

function toVector({ lat, lon }: LatLon): [number, number, number] {
  const la = lat * RAD;
  const lo = lon * RAD;
  return [Math.cos(la) * Math.cos(lo), Math.cos(la) * Math.sin(lo), Math.sin(la)];
}

function toLatLon([x, y, z]: [number, number, number]): LatLon {
  return { lat: Math.asin(Math.max(-1, Math.min(1, z))) / RAD, lon: Math.atan2(y, x) / RAD };
}

/**
 * The shortest route between two places, as `steps + 1` points, each with a
 * lift that rises towards the middle so the route reads as a flight.
 */
export function greatCircle(a: LatLon, b: LatLon, steps = 48, height = 0.18): { point: LatLon; lift: number }[] {
  const va = toVector(a);
  const vb = toVector(b);
  const dot = Math.max(-1, Math.min(1, va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2]));
  const omega = Math.acos(dot);
  const out: { point: LatLon; lift: number }[] = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    let v: [number, number, number];
    if (omega < 1e-6) v = va;
    else {
      const s = Math.sin(omega);
      const wa = Math.sin((1 - t) * omega) / s;
      const wb = Math.sin(t * omega) / s;
      v = [wa * va[0] + wb * vb[0], wa * va[1] + wb * vb[1], wa * va[2] + wb * vb[2]];
    }
    // Longer routes fly a little higher, as on an airline map.
    out.push({ point: toLatLon(v), lift: height * Math.sin(Math.PI * t) * Math.min(1, omega / 1.2) });
  }
  return out;
}

/**
 * The point that faces all of `points` best: their mean direction. For two
 * places it is the middle of the route between them.
 */
export function centroidOf(points: LatLon[]): LatLon {
  let x = 0;
  let y = 0;
  let z = 0;
  for (const p of points) {
    const [px, py, pz] = toVector(p);
    x += px;
    y += py;
    z += pz;
  }
  const n = Math.hypot(x, y, z);
  if (n < 1e-9) return points[0] ?? { lat: 0, lon: 0 };
  return toLatLon([x / n, y / n, z / n]);
}

/** Eases a turn of the globe from `from` to `to`, the short way round. */
export function interpolateCenter(from: LatLon, to: LatLon, t: number): LatLon {
  let dLon = to.lon - from.lon;
  if (dLon > 180) dLon -= 360;
  if (dLon < -180) dLon += 360;
  const e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
  return { lat: from.lat + (to.lat - from.lat) * e, lon: from.lon + dLon * e };
}

// --- places --------------------------------------------------------------

interface Place extends LatLon { city: string; country: string }

const key = (city: string, country: string) => `${city.trim().toLowerCase()}|${country.trim().toLowerCase()}`;

const CITY = new Map<string, Place>(
  (PLACES.cities as Place[]).map((p) => [key(p.city, p.country), p]),
);
const HOME = new Map<string, Place>(
  (PLACES.homes as Place[]).map((p) => [p.country.trim().toLowerCase(), p]),
);

/** Where a result's city is, or null when the table does not have it. */
export function placeOf(result: Pick<ProgramResult, 'city' | 'country'>): Place | null {
  if (!result.city || !result.country) return null;
  return CITY.get(key(result.city, result.country)) ?? null;
}

/** The applicant's home - their country of residence's capital - if known. */
export function homeOf(profile: unknown): Place | null {
  const context = (profile as { context?: { country_of_residence?: unknown } } | null)?.context;
  const country = typeof context?.country_of_residence === 'string' ? context.country_of_residence : '';
  return country ? HOME.get(country.trim().toLowerCase()) ?? null : null;
}

/**
 * Where each region is seen best, and how close: Europe's cities are a few
 * hundred kilometres apart, so its view is closer than the Americas'.
 */
export const REGION_VIEW: Record<string, LatLon & { zoom: number }> = {
  europe: { lat: 50, lon: 12, zoom: 2.1 },
  americas: { lat: 38, lon: -92, zoom: 1.3 },
  asia_oceania: { lat: 8, lon: 122, zoom: 1.1 },
};

/** A view that shows home and Europe together, as the concept did (M2: 60° E, 36° N). */
export function defaultView(home: LatLon | null): LatLon {
  if (!home) return { lat: 36, lon: 30 };
  return { lat: Math.max(20, Math.min(50, home.lat - 12)), lon: home.lon - 25 };
}

export interface ResultMarker extends LatLon {
  id: string;
  label: string;
  name: string;
  /** The region, for a chip at the edge when the globe hides the city. */
  group?: string;
}

/**
 * The results as markers at their cities, and how many could not be placed.
 * The label is the price a year after grants, as on the card, or says the
 * cost was not computed - never a number the card does not show.
 */
export function markersFor(results: ProgramResult[]): { markers: ResultMarker[]; unplaced: number } {
  const markers: ResultMarker[] = [];
  let unplaced = 0;
  for (const r of results) {
    const place = placeOf(r);
    if (!place) {
      unplaced += 1;
      continue;
    }
    const gap = r.funding_gap;
    const price = gap?.computable && gap.gap
      ? `${money({ ...gap.gap, academic_year: null })} a year`
      : 'cost not computed';
    const region = regionOf(r.country);
    markers.push({
      id: r.id,
      lat: place.lat,
      lon: place.lon,
      label: `${r.city} · ${price}`,
      name: r.city,
      group: region === 'other' ? undefined : REGION_LABEL[region],
    });
  }
  return { markers, unplaced };
}

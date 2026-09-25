/**
 * The globe's arithmetic and its places: a point faces the viewer or it does
 * not, a route starts and ends where it should, and a city is placed only
 * when the checked table has it.
 */

import { describe, expect, it } from 'vitest';
import {
  decodeLand, greatCircle, homeOf, interpolateCenter, isVisible, markersFor, placeOf, project,
} from './globe';
import { LAND_DOTS, LAND_DOT_COUNT } from './globe-land';
import type { ProgramResult } from '@/types';

const close = (a: number, b: number, eps = 1e-6) => Math.abs(a - b) < eps;

describe('the projection', () => {
  it('puts the view centre in the middle, facing the viewer', () => {
    const p = project({ lat: 36, lon: 60 }, { lat: 36, lon: 60 });
    expect(close(p.x, 0) && close(p.y, 0) && close(p.z, 1)).toBe(true);
  });

  it('hides the far side and keeps the near one', () => {
    expect(isVisible(project({ lat: -36, lon: -120 }, { lat: 36, lon: 60 }))).toBe(false);
    expect(isVisible(project({ lat: 52, lon: 5 }, { lat: 36, lon: 60 }))).toBe(true);
  });

  it('draws north up and east to the right', () => {
    const north = project({ lat: 50, lon: 60 }, { lat: 36, lon: 60 });
    const east = project({ lat: 36, lon: 75 }, { lat: 36, lon: 60 });
    expect(north.y).toBeGreaterThan(0);
    expect(east.x).toBeGreaterThan(0);
  });
});

describe('routes and turns', () => {
  it('starts at home and ends at the city', () => {
    const route = greatCircle({ lat: 51.17, lon: 71.45 }, { lat: 53.22, lon: 6.57 });
    expect(close(route[0]!.point.lat, 51.17, 1e-4) && close(route[0]!.point.lon, 71.45, 1e-4)).toBe(true);
    expect(close(route.at(-1)!.point.lat, 53.22, 1e-4) && close(route.at(-1)!.point.lon, 6.57, 1e-4)).toBe(true);
    expect(route[0]!.lift).toBe(0);
    expect(route[24]!.lift).toBeGreaterThan(0);
  });

  it('turns the short way round across the date line', () => {
    const half = interpolateCenter({ lat: 0, lon: 170 }, { lat: 0, lon: -170 }, 0.5);
    expect(Math.abs(Math.abs(half.lon) - 180)).toBeLessThan(1);
  });
});

describe('the land', () => {
  it('decodes to the dots the generator counted, in radians', () => {
    const dots = decodeLand(LAND_DOTS);
    expect(dots.length).toBe(LAND_DOT_COUNT * 2);
    for (let i = 0; i < dots.length; i += 2) {
      expect(Math.abs(dots[i]!)).toBeLessThanOrEqual(Math.PI / 2 + 1e-6);
    }
  });
});

describe('places', () => {
  // Every city in the institution registry and the demo corpus.
  const catalogue: [string, string][] = [
    ['Melbourne', 'Australia'], ['Vienna', 'Austria'], ['Leuven', 'Belgium'], ['Montreal', 'Canada'],
    ['Toronto', 'Canada'], ['Vancouver', 'Canada'], ['Brno', 'Czech Republic'], ['Prague', 'Czechia'],
    ['Copenhagen', 'Denmark'], ['Tallinn', 'Estonia'], ['Tartu', 'Estonia'], ['Espoo', 'Finland'],
    ['Munich', 'Germany'], ['Hong Kong', 'Hong Kong'], ['Dublin', 'Ireland'], ['Bologna', 'Italy'],
    ['Milan', 'Italy'], ['Tokyo', 'Japan'], ['Astana', 'Kazakhstan'], ['Vilnius', 'Lithuania'],
    ['Kuala Lumpur', 'Malaysia'], ['Amsterdam', 'Netherlands'], ['Delft', 'Netherlands'],
    ['Eindhoven', 'Netherlands'], ['Groningen', 'Netherlands'], ['Auckland', 'New Zealand'],
    ['Dunedin', 'New Zealand'], ['Oslo', 'Norway'], ['Warsaw', 'Poland'], ['Singapore', 'Singapore'],
    ['Daejeon', 'South Korea'], ['Seoul', 'South Korea'], ['Madrid', 'Spain'], ['Gothenburg', 'Sweden'],
    ['Lund', 'Sweden'], ['Uppsala', 'Sweden'], ['Lausanne', 'Switzerland'], ['Ankara', 'Turkiye'],
    ['Istanbul', 'Turkey'], ['Sharjah', 'United Arab Emirates'], ['Belfast', 'United Kingdom'],
    ['Edinburgh', 'United Kingdom'], ['Tempe', 'United States'],
  ];

  it('places every city the catalogue returns', () => {
    const missing = catalogue.filter(([city, country]) => !placeOf({ city, country }));
    expect(missing).toEqual([]);
  });

  it('never guesses a city it does not have', () => {
    expect(placeOf({ city: 'Atlantis', country: 'Greece' })).toBeNull();
    expect(placeOf({ city: 'Cambridge', country: 'Atlantis' })).toBeNull();
    // Two Cambridges: the country decides which.
    expect(placeOf({ city: 'Cambridge', country: 'United Kingdom' })!.lon).toBeGreaterThan(-1);
    expect(placeOf({ city: 'Cambridge', country: 'United States' })!.lon).toBeLessThan(-70);
  });

  it('starts routes from the capital of the country of residence', () => {
    expect(homeOf({ context: { country_of_residence: 'Kazakhstan' } })?.city).toBe('Astana');
    expect(homeOf({ context: { country_of_residence: 'Narnia' } })).toBeNull();
    expect(homeOf(null)).toBeNull();
  });

  it('labels a marker with the price the card shows, and counts what it cannot place', () => {
    const results = [
      { id: 'g', city: 'Groningen', country: 'Netherlands', funding_gap: { computable: true, gap: { amount: 1848, currency: 'USD' } } },
      { id: 't', city: 'Toronto', country: 'Canada', funding_gap: { computable: false, gap: null } },
      { id: 'x', city: 'Atlantis', country: 'Greece', funding_gap: null },
    ] as unknown as ProgramResult[];
    const { markers, unplaced } = markersFor(results);
    expect(markers.map((m) => m.label)).toEqual(['Groningen · 1,848 USD a year', 'Toronto · cost not computed']);
    expect(unplaced).toBe(1);
    expect(markers.map((m) => m.label).join(' ')).not.toMatch(/%|chance/i);
  });
});

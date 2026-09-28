/**
 * Regions come from a fixed table; a country missing from it is "Other",
 * never guessed, and the counts always add up to the list.
 */

import { describe, expect, it } from 'vitest';
import { regionCounts, regionOf } from './regions';
import type { ProgramResult } from '@/types';

const at = (country: string) => ({ country } as ProgramResult);

describe('regions', () => {
  it('places every country the catalogue returns', () => {
    const catalogue = [
      'Australia', 'Austria', 'Belgium', 'Canada', 'Czech Republic', 'Czechia', 'Denmark', 'Estonia', 'Finland',
      'Germany', 'Hong Kong', 'Ireland', 'Italy', 'Japan', 'Kazakhstan', 'Lithuania', 'Malaysia', 'Netherlands',
      'New Zealand', 'Norway', 'Poland', 'Singapore', 'South Korea', 'Spain', 'Sweden', 'Switzerland', 'Turkey',
      'Turkiye', 'United Arab Emirates', 'United Kingdom', 'United States',
    ];
    expect(catalogue.filter((c) => regionOf(c) === 'other')).toEqual([]);
    expect(regionOf('Canada')).toBe('americas');
    expect(regionOf('New Zealand')).toBe('asia_oceania');
    expect(regionOf('Turkiye')).toBe('europe');
  });

  it('counts an unknown country as Other instead of guessing', () => {
    expect(regionOf('Atlantis')).toBe('other');
    expect(regionOf(null)).toBe('other');
    const counts = regionCounts([at('Netherlands'), at('Canada'), at('Atlantis')]);
    expect(counts).toEqual([
      { region: 'europe', count: 1 },
      { region: 'americas', count: 1 },
      { region: 'asia_oceania', count: 0 },
      { region: 'other', count: 1 },
    ]);
  });

  it('adds up to the list, and hides Other when there is none', () => {
    const list = [at('Japan'), at('Germany'), at('Poland'), at('United States')];
    const counts = regionCounts(list);
    expect(counts.map((c) => c.region)).not.toContain('other');
    expect(counts.reduce((n, c) => n + c.count, 0)).toBe(list.length);
  });
});

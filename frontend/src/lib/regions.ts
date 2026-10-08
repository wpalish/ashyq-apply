/**
 * Where a programme is, by region: concept 07's chips over the list
 * ("Европа · 13", "Америка · 4", "Азия и Австралия · 3").
 *
 * A fixed table of the countries the catalogue can return, never inferred
 * from a name: a country missing from it is counted under "Other", which the
 * chips show, rather than guessed into a region. Two placements are choices,
 * not geography facts, and are kept here where they can be argued with:
 * Türkiye is with Europe (it is in the European Higher Education Area, and
 * that is how applicants weigh it), and the Gulf states and Central Asia are
 * with Asia.
 */

import type { ProgramResult } from '@/types';

export type Region = 'europe' | 'americas' | 'asia_oceania' | 'other';

export const REGION_ORDER: Region[] = ['europe', 'americas', 'asia_oceania', 'other'];

export const REGION_LABEL: Record<Region, string> = {
  europe: 'Europe',
  americas: 'Americas',
  asia_oceania: 'Asia & Oceania',
  other: 'Other',
};

const EUROPE = [
  'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic', 'Czechia', 'Denmark', 'Estonia',
  'Finland', 'France', 'Germany', 'Greece', 'Hungary', 'Iceland', 'Ireland', 'Italy', 'Latvia', 'Lithuania',
  'Luxembourg', 'Malta', 'Netherlands', 'Norway', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia',
  'Spain', 'Sweden', 'Switzerland', 'Turkey', 'Turkiye', 'Türkiye', 'United Kingdom',
];
const AMERICAS = ['Argentina', 'Brazil', 'Canada', 'Chile', 'Colombia', 'Mexico', 'United States'];
const ASIA_OCEANIA = [
  'Australia', 'China', 'Hong Kong', 'India', 'Indonesia', 'Japan', 'Kazakhstan', 'Kyrgyzstan', 'Malaysia',
  'New Zealand', 'Qatar', 'Saudi Arabia', 'Singapore', 'South Korea', 'Taiwan', 'Thailand',
  'United Arab Emirates', 'Uzbekistan',
];

const TABLE: Record<string, Region> = Object.fromEntries([
  ...EUROPE.map((c) => [c, 'europe'] as const),
  ...AMERICAS.map((c) => [c, 'americas'] as const),
  ...ASIA_OCEANIA.map((c) => [c, 'asia_oceania'] as const),
]);

export function regionOf(country: string | null | undefined): Region {
  return (country && TABLE[country.trim()]) || 'other';
}

/** How many results fall in each region; "other" only when there are any. */
export function regionCounts(results: ProgramResult[]): { region: Region; count: number }[] {
  const counts = new Map<Region, number>();
  for (const r of results) counts.set(regionOf(r.country), (counts.get(regionOf(r.country)) ?? 0) + 1);
  return REGION_ORDER
    .map((region) => ({ region, count: counts.get(region) ?? 0 }))
    .filter(({ region, count }) => count > 0 || region !== 'other');
}

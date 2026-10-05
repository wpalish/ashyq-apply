/**
 * Which colour a country's passes wear (concept «Пропуск», palette E).
 *
 * Eight deep, muted colours (`--pass-1` … `--pass-8` in tokens.css) go to the
 * countries the applicant picked, in the order they were picked, then to the
 * other countries in the results in the order they first appear. A ninth
 * country reuses a colour with a pattern rather than a ninth colour, so two
 * countries never look the same. Colour never means a verdict: the three
 * answers on the card are what judge a programme.
 */

export const PASS_COLOURS = 8;

export interface PassColour {
  /** 1 … PASS_COLOURS: the `--pass-N` token. */
  slot: number;
  /** True from the ninth country on: the same colour, striped. */
  pattern: boolean;
}

export function passColours(
  countries: readonly string[],
  preferred: readonly string[] = [],
): Map<string, PassColour> {
  const present = new Set(countries);
  const order: string[] = [];
  for (const country of [...preferred.filter((c) => present.has(c)), ...countries]) {
    if (!order.includes(country)) order.push(country);
  }
  return new Map(order.map((country, i) => [
    country,
    { slot: (i % PASS_COLOURS) + 1, pattern: i >= PASS_COLOURS },
  ]));
}

/** The applicant's chosen countries, from a saved profile of any shape. */
export function preferredCountries(profile: unknown): string[] {
  const list = (profile as { preferences?: { preferred_countries?: unknown } } | null | undefined)
    ?.preferences?.preferred_countries;
  return Array.isArray(list) ? list.filter((c): c is string => typeof c === 'string') : [];
}

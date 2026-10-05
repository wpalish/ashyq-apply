import { describe, expect, it } from 'vitest';
import { PASS_COLOURS, passColours, preferredCountries } from './passColour';

describe('pass colours', () => {
  it('gives the applicant\'s countries the first colours, in the order they were picked', () => {
    const map = passColours(['Japan', 'Netherlands', 'Belgium'], ['Belgium', 'Netherlands', 'Canada']);
    expect(map.get('Belgium')).toEqual({ slot: 1, pattern: false });
    expect(map.get('Netherlands')).toEqual({ slot: 2, pattern: false });
    // Canada is picked but has no result: it keeps colour 3, the one its chip
    // showed, and Japan (not picked) comes after it.
    expect(map.get('Japan')).toEqual({ slot: 4, pattern: false });
    expect(map.has('Canada')).toBe(false);
  });

  it('never gives two countries the same look: the ninth reuses a colour, striped', () => {
    const countries = Array.from({ length: PASS_COLOURS + 2 }, (_, i) => `Country ${i}`);
    const map = passColours(countries);
    expect(map.get('Country 0')).toEqual({ slot: 1, pattern: false });
    expect(map.get('Country 8')).toEqual({ slot: 1, pattern: true });
    expect(map.get('Country 9')).toEqual({ slot: 2, pattern: true });
    const looks = new Set([...map.values()].map((c) => `${c.slot}-${c.pattern}`));
    expect(looks.size).toBe(countries.length);
  });

  it('counts a country once however many programmes it has', () => {
    const map = passColours(['Japan', 'Japan', 'Belgium']);
    expect(map.get('Belgium')).toEqual({ slot: 2, pattern: false });
  });

  it('reads the chosen countries from a profile, and nothing from a missing one', () => {
    expect(preferredCountries({ preferences: { preferred_countries: ['Netherlands', 3, 'Japan'] } })).toEqual(['Netherlands', 'Japan']);
    expect(preferredCountries(null)).toEqual([]);
    expect(preferredCountries({})).toEqual([]);
  });
});

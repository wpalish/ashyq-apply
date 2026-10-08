/**
 * What the research found that is worth hearing about, read off the run:
 * never a guess, and never "nothing" beside a counter that says otherwise.
 */

import { describe, expect, it } from 'vitest';
import { findingTotals, findingsSoFar } from './findings';
import type { ProgramResult } from '@/types';

function result(overrides: Partial<ProgramResult>): ProgramResult {
  return {
    id: 'r', university: 'University', hard_filter_failures: [], source_urls: [], funding_gap: null,
    ...overrides,
  } as unknown as ProgramResult;
}

const delft = result({ id: 'delft', university: 'Delft University of Technology', hard_filter_failures: ['IELTS writing'] });
const toronto = result({
  id: 'toronto',
  university: 'University of Toronto',
  funding_gap: {
    year_mismatch: true,
    warnings: [
      "'Pearson' requires a nomination.",
      'Cost is published for 2026/27 but the award amount for 2024/25. The figures below are not directly comparable.',
    ],
  } as unknown as ProgramResult['funding_gap'],
});
// Every Oslo page failed, so only the programme's own address names the site.
const oslo = result({ id: 'oslo', university: 'University of Oslo', program_url: 'fixture://u-oslo/program-0.html' });

const errors = [
  'fixture://u-oslo/program-0.html: http_error — No bundled page at u-oslo/program-0.html',
  'fixture://u-oslo/costs.html: http_error — No bundled page',
  'page fetch-failed: fixture://u-oslo/program-0.html (page_type unclassified): http_error',
];

describe('findings so far', () => {
  it('names an exclusion, a year mismatch and a site that did not answer', () => {
    const found = findingsSoFar(errors, [delft, toronto, oslo]);
    expect(found.map((f) => [f.kind, f.where])).toEqual([
      ['exclusion', 'Delft University of Technology'],
      ['year', 'University of Toronto'],
      ['unreadable', 'University of Oslo'],
    ]);
    expect(found[0]?.text).toBe('not met: IELTS writing');
    expect(found[1]?.text).toBe('Cost is published for 2026/27 but the award amount for 2024/25.');
  });

  it('counts a page reported twice once', () => {
    const [unreadable] = findingsSoFar(errors, [oslo]);
    expect(unreadable?.text).toMatch(/^2 pages could not be read/);
  });

  it('names the site when no result points to it', () => {
    const [unreadable] = findingsSoFar(['https://www.example.edu/fees: timeout'], []);
    expect(unreadable?.where).toBe('example.edu');
  });

  it('shows the unreadable count before any site can be named', () => {
    const found = findingsSoFar([], [], 2, 10);
    expect(found).toHaveLength(1);
    expect(found[0]?.text).toMatch(/^10 pages could not be read/);
    expect(findingsSoFar([], [], 2, 0)).toEqual([]);
  });

  it('keeps two of each kind and counts the rest', () => {
    const many = ['a', 'b', 'c'].map((id) => result({ id, university: id, hard_filter_failures: ['GPA'] }));
    expect(findingsSoFar([], many)).toHaveLength(2);
    expect(findingTotals([], many)).toBe(3);
  });

  it('never states a chance', () => {
    const text = findingsSoFar(errors, [delft, toronto, oslo]).map((f) => `${f.label} ${f.text}`).join(' ');
    expect(text).not.toMatch(/%|chance|probab/i);
  });
});

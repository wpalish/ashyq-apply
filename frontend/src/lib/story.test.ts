/**
 * The story cards say only what the product knows, and keep a 16-year-old's
 * privacy by default: first name on, price and scores off, never the surname,
 * the city of residence or the school.
 */

import { describe, expect, it } from 'vitest';
import {
  FORBIDDEN, STORY_DEFAULTS, firstName, requirementsShareable, storyKinds, storyModel, storyText,
  type StoryKind,
} from './story';
import type { ProgramResult } from '@/types';

const profile = {
  display_name: 'Aruzhan Sadykova',
  context: { country_of_residence: 'Kazakhstan', intake_year: 2027, city: 'Astana', school: 'NIS Astana' },
  funding: { max_acceptable_gap: 6000, budget_currency: 'USD' },
};

function result(over: Partial<ProgramResult> = {}): ProgramResult {
  return {
    id: 'tokyo',
    university: 'University of Tokyo',
    program: 'PEAK Environmental Sciences',
    intake: 'fall 2027',
    city: 'Tokyo',
    country: 'Japan',
    eligibility: 'MET',
    admission_deadline: '2026-12-01',
    deadline_passed: false,
    source_urls: ['https://www.u-tokyo.ac.jp/peak'],
    last_verified: '2026-09-14T10:00:00Z',
    best_funding_classification: 'FULL_TUITION',
    scholarships: [{
      name: 'MEXT Scholarship',
      classification: 'FULL_TUITION',
      coverage: [{ category: 'tuition', covered: 'yes' }, { category: 'housing', covered: 'yes' }],
    }],
    costs: { items: { tuition: {}, housing: {}, insurance: {} } },
    funding_gap: { computable: true, gap: { amount: 1986, currency: 'USD', academic_year: '2026/27' } },
    requirement_checks: [
      { requirement: 'Admission deadline', published_value: '2026-12-01', applicant_value: '2026-09-25', status: 'MET' },
      { requirement: 'IELTS writing', published_value: 6, applicant_value: 6, status: 'MET' },
      { requirement: 'IELTS overall', published_value: 6.5, applicant_value: 7, status: 'MET' },
      { requirement: 'SAT total', published_value: 1300, applicant_value: 1400, status: 'MET' },
      { requirement: 'Accepted IELTS test type', published_value: ['academic'], applicant_value: 'academic', status: 'MET' },
    ],
    ...over,
  } as unknown as ProgramResult;
}

const input = (over: Partial<ProgramResult> = {}) => ({
  results: [result(over), result({ id: 'g', city: 'Groningen', country: 'Netherlands', admission_deadline: '2027-05-01' })],
  result: result(over),
  profile,
  demo: false,
});

describe('story cards', () => {
  it('print the name only when asked, and nothing about home but the country', () => {
    const route = storyModel('route', input());
    // Off by default: the first word of the label may be the surname.
    expect(route.who).toBe('2027');
    expect(storyModel('route', input(), { ...STORY_DEFAULTS, name: true }).who).toBe('Aruzhan · 2027');
    expect(route.from).toBe('Kazakhstan');
    expect(route.to).toBe('Tokyo');
    const text = (['route', 'requirements', 'map'] as StoryKind[])
      .map((k) => storyText(storyModel(k, input(), { ...STORY_DEFAULTS, name: true }))).join('\n');
    expect(text).not.toMatch(/Sadykova|Astana|NIS/);
  });

  it('leave the name off by default, and when the label is a placeholder', () => {
    expect(STORY_DEFAULTS.name).toBe(false);
    expect(storyModel('map', input()).who).toBe('2027');
    expect(firstName({ display_name: 'Demo Applicant (synthetic)' })).toBeNull();
    expect(firstName({ display_name: 'Applicant' })).toBeNull();
    expect(firstName({ display_name: '  Әлия  Н.' })).toBe('Әлия');
  });

  it('hide the price and the scores until they are switched on', () => {
    const quiet = storyText(storyModel('route', input())) + storyText(storyModel('requirements', input()));
    expect(quiet).not.toContain('1,986');
    expect(quiet).not.toContain('mine');
    const route = storyModel('route', input(), { ...STORY_DEFAULTS, price: true });
    expect(route.lines).toContain('1,986 USD a year left to pay, if awarded');
    const reqs = storyModel('requirements', input(), { ...STORY_DEFAULTS, scores: true });
    expect(reqs.rows[0]).toEqual({ label: 'IELTS overall', detail: 'minimum 6.5 · mine 7' });
  });

  it('say what the grant covers, never that it was won', () => {
    const route = storyModel('route', input());
    expect(route.chip).toBe('MEXT Scholarship · covers tuition, housing');
    expect(route.source).toBe('u-tokyo.ac.jp · read 14 September 2026');
  });

  it('offer "requirements met" only when every checked requirement is met, with the minimums and no dates', () => {
    const reqs = storyModel('requirements', input());
    expect(reqs.rows.map((r) => r.label)).toEqual(['IELTS overall', 'SAT total', 'IELTS writing']);
    expect(reqs.honesty).toBe("The admission decision is the university's.");
    expect(requirementsShareable(result({ eligibility: 'PENDING' }))).toBe(false);
    expect(storyKinds(result({ eligibility: 'GAP' }))).toEqual(['route', 'map']);
    expect(storyKinds(null)).toEqual(['map']);
  });

  it('count the map as the reveal does, with the first deadline still ahead', () => {
    const map = storyModel('map', input());
    expect(map.stats).toEqual([
      { value: '2', label: 'programmes' },
      { value: '2', label: 'countries' },
      { value: '2', label: 'within budget, if awarded' },
    ]);
    expect(map.note).toBe('First deadline: 1 December 2026, Tokyo');
  });

  it('never use the words of an outcome', () => {
    for (const kind of ['route', 'requirements', 'map'] as StoryKind[]) {
      const all = { name: true, price: true, scores: true };
      expect(storyText(storyModel(kind, input(), all))).not.toMatch(FORBIDDEN);
    }
  });

  it('carry the demo flag to the card', () => {
    expect(storyModel('map', { ...input(), demo: true }).demo).toBe(true);
  });
});

/**
 * Documents across screens: what is ready, and when each one needs starting -
 * arithmetic on published dates, never a date the data cannot support.
 */

import { describe, expect, it } from 'vitest';
import { doneKey, itemsOf, nextToStart, timingOf } from './docs';
import type { DocumentItem, ProgramResult } from '@/types';

const today = new Date(2026, 8, 25);

function item(name: string, overrides: Partial<DocumentItem> = {}): DocumentItem {
  return { name, lead_time_days: 14, deadline: null, ...overrides } as DocumentItem;
}

function programme(id: string, decision: string, deadline: string | null, applicant: DocumentItem[]): ProgramResult {
  return {
    id, university: `University ${id}`, user_decision: decision, admission_deadline: deadline,
    checklist: { recommender_actions: [], school_actions: [], certification_actions: [], applicant_actions: applicant },
  } as unknown as ProgramResult;
}

describe('documents across screens', () => {
  it('dates a document from its own deadline first, then the admission one', () => {
    const r = programme('a', 'approved', '2027-05-01', []);
    expect(timingOf(r, item('Essay', { deadline: '2027-02-01' }), today)?.start).toBe('2027-01-18');
    expect(timingOf(r, item('CV'), today)?.start).toBe('2027-04-17');
  });

  it('says a start date has gone by, and dates nothing past its deadline', () => {
    const soon = programme('a', 'approved', '2026-10-01', []);
    expect(timingOf(soon, item('Reference', { lead_time_days: 30 }), today)).toMatchObject({ late: true });
    const past = programme('b', 'approved', '2026-01-01', []);
    expect(timingOf(past, item('CV'), today)).toBeNull();
    expect(timingOf(soon, item('No lead', { lead_time_days: null }), today)).toBeNull();
  });

  it('lists the unticked documents of kept programmes, earliest start first', () => {
    const kept = programme('a', 'approved', '2027-05-01', [item('CV'), item('Essay', { deadline: '2027-02-01' })]);
    const maybe = programme('b', 'maybe', '2026-12-01', [item('Transcript', { lead_time_days: 21 })]);
    const undecided = programme('c', 'undecided', '2026-10-15', [item('Passport')]);
    const done = { [doneKey(kept, item('CV'))]: true };
    const tasks = nextToStart([kept, maybe, undecided], done, today);
    expect(tasks.map((t) => t.item.name)).toEqual(['Transcript', 'Essay']);
    expect(itemsOf(kept)).toHaveLength(2);
  });
});

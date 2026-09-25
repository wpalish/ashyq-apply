/**
 * The plan's deadlines: only the applicant's own list, nearest first, a
 * passed date marked and a missing one never guessed.
 */

import { describe, expect, it } from 'vitest';
import { daysUntil, flapDate, nextDeadline, planDeadlines, rowText } from './deadlines';
import type { ProgramResult, Scholarship } from '@/types';

const today = new Date(2026, 8, 25); // 25 September 2026, local time

function row(
  id: string, decision: string, deadline: string | null, passed = false, scholarships: Partial<Scholarship>[] = [],
): ProgramResult {
  return {
    id, university: `University ${id}`, program: 'BSc', user_decision: decision, eligibility: 'MET',
    admission_deadline: deadline, deadline_passed: passed, scholarships,
  } as unknown as ProgramResult;
}

function award(overrides: Partial<Scholarship>): Partial<Scholarship> {
  return {
    id: 'g', name: 'Talent Grant', application_mode: 'separate', applicant_eligible: 'unknown',
    deadline: '2027-02-01', deadline_passed: false, requires_extra_essays: true,
    eligibility_checks: [{ requirement: 'GPA', status: 'MET' }] as Scholarship['eligibility_checks'],
    ...overrides,
  };
}

describe('the plan deadlines', () => {
  it('counts whole days from today', () => {
    expect(daysUntil('2026-12-01', today)).toBe(67);
    expect(daysUntil('2026-09-25', today)).toBe(0);
    expect(daysUntil('2026-09-24', today)).toBe(-1);
  });

  it('spells the date as the tiles show it', () => {
    expect(flapDate('2026-12-01')).toBe('01 DEC');
    expect(flapDate('2027-05-01T23:59:00Z'.slice(0, 10))).toBe('01 MAY');
  });

  it('takes only kept and maybe programmes', () => {
    const planned = planDeadlines([
      row('a', 'approved', '2027-03-01'), row('b', 'maybe', '2026-12-01'),
      row('c', 'undecided', '2026-10-01'), row('d', 'rejected', '2026-10-01'),
    ], today);
    expect(planned.map((p) => p.result.id)).toEqual(['b', 'a']);
  });

  it('puts upcoming dates first, then passed ones, then the ones not found', () => {
    const planned = planDeadlines([
      row('none', 'approved', null), row('old', 'approved', '2026-01-15'),
      row('late', 'approved', '2027-05-01'), row('soon', 'maybe', '2026-12-01'),
    ], today);
    expect(planned.map((p) => p.result.id)).toEqual(['soon', 'late', 'old', 'none']);
    expect(planned[2]?.passed).toBe(true);
    expect(planned[3]?.daysLeft).toBeNull();
    expect(nextDeadline(planned)?.result.id).toBe('soon');
  });

  it("trusts the run's passed flag even when the date alone looks upcoming", () => {
    const planned = planDeadlines([row('a', 'approved', '2026-09-26', true)], today);
    expect(planned[0]?.passed).toBe(true);
    expect(nextDeadline(planned)).toBeNull();
  });

  it('reads a timestamp as its calendar date, not shifted by the time zone', () => {
    const [p] = planDeadlines([row('a', 'approved', '2026-12-01T23:59:00-05:00')], today);
    expect(p?.day).toBe('2026-12-01');
  });

  it('brings a grant with its own application onto the board, before the admission date', () => {
    const planned = planDeadlines([row('a', 'approved', '2027-05-01', false, [award({})])], today);
    expect(planned.map((p) => p.key)).toEqual(['a:g', 'a']);
    const [grant] = planned;
    expect(grant?.kind).toBe('award');
    expect(grant?.beforeAdmission).toBe(true);
    expect(grant && rowText(grant)).toEqual({ title: 'Talent Grant', detail: 'Grant application · essays · University a' });
    expect(nextDeadline(planned)?.key).toBe('a:g');
  });

  it('leaves off an award considered automatically, and one the applicant cannot hold', () => {
    const planned = planDeadlines([row('a', 'approved', '2027-05-01', false, [
      award({ id: 'auto', application_mode: 'automatic' }),
      award({ id: 'no', applicant_eligible: 'no' }),
      award({ id: 'undated', deadline: null }),
    ])], today);
    expect(planned.map((p) => p.key)).toEqual(['a']);
  });

  it("reads a grant's status from its own checks, the worst one first", () => {
    const planned = planDeadlines([row('a', 'approved', '2027-05-01', false, [
      award({ id: 'gap', eligibility_checks: [{ status: 'MET' }, { status: 'GAP' }] as Scholarship['eligibility_checks'] }),
      award({ id: 'none', eligibility_checks: [] }),
    ])], today);
    const status = Object.fromEntries(planned.map((p) => [p.key, p.status]));
    expect(status).toEqual({ a: 'MET', 'a:gap': 'GAP', 'a:none': 'NEEDS_OFFICIAL_CLARIFICATION' });
  });

  it('names a nomination as one, since someone else has to act by that date', () => {
    const [grant] = planDeadlines([row('a', 'approved', '2027-05-01', false, [
      award({ application_mode: 'nomination', requires_extra_essays: false }),
    ])], today);
    expect(grant && rowText(grant).detail).toBe('Grant nomination · University a');
  });
});

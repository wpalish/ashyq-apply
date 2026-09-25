/**
 * The plan's deadlines: only the applicant's own list, nearest first, a
 * passed date marked and a missing one never guessed.
 */

import { describe, expect, it } from 'vitest';
import { daysUntil, flapDate, nextDeadline, planDeadlines } from './deadlines';
import type { ProgramResult } from '@/types';

const today = new Date(2026, 8, 25); // 25 September 2026, local time

function row(id: string, decision: string, deadline: string | null, passed = false): ProgramResult {
  return {
    id, university: `University ${id}`, user_decision: decision,
    admission_deadline: deadline, deadline_passed: passed,
  } as unknown as ProgramResult;
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
});

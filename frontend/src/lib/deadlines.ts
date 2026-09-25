/**
 * The deadlines on the applicant's own list, in the order they fall.
 *
 * Round 7's plan screen: the nearest deadline first, then every one after it.
 * Only kept and "maybe" programmes are on the list - an undecided row is not
 * a plan yet, and a rejected one is not coming back. The date is the one the
 * university published; the days are counted here from today's calendar
 * date, so the board stays right between runs. A deadline the run could not
 * find is not guessed: it goes to the end as "not found".
 */

import type { ProgramResult } from '@/types';

export interface PlannedDeadline {
  result: ProgramResult;
  /** The published date, YYYY-MM-DD, or null when none was found. */
  day: string | null;
  /** Whole days from today to the deadline; null when there is no date. */
  daysLeft: number | null;
  passed: boolean;
}

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const DAY_MS = 86_400_000;

function calendarDay(iso: string | null | undefined): string | null {
  const match = iso?.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? match[0] : null;
}

function parts(day: string): [number, number, number] {
  const [y = 0, m = 1, d = 1] = day.split('-').map(Number);
  return [y, m, d];
}

function utcOf(day: string): number {
  const [y, m, d] = parts(day);
  return Date.UTC(y, m - 1, d);
}

/** Days from today's local calendar date to a published date. */
export function daysUntil(day: string, today: Date): number {
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((utcOf(day) - start) / DAY_MS);
}

/** "01 DEC" - the date as the board's tiles spell it. */
export function flapDate(day: string): string {
  const [, m, d] = parts(day);
  return `${String(d).padStart(2, '0')} ${MONTHS[m - 1] ?? ''}`;
}

/** "1 December 2027" - the same date for a screen reader. */
export function spokenDate(day: string): string {
  return new Date(utcOf(day)).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  });
}

export function planDeadlines(results: ProgramResult[], today: Date = new Date()): PlannedDeadline[] {
  const planned = results
    .filter((r) => r.user_decision === 'approved' || r.user_decision === 'maybe')
    .map((result) => {
      const day = calendarDay(result.admission_deadline);
      const daysLeft = day ? daysUntil(day, today) : null;
      // The backend's flag was set on the day of the run; the count is today's.
      const passed = Boolean(result.deadline_passed || (daysLeft !== null && daysLeft < 0));
      return { result, day, daysLeft, passed };
    });
  const rank = (p: PlannedDeadline) => (p.day === null ? 2 : p.passed ? 1 : 0);
  return planned.sort((a, b) => rank(a) - rank(b)
    || (a.day ?? '').localeCompare(b.day ?? '')
    || a.result.university.localeCompare(b.result.university));
}

/** The next deadline that has not passed, if there is one. */
export function nextDeadline(planned: PlannedDeadline[]): PlannedDeadline | null {
  return planned.find((p) => p.day !== null && !p.passed) ?? null;
}

/** What the requirements say, in one word for the board's last column. */
export const REQUIREMENT_WORD: Record<string, string> = {
  MET: 'Met',
  NOT_APPLICABLE: 'None apply',
  GAP: 'Action needed',
  PENDING: 'Action needed',
  NEEDS_OFFICIAL_CLARIFICATION: 'Ask the university',
};

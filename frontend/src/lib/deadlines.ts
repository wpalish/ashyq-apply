/**
 * The deadlines on the applicant's own list, in the order they fall.
 *
 * Round 7's plan screen: the nearest deadline first, then every one after it.
 * Only kept and "maybe" programmes are on the list - an undecided row is not
 * a plan yet, and a rejected one is not coming back. The date is the one the
 * university published; the days are counted here from today's calendar
 * date, so the board stays right between runs. A deadline the run could not
 * find is not guessed: it goes to the end as "not found".
 *
 * A grant with its own application has its own deadline, and it is often the
 * earlier one - concept L's board put "the essay for the grant, 1 February"
 * above the admission date of 1 May for exactly that reason. So each kept
 * programme brings its grant deadlines too, except an award that is
 * considered automatically (nothing to do by that date) and one the applicant
 * is recorded as not eligible for.
 */

import type { ProgramResult, Scholarship } from '@/types';

export interface PlannedDeadline {
  /** Unique on the board: the result id, plus the award id for a grant. */
  key: string;
  kind: 'admission' | 'award';
  result: ProgramResult;
  award: Scholarship | null;
  /** The published date, YYYY-MM-DD, or null when none was found. */
  day: string | null;
  /** Whole days from today to the deadline; null when there is no date. */
  daysLeft: number | null;
  passed: boolean;
  /** The requirement status the last column reads, in the enum's words. */
  status: string;
  /** A grant due before the programme's own admission deadline. */
  beforeAdmission: boolean;
}

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const DAY_MS = 86_400_000;

/** The calendar date at the start of an ISO date or timestamp, never shifted by a zone. */
export function calendarDay(iso: string | null | undefined): string | null {
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

/** The day to begin something that takes `leadDays`, to have it ready by `due`. */
export function startBy(due: string, leadDays: number): string {
  return new Date(utcOf(due) - leadDays * DAY_MS).toISOString().slice(0, 10);
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

/** Worst first: what the applicant must act on outranks what is settled. */
const STATUS_ORDER = ['GAP', 'PENDING', 'NEEDS_OFFICIAL_CLARIFICATION', 'MET', 'NOT_APPLICABLE'];

/** An award's own checks, read as one status; no checks at all is a question. */
function awardStatus(award: Scholarship): string {
  const statuses = (award.eligibility_checks ?? []).map((c) => c.status as string);
  if (statuses.length === 0) return 'NEEDS_OFFICIAL_CLARIFICATION';
  return STATUS_ORDER.find((s) => statuses.includes(s)) ?? 'NEEDS_OFFICIAL_CLARIFICATION';
}

function dated(day: string | null, flagged: boolean, today: Date) {
  const daysLeft = day ? daysUntil(day, today) : null;
  // The backend's flag was set on the day of the run; the count is today's.
  return { daysLeft, passed: Boolean(flagged || (daysLeft !== null && daysLeft < 0)) };
}

export function planDeadlines(results: ProgramResult[], today: Date = new Date()): PlannedDeadline[] {
  const planned: PlannedDeadline[] = [];
  for (const result of results) {
    if (result.user_decision !== 'approved' && result.user_decision !== 'maybe') continue;
    const admission = calendarDay(result.admission_deadline);
    planned.push({
      key: result.id,
      kind: 'admission',
      result,
      award: null,
      day: admission,
      ...dated(admission, result.deadline_passed, today),
      status: result.eligibility,
      beforeAdmission: false,
    });
    for (const award of result.scholarships ?? []) {
      const day = calendarDay(award.deadline);
      if (!day || award.application_mode === 'automatic' || award.applicant_eligible === 'no') continue;
      planned.push({
        key: `${result.id}:${award.id}`,
        kind: 'award',
        result,
        award,
        day,
        ...dated(day, award.deadline_passed, today),
        status: awardStatus(award),
        beforeAdmission: Boolean(admission && day < admission),
      });
    }
  }
  const rank = (p: PlannedDeadline) => (p.day === null ? 2 : p.passed ? 1 : 0);
  return planned.sort((a, b) => rank(a) - rank(b)
    || (a.day ?? '').localeCompare(b.day ?? '')
    || a.result.university.localeCompare(b.result.university)
    || a.kind.localeCompare(b.kind));
}

/** The two lines a row shows: what is due, and whose it is. */
export function rowText(p: PlannedDeadline): { title: string; detail: string } {
  if (p.kind === 'award' && p.award) {
    const how = p.award.application_mode === 'nomination' ? 'Grant nomination' : 'Grant application';
    const essays = p.award.requires_extra_essays ? ' · essays' : '';
    return { title: p.award.name, detail: `${how}${essays} · ${p.result.university}` };
  }
  return { title: p.result.university, detail: `Application · ${p.result.program}` };
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

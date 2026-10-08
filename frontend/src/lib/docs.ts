/**
 * The applicant's documents across screens: what is on each list, what they
 * have ticked, and when each one needs starting.
 *
 * The documents screen and the plan both read this, so they cannot disagree
 * about what is ready or when to begin. "Ready" is the applicant's own tick,
 * kept in this browser - the product never uploads or submits anything. When
 * to start is arithmetic on published dates: the document's own due date, or
 * else the programme's admission deadline, minus the time the checklist says
 * it takes. Nothing is dated when either is unknown or the deadline has passed.
 */

import { useState } from 'react';
import { calendarDay, daysUntil, startBy } from '@/lib/deadlines';
import type { DocumentItem, ProgramResult } from '@/types';

export const DONE_KEY = 'ashyq.docsDone';

/** Every document on a checklist, once: the four groups split it by who acts. */
export function itemsOf(result: ProgramResult): DocumentItem[] {
  const c = result.checklist;
  if (!c) return [];
  return [...c.recommender_actions, ...c.school_actions, ...c.certification_actions, ...c.applicant_actions];
}

export function doneKey(result: ProgramResult, item: DocumentItem): string {
  return `${result.id}::${item.name}`;
}

export function loadDone(): Record<string, boolean> {
  try {
    return JSON.parse(window.localStorage.getItem(DONE_KEY) ?? '{}');
  } catch {
    return {};
  }
}

/** The ticks, and a toggle that keeps them in this browser. */
export function useDocsDone(): [Record<string, boolean>, (key: string) => void] {
  const [done, setDone] = useState<Record<string, boolean>>(loadDone);
  const toggle = (key: string) => {
    setDone((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      try {
        window.localStorage.setItem(DONE_KEY, JSON.stringify(next));
      } catch {
        /* progress ticks are a convenience; storage being unavailable is fine */
      }
      return next;
    });
  };
  return [done, toggle];
}

export interface Timing {
  due: string;
  start: string;
  /** The start date has gone by: it needs starting now. */
  late: boolean;
  /** Days from today to the start date; negative when late. */
  daysToStart: number;
}

export function timingOf(result: ProgramResult, item: DocumentItem, today: Date = new Date()): Timing | null {
  const due = calendarDay(item.deadline) ?? calendarDay(result.admission_deadline);
  if (!due || !item.lead_time_days || daysUntil(due, today) < 0) return null;
  const start = startBy(due, item.lead_time_days);
  const daysToStart = daysUntil(start, today);
  return { due, start, late: daysToStart < 0, daysToStart };
}

export interface Task {
  result: ProgramResult;
  item: DocumentItem;
  timing: Timing;
}

/**
 * The unticked documents on the applicant's own list, earliest start first.
 * Only kept and "maybe" programmes with a collected list count.
 */
export function nextToStart(
  results: ProgramResult[], done: Record<string, boolean>, today: Date = new Date(),
): Task[] {
  const tasks: Task[] = [];
  for (const result of results) {
    if (result.user_decision !== 'approved' && result.user_decision !== 'maybe') continue;
    for (const item of itemsOf(result)) {
      if (done[doneKey(result, item)]) continue;
      const timing = timingOf(result, item, today);
      if (timing) tasks.push({ result, item, timing });
    }
  }
  return tasks.sort((a, b) => a.timing.start.localeCompare(b.timing.start)
    || (b.item.lead_time_days ?? 0) - (a.item.lead_time_days ?? 0));
}

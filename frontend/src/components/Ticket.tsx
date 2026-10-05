/**
 * One deadline as a ticket (concept «Пропуск»): a date stub in the country's
 * colour, what is due and for which programme, where the requirements
 * stand, and how many days are left. The date is the one the university
 * published; the stub never stands for a verdict.
 */

import { flapDate, spokenDate, type PlannedDeadline } from '@/lib/deadlines';
import type { PassColour } from '@/lib/passColour';
import { requirementNote, sourceNote, urlHost } from '@/components/ResultCard';
import { date } from '@/lib/format';
import { passStyle } from '@/components/Pass';

/** "in 57 days", "tomorrow", "today", "passed", or that no date was found. */
export function daysWords(p: PlannedDeadline): string {
  if (p.day === null || p.daysLeft === null) return 'date not found';
  if (p.passed) return 'passed';
  if (p.daysLeft === 0) return 'today';
  if (p.daysLeft === 1) return 'tomorrow';
  return `in ${p.daysLeft} days`;
}

/** Where the requirements stand, in words, and the tone they take. */
export function standing(p: PlannedDeadline): { text: string; tone: 'ok' | 'warn' | 'info' | 'neutral' } {
  if (p.status === 'MET') return { text: 'Requirements met', tone: 'ok' };
  if (p.status === 'NOT_APPLICABLE') return { text: 'No requirement applies', tone: 'neutral' };
  if (p.status === 'NEEDS_OFFICIAL_CLARIFICATION') return { text: 'Ask the university', tone: 'info' };
  const note = p.kind === 'admission' ? requirementNote(p.result) : '';
  const text = note ? note.charAt(0).toUpperCase() + note.slice(1) : 'Action needed';
  return { text, tone: 'warn' };
}

/** Where the date was read: a grant's own page for a grant, else the programme's. */
export function ticketSource(p: PlannedDeadline): string {
  if (!p.award) return sourceNote(p.result);
  const where = urlHost(p.award.source_urls?.[0]);
  const when = p.award.last_verified ? `read ${date(p.award.last_verified)}` : 'date not recorded';
  return where ? `${where} · ${when}` : when;
}

/** What is due: "PEAK · application", or the grant and how it is applied for. */
export function dueWhat(p: PlannedDeadline): string {
  if (p.kind === 'award' && p.award) {
    const how = p.award.application_mode === 'nomination' ? 'via the university' : 'grant application';
    return `${p.award.name} · ${how}`;
  }
  return `${p.result.program} · application`;
}

export function Ticket({ planned, colour, source = true, as = 'li' }: {
  planned: PlannedDeadline;
  colour: PassColour | undefined;
  /** The source line; a list that names its source once can leave it out. */
  source?: boolean;
  as?: 'li' | 'div';
}) {
  const p = planned;
  const [day, month] = p.day ? flapDate(p.day).split(' ') : ['—', ''];
  const where = standing(p);
  const soon = !p.passed && p.daysLeft !== null && p.daysLeft <= 30;
  const Tag = as;
  return (
    <Tag className={`ticket${p.passed ? ' is-passed' : ''}`} data-testid={`ticket-${p.key}`}>
      <span className="ticket__stub" style={passStyle(colour)} aria-hidden="true">
        <strong>{day}</strong><span>{month}</span>
      </span>
      <span className="ticket__body">
        <span className="ticket__title">
          <strong>{p.result.city || p.result.university}</strong>
          <span className={`ticket__days${soon ? ' is-soon' : ''}`}>{daysWords(p)}</span>
        </span>
        <span className="ticket__what">{dueWhat(p)}</span>
        <span className={`ticket__status tone-${where.tone}`}>{where.text}</span>
        <span className="visually-hidden">{p.day ? `Deadline ${spokenDate(p.day)}.` : 'No published deadline was found.'}</span>
        {source && <span className="ticket__source">{ticketSource(p)}</span>}
      </span>
    </Tag>
  );
}

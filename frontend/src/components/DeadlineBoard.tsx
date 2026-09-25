/**
 * The departures board: the nearest deadline, then every one on the list.
 *
 * Round 7's plan screen took concept L's board: the next deadline on
 * split-flap tiles with the days left, and one row per deadline under it -
 * the application, and any grant with an application of its own - with the
 * date, where, what, days, and one word for the requirements. That last word
 * describes what the applicant has to do, never how the university will
 * decide: "Met", "Action needed", "Ask the university". Money stays in its
 * own judgement and is not on the board (concept defect L3).
 *
 * The countdown is plain: no colour for "soon", because a board that turns
 * red at 30 days frightens a 16-year-old without telling them anything the
 * number does not. A passed deadline is marked as passed; a deadline the run
 * did not find reads "not found" and is never guessed.
 */

import { useState } from 'react';
import { StatusChip } from '@/components/primitives';
import { FIT_NOTE, awardNote, requirementNote, urlHost } from '@/components/ResultCard';
import {
  REQUIREMENT_WORD, flapDate, nextDeadline, rowText, spokenDate, type PlannedDeadline,
} from '@/lib/deadlines';
import { doneKey, itemsOf, timingOf } from '@/lib/docs';
import {
  admissionsFitTone, date, eligibilityTone, fundingClassTone, money,
} from '@/lib/format';
import type { ProgramResult } from '@/types';

function Flaps({ text }: { text: string }) {
  return (
    <span className="flaps" aria-hidden="true">
      {[...text].map((ch, i) => (
        ch === ' '
          ? <span key={i} className="flaps__gap" />
          : <span key={i} className="flaps__tile" style={{ ['--i' as string]: i }}>{ch}</span>
      ))}
    </span>
  );
}

function days(p: PlannedDeadline): string {
  if (p.daysLeft === null) return '—';
  if (p.passed) return 'passed';
  if (p.daysLeft === 0) return 'today';
  return String(p.daysLeft);
}

function spokenDays(p: PlannedDeadline): string {
  if (p.daysLeft === null) return 'no date';
  if (p.passed) return 'passed';
  if (p.daysLeft === 0) return 'today';
  return p.daysLeft === 1 ? '1 day left' : `${p.daysLeft} days left`;
}

function wordTone(status: string): string {
  if (status === 'MET' || status === 'NOT_APPLICABLE') return 'ok';
  if (status === 'NEEDS_OFFICIAL_CLARIFICATION') return 'ask';
  return 'act';
}

/** The page a row's date was read from: the award's own for a grant. */
function sourceOf(p: PlannedDeadline): { url?: string; read: string | null } {
  return p.award
    ? { url: p.award.source_urls?.[0], read: p.award.last_verified }
    : { url: p.result.source_urls?.[0], read: p.result.last_verified };
}

/** Where the dates were read, once for the whole board. */
function sourcesLine(planned: PlannedDeadline[]): string {
  const where = new Set(planned.filter((p) => p.day).map((p) => urlHost(sourceOf(p).url)));
  return [...where].filter(Boolean).join(' · ');
}

/**
 * A row opened: concept L's "tasks, money and the three judgements" for its
 * programme - the same three answers as the card, the money line, and how
 * far the documents are.
 */
function RowDetail({ result, done, id }: { result: ProgramResult; done: Record<string, boolean>; id: string }) {
  const gap = result.funding_gap;
  const items = itemsOf(result);
  const ready = items.filter((d) => done[doneKey(result, d)]).length;
  const nextItem = items
    .filter((d) => !done[doneKey(result, d)])
    .map((d) => ({ d, t: timingOf(result, d) }))
    .filter((x) => x.t !== null)
    .sort((a, b) => a.t!.start.localeCompare(b.t!.start))[0];
  return (
    <div className="board__detail" id={id} data-testid={`board-detail-${result.id}`}>
      <dl className="board__judgements">
        <div>
          <dt>Requirements</dt>
          <dd><StatusChip status={result.eligibility} tone={eligibilityTone[result.eligibility]} /> {requirementNote(result)}</dd>
        </div>
        <div>
          <dt>Your profile</dt>
          <dd><StatusChip status={result.admissions_fit} tone={admissionsFitTone[result.admissions_fit]} /> {FIT_NOTE[result.admissions_fit] ?? ''}</dd>
        </div>
        <div>
          <dt>Money</dt>
          <dd>
            <StatusChip status={result.best_funding_classification} tone={fundingClassTone[result.best_funding_classification]} />{' '}
            {gap?.computable && gap.gap
              ? <>{money({ ...gap.gap, academic_year: null })} a year left to pay, if awarded · {awardNote(result)}</>
              : <>cost not computed · {awardNote(result)}</>}
          </dd>
        </div>
        <div>
          <dt>Documents</dt>
          <dd>
            {items.length === 0
              ? 'not collected yet'
              : <>{ready} of {items.length} ready{nextItem ? <> · next: {nextItem.d.name}, {nextItem.t!.late ? 'start now' : `start by ${date(nextItem.t!.start)}`}</> : null}</>}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function DeadlineBoard({
  planned, done = {},
}: {
  planned: PlannedDeadline[];
  /** The applicant's document ticks, for a row's detail. */
  done?: Record<string, boolean>;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const next = nextDeadline(planned);
  const dated = planned.filter((p) => p.day !== null);
  const sources = sourcesLine(planned);
  const oldest = dated
    .map((p) => sourceOf(p).read)
    .filter((v): v is string => Boolean(v))
    .sort()[0];

  return (
    <section className="board" aria-labelledby="board-title" data-testid="deadline-board">
      <div className="board__next" data-testid="board-next">
        <h2 className="board__kicker" id="board-title">Next deadline</h2>
        {next && next.day ? (
          <>
            <p className="board__flap-row">
              <span className="visually-hidden">
                {spokenDate(next.day)}, {spokenDays(next)}: {rowText(next).title}, {rowText(next).detail}.
                {next.beforeAdmission && ' Due before the admission deadline.'}
              </span>
              <Flaps text={flapDate(next.day)} />
              <span className="board__next-what" aria-hidden="true">
                <strong>{rowText(next).title}</strong>
                <span>{rowText(next).detail}</span>
                {next.beforeAdmission && <span className="board__note">Due before the admission deadline</span>}
              </span>
              <span className="board__days" aria-hidden="true">
                <Flaps text={days(next)} />
                <span className="board__days-label">{next.daysLeft === 1 ? 'day left' : next.daysLeft === 0 ? '' : 'days left'}</span>
              </span>
            </p>
          </>
        ) : (
          <p className="board__none">
            {planned.length === 0
              ? 'Nothing on your plan yet. Keep a programme on the shortlist, or mark it maybe, and its deadline appears here.'
              : 'No upcoming deadline on your list: every date has passed or was not found.'}
          </p>
        )}
      </div>

      {planned.length > 0 && (
        <ol className="board__rows" aria-label="Every deadline on your list">
          <li className="board__head" aria-hidden="true">
            <span>Date</span><span>Where</span><span>What</span><span>Days</span><span>Requirements</span>
          </li>
          {planned.map((p) => (
            <li
              key={p.key}
              className={`board__row${p.passed ? ' is-passed' : ''}${p === next ? ' is-next' : ''}`}
              data-testid={`board-row-${p.key}`}
              data-kind={p.kind}
            >
              <span className="board__date">
                {p.day ? (
                  <>
                    <span aria-hidden="true">
                      <span className="board__dd">{flapDate(p.day).slice(0, 2)}</span>{' '}
                      <span className="board__mon">{flapDate(p.day).slice(3)}</span>
                    </span>
                    <span className="visually-hidden">{spokenDate(p.day)}</span>
                  </>
                ) : 'not found'}
              </span>
              <span className="board__where">{p.result.city || p.result.country}</span>
              <span className="board__what">
                <span className="board__uni">
                  <button
                    type="button"
                    className="board__open"
                    aria-expanded={open === p.key}
                    aria-controls={`board-detail-${p.key}`}
                    onClick={() => setOpen(open === p.key ? null : p.key)}
                    data-testid={`board-open-${p.key}`}
                  >
                    {rowText(p).title}
                  </button>
                  {p.result.user_decision === 'maybe' && <span className="board__maybe"> · maybe</span>}
                </span>
                <span className="board__prog">{rowText(p).detail}</span>
                {p.beforeAdmission && <span className="board__note">before the admission deadline</span>}
              </span>
              <span className="board__left">
                <span aria-hidden="true">{days(p)}</span>
                <span className="visually-hidden">{spokenDays(p)}</span>
              </span>
              <span className={`board__word board__word--${wordTone(p.status)}`}>
                <span className="visually-hidden">Requirements: </span>
                {REQUIREMENT_WORD[p.status] ?? p.status}
              </span>
              {open === p.key && <RowDetail result={p.result} done={done} id={`board-detail-${p.key}`} />}
            </li>
          ))}
        </ol>
      )}

      {dated.length > 0 && (
        <p className="board__foot">
          Dates as each university publishes them{sources ? <>, from {sources}</> : null}
          {oldest ? <>; the oldest was read {spokenDate(oldest.slice(0, 10))}</> : null}. Days are
          counted from today. The last column is what the requirements ask of you, not a prediction
          of the decision.
        </p>
      )}
    </section>
  );
}

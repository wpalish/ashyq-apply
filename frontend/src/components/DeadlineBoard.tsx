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
import { nextDeadline, spokenDate, type PlannedDeadline } from '@/lib/deadlines';
import type { PassColour } from '@/lib/passColour';
import { Ticket } from '@/components/Ticket';
import { doneKey, itemsOf, timingOf } from '@/lib/docs';
import {
  admissionsFitTone, date, eligibilityTone, fundingClassTone, money,
} from '@/lib/format';
import type { ProgramResult } from '@/types';





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
  planned, done = {}, colourOf,
}: {
  planned: PlannedDeadline[];
  /** The applicant's document ticks, for a row's detail. */
  done?: Record<string, boolean>;
  /** Each country's pass colour, for the ticket's stub. */
  colourOf?: (country: string) => PassColour | undefined;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const dated = planned.filter((p) => p.day !== null);
  const sources = sourcesLine(planned);
  const oldest = dated
    .map((p) => sourceOf(p).read)
    .filter((v): v is string => Boolean(v))
    .sort()[0];

  return (
    <section className="board" aria-labelledby="board-title" data-testid="deadline-board">
      <h2 className="visually-hidden" id="board-title">Every deadline on your list, nearest first</h2>
      {planned.length > 0 && !nextDeadline(planned) && (
        <p className="board__none">No upcoming deadline on your list: every date has passed or was not found.</p>
      )}
      {planned.length === 0 ? (
        <p className="board__none">
          Nothing on your plan yet. Keep a programme on Find, or mark it maybe, and its deadline
          appears here.
        </p>
      ) : (
        <ol className="tickets" aria-label="Every deadline on your list">
          {planned.map((p) => (
            <Ticket
              key={p.key}
              planned={p}
              colour={colourOf?.(p.result.country)}
              source={false}
              open={open === p.key}
              onToggle={() => setOpen(open === p.key ? null : p.key)}
              testId={`board-row-${p.key}`}
            >
              <RowDetail result={p.result} done={done} id={`board-detail-${p.key}`} />
            </Ticket>
          ))}
        </ol>
      )}

      {dated.length > 0 && (
        <p className="board__foot">
          Dates as each university publishes them{sources ? <>, from {sources}</> : null}
          {oldest ? <>; the oldest was read {spokenDate(oldest.slice(0, 10))}</> : null}. Days are
          counted from today. The coloured line is what the requirements ask of you, not a
          prediction of the decision.
        </p>
      )}
    </section>
  );
}

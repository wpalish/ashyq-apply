/**
 * The departures board: the nearest deadline, then every one on the list.
 *
 * Round 7's plan screen took concept L's board: the next deadline on
 * split-flap tiles with the days left, and one row per programme under it -
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

import { sourceHost } from '@/components/ResultCard';
import {
  REQUIREMENT_WORD, flapDate, nextDeadline, spokenDate, type PlannedDeadline,
} from '@/lib/deadlines';

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

/** Where the dates were read, once for the whole board. */
function sourcesLine(planned: PlannedDeadline[]): string {
  const where = new Set(planned.filter((p) => p.day).map((p) => sourceHost(p.result)));
  return [...where].filter(Boolean).join(' · ');
}

export function DeadlineBoard({ planned }: { planned: PlannedDeadline[] }) {
  const next = nextDeadline(planned);
  const dated = planned.filter((p) => p.day !== null);
  const sources = sourcesLine(planned);
  const oldest = dated
    .map((p) => p.result.last_verified)
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
                {spokenDate(next.day)}, {spokenDays(next)}: {next.result.university}, {next.result.program}.
              </span>
              <Flaps text={flapDate(next.day)} />
              <span className="board__next-what" aria-hidden="true">
                <strong>{next.result.university}</strong>
                <span>Application · {next.result.program}</span>
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
            <span>Date</span><span>Where</span><span>Programme</span><span>Days</span><span>Requirements</span>
          </li>
          {planned.map((p) => (
            <li
              key={p.result.id}
              className={`board__row${p.passed ? ' is-passed' : ''}${p === next ? ' is-next' : ''}`}
              data-testid={`board-row-${p.result.id}`}
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
                  {p.result.university}
                  {p.result.user_decision === 'maybe' && <span className="board__maybe"> · maybe</span>}
                </span>
                <span className="board__prog">{p.result.program}</span>
              </span>
              <span className="board__left">
                <span aria-hidden="true">{days(p)}</span>
                <span className="visually-hidden">{spokenDays(p)}</span>
              </span>
              <span className={`board__word board__word--${wordTone(p.result.eligibility)}`}>
                <span className="visually-hidden">Requirements: </span>
                {REQUIREMENT_WORD[p.result.eligibility] ?? p.result.eligibility}
              </span>
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

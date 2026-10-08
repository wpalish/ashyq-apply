/**
 * Decide one programme at a time.
 *
 * Twenty rows of ten columns is a spreadsheet; a student on a phone decides
 * better looking at one programme with its three judgements side by side and
 * three answers under it. Nothing here is new data or a new rule: the card
 * reads the same fields as the table and the answers go through the same
 * `decide()`, so a decision made here is the decision the table shows.
 *
 * "Not for me" still asks why, with the same one-click reasons as the table:
 * the product promises that a rejection keeps its reason, and a faster path
 * is not a reason to drop that promise. The reason stays optional.
 */

import { useEffect, useRef, useState } from 'react';
import { Check, Question, X } from '@phosphor-icons/react';
import { PassRoute } from '@/components/PassRoute';
import { passPrice, passStyle } from '@/components/Pass';
import { DeadlineNote, ThreeAnswers, sourceNote } from '@/components/ResultCard';
import { money } from '@/lib/format';
import { orderCaveats } from '@/lib/caveats';
import type { PassColour } from '@/lib/passColour';
import type { ProgramResult, UserDecision } from '@/types';

const REASONS = ['cost', 'deadline passed', 'no funding', 'not a fit'];

export function Triage({
  queue, total, decide, onClose, home, colourOf, intake = '',
}: {
  /** Undecided rows in the order the screen shows them. */
  queue: ProgramResult[];
  /** How many rows the triage started with, for "3 of 6". */
  total: number;
  decide: (id: string, decision: UserDecision, reason: string, notes: string) => Promise<void>;
  onClose: () => void;
  /** Home's city: the pass draws its route there. Without it, no route. */
  home?: string | null;
  /** Each country's pass colour (lib/passColour). */
  colourOf?: (country: string) => PassColour | undefined;
  /** "Fall 2027", for the pass's kicker. */
  intake?: string;
}) {
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const current = queue[0];
  const title = useRef<HTMLHeadingElement>(null);
  // Each new programme (and the final "every programme has an answer") takes
  // focus on its heading: the button that was pressed may be gone, and a
  // screen reader should hear which university is on the table now.
  const currentId = current?.id ?? null;
  useEffect(() => {
    title.current?.focus();
  }, [currentId]);

  // "Not for me" swaps the three answers for the reasons, so the button that
  // was pressed is gone: focus goes to the first reason, and the whole block,
  // "Save and next" included, is brought above a phone's tab bar - with the
  // globe above the card it could open under it. Cancel returns focus to
  // "Not for me".
  const reasons = useRef<HTMLDivElement>(null);
  const notForMe = useRef<HTMLButtonElement>(null);
  // Which programme the question was asked about: after "Save and next" the
  // next programme's heading has the focus, and keeps it.
  const askedAbout = useRef<string | null>(null);
  useEffect(() => {
    if (asking) {
      askedAbout.current = currentId;
      reasons.current?.querySelector<HTMLButtonElement>('button')?.focus({ preventScroll: true });
      reasons.current?.scrollIntoView?.({ block: 'nearest' });
    } else if (askedAbout.current !== null) {
      if (askedAbout.current === currentId) notForMe.current?.focus();
      askedAbout.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asking]);

  if (!current) {
    return (
      <section className="triage" aria-labelledby="triage-title" data-testid="triage">
        <h2 className="triage__title" id="triage-title" tabIndex={-1} ref={title}>Every programme has an answer</h2>
        <p className="triage__muted">
          Approved and maybe programmes are waiting on the Approved screen. Nothing was decided for
          you: every answer here was yours.
        </p>
        <button type="button" className="btn btn--primary" onClick={onClose} data-testid="triage-close">
          Back to the list
        </button>
      </section>
    );
  }

  const answer = async (decision: UserDecision, why = '') => {
    setBusy(true);
    try {
      await decide(current.id, decision, why, current.user_notes);
      setAsking(false);
      setReason('');
    } finally {
      setBusy(false);
    }
  };

  const gap = current.funding_gap;
  const position = total - queue.length + 1;
  // The remaining cost already subtracts published aid, and most of that aid
  // is competitive. The card says so with the price and the ranking's own
  // caveats, so "1,848 a year" is never read as a grant already won.
  const aid = gap?.confirmed_aid?.amount ?? 0;
  // What explains the figures first, then whether the aid can be won.
  const caveats = orderCaveats(gap?.warnings);

  const price = passPrice(current);
  // The next two programmes, in their colours, fanned behind the card: how
  // many are left, at a glance. Decoration only - the count says it in words.
  const behind = queue.slice(1, 3);

  return (
    <section className="triage" aria-labelledby="triage-title" data-testid="triage">
      <div className="triage__top">
        <span className="triage__count" aria-live="polite">{position} of {total} to decide</span>
        <button type="button" className="triage__back" onClick={onClose} data-testid="triage-close">
          Back to the list
        </button>
      </div>

      <div className="triage__deck">
        {behind.map((r, i) => (
          <span
            key={r.id}
            className={`triage__behind triage__behind--${i + 1}`}
            style={passStyle(colourOf?.(r.country))}
            aria-hidden="true"
          />
        ))}
        <article
          className={`triage__card pass${colourOf?.(current.country)?.pattern ? ' pass--pattern' : ''}`}
          style={passStyle(colourOf?.(current.country))}
          data-testid={`triage-card-${current.id}`}
        >
          <p className="pass__country">{[current.country, intake].filter(Boolean).join(' · ')}</p>
          <h2 className="triage__city" id="triage-title" tabIndex={-1} ref={title}>
            {current.city || current.university}
            {/* Two programmes can share a city: the heading names which one. */}
            <span className="visually-hidden">: {current.university}, {current.program}</span>
          </h2>
          <p className="triage__prog">{current.university} · {current.program}</p>
          <PassRoute city={current.city} home={home} />
          <p className="triage__price">
            {price.amount ? (
              <>
                <strong>{price.amount}</strong>
                <span>{gap?.gap?.currency} a year left to pay{aid > 0 ? ', if awarded' : ''}</span>
              </>
            ) : (
              <>
                <strong className="triage__price--none">Cost not computed</strong>
                <span title={gap?.reason}>{price.unit}</span>
              </>
            )}
          </p>
          {gap?.computable && gap.gap && gap.total_cost && aid > 0 && (
            <p className="triage__sub" data-testid="triage-price">
              price {money({ ...gap.total_cost, academic_year: null })} before grants
            </p>
          )}
          <div className="triage__inner">
            <ThreeAnswers result={current} />
            <p className="triage__source">
              <DeadlineNote result={current} /> · {sourceNote(current)}
            </p>
            {caveats.length > 0 && (
              <ul className="triage__caveats" data-testid="triage-caveats">
                {caveats.map((text) => <li key={text}>{text}</li>)}
              </ul>
            )}
          </div>
        </article>
      </div>

      {asking ? (
        <div className="triage__reason" data-testid="triage-reason" ref={reasons}>
          <p className="triage__muted" id="triage-why">Why not this one? Optional, and kept with the row.</p>
          <div className="row row--tight" role="group" aria-labelledby="triage-why">
            {REASONS.map((preset) => (
              <button
                key={preset}
                type="button"
                className={`btn btn--sm triage__chip${reason === preset ? ' is-on' : ''}`}
                aria-pressed={reason === preset}
                onClick={() => setReason(reason === preset ? '' : preset)}
              >{preset}</button>
            ))}
          </div>
          <div className="row row--tight">
            <button
              type="button"
              className="btn btn--primary"
              disabled={busy}
              onClick={() => answer('rejected', reason)}
              data-testid="triage-reject-save"
            >Save and next</button>
            <button type="button" className="btn btn--sm" onClick={() => setAsking(false)}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="triage__answers" role="group" aria-label={`Decision for ${current.university}`}>
          <button
            type="button"
            className="triage__answer"
            disabled={busy}
            onClick={() => setAsking(true)}
            ref={notForMe}
            data-testid="triage-reject"
          >
            <span className="triage__icon" aria-hidden="true"><X size={22} weight="bold" /></span>Not for me
          </button>
          <button
            type="button"
            className="triage__answer"
            disabled={busy}
            onClick={() => answer('maybe')}
            data-testid="triage-maybe"
          >
            <span className="triage__icon" aria-hidden="true"><Question size={22} weight="bold" /></span>Maybe
          </button>
          <button
            type="button"
            className="triage__answer triage__answer--keep"
            disabled={busy}
            onClick={() => answer('approved')}
            data-testid="triage-approve"
          >
            <span className="triage__icon" aria-hidden="true"><Check size={22} weight="bold" /></span>Keep
          </button>
        </div>
      )}
      <p className="triage__muted triage__foot">
        None of these predicts a decision: they compare your profile and budget with what the
        university publishes.
      </p>
    </section>
  );
}

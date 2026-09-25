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
import { StatusChip } from '@/components/primitives';
import {
  admissionsFitTone, date, eligibilityTone, fundingClassTone, money,
} from '@/lib/format';
import { orderCaveats } from '@/lib/caveats';
import type { ProgramResult, UserDecision } from '@/types';

const REASONS = ['cost', 'deadline passed', 'no funding', 'not a fit'];

export function Triage({
  queue, total, decide, onClose,
}: {
  /** Undecided rows in the order the screen shows them. */
  queue: ProgramResult[];
  /** How many rows the triage started with, for "3 of 6". */
  total: number;
  decide: (id: string, decision: UserDecision, reason: string, notes: string) => Promise<void>;
  onClose: () => void;
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

  return (
    <section className="triage" aria-labelledby="triage-title" data-testid="triage">
      <div className="triage__top">
        <span className="triage__count" aria-live="polite">{position} of {total} to decide</span>
        <button type="button" className="btn btn--sm triage__close" onClick={onClose} data-testid="triage-close">
          Back to the list
        </button>
      </div>

      <article className="triage__card" data-testid={`triage-card-${current.id}`}>
        <div className="triage__head">
          <h2 className="triage__uni" id="triage-title" tabIndex={-1} ref={title}>{current.university}</h2>
          <p className="triage__prog">{current.program} · {current.city}, {current.country}</p>
        </div>

        <dl className="triage__judgements">
          <div>
            <dt>Eligibility</dt>
            <dd><StatusChip status={current.eligibility} tone={eligibilityTone[current.eligibility]} /></dd>
          </div>
          <div>
            <dt>Admissions fit</dt>
            <dd><StatusChip status={current.admissions_fit} tone={admissionsFitTone[current.admissions_fit]} /></dd>
          </div>
          <div>
            <dt>Funding</dt>
            <dd>
              <StatusChip
                status={current.best_funding_classification}
                tone={fundingClassTone[current.best_funding_classification]}
              />
            </dd>
          </div>
        </dl>

        <dl className="triage__facts">
          <div>
            <dt>Left to pay a year</dt>
            <dd>
              {gap?.computable && gap.gap
                ? money({ ...gap.gap, academic_year: null })
                : <span className="triage__muted" title={gap?.reason}>not computable</span>}
              {gap?.computable && gap.gap && gap.total_cost && aid > 0 && (
                <span className="triage__sub" data-testid="triage-price">
                  if awarded · price {money({ ...gap.total_cost, academic_year: null })}
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt>Deadline</dt>
            <dd>
              {current.admission_deadline ? date(current.admission_deadline) : <span className="triage__muted">not found</span>}
              {current.deadline_passed && ' · passed'}
            </dd>
          </div>
        </dl>
        {caveats.length > 0 && (
          <ul className="triage__caveats" data-testid="triage-caveats">
            {caveats.map((text) => <li key={text}>{text}</li>)}
          </ul>
        )}
      </article>

      {asking ? (
        <div className="triage__reason" data-testid="triage-reason">
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
            <button type="button" className="btn btn--sm triage__close" onClick={() => setAsking(false)}>
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
            data-testid="triage-reject"
          >
            <span className="triage__icon" aria-hidden="true">✕</span>Not for me
          </button>
          <button
            type="button"
            className="triage__answer"
            disabled={busy}
            onClick={() => answer('maybe')}
            data-testid="triage-maybe"
          >
            <span className="triage__icon" aria-hidden="true">?</span>Maybe
          </button>
          <button
            type="button"
            className="triage__answer triage__answer--keep"
            disabled={busy}
            onClick={() => answer('approved')}
            data-testid="triage-approve"
          >
            <span className="triage__icon" aria-hidden="true">✓</span>Keep
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

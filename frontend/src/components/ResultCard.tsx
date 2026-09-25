/**
 * One programme as a card: the price a year after grants, and three answers.
 *
 * The concept's list card, built from the same row the table shows. The
 * price is the headline because it is the question a family asks first; the
 * three judgements stay three separate lines - requirements, the applicant's
 * profile, money - each with the one reason that matters, because a single
 * verdict would hide which of them is the problem. Nothing here is a chance:
 * every line is read off a published page, and the source and the date it
 * was read sit at the bottom of the card.
 */

import type { ReactNode } from 'react';
import { StatusChip } from '@/components/primitives';
import {
  admissionsFitTone, date, eligibilityTone, fundingClassTone, money,
} from '@/lib/format';
import type { ProgramResult } from '@/types';

/** The one requirement that explains an eligibility that is not simply met. */
export function requirementNote(result: ProgramResult): string {
  if (result.eligibility === 'MET') return 'every requirement checked is met';
  if (result.eligibility === 'NOT_APPLICABLE') return 'no requirement applies';
  const checks = result.requirement_checks ?? [];
  const culprit = checks.find((check) => check.status === result.eligibility)
    ?? checks.find((check) => check.status !== 'MET' && check.status !== 'NOT_APPLICABLE');
  if (culprit) {
    const prefix = result.eligibility === 'GAP'
      ? 'not met'
      : result.eligibility === 'PENDING' ? 'waiting on' : 'unverified';
    return `${prefix}: ${culprit.requirement}`;
  }
  if (result.missing_prerequisites?.length) return `missing: ${result.missing_prerequisites[0]}`;
  return '';
}

/** What an admissions-fit label does and does not say. */
export const FIT_NOTE: Record<string, string> = {
  STRONGER_FIT: 'above the minimums; selection is still competitive',
  PLAUSIBLE_FIT: 'meets the minimums; selection is competitive',
  AMBITIOUS: 'at or below the published range',
  INSUFFICIENT_DATA: 'not enough verified data to compare',
};

/** The award behind the funding label, by name. */
export function awardNote(result: ProgramResult): string {
  const awards = result.scholarships ?? [];
  const best = awards.find((award) => award.classification === result.best_funding_classification)
    ?? awards[0];
  return best ? best.name : 'no award found for this programme';
}

/** A page's site: its host name, or "demo fixture". */
export function urlHost(url: string | undefined): string {
  if (!url) return '';
  if (url.startsWith('fixture://')) return 'demo fixture';
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

/** The site the facts were read from: a host name, or "demo fixture". */
export function sourceHost(result: ProgramResult): string {
  return urlHost(result.source_urls?.[0]);
}

/** Where the facts come from, short enough for one line. */
export function sourceNote(result: ProgramResult): string {
  const where = sourceHost(result);
  const when = result.last_verified ? `read ${date(result.last_verified)}` : 'date not recorded';
  return where ? `${where} · ${when}` : when;
}

function firstSentence(text: string | undefined): string {
  if (!text) return '';
  const match = text.match(/^.*?[.!?](\s|$)/);
  return (match ? match[0] : text).trim();
}

export function ResultCard({
  result, open, onToggle, decision, detail, compare,
}: {
  result: ProgramResult;
  open: boolean;
  onToggle: () => void;
  /** The same decision controls the table row has. */
  decision: ReactNode;
  /** The full detail, shown under the card when it is open. */
  detail?: ReactNode;
  /** The "compare" toggle, when the screen offers a comparison. */
  compare?: ReactNode;
}) {
  const r = result;
  const gap = r.funding_gap;
  const aid = gap?.confirmed_aid?.amount ?? 0;
  const priced = Boolean(gap?.computable && gap.gap);

  return (
    <article
      className={`rcard${open ? ' is-open' : ''}${r.user_decision === 'rejected' ? ' is-rejected' : ''}`}
      data-testid={`card-${r.id}`}
    >
      <div className="rcard__head">
        <div className="rcard__names">
          <h3 className="rcard__uni">
            <button
              type="button"
              onClick={onToggle}
              aria-expanded={open}
              data-testid={`card-open-${r.id}`}
            >
              {r.university}
            </button>
          </h3>
          <p className="rcard__prog">{r.program} · {r.city}, {r.country}</p>
        </div>
        <div className={`rcard__price${priced ? '' : ' rcard__price--unknown'}`}>
          {priced && gap?.gap ? (
            <>
              <span className="rcard__amount">{money({ ...gap.gap, academic_year: null })}</span>
              <span className="rcard__per">{aid > 0 ? 'a year after grants, if awarded' : 'a year'}</span>
            </>
          ) : (
            <>
              <span className="rcard__amount rcard__amount--unknown">Cost not computed</span>
              <span className="rcard__per">{firstSentence(gap?.reason) || 'No official cost was found.'}</span>
            </>
          )}
        </div>
      </div>

      <dl className="rcard__lines">
        <div className="rcard__line">
          <dt>Requirements</dt>
          <dd>
            <StatusChip status={r.eligibility} tone={eligibilityTone[r.eligibility]} />
            <span className="rcard__note">{requirementNote(r)}</span>
          </dd>
        </div>
        <div className="rcard__line">
          <dt>Your profile</dt>
          <dd>
            <StatusChip status={r.admissions_fit} tone={admissionsFitTone[r.admissions_fit]} />
            <span className="rcard__note">{FIT_NOTE[r.admissions_fit] ?? ''}</span>
          </dd>
        </div>
        <div className="rcard__line">
          <dt>Money</dt>
          <dd>
            <StatusChip
              status={r.best_funding_classification}
              tone={fundingClassTone[r.best_funding_classification]}
            />
            <span className="rcard__note">{awardNote(r)}</span>
          </dd>
        </div>
      </dl>

      <div className="rcard__foot">
        <span className="rcard__source">
          <span className="rcard__dot" aria-hidden="true" />
          {sourceNote(r)}
        </span>
        <span className="rcard__deadline">
          {r.admission_deadline ? <>Deadline {date(r.admission_deadline)}</> : 'Deadline not found'}
          {r.deadline_passed && <strong className="rcard__passed"> · passed</strong>}
        </span>
      </div>

      <div className="rcard__decide">{decision}{compare}</div>

      {open && detail && <div className="rcard__detail">{detail}</div>}
    </article>
  );
}

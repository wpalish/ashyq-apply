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
  admissionsFitTone, date, eligibilityTone, fundingClassTone,
} from '@/lib/format';
import type { PassColour } from '@/lib/passColour';
import { Pass, PassAnswers } from '@/components/Pass';
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

/**
 * The three answers, each labelled, each with the one reason that matters.
 * Shared by the pass on Find, the opened programme and the triage card.
 */
export function ThreeAnswers({ result }: { result: ProgramResult }) {
  const r = result;
  return (
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
  );
}

/** The deadline as a card states it: the date, "passed", an earlier cycle's date as a guide. */
export function DeadlineNote({ result }: { result: ProgramResult }) {
  const r = result;
  return (
    <span className="rcard__deadline">
      {r.admission_deadline ? <>Deadline {date(r.admission_deadline)}</> : 'Deadline not found'}
      {r.deadline_passed && <strong className="rcard__passed"> · passed</strong>}
      {/* A date from an earlier cycle is a guide, not this intake's deadline. */}
      {r.previous_cycle_deadline && <> · previous cycle {date(r.previous_cycle_deadline)}</>}
    </span>
  );
}

/**
 * One programme on Find, as a pass (concept «Пропуск»): the country's colour,
 * the city, what is left to pay a year after grants. On a phone the pass
 * carries the three answers and what to do on white; on a desk it stays
 * compact - the three answers as three marks - and opens beside the list.
 */
export function ResultCard({
  result, open, onToggle, actions, pass, compact = false,
}: {
  result: ProgramResult;
  open: boolean;
  /** Open the programme (or close it again). */
  onToggle: () => void;
  /** Open, keep, compare: what the pass offers under its answers. */
  actions?: ReactNode;
  /** The country's colour (lib/passColour). */
  pass?: PassColour;
  /** The desk's pass: the head and three marks; the rest is in the panel. */
  compact?: boolean;
}) {
  const r = result;
  return (
    <Pass
      result={r}
      colour={pass}
      className={`rcard${open ? ' is-open' : ''}${r.user_decision === 'rejected' ? ' is-rejected' : ''}${compact ? ' rcard--compact' : ''}`}
      testId={`card-${r.id}`}
      title={(
        <button type="button" onClick={onToggle} aria-expanded={open} data-testid={`card-open-${r.id}`}>
          {r.city || r.university}
        </button>
      )}
    >
      {compact ? (
        <PassAnswers result={r} />
      ) : (
        <div className="rcard__inner">
          {!(r.funding_gap?.computable && r.funding_gap.gap) && (
            <p className="rcard__why">{firstSentence(r.funding_gap?.reason) || 'No official cost was found.'}</p>
          )}
          <ThreeAnswers result={r} />
          {actions && <div className="rcard__actions">{actions}</div>}
          <p className="rcard__foot">
            <span className="rcard__source">{sourceNote(r)}</span>
            <DeadlineNote result={r} />
          </p>
        </div>
      )}
    </Pass>
  );
}

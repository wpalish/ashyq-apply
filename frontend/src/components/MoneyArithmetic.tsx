/**
 * The money for one programme, as arithmetic: price − grants = left to pay.
 *
 * Round 7's programme screen showed the remainder as a sum rather than a
 * claim, because "the grant covers everything" was the sentence a family
 * would act on and the page did not say it. Every figure here is the
 * backend's own: the price, the aid it counted and the remainder, all in the
 * currency it computed them in. When the university publishes in another
 * currency the published figure is shown too, with the date of the rate
 * snapshot the backend converted with - this component converts nothing.
 *
 * What the grant covers is read off the award's coverage, category by
 * category; what the price includes that the grant does not is listed next
 * to it, because a remainder with no reason reads as a mistake.
 */

import type { Money, ProgramResult } from '@/types';
import { orderCaveats } from '@/lib/caveats';
import { date, humanize, money } from '@/lib/format';

export interface RateNote {
  date: string;
  source?: string;
}

function plain(value: Money | null | undefined): string {
  return value ? money({ ...value, academic_year: null }) : '—';
}

function hostOf(url: string | undefined): string {
  if (!url) return '';
  if (url.startsWith('fixture://')) return 'demo fixture';
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

export function MoneyArithmetic({ result, rate }: { result: ProgramResult; rate?: RateNote | null }) {
  const gap = result.funding_gap;
  if (!gap) return null;
  const award = result.scholarships.find((s) => s.classification === result.best_funding_classification)
    ?? result.scholarships[0];
  const covered = (award?.coverage ?? []).filter((c) => c.covered === 'yes').map((c) => c.category);
  const partly = (award?.coverage ?? []).filter((c) => c.covered === 'partial').map((c) => c.category);
  const priced = Object.keys(result.costs?.items ?? {});
  const leftOut = award ? priced.filter((category) => !covered.includes(category as never) && !partly.includes(category as never)) : [];
  const computedIn = gap.gap?.currency ?? gap.total_cost?.currency;
  const published = result.costs?.total;
  const converted = Boolean(published && computedIn && published.currency !== computedIn);
  const caveats = orderCaveats(gap.warnings);

  return (
    <section className="money" aria-label="Money a year" data-testid={`money-${result.id}`}>
      <h3 className="money__title">Money a year</h3>
      {gap.computable && gap.gap && gap.total_cost ? (
        <div className="money__sum" data-testid="money-sum">
          <div className="money__term">
            <span className="money__value">{plain(gap.total_cost)}</span>
            <span className="money__label">price</span>
          </div>
          <span className="money__op" aria-hidden="true">−</span>
          <div className="money__term">
            <span className="money__value">{plain(gap.confirmed_aid)}</span>
            <span className="money__label">grants, if awarded</span>
          </div>
          <span className="money__op" aria-hidden="true">=</span>
          <div className="money__term money__term--result">
            <span className="money__value">{plain(gap.gap)}</span>
            <span className="money__label">left to pay</span>
          </div>
        </div>
      ) : (
        <p className="money__unknown" data-testid="money-unknown">
          <strong>Not computed.</strong> {gap.reason}
        </p>
      )}

      {converted && published && (
        <p className="money__note" data-testid="money-converted">
          Published in {published.currency}: price {plain(published)}
          {award?.amount && award.amount.currency === published.currency && <>, {award.name} {plain(award.amount)}</>}.
          {' '}Converted to {computedIn}
          {rate?.date
            ? <> with the rate snapshot of <span title={rate.source}>{date(rate.date)}</span></>
            : ' by the backend'}.
        </p>
      )}

      {award && (
        <p className="money__note" data-testid="money-coverage">
          <strong>{award.name}</strong>
          {covered.length > 0 && <> covers {covered.map(humanize).join(', ').toLowerCase()}</>}
          {partly.length > 0 && <>{covered.length > 0 ? '; ' : ' '}partly {partly.map(humanize).join(', ').toLowerCase()}</>}
          {covered.length === 0 && partly.length === 0 && <> - what it covers is not published</>}.
          {leftOut.length > 0 && <> Not covered: {leftOut.map(humanize).join(', ').toLowerCase()}.</>}
        </p>
      )}

      {caveats.length > 0 && (
        <ul className="money__caveats">
          {caveats.map((text) => <li key={text}>{text}</li>)}
        </ul>
      )}

      {award && (
        <p className="money__source">
          <span className="rcard__dot" aria-hidden="true" />
          {hostOf(award.source_urls?.[0]) || 'source not recorded'}
          {' · '}
          {award.last_verified ? `read ${date(award.last_verified)}` : 'date not recorded'}
        </p>
      )}
    </section>
  );
}

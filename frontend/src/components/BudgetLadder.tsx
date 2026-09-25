/**
 * The budget ladder: what is left to pay each year, against the family's ceiling.
 *
 * It answers the question a family asks first - "which of these can we
 * afford?" - with the numbers already on the rows, and nothing new. The
 * ceiling is the one the ranking uses (`max_acceptable_gap`, falling back to
 * `max_annual_budget`; an explicit 0 is a real answer, not a missing one), and
 * a remaining cost is only compared with it in the same currency: this app
 * holds no exchange rates, and a converted guess is exactly what the product
 * refuses to show. A row whose cost could not be computed keeps its place in
 * its own group, with the reason, instead of being dropped or counted as 0.
 */

import { useState } from 'react';
import type { ProgramResult } from '@/types';

export interface Ceiling {
  amount: number;
  currency: string;
}

/** The ceiling as the ranking reads it, or null when the profile gives none. */
export function ceilingFrom(profile: unknown): Ceiling | null {
  const funding = (profile as { funding?: Record<string, unknown> } | null | undefined)?.funding;
  if (!funding) return null;
  const gap = funding.max_acceptable_gap;
  const annual = funding.max_annual_budget;
  // `??`, not `||`: "I can contribute nothing" is 0 and must stay 0.
  const amount = typeof gap === 'number' ? gap : typeof annual === 'number' ? annual : null;
  if (amount === null || !Number.isFinite(amount) || amount < 0) return null;
  const currency = typeof funding.budget_currency === 'string' && funding.budget_currency
    ? funding.budget_currency.toUpperCase()
    : 'USD';
  return { amount, currency };
}

export interface LadderGroups {
  within: ProgramResult[];
  above: ProgramResult[];
  unknown: { result: ProgramResult; reason: string }[];
}

/** Split rows by remaining cost against the ceiling; each group cheapest first. */
export function groupByBudget(results: ProgramResult[], ceiling: Ceiling): LadderGroups {
  const within: ProgramResult[] = [];
  const above: ProgramResult[] = [];
  const unknown: { result: ProgramResult; reason: string }[] = [];
  for (const r of results) {
    const gap = r.funding_gap;
    if (!gap?.computable || !gap.gap) {
      unknown.push({ result: r, reason: firstSentence(gap?.reason) || 'The remaining cost could not be computed.' });
      continue;
    }
    if (gap.gap.currency.toUpperCase() !== ceiling.currency) {
      unknown.push({
        result: r,
        reason: `The cost is in ${gap.gap.currency} and your budget in ${ceiling.currency}; this screen does not convert.`,
      });
      continue;
    }
    (gap.gap.amount <= ceiling.amount ? within : above).push(r);
  }
  const amount = (r: ProgramResult) => r.funding_gap?.gap?.amount ?? 0;
  within.sort((a, b) => amount(a) - amount(b) || a.id.localeCompare(b.id));
  above.sort((a, b) => amount(a) - amount(b) || a.id.localeCompare(b.id));
  return { within, above, unknown };
}

function firstSentence(text: string | undefined): string {
  if (!text) return '';
  const match = text.match(/^.*?[.!?](\s|$)/);
  return (match ? match[0] : text).trim();
}

function formatAmount(amount: number, currency: string): string {
  return `${Math.round(amount).toLocaleString('en-US')} ${currency}`;
}

const PREVIEW = 3;

export function BudgetLadder({
  results, ceiling, onOpen,
}: {
  results: ProgramResult[];
  ceiling: Ceiling;
  onOpen: (id: string) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const groups = groupByBudget(results, ceiling);
  // Twice the ceiling fills the track, so the ceiling line always sits in the
  // middle; a zero ceiling still needs a scale, so it borrows the dearest row.
  const dearest = Math.max(0, ...groups.above.map((r) => r.funding_gap?.gap?.amount ?? 0));
  const scale = ceiling.amount > 0 ? ceiling.amount * 2 : Math.max(dearest, 1);
  const linePct = ceiling.amount > 0 ? 50 : 0;

  const row = (r: ProgramResult, tone: 'within' | 'above') => {
    const value = r.funding_gap?.gap?.amount ?? 0;
    const pct = Math.min(100, (value / scale) * 100);
    const clipped = value > scale;
    const label = `${r.university}, ${r.program}: ${formatAmount(value, ceiling.currency)} a year, `
      + (tone === 'within' ? 'within your budget' : 'above your budget');
    return (
      <li key={r.id}>
        <button
          type="button"
          className={`ladder__row ladder__row--${tone}`}
          onClick={() => onOpen(r.id)}
          aria-label={label}
          data-testid={`ladder-row-${r.id}`}
        >
          <span className="ladder__name">
            <span className="ladder__uni">{r.university}</span>
            <span className="ladder__prog">{r.program}</span>
          </span>
          <span className="ladder__track" aria-hidden="true">
            <span className="ladder__bar" style={{ width: `${Math.max(pct, 1.5)}%` }} />
            {clipped && <span className="ladder__clip" />}
          </span>
          <span className="ladder__amount">{formatAmount(value, ceiling.currency)}</span>
        </button>
      </li>
    );
  };

  const aboveShown = showAll ? groups.above : groups.above.slice(0, PREVIEW);
  const unknownShown = showAll ? groups.unknown : groups.unknown.slice(0, PREVIEW);
  const hidden = groups.above.length - aboveShown.length + groups.unknown.length - unknownShown.length;

  return (
    <section className="panel ladder" aria-labelledby="ladder-title" data-testid="budget-ladder">
      <div className="ladder__head">
        <div>
          <h2 className="panel__title" id="ladder-title">What is left to pay each year</h2>
          <p className="panel__hint">
            After confirmed grants, against your budget of{' '}
            <strong>{formatAmount(ceiling.amount, ceiling.currency)}</strong> a year from Preferences.
            A number is a published price minus a confirmed award, never an estimate of your chances.
          </p>
        </div>
      </div>

      <div className="ladder__body" style={{ ['--ladder-line' as string]: `${linePct}%` }}>
        <h3 className="ladder__label ladder__label--within" data-testid="ladder-within">
          Within budget · {groups.within.length}
        </h3>
        {groups.within.length > 0 ? (
          <ol className="ladder__list">{groups.within.map((r) => row(r, 'within'))}</ol>
        ) : (
          <p className="xs muted">Nothing here yet at this budget.</p>
        )}

        <h3 className="ladder__label" data-testid="ladder-above">Above budget · {groups.above.length}</h3>
        {groups.above.length > 0 && <ol className="ladder__list">{aboveShown.map((r) => row(r, 'above'))}</ol>}

        <h3 className="ladder__label" data-testid="ladder-unknown">Cost not computed · {groups.unknown.length}</h3>
        {groups.unknown.length > 0 && (
          <ul className="ladder__list">
            {unknownShown.map(({ result, reason }) => (
              <li key={result.id}>
                <button
                  type="button"
                  className="ladder__row ladder__row--unknown"
                  onClick={() => onOpen(result.id)}
                  data-testid={`ladder-row-${result.id}`}
                >
                  <span className="ladder__name">
                    <span className="ladder__uni">{result.university}</span>
                    <span className="ladder__prog">{result.program}</span>
                  </span>
                  <span className="ladder__reason">{reason}</span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {(hidden > 0 || showAll) && (
          <button type="button" className="btn btn--sm btn--ghost" onClick={() => setShowAll(!showAll)}>
            {showAll ? 'Show fewer' : `Show ${hidden} more`}
          </button>
        )}
      </div>
    </section>
  );
}

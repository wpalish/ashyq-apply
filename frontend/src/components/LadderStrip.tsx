/**
 * The budget ladder as the concept draws it on Find: one strip of four bands -
 * within the family's budget, up to twice it, above that, and not computed -
 * each with its count. A band is a filter: tapping it shows only its passes.
 *
 * The bands are counted with the same rule as the full ladder
 * (`groupByBudget`): the ceiling from Preferences, compared only in its own
 * currency. A row whose cost could not be computed is counted as such, never
 * as 0, and nothing here is a chance of anything.
 */

import { groupByBudget, type Ceiling } from '@/components/BudgetLadder';
import type { ProgramResult } from '@/types';

export type Band = 'within' | 'near' | 'over' | 'unknown';

/** "6k" for round thousands, "6,500" otherwise. */
function short(amount: number): string {
  return amount >= 1000 && amount % 1000 === 0 ? `${amount / 1000}k` : Math.round(amount).toLocaleString('en-US');
}

/** Which band a programme falls in against the ceiling. */
export function bandsOf(results: ProgramResult[], ceiling: Ceiling): Map<string, Band> {
  const groups = groupByBudget(results, ceiling);
  const bands = new Map<string, Band>();
  for (const r of groups.within) bands.set(r.id, 'within');
  for (const r of groups.above) {
    const amount = r.funding_gap?.gap?.amount ?? 0;
    bands.set(r.id, ceiling.amount > 0 && amount <= ceiling.amount * 2 ? 'near' : 'over');
  }
  for (const { result } of groups.unknown) bands.set(result.id, 'unknown');
  return bands;
}

export function LadderStrip({ results, ceiling, band, onBand }: {
  results: ProgramResult[];
  ceiling: Ceiling;
  /** The band the list is narrowed to, if any. */
  band: Band | null;
  onBand: (band: Band | null) => void;
}) {
  const bands = bandsOf(results, ceiling);
  const count = (b: Band) => [...bands.values()].filter((x) => x === b).length;
  const c = ceiling.amount;
  const all: { id: Band; label: string; spoken: string }[] = [
    { id: 'within', label: `up to ${short(c)}`, spoken: `up to ${c.toLocaleString('en-US')} ${ceiling.currency}, within your budget` },
    ...(c > 0 ? [{ id: 'near' as Band, label: `${short(c)}–${short(c * 2)}`, spoken: `${c.toLocaleString('en-US')} to ${(c * 2).toLocaleString('en-US')} ${ceiling.currency}` }] : []),
    { id: 'over', label: `over ${short(c > 0 ? c * 2 : c)}`, spoken: `over ${(c > 0 ? c * 2 : c).toLocaleString('en-US')} ${ceiling.currency}` },
    { id: 'unknown', label: 'not computed', spoken: 'cost not computed' },
  ];
  const lit = band ?? 'within';
  return (
    <section className="lstrip" aria-labelledby="lstrip-title" data-testid="ladder-strip">
      <h2 className="lstrip__title" id="lstrip-title">Left to pay a year, if awarded · {ceiling.currency}</h2>
      <div className="lstrip__bands" role="group" aria-label="Show programmes by what is left to pay">
        {all.map((b) => {
          const n = count(b.id);
          return (
            <button
              key={b.id}
              type="button"
              className={`lstrip__band${lit === b.id ? ' is-lit' : ''}`}
              style={{ flexGrow: Math.max(n, 1) }}
              aria-pressed={band === b.id}
              aria-label={`${n} programme${n === 1 ? '' : 's'} ${b.spoken}`}
              onClick={() => onBand(band === b.id ? null : b.id)}
              data-testid={`band-${b.id}`}
            >
              <span className="lstrip__bar" aria-hidden="true" />
              <span className="lstrip__n" aria-hidden="true">{n}</span>
              <span className="lstrip__label" aria-hidden="true">{b.label}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

/**
 * The countries in the results, each in its route tint (lib/passColour), with
 * how many programmes it has - the key to the routes on a night globe.
 */

import type { PassColour } from '@/lib/passColour';
import type { ProgramResult } from '@/types';

export function CountryLegend({ results, passes, shown = 5, className = '' }: {
  results: ProgramResult[];
  passes: Map<string, PassColour>;
  /** How many countries are named before "+N more countries". */
  shown?: number;
  className?: string;
}) {
  const counts = new Map<string, number>();
  for (const r of results) counts.set(r.country, (counts.get(r.country) ?? 0) + 1);
  const order = [...passes.keys()].filter((c) => counts.has(c));
  const named = order.slice(0, shown);
  return (
    <ul className={`legend${className ? ` ${className}` : ''}`} aria-label="Countries in the results">
      {named.map((c) => (
        <li key={c} style={{ ['--tint' as string]: `var(--pass-tint-${passes.get(c)?.slot ?? 1})` }}>
          {c} {counts.get(c)}
        </li>
      ))}
      {order.length > named.length && <li className="legend__more">+{order.length - named.length} more countries</li>}
    </ul>
  );
}

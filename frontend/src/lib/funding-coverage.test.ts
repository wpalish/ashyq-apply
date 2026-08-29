import { describe, expect, it } from 'vitest';
import { uncoveredCategories } from '@/lib/format';
import type { CoverageBreakdown, Money } from '@/types';

const money = (amount: number): Money => ({
  amount, currency: 'USD', academic_year: '2026/27',
  is_estimate: false, range_low: null, range_high: null,
});

const cover = (category: string, covered: string): CoverageBreakdown =>
  ({ category, covered, amount: null, claim_ids: [] }) as never;

describe('what a "full ride" does not cover', () => {
  /**
   * A student was shown "Full ride" and, in the next column, a remaining cost
   * per year that was not zero. Both were true — the award covers tuition,
   * fees, housing and meals, and the university also publishes insurance,
   * books and travel — but side by side with nothing joining them they read as
   * a contradiction, and the one a student is likelier to believe is the one
   * that says they have nothing to pay.
   */
  it('names the categories the award does not cover', () => {
    const uncovered = uncoveredCategories(
      [cover('tuition', 'yes'), cover('housing', 'yes'), cover('insurance', 'no')],
      { insurance: money(900), books: money(400) },
    );
    expect(uncovered).toContain('insurance');
    expect(uncovered).toContain('books');
    expect(uncovered).not.toContain('tuition');
  });

  it('treats an unknown coverage as uncovered, never as covered', () => {
    /** Silence is not permission anywhere else in this product either. */
    const uncovered = uncoveredCategories(
      [cover('insurance', 'unknown')],
      { insurance: money(900) },
    );
    expect(uncovered).toContain('insurance');
  });

  it('says nothing when the award covers everything the university publishes', () => {
    const uncovered = uncoveredCategories(
      [cover('tuition', 'yes'), cover('housing', 'yes')],
      { tuition: money(1), housing: money(2) },
    );
    expect(uncovered).toEqual([]);
  });

  it('does not invent a category the university never published a cost for', () => {
    /** An award silent about travel, on a university that publishes no travel
     * cost, leaves nothing unpaid. Listing it would manufacture a worry. */
    const uncovered = uncoveredCategories([cover('tuition', 'yes')], { tuition: money(1) });
    expect(uncovered).toEqual([]);
  });
});

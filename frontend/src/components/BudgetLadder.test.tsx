/**
 * The budget ladder groups rows by what is left to pay, against the same
 * ceiling the ranking uses, and never converts or invents a number.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { BudgetLadder, ceilingFrom, groupByBudget } from './BudgetLadder';
import type { ProgramResult } from '@/types';

function row(id: string, gap: number | null, overrides: Record<string, unknown> = {}): ProgramResult {
  return {
    id,
    university: `University ${id}`,
    program: 'BSc Computing',
    funding_gap: gap === null
      ? { computable: false, gap: null, reason: 'Cost is published for 2026/27 but the award for 2024/25. More text.' }
      : { computable: true, gap: { amount: gap, currency: 'USD', academic_year: '2026/27' }, reason: '' },
    ...overrides,
  } as unknown as ProgramResult;
}

describe('the ceiling', () => {
  it('prefers the acceptable gap, as the ranking does', () => {
    expect(ceilingFrom({ funding: { max_acceptable_gap: 4000, max_annual_budget: 9000, budget_currency: 'usd' } }))
      .toEqual({ amount: 4000, currency: 'USD' });
  });

  it('falls back to the annual budget', () => {
    expect(ceilingFrom({ funding: { max_acceptable_gap: null, max_annual_budget: 6000 } }))
      .toEqual({ amount: 6000, currency: 'USD' });
  });

  it('keeps an explicit zero instead of treating it as missing', () => {
    expect(ceilingFrom({ funding: { max_acceptable_gap: 0, max_annual_budget: 6000 } })?.amount).toBe(0);
  });

  it('shows no ladder without a budget', () => {
    expect(ceilingFrom(null)).toBeNull();
    expect(ceilingFrom({ funding: {} })).toBeNull();
  });
});

describe('grouping', () => {
  const ceiling = { amount: 6000, currency: 'USD' };

  it('puts a row exactly at the ceiling within budget, cheapest first', () => {
    const groups = groupByBudget([row('b', 6000), row('a', 1848), row('c', 7554)], ceiling);
    expect(groups.within.map((r) => r.id)).toEqual(['a', 'b']);
    expect(groups.above.map((r) => r.id)).toEqual(['c']);
  });

  it('keeps an uncomputed cost with its reason, never as zero', () => {
    const groups = groupByBudget([row('x', null)], ceiling);
    expect(groups.within).toHaveLength(0);
    expect(groups.unknown[0]?.reason).toBe('Cost is published for 2026/27 but the award for 2024/25.');
  });

  it('refuses to compare across currencies', () => {
    const kzt = { amount: 2_000_000, currency: 'KZT' };
    const groups = groupByBudget([row('a', 1848)], kzt);
    expect(groups.within).toHaveLength(0);
    expect(groups.unknown[0]?.reason).toMatch(/does not convert/);
  });
});

describe('the ladder', () => {
  it('names every row with its amount, and opens it on click', () => {
    const onOpen = vi.fn();
    render(<BudgetLadder results={[row('a', 1848), row('c', 7554), row('x', null)]} ceiling={{ amount: 6000, currency: 'USD' }} onOpen={onOpen} />);
    expect(screen.getByTestId('ladder-within')).toHaveTextContent('Within budget · 1');
    expect(screen.getByTestId('ladder-above')).toHaveTextContent('Above budget · 1');
    expect(screen.getByTestId('ladder-unknown')).toHaveTextContent('Cost not computed · 1');
    const first = screen.getByRole('button', { name: /University a.*1,848 USD a year, within your budget/ });
    fireEvent.click(first);
    expect(onOpen).toHaveBeenCalledWith('a');
  });

  it('never says chance or shows a percentage', () => {
    render(<BudgetLadder results={[row('a', 1848)]} ceiling={{ amount: 6000, currency: 'USD' }} onOpen={() => {}} />);
    const text = screen.getByTestId('budget-ladder').textContent ?? '';
    expect(text).not.toMatch(/%|probab/i);
    expect(text).toMatch(/not an estimate of your chances/);
    // The grants it subtracts are mostly competitive; the ladder must say so.
    expect(text).toMatch(/Most of those grants are competitive/);
    expect(text).toMatch(/not a promise/);
  });

  it('shows three above budget and hides the rest behind a button', () => {
    const many = [row('a', 7000), row('b', 8000), row('c', 9000), row('d', 10000), row('e', 11000)];
    render(<BudgetLadder results={many} ceiling={{ amount: 6000, currency: 'USD' }} onOpen={() => {}} />);
    expect(screen.queryByTestId('ladder-row-d')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Show 2 more' }));
    expect(screen.getByTestId('ladder-row-e')).toBeInTheDocument();
  });
});

/**
 * The money as arithmetic: the backend's figures, the published currency and
 * the rate date when converted, and what the grant covers and leaves out.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MoneyArithmetic } from './MoneyArithmetic';
import type { ProgramResult } from '@/types';

const usd = (amount: number) => ({ amount, currency: 'USD', academic_year: '2026/27' });
const eur = (amount: number) => ({ amount, currency: 'EUR', academic_year: '2026/27' });

function groningen(overrides: Partial<ProgramResult> = {}): ProgramResult {
  return {
    id: 'r1',
    best_funding_classification: 'FULL_RIDE_CONFIRMED',
    costs: {
      total: eur(30050),
      items: { tuition: eur(16500), mandatory_fees: eur(600), housing: eur(7200), meals: eur(3600), health_insurance: eur(1450), books: eur(700) },
    },
    scholarships: [{
      name: 'Groningen Talent Grant',
      classification: 'FULL_RIDE_CONFIRMED',
      amount: eur(28350),
      coverage: [
        { category: 'tuition', covered: 'yes' },
        { category: 'mandatory_fees', covered: 'yes' },
        { category: 'housing', covered: 'yes' },
        { category: 'meals', covered: 'yes' },
      ],
      source_urls: ['https://www.rug.nl/scholarships/talent-grant'],
      last_verified: '2026-09-14T10:00:00Z',
    }],
    funding_gap: {
      computable: true,
      gap: usd(1847.82),
      total_cost: usd(32663.04),
      confirmed_aid: usd(30815.22),
      reason: 'Remaining annual cost after officially published, applicable aid.',
      warnings: [
        "'Groningen Talent Grant' states it may not be combined with other awards.",
        "'Groningen Talent Grant' is awarded by competitive selection.",
      ],
    },
    ...overrides,
  } as unknown as ProgramResult;
}

describe('the money as arithmetic', () => {
  it('shows price − grants = left to pay with the backend figures', () => {
    render(<MoneyArithmetic result={groningen()} rate={{ date: '2026-08-01', source: 'Static snapshot' }} />);
    const sum = screen.getByTestId('money-sum');
    expect(sum).toHaveTextContent('32,663 USD');
    expect(sum).toHaveTextContent('30,815 USD');
    expect(sum).toHaveTextContent('1,848 USD');
    expect(sum).toHaveTextContent('grants, if awarded');
  });

  it('names the published currency and the rate date, and converts nothing itself', () => {
    render(<MoneyArithmetic result={groningen()} rate={{ date: '2026-08-01', source: 'Static snapshot' }} />);
    const note = screen.getByTestId('money-converted');
    expect(note).toHaveTextContent('Published in EUR: price 30,050 EUR, Groningen Talent Grant 28,350 EUR');
    expect(note).toHaveTextContent('Converted to USD with the rate snapshot of');
  });

  it('says what the grant covers and what the price includes that it does not', () => {
    render(<MoneyArithmetic result={groningen()} />);
    const coverage = screen.getByTestId('money-coverage');
    expect(coverage).toHaveTextContent('covers tuition, mandatory fees, housing, meals');
    expect(coverage).toHaveTextContent('Not covered: health insurance, books');
  });

  it('puts whether the grant can be won first', () => {
    render(<MoneyArithmetic result={groningen()} />);
    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('competitive selection');
  });

  it('gives the reason instead of a number when the remainder was not computed', () => {
    const result = groningen({
      funding_gap: {
        computable: false, gap: null, total_cost: usd(65367), confirmed_aid: usd(65441),
        reason: 'The cost and coverage figures are not comparable.', warnings: [],
      },
    } as unknown as Partial<ProgramResult>);
    render(<MoneyArithmetic result={result} />);
    expect(screen.queryByTestId('money-sum')).toBeNull();
    expect(screen.getByTestId('money-unknown')).toHaveTextContent('Not computed. The cost and coverage figures are not comparable.');
  });

  it('never states a chance', () => {
    const { container } = render(<MoneyArithmetic result={groningen()} />);
    expect(container.textContent).not.toMatch(/%|chance|probab/i);
  });
});

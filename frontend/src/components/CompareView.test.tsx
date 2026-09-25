/**
 * Programmes row by row: the same questions for each, nothing scored between
 * them, an unknown left as unknown.
 */

import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CompareView } from './CompareView';
import type { ProgramResult } from '@/types';

const usd = (amount: number) => ({ amount, currency: 'USD', academic_year: '2026/27' });

function programme(id: string, overrides: Partial<ProgramResult> = {}): ProgramResult {
  return {
    id,
    university: `University ${id}`,
    program: 'BSc Computing',
    eligibility: 'MET',
    admissions_fit: 'STRONGER_FIT',
    best_funding_classification: 'FULL_TUITION',
    requirement_checks: [],
    missing_prerequisites: [],
    scholarships: [{
      name: `Grant ${id}`, classification: 'FULL_TUITION',
      coverage: [{ category: 'tuition', covered: 'yes' }],
      source_urls: [], last_verified: null,
    }],
    costs: { total: usd(20000), items: { tuition: usd(12000), housing: usd(8000) } },
    funding_gap: {
      computable: true, gap: usd(8000), total_cost: usd(20000), confirmed_aid: usd(12000),
      reason: '', warnings: [],
    },
    admission_deadline: '2027-03-01',
    deadline_passed: false,
    source_urls: ['https://example.edu/programme'],
    last_verified: '2026-09-14T10:00:00Z',
    ...overrides,
  } as unknown as ProgramResult;
}

describe('comparing programmes', () => {
  it('asks each programme the same questions, one row each', () => {
    render(<CompareView programmes={[programme('a'), programme('b')]} onClose={() => {}} onRemove={() => {}} />);
    const table = screen.getByRole('table');
    for (const label of ['Left to pay a year', 'Price a year', 'Grant', 'The grant covers', 'Not covered', 'Requirements', 'Your profile', 'Deadline', 'Source']) {
      expect(within(table).getByRole('rowheader', { name: label })).toBeInTheDocument();
    }
    expect(within(table).getAllByRole('columnheader')).toHaveLength(2);
    const notCovered = within(table).getByRole('rowheader', { name: 'Not covered' }).closest('tr')!;
    expect(notCovered).toHaveTextContent('housing');
  });

  it('leaves an unknown remainder unknown, never zero', () => {
    const unknown = programme('b', {
      funding_gap: { computable: false, gap: null, total_cost: null, confirmed_aid: null, reason: 'No cost.', warnings: [] },
    } as unknown as Partial<ProgramResult>);
    render(<CompareView programmes={[programme('a'), unknown]} onClose={() => {}} onRemove={() => {}} />);
    const row = screen.getByRole('rowheader', { name: 'Left to pay a year' }).closest('tr')!;
    expect(row).toHaveTextContent('not computed');
    expect(row).not.toHaveTextContent(/\b0 USD/);
  });

  it('scores nothing and predicts nothing', () => {
    const { container } = render(<CompareView programmes={[programme('a'), programme('b')]} onClose={() => {}} onRemove={() => {}} />);
    expect(container.textContent).not.toMatch(/%|chance|probab|winner|better/i);
  });

  it('removes a programme and goes back, with focus on the heading first', () => {
    const onRemove = vi.fn();
    const onClose = vi.fn();
    render(<CompareView programmes={[programme('a'), programme('b')]} onClose={onClose} onRemove={onRemove} />);
    expect(screen.getByRole('heading', { name: 'Row by row' })).toHaveFocus();
    fireEvent.click(screen.getByRole('button', { name: 'Remove University a from the comparison' }));
    expect(onRemove).toHaveBeenCalledWith('a');
    fireEvent.click(screen.getByTestId('compare-close'));
    expect(onClose).toHaveBeenCalled();
  });
});

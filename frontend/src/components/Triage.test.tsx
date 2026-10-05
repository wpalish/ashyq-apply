/**
 * One programme at a time: the same decide() as the table, and a rejection
 * still asks why.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Triage } from './Triage';
import type { ProgramResult } from '@/types';

function row(id: string): ProgramResult {
  return {
    id,
    university: `University ${id}`,
    program: 'BSc Computing',
    city: 'Groningen',
    country: 'Netherlands',
    eligibility: 'PENDING',
    admissions_fit: 'STRONGER_FIT',
    best_funding_classification: 'FULL_RIDE_CONFIRMED',
    funding_gap: { computable: true, gap: { amount: 1848, currency: 'USD', academic_year: '2026/27' }, reason: '' },
    admission_deadline: '2027-05-01',
    deadline_passed: false,
    user_decision: 'undecided',
    user_notes: 'ask about housing',
  } as unknown as ProgramResult;
}

describe('triage', () => {
  it('shows one programme with its three judgements and its place in the queue', () => {
    render(<Triage queue={[row('a'), row('b')]} total={3} decide={vi.fn()} onClose={() => {}} />);
    expect(screen.getByText('2 of 3 to decide')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Groningen.*University a/ })).toBeInTheDocument();
    // The three answers stay three, each labelled.
    expect(screen.getByText('Requirements')).toBeInTheDocument();
    expect(screen.getByText('Your profile')).toBeInTheDocument();
    expect(screen.getByText('Money')).toBeInTheDocument();
    expect(screen.getByTestId('triage-card-a')).toHaveTextContent('1,848USD a year left to pay');
  });

  it('never lets a remaining cost read as a grant already won', () => {
    const r = row('a');
    r.funding_gap = {
      ...r.funding_gap!,
      total_cost: { amount: 32663, currency: 'USD', academic_year: '2026/27' },
      confirmed_aid: { amount: 30815, currency: 'USD', academic_year: '2026/27' },
      warnings: [
        "'Talent Grant' is open to this applicant by published criteria and is awarded by competitive selection.",
        'second caveat',
        'third caveat is not shown on the card',
      ],
    } as ProgramResult['funding_gap'];
    render(<Triage queue={[r]} total={1} decide={vi.fn()} onClose={() => {}} />);
    expect(screen.getByTestId('triage-card-a')).toHaveTextContent('USD a year left to pay, if awarded');
    expect(screen.getByTestId('triage-price')).toHaveTextContent('price 32,663 USD before grants');
    const caveats = screen.getByTestId('triage-caveats');
    expect(caveats).toHaveTextContent('awarded by competitive selection');
    expect(caveats).toHaveTextContent('second caveat');
    expect(caveats).not.toHaveTextContent('third caveat');
  });

  it('adds no price line when no aid was subtracted', () => {
    render(<Triage queue={[row('a')]} total={1} decide={vi.fn()} onClose={() => {}} />);
    expect(screen.queryByTestId('triage-price')).not.toBeInTheDocument();
    expect(screen.queryByTestId('triage-caveats')).not.toBeInTheDocument();
  });

  it('shows an earlier cycle\'s deadline as a guide, never as passed', () => {
    const r = { ...row('a'), admission_deadline: null, previous_cycle_deadline: '2026-01-15' } as ProgramResult;
    render(<Triage queue={[r]} total={1} decide={vi.fn()} onClose={() => {}} />);
    const card = screen.getByTestId('triage-card-a');
    expect(card).toHaveTextContent('not found');
    expect(card).toHaveTextContent(/previous cycle/);
    expect(card).not.toHaveTextContent('passed');
  });

  it('keeps and maybes go straight through decide(), keeping the notes', async () => {
    const decide = vi.fn().mockResolvedValue(undefined);
    render(<Triage queue={[row('a')]} total={1} decide={decide} onClose={() => {}} />);
    fireEvent.click(screen.getByTestId('triage-approve'));
    await waitFor(() => expect(decide).toHaveBeenCalledWith('a', 'approved', '', 'ask about housing'));
  });

  it('asks why before rejecting, and the reason is optional', async () => {
    const decide = vi.fn().mockResolvedValue(undefined);
    render(<Triage queue={[row('a')]} total={1} decide={decide} onClose={() => {}} />);
    fireEvent.click(screen.getByTestId('triage-reject'));
    expect(decide).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'no funding' }));
    fireEvent.click(screen.getByTestId('triage-reject-save'));
    await waitFor(() => expect(decide).toHaveBeenCalledWith('a', 'rejected', 'no funding', 'ask about housing'));
  });

  it('keeps the focus in place when the reasons open and when they are cancelled', () => {
    render(<Triage queue={[row('a')]} total={1} decide={vi.fn()} onClose={() => {}} />);
    fireEvent.click(screen.getByTestId('triage-reject'));
    // The button that was pressed is gone; the first reason has the focus.
    expect(screen.getByRole('button', { name: 'cost' })).toHaveFocus();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByTestId('triage-reject')).toHaveFocus();
  });

  it('moves focus to the next programme after an answer', async () => {
    const decide = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(<Triage queue={[row('a'), row('b')]} total={2} decide={decide} onClose={() => {}} />);
    expect(screen.getByRole('heading', { name: /University a/ })).toHaveFocus();
    fireEvent.click(screen.getByTestId('triage-reject'));
    fireEvent.click(screen.getByTestId('triage-reject-save'));
    await waitFor(() => expect(decide).toHaveBeenCalled());
    rerender(<Triage queue={[row('b')]} total={2} decide={decide} onClose={() => {}} />);
    expect(screen.getByRole('heading', { name: /University b/ })).toHaveFocus();
  });

  it('says so when every programme has an answer', () => {
    const onClose = vi.fn();
    render(<Triage queue={[]} total={4} decide={vi.fn()} onClose={onClose} />);
    expect(screen.getByText('Every programme has an answer')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('triage-close'));
    expect(onClose).toHaveBeenCalled();
  });

  describe('the pass on the table', () => {
    it('wears its country colour, with the next ones fanned behind it', () => {
      const tokyo = { ...row('b'), city: 'Tokyo', country: 'Japan' } as ProgramResult;
      const colourOf = (c: string) => (c === 'Japan' ? { slot: 3, pattern: false } : { slot: 1, pattern: false });
      const { container } = render(
        <Triage queue={[row('a'), tokyo, row('c')]} total={3} decide={vi.fn()} onClose={() => {}} colourOf={colourOf} />,
      );
      expect(screen.getByTestId('triage-card-a').getAttribute('style')).toContain('--pass-1');
      const behind = container.querySelectorAll('.triage__behind');
      expect(behind).toHaveLength(2);
      expect(behind[0]?.getAttribute('style')).toContain('--pass-3');
    });

    it('prints the route home with both ends named, and none without a home', () => {
      const { rerender } = render(<Triage queue={[row('a')]} total={1} decide={vi.fn()} onClose={() => {}} home="Astana" />);
      expect(screen.getByRole('figure', { name: 'Route from Groningen to Astana' })).toBeInTheDocument();
      rerender(<Triage queue={[row('a')]} total={1} decide={vi.fn()} onClose={() => {}} home={null} />);
      expect(screen.queryByRole('figure')).toBeNull();
    });
  });
});

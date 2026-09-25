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
    expect(screen.getByRole('heading', { name: 'University a' })).toBeInTheDocument();
    expect(screen.getByText('Eligibility')).toBeInTheDocument();
    expect(screen.getByText('Admissions fit')).toBeInTheDocument();
    expect(screen.getByText('Funding')).toBeInTheDocument();
    expect(screen.getByText('1,848 USD')).toBeInTheDocument();
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

  it('says so when every programme has an answer', () => {
    const onClose = vi.fn();
    render(<Triage queue={[]} total={4} decide={vi.fn()} onClose={onClose} />);
    expect(screen.getByText('Every programme has an answer')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('triage-close'));
    expect(onClose).toHaveBeenCalled();
  });
});

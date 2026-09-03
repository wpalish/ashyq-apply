/**
 * Rejections keep their reason.
 *
 * The product and the README both promise it, and the API has always accepted
 * `reason` — the UI simply sent an empty string, so every rejection was
 * recorded as "no reason given".
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ShortlistScreen } from './ShortlistScreen';
import type { ProgramResult } from '@/types';

const decide = vi.fn().mockResolvedValue(undefined);

vi.mock('@/lib/store', () => ({
  useStore: () => ({ results: [row], summary: null, decide }),
}));

let row: ProgramResult;

function makeRow(overrides: Partial<ProgramResult> = {}): ProgramResult {
  return {
    id: 'result-1',
    run_id: 'run-1',
    university: 'University of Groningen',
    university_id: 'netherlands::groningen',
    country: 'Netherlands',
    city: 'Groningen',
    program: 'BSc Computing Science',
    degree: 'bachelor',
    intake: 'fall 2027',
    eligibility: 'MET',
    admissions_fit: 'PLAUSIBLE_FIT',
    funding_fit: 'LIMITED_OPPORTUNITY',
    best_funding_classification: 'NO_AWARD_FOUND',
    rankings: [],
    requirement_checks: [],
    claims: [],
    conflicts: [],
    unresolved: [],
    scholarships: [],
    source_urls: [],
    user_decision: 'undecided',
    user_decision_reason: '',
    user_notes: '',
    ...overrides,
  } as unknown as ProgramResult;
}

beforeEach(() => {
  decide.mockClear();
  row = makeRow();
});

describe('rejecting a programme', () => {
  it('asks for a reason instead of silently sending an empty one', () => {
    render(<ShortlistScreen />);
    fireEvent.click(screen.getByTestId('reject-result-1'));

    expect(screen.getByTestId('reject-reason-result-1')).toBeInTheDocument();
    expect(decide).not.toHaveBeenCalled();
  });

  it('records the reason typed by the applicant', async () => {
    render(<ShortlistScreen />);
    fireEvent.click(screen.getByTestId('reject-result-1'));
    fireEvent.change(screen.getByTestId('reject-input-result-1'), {
      target: { value: 'tuition is out of reach' },
    });
    fireEvent.click(screen.getByTestId('reject-save-result-1'));

    await waitFor(() =>
      expect(decide).toHaveBeenCalledWith('result-1', 'rejected', 'tuition is out of reach', ''),
    );
  });

  it('offers the common reasons as one click', async () => {
    render(<ShortlistScreen />);
    fireEvent.click(screen.getByTestId('reject-result-1'));
    fireEvent.click(screen.getByTestId('reject-chip-no-funding-result-1'));
    fireEvent.click(screen.getByTestId('reject-save-result-1'));

    await waitFor(() =>
      expect(decide).toHaveBeenCalledWith('result-1', 'rejected', 'no funding', ''),
    );
  });

  it('keeps the reason optional: saying No with nothing typed still works', async () => {
    render(<ShortlistScreen />);
    fireEvent.click(screen.getByTestId('reject-result-1'));
    fireEvent.click(screen.getByTestId('reject-save-result-1'));

    await waitFor(() => expect(decide).toHaveBeenCalledWith('result-1', 'rejected', '', ''));
  });

  it('shows the stored reason on a row already rejected', () => {
    row = makeRow({ user_decision: 'rejected', user_decision_reason: 'deadline passed' });
    render(<ShortlistScreen />);
    expect(screen.getByText(/Rejected: deadline passed/)).toBeInTheDocument();
  });

  it('does not ask for a reason when approving', async () => {
    render(<ShortlistScreen />);
    fireEvent.click(screen.getByTestId('approve-result-1'));

    await waitFor(() => expect(decide).toHaveBeenCalledWith('result-1', 'approved', '', ''));
    expect(screen.queryByTestId('reject-reason-result-1')).toBeNull();
  });
});

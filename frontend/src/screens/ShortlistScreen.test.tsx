/**
 * Rejections keep their reason.
 *
 * The product and the README both promise it, and the API has always accepted
 * `reason` — the UI simply sent an empty string, so every rejection was
 * recorded as "no reason given".
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ShortlistScreen } from './ShortlistScreen';
import type { ProgramResult } from '@/types';

const decide = vi.fn().mockResolvedValue(undefined);
const saveNotes = vi.fn().mockResolvedValue(undefined);

vi.mock('@/lib/store', () => ({
  useStore: () => ({ results: [row], summary, shortlist: null, decide, saveNotes }),
}));

let row: ProgramResult;
// The filters are built from the summary the API returns, not from the rows.
const summary = {
  total: 1,
  by_eligibility: { MET: 1, NEEDS_OFFICIAL_CLARIFICATION: 2 },
  by_funding: { FULL_RIDE_CONFIRMED: 1 },
  by_decision: { undecided: 1 },
  with_conflicts: 0,
  with_open_questions: 0,
  demo_data: true,
};

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
  saveNotes.mockClear();
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

describe('filter labels', () => {
  it('offers readable statuses, not raw enum tokens', () => {
    render(<ShortlistScreen />);
    const eligibility = screen.getByLabelText('Eligibility');

    expect(eligibility).toHaveTextContent('Met');
    expect(eligibility).not.toHaveTextContent('NEEDS_OFFICIAL_CLARIFICATION');
  });

  it('keeps the enum as the option value, so filtering still works', () => {
    render(<ShortlistScreen />);
    const option = screen
      .getByLabelText('Eligibility')
      .querySelector('option[value="MET"]');
    expect(option).not.toBeNull();
    expect(option?.textContent).toContain('Met');
  });
});

describe('notes', () => {
  it('saves a note without deciding the row', async () => {
    render(<ShortlistScreen />);
    fireEvent.click(screen.getByRole('button', { name: 'Add note' }));
    fireEvent.change(screen.getByTestId('note-input-result-1'), {
      target: { value: 'ask about housing' },
    });
    fireEvent.click(screen.getByTestId('note-save-result-1'));

    await waitFor(() => expect(saveNotes).toHaveBeenCalledWith('result-1', 'ask about housing'));
    expect(decide).not.toHaveBeenCalled();
  });
});


describe('the v2 ranking on the shortlist', () => {
  const ranking = (overrides: Record<string, unknown> = {}) => ({
    fit: 0.82,
    coverage: 0.94,
    sort_key: 0.79,
    gamma: 0.5,
    axes: [],
    unknown_axes: [],
    not_applicable_axes: [],
    knocked_out_by: [],
    bucket: 'PLAUSIBLE',
    bucket_reason: 'Requirements and funding both look reachable.',
    weights_source: 'priorities_roc',
    version: '2',
    disclaimer: 'Not a probability of admission.',
    ...overrides,
  });

  it('shows the match, what is confirmed, and the bucket', () => {
    row = makeRow({ ranking: ranking() } as Partial<ProgramResult>);
    render(<ShortlistScreen />);

    expect(screen.getByText('0.82')).toBeInTheDocument();
    const rankedTable = within(screen.getByTestId('shortlist-table'));
    expect(rankedTable.getByRole('columnheader', { name: 'Confirmed' })).toBeInTheDocument();
    expect(screen.getByTestId('coverage-result-1')).toHaveTextContent('94%');
    // Scoped to its own cell: PLAUSIBLE_FIT and the PLAUSIBLE bucket both read
    // "Plausible", and a bare text query lets the fit chip answer for the bucket.
    expect(document.querySelector('[data-label="Bucket"]')).toHaveTextContent('Plausible');
  });

  it('never presents the match as a probability', () => {
    row = makeRow({ ranking: ranking() } as Partial<ProgramResult>);
    render(<ShortlistScreen />);
    expect(screen.getByText(/not a probability of admission/i)).toBeInTheDocument();
  });

  it('moves an unaffordable row out of the ranked table into its own section', () => {
    row = makeRow({ ranking: ranking({ bucket: 'OUT_OF_BUDGET' }) } as Partial<ProgramResult>);
    render(<ShortlistScreen />);

    expect(screen.getByTestId('section-OUT_OF_BUDGET')).toBeInTheDocument();
    expect(screen.queryByTestId('shortlist-table')).toBeNull();
  });

  it('keeps a row assessed before v2 in the ranked table', () => {
    render(<ShortlistScreen />);
    expect(screen.getByTestId('shortlist-table')).toBeInTheDocument();
  });
});

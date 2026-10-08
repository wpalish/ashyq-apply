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
const rerank = vi.fn();
const startRun = vi.fn();
const collectDocuments = vi.fn();
const refreshResults = vi.fn();
const { universities } = vi.hoisted(() => ({
  universities: vi.fn().mockResolvedValue({ items: [], countries: [], total: 0, catalogue_total: 0, seed_count: 0 }),
}));
vi.mock('@/api/client', () => ({ api: { universities } }));

vi.mock('@/lib/store', () => ({
  useStore: () => ({ results: [row, ...additionalRows], summary, shortlist: null, decide, saveNotes, rerank, startRun, collectDocuments, refreshResults }),
}));

let row: ProgramResult;
let additionalRows: ProgramResult[];
// The filters are built from the summary the API returns, not from the rows.
const summary = {
  total: 1,
  by_eligibility: { MET: 1, NEEDS_OFFICIAL_CLARIFICATION: 2 },
  by_funding: { FULL_RIDE_CONFIRMED: 1, UNKNOWN: 1 },
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
  for (const action of [rerank, startRun, collectDocuments, refreshResults, universities]) action.mockClear();
  additionalRows = [];
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

describe('Find search', () => {
  it.each(['approved', 'maybe'] as const)('removes a saved %s programme instead of changing its decision silently', async (decision) => {
    row = makeRow({ user_decision: decision, user_notes: 'Keep this note' });
    render(<ShortlistScreen />);
    fireEvent.click(screen.getByRole('button', { name: /^Saved$/ }));
    await waitFor(() => expect(decide).toHaveBeenCalledWith(row.id, 'undecided', '', 'Keep this note'));
  });

  it('filters by university, programme and country without changing the saved results', () => {
    render(<ShortlistScreen />);
    const search = screen.getByPlaceholderText('Search universities, programmes or countries…');
    expect(screen.getByTestId('card-result-1')).toBeInTheDocument();
    fireEvent.change(search, { target: { value: 'Toronto' } });
    expect(screen.queryByTestId('card-result-1')).not.toBeInTheDocument();
    expect(screen.getByText('Nothing matches these filters yet.')).toBeInTheDocument();
    fireEvent.change(search, { target: { value: 'netherlands' } });
    expect(screen.getByTestId('card-result-1')).toBeInTheDocument();
  });

  it('opens a source-backed result and compares only selected programmes', () => {
    render(<ShortlistScreen />);
    fireEvent.click(screen.getByTestId('card-expand-result-1'));
    expect(screen.getByTestId('card-expand-result-1')).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(screen.getByRole('button', { name: /^Compare$/ }));
    expect(screen.getByRole('button', { name: 'Compare (1)' })).toBeEnabled();
    expect(screen.getByRole('region', { name: 'Compare selected programmes' })).toHaveTextContent('University of Groningen');
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


describe('visible active filters', () => {
  const search = () => screen.getByPlaceholderText('Search universities, programmes or countries…');
  const labels = ['Search: Groningen', 'List: Saved', 'Country: Netherlands', 'Eligibility: Met', 'Funding: Full ride', 'Hide rejected'];

  function twoResults() {
    row = makeRow({ user_decision: 'maybe', best_funding_classification: 'FULL_RIDE_CONFIRMED' });
    additionalRows = [makeRow({ id: 'result-2', university: 'Canadian Example', country: 'Canada', user_decision: 'rejected' })];
  }

  function applyFilters() {
    fireEvent.change(search(), { target: { value: 'Groningen' } });
    fireEvent.click(screen.getByRole('tab', { name: 'Saved' }));
    fireEvent.change(screen.getByLabelText('Country'), { target: { value: 'Netherlands' } });
    fireEvent.change(screen.getByLabelText('Eligibility'), { target: { value: 'MET' } });
    fireEvent.change(screen.getByLabelText('Funding'), { target: { value: 'FULL_RIDE_CONFIRMED' } });
    fireEvent.click(screen.getByLabelText('Hide rejected'));
  }

  it('keeps a readable removal button outside collapsed Filters and shows filtered / total', () => {
    twoResults();
    render(<ShortlistScreen />);
    fireEvent.change(screen.getByLabelText('Country'), { target: { value: 'Netherlands' } });
    const chip = screen.getByRole('button', { name: 'Remove filter: Country: Netherlands' });
    expect(chip.closest('details')).toBeNull();
    expect(document.getElementById('find-filters')).not.toHaveAttribute('open');
    expect(screen.getByText('Showing 1 of 2 results from this research run')).toBeInTheDocument();
    expect(screen.queryByTestId('card-result-2')).not.toBeInTheDocument();
  });

  it.each(labels)('removes only %s and leaves the other active filters in place', (removed) => {
    twoResults();
    render(<ShortlistScreen />);
    applyFilters();
    fireEvent.click(screen.getByRole('button', { name: `Remove filter: ${removed}` }));
    for (const label of labels) {
      if (label === removed) expect(screen.queryByRole('button', { name: `Remove filter: ${label}` })).not.toBeInTheDocument();
      else expect(screen.getByRole('button', { name: `Remove filter: ${label}` })).toBeInTheDocument();
    }
    expect(search()).toHaveValue(removed === 'Search: Groningen' ? '' : 'Groningen');
    expect(screen.getByRole('tab', { name: removed === 'List: Saved' ? 'All' : 'Saved' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByLabelText('Country')).toHaveValue(removed === 'Country: Netherlands' ? '' : 'Netherlands');
    expect(screen.getByLabelText('Eligibility')).toHaveValue(removed === 'Eligibility: Met' ? '' : 'MET');
    expect(screen.getByLabelText('Funding')).toHaveValue(removed === 'Funding: Full ride' ? '' : 'FULL_RIDE_CONFIRMED');
    expect(screen.getByLabelText('Hide rejected')).toHaveProperty('checked', removed !== 'Hide rejected');
    expect(decide).not.toHaveBeenCalled();
    expect(saveNotes).not.toHaveBeenCalled();
  });

  it('clears all filters locally while preserving sort, compare, notes and unknown evidence', async () => {
    twoResults();
    row.user_notes = 'Keep my shortlist note';
    additionalRows.push(makeRow({ id: 'result-3', university: 'Unknown Example', country: 'Canada', eligibility: 'NEEDS_OFFICIAL_CLARIFICATION', best_funding_classification: 'UNKNOWN' }));
    const original = JSON.stringify([row, ...additionalRows]);
    render(<ShortlistScreen />);
    fireEvent.click(within(screen.getByTestId('card-result-1')).getByRole('button', { name: 'Compare' }));
    fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'university' } });
    await waitFor(() => expect(universities).toHaveBeenCalledOnce());
    applyFilters();
    fireEvent.change(search(), { target: { value: 'No such programme' } });
    expect(screen.getByText('Showing 0 of 3 results from this research run')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Clear all filters' }));
    expect(screen.getByText('Showing 3 of 3 results from this research run')).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'Active filters' })).not.toBeInTheDocument();
    expect(search()).toHaveValue('');
    for (const field of ['Country', 'Eligibility', 'Funding']) expect(screen.getByLabelText(field)).toHaveValue('');
    expect(screen.getByLabelText('Hide rejected')).not.toBeChecked();
    expect(screen.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByLabelText('Sort by')).toHaveValue('university');
    expect(screen.getByRole('button', { name: 'Compare (1)' })).toBeEnabled();
    expect(screen.getByRole('region', { name: 'Compare selected programmes' })).toHaveTextContent('University of Groningen');
    const unknown = within(screen.getByTestId('card-result-3'));
    expect(unknown.getByText('Unverified')).toBeInTheDocument();
    expect(unknown.getByText('Unknown')).toBeInTheDocument();
    expect(unknown.getByText('Not enough comparable data')).toBeInTheDocument();
    expect(unknown.getByText('Not confirmed')).toBeInTheDocument();
    expect(JSON.stringify([row, ...additionalRows])).toBe(original);
    await new Promise((resolve) => setTimeout(resolve, 250));
    expect(universities).toHaveBeenCalledOnce(); // Existing catalogue mount only, no new load on clearing.
    for (const action of [decide, saveNotes, rerank, startRun, collectDocuments, refreshResults]) expect(action).not.toHaveBeenCalled();
  });

  it('uses the same local reset from the no-match recovery action', () => {
    twoResults();
    render(<ShortlistScreen />);
    applyFilters();
    fireEvent.change(search(), { target: { value: 'No such programme' } });
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(screen.getByText('Showing 2 of 2 results from this research run')).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'Active filters' })).not.toBeInTheDocument();
    expect(decide).not.toHaveBeenCalled();
    expect(saveNotes).not.toHaveBeenCalled();
  });

  it('does not describe whitespace-only search as an active filter', () => {
    twoResults();
    render(<ShortlistScreen />);
    fireEvent.change(search(), { target: { value: '   ' } });
    expect(screen.getByText('Showing 2 of 2 results from this research run')).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'Active filters' })).not.toBeInTheDocument();
  });

  it.each(['Priority', 'Saved', 'Exploring'])('makes %s list context removable without changing decisions', (label) => {
    twoResults();
    const decisions = [row.user_decision, additionalRows[0]!.user_decision];
    render(<ShortlistScreen />);
    fireEvent.click(screen.getByRole('tab', { name: label }));
    fireEvent.click(screen.getByRole('button', { name: `Remove filter: List: ${label}` }));
    expect(screen.getByRole('tab', { name: 'All' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Showing 2 of 2 results from this research run')).toBeInTheDocument();
    expect([row.user_decision, additionalRows[0]!.user_decision]).toEqual(decisions);
    expect(decide).not.toHaveBeenCalled();
  });
});

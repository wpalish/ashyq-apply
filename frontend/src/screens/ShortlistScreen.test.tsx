/**
 * Rejections keep their reason.
 *
 * The product and the README both promise it, and the API has always accepted
 * `reason` — the UI simply sent an empty string, so every rejection was
 * recorded as "no reason given".
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ShortlistScreen } from './ShortlistScreen';
import { setLocale } from '@/lib/i18n';
import type { ProgramResult, RunView } from '@/types';

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
  useStore: () => ({ profileDraft:{context:{intended_fields:['Computer Science']},funding:{}}, run, results: resultOverride ?? [row, ...additionalRows], summary, shortlist: null, decide, saveNotes, rerank, startRun, collectDocuments, refreshResults }),
}));

let row: ProgramResult;
let additionalRows: ProgramResult[];
let run: RunView | null;
let resultOverride: ProgramResult[] | null;
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
  setLocale('en');
  decide.mockClear();
  saveNotes.mockClear();
  for (const action of [rerank, startRun, collectDocuments, refreshResults, universities]) action.mockClear();
  additionalRows = [];
  run = null;
  resultOverride = null;
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
    await waitFor(() => expect(universities).not.toHaveBeenCalled());
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
    expect(universities).not.toHaveBeenCalled(); // Existing catalogue mount only, no new load on clearing.
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


describe('research recovery in Find', () => {
  function makeRun(overrides: Partial<RunView> = {}): RunView {
    return {
      id: 'run-1', profile_id: 'profile-1', stage: 'assessment', demo_mode: false,
      cancelled: false, progress: 0.5, candidates_found: 1, programs_verified: 0,
      pages_checked: 1, pages_failed: 0, claims_recorded: 0, results_count: 0,
      decided_count: 0, stages: [], errors: [], retry_urls: [], settings: {},
      created_at: '2026-10-09T00:00:00Z', started_at: null, finished_at: null,
      job_running: false, job_error: '', job_id: 'job-1', job_status: null,
      job_attempts: 1, candidate_limit: 10, verify_limit: 10, fetch_tiers: {},
      stale: false, worker_id: null, heartbeat_at: null, recovery_count: 0,
      ...overrides,
    };
  }

  function expectNoResearchMutation() {
    for (const action of [decide, saveNotes, rerank, startRun, collectDocuments, refreshResults]) {
      expect(action).not.toHaveBeenCalled();
    }
  }

  it.each([
    ['failed stage', { stage: 'failed' }],
    ['retryable stage', { stage: 'retryable_failed' }],
    ['cancelled stage', { stage: 'cancelled' }],
    ['cancelled flag despite a running job', { cancelled: true, job_status: 'running' }],
    ['stale despite a running job', { stale: true, job_running: true }],
    ['dead job', { job_status: 'dead' }],
    ['failed job', { job_status: 'failed' }],
    ['cancelled job', { job_status: 'cancelled' }],
  ] satisfies [string, Partial<RunView>][])('opens Progress for empty %s without starting work', async (_label, state) => {
    resultOverride = [];
    run = makeRun(state);
    const onStart = vi.fn();
    const onProgress = vi.fn();
    render(<ShortlistScreen onStart={onStart} onProgress={onProgress} />);
    await waitFor(() => expect(universities).not.toHaveBeenCalled());
    expect(screen.getByText('Research needs attention.')).toBeInTheDocument();
    expect(screen.getByText(/does not establish that no programmes match/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Start research/ })).not.toBeInTheDocument();
    expect(onProgress).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'View research progress' }));
    expect(onProgress).toHaveBeenCalledOnce();
    expect(onStart).not.toHaveBeenCalled();
    expectNoResearchMutation();
  });

  it.each(['awaiting_user_decision', 'completed'] as const)('reviews an empty %s run without claiming absence', async (stage) => {
    resultOverride = [];
    run = makeRun({ stage, job_status: 'succeeded' });
    const onStart = vi.fn();
    const onProgress = vi.fn();
    render(<ShortlistScreen onStart={onStart} onProgress={onProgress} />);
    await waitFor(() => expect(universities).not.toHaveBeenCalled());
    expect(screen.getByText('Review your research findings.')).toBeInTheDocument();
    expect(screen.getByText(/does not establish that no programmes match/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'View research progress' }));
    expect(onProgress).toHaveBeenCalledOnce();
    expect(onStart).not.toHaveBeenCalled();
    expectNoResearchMutation();
  });

  it.each(['queued', 'running'] as const)('shows progress for an empty %s job instead of a second start', async (job_status) => {
    resultOverride = [];
    run = makeRun({ job_status });
    const onStart = vi.fn();
    const onProgress = vi.fn();
    render(<ShortlistScreen onStart={onStart} onProgress={onProgress} />);
    await waitFor(() => expect(universities).not.toHaveBeenCalled());
    expect(screen.getByText('Research is in progress.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Start research/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'View research progress' }));
    expect(onProgress).toHaveBeenCalledOnce();
    expect(onStart).not.toHaveBeenCalled();
    expectNoResearchMutation();
  });

  it('shows an honest empty-run notice without an inert callback button', async () => {
    resultOverride = [];
    run = makeRun({ stale: true });
    render(<ShortlistScreen />);
    await waitFor(() => expect(universities).not.toHaveBeenCalled());
    expect(screen.getByText('Research needs attention.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'View research progress' })).not.toBeInTheDocument();
    expectNoResearchMutation();
  });

  it('keeps the existing Start route only when no run exists', async () => {
    resultOverride = [];
    const onStart = vi.fn();
    render(<ShortlistScreen onStart={onStart} onProgress={vi.fn()} />);
    await waitFor(() => expect(universities).not.toHaveBeenCalled());
    expect(screen.getByText('No results yet')).toBeInTheDocument();
    expect(onStart).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /Start research/ }));
    expect(onStart).toHaveBeenCalledOnce();
    expectNoResearchMutation();
  });

  it('retains partial rows, filters, compare, unsaved notes and unknowns when the run stops', async () => {
    row = makeRow({ user_decision: 'maybe', user_notes: 'Saved note', eligibility: 'NEEDS_OFFICIAL_CLARIFICATION', best_funding_classification: 'UNKNOWN' });
    additionalRows = [makeRow({ id: 'result-2', university: 'Canadian Example', country: 'Canada' })];
    const original = JSON.stringify([row, ...additionalRows]);
    run = makeRun({ job_status: 'running', results_count: 2 });
    const onProgress = vi.fn();
    const { rerender } = render(<ShortlistScreen onProgress={onProgress} />);
    await waitFor(() => expect(universities).not.toHaveBeenCalled());
    expect(screen.getByText('Research is in progress.')).toBeInTheDocument();
    fireEvent.click(within(screen.getByTestId('card-result-1')).getByRole('button', { name: 'Compare' }));
    fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'university' } });
    fireEvent.change(screen.getByPlaceholderText('Search universities, programmes or countries…'), { target: { value: 'Groningen' } });
    fireEvent.click(screen.getByRole('tab', { name: 'Saved' }));
    fireEvent.change(screen.getByLabelText('Country'), { target: { value: 'Netherlands' } });
    fireEvent.click(screen.getByRole('button', { name: 'Edit note' }));
    fireEvent.change(screen.getByTestId('note-input-result-1'), { target: { value: 'Unsaved housing question' } });
    run = makeRun({ stage: 'retryable_failed', job_status: 'failed', results_count: 2 });
    rerender(<ShortlistScreen onProgress={onProgress} />);
    expect(screen.getByText('Research needs attention.')).toBeInTheDocument();
    expect(screen.getByTestId('card-result-1')).toBeInTheDocument();
    expect(screen.queryByTestId('card-result-2')).not.toBeInTheDocument();
    expect(screen.getByText('Showing 1 of 2 results from this research run')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search universities, programmes or countries…')).toHaveValue('Groningen');
    expect(screen.getByRole('tab', { name: 'Saved' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByLabelText('Country')).toHaveValue('Netherlands');
    expect(screen.getByLabelText('Sort by')).toHaveValue('university');
    expect(screen.getByRole('button', { name: 'Remove filter: Country: Netherlands' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Compare (1)' })).toBeEnabled();
    expect(screen.getByRole('region', { name: 'Compare selected programmes' })).toHaveTextContent('University of Groningen');
    expect(screen.getByTestId('note-input-result-1')).toHaveValue('Unsaved housing question');
    expect(within(screen.getByTestId('card-result-1')).getByText('Unverified')).toBeInTheDocument();
    expect(within(screen.getByTestId('card-result-1')).getByText('Unknown')).toBeInTheDocument();
    expect(JSON.stringify([row, ...additionalRows])).toBe(original);
    fireEvent.click(screen.getByRole('button', { name: 'View research progress' }));
    expect(onProgress).toHaveBeenCalledOnce();
    expect(universities).not.toHaveBeenCalled();
    expectNoResearchMutation();
  });

  it('does not turn locally filtered-zero rows into a stopped or empty research run', async () => {
    run = makeRun({ stage: 'completed', job_status: 'succeeded', results_count: 1 });
    render(<ShortlistScreen onProgress={vi.fn()} />);
    await waitFor(() => expect(universities).not.toHaveBeenCalled());
    expect(screen.queryByText('Research needs attention.')).not.toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText('Search universities, programmes or countries…'), { target: { value: 'No local match' } });
    expect(screen.getByText('Showing 0 of 1 result from this research run')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Clear filters' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'View research progress' })).not.toBeInTheDocument();
    expectNoResearchMutation();
  });
});

it('opens a focused comparison and returns without losing the search or selection', () => {
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  render(<ShortlistScreen />);
  fireEvent.change(screen.getByLabelText('Search universities, programmes or countries'), { target: { value: 'Groningen' } });
  fireEvent.click(within(screen.getByTestId('card-result-1')).getByRole('button', { name: 'Compare' }));
  fireEvent.click(screen.getByRole('button', { name: 'Compare (1)' }));
  expect(screen.getByRole('heading', { name: 'Compare programmes' })).toHaveFocus();
  expect(screen.queryByTestId('card-result-1')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /Back to results/ }));
  expect(screen.getByLabelText('Search universities, programmes or countries')).toHaveValue('Groningen');
  expect(within(screen.getByTestId('card-result-1')).getByRole('button', { name: 'Remove' })).toHaveAttribute('aria-pressed', 'true');
});
it('drops obsolete comparison identifiers when the result set belongs to a new case or run', async () => {
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  const view = render(<ShortlistScreen />);
  fireEvent.click(within(screen.getByTestId('card-result-1')).getByRole('button', { name: 'Compare' }));
  fireEvent.click(screen.getByRole('button', { name: 'Compare (1)' }));
  resultOverride = [makeRow({ id: 'new-result', university: 'New case university' })];
  view.rerender(<ShortlistScreen />);
  await waitFor(() => expect(screen.getByRole('button', { name: 'Compare (0)' })).toBeDisabled());
  expect(screen.getByTestId('card-new-result')).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Compare programmes' })).not.toBeInTheDocument();
});


afterEach(()=>setLocale('en'));
describe('book result controls',()=>{
  it('filters real rows by degree and does not offer an unverified teaching language',()=>{
    setLocale('ru');
    additionalRows=[makeRow({id:'masters',degree:'master',university:'Masters Example'})];
    render(<ShortlistScreen/>);
    fireEvent.change(screen.getByLabelText('Степень',{exact:true}),{target:{value:'master'}});
    expect(screen.queryByTestId('card-result-1')).not.toBeInTheDocument();
    expect(screen.getByTestId('card-masters')).toBeInTheDocument();
    expect(within(screen.getByLabelText('Язык обучения',{exact:true})).getAllByRole('option')).toHaveLength(1);
    for(const action of [decide,saveNotes,rerank,startRun,collectDocuments,refreshResults]) expect(action).not.toHaveBeenCalled();
  });
  it('shows the nested programme from the same row and reports a refused decision',async()=>{
    setLocale('ru'); row=makeRow({user_notes:'Keep this note'});
    decide.mockRejectedValueOnce(new Error('Decision refused'));
    render(<ShortlistScreen/>);
    fireEvent.click(screen.getByTestId('card-expand-result-1'));
    expect(screen.getByRole('heading',{level:1,name:'University of Groningen'})).toHaveFocus();
    fireEvent.click(screen.getByRole('button',{name:'Добавить в план'}));
    await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('Decision refused'));
    expect(decide).toHaveBeenCalledWith('result-1','approved','','Keep this note');
    expect(screen.getByRole('button',{name:'Добавить в план'})).toBeEnabled();
    expect(screen.queryByRole('button',{name:/В твоём плане/})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'К результатам подбора'}));
    expect(screen.getByTestId('card-expand-result-1')).toHaveFocus();
  });
});

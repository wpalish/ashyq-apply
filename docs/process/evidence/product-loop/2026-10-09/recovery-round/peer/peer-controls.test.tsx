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
  useStore: () => ({ run, results: resultOverride ?? [row, ...additionalRows], summary, shortlist: null, decide, saveNotes, rerank, startRun, collectDocuments, refreshResults }),
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
  decide.mockClear();
  saveNotes.mockClear();
  for (const action of [rerank, startRun, collectDocuments, refreshResults, universities]) action.mockClear();
  additionalRows = [];
  run = null;
  resultOverride = null;
  row = makeRow();
});


function makeRun(overrides: Partial<RunView> = {}): RunView {
  return {
    id: 'run-1', profile_id: 'profile-1', stage: 'assessment', demo_mode: false,
    cancelled: false, progress: 0.5, candidates_found: 1, programs_verified: 0,
    pages_checked: 1, pages_failed: 0, claims_recorded: 0, results_count: 1,
    decided_count: 0, stages: [], errors: [], retry_urls: [], settings: {},
    created_at: '2026-10-09T00:00:00Z', started_at: null, finished_at: null,
    job_running: false, job_error: '', job_id: 'job-1', job_status: null,
    job_attempts: 1, candidate_limit: 10, verify_limit: 10, fetch_tiers: {},
    stale: false, worker_id: null, heartbeat_at: null, recovery_count: 0,
    ...overrides,
  };
}
function noMutation() {
  for (const fn of [decide, saveNotes, rerank, startRun, collectDocuments, refreshResults]) expect(fn).not.toHaveBeenCalled();
}

describe('Independent recovery state transitions', () => {
  it('keeps stopped filtered-zero results distinct from empty research and retains the exact comparison', async () => {
    row = makeRow({ user_decision: 'maybe', user_notes: 'Keep my question' });
    const original = JSON.stringify(row);
    run = makeRun({ stage: 'completed', job_status: 'succeeded', errors: ['Synthetic partial page limit'], unknowns: ['Synthetic scope remains unknown'] });
    const progress = vi.fn();
    const start = vi.fn();
    const { rerender } = render(<ShortlistScreen onProgress={progress} onStart={start} />);
    await waitFor(() => expect(universities).toHaveBeenCalledOnce());
    expect(screen.queryByRole('button', { name: 'View research progress' })).not.toBeInTheDocument();
    fireEvent.click(within(screen.getByTestId('card-result-1')).getByRole('button', { name: 'Compare' }));
    fireEvent.change(screen.getByPlaceholderText('Search universities, programmes or countries…'), { target: { value: 'No local row' } });
    run = makeRun({ stage: 'assessment', stale: true, job_status: 'running', errors: ['Synthetic partial page limit'], unknowns: ['Synthetic scope remains unknown'] });
    const stopped = JSON.stringify(run);
    rerender(<ShortlistScreen onProgress={progress} onStart={start} />);
    expect(screen.getByText('Research needs attention.')).toBeInTheDocument();
    expect(screen.queryByText('Research is in progress.')).not.toBeInTheDocument();
    expect(screen.getByText(/Existing findings remain available/)).toBeInTheDocument();
    expect(screen.queryByText(/No results have been returned/)).not.toBeInTheDocument();
    expect(screen.getByText('Showing 0 of 1 result from this research run')).toBeInTheDocument();
    expect(screen.queryByTestId('card-result-1')).not.toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Compare selected programmes' })).toHaveTextContent('University of Groningen');
    expect(screen.getByRole('button', { name: 'Compare (1)' })).toBeEnabled();
    expect(progress).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'View research progress' }));
    expect(progress).toHaveBeenCalledOnce();
    expect(start).not.toHaveBeenCalled();
    expect(JSON.stringify(row)).toBe(original);
    expect(JSON.stringify(run)).toBe(stopped);
    expect(universities).toHaveBeenCalledOnce();
    noMutation();
  });

  it('honours late optional callbacks and restores the completed populated native flow', async () => {
    row = makeRow({ user_decision: 'approved' });
    const original = JSON.stringify(row);
    run = makeRun({ stage: 'failed', job_status: 'running' });
    const start = vi.fn();
    const progress = vi.fn();
    const { rerender } = render(<ShortlistScreen onStart={start} />);
    await waitFor(() => expect(universities).toHaveBeenCalledOnce());
    expect(screen.getByText('Research needs attention.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'View research progress' })).not.toBeInTheDocument();
    run = makeRun({ stage: 'assessment', job_status: 'queued' });
    rerender(<ShortlistScreen onStart={start} onProgress={progress} />);
    expect(screen.getByText('Research is in progress.')).toBeInTheDocument();
    expect(progress).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'View research progress' }));
    expect(progress).toHaveBeenCalledOnce();
    run = makeRun({ stage: 'completed', job_status: 'succeeded' });
    rerender(<ShortlistScreen onStart={start} onProgress={progress} />);
    expect(screen.queryByText('Research needs attention.')).not.toBeInTheDocument();
    expect(screen.queryByText('Research is in progress.')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'View research progress' })).not.toBeInTheDocument();
    expect(screen.getByTestId('card-result-1')).toBeInTheDocument();
    expect(start).not.toHaveBeenCalled();
    expect(JSON.stringify(row)).toBe(original);
    expect(universities).toHaveBeenCalledOnce();
    noMutation();
  });
});

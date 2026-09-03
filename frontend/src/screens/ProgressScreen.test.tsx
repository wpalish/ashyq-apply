/**
 * Retry controls.
 *
 * The audited defect was a labelling lie: one button said "Retry from the
 * failed stage" and called the endpoint with no stage, which restarted the
 * whole pipeline. There are now two buttons and each does what it says.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProgressScreen } from './ProgressScreen';
import type { RunView } from '@/types';

const retryRun = vi.fn();

vi.mock('@/lib/store', () => ({
  useStore: () => ({ run: currentRun, cancelRun: vi.fn(), retryRun, results: [] }),
}));

let currentRun: RunView;

function makeRun(overrides: Partial<RunView> = {}): RunView {
  return {
    id: 'run-1',
    profile_id: 'profile-1',
    stage: 'failed',
    demo_mode: true,
    cancelled: false,
    progress: 0.6,
    candidates_found: 40,
    programs_verified: 20,
    pages_checked: 72,
    pages_failed: 13,
    claims_recorded: 104,
    candidate_limit: 40,
    verify_limit: 20,
    fetch_tiers: {},
    results_count: 20,
    decided_count: 1,
    stages: [
      { stage: 'profile_validation', status: 'done', detail: '', error: '', items_done: 0, items_total: 0, started_at: null, finished_at: null },
      { stage: 'candidate_discovery', status: 'done', detail: '', error: '', items_done: 0, items_total: 0, started_at: null, finished_at: null },
      { stage: 'program_verification', status: 'done', detail: '', error: '', items_done: 0, items_total: 0, started_at: null, finished_at: null },
      { stage: 'funding_discovery', status: 'failed', detail: '', error: 'timeout', items_done: 0, items_total: 0, started_at: null, finished_at: null },
      { stage: 'assessment', status: 'pending', detail: '', error: '', items_done: 0, items_total: 0, started_at: null, finished_at: null },
    ],
    errors: [],
    retry_urls: [],
    settings: {},
    created_at: '2026-09-01T10:00:00Z',
    started_at: '2026-09-01T10:00:01Z',
    finished_at: null,
    job_running: false,
    ...overrides,
  } as unknown as RunView;
}

beforeEach(() => {
  retryRun.mockReset();
  currentRun = makeRun();
});

describe('retry controls', () => {
  it('retries from the stage that actually stopped', () => {
    render(<ProgressScreen onDone={() => {}} />);
    fireEvent.click(screen.getByTestId('retry-stage'));
    expect(retryRun).toHaveBeenCalledWith('funding_discovery');
  });

  it('asks before re-running everything, and says decisions are kept', () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<ProgressScreen onDone={() => {}} />);
    fireEvent.click(screen.getByTestId('retry-run'));

    expect(confirm.mock.calls[0]?.[0]).toMatch(/approvals, rejections and notes are kept/);
    expect(retryRun).toHaveBeenCalledWith();
  });

  it('does not re-run when the confirmation is declined', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<ProgressScreen onDone={() => {}} />);
    fireEvent.click(screen.getByTestId('retry-run'));
    expect(retryRun).not.toHaveBeenCalled();
  });

  it('offers a re-run on a finished run, where there is no failed stage to resume', () => {
    currentRun = makeRun({ stage: 'awaiting_user_decision', stages: makeRun().stages.map((s) => ({ ...s, status: 'done' })) });
    render(<ProgressScreen onDone={() => {}} />);
    expect(screen.queryByTestId('retry-stage')).toBeNull();
    expect(screen.getByTestId('retry-run')).toBeInTheDocument();
  });
});

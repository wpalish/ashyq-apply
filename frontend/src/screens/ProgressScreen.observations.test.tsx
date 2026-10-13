import { render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProgressScreen } from './ProgressScreen';
import { setLocale } from '@/lib/i18n';
import type { ProgrammeObservation, RunView } from '@/types';

const { deadJobCount } = vi.hoisted(() => ({ deadJobCount: vi.fn() }));
vi.mock('@/api/client', () => ({ api: { deadJobCount } }));
vi.mock('@/lib/store', () => ({ useStore: () => ({
  run, results: [], cancelRun: vi.fn(), retryRun: vi.fn(), recheckNow: vi.fn(),
}) }));
let run: RunView;
const observation: ProgrammeObservation = {
  schema_version: 'programme-page-observation-v1', id: 'synthetic-page',
  institution: 'Synthetic University', domain: 'synthetic.edu',
  programme_url: 'https://synthetic.edu/bsc/computer-science', requested_degree: 'bachelor',
  confirmation_basis: 'existing_discovery_page_predicate', requirements_state: 'unknown',
  compatibility: 'not_assessed', reads: [{ content_hash: 'synthetic-hash',
    fetched_at: '2026-10-13T10:00:00Z', page_type: 'program_detail',
    classified_degree: 'bachelor', classified_subject: 'Computer Science' }],
  further_reads_omitted: false,
};

beforeEach(() => {
  setLocale('en');
  deadJobCount.mockResolvedValue(0);
  run = {
    id: 'synthetic-run', profile_id: 'synthetic-case', stage: 'failed', demo_mode: false,
    cancelled: false, progress: 0.1, candidates_found: 0, programs_verified: 0,
    pages_checked: 1, pages_failed: 1, claims_recorded: 0, results_count: 0,
    decided_count: 0, stages: [], errors: ['timeout'], retry_urls: [], settings: {},
    created_at: '2026-10-13T10:00:00Z', started_at: null, finished_at: null,
    job_running: false, job_error: 'timeout', job_id: 'synthetic-job', job_status: 'failed',
    job_attempts: 1, candidate_limit: 10, verify_limit: 10, fetch_tiers: {}, stale: false,
    worker_id: null, heartbeat_at: null, recovery_count: 0,
    programme_observations: [observation], programme_observation_state: 'readable',
    additional_programme_observations_omitted: false,
  };
});

describe('pages saved before optional enrichment', () => {
  it('shows the official page after failure without presenting an eligibility result', () => {
    render(<ProgressScreen onDone={() => {}} />);
    const panel = screen.getByTestId('programme-observations');
    expect(within(panel).getByRole('link')).toHaveAttribute('href', observation.programme_url);
    expect(panel).toHaveTextContent('Requirements are still unknown');
    expect(panel).toHaveTextContent('have not been assessed');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('needs attention');
    expect(screen.queryByText('Your opportunities are ready.')).toBeNull();
  });

  it('retains the page on remount and keeps cancellation explicit', () => {
    run = { ...run, stage: 'cancelled', cancelled: true, job_status: 'cancelled' };
    const first = render(<ProgressScreen onDone={() => {}} />);
    first.unmount();
    render(<ProgressScreen onDone={() => {}} />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('cancelled');
    expect(screen.getByTestId('programme-observations')).toHaveTextContent('Synthetic University');
  });

  it('does not turn corrupt or unavailable observations into programme absence', () => {
    run = { ...run, programme_observations: [], programme_observation_state: 'unavailable' };
    render(<ProgressScreen onDone={() => {}} />);
    expect(screen.getByTestId('observations-unavailable')).toHaveTextContent('does not mean that a programme is absent');
    expect(screen.queryByTestId('programme-observations')).toBeNull();
  });

  it('reads an older run without the additive fields', () => {
    delete run.programme_observations;
    delete run.programme_observation_state;
    render(<ProgressScreen onDone={() => {}} />);
    expect(screen.queryByTestId('programme-observations')).toBeNull();
    expect(screen.queryByTestId('observations-unavailable')).toBeNull();
  });

  it('reports an incomplete bounded list and uses the safe link renderer', () => {
    run = { ...run, additional_programme_observations_omitted: true,
      programme_observations: [{ ...observation, programme_url: 'javascript:alert(1)' }] };
    render(<ProgressScreen onDone={() => {}} />);
    const panel = screen.getByTestId('programme-observations');
    expect(within(panel).queryByRole('link')).toBeNull();
    expect(panel).toHaveTextContent('does not represent complete research');
  });
});

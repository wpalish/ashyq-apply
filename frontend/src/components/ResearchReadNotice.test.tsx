import { render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { ResearchReadNotice } from './ResearchReadNotice';
import { setLocale } from '@/lib/i18n';
import type { ResearchInputStatusRead } from '@/types';
let id = 'A'; let status: ResearchInputStatusRead | null;
vi.mock('@/lib/useResearchInputRead', () => ({ useResearchInputRead: () => ({ applicable: true, status, loading: false, error: '', refresh: vi.fn() }) }));
vi.mock('@/lib/store', () => ({ useStore: () => ({ currentAdmissionsCase: () => ({ scope: undefined, profile_id: id, case_epoch: 1 }), savedProfile: { id: 'A' }, run: { id: 'run-A', profile_id: 'A' },
  results: [{ id: 'r1', run_id: 'run-A', read_freshness: { schema_version: 'result-freshness-read-v1', observed_at: '2026-10-14T00:00:00Z', evidence: 'observed', stale_claim_count: 1, assessment: 'stored_evaluation' } }] }) }));
beforeEach(() => { id = 'A'; setLocale('en'); status = { schema_version: 'research-input-status-v1', state: 'changed', changed_sections: ['academics'], observed_at: '2026-10-14T00:00:00Z', applicability: 'not_assessed' }; });
it('shows exact changed section and historical source/evaluation limits without calculating a new result', () => {
  render(<ResearchReadNotice />); expect(screen.getByText('Your profile inputs have changed since this research.')).toBeInTheDocument();
  expect(screen.getByText(/Changed sections: Academic record/)).toBeInTheDocument(); expect(screen.getByText('Recorded assessment.')).toBeInTheDocument();
  expect(screen.getByText(/saved evaluation has not been recalculated/)).toBeInTheDocument();
});
it('hides all old-case read notices before another case rerenders its private records', () => {
  id = 'B'; render(<ResearchReadNotice />); expect(screen.queryByTestId('research-read-notice')).toBeNull();
});

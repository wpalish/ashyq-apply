import { render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { AdmissionsTodayPanel } from './AdmissionsTodayPanel';
import { emptyToday } from '@/test/admissionsTodayFixtures';
import { acceptedActions } from '@/test/admissionsFixtures';
import { setLocale } from '@/lib/i18n';
let value = emptyToday(); let error = '';
vi.mock('@/lib/useAdmissionsToday', () => ({ useAdmissionsToday: () => ({ profileId: 'A', value, loading: false, error, refresh: vi.fn() }) }));
vi.mock('@/lib/useAdmissionsActions', () => ({ useAdmissionsActions: () => ({ current: acceptedActions().current, refresh: vi.fn() }) }));
beforeEach(() => { value = emptyToday(); error = ''; setLocale('en'); });
it('shows personal tasks without research or a preparation plan and links the exact saved record', () => {
  value.action_state = 'readable'; value.action_revision = 1; value.action_digest = 'a'.repeat(64);
  value.undated_personal = [{ id: 'own-task-card', reason: 'personal_document_action', target: { kind: 'document_task', id: 'task-a' }, target_result_id: null,
    date: { local_date: null, timezone: null, certainty: 'unknown', comparison_zone: 'UTC', fallback_display_only: true, official_closure: 'not_assessed' },
    dependency_reasons: ['dependency_missing'], workload_origin: 'personal_unallocated', planned_minutes: null, source_state: 'applicant_entered', actionable: true }];
  render(<AdmissionsTodayPanel />); const card = screen.getByTestId('today-action');
  expect(within(card).getByRole('heading')).toHaveTextContent('Synthetic document task');
  expect(within(card).getByRole('link', { name: 'Open this record' })).toHaveAttribute('href', '#/documents?case=A&kind=document_task&id=task-a');
  expect(within(card).getByText('An earlier required task is unavailable.')).toBeInTheDocument();
  expect(screen.queryByText('Optional study actions')).toBeNull(); expect(card).not.toHaveTextContent('planned study minutes');
});
it('distinguishes unavailable data from an empty personal list and last-confirmed read', () => {
  value.action_state = 'unavailable'; value.action_revision = null; error = 'Synthetic API failure'; render(<AdmissionsTodayPanel />);
  expect(screen.getByText(/Showing the last confirmed view/)).toBeInTheDocument(); expect(screen.queryByText(/No active personal actions/)).toBeNull();
});

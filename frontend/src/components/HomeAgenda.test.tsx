import { render, screen, fireEvent } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { emptyToday } from '@/test/admissionsTodayFixtures';
import { acceptedActions } from '@/test/admissionsFixtures';
import { HomeAgenda } from './HomeAgenda';
let value = emptyToday('A'); let error = ''; let loading = false;
const refreshToday = vi.fn(); const refreshActions = vi.fn();
vi.mock('@/lib/useAdmissionsToday', () => ({ useAdmissionsToday: () => ({ value, error, loading, refresh: refreshToday }) }));
vi.mock('@/lib/useAdmissionsActions', () => ({ useAdmissionsActions: () => ({ current: acceptedActions().current, loading: false, refresh: refreshActions }) }));
beforeEach(() => { value = emptyToday('A'); error = ''; loading = false; vi.clearAllMocks(); });
function addTask() {
  value.action_revision = 1;
  value.today_personal = [{ id:'card-a', reason:'personal_document_action', target:{ kind:'document_task', id:'task-a' }, target_result_id:null,
    date:{ local_date:'2026-10-20', timezone:null, certainty:'applicant_entered', comparison_zone:'UTC', fallback_display_only:false, official_closure:'not_assessed' },
    dependency_reasons:[], workload_origin:'personal_unallocated', planned_minutes:null, source_state:'applicant_entered', actionable:true }];
}
it('opens the actual saved task directly from home, with its case identity', () => {
  addTask(); render(<HomeAgenda/>);
  expect(screen.getByRole('link', { name:/Synthetic document task/ })).toHaveAttribute('href', '#/documents?case=A&kind=document_task&id=task-a');
});
it.each(['stale','mixed'] as const)('withholds exact task actions for %s projections', state => {
  addTask(); if (state === 'stale') value.needs_refresh = true; else value.consistency = 'mixed_revision';
  render(<HomeAgenda/>);
  expect(screen.queryByRole('link', { name:/Synthetic document task/ })).toBeNull();
  expect(screen.getByText(/Переход недоступен/)).toBeInTheDocument();
});
it('distinguishes a failed read from a genuine empty agenda and refreshes both projections', () => {
  error = 'Synthetic read failure'; render(<HomeAgenda/>);
  expect(screen.queryByText('Добавь первое дело')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name:'Обновить план' }));
  expect(refreshToday).toHaveBeenCalledOnce(); expect(refreshActions).toHaveBeenCalledOnce();
});
it('offers a real document-task workflow for an empty agenda', () => {
  render(<HomeAgenda/>);
  expect(screen.getByRole('link', { name:/Добавить задачу/ })).toHaveAttribute('href','#/documents');
});

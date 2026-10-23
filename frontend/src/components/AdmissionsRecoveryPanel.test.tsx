import { webcrypto } from 'node:crypto';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { AdmissionsRecoveryPanel } from './AdmissionsRecoveryPanel';
import { setLocale } from '@/lib/i18n';
import { acknowledgeAdmissionsAction, journalAdmissionsAction, openAdmissionsActionsRecovery, readAdmissionsActionsRecovery } from '@/lib/admissionsActionsRecovery';
import { acceptedActions, actionBody, emptyActions, FIXTURE_UUID } from '@/test/admissionsFixtures';
import type { AdmissionsActionsController } from '@/lib/useAdmissionsActions';

beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto); setLocale('en'); localStorage.clear(); sessionStorage.clear();
  localStorage.setItem('ashyq.applicantOwner', 'demo'); sessionStorage.setItem('ashyq.applicantOwner', 'demo');
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
async function controller(): Promise<AdmissionsActionsController> {
  const opened = openAdmissionsActionsRecovery(undefined, 'A', 1, () => ({ scope: undefined, profile_id: 'A', case_epoch: 1 }));
  if (!opened.ok) throw new Error(opened.reason);
  const body = actionBody(); const fixture = acceptedActions(body);
  await journalAdmissionsAction(opened.value, body, 1);
  await acknowledgeAdmissionsAction(opened.value, body, fixture.receipt);
  await journalAdmissionsAction(opened.value, actionBody('aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee', 1), 2);
  const recovered = await readAdmissionsActionsRecovery(opened.value); if (!recovered.ok) throw new Error(recovered.reason);
  return { key: 'A:1', caseKey: 'A:1', activeCase: 'A', current: emptyActions(), historyPage: null,
    entries: recovered.value.entries, indexRaw: recovered.value.index_raw, journalError: null,
    loading: false, sending: false, error: null, acceptedButUnrefreshed: false,
    refresh: vi.fn().mockResolvedValue(true), submit: vi.fn().mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null }),
    retry: vi.fn().mockResolvedValue({ accepted: false, currentRefreshed: false, receipt: null }),
    loadHistory: vi.fn().mockResolvedValue(true), clearAcknowledged: vi.fn().mockResolvedValue(true), reconcile: vi.fn().mockResolvedValue(true) };
}

it('asks for explicit selection and explains that local cleanup retains server records', async () => {
  const model = await controller(); render(<AdmissionsRecoveryPanel controller={model} />);
  const clean = screen.getByRole('button', { name: 'Clear selected local confirmations' });
  expect(clean).toBeDisabled();
  expect(screen.getByText(/does not delete saved records or server history/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('checkbox')); expect(clean).toBeEnabled(); fireEvent.click(clean);
  await waitFor(() => expect(model.clearAcknowledged).toHaveBeenCalledWith([FIXTURE_UUID]));
  expect(screen.queryByText(FIXTURE_UUID)).toBeNull();
});
it('offers retry for unresolved commands and keeps the original request hidden from automatic dispatch', async () => {
  const model = await controller(); render(<AdmissionsRecoveryPanel controller={model} />);
  expect(model.retry).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Retry original request' }));
  expect(model.retry).toHaveBeenCalledWith('aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee');
});
it('clears the selection synchronously on a different case generation even with the same UUID', async () => {
  const model = await controller(); const view = render(<AdmissionsRecoveryPanel controller={model} />);
  fireEvent.click(screen.getByRole('checkbox')); expect(screen.getByRole('checkbox')).toBeChecked();
  view.rerender(<AdmissionsRecoveryPanel controller={{ ...model, key: 'B:2', caseKey: 'B:2', activeCase: 'B' }} />);
  expect(screen.getByRole('checkbox')).not.toBeChecked(); expect(screen.getByRole('button', { name: 'Clear selected local confirmations' })).toBeDisabled();
});
it('disables retries and cleanup when local recovery cannot be verified', async () => {
  const model = await controller(); render(<AdmissionsRecoveryPanel controller={{ ...model, journalError: 'invalid' }} />);
  expect(screen.getByRole('button', { name: 'Retry original request' })).toBeDisabled(); expect(screen.getByRole('checkbox')).toBeDisabled();
  expect(screen.queryByRole('button', { name: 'Recheck local recovery entries' })).toBeNull();
});
it('shows conflict as review-needed, never as saved or as an automatic retry', async () => {
  const model = await controller(); const pending = model.entries.find(entry => entry.descriptor.status === 'pending');
  if (!pending) throw new Error('Synthetic pending fixture'); pending.pending_state = 'conflict';
  render(<AdmissionsRecoveryPanel controller={model} />);
  expect(screen.getByText(/Data changed. Review the saved version/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Retry original request' })).toBeNull();
});

it('keeps selected confirmed cleanup and original retry available at a valid capacity limit', async () => {
  const model = await controller(); render(<AdmissionsRecoveryPanel controller={{ ...model, journalError: 'limit' }} />);
  expect(screen.getByRole('button', { name: 'Retry original request' })).toBeEnabled();
  expect(screen.getByRole('checkbox')).toBeEnabled();
  fireEvent.click(screen.getByRole('checkbox'));
  const clean = screen.getByRole('button', { name: 'Clear selected local confirmations' });
  expect(clean).toBeEnabled(); fireEvent.click(clean);
  await waitFor(() => expect(model.clearAcknowledged).toHaveBeenCalledWith([FIXTURE_UUID]));
});

it('collapses only acknowledged history and exposes a newly unresolved operation immediately',async()=>{
  const model=await controller();
  const view=render(<AdmissionsRecoveryPanel controller={{...model,entries:model.entries.filter(entry=>entry.descriptor.status==='acknowledged')}}/>);
  expect(screen.getByRole('checkbox',{hidden:true})).not.toBeVisible();
  view.rerender(<AdmissionsRecoveryPanel controller={model}/>);
  expect(screen.getByRole('button',{name:'Retry original request'})).toBeVisible();
});

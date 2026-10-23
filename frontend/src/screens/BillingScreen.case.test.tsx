import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { BillingScreen } from './BillingScreen';
import { deferred } from './preparationFixtures';
import type { EntitlementView } from '@/types';
const state = vi.hoisted(() => ({ id: 'A', epoch: 1, unlock: vi.fn(), refresh: vi.fn(), paid: null as null | (() => Promise<void>) }));
vi.mock('@/lib/store', () => ({ useStore: () => ({ savedProfile: { id: state.id }, currentAdmissionsCase: () => ({ scope: undefined, profile_id: state.id, case_epoch: state.epoch }), unlockFromSubscription: state.unlock, refreshResults: state.refresh }) }));
vi.mock('@/components/PaymentModal', () => ({ PaymentModal: ({ profileId, onPaid }: { profileId: string; onPaid: () => Promise<void> }) => { state.paid = onPaid; return <div>Own payment for {profileId}</div>; } }));
const access = (profile_id: string, full_access = false, left: number | null = null): EntitlementView => ({ profile_id, full_access, subscription_cases_left: left, subscription_queued: 0 });
beforeEach(() => {
  state.id = 'A'; state.epoch = 1; state.paid = null; state.unlock.mockReset(); state.refresh.mockReset();
  vi.spyOn(api, 'pricing').mockResolvedValue({ case_unlock_price_kzt: 7300, currency: 'KZT', payments_enabled: true, includes: [] });
  vi.spyOn(api, 'entitlements').mockImplementation(async id => access(id));
});
afterEach(() => vi.restoreAllMocks());
it('hides previous full research/quota when the next case read fails and keeps access unknown', async () => {
  vi.mocked(api.entitlements).mockResolvedValueOnce(access('A', true, 4)); const view = render(<BillingScreen />);
  await screen.findByText('Full access'); vi.mocked(api.entitlements).mockRejectedValueOnce(new Error('Synthetic read failure'));
  state.id = 'B'; state.epoch = 2; view.rerender(<BillingScreen />);
  expect(screen.queryByText('Full access')).toBeNull(); await screen.findByText('Access not confirmed');
  expect(screen.queryByRole('button', { name: /Use 1 subscription/ })).toBeNull();
  expect(screen.getByRole('button', { name: 'Unlock for 7,300 KZT' })).toBeDisabled();
});
it('rejects a late A response after A→B→A despite a matching profile ID', async () => {
  const old = deferred<EntitlementView>(); const fresh = deferred<EntitlementView>();
  vi.mocked(api.entitlements).mockImplementationOnce(() => old.promise).mockResolvedValueOnce(access('B')).mockImplementationOnce(() => fresh.promise);
  const view = render(<BillingScreen />); state.id = 'B'; state.epoch = 2; view.rerender(<BillingScreen />);
  await screen.findByText('Free preview'); state.id = 'A'; state.epoch = 3; view.rerender(<BillingScreen />);
  await act(async () => old.resolve(access('A', true, 5))); expect(screen.queryByText('Full access')).toBeNull();
  await act(async () => fresh.resolve(access('A'))); await screen.findByText('Free preview');
});
it('hides an old payment and fences its callback before the new case rerenders', async () => {
  const view = render(<BillingScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Unlock for 7,300 KZT' }));
  await screen.findByText('Own payment for A'); const paid = state.paid; if (!paid) throw new Error('Synthetic callback');
  state.id = 'B'; state.epoch = 2; await act(async () => paid()); expect(state.refresh).not.toHaveBeenCalled();
  view.rerender(<BillingScreen />); expect(screen.queryByText('Own payment for A')).toBeNull();
});
it('fences a late subscription response and offers no stale quota', async () => {
  const done = deferred<void>(); state.unlock.mockImplementationOnce(() => done.promise);
  vi.mocked(api.entitlements).mockResolvedValueOnce(access('A', false, 2)); const view = render(<BillingScreen />);
  fireEvent.click(await screen.findByRole('button', { name: 'Use 1 subscription case · 2 left' }));
  state.id = 'B'; state.epoch = 2; view.rerender(<BillingScreen />); await act(async () => done.resolve());
  await screen.findByText('Free preview'); expect(screen.queryByRole('button', { name: /Use 1 subscription/ })).toBeNull();
  expect(vi.mocked(api.entitlements).mock.calls.filter(([id]) => id === 'A')).toHaveLength(1);
});

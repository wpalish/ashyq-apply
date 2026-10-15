import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { BillingScreen } from './BillingScreen';
import { access, deferred } from './preparationFixtures';
import type { EntitlementView } from '@/types';
const state = vi.hoisted(() => ({ profileId: 'case-a' }));
vi.mock('@/lib/store', () => ({ useStore: () => ({
  currentAdmissionsCase: () => ({ scope: undefined, profile_id: state.profileId, case_epoch: 1 }),
  savedProfile: { id: state.profileId }, refreshResults: vi.fn(), unlockFromSubscription: vi.fn(),
}) }));
beforeEach(() => {
  state.profileId = 'case-a';
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in synthetic billing control'); }));
  vi.spyOn(api, 'pricing').mockResolvedValue({ case_unlock_price_kzt: 7300, currency: 'KZT', payments_enabled: true, includes: [] });
  vi.spyOn(api, 'entitlements').mockResolvedValue({ profile_id: 'case-a', full_access: false,
    subscription_cases_left: 0, subscription_queued: 0 });
});
afterEach(() => { expect(fetch).not.toHaveBeenCalled(); cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('billing only advertises confirmed starter entitlement', () => {
  it('does not infer preparation inclusion from research full access or missing education metadata', async () => {
    vi.mocked(api.entitlements).mockResolvedValue({ profile_id: 'case-a', full_access: true,
      subscription_cases_left: 12, subscription_queued: 0 });
    render(<BillingScreen />);
    await screen.findByText('Full access');
    expect(screen.queryByRole('heading', { name: 'Exam preparation access' })).not.toBeInTheDocument();
    expect(screen.queryByText(/includes original starter preparation/)).not.toBeInTheDocument();
  });
  it('confirms bounded starters when education access is allowed despite exhausted research quota', async () => {
    vi.mocked(api.entitlements).mockResolvedValue({ profile_id: 'case-a', full_access: false,
      subscription_cases_left: 0, subscription_queued: 0, preparation_access: access() });
    const open = vi.fn(); render(<BillingScreen onPrepare={open} />);
    expect(await screen.findByText('Your eligible started subscription includes original starter preparation.')).toBeInTheDocument();
    expect(screen.getByText(/not a full course, official mock or score guarantee/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Open preparation & history' })); expect(open).toHaveBeenCalledOnce();
  });
  it('labels payments-disabled access as development rather than a paid subscription', async () => {
    vi.mocked(api.entitlements).mockResolvedValue({ profile_id: 'case-a', full_access: false,
      subscription_cases_left: null, subscription_queued: 0, preparation_access: access(true, true) });
    render(<BillingScreen />);
    expect(await screen.findByText('Development starter access — not a paid subscription.')).toBeInTheDocument();
    expect(screen.queryByText(/Your eligible started subscription includes/)).not.toBeInTheDocument();
  });
  it('does not transfer A education entitlement while B is loading', async () => {
    vi.mocked(api.entitlements).mockResolvedValueOnce({ profile_id: 'case-a', full_access: false,
      subscription_cases_left: 0, subscription_queued: 0, preparation_access: access() });
    const view = render(<BillingScreen />);
    await screen.findByRole('heading', { name: 'Exam preparation access' });
    const pending = deferred<EntitlementView>(); vi.mocked(api.entitlements).mockImplementationOnce(() => pending.promise);
    state.profileId = 'case-b'; view.rerender(<BillingScreen />);
    expect(screen.queryByRole('heading', { name: 'Exam preparation access' })).not.toBeInTheDocument();
    pending.resolve({ profile_id: 'case-b', full_access: false, subscription_cases_left: 0,
      subscription_queued: 0, preparation_access: access(false) });
    expect(await screen.findByText('No eligible started subscription term was confirmed for preparation.')).toBeInTheDocument();
    expect(screen.queryByText(/includes original starter preparation/)).not.toBeInTheDocument();
  });
});

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { BillingScreen } from './BillingScreen';

const refreshResults = vi.fn();
const unlockFromSubscription = vi.fn();
let profileId: string | null = 'profile-1';

vi.mock('@/lib/store', () => ({
  useStore: () => ({
    savedProfile: profileId ? { id: profileId } : null,
    refreshResults,
    unlockFromSubscription,
  }),
}));

beforeEach(() => {
  vi.restoreAllMocks();
  profileId = 'profile-1';
  refreshResults.mockReset();
  unlockFromSubscription.mockReset();
  unlockFromSubscription.mockResolvedValue(undefined);
  vi.spyOn(api, 'pricing').mockResolvedValue({
    case_unlock_price_kzt: 7300,
    currency: 'KZT',
    payments_enabled: true,
    includes: ['Official evidence', 'Full shortlist'],
  });
  vi.spyOn(api, 'entitlements').mockResolvedValue({
    profile_id: 'profile-1', full_access: false, subscription_cases_left: null, subscription_queued: 0,
  });
});

it('uses server pricing for a case rather than a fictional monthly plan', async () => {
  render(<BillingScreen />);
  expect(await screen.findByRole('button', { name: 'Unlock for 7,300 KZT' })).toBeInTheDocument();
  expect(screen.getByText('Official evidence')).toBeInTheDocument();
  expect(screen.queryByText(/per month/i)).not.toBeInTheDocument();
});

it('spends a real subscription case when quota is available', async () => {
  vi.mocked(api.entitlements).mockResolvedValue({
    profile_id: 'profile-1', full_access: false, subscription_cases_left: 2, subscription_queued: 0,
  });
  render(<BillingScreen />);
  fireEvent.click(await screen.findByRole('button', { name: 'Use 1 subscription case · 2 left' }));
  await waitFor(() => expect(unlockFromSubscription).toHaveBeenCalledWith('profile-1'));
  expect(api.entitlements).toHaveBeenCalledWith('profile-1');
});

it('does not offer payment before a case exists', async () => {
  profileId = null;
  render(<BillingScreen />);
  expect(await screen.findByRole('button', { name: 'Unlock for 7,300 KZT' })).toBeDisabled();
});

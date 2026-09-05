import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PaywallNotice } from './PaywallNotice';
import { StoreProvider } from '@/lib/store';
import { api } from '@/api/client';

afterEach(() => vi.restoreAllMocks());

function renderWith(paywall: { profileId: string; priceKzt: number; casesLeft: number | null }) {
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({} as never);
  return render(
    <StoreProvider>
      <PaywallNotice testPaywall={paywall} />
    </StoreProvider>,
  );
}

describe('PaywallNotice', () => {
  it('offers the price when there is no subscription', () => {
    renderWith({ profileId: 'c1', priceKzt: 4990, casesLeft: null });
    expect(screen.getByRole('button', { name: /4990/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /подписки/i })).toBeNull();
  });

  it('offers the subscription first when cases remain', () => {
    renderWith({ profileId: 'c1', priceKzt: 4990, casesLeft: 37 });
    expect(screen.getByRole('button', { name: /осталось 37/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /4990/ })).toBeNull();
  });

  it('falls back to the price when the quota is exhausted', () => {
    renderWith({ profileId: 'c1', priceKzt: 4990, casesLeft: 0 });
    expect(screen.getByRole('button', { name: /4990/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /осталось/i })).toBeNull();
  });

  it('spends a subscription case when asked', async () => {
    const unlock = vi.spyOn(api, 'unlockFromSubscription').mockResolvedValue({
      profile_id: 'c1',
      full_access: true,
      subscription_cases_left: 36,
      subscription_queued: 0,
    });
    renderWith({ profileId: 'c1', priceKzt: 4990, casesLeft: 37 });
    fireEvent.click(screen.getByRole('button', { name: /осталось 37/i }));
    await waitFor(() => expect(unlock).toHaveBeenCalledWith('c1'));
  });
});

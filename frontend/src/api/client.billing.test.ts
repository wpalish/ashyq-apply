import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api, isPaymentRequired } from './client';

function respond(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: 'x',
    json: () => Promise.resolve(body),
  } as Response);
}

const order = {
  id: 'o1',
  profile_id: 'c1',
  status: 'pending',
  method: 'phone',
  amount_kzt: 4990,
  phone_masked: '8707***4455',
  qr_payload: '',
  qr_expires_at: null,
  created_at: '2026-09-04T10:00:00Z',
};

afterEach(() => vi.unstubAllGlobals());

describe('billing client', () => {
  it('reads pricing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        respond(200, {
          case_unlock_price_kzt: 4990,
          currency: 'KZT',
          payments_enabled: true,
          includes: ['a'],
        }),
      ),
    );
    expect((await api.pricing()).case_unlock_price_kzt).toBe(4990);
  });

  it('opens an order without ever sending a price', async () => {
    let sentBody = '';
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        sentBody = String(init?.body ?? '');
        return respond(201, order);
      }),
    );

    expect((await api.openOrder({ profile_id: 'c1', method: 'phone', phone: '87071234455' })).status)
      .toBe('pending');

    const sent = JSON.parse(sentBody);
    expect(sent).not.toHaveProperty('amount_kzt');
    expect(sent).not.toHaveProperty('price_kzt');
  });

  it('recognises a 402 and carries what the paywall needs', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        respond(402, {
          detail: 'Unlock this case to see the full report.',
          code: 'payment_required',
          profile_id: 'c1',
          price_kzt: 4990,
        }),
      ),
    );

    await expect(api.claims('run1')).rejects.toThrow(ApiError);
    try {
      await api.claims('run1');
      expect.unreachable('a 402 must reject');
    } catch (error) {
      expect(isPaymentRequired(error)).toBe(true);
      if (isPaymentRequired(error)) {
        expect(error.profileId).toBe('c1');
        expect(error.priceKzt).toBe(4990);
      }
    }
  });

  it('does not mistake other errors for a paywall', async () => {
    vi.stubGlobal('fetch', vi.fn(() => respond(404, { detail: 'Run not found' })));
    try {
      await api.claims('run1');
      expect.unreachable('a 404 must reject');
    } catch (error) {
      expect(isPaymentRequired(error)).toBe(false);
      expect((error as ApiError).message).toBe('Run not found');
    }
  });

  it('routes a locked export through the client so the paywall can be raised', async () => {
    // A plain <a href> would have rendered this JSON in a tab instead.
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        respond(402, {
          detail: 'Unlock this case to see the full report.',
          code: 'payment_required',
          profile_id: 'c1',
          price_kzt: 4990,
        }),
      ),
    );

    try {
      await api.downloadExport('run1', 'csv');
      expect.unreachable('a locked export must reject');
    } catch (error) {
      expect(isPaymentRequired(error)).toBe(true);
    }
  });

  it('still reports a non-JSON error body by status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 500,
          statusText: 'Server Error',
          json: () => Promise.reject(new Error('not json')),
        } as unknown as Response),
      ),
    );
    try {
      await api.claims('run1');
      expect.unreachable('a 500 must reject');
    } catch (error) {
      expect((error as ApiError).status).toBe(500);
      expect(isPaymentRequired(error)).toBe(false);
    }
  });
});

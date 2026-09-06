/**
 * Initial-hydration error semantics (T09).
 *
 * Complements the drafts suite: the transient-failure contract is asserted
 * here with matchers that exist in this environment, so the pointer-retention
 * and error-reporting behavior is guarded independently of the QA file's
 * `toContainText` line, which vitest 3 + jest-dom do not provide (the QA
 * author's fix belongs to QA; see the T09 developer report).
 */

import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StoreProvider, useStore } from './store';
import { ApiError, api } from '@/api/client';

function Probe() {
  const { error } = useStore();
  return <span data-testid="error">{error ?? ''}</span>;
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  vi.restoreAllMocks();
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({
    gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok',
  });
  vi.spyOn(api, 'cases').mockResolvedValue([]);
});

describe('initial hydration error semantics', () => {
  it('keeps the per-tab case pointer and reports a 500', async () => {
    window.localStorage.setItem('ashyq.activeProfile', 'A');
    vi.spyOn(api, 'getProfile').mockRejectedValue(
      new ApiError(500, 'The database is unreachable.'),
    );

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('error')).toHaveTextContent(
      'The database is unreachable.',
    ));
    // The pointer survives - in the per-tab slot, with no global copy left.
    expect(window.sessionStorage.getItem('ashyq.activeProfile')).toBe('A');
    expect(window.localStorage.getItem('ashyq.activeProfile')).toBeNull();
  });

  it('routes a 401 on the initial profile load to the reload path', async () => {
    const reload = vi.fn();
    const original = window.location;
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...original, reload },
    });
    try {
      window.localStorage.setItem('ashyq.activeProfile', 'A');
      vi.spyOn(api, 'getProfile').mockRejectedValue(
        new ApiError(401, 'Authentication required.'),
      );

      render(<StoreProvider><Probe /></StoreProvider>);

      await waitFor(() => expect(reload).toHaveBeenCalled());
      // An expired session is not an error to act on from this screen.
      expect(screen.queryByText(/Authentication required/)).not.toBeInTheDocument();
    } finally {
      Object.defineProperty(window, 'location', { configurable: true, value: original });
    }
  });
});

/** The visible live default must survive the real store and API client. */

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import { StoreProvider } from '@/lib/store';
import type { Capabilities, StoredProfile } from '@/types';
import { PreferencesScreen } from './PreferencesScreen';

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it('waits for capabilities and sends demo_mode=false through the store and HTTP client', async () => {
  let resolveCapabilities!: (value: Capabilities) => void;
  vi.spyOn(api, 'capabilities').mockReturnValue(new Promise((resolve) => {
    resolveCapabilities = resolve;
  }));
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({
    gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok',
  });
  vi.spyOn(api, 'createProfile').mockResolvedValue({
    ...structuredClone(DEFAULT_PROFILE),
    id: 'synthetic-profile',
    created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
  } as unknown as StoredProfile);
  const fetchRequest = vi.fn().mockResolvedValue(new Response(JSON.stringify({
    id: 'live-run', stage: 'queued', demo_mode: false,
  }), { status: 202, headers: { 'Content-Type': 'application/json' } }));
  vi.stubGlobal('fetch', fetchRequest);
  const onStarted = vi.fn();

  render(<StoreProvider><PreferencesScreen onStarted={onStarted} /></StoreProvider>);
  expect(screen.getByTestId('start-research')).toBeDisabled();
  fireEvent.click(screen.getByTestId('start-research'));
  expect(fetchRequest).not.toHaveBeenCalled();

  await act(async () => {
    resolveCapabilities({
      demo_mode: false,
      currency: { supported: ['USD'], rate_date: '2026-10-01', rate_source: 'ECB' },
    } as Capabilities);
  });
  expect(screen.getByTestId('demo-toggle')).not.toBeChecked();
  fireEvent.click(screen.getByTestId('start-research'));

  await waitFor(() => expect(onStarted).toHaveBeenCalledOnce());
  expect(fetchRequest).toHaveBeenCalledOnce();
  const [url, request] = fetchRequest.mock.calls[0] as [string, RequestInit];
  expect(url).toBe('/api/runs');
  expect(request.method).toBe('POST');
  expect(JSON.parse(String(request.body))).toEqual({
    profile_id: 'synthetic-profile', demo_mode: false,
  });
});

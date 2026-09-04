/**
 * Polling behaviour.
 *
 * The old effect listed the whole run object and the results length in its
 * dependencies, so every tick tore the interval down and rebuilt it; a slow
 * response could overlap the next request; a hidden tab kept polling; and one
 * dropped request showed a banner.
 */

import { act, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { StoreProvider, useStore } from './store';
import { api } from '@/api/client';
import type { RunView } from '@/types';

const RUNNING = {
  id: 'run-1',
  stage: 'program_verification',
  job_status: 'running',
  job_running: true,
  results_count: 0,
  stages: [],
  errors: [],
  retry_urls: [],
  progress: 0.4,
} as unknown as RunView;

function Probe() {
  const { run, error } = useStore();
  return (
    <div>
      <span data-testid="stage">{run?.stage ?? 'none'}</span>
      <span data-testid="error">{error ?? 'none'}</span>
    </div>
  );
}

beforeEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({
    gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok',
  });
  vi.spyOn(api, 'results').mockResolvedValue([]);
  vi.spyOn(api, 'summary').mockResolvedValue({} as never);
  window.localStorage.setItem('ashyq.activeRun', RUNNING.id);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('polling', () => {
  it('issues one request per tick, not one per re-render', async () => {
    const getRun = vi.spyOn(api, 'getRun').mockResolvedValue(RUNNING);
    render(<StoreProvider><Probe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('stage')).toHaveTextContent('program_verification'));

    const afterRestore = getRun.mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(1300); });
    expect(getRun.mock.calls.length).toBe(afterRestore + 1);

    await act(async () => { await vi.advanceTimersByTimeAsync(1300); });
    expect(getRun.mock.calls.length).toBe(afterRestore + 2);
  });

  it('does not overlap requests when the server is slow', async () => {
    let resolveIt: (v: RunView) => void = () => {};
    const getRun = vi.spyOn(api, 'getRun').mockImplementation(() =>
      new Promise<RunView>((resolve) => { resolveIt = resolve; }),
    );
    render(<StoreProvider><Probe /></StoreProvider>);

    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(getRun.mock.calls.length).toBe(1);
    await act(async () => { resolveIt(RUNNING); });
  });

  it('pauses while the tab is hidden and answers at once on return', async () => {
    const getRun = vi.spyOn(api, 'getRun').mockResolvedValue(RUNNING);
    render(<StoreProvider><Probe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('stage')).toHaveTextContent('program_verification'));

    const visible = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true);
    const beforeHidden = getRun.mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(getRun.mock.calls.length).toBe(beforeHidden);

    visible.mockReturnValue(false);
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(getRun.mock.calls.length).toBeGreaterThan(beforeHidden);
  });

  it('backs off on errors and only complains after several in a row', async () => {
    vi.spyOn(api, 'getRun')
      .mockResolvedValueOnce(RUNNING)
      .mockRejectedValue(new Error('network down'));
    render(<StoreProvider><Probe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('stage')).toHaveTextContent('program_verification'));

    // Three failures: still quiet, because one dropped poll is not news.
    await act(async () => { await vi.advanceTimersByTimeAsync(1300 + 1300 + 2500); });
    expect(screen.getByTestId('error')).toHaveTextContent('none');

    await act(async () => { await vi.advanceTimersByTimeAsync(5100 + 15100); });
    expect(screen.getByTestId('error')).not.toHaveTextContent('none');
  });

  it('stops entirely once the run settles', async () => {
    const settled = { ...RUNNING, stage: 'awaiting_user_decision', job_status: 'succeeded', job_running: false };
    const getRun = vi.spyOn(api, 'getRun').mockResolvedValue(settled as unknown as RunView);
    render(<StoreProvider><Probe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('stage')).toHaveTextContent('awaiting_user_decision'));

    const afterSettle = getRun.mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(getRun.mock.calls.length).toBe(afterSettle);
  });
});

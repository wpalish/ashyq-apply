/**
 * Store regressions.
 *
 * FP-10: after a reload the saved profile was restored into `savedProfile` but
 * the editable draft stayed as the synthetic DEFAULT_PROFILE. The next save
 * then wrote demo data over the applicant's real profile — silent data loss.
 */

import { act, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StoreProvider, blankProfile, toDraft, useStore } from './store';
import { DEFAULT_PROFILE } from './defaultProfile';
import { ApiError, api } from '@/api/client';
import type { RunView, StoredProfile } from '@/types';

// The spread comes first: anything after it is the part that makes this
// profile distinguishable from the synthetic demo one.
const REAL_PROFILE: StoredProfile = {
  ...structuredClone(DEFAULT_PROFILE),
  id: 'saved-profile-id',
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-02T00:00:00Z',
  display_name: 'Aisha (real applicant)',
  context: {
    ...structuredClone(DEFAULT_PROFILE).context,
    citizenship: 'Uzbekistan',
    intended_fields: ['civil engineering'],
  },
} as unknown as StoredProfile;

function Probe() {
  const { profileDraft, savedProfile, restored } = useStore();
  const context = profileDraft.context as Record<string, unknown>;
  return (
    <div>
      <span data-testid="citizenship">{String(context?.citizenship)}</span>
      <span data-testid="display">{String(profileDraft.display_name)}</span>
      <span data-testid="saved">{savedProfile?.id ?? 'none'}</span>
      <span data-testid="restored">{String(restored)}</span>
    </div>
  );
}

beforeEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({
    gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok',
  });
});

describe('profile restoration after a reload', () => {
  it('hydrates the editable draft from the stored profile', async () => {
    window.localStorage.setItem('unimatch.activeProfile', REAL_PROFILE.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('restored')).toHaveTextContent('true'));
    expect(screen.getByTestId('citizenship')).toHaveTextContent('Uzbekistan');
    expect(screen.getByTestId('display')).toHaveTextContent('Aisha (real applicant)');
    expect(screen.getByTestId('saved')).toHaveTextContent(REAL_PROFILE.id);
  });

  it('never leaves the synthetic demo profile in the draft after restoring', async () => {
    window.localStorage.setItem('unimatch.activeProfile', REAL_PROFILE.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('restored')).toHaveTextContent('true'));
    expect(screen.getByTestId('citizenship')).not.toHaveTextContent('Kazakhstan');
    expect(screen.getByTestId('display')).not.toHaveTextContent('Demo Applicant');
  });

  it('forgets the pointer when the stored profile is gone', async () => {
    window.localStorage.setItem('unimatch.activeProfile', 'deleted-id');
    window.localStorage.setItem('unimatch.activeRun', 'some-run');
    vi.spyOn(api, 'getProfile').mockRejectedValue(new Error('404'));
    vi.spyOn(api, 'getRun').mockRejectedValue(new Error('404'));

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() =>
      expect(window.localStorage.getItem('unimatch.activeProfile')).toBeNull(),
    );
    expect(screen.getByTestId('saved')).toHaveTextContent('none');
  });

  it('restores the profile even when no run is stored', async () => {
    window.localStorage.setItem('unimatch.activeProfile', REAL_PROFILE.id);
    const getRun = vi.spyOn(api, 'getRun');
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('restored')).toHaveTextContent('true'));
    expect(getRun).not.toHaveBeenCalled();
  });
});

describe('toDraft', () => {
  it('strips the server-side fields the API rejects on write', () => {
    const draft = toDraft(REAL_PROFILE);
    expect(draft).not.toHaveProperty('id');
    expect(draft).not.toHaveProperty('created_at');
    expect(draft).not.toHaveProperty('updated_at');
    expect(draft).toHaveProperty('context');
  });
});

describe('blankProfile', () => {
  it('carries no synthetic scores', () => {
    const blank = blankProfile();
    const academics = blank.academics as {
      gpa: unknown;
      ielts: { overall: unknown };
      sat: { total: unknown };
    };
    expect(academics.gpa).toBeNull();
    expect(academics.ielts.overall).toBeNull();
    expect(academics.sat.total).toBeNull();
    expect(blank.activities).toEqual([]);
    expect(blank.achievements).toEqual([]);
  });

  it('is distinguishable from the demo profile', () => {
    expect(blankProfile()).not.toEqual(structuredClone(DEFAULT_PROFILE));
  });
});

describe('explicit demo loading', () => {
  it('only puts demo data in the draft when asked', async () => {
    function DemoProbe() {
      const { profileDraft, loadDemoProfile, clearProfile } = useStore();
      const context = profileDraft.context as Record<string, unknown>;
      return (
        <div>
          <span data-testid="fields">{JSON.stringify(context.intended_fields)}</span>
          <button onClick={clearProfile}>clear</button>
          <button onClick={loadDemoProfile}>demo</button>
        </div>
      );
    }
    render(<StoreProvider><DemoProbe /></StoreProvider>);

    await act(async () => { screen.getByText('clear').click(); });
    expect(screen.getByTestId('fields')).toHaveTextContent('[]');

    await act(async () => { screen.getByText('demo').click(); });
    expect(screen.getByTestId('fields')).toHaveTextContent('computer science');
  });
});

describe('starting research twice', () => {
  function StartProbe() {
    const { run, startRun, error } = useStore();
    return (
      <div>
        <span data-testid="run">{run?.id ?? 'none'}</span>
        <span data-testid="error">{error ?? 'none'}</span>
        <button onClick={() => startRun(true)}>start</button>
      </div>
    );
  }

  it('joins the run already in flight instead of reporting a conflict', async () => {
    const active = { id: 'a'.repeat(32), stage: 'candidate_discovery' } as unknown as RunView;
    vi.spyOn(api, 'createProfile').mockResolvedValue(REAL_PROFILE);
    vi.spyOn(api, 'cases').mockResolvedValue([]);
    vi.spyOn(api, 'startRun').mockRejectedValue(
      new ApiError(409, `Research is already running for this applicant (run ${active.id}). `),
    );
    const getRun = vi.spyOn(api, 'getRun').mockResolvedValue(active);

    render(<StoreProvider><StartProbe /></StoreProvider>);
    await act(async () => { screen.getByText('start').click(); });

    expect(getRun).toHaveBeenCalledWith(active.id);
    expect(screen.getByTestId('run')).toHaveTextContent(active.id);
    expect(screen.getByTestId('error')).toHaveTextContent('none');
    expect(window.localStorage.getItem('unimatch.activeRun')).toBe(active.id);
  });

  it('sends an idempotency key so a retried request cannot start a second run', async () => {
    vi.spyOn(api, 'createProfile').mockResolvedValue(REAL_PROFILE);
    vi.spyOn(api, 'cases').mockResolvedValue([]);
    const startRun = vi.spyOn(api, 'startRun').mockResolvedValue(
      { id: 'run-1' } as unknown as RunView,
    );

    render(<StoreProvider><StartProbe /></StoreProvider>);
    await act(async () => { screen.getByText('start').click(); });

    expect(startRun).toHaveBeenCalledWith(REAL_PROFILE.id, true, expect.any(String));
    expect(startRun.mock.calls[0]?.[2]).toBeTruthy();
  });
});

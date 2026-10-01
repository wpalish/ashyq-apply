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
import type { ApplicantCase, RunView, StoredProfile } from '@/types';

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
  const { profileDraft, savedProfile, restored, error } = useStore();
  const context = profileDraft.context as Record<string, unknown>;
  return (
    <div>
      <span data-testid="citizenship">{String(context?.citizenship)}</span>
      <span data-testid="display">{String(profileDraft.display_name)}</span>
      <span data-testid="saved">{savedProfile?.id ?? 'none'}</span>
      <span data-testid="restored">{String(restored)}</span>
      <span data-testid="error">{error ?? ''}</span>
    </div>
  );
}

beforeEach(() => {
  window.localStorage.clear();
  // T09: the active case/run pointers are per-tab sessionStorage, so tests
  // must not leak a pointer from one test into the next.
  window.sessionStorage.clear();
  vi.restoreAllMocks();
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({
    gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok',
  });
});

describe('profile restoration after a reload', () => {
  it('hydrates the editable draft from the stored profile', async () => {
    window.localStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('restored')).toHaveTextContent('true'));
    expect(screen.getByTestId('citizenship')).toHaveTextContent('Uzbekistan');
    expect(screen.getByTestId('display')).toHaveTextContent('Aisha (real applicant)');
    expect(screen.getByTestId('saved')).toHaveTextContent(REAL_PROFILE.id);
  });

  it('never leaves the synthetic demo profile in the draft after restoring', async () => {
    window.localStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('restored')).toHaveTextContent('true'));
    expect(screen.getByTestId('citizenship')).not.toHaveTextContent('Kazakhstan');
    expect(screen.getByTestId('display')).not.toHaveTextContent('Demo Applicant');
  });

  it('forgets the pointer when the stored profile is gone', async () => {
    window.localStorage.setItem('ashyq.activeProfile', 'deleted-id');
    window.localStorage.setItem('ashyq.activeRun', 'some-run');
    // A real ApiError: a plain Error would never run the store's 404 branch,
    // and the pointer assertions below would only exercise the adopt step.
    vi.spyOn(api, 'getProfile').mockRejectedValue(new ApiError(404, 'Not found.'));
    vi.spyOn(api, 'getRun').mockRejectedValue(new ApiError(404, 'Not found.'));

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() =>
      expect(window.localStorage.getItem('ashyq.activeProfile')).toBeNull(),
    );
    // A 404 proves the case is gone: the per-tab pointers are forgotten too,
    // not just the legacy global keys the adopt step already removed.
    await waitFor(() =>
      expect(window.sessionStorage.getItem('ashyq.activeProfile')).toBeNull(),
    );
    expect(window.sessionStorage.getItem('ashyq.activeRun')).toBeNull();
    expect(screen.getByTestId('saved')).toHaveTextContent('none');
  });

  it('restores the profile even when no run is stored', async () => {
    window.localStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
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

  it('carries no invented preferences or family budget into a cleared or new case', () => {
    expectNeutralProfile(blankProfile());
  });
});

function expectNeutralProfile(payload: unknown, fields: string[] = []) {
  const draft = payload as Record<string, unknown>;
  expect(draft.display_name).toBe('New applicant');
  expect(draft.context).toMatchObject({
    intended_fields: fields, citizenship: '', country_of_residence: '', education_country: '',
    education_system: '', graduation_date: null, second_citizenship: null,
  });
  expect(draft.academics).toMatchObject({
    gpa: null, class_rank: null, class_size: null, planned_retakes: [], subject_grades: [],
    sat: { total: null, math: null, reading_writing: null },
    ielts: { overall: null, listening: null, reading: null, writing: null, speaking: null },
  });
  expect(draft.activities).toEqual([]);
  expect(draft.achievements).toEqual([]);
  expect(draft.preferences).toMatchObject({
    preferred_countries: [], excluded_countries: [], research_interests: [],
    city_size: 'any', climate: 'any', university_size: 'any', campus_type: 'any',
    acceptable_workload: 'any', target_ranking_band: 'any',
    needs_work_during_study: false, needs_post_study_work: false,
    safety_priority: 'medium', diversity_priority: 'medium', housing_guarantee_priority: 'medium',
  });
  expect(draft.funding).toMatchObject({
    max_annual_budget: null, max_family_contribution: null, max_acceptable_gap: null,
  });
}

describe('a fresh browser opens a new applicant', () => {
  function FreshProbe() {
    const store = useStore();
    return (
      <div>
        <output data-testid="draft">{JSON.stringify(store.profileDraft)}</output>
        <span data-testid="hydrated">{String(store.hydrated)}</span>
        <span data-testid="cases">{store.cases.length}</span>
        <span data-testid="saved">{store.savedProfile?.id ?? 'none'}</span>
        <button onClick={() => store.setProfileDraft((d) => ({
          ...d, context: { ...(d.context as object), intended_fields: ['biology'] },
        }))}>choose field</button>
        <button onClick={() => store.saveProfile()}>save</button>
        <button onClick={() => store.startRun(false)}>start live</button>
        <button onClick={() => store.switchCase('saved-demo')}>open saved demo</button>
      </div>
    );
  }

  const savedDemoCase: ApplicantCase = {
    id: 'saved-demo', profile_id: 'saved-demo', display_name: DEFAULT_PROFILE.display_name,
    status: 'draft', run_count: 0, created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
  };

  it.each([false, true])('starts neutral when saved cases exist=%s', async (hasCases) => {
    vi.mocked(api.cases).mockResolvedValue(hasCases ? [savedDemoCase] : []);
    const getProfile = vi.spyOn(api, 'getProfile');
    render(<StoreProvider><FreshProbe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('hydrated')).toHaveTextContent('true'));
    expectNeutralProfile(JSON.parse(screen.getByTestId('draft').textContent!));
    expect(screen.getByTestId('cases')).toHaveTextContent(hasCases ? '1' : '0');
    expect(screen.getByTestId('saved')).toHaveTextContent('none');
    expect(getProfile).not.toHaveBeenCalled();
  });

  it.each(['save', 'start live'])('does not submit demo data when the applicant clicks %s', async (action) => {
    const createProfile = vi.spyOn(api, 'createProfile').mockImplementation(async (draft) => ({
      ...(draft as Record<string, unknown>), id: 'new-profile', created_at: '2026-10-01T00:00:00Z',
      updated_at: '2026-10-01T00:00:00Z',
    }) as StoredProfile);
    const startRun = vi.spyOn(api, 'startRun').mockResolvedValue({ id: 'new-run' } as RunView);
    render(<StoreProvider><FreshProbe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('hydrated')).toHaveTextContent('true'));
    await act(async () => { screen.getByText('choose field').click(); });
    await act(async () => { screen.getByText(action).click(); });

    expect(createProfile).toHaveBeenCalledOnce();
    expectNeutralProfile(createProfile.mock.calls[0]![0], ['biology']);
    if (action === 'start live') {
      expect(startRun).toHaveBeenCalledWith('new-profile', false, expect.any(String));
    } else {
      expect(startRun).not.toHaveBeenCalled();
    }
  });

  it('still opens an explicitly selected saved synthetic case unchanged', async () => {
    vi.mocked(api.cases).mockResolvedValue([savedDemoCase]);
    vi.spyOn(api, 'getProfile').mockResolvedValue({
      ...structuredClone(DEFAULT_PROFILE), id: savedDemoCase.profile_id,
      created_at: savedDemoCase.created_at, updated_at: savedDemoCase.updated_at,
    } as unknown as StoredProfile);
    vi.spyOn(api, 'listRuns').mockResolvedValue([]);
    render(<StoreProvider><FreshProbe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('hydrated')).toHaveTextContent('true'));
    await act(async () => { screen.getByText('open saved demo').click(); });
    expect(JSON.parse(screen.getByTestId('draft').textContent!)).toEqual(DEFAULT_PROFILE);
    expect(screen.getByTestId('saved')).toHaveTextContent(savedDemoCase.profile_id);
  });
});

describe('explicit demo loading', () => {
  it('only puts demo data in the draft when asked', async () => {
    function DemoProbe() {
      const { profileDraft, loadDemoProfile, clearProfile } = useStore();
      return (
        <div>
          <output data-testid="draft">{JSON.stringify(profileDraft)}</output>
          <button onClick={clearProfile}>clear</button>
          <button onClick={loadDemoProfile}>demo</button>
        </div>
      );
    }
    render(<StoreProvider><DemoProbe /></StoreProvider>);

    expectNeutralProfile(JSON.parse(screen.getByTestId('draft').textContent!));

    await act(async () => { screen.getByText('demo').click(); });
    expect(JSON.parse(screen.getByTestId('draft').textContent!)).toEqual(DEFAULT_PROFILE);

    await act(async () => { screen.getByText('clear').click(); });
    expectNeutralProfile(JSON.parse(screen.getByTestId('draft').textContent!));
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
    // T09: the run pointer is per-tab sessionStorage; no global copy is kept.
    expect(window.sessionStorage.getItem('ashyq.activeRun')).toBe(active.id);
    expect(window.localStorage.getItem('ashyq.activeRun')).toBeNull();
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

describe('renaming the storage keys', () => {
  it('carries a session stored under the old name across, once', async () => {
    // A rename with no migration would have signed everyone out of their own
    // case the first time they loaded the renamed build. T09 moved the active
    // case pointer to per-tab sessionStorage: the legacy global pointer is
    // adopted into this tab once and the global keys are then removed.
    window.localStorage.setItem('unimatch.activeProfile', REAL_PROFILE.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('saved')).toHaveTextContent(REAL_PROFILE.id));
    expect(window.sessionStorage.getItem('ashyq.activeProfile')).toBe(REAL_PROFILE.id);
    expect(window.localStorage.getItem('ashyq.activeProfile')).toBeNull();
    expect(window.localStorage.getItem('unimatch.activeProfile')).toBeNull();
  });

  it('prefers the new key when both exist', async () => {
    window.localStorage.setItem('unimatch.activeProfile', 'stale-id');
    window.localStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
    const getProfile = vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><Probe /></StoreProvider>);

    await waitFor(() => expect(getProfile).toHaveBeenCalledWith(REAL_PROFILE.id));
  });
});

describe('unsaved edits', () => {
  function DirtyProbe() {
    const { profileDraft, setProfileDraft, dirty, draftRestored, discardDraft } = useStore();
    const context = profileDraft.context as Record<string, unknown>;
    return (
      <div>
        <span data-testid="dirty">{String(dirty)}</span>
        <span data-testid="draft-restored">{String(draftRestored)}</span>
        <span data-testid="citizenship">{String(context?.citizenship)}</span>
        <button onClick={() => setProfileDraft((d) => ({
          ...d, context: { ...(d.context as object), citizenship: 'Georgia' },
        }))}>edit</button>
        <button onClick={discardDraft}>discard</button>
      </div>
    );
  }

  it('knows the draft is dirty only after a real edit', async () => {
    window.localStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><DirtyProbe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('citizenship')).toHaveTextContent('Uzbekistan'));
    expect(screen.getByTestId('dirty')).toHaveTextContent('false');

    await act(async () => { screen.getByText('edit').click(); });
    expect(screen.getByTestId('dirty')).toHaveTextContent('true');
  });

  it('restores an unsaved draft after a reload without touching the saved profile', async () => {
    window.localStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
    window.localStorage.setItem(
      'ashyq.unsavedDraft',
      JSON.stringify({ ...toDraft(REAL_PROFILE), display_name: 'Half-typed name' }),
    );
    const update = vi.spyOn(api, 'updateProfile');
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><DirtyProbe /></StoreProvider>);

    await waitFor(() => expect(screen.getByTestId('draft-restored')).toHaveTextContent('true'));
    // Nothing was written back to the server, and the saved copy is intact.
    expect(update).not.toHaveBeenCalled();
  });

  it('discarding a restored draft returns to the saved profile', async () => {
    window.localStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
    window.localStorage.setItem(
      'ashyq.unsavedDraft',
      JSON.stringify({
        ...toDraft(REAL_PROFILE),
        context: { ...(toDraft(REAL_PROFILE).context as object), citizenship: 'Georgia' },
      }),
    );
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    render(<StoreProvider><DirtyProbe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('citizenship')).toHaveTextContent('Georgia'));

    // The migration re-wrapped the legacy draft into the active case's own
    // slot; discard must remove THAT slot — deleting the legacy key alone
    // proves nothing, the migration already removed it before the discard.
    const draftSlots: string[] = [];
    for (let i = 0; i < window.localStorage.length; i += 1) {
      const key = window.localStorage.key(i) as string;
      if ((window.localStorage.getItem(key) ?? '').includes('Georgia')) draftSlots.push(key);
    }
    expect(draftSlots.length).toBeGreaterThan(0);

    await act(async () => { screen.getByText('discard').click(); });
    expect(screen.getByTestId('citizenship')).toHaveTextContent('Uzbekistan');
    for (const key of draftSlots) {
      expect(window.localStorage.getItem(key)).toBeNull();
    }
  });

  it('never lets a restored draft become the saved profile by itself', async () => {
    // The FP-10 shape: demo data in the draft must not reach savedProfile.
    window.localStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
    window.localStorage.setItem(
      'ashyq.unsavedDraft',
      JSON.stringify({ ...structuredClone(DEFAULT_PROFILE), display_name: 'Demo Applicant' }),
    );
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);

    function SavedProbe() {
      const { savedProfile } = useStore();
      return <span data-testid="saved-name">{savedProfile?.display_name ?? 'none'}</span>;
    }
    render(<StoreProvider><SavedProbe /></StoreProvider>);

    await waitFor(() =>
      expect(screen.getByTestId('saved-name')).toHaveTextContent('Aisha (real applicant)'),
    );
  });
});

describe('a session that dies mid-use', () => {
  /**
   * With auth on, `AuthGate` asks `/api/auth/status` exactly once, at mount.
   * Every later 401 arrived at `fail`, which renders any ApiError as a topbar
   * banner - so an expired session read as "Something went wrong.
   * Authentication required." on a screen the user could no longer act on,
   * with no way back to the sign-in form. The guard belongs in `fail`, which
   * all thirteen call sites already route through, not at each of them.
   */
  it('reloads to the sign-in screen instead of showing an error banner', async () => {
    const reload = vi.fn();
    const original = window.location;
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...original, reload },
    });

    try {
      vi.spyOn(api, 'cases').mockRejectedValue(new ApiError(401, 'Authentication required.'));

      render(
        <StoreProvider>
          <Probe />
        </StoreProvider>,
      );

      await waitFor(() => expect(reload).toHaveBeenCalled());
      expect(screen.queryByText(/Authentication required/)).not.toBeInTheDocument();
    } finally {
      Object.defineProperty(window, 'location', { configurable: true, value: original });
    }
  });

  it('still shows the banner for errors that are not about authentication', async () => {
    vi.spyOn(api, 'cases').mockRejectedValue(new ApiError(500, 'The database is unreachable.'));

    render(
      <StoreProvider>
        <Probe />
      </StoreProvider>,
    );

    await waitFor(() =>
      expect(screen.getByText(/The database is unreachable/)).toBeInTheDocument(),
    );
  });
});

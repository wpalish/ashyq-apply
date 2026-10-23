import { profileAck } from '@/lib/profileWriteFixtures';
/**
 * Store regressions.
 *
 * FP-10: after a reload the saved profile was restored into `savedProfile` but
 * the editable draft stayed as the synthetic DEFAULT_PROFILE. The next save
 * then wrote demo data over the applicant's real profile — silent data loss.
 */

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StoreProvider, blankProfile, toDraft, useStore } from './store';
import { DEFAULT_PROFILE } from './defaultProfile';
import { ExportScreen } from '@/screens/ExportScreen';
import { ApiError, api } from '@/api/client';
import type { ApplicantCase, RunView, StoredProfile } from '@/types';
import { bindApplicantOwner, forgetApplicantBrowserData } from '@/lib/applicantStorage';
import { writePointer, writeDraftEnvelope } from '@/lib/caseDrafts';

// The spread comes first: anything after it is the part that makes this
// profile distinguishable from the synthetic demo one.
const REAL_PROFILE: StoredProfile = {
  ...structuredClone(DEFAULT_PROFILE),
    revision:1,
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
    const createProfile = vi.spyOn(api, 'createProfile').mockImplementation(async (draft,command) => profileAck({
      ...(draft as Record<string, unknown>), id: 'new-profile', created_at: '2026-10-01T00:00:00Z',
      updated_at: '2026-10-01T00:00:00Z',
    } as StoredProfile,command,'create'));
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
      ...structuredClone(DEFAULT_PROFILE), revision:1, id: savedDemoCase.profile_id,
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
    vi.spyOn(api, 'createProfile').mockImplementation(async(_body,command)=>profileAck(REAL_PROFILE,command,'create'));
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
    vi.spyOn(api, 'createProfile').mockImplementation(async(_body,command)=>profileAck(REAL_PROFILE,command,'create'));
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

describe('document collection acknowledgement', () => {
  function CollectProbe() {
    const { collectDocuments, run, error } = useStore();
    const [accepted, setAccepted] = useState<boolean | null>(null);
    return <>
      <span data-testid="collection-run">{run?.id ?? 'none'}</span>
      <span data-testid="collection-error">{error ?? ''}</span>
      <span data-testid="collection-accepted">{String(accepted)}</span>
      <button onClick={async () => setAccepted(await collectDocuments())}>collect</button>
    </>;
  }

  it.each([true, false])('reports the actual API acknowledgement: %s', async (accepted) => {
    const run = { id: 'run-1', stage: 'awaiting_user_decision', job_running: false } as RunView;
    window.sessionStorage.setItem('ashyq.activeRun', run.id);
    vi.spyOn(api, 'getRun').mockResolvedValue(run);
    vi.spyOn(api, 'results').mockResolvedValue([]);
    vi.spyOn(api, 'summary').mockResolvedValue({} as never);
    vi.spyOn(api, 'shortlist').mockResolvedValue({} as never);
    const request = vi.spyOn(api, 'collectDocuments');
    if (accepted) request.mockResolvedValue({ ...run, stage: 'document_collection' });
    else request.mockRejectedValue(new ApiError(503, 'Collection service unavailable'));
    render(<StoreProvider><CollectProbe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('collection-run')).toHaveTextContent(run.id));
    await act(async () => screen.getByText('collect').click());
    expect(screen.getByTestId('collection-accepted')).toHaveTextContent(String(accepted));
    expect(request).toHaveBeenCalledWith(run.id);
    if (!accepted) expect(screen.getByTestId('collection-error')).toHaveTextContent('Collection service unavailable');
  });

  it('does not claim success or call the API without a run', async () => {
    const request = vi.spyOn(api, 'collectDocuments');
    render(<StoreProvider><CollectProbe /></StoreProvider>);
    await act(async () => screen.getByText('collect').click());
    expect(screen.getByTestId('collection-accepted')).toHaveTextContent('false');
    expect(request).not.toHaveBeenCalled();
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
    const { profileDraft, setProfileDraft, saveProfile, dirty, draftRestored, discardDraft } = useStore();
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
        <button onClick={() => void saveProfile()}>save profile</button>
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

  it('aligns a saved form with the server-normalized profile', async () => {
    window.localStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);
    vi.spyOn(api, 'updateProfile').mockImplementation(async (_id, draft,command) => profileAck({
      ...REAL_PROFILE,
      context: { ...((draft as StoredProfile).context as object), citizenship: 'Republic of Georgia' },
    } as StoredProfile,command));

    render(<StoreProvider><DirtyProbe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('citizenship')).toHaveTextContent('Uzbekistan'));
    await act(async () => { screen.getByText('edit').click(); });
    expect(screen.getByTestId('dirty')).toHaveTextContent('true');
    await act(async () => { screen.getByText('save profile').click(); });
    await waitFor(() => expect(screen.getByTestId('citizenship')).toHaveTextContent('Republic of Georgia'));
    expect(screen.getByTestId('dirty')).toHaveTextContent('false');
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


function DeletionProbe() {
  const { profileDraft, savedProfile, validation, deleteEverything, results } = useStore();
  const [ack, setAck] = useState<unknown>(null);
  return <>
    <output data-testid="delete-draft">{JSON.stringify(profileDraft)}</output>
    <output data-testid="delete-saved">{savedProfile?.id ?? 'none'}</output>
    <output data-testid="delete-validation">{JSON.stringify(validation)}</output>
    <output data-testid="delete-ack">{String(ack)}</output>
    <output data-testid="delete-results">{results.map((result) => result.id).join(',')}</output>
    <button onClick={async () => setAck(await deleteEverything())}>Delete via store</button>
  </>;
}
function privacyCase(withRun = false) {
  window.sessionStorage.setItem('ashyq.activeProfile', REAL_PROFILE.id);
  vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);
  vi.spyOn(api, 'deleteProfile').mockResolvedValue(undefined);
  vi.spyOn(api, 'exportProfile').mockResolvedValue({ profile: { display_name: 'Synthetic own case' }, runs: [] });
  vi.mocked(api.capabilities).mockResolvedValue({ demo_mode: true, guarantees: [], limits: [], currency: { rate_date: '2026-10-01', rate_source: 'synthetic' } } as never);
  if (withRun) {
    window.sessionStorage.setItem('ashyq.activeRun', 'run-for-case');
    vi.spyOn(api, 'getRun').mockResolvedValue({ id: 'run-for-case', profile_id: REAL_PROFILE.id,
      stage: 'awaiting_user_decision', job_running: false, cancelled: false, progress: 1,
      results_count: 1, claims_recorded: 0, pages_checked: 0, demo_mode: true } as RunView);
    vi.spyOn(api, 'results').mockResolvedValue([]);
    vi.spyOn(api, 'summary').mockResolvedValue({} as never);
  }
}

describe('case privacy controls acknowledge actual deletion', () => {
  it('exports a saved profile with no research run without starting research', async () => {
    privacyCase();
    const start = vi.spyOn(api, 'startRun');
    render(<StoreProvider><ExportScreen /></StoreProvider>);
    fireEvent.click(await screen.findByTestId('export-profile'));
    expect(await screen.findByLabelText('Stored profile data')).toHaveTextContent('Synthetic own case');
    expect(screen.queryByTestId('export-csv')).not.toBeInTheDocument();
    expect(start).not.toHaveBeenCalled();
    expect(api.deleteProfile).not.toHaveBeenCalled();
  });

  it('deletes a saved zero-run case only after explicit confirmation', async () => {
    privacyCase();
    render(<StoreProvider><ExportScreen /></StoreProvider>);
    const confirm = await screen.findByTestId('delete-confirm');
    expect(api.deleteProfile).not.toHaveBeenCalled();
    fireEvent.change(confirm, { target: { value: 'DELETE' } });
    fireEvent.click(screen.getByTestId('delete-everything'));
    await waitFor(() => expect(api.deleteProfile).toHaveBeenCalledWith(REAL_PROFILE.id));
    expect(await screen.findByText(/Deleted. The profile/)).toBeInTheDocument();
  });

  it.each([403, 500])('keeps the actual case and does not show deletion success on HTTP %i', async (status) => {
    privacyCase(true);
    vi.mocked(api.deleteProfile).mockRejectedValue(new ApiError(status, 'Deletion refused'));
    render(<StoreProvider><DeletionProbe /><ExportScreen /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('delete-saved')).toHaveTextContent(REAL_PROFILE.id));
    fireEvent.change(await screen.findByTestId('delete-confirm'), { target: { value: 'DELETE' } });
    fireEvent.click(screen.getByTestId('delete-everything'));
    await waitFor(() => expect(api.deleteProfile).toHaveBeenCalled());
    await act(async () => { await Promise.resolve(); });
    expect(screen.queryByText(/Deleted. The profile/)).not.toBeInTheDocument();
    expect(screen.getByTestId('delete-saved')).toHaveTextContent(REAL_PROFILE.id);
    expect(screen.getByTestId('delete-draft')).toHaveTextContent(REAL_PROFILE.display_name);
  });

  it('returns an acknowledgment and clears only successful case draft memory and its marks', async () => {
    privacyCase(true);
    vi.mocked(api.results).mockResolvedValue([{ id: 'result-for-case' }] as never);
    window.localStorage.setItem('ashyq.docsDone', '{"result-for-case::Passport":true,"other-case::Reference":true}');
    render(<StoreProvider><DeletionProbe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('delete-saved')).toHaveTextContent(REAL_PROFILE.id));
    await waitFor(() => expect(screen.getByTestId('delete-results')).toHaveTextContent('result-for-case'));
    fireEvent.click(screen.getByRole('button', { name: 'Delete via store' }));
    await waitFor(() => expect(screen.getByTestId('delete-ack')).toHaveTextContent('true'));
    expect(screen.getByTestId('delete-saved')).toHaveTextContent('none');
    expect(screen.getByTestId('delete-draft')).not.toHaveTextContent(REAL_PROFILE.display_name);
    expect(screen.getByTestId('delete-validation')).toHaveTextContent('null');
    expect(window.sessionStorage.getItem('ashyq.activeProfile')).toBeNull();
    expect(JSON.parse(window.localStorage.getItem('ashyq.docsDone')!)).toHaveProperty('other-case::Reference', true);
    expect(JSON.parse(window.localStorage.getItem('ashyq.docsDone')!)).not.toHaveProperty('result-for-case::Passport');
  });
});

let capturedPrivateActions: ReturnType<typeof useStore>;
function PrivateActionProbe() {
  capturedPrivateActions = useStore();
  return <p>Private action source</p>;
}
describe('unmounted applicant actions cannot resume under a newly bound owner', () => {
  it.each(['saveProfile', 'startRun'] as const)('refuses an old %s closure before creating the old private draft', async (operation) => {
    window.localStorage.setItem('ashyq.applicantOwner', 'auth:["user-a","org-a"]');
    window.sessionStorage.setItem('ashyq.applicantOwner', 'auth:["user-a","org-a"]');
    const first = render(<StoreProvider><PrivateActionProbe /></StoreProvider>);
    await waitFor(() => expect(capturedPrivateActions.hydrated).toBe(true));
    const oldActions = capturedPrivateActions;
    first.unmount();
    window.localStorage.setItem('ashyq.applicantOwner', 'auth:["user-b","org-b"]');
    window.sessionStorage.setItem('ashyq.applicantOwner', 'auth:["user-b","org-b"]');
    const create = vi.spyOn(api, 'createProfile').mockImplementation(async(_body,command)=>profileAck(REAL_PROFILE,command,'create'));
    const start = vi.spyOn(api, 'startRun').mockResolvedValue({ id: 'synthetic-run' } as RunView);
    const pending = operation === 'saveProfile' ? oldActions.saveProfile() : oldActions.startRun(false);
    await expect(pending).rejects.toThrow(/workspace changed/);
    expect(create).not.toHaveBeenCalled();
    expect(start).not.toHaveBeenCalled();
  });
});


describe('authenticated pointerless recovery reads only the authorized server case', () => {
  function RecoveryProbe() {
    const store = useStore();
    return <div>
      <output data-testid="recovery-profile">{store.savedProfile?.id ?? 'none'}</output>
      <output data-testid="recovery-run">{store.run?.id ?? 'none'}</output>
      <output data-testid="recovery-results">{store.results.length}</output>
      <output data-testid="recovery-hydrated">{String(store.hydrated)}</output>
      <output data-testid="recovery-draft">{JSON.stringify(store.profileDraft)}</output>
      <output data-testid="recovery-error">{store.error ?? ''}</output>
      <button onClick={() => store.newCase()}>explicit new applicant</button>
      <button onClick={() => void store.switchCase(REAL_PROFILE.id)}>open authorized existing case</button>
    </div>;
  }
  const ownedCase: ApplicantCase = {
    id: REAL_PROFILE.id, profile_id: REAL_PROFILE.id, display_name: 'Owned synthetic case',
    status: 'active', run_count: 1, created_at: REAL_PROFILE.created_at,
    updated_at: REAL_PROFILE.updated_at,
  };
  const latestRun = { id: 'owned-latest-run', profile_id: REAL_PROFILE.id,
    stage: 'awaiting_user_decision', job_running: false, job_status: 'succeeded',
  } as RunView;
  function owner(user = 'synthetic-A') {
    bindApplicantOwner({ enabled: true, authenticated: true, principal: {
      user_id: user, organization_id: `${user}-workspace`, local_development: false,
    } } as never);
  }
  function reads(cases = [ownedCase], runs = [latestRun]) {
    vi.mocked(api.cases).mockResolvedValue(cases);
    const profile = vi.spyOn(api, 'getProfile').mockResolvedValue(REAL_PROFILE);
    const list = vi.spyOn(api, 'listRuns').mockResolvedValue(runs);
    const results = vi.spyOn(api, 'results').mockResolvedValue([{ id: 'owned-result' }] as never);
    vi.spyOn(api, 'summary').mockResolvedValue({} as never);
    vi.spyOn(api, 'shortlist').mockResolvedValue({} as never);
    const create = vi.spyOn(api, 'createProfile');
    const research = vi.spyOn(api, 'startRun');
    return { profile, list, results, create, research };
  }
  async function settled() {
    await waitFor(() => expect(screen.getByTestId('recovery-hydrated')).toHaveTextContent('true'));
  }
  it('recovers latest run/results after logout removed every private pointer', async () => {
    owner(); writePointer('profile', 'private-old-pointer'); writePointer('run', 'private-old-run');
    forgetApplicantBrowserData(); owner(); const call = reads();
    render(<StoreProvider><RecoveryProbe /></StoreProvider>);
    await settled();
    expect(screen.getByTestId('recovery-profile')).toHaveTextContent(REAL_PROFILE.id);
    expect(screen.getByTestId('recovery-run')).toHaveTextContent(latestRun.id);
    expect(screen.getByTestId('recovery-results')).toHaveTextContent('1');
    expect(call.profile).toHaveBeenCalledWith(ownedCase.profile_id);
    expect(call.list).toHaveBeenCalledWith(ownedCase.profile_id, 1);
    expect(call.results).toHaveBeenCalledWith(latestRun.id);
    expect(call.create).not.toHaveBeenCalled(); expect(call.research).not.toHaveBeenCalled();
  });
  it('uses first server-ordered authorized case when multiple cases exist', async () => {
    owner(); const call = reads([ownedCase, { ...ownedCase, id: 'older-owned-case', profile_id: 'older-owned-case' }]);
    render(<StoreProvider><RecoveryProbe /></StoreProvider>); await settled();
    expect(call.profile).toHaveBeenCalledWith(ownedCase.profile_id);
    expect(call.profile).not.toHaveBeenCalledWith('older-owned-case');
    expect(screen.getByTestId('recovery-profile')).toHaveTextContent(ownedCase.profile_id);
  });
  it('recovers a saved zero-run profile without creating research', async () => {
    owner(); const call = reads([{ ...ownedCase, run_count: 0 }], []);
    render(<StoreProvider><RecoveryProbe /></StoreProvider>); await settled();
    expect(screen.getByTestId('recovery-profile')).toHaveTextContent(ownedCase.profile_id);
    expect(screen.getByTestId('recovery-run')).toHaveTextContent('none');
    expect(call.results).not.toHaveBeenCalled(); expect(call.research).not.toHaveBeenCalled();
  });
  it('keeps anonymous auth-disabled demo neutral despite saved server cases', async () => {
    bindApplicantOwner({ enabled: false, authenticated: false } as never); const call = reads();
    render(<StoreProvider><RecoveryProbe /></StoreProvider>); await settled();
    expect(screen.getByTestId('recovery-profile')).toHaveTextContent('none');
    expect(call.profile).not.toHaveBeenCalled(); expect(call.list).not.toHaveBeenCalled();
  });
  it('keeps an explicit local new case and its own unsaved draft', async () => {
    owner(); const call = reads(); const key = 'local:explicit-owned-case';
    const draft = { ...DEFAULT_PROFILE, display_name: 'Explicit owned unsaved marker' };
    writePointer('profile', key); writeDraftEnvelope(key, draft, null);
    render(<StoreProvider><RecoveryProbe /></StoreProvider>); await settled();
    expect(screen.getByTestId('recovery-draft')).toHaveTextContent('Explicit owned unsaved marker');
    expect(call.profile).not.toHaveBeenCalled(); expect(call.list).not.toHaveBeenCalled();
  });
  it('keeps an empty authenticated workspace neutral', async () => {
    owner(); const call = reads([]);
    render(<StoreProvider><RecoveryProbe /></StoreProvider>); await settled();
    expect(screen.getByTestId('recovery-profile')).toHaveTextContent('none');
    expect(call.profile).not.toHaveBeenCalled(); expect(call.research).not.toHaveBeenCalled();
  });
  it('reports a case-list failure instead of inventing recovered data', async () => {
    owner(); const call = reads(); vi.mocked(api.cases).mockRejectedValue(new ApiError(500, 'Owned list unavailable'));
    render(<StoreProvider><RecoveryProbe /></StoreProvider>); await settled();
    expect(screen.getByTestId('recovery-error')).toHaveTextContent('Owned list unavailable');
    expect(call.profile).not.toHaveBeenCalled(); expect(call.research).not.toHaveBeenCalled();
  });
  it('keeps hydration closed while a server recovery waits, then honors newer new-case intent', async () => {
    owner(); const call = reads(); let answer!: (value: ApplicantCase[]) => void;
    vi.mocked(api.cases).mockReturnValue(new Promise((resolve) => { answer = resolve; }));
    render(<StoreProvider><RecoveryProbe /></StoreProvider>);
    expect(screen.getByTestId('recovery-hydrated')).toHaveTextContent('false');
    fireEvent.click(screen.getByText('explicit new applicant'));
    await act(async () => { answer([ownedCase]); }); await settled();
    expect(screen.getByTestId('recovery-profile')).toHaveTextContent('none');
    expect(call.profile).not.toHaveBeenCalled(); expect(call.list).not.toHaveBeenCalled();
  });
  it('drops a late profile answer after the authenticated owner changes', async () => {
    owner(); writePointer('profile', 'local:explicit-before-switch');
    const call = reads(); let answer!: (value: StoredProfile) => void;
    call.profile.mockReturnValue(new Promise((resolve) => { answer = resolve; }));
    // jsdom logs its unsupported location.reload; the owner fence must still refuse data.
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    render(<StoreProvider><RecoveryProbe /></StoreProvider>); await settled();
    fireEvent.click(screen.getByText('open authorized existing case'));
    await waitFor(() => expect(call.profile).toHaveBeenCalledWith(ownedCase.profile_id));
    owner('synthetic-B'); await act(async () => { answer(REAL_PROFILE); }); await settled();
    expect(screen.getByTestId('recovery-profile')).toHaveTextContent('none');
    expect(screen.getByTestId('recovery-run')).toHaveTextContent('none');
    expect(call.results).not.toHaveBeenCalled(); expect(call.create).not.toHaveBeenCalled();
  });
});


describe('an explicit new case releases a cancelled case switch', () => {
  it('releases loading and preserves blank intent after the old detail answer arrives', async () => {
    bindApplicantOwner({ enabled: true, authenticated: true, principal: {
      user_id: 'synthetic-switch-owner', organization_id: 'synthetic-switch-org', local_development: false,
    } } as never);
    writePointer('profile', 'local:before-explicit-switch');
    let answer!: (value: StoredProfile) => void;
    const detail = vi.spyOn(api, 'getProfile').mockReturnValue(new Promise((resolve) => { answer = resolve; }));
    vi.spyOn(api, 'listRuns').mockResolvedValue([]);
    const resultRead = vi.spyOn(api, 'results');
    const create = vi.spyOn(api, 'createProfile');
    const start = vi.spyOn(api, 'startRun');
    function SwitchProbe() {
      const store = useStore();
      return <div>
        <output data-testid="switch-loading">{String(store.loading)}</output>
        <output data-testid="switch-hydrated">{String(store.hydrated)}</output>
        <output data-testid="switch-profile">{store.savedProfile?.id ?? 'none'}</output>
        <output data-testid="switch-run">{store.run?.id ?? 'none'}</output>
        <output data-testid="switch-draft">{JSON.stringify(store.profileDraft)}</output>
        <button onClick={() => void store.switchCase(REAL_PROFILE.id)}>switch pending owned case</button>
        <button onClick={() => store.newCase()}>new case overrides switch</button>
        <button disabled={store.loading}>Save remains usable</button>
      </div>;
    }
    render(<StoreProvider><SwitchProbe /></StoreProvider>);
    await waitFor(() => expect(screen.getByTestId('switch-hydrated')).toHaveTextContent('true'));
    fireEvent.click(screen.getByText('switch pending owned case'));
    await waitFor(() => expect(detail).toHaveBeenCalledWith(REAL_PROFILE.id));
    expect(screen.getByTestId('switch-loading')).toHaveTextContent('true');
    fireEvent.click(screen.getByText('new case overrides switch'));
    await act(async () => { answer(REAL_PROFILE); });
    expect(screen.getByTestId('switch-loading')).toHaveTextContent('false');
    expect(screen.getByText('Save remains usable')).not.toBeDisabled();
    expect(screen.getByTestId('switch-profile')).toHaveTextContent('none');
    expect(screen.getByTestId('switch-run')).toHaveTextContent('none');
    expect(JSON.parse(screen.getByTestId('switch-draft').textContent!)).toEqual(blankProfile());
    expect(resultRead).not.toHaveBeenCalled(); expect(create).not.toHaveBeenCalled(); expect(start).not.toHaveBeenCalled();
  });
});

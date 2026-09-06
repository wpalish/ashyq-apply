/**
 * Draft lifecycle and case isolation regressions (T09 / FE01-FE03).
 *
 * These tests codify the frozen contract, not the current behaviour:
 *
 * - FE01: a brand-new (never saved to the server) case keeps its edits across
 *   a reload; the recovery block must not be gated on a server profile id.
 * - FE02: hydration gates autosave. A getProfile that answers slower than the
 *   600 ms debounce must not let the autosave tick wipe the persisted draft
 *   slot, and `hydrated` stays false until BOTH initial requests (profile and
 *   run) have settled.
 * - FE03: drafts are isolated per case. Persisted edits belong to the case
 *   they were made in and are never applied to another active case; a late
 *   response for case A after the user switched to case B is discarded whole;
 *   a corrupt envelope degrades to a controlled fallback without throwing.
 * - Error semantics: 404 proves the case is gone, 500/network keeps the
 *   pointers and reports the error.
 * - React StrictMode double mount leaves one final state and does not wipe
 *   the slot while hydration is pending.
 * - A2 (reviewer finding 3): a restored local-case draft survives not just one
 *   reload but a second one too — a restored draft is clean (baseline equals
 *   the envelope), so an autosave tick that treats "clean" as "delete the
 *   slot" loses the edits on the next reload.
 * - A2 (reviewer finding 1): a failed saveProfile loses nothing — the draft,
 *   the dirty flag and the persisted envelope stay, the error is reported,
 *   and a successful retry clears the dirty flag and retires the slot.
 *
 * Several of these fail at the baseline SHA on purpose (RED). Do not weaken
 * an assertion to match the bug being fixed.
 *
 * Storage layout note: tests seed only the legacy pointer keys
 * (`ashyq.activeProfile`, `ashyq.activeRun`) that the existing suite already
 * relies on, plus whatever the store itself writes while under test. No
 * private implementation key is assumed anywhere.
 */

import { StrictMode } from 'react';
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { StoreProvider, useStore } from './store';
import { DEFAULT_PROFILE } from './defaultProfile';
import { ApiError, api } from '@/api/client';
import type { RunView, StoredProfile } from '@/types';

const EDIT_MARKER = 'Georgia';

const PROFILE_A: StoredProfile = {
  ...structuredClone(DEFAULT_PROFILE),
  id: 'A',
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-02T00:00:00Z',
  display_name: 'Aisha (case A)',
  context: {
    ...structuredClone(DEFAULT_PROFILE).context,
    citizenship: 'Uzbekistan',
  },
} as unknown as StoredProfile;

const PROFILE_B: StoredProfile = {
  ...structuredClone(DEFAULT_PROFILE),
  id: 'B',
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-02T00:00:00Z',
  display_name: 'Bek (case B)',
  context: {
    ...structuredClone(DEFAULT_PROFILE).context,
    citizenship: 'Kyrgyzstan',
  },
} as unknown as StoredProfile;

const RUN_VIEW = {
  id: 'run-1', stage: 'completed', job_running: false, job_status: 'finished',
} as unknown as RunView;

function Probe() {
  const store = useStore();
  const context = store.profileDraft.context as Record<string, unknown> | undefined;
  return (
    <div>
      <span data-testid="display">{String(store.profileDraft.display_name)}</span>
      <span data-testid="citizenship">{String(context?.citizenship)}</span>
      <span data-testid="saved">{store.savedProfile?.id ?? 'none'}</span>
      <span data-testid="dirty">{String(store.dirty)}</span>
      <span data-testid="draft-restored">{String(store.draftRestored)}</span>
      <span data-testid="hydrated">{String(store.hydrated)}</span>
      <span data-testid="restored">{String(store.restored)}</span>
      <span data-testid="error">{store.error ?? ''}</span>
      <button onClick={() => store.setProfileDraft((d) => ({
        ...d,
        context: { ...(d.context as object), citizenship: EDIT_MARKER },
      }))}>edit</button>
      <button onClick={() => store.newCase()}>new</button>
      <button onClick={() => { void store.switchCase('A'); }}>switch-a</button>
      <button onClick={() => { void store.switchCase('B'); }}>switch-b</button>
    </div>
  );
}

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

/** Drain pending microtasks so the store's promise chains settle. */
async function flush(): Promise<void> {
  await act(async () => {
    for (let i = 0; i < 10; i += 1) await Promise.resolve();
  });
}

/** Fire due timers (the 600 ms autosave debounce) inside act. */
async function advance(ms: number): Promise<void> {
  await act(async () => {
    vi.advanceTimersByTime(ms);
    for (let i = 0; i < 3; i += 1) await Promise.resolve();
  });
}

function storageValues(store: Storage): string[] {
  const values: string[] = [];
  for (let i = 0; i < store.length; i += 1) {
    values.push(store.getItem(store.key(i) as string) ?? '');
  }
  return values;
}

/** True when some entry of either storage mentions the needle anywhere. */
function anyStorageMentions(needle: string): boolean {
  return [...storageValues(window.localStorage), ...storageValues(window.sessionStorage)]
    .some((value) => value.includes(needle));
}

/**
 * True when a pointer to the given id survived in some form: the legacy bare
 * value or a JSON-encoded one, in either storage.
 */
function pointerSurvives(id: string): boolean {
  return [...storageValues(window.localStorage), ...storageValues(window.sessionStorage)]
    .some((value) => value === id || value.includes(`"${id}"`));
}

/** localStorage keys whose stored value mentions the needle (draft slots). */
function draftSlotKeys(needle: string): string[] {
  const keys: string[] = [];
  for (let i = 0; i < window.localStorage.length; i += 1) {
    const key = window.localStorage.key(i) as string;
    if ((window.localStorage.getItem(key) ?? '').includes(needle)) keys.push(key);
  }
  return keys;
}

/** Edit one field through the public draft updater. */
async function editCitizenship(): Promise<void> {
  await act(async () => { screen.getByText('edit').click(); });
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  // Deterministic clock: the autosave debounce only fires when a test
  // advances it, never as a side effect of awaiting a promise.
  vi.useFakeTimers();
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({
    gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok',
  });
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'listRuns').mockResolvedValue([]);
  vi.spyOn(api, 'results').mockResolvedValue([]);
  vi.spyOn(api, 'summary').mockResolvedValue({} as never);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('FE01: a brand-new unsaved case survives a reload', () => {
  it('restores the edits and flags draftRestored after a remount', async () => {
    // No legacy pointer: this case has never existed on the server.
    const view = render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    await act(async () => { screen.getByText('new').click(); });
    await editCitizenship();
    expect(screen.getByTestId('citizenship')).toHaveTextContent(EDIT_MARKER);
    expect(screen.getByTestId('dirty')).toHaveTextContent('true');

    // The debounced autosave persists the new case's draft, then the tab
    // reloads: same window, so the per-tab pointer is still there.
    await advance(600);
    expect(anyStorageMentions(EDIT_MARKER)).toBe(true);
    view.unmount();

    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    expect(screen.getByTestId('citizenship')).toHaveTextContent(EDIT_MARKER);
    expect(screen.getByTestId('draft-restored')).toHaveTextContent('true');
    expect(screen.getByTestId('saved')).toHaveTextContent('none');
  });

  it('keeps a restored local-case draft across a second reload', async () => {
    // Session one: a brand-new case gets an edit, autosaved into its own slot.
    const first = render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    await act(async () => { screen.getByText('new').click(); });
    await editCitizenship();
    expect(screen.getByTestId('dirty')).toHaveTextContent('true');
    await advance(600);
    expect(anyStorageMentions(EDIT_MARKER)).toBe(true);
    first.unmount();

    // First reload: the edits come back (covered by the test above).
    const second = render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    expect(screen.getByTestId('citizenship')).toHaveTextContent(EDIT_MARKER);
    expect(screen.getByTestId('draft-restored')).toHaveTextContent('true');

    // Let the autosave debounce tick while the restored draft sits unedited.
    // The restored draft is clean, so this tick must not treat the case as
    // "nothing worth keeping": a local case has no server copy to fall back
    // to, and the next reload reads only what this slot holds.
    await advance(600);
    second.unmount();

    // Second reload without new edits: the restored draft must still be there.
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    expect(screen.getByTestId('citizenship')).toHaveTextContent(EDIT_MARKER);
    expect(screen.getByTestId('draft-restored')).toHaveTextContent('true');
    expect(screen.getByTestId('saved')).toHaveTextContent('none');
  });
});

describe('a rejected save keeps the draft and reports the error', () => {
  function SaveProbe() {
    const store = useStore();
    const context = store.profileDraft.context as Record<string, unknown> | undefined;
    return (
      <div>
        <span data-testid="citizenship">{String(context?.citizenship)}</span>
        <span data-testid="saved">{store.savedProfile?.id ?? 'none'}</span>
        <span data-testid="dirty">{String(store.dirty)}</span>
        <span data-testid="loading">{String(store.loading)}</span>
        <span data-testid="error">{store.error ?? ''}</span>
        <button onClick={() => store.setProfileDraft((d) => ({
          ...d,
          context: { ...(d.context as object), citizenship: EDIT_MARKER },
        }))}>edit</button>
        <button onClick={() => {
          // A rejected save rethrows after reporting; the UI just calls it.
          void store.saveProfile().catch(() => { /* asserted via `error` */ });
        }}>save</button>
      </div>
    );
  }

  it('loses nothing on a failed save and retires the slot on a successful retry', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(PROFILE_A);
    render(<StoreProvider><SaveProbe /></StoreProvider>);
    await flush();
    expect(screen.getByTestId('saved')).toHaveTextContent('A');

    await editCitizenship();
    await advance(600);
    // The unsaved edit is persisted in the case's own slot before saving.
    expect(draftSlotKeys(EDIT_MARKER).length).toBeGreaterThan(0);

    // Save fails: the edit stays dirty, the envelope stays persisted and the
    // failure is reported instead of being swallowed as a silent success.
    const update = vi.spyOn(api, 'updateProfile')
      .mockRejectedValueOnce(new ApiError(500, 'The database is unreachable.'));
    await act(async () => { screen.getByText('save').click(); });
    await flush();

    expect(screen.getByTestId('error')).toHaveTextContent('The database is unreachable');
    expect(screen.getByTestId('dirty')).toHaveTextContent('true');
    expect(screen.getByTestId('saved')).toHaveTextContent('A');
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(draftSlotKeys(EDIT_MARKER).length).toBeGreaterThan(0);

    // Retry succeeds: the draft is saved, dirty clears, the error clears and
    // the now-merged draft slot retires — the saved profile is the baseline.
    update.mockResolvedValue({
      ...structuredClone(PROFILE_A),
      updated_at: '2026-08-03T00:00:00Z',
      context: { ...(structuredClone(PROFILE_A).context as object), citizenship: EDIT_MARKER },
    } as unknown as StoredProfile);
    await act(async () => { screen.getByText('save').click(); });
    await flush();

    expect(screen.getByTestId('dirty')).toHaveTextContent('false');
    expect(screen.getByTestId('error')).toBeEmptyDOMElement();
    expect(screen.getByTestId('saved')).toHaveTextContent('A');
    expect(draftSlotKeys(EDIT_MARKER)).toEqual([]);
  });
});

describe('FE02: hydration gates autosave', () => {
  it('does not wipe the draft slot while getProfile is slower than the debounce', async () => {
    // Session one: edit case A and let the autosave persist the draft.
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(PROFILE_A);
    const first = render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    await editCitizenship();
    await advance(600);
    expect(anyStorageMentions(EDIT_MARKER)).toBe(true);
    first.unmount();

    // Session two: the profile request answers after the autosave tick.
    const slowProfile = deferred<StoredProfile>();
    vi.spyOn(api, 'getProfile').mockReturnValue(slowProfile.promise);
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    // The debounce fires while hydration is still pending…
    await advance(600);
    // …and must not have wiped the persisted draft.
    expect(anyStorageMentions(EDIT_MARKER)).toBe(true);

    // Once hydration settles, the stored edits come back.
    await act(async () => { slowProfile.resolve(PROFILE_A); });
    await flush();
    expect(screen.getByTestId('citizenship')).toHaveTextContent(EDIT_MARKER);
    expect(screen.getByTestId('draft-restored')).toHaveTextContent('true');
    expect(screen.getByTestId('hydrated')).toHaveTextContent('true');
  });

  it('keeps hydrated false until the profile request settles', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    const slowProfile = deferred<StoredProfile>();
    vi.spyOn(api, 'getProfile').mockReturnValue(slowProfile.promise);

    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    // No run is stored: the profile request is the only one in flight, and
    // hydration is not done while it is pending.
    expect(screen.getByTestId('hydrated')).toHaveTextContent('false');

    await act(async () => { slowProfile.resolve(PROFILE_A); });
    await flush();
    expect(screen.getByTestId('hydrated')).toHaveTextContent('true');
    expect(screen.getByTestId('restored')).toHaveTextContent('true');
  });

  it('keeps hydrated false until both the profile and the run settle', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    window.localStorage.setItem('ashyq.activeRun', RUN_VIEW.id);
    const slowProfile = deferred<StoredProfile>();
    const slowRun = deferred<RunView>();
    vi.spyOn(api, 'getProfile').mockReturnValue(slowProfile.promise);
    vi.spyOn(api, 'getRun').mockReturnValue(slowRun.promise);

    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    expect(screen.getByTestId('hydrated')).toHaveTextContent('false');

    await act(async () => { slowProfile.resolve(PROFILE_A); });
    await flush();
    expect(screen.getByTestId('hydrated')).toHaveTextContent('false');

    await act(async () => { slowRun.resolve(RUN_VIEW); });
    await flush();
    expect(screen.getByTestId('hydrated')).toHaveTextContent('true');
  });
});

describe('FE03: case isolation', () => {
  it('never applies case A saved edits to case B after a reload', async () => {
    // Session one: case A active, an unsaved draft is persisted for A.
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile').mockImplementation(
      (id: string) => Promise.resolve(id === PROFILE_A.id ? PROFILE_A : PROFILE_B),
    );
    const first = render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    await editCitizenship();
    await advance(600);
    first.unmount();

    // Session two: the next reload opens case B. The per-tab pointer is
    // cleared so the re-seeded legacy pointer is the only active-case source.
    window.sessionStorage.clear();
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_B.id);
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    expect(screen.getByTestId('citizenship')).toHaveTextContent('Kyrgyzstan');
    expect(screen.getByTestId('display')).toHaveTextContent('Bek (case B)');
    expect(screen.getByTestId('draft-restored')).toHaveTextContent('false');
  });

  it('keeps case A draft through a round trip A → B → A', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile').mockImplementation(
      (id: string) => Promise.resolve(id === PROFILE_A.id ? PROFILE_A : PROFILE_B),
    );
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    await editCitizenship();
    await advance(600);

    // Switch away: B must show only B.
    await act(async () => { screen.getByText('switch-b').click(); });
    await flush();
    expect(screen.getByTestId('citizenship')).toHaveTextContent('Kyrgyzstan');

    // Switch back: A's own unsaved edits must still be there.
    await act(async () => { screen.getByText('switch-a').click(); });
    await flush();
    expect(screen.getByTestId('citizenship')).toHaveTextContent(EDIT_MARKER);
  });

  it('discards a late response for case A after the user moved to case B', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    const lateA = deferred<StoredProfile>();
    let aCalls = 0;
    vi.spyOn(api, 'getProfile').mockImplementation((id: string) => {
      if (id === PROFILE_A.id) {
        aCalls += 1;
        return aCalls === 1 ? Promise.resolve(PROFILE_A) : lateA.promise;
      }
      return Promise.resolve(PROFILE_B);
    });

    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    expect(screen.getByTestId('saved')).toHaveTextContent('A');

    // Switch to B (fast), start a switch back to A that hangs, then switch to
    // B again before the stale A answer arrives.
    await act(async () => { screen.getByText('switch-b').click(); });
    await flush();
    expect(screen.getByTestId('saved')).toHaveTextContent('B');

    await act(async () => { screen.getByText('switch-a').click(); });
    await flush();
    await act(async () => { screen.getByText('switch-b').click(); });
    await flush();
    expect(screen.getByTestId('saved')).toHaveTextContent('B');

    // The stale A answer lands last. The final state must still be B.
    await act(async () => { lateA.resolve(PROFILE_A); });
    await flush();
    expect(screen.getByTestId('saved')).toHaveTextContent('B');
    expect(screen.getByTestId('citizenship')).toHaveTextContent('Kyrgyzstan');
    expect(screen.getByTestId('display')).toHaveTextContent('Bek (case B)');
    expect(screen.getByTestId('error')).toBeEmptyDOMElement();
  });

  it('falls back to the server profile and drops an envelope with an unknown version', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(PROFILE_A);
    const first = render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    await editCitizenship();
    await advance(600);

    // Whatever slot(s) the autosave wrote for this draft, rewrite the payload
    // as an envelope whose schema version the store cannot know.
    const slots = draftSlotKeys(EDIT_MARKER);
    expect(slots.length).toBeGreaterThan(0);
    for (const key of slots) {
      window.localStorage.setItem(key, JSON.stringify({
        v: 999,
        case_key: PROFILE_A.id,
        saved_at: '2026-08-03T00:00:00Z',
        draft: { display_name: 'ENVELOPE GARBAGE' },
      }));
    }
    first.unmount();

    window.sessionStorage.clear();
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    // Controlled fallback: the server profile is shown, not the garbage, and
    // the unreadable slot is removed rather than left behind.
    expect(screen.getByTestId('display')).toHaveTextContent('Aisha (case A)');
    expect(screen.getByTestId('citizenship')).toHaveTextContent('Uzbekistan');
    for (const key of slots) {
      expect(window.localStorage.getItem(key)).toBeNull();
    }
  });

  it('ignores an envelope that belongs to a different case', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(PROFILE_A);
    const first = render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    await editCitizenship();
    await advance(600);

    const slots = draftSlotKeys(EDIT_MARKER);
    expect(slots.length).toBeGreaterThan(0);
    for (const key of slots) {
      window.localStorage.setItem(key, JSON.stringify({
        v: 1,
        case_key: 'some-other-case',
        saved_at: '2026-08-03T00:00:00Z',
        draft: { display_name: 'ENVELOPE GARBAGE' },
      }));
    }
    first.unmount();

    window.sessionStorage.clear();
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    // A foreign case_key is never applied to the active case.
    expect(screen.getByTestId('display')).toHaveTextContent('Aisha (case A)');
    expect(screen.getByTestId('citizenship')).toHaveTextContent('Uzbekistan');
  });

  it('falls back cleanly when the draft slot holds broken JSON', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(PROFILE_A);
    const first = render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    await editCitizenship();
    await advance(600);

    const slots = draftSlotKeys(EDIT_MARKER);
    expect(slots.length).toBeGreaterThan(0);
    for (const key of slots) window.localStorage.setItem(key, '{not-json');
    first.unmount();

    window.sessionStorage.clear();
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    expect(screen.getByTestId('display')).toHaveTextContent('Aisha (case A)');
    for (const key of slots) {
      expect(window.localStorage.getItem(key)).toBeNull();
    }
  });
});

describe('error semantics on initial hydration', () => {
  it('treats 404 as proof the case is gone and forgets the pointer', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile').mockRejectedValue(new ApiError(404, 'Not found.'));
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    expect(window.localStorage.getItem('ashyq.activeProfile')).toBeNull();
    // Forgotten completely: the per-tab pointer is gone too, and no storage
    // still carries the id in any form (unlike a 500, which keeps it).
    expect(window.sessionStorage.getItem('ashyq.activeProfile')).toBeNull();
    expect(pointerSurvives(PROFILE_A.id)).toBe(false);
    // A proven absence is not an error to report.
    expect(screen.getByTestId('error')).toBeEmptyDOMElement();
  });

  it('keeps the case pointer and reports a 500', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile')
      .mockRejectedValue(new ApiError(500, 'The database is unreachable.'));
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    // A transient failure is not evidence that the case disappeared: the
    // pointer must survive so a retry can find the case again.
    expect(pointerSurvives(PROFILE_A.id)).toBe(true);
    expect(screen.getByTestId('error')).toHaveTextContent('The database is unreachable');
  });

  it('keeps the run pointer when the stored run cannot be fetched right now', async () => {
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    window.localStorage.setItem('ashyq.activeRun', RUN_VIEW.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(PROFILE_A);
    vi.spyOn(api, 'getRun')
      .mockRejectedValue(new ApiError(0, 'Cannot reach the ASHYQ Apply API.'));
    render(<StoreProvider><Probe /></StoreProvider>);
    await flush();

    expect(pointerSurvives(RUN_VIEW.id)).toBe(true);
  });
});

describe('React StrictMode double mount', () => {
  it('leaves one final state and does not wipe the slot during hydration', async () => {
    // Session one creates a persisted draft the usual way.
    window.localStorage.setItem('ashyq.activeProfile', PROFILE_A.id);
    vi.spyOn(api, 'getProfile').mockResolvedValue(PROFILE_A);
    const first = render(<StoreProvider><Probe /></StoreProvider>);
    await flush();
    await editCitizenship();
    await advance(600);
    first.unmount();

    // Session two mounts under StrictMode, so every effect runs twice while
    // the profile request is still pending.
    const slowProfile = deferred<StoredProfile>();
    vi.spyOn(api, 'getProfile').mockReturnValue(slowProfile.promise);
    render(
      <StrictMode>
        <StoreProvider><Probe /></StoreProvider>
      </StrictMode>,
    );
    await flush();
    await advance(600);
    expect(anyStorageMentions(EDIT_MARKER)).toBe(true);

    await act(async () => { slowProfile.resolve(PROFILE_A); });
    await flush();
    expect(screen.getByTestId('citizenship')).toHaveTextContent(EDIT_MARKER);
    expect(screen.getByTestId('draft-restored')).toHaveTextContent('true');
  });
});

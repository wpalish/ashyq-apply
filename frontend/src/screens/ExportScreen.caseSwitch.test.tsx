/** Synthetic integration controls for App's same-owner case switch on Export. */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '@/App';
import { api } from '@/api/client';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import type { RunView, StoredProfile } from '@/types';

const state = vi.hoisted(() => ({
  value: {} as Record<string, unknown>,
  listeners: new Set<() => void>(),
}));
vi.mock('@/lib/store', async () => {
  const { useSyncExternalStore } = await import('react');
  return {
    useStore: () => useSyncExternalStore(
      (listener) => { state.listeners.add(listener); return () => { state.listeners.delete(listener); }; },
      () => state.value,
      () => state.value,
    ),
  };
});

const profile = (id: string, display_name: string): StoredProfile => ({
  ...structuredClone(DEFAULT_PROFILE), revision:1, id, display_name,
  created_at: '2026-10-09T00:00:00Z', updated_at: '2026-10-09T00:00:00Z',
}) as StoredProfile;
const a = profile('synthetic-case-a', 'Synthetic case A');
const b = profile('synthetic-case-b', 'Synthetic case B');
const run = (id: string): RunView => ({
  id: `synthetic-run-${id}`, profile_id: id, stage: 'awaiting_user_decision',
  job_running: false, cancelled: false, progress: 1, results_count: 0,
  claims_recorded: 0, pages_checked: 0, demo_mode: true,
}) as RunView;
const record = (saved: StoredProfile) => ({ profile: { id: saved.id, display_name: saved.display_name }, runs: [] });
function publish(patch: Record<string, unknown>) {
  state.value = { ...state.value, ...patch };
  state.listeners.forEach((listener) => listener());
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
async function flush() {
  await act(async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); });
}
const caseInput = () => screen.getByLabelText('Applicant');
const confirmInput = () => screen.getByTestId('delete-confirm');

beforeEach(() => {
  localStorage.clear(); sessionStorage.clear();
  const owner = 'auth:["synthetic-owner","synthetic-workspace"]';
  localStorage.setItem('ashyq.applicantOwner', owner);
  sessionStorage.setItem('ashyq.applicantOwner', owner);
  window.location.hash = '#/export';
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  // No native transport is allowed; all three shell requests and export are explicit mocks.
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in synthetic export control'); }));
  vi.spyOn(api, 'authStatus').mockResolvedValue({
    enabled: true, authenticated: true, registration_enabled: false,
    principal: { user_id: 'synthetic-owner', organization_id: 'synthetic-workspace',
      email: 'owner@example.test', display_name: 'Synthetic owner',
      organization_name: 'Synthetic workspace', role: 'owner', local_development: false },
  });
  vi.spyOn(api, 'socialMe').mockResolvedValue({ joined: false, profile: null });
  vi.spyOn(api, 'unreadMessages').mockResolvedValue({ unread: 0 });
  vi.spyOn(api, 'exportProfile').mockImplementation(async (id) => record(id === a.id ? a : b));
  state.value = {
    run: run(a.id), results: [], summary: null, error: null, clearError: vi.fn(),
    capabilities: null, paywall: null, dirty: false, hydrated: true, loading: false,
    savedProfile: a, caseEpoch: 0,
    cases: [a, b].map((saved) => ({ id: saved.id, profile_id: saved.id, display_name: saved.display_name, run_count: 1 })),
    newCase: vi.fn(),
    switchCase: vi.fn(async (id: string) => {
      publish({ caseEpoch: Number(state.value.caseEpoch) + 1, savedProfile: id === a.id ? a : b, run: run(id) });
    }),
    deleteEverything: vi.fn(async () => {
      // The actual store clears the accepted case and advances caseEpoch before returning true.
      publish({ savedProfile: null, run: null, results: [], summary: null,
        caseEpoch: Number(state.value.caseEpoch) + 1 });
      return true;
    }),
    exportShortlist: vi.fn(),
  };
});
afterEach(() => {
  expect(fetch).not.toHaveBeenCalled();
  cleanup(); state.listeners.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals();
});

describe('export state follows the same-owner active case', () => {
  it('retains confirmation and shown data on an ordinary same-case store redraw', async () => {
    render(<App />); await flush();
    fireEvent.click(screen.getByTestId('export-profile')); await flush();
    fireEvent.change(confirmInput(), { target: { value: 'DELETE' } });
    await act(async () => { publish({ savedProfile: { ...a, updated_at: '2026-10-09T00:01:00Z' }, error: null }); });
    expect(confirmInput()).toHaveValue('DELETE');
    expect(screen.getByTestId('delete-everything')).toBeEnabled();
    expect(screen.getByLabelText('Stored profile data')).toHaveTextContent(a.display_name);
    expect(api.exportProfile).toHaveBeenCalledTimes(1);
    expect(state.value.deleteEverything).not.toHaveBeenCalled();
  });

  it('does not transfer A confirmation or shown output to B at the delayed case commit', async () => {
    const commit = deferred<void>();
    state.value.switchCase = vi.fn(async (id: string) => {
      // Mirrors store.switchCase: epoch changes at entry; savedProfile changes only after the reads.
      publish({ caseEpoch: Number(state.value.caseEpoch) + 1, loading: true });
      await commit.promise;
      publish({ savedProfile: b, run: run(id), loading: false });
    });
    render(<App />); await flush();
    fireEvent.click(screen.getByTestId('export-profile')); await flush();
    fireEvent.change(confirmInput(), { target: { value: 'DELETE' } });
    fireEvent.change(caseInput(), { target: { value: b.id } }); await flush();
    expect(state.value.switchCase).toHaveBeenCalledWith(b.id);
    // If A remains editable while B loads, fresh typing there still belongs to A.
    const duringSwitch = screen.queryByTestId('delete-confirm') as HTMLInputElement | null;
    if (duringSwitch && !duringSwitch.disabled) fireEvent.change(duringSwitch, { target: { value: 'DELETE' } });
    await act(async () => { commit.resolve(); }); await flush();
    expect(caseInput()).toHaveValue(b.id);
    expect({
      confirmation: (confirmInput() as HTMLInputElement).value,
      deleteDisabled: (screen.getByTestId('delete-everything') as HTMLButtonElement).disabled,
      oldExportVisible: screen.queryByLabelText('Stored profile data')?.textContent?.includes(a.display_name) ?? false,
    }).toEqual({ confirmation: '', deleteDisabled: true, oldExportVisible: false });
    fireEvent.click(screen.getByTestId('delete-everything'));
    expect(state.value.deleteEverything).not.toHaveBeenCalled();
    fireEvent.change(confirmInput(), { target: { value: 'DELETE' } });
    expect(screen.getByTestId('delete-everything')).toBeEnabled();
  });

  it('does not show a late A export response after the same-screen switch commits B', async () => {
    const pending = deferred<ReturnType<typeof record>>();
    vi.mocked(api.exportProfile).mockImplementationOnce(() => pending.promise);
    render(<App />); await flush();
    fireEvent.click(screen.getByTestId('export-profile')); await flush();
    expect(api.exportProfile).toHaveBeenCalledWith(a.id);
    fireEvent.change(caseInput(), { target: { value: b.id } }); await flush();
    expect(caseInput()).toHaveValue(b.id);
    await act(async () => { pending.resolve(record(a)); }); await flush();
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('export-profile')); await flush();
    expect(api.exportProfile).toHaveBeenLastCalledWith(b.id);
    expect(screen.getByLabelText('Stored profile data')).toHaveTextContent(b.display_name);
    expect(screen.getByLabelText('Stored profile data')).not.toHaveTextContent(a.display_name);
  });

  it('preserves the actual successful delete receipt when its own store acknowledgment clears the case', async () => {
    render(<App />); await flush();
    fireEvent.change(confirmInput(), { target: { value: 'DELETE' } });
    fireEvent.click(screen.getByTestId('delete-everything')); await flush();
    expect(state.value.deleteEverything).toHaveBeenCalledTimes(1);
    expect(state.value.savedProfile).toBeNull();
    expect(screen.getByText(/Deleted\. The profile and its linked research records/)).toBeInTheDocument();
  });
});

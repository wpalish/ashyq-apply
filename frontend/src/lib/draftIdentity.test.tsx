import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { AuthGate } from '@/AuthGate';
import { ApiError, api } from '@/api/client';
import { APPLICANT_OWNER_KEY, applicantStorageKey, bindApplicantOwner } from '@/lib/applicantStorage';
import { adoptPointer, readDraftEnvelope, writeDraftEnvelope, writePointer } from '@/lib/caseDrafts';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import { StoreProvider, useStore } from '@/lib/store';
import type { AuthPrincipal, AuthStatus, StoredProfile } from '@/types';

const principal = (user = 'A', org = 'org-A'): AuthPrincipal => ({
  user_id: user, organization_id: org, email: `${user}@synthetic.invalid`,
  display_name: user, organization_name: org, role: 'owner', local_development: false,
});
const scope = (p: AuthPrincipal) => JSON.stringify([p.user_id, p.organization_id]);
const status = (p: AuthPrincipal | null): AuthStatus => ({
  enabled: true, registration_enabled: true, authenticated: true, principal: p,
});
const stored: StoredProfile = {
  ...structuredClone(DEFAULT_PROFILE), id: 'saved-A', display_name: 'draft private marker',
  created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
};
function Probe() {
  const s = useStore();
  return <div>
    <span data-testid="draft">{String(s.profileDraft.display_name)}</span>
    <span data-testid="saved">{s.savedProfile?.id ?? 'none'}</span>
    <span data-testid="save-error">{s.error ?? ''}</span>
    <button onClick={() => s.setProfileDraft(d => ({ ...d, display_name: 'draft private marker' }))}>Edit draft</button>
    <button onClick={() => { void s.saveProfile().catch(() => {}); }}>Save draft</button>
  </div>;
}
function tree() { return <AuthGate><StoreProvider><Probe /></StoreProvider></AuthGate>; }
async function flush() { await act(async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); }); }
async function persist() {
  fireEvent.click(screen.getByRole('button', { name: 'Edit draft' }));
  await act(async () => { vi.advanceTimersByTime(600); });
  await flush();
}
beforeEach(() => {
  vi.useFakeTimers(); localStorage.clear(); sessionStorage.clear(); window.location.hash = '#/home';
  vi.spyOn(api, 'authStatus').mockResolvedValue(status(principal()));
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({ gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok' });
  vi.spyOn(api, 'getProfile').mockRejectedValue(new ApiError(404, 'No owned synthetic profile'));
});
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it('acknowledged real-client logout erases A drafts before B or A can return', async () => {
  const a = render(tree()); await flush(); await persist();
  const aCase = adoptPointer('profile', scope(principal()));
  expect(aCase).not.toBeNull();
  const aSlot = applicantStorageKey(`ashyq.draft.${aCase}`)!;
  expect(localStorage.getItem(aSlot)).toContain('draft private marker');
  localStorage.setItem('unimatch.theme', 'dark');
  const transport = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal('fetch', transport);
  await api.logout();
  expect(transport).toHaveBeenCalledWith('/api/auth/logout', expect.objectContaining({ method: 'POST' }));
  expect(localStorage.getItem(aSlot)).toBeNull();
  expect(localStorage.getItem('unimatch.theme')).toBe('dark');
  expect(sessionStorage.getItem(APPLICANT_OWNER_KEY)).toBe('signed-out');
  a.unmount();
  vi.mocked(api.authStatus).mockResolvedValue(status(principal('B', 'org-B')));
  const b = render(tree()); await flush();
  expect(screen.getByTestId('draft')).not.toHaveTextContent('private marker');
  expect(api.getProfile).not.toHaveBeenCalled();
  b.unmount(); vi.mocked(api.authStatus).mockResolvedValue(status(principal()));
  render(tree()); await flush();
  expect(screen.getByTestId('draft')).not.toHaveTextContent('private marker');
  expect(adoptPointer('profile', scope(principal()))).toBeNull();
});
it('organization change erases the previous workspace slot instead of keeping a private backup', async () => {
  const a = render(tree()); await flush(); await persist();
  const oldCase = adoptPointer('profile', scope(principal()))!;
  const oldSlot = applicantStorageKey(`ashyq.draft.${oldCase}`)!;
  a.unmount();
  vi.mocked(api.authStatus).mockResolvedValue(status(principal('A', 'org-B')));
  render(tree()); await flush();
  expect(screen.getByTestId('draft')).not.toHaveTextContent('private marker');
  expect(localStorage.getItem(oldSlot)).toBeNull();
  expect(readDraftEnvelope(oldCase, scope(principal()))).toBeNull();
});
it('authenticated binding erases unowned drafts and pointers while preserving appearance', async () => {
  writePointer('profile', 'local:unowned');
  writeDraftEnvelope('local:unowned', { ...structuredClone(DEFAULT_PROFILE), display_name: 'Previous unknown account' });
  localStorage.setItem('ashyq.unsavedDraft', JSON.stringify({ display_name: 'Bare unowned draft' }));
  localStorage.setItem('unimatch.theme', 'dark');
  render(tree()); await flush();
  expect(screen.getByTestId('draft')).not.toHaveTextContent('Previous unknown account');
  expect(screen.getByTestId('draft')).not.toHaveTextContent('Bare unowned draft');
  expect(localStorage.getItem('ashyq.draft.local:unowned')).toBeNull();
  expect(localStorage.getItem('ashyq.unsavedDraft')).toBeNull();
  expect(sessionStorage.getItem('ashyq.activeProfile')).toBeNull();
  expect(adoptPointer('profile', scope(principal()))).toBeNull();
  expect(localStorage.getItem('unimatch.theme')).toBe('dark');
});
it('an enabled authenticated response without a verified principal locks the private tree', async () => {
  writePointer('profile', 'local:unowned');
  writeDraftEnvelope('local:unowned', { display_name: 'Previous account secret' });
  vi.mocked(api.authStatus).mockResolvedValue(status(null));
  const create = vi.spyOn(api, 'createProfile');
  render(tree()); await flush();
  expect(screen.queryByTestId('draft')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Edit draft' })).not.toBeInTheDocument();
  expect(screen.getByText('The server did not identify this workspace. Sign in again.')).toBeVisible();
  expect(api.getProfile).not.toHaveBeenCalled();
  expect(create).not.toHaveBeenCalled();
});
it('an old mounted identity cannot recreate its draft when the shared-cookie owner changes before an event', async () => {
  const a = render(tree()); await flush();
  fireEvent.click(screen.getByRole('button', { name: 'Edit draft' }));
  // Real binding, not two independent cookie owners on one origin.
  bindApplicantOwner(status(principal('B', 'org-B')));
  await act(async () => { vi.advanceTimersByTime(600); }); await flush();
  expect(adoptPointer('profile', scope(principal()))).toBeNull();
  const ownedKeys = Array.from({ length: localStorage.length }, (_, i) => localStorage.key(i));
  expect(ownedKeys.filter(key => key?.startsWith('ashyq.owner.'))).toEqual([]);
  expect(adoptPointer('profile', scope(principal('B', 'org-B')))).toBeNull();
  a.unmount();
  vi.mocked(api.authStatus).mockResolvedValue(status(principal('B', 'org-B')));
  render(tree()); await flush(); await persist();
  const bCase = adoptPointer('profile', scope(principal('B', 'org-B')))!;
  expect(readDraftEnvelope(bCase, scope(principal('B', 'org-B')))?.draft.display_name).toBe('draft private marker');
  expect(readDraftEnvelope(bCase, scope(principal()))).toBeNull();
});
it('a canonically scoped saved pointer still requires server ownership before restoring its draft', async () => {
  const aScope = scope(principal()); bindApplicantOwner(status(principal()));
  writePointer('profile', 'wrong-owner', aScope);
  writeDraftEnvelope('wrong-owner', { display_name: 'Blocked saved draft' }, undefined, aScope);
  render(tree()); await flush();
  expect(api.getProfile).toHaveBeenCalledWith('wrong-owner');
  expect(screen.getByTestId('draft')).not.toHaveTextContent('Blocked saved draft');
  expect(screen.getByTestId('saved')).toHaveTextContent('none');
  expect(adoptPointer('profile', aScope)).toBeNull();
  expect(readDraftEnvelope('wrong-owner', aScope)).toBeNull();
});
it('changing the authenticated owner erases old run pointers and never requests that run', async () => {
  const aScope = scope(principal()); bindApplicantOwner(status(principal()));
  writePointer('run', 'private-A-run', aScope);
  const aRunKey = applicantStorageKey('ashyq.activeRun')!;
  sessionStorage.setItem('ashyq.activeRun', 'unowned-legacy-run');
  const getRun = vi.spyOn(api, 'getRun');
  vi.mocked(api.authStatus).mockResolvedValue(status(principal('B', 'org-B')));
  render(tree()); await flush();
  expect(getRun).not.toHaveBeenCalled();
  expect(sessionStorage.getItem(aRunKey)).toBeNull();
  expect(sessionStorage.getItem('ashyq.activeRun')).toBeNull();
  expect(adoptPointer('run', aScope)).toBeNull();
  expect(adoptPointer('run', scope(principal('B', 'org-B')))).toBeNull();
});
it('the active owner keeps local edits after a failed save, recovers on reload and can explicitly retry', async () => {
  const create = vi.spyOn(api, 'createProfile').mockRejectedValueOnce(new ApiError(503, 'Synthetic save refused'));
  const first = render(tree()); await flush(); await persist();
  const localCase = adoptPointer('profile', scope(principal()))!;
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' })); await flush();
  expect(screen.getByTestId('save-error')).toHaveTextContent('Synthetic save refused');
  expect(screen.getByTestId('draft')).toHaveTextContent('draft private marker');
  expect(adoptPointer('profile', scope(principal()))).toBe(localCase);
  expect(readDraftEnvelope(localCase, scope(principal()))?.draft.display_name).toBe('draft private marker');
  first.unmount(); render(tree()); await flush();
  expect(screen.getByTestId('draft')).toHaveTextContent('draft private marker');
  create.mockResolvedValueOnce(stored);
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' })); await flush();
  expect(create).toHaveBeenCalledTimes(2);
  expect(screen.getByTestId('saved')).toHaveTextContent(stored.id);
  expect(readDraftEnvelope(localCase, scope(principal()))).toBeNull();
  expect(adoptPointer('profile', scope(principal()))).toBe(stored.id);
});
it('explicit and legacy helper callers share exactly one primary canonical authenticated namespace', () => {
  const aScope = scope(principal()); bindApplicantOwner(status(principal()));
  writePointer('profile', 'local:canonical', aScope);
  writeDraftEnvelope('local:canonical', { display_name: 'Canonical draft' }, undefined, aScope);
  expect(adoptPointer('profile')).toBe('local:canonical');
  expect(readDraftEnvelope('local:canonical')?.draft.display_name).toBe('Canonical draft');
  const expected = `ashyq.owner.${encodeURIComponent(`auth:${aScope}`)}.ashyq.draft.local:canonical`;
  expect(applicantStorageKey('ashyq.draft.local:canonical')).toBe(expected);
  expect(localStorage.getItem(expected)).toContain('Canonical draft');
  expect(localStorage.getItem(`ashyq.owner.${encodeURIComponent(aScope)}.draft.local:canonical`)).toBeNull();
});

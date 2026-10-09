import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StoreProvider, useStore } from './store';
import { DEFAULT_PROFILE } from './defaultProfile';
import { api } from '@/api/client';
import { bindApplicantOwner } from './applicantStorage';
import { writePointer } from './caseDrafts';
import type { ApplicantCase, RunView, StoredProfile } from '@/types';

const profile = { ...structuredClone(DEFAULT_PROFILE), id: 'peer-owned-case', display_name: 'Peer saved applicant',
  created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-02T00:00:00Z' } as unknown as StoredProfile;
const ownedCase = { id: profile.id, profile_id: profile.id, display_name: profile.display_name, status: 'active',
  run_count: 1, created_at: profile.created_at, updated_at: profile.updated_at } as ApplicantCase;
const run = { id: 'peer-latest-run', profile_id: profile.id, stage: 'awaiting_user_decision', job_running: false,
  job_status: 'succeeded' } as RunView;
function Probe() {
 const s = useStore();
 return <><output data-testid="state">{JSON.stringify({ profile: s.savedProfile?.id ?? null, run: s.run?.id ?? null,
  results: s.results.map(r => r.id), hydrated: s.hydrated, loading: s.loading })}</output>
  <button onClick={s.newCase}>New case during recovery</button></>;
}
function state() { return JSON.parse(screen.getByTestId('state').textContent!); }
function owner(user = 'peer-A') { bindApplicantOwner({ enabled: true, authenticated: true, principal: {
 user_id: user, organization_id: user + '-org', local_development: false } } as never); }
beforeEach(() => {
 window.localStorage.clear(); window.sessionStorage.clear(); vi.restoreAllMocks(); owner();
 vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
 vi.spyOn(api, 'cases').mockResolvedValue([ownedCase]);
 vi.spyOn(api, 'getProfile').mockResolvedValue(profile);
 vi.spyOn(api, 'listRuns').mockResolvedValue([run]);
 vi.spyOn(api, 'results').mockResolvedValue([{ id: 'peer-result' }] as never);
 vi.spyOn(api, 'summary').mockResolvedValue({} as never);
 vi.spyOn(api, 'shortlist').mockResolvedValue({} as never);
 vi.spyOn(api, 'createProfile'); vi.spyOn(api, 'startRun');
});
describe('independent recovery lifecycle boundaries', () => {
 it('new case during profile detail waits releases loading and retains the blank intent', async () => {
  let answer!: (p: StoredProfile) => void;
  vi.mocked(api.getProfile).mockReturnValue(new Promise(resolve => { answer = resolve; }));
  render(<StoreProvider><Probe /></StoreProvider>);
  await waitFor(() => expect(api.getProfile).toHaveBeenCalledWith(profile.id));
  expect(state().loading).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'New case during recovery' }));
  await act(async () => { answer(profile); });
  await waitFor(() => expect(state().hydrated).toBe(true));
  expect(state().profile).toBeNull(); expect(state().run).toBeNull(); expect(state().results).toEqual([]);
  const pointerKey = Object.keys(sessionStorage).find(k => k.includes('activeProfile'))!;
  expect(sessionStorage.getItem(pointerKey)).toMatch(/^local:/);
  expect(api.results).not.toHaveBeenCalled(); expect(api.createProfile).not.toHaveBeenCalled(); expect(api.startRun).not.toHaveBeenCalled();
  expect(state().loading).toBe(false);
 });
 it('a delayed orphan run pointer cannot replace the authorized recovered latest run', async () => {
  let answer!: (r: RunView) => void;
  writePointer('run', 'peer-orphan-run');
  vi.spyOn(api, 'getRun').mockReturnValue(new Promise(resolve => { answer = resolve; }));
  render(<StoreProvider><Probe /></StoreProvider>);
  await waitFor(() => expect(state().run).toBe(run.id));
  expect(state().hydrated).toBe(false);
  await act(async () => { answer({ ...run, id: 'peer-orphan-run', profile_id: 'other-owned-case' }); });
  await waitFor(() => expect(state().hydrated).toBe(true));
  expect(state().profile).toBe(profile.id); expect(state().run).toBe(run.id); expect(state().results).toEqual(['peer-result']);
  expect(api.results).toHaveBeenCalledTimes(1); expect(api.results).toHaveBeenCalledWith(run.id);
 });
 it('owner change during fallback detail cannot publish old profile/run/results', async () => {
  let answer!: (p: StoredProfile) => void;
  vi.mocked(api.getProfile).mockReturnValue(new Promise(resolve => { answer = resolve; }));
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
  render(<StoreProvider><Probe /></StoreProvider>);
  await waitFor(() => expect(api.getProfile).toHaveBeenCalledWith(profile.id));
  owner('peer-B'); await act(async () => { answer(profile); });
  await waitFor(() => expect(state().hydrated).toBe(true));
  expect(state().profile).toBeNull(); expect(state().run).toBeNull(); expect(state().results).toEqual([]);
  expect(api.results).not.toHaveBeenCalled(); expect(api.createProfile).not.toHaveBeenCalled(); expect(api.startRun).not.toHaveBeenCalled();
 });
});

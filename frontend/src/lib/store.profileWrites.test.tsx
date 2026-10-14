import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError } from '@/api/client';
import { DEFAULT_PROFILE } from './defaultProfile';
import { readProfileCommands } from './profileCommands';
import { StoreProvider, useStore, toDraft } from './store';
import { deferred } from '@/screens/preparationFixtures';
import type { ProfileCommandHeaders, StoredProfile } from '@/types';
const original={...structuredClone(DEFAULT_PROFILE),id:'own-profile',revision:1,created_at:'2026-10-14T00:00:00Z',updated_at:'2026-10-14T00:00:00Z'} as StoredProfile;
function ack(body:unknown, command:ProfileCommandHeaders,kind:'create'|'update'|'persisted_rerank'='update'):StoredProfile {
 return {...original,...body as object,revision:(command.expected_revision??0)+1,write_receipt:{command_id:command.command_id,kind,profile_id:original.id,expected_revision:command.expected_revision??null,accepted_revision:(command.expected_revision??0)+1}};
}
function Probe(){const s=useStore();return <><output data-testid="draft">{JSON.stringify(s.profileDraft)}</output><output data-testid="stored">{JSON.stringify(s.savedProfile)}</output><output data-testid="recovery">{s.profileRecovery?.message??''}</output>
<button onClick={()=>s.setProfileDraft(d=>({...d,display_name:'First edits'}))}>edit</button><button onClick={()=>s.setProfileDraft(d=>({...d,display_name:'Newer typing'}))}>type more</button>
<button onClick={()=>void s.saveProfile().catch(()=>{})}>save</button><button onClick={()=>void s.startRun(true)}>start</button><button onClick={()=>void s.retryProfileWrite()}>retry</button>
<button onClick={()=>s.applyProfileComparison({'["display_name"]':'local'},JSON.stringify(s.profileDraft))}>compare</button><button onClick={s.newCase}>new</button></>;}
beforeEach(()=>{localStorage.clear();sessionStorage.clear();vi.restoreAllMocks();sessionStorage.setItem('ashyq.activeProfile',original.id);vi.spyOn(api,'capabilities').mockResolvedValue({} as never);vi.spyOn(api,'cases').mockResolvedValue([]);vi.spyOn(api,'getProfile').mockResolvedValue(original);vi.spyOn(api,'listRuns').mockResolvedValue([]);vi.spyOn(api,'validateProfile').mockResolvedValue({gaps:[],can_proceed:true,blocking_count:0,summary:'ok'});vi.spyOn(api,'startRun').mockResolvedValue({id:'run',profile_id:original.id,stage:'completed'} as never);vi.spyOn(api,'results').mockResolvedValue([]);vi.spyOn(api,'summary').mockResolvedValue({} as never);vi.spyOn(api,'shortlist').mockResolvedValue({} as never);});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function mount(){render(<StoreProvider><Probe/></StoreProvider>);await waitFor(()=>expect(screen.getByTestId('stored')).toHaveTextContent(original.id));}
it('strips all server metadata from editable data and validation',async()=>{
 expect(toDraft({...original,write_receipt:null})).not.toHaveProperty('revision');expect(toDraft(original)).not.toHaveProperty('write_receipt');
 await mount();await waitFor(()=>expect(api.validateProfile).toHaveBeenCalled());expect(vi.mocked(api.validateProfile).mock.lastCall![0]).not.toHaveProperty('revision');
});
it('publishes the accepted revision before optional metadata fails and preserves newer typing',async()=>{
 const pending=deferred<StoredProfile>();vi.spyOn(api,'updateProfile').mockReturnValue(pending.promise);await mount();fireEvent.click(screen.getByText('edit'));fireEvent.click(screen.getByText('save'));await waitFor(()=>expect(api.updateProfile).toHaveBeenCalledOnce());
 const [,body,command]=vi.mocked(api.updateProfile).mock.calls[0]!;expect(command.expected_revision).toBe(1);expect(body).not.toHaveProperty('revision');
 fireEvent.click(screen.getByText('type more'));vi.mocked(api.cases).mockRejectedValue(new ApiError(500,'Metadata failed'));await act(async()=>pending.resolve(ack(body,command)));
 expect(screen.getByTestId('stored')).toHaveTextContent('"revision":2');expect(screen.getByTestId('draft')).toHaveTextContent('Newer typing');expect(readProfileCommands()[0]!.status).toBe('accepted');
});
it('keeps the original unknown command across reload and explicitly replays it',async()=>{
 vi.spyOn(api,'updateProfile').mockRejectedValue(new TypeError('Lost committed ACK'));await mount();fireEvent.click(screen.getByText('edit'));fireEvent.click(screen.getByText('save'));await waitFor(()=>expect(screen.getByTestId('recovery')).toHaveTextContent('response was lost'));
 const oldCall=vi.mocked(api.updateProfile).mock.calls[0]!;cleanup();await mount();expect(screen.getByTestId('recovery')).toHaveTextContent('original');
 vi.mocked(api.updateProfile).mockImplementation(async(_id,body,command)=>ack(body,command));fireEvent.click(screen.getByText('retry'));await waitFor(()=>expect(screen.getByTestId('stored')).toHaveTextContent('"revision":2'));
 expect(vi.mocked(api.updateProfile).mock.calls[1]!).toEqual(oldCall);expect(readProfileCommands()[0]!.status).toBe('accepted');
});
it('blocks research on conflict and preserves typing during the current-profile GET',async()=>{
 vi.spyOn(api,'updateProfile').mockRejectedValue(new ApiError(409,'Changed','profile_revision_conflict'));await mount();const pending=deferred<StoredProfile>();vi.mocked(api.getProfile).mockReturnValue(pending.promise);fireEvent.click(screen.getByText('edit'));fireEvent.click(screen.getByText('start'));await waitFor(()=>expect(api.getProfile).toHaveBeenCalledTimes(2));fireEvent.click(screen.getByText('type more'));
 const server={...original,revision:2,display_name:'Server changed'};await act(async()=>pending.resolve(server));expect(api.startRun).not.toHaveBeenCalled();expect(screen.getByTestId('draft')).toHaveTextContent('Newer typing');
 fireEvent.click(screen.getByText('compare'));expect(api.updateProfile).toHaveBeenCalledOnce();expect(readProfileCommands()[0]!.status).toBe('conflict');expect(readProfileCommands()[0]!.reviewed_conflict).toBe(true);
 vi.mocked(api.updateProfile).mockImplementation(async(_id,body,command)=>ack(body,command));fireEvent.click(screen.getByText('save'));await waitFor(()=>expect(api.updateProfile).toHaveBeenCalledTimes(2));
 const command=vi.mocked(api.updateProfile).mock.calls[1]![2]!;expect(command.expected_revision).toBe(2);expect(command.command_id).not.toBe(vi.mocked(api.updateProfile).mock.calls[0]![2]!.command_id);
});
it('does not dispatch at all when recovery storage is denied',async()=>{
 const update=vi.spyOn(api,'updateProfile');await mount();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Denied');});fireEvent.click(screen.getByText('save'));await act(async()=>{});expect(update).not.toHaveBeenCalled();expect(api.startRun).not.toHaveBeenCalled();
});

import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError } from '@/api/client';
import { DEFAULT_PROFILE } from './defaultProfile';
import { readProfileCommands } from './profileCommands';
import { readDraftEnvelope } from './caseDrafts';
import { bindApplicantOwner } from './applicantStorage';
import { StoreProvider, useStore } from './store';
import { deferred } from '@/screens/preparationFixtures';
import type { ProfileCommandHeaders, StoredProfile } from '@/types';
const original={...structuredClone(DEFAULT_PROFILE),id:'own-profile',revision:1,created_at:'2026-10-14T00:00:00Z',updated_at:'2026-10-14T00:00:00Z'} as StoredProfile;
function ack(body:unknown, command:ProfileCommandHeaders,kind:'create'|'update'|'persisted_rerank'='update'):StoredProfile {
 return {...original,...body as object,revision:(command.expected_revision??0)+1,write_receipt:{command_id:command.command_id,kind,profile_id:original.id,expected_revision:command.expected_revision??null,accepted_revision:(command.expected_revision??0)+1}};
}
function Probe(){const s=useStore();return <><output data-testid="draft">{JSON.stringify(s.profileDraft)}</output><output data-testid="stored">{JSON.stringify(s.savedProfile)}</output><output data-testid="recovery">{s.profileRecovery?.message??''}</output>
<button onClick={()=>s.setProfileDraft(d=>({...d,display_name:'First edits'}))}>edit</button><button onClick={()=>s.setProfileDraft(d=>({...d,display_name:'Newer typing'}))}>type more</button>
<button onClick={()=>void s.saveProfile().catch(()=>{})}>save</button><button onClick={()=>void s.startRun(true)}>start</button><button onClick={()=>void s.retryProfileWrite()}>retry</button>
<button onClick={()=>void s.compareSavedProfile()}>read comparison</button><button onClick={()=>s.clearConfirmedProfileWrites()}>clear confirmed</button><button onClick={()=>s.applyProfileComparison({'["display_name"]':'local'},JSON.stringify(s.profileDraft))}>compare</button><button onClick={s.newCase}>new</button><button onClick={()=>void s.switchCase("other-profile")}>switch</button><button onClick={()=>void s.switchCase(original.id)}>back</button><button onClick={()=>void s.deleteEverything()}>delete</button><output data-testid="audit-error">{s.error}</output></>;}
beforeEach(()=>{localStorage.clear();sessionStorage.clear();vi.restoreAllMocks();sessionStorage.setItem('ashyq.activeProfile',original.id);vi.spyOn(api,'capabilities').mockResolvedValue({} as never);vi.spyOn(api,'cases').mockResolvedValue([]);vi.spyOn(api,'getProfile').mockResolvedValue(original);vi.spyOn(api,'listRuns').mockResolvedValue([]);vi.spyOn(api,'validateProfile').mockResolvedValue({gaps:[],can_proceed:true,blocking_count:0,summary:'ok'});vi.spyOn(api,'startRun').mockResolvedValue({id:'run',profile_id:original.id,stage:'completed'} as never);vi.spyOn(api,'results').mockResolvedValue([]);vi.spyOn(api,'summary').mockResolvedValue({} as never);vi.spyOn(api,'shortlist').mockResolvedValue({} as never);});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function mount(id=original.id){render(<StoreProvider><Probe/></StoreProvider>);await waitFor(()=>expect(screen.getByTestId('stored')).toHaveTextContent(id));}
// All API calls are local mocks; these controls exercise React lifecycle ordering.
beforeEach(()=>vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('Unexpected network');})));
afterEach(()=>{expect(fetch).not.toHaveBeenCalled();vi.unstubAllGlobals();});
for (const create of [false,true]) for (const replay of [false,true]) for (const durableBeforeAck of [false,true]) {
 it(`retains ${create?'create':'update'} newer text through ${replay?'replay':'normal'} ACK/reload, pre-ACK autosave=${durableBeforeAck}`,async()=>{
  await mount();if(create)fireEvent.click(screen.getByText('new'));
  const pending=deferred<StoredProfile>();
  const method=create?'createProfile':'updateProfile';
  const spy=vi.spyOn(api,method);
  if(replay)spy.mockRejectedValueOnce(new ApiError(0,'Lost ACK'));
  else spy.mockReturnValueOnce(pending.promise);
  fireEvent.click(screen.getByText('edit'));fireEvent.click(screen.getByText('save'));
  await waitFor(()=>expect(spy).toHaveBeenCalledOnce());
  const entry=readProfileCommands()[0]!;
  const body=entry.body, command=entry.command;
  if(replay){await waitFor(()=>expect(screen.getByTestId('recovery')).toHaveTextContent('response was lost'));spy.mockReturnValueOnce(pending.promise);fireEvent.click(screen.getByText('retry'));await waitFor(()=>expect(spy).toHaveBeenCalledTimes(2));}
  fireEvent.click(screen.getByText('type more'));
  if(durableBeforeAck)await waitFor(()=>expect(readDraftEnvelope(entry.case_key)?.draft.display_name).toBe('Newer typing'),{timeout:2000});
  const saved={...ack(body,command,create?'create':'update'),...(create?{id:'created-profile',write_receipt:{...ack(body,command,'create').write_receipt!,profile_id:'created-profile'}}:{})};
  await act(async()=>pending.resolve(saved));
  expect(readProfileCommands()[0]!.status).toBe('accepted');expect(readProfileCommands()[0]!.reconciliation_required).toBe(false);
  const envelope=readDraftEnvelope(saved.id)!;expect(envelope.draft.display_name).toBe('Newer typing');expect(envelope.base_revision).toBe(saved.revision);expect(envelope.base_draft?.display_name).toBe('First edits');
  if(create)expect(readDraftEnvelope(entry.case_key)).toBeNull();
  cleanup();vi.mocked(api.getProfile).mockResolvedValue(saved);await mount(saved.id);expect(screen.getByTestId('draft')).toHaveTextContent('Newer typing');
  expect(spy).toHaveBeenCalledTimes(replay?2:1);if(replay)expect(spy.mock.calls[1]).toEqual(spy.mock.calls[0]);
 });
}
it('retires clean captured text and adopts server normalization through immediate reload',async()=>{
 vi.spyOn(api,'updateProfile').mockImplementation(async(_id,body,command)=>({...ack(body,command),display_name:'Normalized'}));await mount();fireEvent.click(screen.getByText('edit'));fireEvent.click(screen.getByText('save'));
 await waitFor(()=>expect(screen.getByTestId('draft')).toHaveTextContent('Normalized'));expect(readDraftEnvelope(original.id)).toBeNull();
 const saved=await vi.mocked(api.updateProfile).mock.results[0]!.value;cleanup();vi.mocked(api.getProfile).mockResolvedValue(saved);await mount();expect(screen.getByTestId('draft')).toHaveTextContent('Normalized');
});
it.each(['local','session'])('keeps accepted ACK recoverable when %s storage refuses retirement',async(kind)=>{
 const pending=deferred<StoredProfile>();vi.spyOn(api,'updateProfile').mockReturnValue(pending.promise);await mount();fireEvent.click(screen.getByText('edit'));fireEvent.click(screen.getByText('save'));await waitFor(()=>expect(api.updateProfile).toHaveBeenCalledOnce());
 const [,body,command]=vi.mocked(api.updateProfile).mock.calls[0]!;fireEvent.click(screen.getByText('type more'));
 const originalSet=Storage.prototype.setItem;
 const refusal=vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(this:Storage,key,value){if(this===(kind==='local'?localStorage:sessionStorage))throw new Error('Synthetic storage refusal');return originalSet.call(this,key,value);});
 const saved=ack(body,command);await act(async()=>pending.resolve(saved));expect(screen.getByTestId('stored')).toHaveTextContent('First edits');expect(screen.getByTestId('draft')).toHaveTextContent('Newer typing');
 expect(readProfileCommands()[0]!.status).toBe(kind==='local'?'accepted':'pending');
 if(kind==='local'){expect(readProfileCommands()[0]!.reconciliation_required).toBe(true);fireEvent.click(screen.getByText('clear confirmed'));expect(readProfileCommands()).toHaveLength(1);}
 expect(screen.getByTestId('recovery')).not.toHaveTextContent('response was lost');
 refusal.mockRestore();cleanup();vi.mocked(api.getProfile).mockResolvedValue(saved);await mount(saved.id);expect(screen.getByTestId('draft')).toHaveTextContent('Newer typing');fireEvent.click(screen.getByText('start'));await act(async()=>{});expect(api.startRun).not.toHaveBeenCalled();expect(api.updateProfile).toHaveBeenCalledOnce();
});
it('persists the departed case draft on its own ACK without copying the new case into it',async()=>{
 const pending=deferred<StoredProfile>();vi.spyOn(api,'updateProfile').mockReturnValue(pending.promise);await mount();fireEvent.click(screen.getByText('edit'));fireEvent.click(screen.getByText('save'));await waitFor(()=>expect(api.updateProfile).toHaveBeenCalledOnce());const [,body,command]=vi.mocked(api.updateProfile).mock.calls[0]!;
 fireEvent.click(screen.getByText('type more'));fireEvent.click(screen.getByText('new'));const saved=ack(body,command);await act(async()=>pending.resolve(saved));expect(screen.getByTestId('stored')).toHaveTextContent('null');expect(screen.getByTestId('draft')).not.toHaveTextContent('Newer typing');
 vi.mocked(api.getProfile).mockResolvedValue(saved);fireEvent.click(screen.getByText('back'));await waitFor(()=>expect(screen.getByTestId('draft')).toHaveTextContent('Newer typing'));
});
for(const action of ['new','switch','roundtrip','owner','unchanged'])for(const rejects of [false,true]){
 it(`fences research after optional metadata ${rejects?'failure':'success'}: ${action}`,async()=>{
  vi.spyOn(api,'updateProfile').mockImplementation(async(_id,body,command)=>ack(body,command));await mount();
  const metadata=deferred<never[]>();vi.mocked(api.cases).mockReturnValue(metadata.promise);fireEvent.click(screen.getByText('start'));await waitFor(()=>expect(api.cases).toHaveBeenCalledTimes(2));
  if(action==='new')fireEvent.click(screen.getByText('new'));
  if(action==='switch'||action==='roundtrip'){vi.mocked(api.getProfile).mockImplementation(async id=>({...original,id}));fireEvent.click(screen.getByText('switch'));await waitFor(()=>expect(screen.getByTestId('stored')).toHaveTextContent('other-profile'));if(action==='roundtrip'){fireEvent.click(screen.getByText('back'));await waitFor(()=>expect(screen.getByTestId('stored')).toHaveTextContent(original.id));}}
  if(action==='owner')bindApplicantOwner({enabled:false,authenticated:false,registration_enabled:false,principal:null});
  await act(async()=>rejects?metadata.reject(new ApiError(500,'Metadata failed')):metadata.resolve([]));
  expect(api.startRun).toHaveBeenCalledTimes(action==='unchanged'?1:0);
 });
}

it('preserves the submitted draft when a create replay returns a newer server version',async()=>{
 await mount();fireEvent.click(screen.getByText('new'));let saved!:StoredProfile;
 vi.spyOn(api,'createProfile').mockImplementation(async(body,command)=>{saved={...ack(body,command!,'create'),revision:3,display_name:'Later server edit'};return saved;});
 fireEvent.click(screen.getByText('edit'));fireEvent.click(screen.getByText('save'));await waitFor(()=>expect(screen.getByTestId('recovery')).toHaveTextContent('original command was accepted'));
 cleanup();vi.mocked(api.getProfile).mockResolvedValue(saved);await mount();expect(screen.getByTestId('draft')).toHaveTextContent('First edits');expect(readProfileCommands()[0]!.reconciliation_required).toBe(true);
});
it('does not join an old conflicting run after switching case while its POST was in flight',async()=>{
 vi.spyOn(api,'updateProfile').mockImplementation(async(_id,body,command)=>ack(body,command));await mount();
 const starting=deferred<never>();vi.mocked(api.startRun).mockReturnValue(starting.promise);const join=vi.spyOn(api,'getRun');
 fireEvent.click(screen.getByText('start'));await waitFor(()=>expect(api.startRun).toHaveBeenCalledOnce());fireEvent.click(screen.getByText('new'));
 await act(async()=>starting.reject(new ApiError(409,'run 0123456789abcdef0123456789abcdef')));expect(join).not.toHaveBeenCalled();expect(screen.getByTestId('stored')).toHaveTextContent('null');
});

it.each(['local','session'])('retains first create recovery when %s storage refuses its accepted ACK',async(kind)=>{
 await mount();fireEvent.click(screen.getByText('new'));
 const pending=deferred<StoredProfile>();const create=vi.spyOn(api,'createProfile').mockReturnValue(pending.promise);
 const update=vi.spyOn(api,'updateProfile').mockRejectedValue(new ApiError(500,'Should never dispatch replacement'));
 fireEvent.click(screen.getByText('edit'));fireEvent.click(screen.getByText('save'));await waitFor(()=>expect(create).toHaveBeenCalledOnce());
 const entry=readProfileCommands()[0]!;fireEvent.click(screen.getByText('type more'));
 const originalSet=Storage.prototype.setItem;const refusal=vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(this:Storage,key,value){if(this===(kind==='local'?localStorage:sessionStorage))throw new Error('Synthetic create retirement refusal');return originalSet.call(this,key,value);});
 const saved={...ack(entry.body,entry.command,'create'),id:'created-profile',write_receipt:{...ack(entry.body,entry.command,'create').write_receipt!,profile_id:'created-profile'}};
 await act(async()=>pending.resolve(saved));
 expect(screen.getByTestId('draft')).toHaveTextContent('Newer typing');expect(screen.getByTestId('recovery')).not.toBeEmptyDOMElement();
 fireEvent.click(screen.getByText('start'));await act(async()=>{});expect(update).not.toHaveBeenCalled();expect(create).toHaveBeenCalledOnce();expect(api.startRun).not.toHaveBeenCalled();
 refusal.mockRestore();cleanup();vi.mocked(api.getProfile).mockResolvedValue(saved);render(<StoreProvider><Probe/></StoreProvider>);await waitFor(()=>expect(screen.getByTestId('draft')).toHaveTextContent('Newer typing'));
 expect(readProfileCommands()[0]!.command.command_id).toBe(entry.command.command_id);
});

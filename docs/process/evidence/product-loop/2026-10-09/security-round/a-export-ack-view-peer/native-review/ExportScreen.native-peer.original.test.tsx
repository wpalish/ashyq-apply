import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ExportScreen } from './ExportScreen';
import { StoreProvider, useStore } from '@/lib/store';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import { api } from '@/api/client';
import { bindApplicantOwner } from '@/lib/applicantStorage';
import { writePointer } from '@/lib/caseDrafts';
import type { StoredProfile } from '@/types';

const a = { ...structuredClone(DEFAULT_PROFILE), id: 'peer-case-A', display_name: 'Native peer A',
 created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-02T00:00:00Z' } as unknown as StoredProfile;
const b = { ...a, id: 'peer-case-B', display_name: 'Native peer B' };
let captured: ReturnType<typeof useStore>;
function State() { captured=useStore();return <output data-testid="native-state">{JSON.stringify({ saved:captured.savedProfile?.id??null, run:captured.run?.id??null })}</output>; }
function mount() {return render(<StoreProvider><State /><ExportScreen /></StoreProvider>);}
function deferred<T>() {let answer!: (value:T)=>void;const promise=new Promise<T>(resolve=>{answer=resolve;});return {promise,answer};}
beforeEach(()=>{
 localStorage.clear();sessionStorage.clear();vi.restoreAllMocks();
 bindApplicantOwner({enabled:true,authenticated:true,principal:{user_id:'peer-owner',organization_id:'peer-org',local_development:false}} as never);
 writePointer('profile',a.id);
 vi.spyOn(api,'capabilities').mockResolvedValue({demo_mode:false,guarantees:[],limits:[],currency:{rate_date:'2026-10-01',rate_source:'synthetic'}} as never);
 vi.spyOn(api,'cases').mockResolvedValue([]);
 vi.spyOn(api,'getProfile').mockImplementation(async id=>id===a.id?a:b);
 vi.spyOn(api,'listRuns').mockResolvedValue([]);
 vi.spyOn(api,'validateProfile').mockResolvedValue({gaps:[],can_proceed:true,blocking_count:0,summary:'ok'});
 vi.spyOn(api,'shortlist').mockResolvedValue({} as never);
 vi.spyOn(api,'exportProfile').mockResolvedValue({marker:'first-owned-JSON'});
 vi.spyOn(api,'deleteProfile').mockResolvedValue(undefined);
 Object.defineProperty(URL,'createObjectURL',{configurable:true,value:vi.fn(()=> 'blob:peer')});
 Object.defineProperty(URL,'revokeObjectURL',{configurable:true,value:vi.fn()});
 vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>undefined);
});
async function show() {fireEvent.click(await screen.findByTestId('export-profile'));await screen.findByLabelText('Stored profile data');}
function requestDelete() {fireEvent.change(screen.getByTestId('delete-confirm'),{target:{value:'DELETE'}});fireEvent.click(screen.getByTestId('delete-everything'));}
describe('independent native Store delete/export integration',()=>{
 it('clears an opened JSON after real Store acknowledgment and refuses late Show/download copies',async()=>{
  const del=deferred<void>();vi.mocked(api.deleteProfile).mockReturnValue(del.promise);
  mount();await show();expect(captured.savedProfile?.id).toBe(a.id);
  const lateShow=deferred<Record<string,unknown>>();const lateDownload=deferred<Record<string,unknown>>();
  vi.mocked(api.exportProfile).mockReturnValueOnce(lateShow.promise).mockReturnValueOnce(lateDownload.promise);
  fireEvent.click(screen.getByTestId('export-profile'));fireEvent.click(screen.getByTestId('download-profile'));requestDelete();
  await waitFor(()=>expect(api.deleteProfile).toHaveBeenCalledWith(a.id));
  expect(screen.getByLabelText('Stored profile data')).toHaveTextContent('first-owned-JSON');
  expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
  await act(async()=>{del.answer();});
  expect(await screen.findByText(/^Deleted\./)).toBeInTheDocument();
  expect(captured.savedProfile).toBeNull();expect(captured.run).toBeNull();
  expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
  await act(async()=>{lateShow.answer({marker:'late-deleted-private-copy'});lateDownload.answer({marker:'late-deleted-private-download'});});
  expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
  expect(URL.createObjectURL).not.toHaveBeenCalled();expect(HTMLAnchorElement.prototype.click).not.toHaveBeenCalled();
 });
 it('keeps selected case B when native Store rejects a superseded deletion and late A export',async()=>{
  const del=deferred<void>();vi.mocked(api.deleteProfile).mockReturnValue(del.promise);
  mount();await show();const oldExport=deferred<Record<string,unknown>>();vi.mocked(api.exportProfile).mockReturnValueOnce(oldExport.promise);
  fireEvent.click(screen.getByTestId('export-profile'));requestDelete();await waitFor(()=>expect(api.deleteProfile).toHaveBeenCalledWith(a.id));
  await act(async()=>{await captured.switchCase(b.id);});
  expect(captured.savedProfile?.id).toBe(b.id);
  expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
  await act(async()=>{del.answer();oldExport.answer({marker:'late-A'});});
  expect(captured.savedProfile?.id).toBe(b.id);expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
  vi.mocked(api.exportProfile).mockResolvedValue({marker:'current-B'});await show();
  expect(screen.getByLabelText('Stored profile data')).toHaveTextContent('current-B');expect(screen.getByLabelText('Stored profile data')).not.toHaveTextContent('late-A');
  expect(api.exportProfile).toHaveBeenLastCalledWith(b.id);
 });
});

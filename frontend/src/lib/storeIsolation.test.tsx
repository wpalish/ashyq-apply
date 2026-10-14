import { profileAck } from '@/lib/profileWriteFixtures';
import { webcrypto } from 'node:crypto';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ApiError, api } from '@/api/client';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import { StoreProvider, useStore, type Store } from '@/lib/store';
import { journalAdmissionsAction, openAdmissionsActionsRecovery, readAdmissionsActionsRecovery } from '@/lib/admissionsActionsRecovery';
import { sharedRouteRecoveryBinding } from '@/lib/sharedRouteRecovery';
import type { ProgramResult, RunView } from '@/types';
const profile = (id: string) => ({ ...structuredClone(DEFAULT_PROFILE), revision:1, id, display_name: `Saved ${id}`, created_at: '2026-01-01', updated_at: '2026-01-01' });
const run = (id: string) => ({ id, stage: 'failed', job_running: false, job_status: 'failed' }) as unknown as RunView;
const row = (id: string) => ({ id, claims: [], user_notes: '' }) as unknown as ProgramResult;
let latestStore: Store | null = null;
function store(): Store { if (latestStore === null) throw new Error('Synthetic store not mounted'); return latestStore; }
function Probe() {
 const s=useStore(); latestStore=s; return <div>
 <span data-testid="case">{s.savedProfile?.id ?? 'none'}</span><span data-testid="run">{s.run?.id ?? 'none'}</span><span data-testid="rows">{s.results.map(r=>r.id).join(',')}</span><span data-testid="total">{s.summary?.total ?? 0}</span><span data-testid="error">{s.error ?? ''}</span><span data-testid="draft">{String(s.profileDraft.display_name)}</span>
 <button onClick={()=>void s.switchCase('A')}>A</button><button onClick={()=>void s.switchCase('B')}>B</button><button onClick={()=>void s.startRun(true)}>start</button><button onClick={()=>void s.refreshResults()}>refresh</button><button onClick={()=>void s.rerank({priorities:['funding']})}>rerank</button><button onClick={()=>void s.cancelRun()}>cancel</button><button onClick={()=>void s.retryRun()}>retry</button><button onClick={()=>void s.recheckNow()}>recheck</button><button onClick={()=>void s.collectDocuments()}>collect</button><button onClick={()=>void s.decide('a-row','approved','','')}>decide</button><button onClick={()=>void s.saveNotes('a-row','Typed notes')}>notes</button><button onClick={()=>void s.deleteEverything()}>delete</button><button onClick={()=>s.setProfileDraft(d=>({...d,display_name:'Recovered fresh edit'}))}>edit</button>
 </div>;
}
async function flush() { await act(async()=>{for(let i=0;i<15;i++)await Promise.resolve();}); }
function deferred<T>() { let resolve!:(v:T)=>void;let reject!:(e:unknown)=>void;const promise=new Promise<T>((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject}; }
beforeEach(()=>{
 latestStore=null;vi.stubGlobal('crypto',webcrypto);
 localStorage.clear();sessionStorage.clear();sessionStorage.setItem('ashyq.activeProfile','A');sessionStorage.setItem('ashyq.activeRun','a');
 localStorage.setItem('ashyq.applicantOwner','demo');sessionStorage.setItem('ashyq.applicantOwner','demo');
 vi.spyOn(api,'capabilities').mockResolvedValue({} as never);vi.spyOn(api,'cases').mockResolvedValue([]);vi.spyOn(api,'validateProfile').mockResolvedValue({gaps:[],can_proceed:true,blocking_count:0,summary:'ok'});vi.spyOn(api,'shortlist').mockResolvedValue({} as never);
 vi.spyOn(api,'getProfile').mockImplementation(async id=>profile(id) as never);vi.spyOn(api,'getRun').mockResolvedValue(run('a'));vi.spyOn(api,'listRuns').mockResolvedValue([run('b')]);vi.spyOn(api,'results').mockImplementation(async id=>[row(`${id}-row`)]);vi.spyOn(api,'summary').mockImplementation(async id=>({total:id==='b'?2:1}) as never);
});
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();vi.unstubAllGlobals();});

it.each([['cancel','cancelRun'],['retry','retryRun'],['recheck','recheckNow'],['collect','collectDocuments']] as const)('a late %s response cannot restore run A under case B', async(button,method)=>{
 const old=deferred<RunView>();vi.spyOn(api,method).mockReturnValue(old.promise);
 render(<StoreProvider><Probe/></StoreProvider>);await flush();fireEvent.click(screen.getByText(button));await flush();fireEvent.click(screen.getByText('B'));await flush();old.resolve(run('a'));await flush();
 expect(screen.getByTestId('case')).toHaveTextContent('B');expect(screen.getByTestId('run')).toHaveTextContent('b');
});
it('a late rerank for A cannot overwrite B results', async()=>{
 const old=deferred<Awaited<ReturnType<typeof api.rerank>>>();vi.spyOn(api,'rerank').mockReturnValue(old.promise);render(<StoreProvider><Probe/></StoreProvider>);await flush();fireEvent.click(screen.getByText('rerank'));await flush();fireEvent.click(screen.getByText('B'));await flush();old.resolve({rows:1,gamma:1,weights_source:'profile'});await flush();expect(screen.getByTestId('rows')).toHaveTextContent('b-row');
});
it('a late decision summary for A cannot overwrite B summary', async()=>{
 const old=deferred<never>();vi.spyOn(api,'decide').mockResolvedValue(row('a-row'));vi.mocked(api.summary).mockImplementation(id=>id==='a'?old.promise:Promise.resolve({total:2}) as never);
 render(<StoreProvider><Probe/></StoreProvider>);await flush();fireEvent.click(screen.getByText('decide'));await flush();fireEvent.click(screen.getByText('B'));await flush();old.resolve({total:1} as never);await flush();expect(screen.getByTestId('total')).toHaveTextContent('2');
});
it('a late notes failure for A does not raise an error on B',async()=>{
 const old=deferred<ProgramResult>();vi.spyOn(api,'saveNotes').mockReturnValue(old.promise);render(<StoreProvider><Probe/></StoreProvider>);await flush();fireEvent.click(screen.getByText('notes'));await flush();fireEvent.click(screen.getByText('B'));await flush();old.reject(new ApiError(500,'Old A notes failure'));await flush();expect(screen.getByTestId('error')).toHaveTextContent('');
});
it('a late deletion response for A does not clear B',async()=>{
 const journalA=sharedRouteRecoveryBinding(undefined,'A')!; const journalB=sharedRouteRecoveryBinding(undefined,'B')!;
 sessionStorage.setItem(journalA.key,'A unresolved local command');sessionStorage.setItem(journalB.key,'B newer local draft');
 const old=deferred<void>();vi.spyOn(api,'deleteProfile').mockReturnValue(old.promise);render(<StoreProvider><Probe/></StoreProvider>);await flush();fireEvent.click(screen.getByText('delete'));await flush();fireEvent.click(screen.getByText('B'));await flush();old.resolve();await flush();expect(screen.getByTestId('case')).toHaveTextContent('B');expect(screen.getByTestId('run')).toHaveTextContent('b');
 expect(sessionStorage.getItem(journalA.key)).toBeNull();expect(sessionStorage.getItem(journalB.key)).toBe('B newer local draft');
});
it('starting a new run already invalidates a refresh from its predecessor',async()=>{
 const old=deferred<ProgramResult[]>();vi.spyOn(api,'updateProfile').mockImplementation(async(_id,_body,command)=>profileAck(profile('A'),command));vi.spyOn(api,'startRun').mockResolvedValue(run('new-run'));
 render(<StoreProvider><Probe/></StoreProvider>);await flush();vi.mocked(api.results).mockReturnValue(old.promise);fireEvent.click(screen.getByText('refresh'));await flush();fireEvent.click(screen.getByText('start'));await flush();old.resolve([row('old-run row')]);await flush();expect(screen.getByTestId('run')).toHaveTextContent('new-run');expect(screen.getByTestId('rows')).toHaveTextContent('');
});
it('a refresh begun before reranking cannot overwrite the new same-run order',async()=>{
 const old=deferred<ProgramResult[]>();vi.spyOn(api,'rerank').mockResolvedValue({rows:1,gamma:1,weights_source:'profile'});render(<StoreProvider><Probe/></StoreProvider>);await flush();vi.mocked(api.results).mockReturnValueOnce(old.promise).mockResolvedValueOnce([row('new ranked row')]);
 fireEvent.click(screen.getByText('refresh'));await flush();fireEvent.click(screen.getByText('rerank'));await flush();old.resolve([row('old order row')]);await flush();expect(screen.getByTestId('rows')).toHaveTextContent('new ranked row');
});
it('a 404 profile starts a locally persistable replacement without reviving the old pointer',async()=>{
 vi.useFakeTimers();vi.mocked(api.getProfile).mockRejectedValue(new ApiError(404,'Missing synthetic profile'));vi.mocked(api.getRun).mockRejectedValue(new ApiError(404,'Missing synthetic run'));
 const v=render(<StoreProvider><Probe/></StoreProvider>);await flush();expect(sessionStorage.getItem('ashyq.activeProfile')).toBeNull();fireEvent.click(screen.getByText('edit'));await act(async()=>{vi.advanceTimersByTime(600);});await flush();v.unmount();render(<StoreProvider><Probe/></StoreProvider>);await flush();expect(screen.getByTestId('draft')).toHaveTextContent('Recovered fresh edit');expect(screen.getByTestId('case')).toHaveTextContent('none');
});

it('a failed case deletion retains the exact own route journal and another case journal',async()=>{
 const journalA=sharedRouteRecoveryBinding(undefined,'A')!;const journalB=sharedRouteRecoveryBinding(undefined,'B')!;
 sessionStorage.setItem(journalA.key,'A original unresolved UUID/body');sessionStorage.setItem(journalB.key,'B local input');
 vi.spyOn(api,'deleteProfile').mockRejectedValue(new ApiError(403,'Synthetic delete refusal'));
 render(<StoreProvider><Probe/></StoreProvider>);await flush();fireEvent.click(screen.getByText('delete'));await flush();
 expect(screen.getByTestId('case')).toHaveTextContent('A');expect(screen.getByTestId('error')).toHaveTextContent('Synthetic delete refusal');
 expect(sessionStorage.getItem(journalA.key)).toBe('A original unresolved UUID/body');expect(sessionStorage.getItem(journalB.key)).toBe('B local input');
});


const g3UuidA = '11111111-2222-4333-8444-555555555555';
const g3UuidB = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee';
function g3Body(uuid: string) {
 return { schema_version: 'admissions-actions-v1' as const, kind: 'create_personal_task' as const,
 client_write_uuid: uuid, expected_revision: 0, application_id: null,
 personal: { label: 'Synthetic own task', responsible_actor: 'applicant' as const,
 details: { due: null, notes: 'Synthetic note' }, depends_on_task_ids: [] } };
}

it('invalidates the live G3 identity synchronously before waiting for a case switch', async()=>{
 const slow=deferred<ReturnType<typeof profile>>();
 vi.mocked(api.getProfile).mockImplementation(async id=>(id==='B'?await slow.promise:profile(id)) as never);
 render(<StoreProvider><Probe/></StoreProvider>);await flush();
 const original=store().currentAdmissionsCase();expect(original.profile_id).toBe('A');
 let pending:Promise<void>;
 act(()=>{pending=store().switchCase('B');expect(store().currentAdmissionsCase().profile_id).toBeNull();expect(store().currentAdmissionsCase().case_epoch).toBeGreaterThan(original.case_epoch);});
 await act(async()=>{slow.resolve(profile('B'));await pending;});
 expect(store().currentAdmissionsCase().profile_id).toBe('B');
});

it('a same case ID after A→B→A has a fresh G3 epoch, while the original journal remains', async()=>{
 render(<StoreProvider><Probe/></StoreProvider>);await flush();
 const start=store().currentAdmissionsCase();
 const opened=openAdmissionsActionsRecovery(undefined,'A',start.case_epoch,store().currentAdmissionsCase);
 if(!opened.ok)throw new Error(opened.reason);
 const journal=await journalAdmissionsAction(opened.value,g3Body(g3UuidA),1);expect(journal.ok).toBe(true);
 fireEvent.click(screen.getByText('B'));await flush();fireEvent.click(screen.getByText('A'));await flush();
 const current=store().currentAdmissionsCase();expect(current.profile_id).toBe('A');expect(current.case_epoch).toBeGreaterThan(start.case_epoch);
 expect(await readAdmissionsActionsRecovery(opened.value)).toEqual({ok:false,reason:'case'});
 const reopened=openAdmissionsActionsRecovery(undefined,'A',current.case_epoch,store().currentAdmissionsCase);
 if(!reopened.ok)throw new Error(reopened.reason);
 const restored=await readAdmissionsActionsRecovery(reopened.value);if(!restored.ok)throw new Error(restored.reason);
 expect(restored.value.entries[0]?.body).toEqual(g3Body(g3UuidA));
});

it('a late successful DELETE tombstones only captured G3 A and preserves B’s unresolved body', async()=>{
 const deletion=deferred<void>();vi.spyOn(api,'deleteProfile').mockReturnValue(deletion.promise);
 render(<StoreProvider><Probe/></StoreProvider>);await flush();
 const identity=store().currentAdmissionsCase();
 const a=openAdmissionsActionsRecovery(undefined,'A',identity.case_epoch,store().currentAdmissionsCase);if(!a.ok)throw new Error(a.reason);
 const b=openAdmissionsActionsRecovery(undefined,'B',1,()=>({scope:undefined,profile_id:'B',case_epoch:1}));if(!b.ok)throw new Error(b.reason);
 await journalAdmissionsAction(a.value,g3Body(g3UuidA),1);await journalAdmissionsAction(b.value,g3Body(g3UuidB),1);
 const bRaw=localStorage.getItem(`${b.value.family}intent.${g3UuidB}`);
 fireEvent.click(screen.getByText('delete'));await flush();fireEvent.click(screen.getByText('B'));await flush();
 await act(async()=>{deletion.resolve();});await flush();
 expect(screen.getByTestId('case')).toHaveTextContent('B');expect(store().currentAdmissionsCase().profile_id).toBe('B');
 expect(localStorage.getItem(`${a.value.family}intent.${g3UuidA}`)).toBeNull();
 expect(localStorage.getItem(`${b.value.family}intent.${g3UuidB}`)).toBe(bRaw);
 const deleted=openAdmissionsActionsRecovery(undefined,'A',99,()=>({scope:undefined,profile_id:'A',case_epoch:99}));expect(deleted).toEqual({ok:false,reason:'deleted'});
});

it('failed DELETE keeps its original G3 body and reactivates the own case with a fresh epoch', async()=>{
 vi.spyOn(api,'deleteProfile').mockRejectedValue(new ApiError(403,'Synthetic rejection'));
 render(<StoreProvider><Probe/></StoreProvider>);await flush();const old=store().currentAdmissionsCase();
 const a=openAdmissionsActionsRecovery(undefined,'A',old.case_epoch,store().currentAdmissionsCase);if(!a.ok)throw new Error(a.reason);
 await journalAdmissionsAction(a.value,g3Body(g3UuidA),1);const raw=localStorage.getItem(`${a.value.family}intent.${g3UuidA}`);
 fireEvent.click(screen.getByText('delete'));await flush();const current=store().currentAdmissionsCase();
 expect(current.profile_id).toBe('A');expect(current.case_epoch).toBeGreaterThan(old.case_epoch);
 expect(localStorage.getItem(`${a.value.family}intent.${g3UuidA}`)).toBe(raw);
 const reopened=openAdmissionsActionsRecovery(undefined,'A',current.case_epoch,store().currentAdmissionsCase);expect(reopened.ok).toBe(true);
});

it('the current G3 getter refuses a replaced owner and an unmounted Store', async()=>{
 const mounted=render(<StoreProvider><Probe/></StoreProvider>);await flush();const getter=store().currentAdmissionsCase;
 localStorage.setItem('ashyq.applicantOwner','auth:other');expect(getter().scope).toBeNull();expect(getter().profile_id).toBeNull();
 localStorage.setItem('ashyq.applicantOwner','demo');mounted.unmount();expect(getter().scope).toBeNull();expect(getter().profile_id).toBeNull();
});

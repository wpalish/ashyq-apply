import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { ApiError, api } from '@/api/client';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import { StoreProvider, useStore } from '@/lib/store';
import type { ProgramResult, RunView } from '@/types';
const profile = (id: string) => ({ ...structuredClone(DEFAULT_PROFILE), id, display_name: `Saved ${id}`, created_at: '2026-01-01', updated_at: '2026-01-01' });
const run = (id: string) => ({ id, stage: 'failed', job_running: false, job_status: 'failed' }) as unknown as RunView;
const row = (id: string) => ({ id, claims: [], user_notes: '' }) as unknown as ProgramResult;
function Probe() {
 const s=useStore(); return <div>
 <span data-testid="case">{s.savedProfile?.id ?? 'none'}</span><span data-testid="run">{s.run?.id ?? 'none'}</span><span data-testid="rows">{s.results.map(r=>r.id).join(',')}</span><span data-testid="total">{s.summary?.total ?? 0}</span><span data-testid="error">{s.error ?? ''}</span><span data-testid="draft">{String(s.profileDraft.display_name)}</span>
 <button onClick={()=>void s.switchCase('B')}>B</button><button onClick={()=>void s.startRun(true)}>start</button><button onClick={()=>void s.refreshResults()}>refresh</button><button onClick={()=>void s.rerank({priorities:['funding']})}>rerank</button><button onClick={()=>void s.cancelRun()}>cancel</button><button onClick={()=>void s.retryRun()}>retry</button><button onClick={()=>void s.recheckNow()}>recheck</button><button onClick={()=>void s.collectDocuments()}>collect</button><button onClick={()=>void s.decide('a-row','approved','','')}>decide</button><button onClick={()=>void s.saveNotes('a-row','Typed notes')}>notes</button><button onClick={()=>void s.deleteEverything()}>delete</button><button onClick={()=>s.setProfileDraft(d=>({...d,display_name:'Recovered fresh edit'}))}>edit</button>
 </div>;
}
async function flush() { await act(async()=>{for(let i=0;i<15;i++)await Promise.resolve();}); }
function deferred<T>() { let resolve!:(v:T)=>void;let reject!:(e:unknown)=>void;const promise=new Promise<T>((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject}; }
beforeEach(()=>{
 localStorage.clear();sessionStorage.clear();sessionStorage.setItem('ashyq.activeProfile','A');sessionStorage.setItem('ashyq.activeRun','a');
 vi.spyOn(api,'capabilities').mockResolvedValue({} as never);vi.spyOn(api,'cases').mockResolvedValue([]);vi.spyOn(api,'validateProfile').mockResolvedValue({gaps:[],can_proceed:true,blocking_count:0,summary:'ok'});vi.spyOn(api,'shortlist').mockResolvedValue({} as never);
 vi.spyOn(api,'getProfile').mockImplementation(async id=>profile(id) as never);vi.spyOn(api,'getRun').mockResolvedValue(run('a'));vi.spyOn(api,'listRuns').mockResolvedValue([run('b')]);vi.spyOn(api,'results').mockImplementation(async id=>[row(`${id}-row`)]);vi.spyOn(api,'summary').mockImplementation(async id=>({total:id==='b'?2:1}) as never);
});
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();});

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
 const old=deferred<void>();vi.spyOn(api,'deleteProfile').mockReturnValue(old.promise);render(<StoreProvider><Probe/></StoreProvider>);await flush();fireEvent.click(screen.getByText('delete'));await flush();fireEvent.click(screen.getByText('B'));await flush();old.resolve();await flush();expect(screen.getByTestId('case')).toHaveTextContent('B');expect(screen.getByTestId('run')).toHaveTextContent('b');
});
it('starting a new run already invalidates a refresh from its predecessor',async()=>{
 const old=deferred<ProgramResult[]>();vi.spyOn(api,'updateProfile').mockResolvedValue(profile('A') as never);vi.spyOn(api,'startRun').mockResolvedValue(run('new-run'));
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

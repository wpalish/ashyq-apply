import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import {OfficialProgrammeLibrary} from './OfficialProgrammeLibrary';
const submit=vi.fn();let key='case-a';let profile:{id:string}|null={id:'a'};
vi.mock('@/lib/store',()=>({useStore:()=>({savedProfile:profile})}));
vi.mock('@/lib/useAdmissionsActions',()=>({useAdmissionsActions:()=>({caseKey:key,activeCase:profile?.id,current:{revision:3,state:{applications:[],document_tasks:[]}},loading:false,sending:false,journalError:null,entries:[],submit})}));
vi.mock('./AdmissionsRecoveryPanel',()=>({AdmissionsRecoveryPanel:()=>null}));
beforeEach(()=>{key='case-a';profile={id:'a'};submit.mockReset();window.location.hash='#/shortlist?view=catalogue&university=qs2027-004&course=oxford-advanced-computer-science-msc';});
it('requires explicit review before saving the selected programme and follows the accepted own application',async()=>{
 submit.mockResolvedValue({accepted:true,currentRefreshed:true,receipt:{kind:'create_application',applied_delta:{applications:[{id:'b'.repeat(32),profile_id:'a'.repeat(32)}]}}});
 render(<OfficialProgrammeLibrary universityId="qs2027-004" university="University of Oxford"/>);
 fireEvent.click(screen.getAllByRole('button',{name:'Добавить программу в мой план'})[1]!);
 expect(submit).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Сохранить план на сервере'})).toBeDisabled();
 fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Сохранить план на сервере'}));
 await waitFor(()=>expect(submit).toHaveBeenCalledOnce());expect(submit.mock.calls[0]![0]).toMatchObject({expected_revision:3,target:{programme:{value:'MSc in Advanced Computer Science'}},details:{due:null}});
 await waitFor(()=>expect(window.location.hash).toContain('kind=application'));
});
it('fences a late accepted write after changing cases and prevents a replacement click on an unknown outcome',async()=>{
 let finish!:(v:unknown)=>void;submit.mockReturnValue(new Promise(resolve=>{finish=resolve;}));
 const view=render(<OfficialProgrammeLibrary universityId="qs2027-004" university="University of Oxford"/>);
 fireEvent.click(screen.getAllByRole('button',{name:'Добавить программу в мой план'})[1]!);fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Сохранить план на сервере'}));
 expect(screen.getByRole('button',{name:'Сохранить план на сервере'})).toBeDisabled();key='case-b';profile={id:'b'};view.rerender(<OfficialProgrammeLibrary universityId="qs2027-004" university="University of Oxford"/>);
 await act(async()=>finish({accepted:true,currentRefreshed:true,receipt:{kind:'create_application',applied_delta:{applications:[{id:'b'.repeat(32),profile_id:'a'.repeat(32)}]}}}));
 expect(window.location.hash).not.toContain('kind=application');expect(submit).toHaveBeenCalledOnce();
});
it('labels missing programme coverage explicitly and does not invent a degree or price',()=>{
 render(<OfficialProgrammeLibrary universityId="qs2027-500" university="Example"/>);expect(screen.getByRole('heading',{name:'Проверенные программы этого вуза ещё не опубликованы'})).toBeInTheDocument();expect(screen.queryByRole('button',{name:'Добавить программу в мой план'})).toBeNull();
});

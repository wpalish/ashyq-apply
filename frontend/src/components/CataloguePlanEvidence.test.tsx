import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {CataloguePlanEvidence} from './CataloguePlanEvidence';
import {officialProgrammes,programmeNotes,catalogueMarker} from '@/lib/officialProgrammes';
import type {AdmissionsActionsController} from '@/lib/useAdmissionsActions';
import type {ApplicationRecord} from '@/types/admissionsActions';
const p=officialProgrammes.find(p=>p.id==='oxford-advanced-computer-science-msc')!;
function fixture(){
 const application={id:'app-a',profile_id:'owner-a',details:{notes:programmeNotes(p),due:null},target:{university:p.universityName,programme:{state:'applicant_entered',value:p.title},route:{state:'applicant_entered',value:p.url},intake:{state:'applicant_entered',value:p.cycle}}} as ApplicationRecord;
 const submit=vi.fn().mockResolvedValue({accepted:true,currentRefreshed:true});
 const controller={caseKey:'owner-a',activeCase:'owner-a',current:{revision:7,state:{applications:[application],document_tasks:[]}},loading:false,sending:false,journalError:null,acceptedButUnrefreshed:false,entries:[],submit} as unknown as AdmissionsActionsController;
 return {application,controller,submit};
}
it('freezes the reviewed revision, creates one linked personal task and shows its durable target',async()=>{
 const {application,controller,submit}=fixture();
 const view=render(<CataloguePlanEvidence application={application} controller={controller}/>);
 fireEvent.click(screen.getAllByRole('button',{name:'Добавить в мои документы'})[0]!);
 expect(submit).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Сохранить задачу документа'})).toBeDisabled();
 const newer={...controller,current:{...controller.current!,revision:8}};
 view.rerender(<CataloguePlanEvidence application={application} controller={newer}/>);
 fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Сохранить задачу документа'}));
 await waitFor(()=>expect(submit).toHaveBeenCalledOnce());
 const body=submit.mock.calls[0]![0];expect(body).toMatchObject({kind:'create_personal_task',expected_revision:7,application_id:'app-a',personal:{details:{due:null}}});
 expect(body.personal.details.notes).toContain(p.documents[0]!.source.url);expect(body.personal.details.notes).toContain(`${catalogueMarker(p)}:document:0`);
 const saved={...newer,current:{...newer.current!,state:{...newer.current!.state,document_tasks:[{id:'document-a',profile_id:'owner-a',application_id:'app-a',personal:body.personal}]}}} as AdmissionsActionsController;
 view.rerender(<CataloguePlanEvidence application={application} controller={saved}/>);
 expect(screen.getByRole('link',{name:'Открыть задачу документа'})).toHaveAttribute('href',expect.stringContaining('case=owner-a&kind=document_task&id=document-a'));
 expect(screen.getAllByRole('button',{name:'Добавить в мои документы'})).toHaveLength(p.documents.length-1);
});
it('blocks replacement document writes when a prior command is pending and fences late case feedback',async()=>{
 const {application,controller,submit}=fixture();let finish!:(v:unknown)=>void;submit.mockReturnValue(new Promise(resolve=>{finish=resolve;}));
 const view=render(<CataloguePlanEvidence application={application} controller={controller}/>);
 fireEvent.click(screen.getAllByRole('button',{name:'Добавить в мои документы'})[0]!);fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Сохранить задачу документа'}));
 expect(screen.getByRole('button',{name:'Сохранить задачу документа'})).toBeDisabled();
 const other={...controller,caseKey:'owner-b',activeCase:'owner-b',current:{...controller.current!,state:{...controller.current!.state,applications:[]}}};
 view.rerender(<CataloguePlanEvidence application={application} controller={other as AdmissionsActionsController}/>);
 await act(async()=>finish({accepted:true,currentRefreshed:true}));
 expect(screen.queryByText('Сервер подтвердил личную задачу. Она связана с этой заявкой.')).toBeNull();expect(submit).toHaveBeenCalledOnce();
 expect(screen.getAllByRole('button',{name:'Добавить в мои документы'}).every(button=>(button as HTMLButtonElement).disabled)).toBe(true);
});
it('does not offer source document actions when application context no longer matches the snapshot',()=>{
 const {application,controller}=fixture();
 const changed={...application,target:{...application.target,university:'Other university'}} as ApplicationRecord;
 render(<CataloguePlanEvidence application={changed} controller={controller}/>);
 expect(screen.getByText(/Сохранённая версия условий недоступна или контекст заявки изменён/)).toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Добавить в мои документы'})).toBeNull();
});

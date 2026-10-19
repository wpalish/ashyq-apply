import { useRef, useState } from 'react';
import { planProgramme, catalogueMarker, programmeHref } from '@/lib/officialProgrammes';
import { useAdmissionsActions } from '@/lib/useAdmissionsActions';
import { OfficialProgrammeFacts } from './OfficialProgrammeLibrary';
import { AdmissionsRecoveryPanel } from './AdmissionsRecoveryPanel';
import { targetHref } from '@/lib/admissionsNavigation';
import type { ApplicationRecord } from '@/types/admissionsActions';
export function CataloguePlanEvidence({application}:{application:ApplicationRecord}){
 const p=planProgramme(application.details.notes);
 if(!application.details.notes.startsWith('unimatch-catalogue:'))return null;
 return <section className="panel official-plan-evidence"><h2>План по программе из каталога</h2>{p?<><p>Сохранённый снимок условий: {p.checkedAt} · {p.cycle}. Проверка соответствия твоего профиля и подтверждение университета не выполнены.</p><a href={programmeHref(p)}>Открыть карточку и официальные источники</a><details><summary>Требования, стоимость, финансирование и официальные сроки</summary><OfficialProgrammeFacts programme={p}/></details><CatalogueDocumentActions application={application}/></>:<p>Сохранённая версия условий сейчас недоступна. Ссылки остались в заметках заявки; новые условия не подставляются вместо прежнего снимка.</p>}</section>;
}
function CatalogueDocumentActions({application}:{application:ApplicationRecord}){
 const p=planProgramme(application.details.notes)!; const actions=useAdmissionsActions();
 const [review,setReview]=useState<{key:string;index:number;confirmed:boolean;attempted:boolean}|null>(null);
 const [message,setMessage]=useState<{key:string;text:string}|null>(null);const live=useRef(actions.caseKey);live.current=actions.caseKey;const busy=useRef(false);
 const current=actions.current?.state?.applications.find(app=>app.id===application.id);const own=current&&current.profile_id===actions.activeCase&&current.details.notes===application.details.notes;
 const ready=Boolean(own&&actions.current&&!actions.loading&&!actions.sending&&!actions.journalError&&!actions.acceptedButUnrefreshed&&!actions.entries.some(e=>e.descriptor.status!=='acknowledged'));
 const save=async(index:number)=>{
  if(!ready||!actions.current||!review||review.key!==actions.caseKey||review.index!==index||!review.confirmed||review.attempted||busy.current)return;
  const key=actions.caseKey;const revision=actions.current.revision;const doc=p.documents[index];if(!doc)return;const marker=`${catalogueMarker(p)}:document:${index}`;busy.current=true;setReview({...review,attempted:true});
  try{const result=await actions.submit({schema_version:'admissions-actions-v1',kind:'create_personal_task',client_write_uuid:crypto.randomUUID(),expected_revision:revision,application_id:application.id,personal:{label:doc.text.slice(0,200),responsible_actor:'applicant',depends_on_task_ids:[],details:{due:null,notes:`${marker}\nPersonal task copied from a dated catalogue source, not a live requirement binding.\n${doc.text}\n${doc.scope}\nChecked ${doc.source.checkedAt}\n${doc.source.url}`}}});
   if(live.current!==key)return;
   setMessage({key,text:result.accepted?'Сервер подтвердил личную задачу. Она связана с этой заявкой.':'Сохранение не подтверждено. Сначала проверь журнал восстановления.'});
  }catch{if(live.current===key)setMessage({key,text:'Не удалось подтвердить задачу. Проверь журнал перед повторным сохранением.'});}finally{busy.current=false;}
 };
 return <div><h3>Подготовить документы</h3><p>Это личные задачи со ссылкой на датированный источник. Их готовность и применимость ты проверяешь отдельно.</p>{p.documents.length?<ul className="official-facts">{p.documents.map((doc,index)=>{const marker=`${catalogueMarker(p)}:document:${index}`;const task=actions.current?.state?.document_tasks.find(t=>t.application_id===application.id&&t.personal.details.notes.split('\n')[0]===marker);const selected=review?.key===actions.caseKey&&review.index===index;return <li key={index}><p>{doc.text}</p>{task?<a className="btn btn--sm" href={targetHref({screen:'documents',profileId:task.profile_id,target:{kind:'document_task',id:task.id}})}>Открыть задачу документа</a>:selected?<div><label className="check"><input type="checkbox" disabled={review.attempted} checked={review.confirmed} onChange={e=>setReview({...review,confirmed:e.target.checked})}/>Я проверил(а) требование и хочу создать связанную личную задачу.</label><button className="btn" disabled={!ready||!review.confirmed||review.attempted} onClick={()=>void save(index)}>Сохранить задачу документа</button>{!review.attempted&&<button className="btn btn--ghost" onClick={()=>setReview(null)}>Отмена</button>}</div>:<button className="btn btn--sm" disabled={!ready} onClick={()=>setReview({key:actions.caseKey,index,confirmed:false,attempted:false})}>Добавить в мои документы</button>}</li>;})}</ul>:<p>Список документов ещё не проверен.</p>}{message?.key===actions.caseKey&&<p role="status">{message.text}</p>}{actions.error&&<p role="alert">{actions.error}</p>}<AdmissionsRecoveryPanel controller={actions}/></div>;
}

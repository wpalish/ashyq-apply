import { useState } from 'react';
import { BookModerationBoard } from '@/components/BookModerationBoard';
import type { ReportStatus, ReportView } from '@/types';
const samples:ReportView[]=[
 {id:'sample-spam',reporter:{user_id:'fictional-one',display_name:'Демо-участник 1'},subject_type:'post',subject_id:'fictional-post',subject_author:{user_id:'fictional-author',display_name:'Вымышленный автор'},reason:'spam',note:'Пример жалобы для проверки расположения элементов.',excerpt:'Повторяющаяся реклама услуг в учебном обсуждении. Содержимое вымышлено.',status:'open',created_at:'2026-10-18T12:00:00Z',resolved_by:null,resolution_note:''},
 {id:'sample-harassment',reporter:{user_id:'fictional-two',display_name:'Демо-участник 2'},subject_type:'reply',subject_id:'fictional-reply',subject_author:null,reason:'harassment',note:'Синтетическая карточка.',excerpt:'Пример неподобающего комментария. Реальных участников здесь нет.',status:'open',created_at:'2026-10-18T13:00:00Z',resolved_by:null,resolution_note:''},
];
/** Isolated loopback-only design fixture. Does not import or call application APIs. */
export function BookModerationFixture(){
 const [selected,setSelected]=useState(samples[0]!.id),[tab,setTab]=useState<ReportStatus>('open');const items=samples.filter(item=>item.status===tab);const report=items.find(item=>item.id===selected)??items[0];
 return <><div className="notice notice--demo" role="note"><strong>Демонстрация макета модерации</strong><p>Вымышленные записи. Доступ к настоящей очереди не предоставлен. Кнопки принятия решений отключены; запросы на сервер не отправляются.</p></div><BookModerationBoard items={items} selectedId={selected} onSelect={setSelected} tab={tab} onTab={setTab} detail={report?<article className="report-row"><h2>Жалоба на публикацию</h2><p className="report-row__excerpt">{report.excerpt}</p><p className="small">{report.note}</p><p className="xs muted">Отправитель: {report.reporter.display_name} · только вымышленный пример</p><fieldset disabled className="stack" style={{border:0,padding:0,marginTop:30}}><label className="field">Примечание к решению<input value="" readOnly/></label><div className="row"><button className="btn btn--danger">Удалить контент</button><button className="btn">Отклонить жалобу</button></div></fieldset></article>:null}/></>;
}

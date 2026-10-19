import { useJourneyRoute, programmeTab } from '@/lib/programmeJourney';
import { useEffect, useRef, useState } from 'react';
import { ArrowRight, CalendarBlank, FileText, GraduationCap } from '@phosphor-icons/react';
import { useStore } from '@/lib/store';
import { useAdmissionsToday } from '@/lib/useAdmissionsToday';
import { useAdmissionsActions } from '@/lib/useAdmissionsActions';
import { useAdmissionsTarget } from '@/lib/admissionsNavigation';
import { dateTime, localDate } from '@/lib/format';
import { bookTaskView } from '@/lib/bookPlanPresentation';
import { BookHelp, BookLogo } from './BookUI';
import { BookTaskList } from './BookTaskList';
import { BookProgramme } from './BookProgramme';
import { BookComparison } from './BookComparison';
import { ApplicationsPanel } from '@/screens/ApplicationsPanel';

export function BookPlan({ onCollect, onFind, onPrepare }: { onCollect:()=>void; onFind?:()=>void; onPrepare?:()=>void }) {
  const { results, run, savedProfile, collectDocuments, decide, caseEpoch }=useStore();
  const journey=useJourneyRoute();
  const today=useAdmissionsToday(); const actions=useAdmissionsActions(); const target=useAdmissionsTarget();
  const [programmeLinkError,setProgrammeLinkError]=useState(false);
  const [opened,setOpened]=useState<{epoch:number;id:string}|null>(null);
  const [compared,setCompared]=useState<string[]>([]); const [error,setError]=useState(''); const [collecting,setCollecting]=useState(false);
  const previous=useRef<string|null>(null);
  useEffect(() => {
    const followProgramme = () => {
      const [route, query] = window.location.hash.split('?');
      const params = new URLSearchParams(query);
      const id = params.get('programme');
      setProgrammeLinkError(Boolean(id && (params.get('case') !== savedProfile?.id || !results.some(result => result.id === id && run?.profile_id === savedProfile?.id))));
      setOpened(route === '#/approved' && params.get('case') === savedProfile?.id && id ? { epoch: caseEpoch, id } : null);
    };
    followProgramme(); window.addEventListener('hashchange', followProgramme);
    return () => window.removeEventListener('hashchange', followProgramme);
  }, [caseEpoch, savedProfile?.id, results, run?.profile_id]);
  const owned=run?.profile_id===savedProfile?.id?results:[];
  const selected=owned.filter(result=>['approved','maybe'].includes(result.user_decision));
  const current=opened?.epoch===caseEpoch?owned.find(result=>result.id===opened.id):null;
  const openedId=current?.id??null;
  useEffect(()=>{if(openedId) document.getElementById('book-programme-title')?.focus();else if(previous.current) document.getElementById(`book-plan-${previous.current}`)?.focus();previous.current=openedId;},[openedId]);
  const value=today.value;
  const cards=value?[...value.overdue_personal,...value.today_personal,...value.future.filter(card=>card.reason!=='accepted_study_action'),...value.undated_personal]:[];
  const nearest=value&&cards[0]?bookTaskView(cards[0],value,actions.current):null;
  const dates=selected.filter(result=>result.admission_deadline).sort((a,b)=>(a.admission_deadline??'').localeCompare(b.admission_deadline??''));
  const collectingJob=run?.job_status==='queued'||run?.job_status==='running'||run?.stage==='document_collection'&&run.job_running;
  const liveEpoch=useRef(caseEpoch); liveEpoch.current=caseEpoch;
  useEffect(()=>{setCollecting(false);setError('');setCompared([]);},[caseEpoch]);
  const collect=async()=>{const epoch=caseEpoch;setCollecting(true);setError('');try{const confirmed=await collectDocuments();if(liveEpoch.current!==epoch)return;if(confirmed)onCollect();else setError('Список документов не подтверждён. Проверь состояние исследования.');}catch(failure){if(liveEpoch.current===epoch)setError(failure instanceof Error?failure.message:String(failure));}finally{if(liveEpoch.current===epoch)setCollecting(false);}};
  if(target?.target.kind==='application')return <ApplicationsPanel pageHeading/>;
  if(current) return <><BookProgramme profileId={savedProfile?.id} initialTab={programmeTab(journey?.view)} backLabel="К моему плану" result={current} onBack={()=>{setOpened(null);window.location.hash='#/approved';}} onDecision={(decision,reason)=>decide(current.id,decision,reason,current.user_notes)} compared={compared.includes(current.id)} onCompare={()=>setCompared(old=>old.includes(current.id)?old.filter(id=>id!==current.id):old.length<3?[...old,current.id]:old)}/>{compared.length>0&&<BookComparison results={owned.filter(row=>compared.includes(row.id))} onRemove={id=>setCompared(old=>old.filter(value=>value!==id))} onClear={()=>setCompared([])} onAdd={result=>decide(result.id,'approved','',result.user_notes)}/>}</>;
  return <div className="book-plan workspace-plan"><header className="screen__head"><h1 className="screen__title">Мой план</h1><p className="screen__lede">Сначала ближайшие дела. Затем программы, требования и сроки.</p></header>
    <nav className="workspace-section-nav" aria-label="Разделы плана"><a href="#plan-tasks" onClick={event=>{event.preventDefault();document.getElementById('plan-tasks')?.scrollIntoView({block:'start'});document.getElementById('plan-tasks')?.focus();}}>Задачи</a><a href="#plan-programmes" onClick={event=>{event.preventDefault();document.getElementById('plan-programmes')?.scrollIntoView({block:'start'});document.getElementById('plan-programmes')?.focus();}}>Программы ({selected.length})</a><a href="#/applications">Заявки</a><a href="#/calendar">Календарь</a><a href="#/profile">Профиль</a></nav>
    <div className="book-plan__layout">
    <div className="book-plan__main">{programmeLinkError&&<p className="notice notice--warn" role="status">Эта программа недоступна в текущем профиле. Выбери программу из своего плана ниже.</p>}{(today.error||actions.error)&&<div className="notice notice--warn"><p>{today.error||actions.error} {value?'Показаны последние подтверждённые записи.':''}</p><button className="btn btn--sm" onClick={()=>{void today.refresh();void actions.refresh();}}>Обновить</button></div>}{value?.needs_refresh&&<BookHelp>План изменился. Обнови данные, прежде чем открывать задачу.</BookHelp>}
      <div className="book-plan__two" id="plan-tasks" tabIndex={-1}><section className="panel"><header><h2>Задачи и личные сроки</h2><a href="#/today">Смотреть все →</a></header>{today.loading&&!value?<p role="status">Читаем сохранённый план…</p>:value&&cards.length>0?<BookTaskList cards={cards.slice(0,4)} projection={value} current={actions.current} compact/>:<p className="muted small">Задачи ещё не добавлены. Требования из исследования не становятся личными задачами автоматически.</p>}{nearest?.href&&<a href={nearest.href} className="btn btn--primary">Открыть ближайшую задачу<ArrowRight size={18}/></a>}<a className="book-text-action" href="#/documents">Добавить задачу по документам</a></section>
      <section className="panel"><header><h2>Ключевые дедлайны</h2><a href="#/calendar">Все сроки →</a></header><ol className="book-plan__timeline">{dates.slice(0,4).map(result=><li key={result.id}><strong>{localDate(result.admission_deadline,'ru-RU')}</strong><div>{result.university}<small>Дата из исследования · {result.admission_deadline_timezone??'часовой пояс не подтверждён'}</small></div></li>)}</ol>{!dates.length&&<p className="muted small">Сроки выбранных программ ещё не подтверждены.</p>}<a className="book-text-action" href="#/calendar"><CalendarBlank size={18}/>Открыть календарь</a></section></div>
      <section className="panel book-plan__programmes" id="plan-programmes" tabIndex={-1}><header><div><h2>Сохранённые программы ({selected.length})</h2><p>Отслеживай требования и прогресс по каждой программе.</p></div>{onFind&&<button className="book-text-action" onClick={onFind}>Добавить программу<ArrowRight size={17}/></button>}</header>
      {selected.length?<div className="book-plan__table"><div className="book-plan__table-head"><span>Программа</span><span>Университет</span><span>Дедлайн подачи</span><span>Статус</span><span/></div>{selected.map(result=><button className="book-plan__programme" id={`book-plan-${result.id}`} key={result.id} onClick={()=>{setOpened({epoch:caseEpoch,id:result.id});window.location.hash=`#/approved?case=${encodeURIComponent(savedProfile?.id??'')}&programme=${encodeURIComponent(result.id)}`;}}><div><BookLogo university={result.university}/><span><strong>{result.program}</strong><small>{result.degree==='bachelor'?'Бакалавриат':result.degree==='master'?'Магистратура':result.degree}</small></span></div><div><strong>{result.university}</strong><small>{result.country}</small></div><span>{result.admission_deadline?localDate(result.admission_deadline,'ru-RU'):'Не подтверждён'}<small>{result.admission_deadline_timezone??'Часовой пояс неизвестен'}</small></span><span className="chip chip--info">{result.user_decision==='approved'?'В плане':'Рассматриваю'}</span><span aria-hidden="true">›</span></button>)}</div>:<div className="empty"><h3>Пока нет сохранённых программ</h3><p>Добавь подходящие программы из результатов подбора.</p>{onFind&&<button className="btn btn--primary" onClick={onFind}>Открыть подбор</button>}</div>}</section>
      <div className="book-plan__two book-plan__guidance"><section className="panel"><FileText size={23}/><div><h3>Обязательные требования</h3><p>Проверь собранные чеклисты и открытые вопросы выбранных программ.</p><button className="book-text-action" disabled={!selected.length||Boolean(collectingJob)||collecting} onClick={()=>void collect()}>{collecting||collectingJob?'Собираем документы…':'Собрать требования к документам'}</button>{selected.some(result=>result.checklist)&&<button className="book-text-action" onClick={onCollect}>Открыть собранные чеклисты</button>}</div></section><section className="panel"><GraduationCap size={23}/><div><h3>Дополнительная подготовка</h3><p>То, что может усилить заявку, но не всегда обязательно. Покупка курса не является требованием вуза.</p>{onPrepare&&<button className="book-text-action" onClick={onPrepare}>Открыть подготовку →</button>}</div></section></div>{error&&<p role="alert">{error}</p>}
      <details className="book-plan__applications"><summary>Мои заявки и личные статусы</summary><ApplicationsPanel/></details>
      {owned.some(row=>row.user_decision==='rejected')&&<details><summary>Программы, от которых ты отказался</summary>{owned.filter(row=>row.user_decision==='rejected').map(row=><article className="book-plan__rejected" key={row.id}><strong>{row.university} · {row.program}</strong><p>{row.user_decision_reason}</p><button className="btn btn--sm" onClick={()=>void decide(row.id,'undecided','',row.user_notes)}>Вернуть к рассмотрению</button></article>)}</details>}
      {value&&<p className="book-plan__observed">План прочитан: {dateTime(value.as_of)} · {value.display_timezone}</p>}
    </div></div>
  </div>;
}

import { ArrowRight, CalendarBlank, Clock } from '@phosphor-icons/react';
import { useStore } from '@/lib/store';
import { useAdmissionsToday } from '@/lib/useAdmissionsToday';
import { useAdmissionsActions } from '@/lib/useAdmissionsActions';
import { bookTaskView } from '@/lib/bookPlanPresentation';
import { dateTime } from '@/lib/format';
import { BookTaskList } from './BookTaskList';
import { BookHelp } from './BookUI';

export function BookToday() {
  const { savedProfile }=useStore(); const today=useAdmissionsToday(); const actions=useAdmissionsActions();
  const value=today.value;
  const personal=value?[...value.overdue_personal,...value.today_personal,...value.future.filter(card=>card.reason!=='accepted_study_action'),...value.undated_personal]:[];
  const study=value?[...value.today_study,...value.future.filter(card=>card.reason==='accepted_study_action')]:[];
  const first=value&&personal[0]?bookTaskView(personal[0],value,actions.current):null;
  const year=(savedProfile?.context as {intake_year?:number})?.intake_year;
  const stamp=value?.as_of?dateTime(value.as_of,value.display_timezone):'Дата чтения пока не подтверждена';
  return <div className="book-today"><header className="book-today__header"><div><p className="screen__eyebrow">Сегодня · {stamp}</p><h1 className="screen__title">Сегодня</h1><p className="screen__lede">Важные шаги, чтобы двигаться к поступлению{year?` в ${year} году`:''}.<br/>Твои личные задачи и ближайшие сроки собраны в одном месте.</p></div><aside><span className="book-icon-tile"><CalendarBlank size={28}/></span><div><h2>Поступление{year?` · ${year}`:''}</h2><p>Сроки могут отличаться по программам. Проверяй актуальные даты и применимость требований.</p><a href="#/calendar">Открыть календарь <ArrowRight size={16}/></a></div></aside></header>
    {(today.error||actions.error)&&<div className="notice notice--warn"><p>{today.error||actions.error} {value?'Показан последний подтверждённый план.':'Список может быть неполным.'}</p><button className="btn btn--sm" onClick={()=>{void today.refresh();void actions.refresh();}}>Повторить чтение</button></div>}
    {value&&(value.needs_refresh||value.consistency==='mixed_revision')&&<BookHelp>Данные прочитаны в разных состояниях. Обнови план перед переходом к задаче.</BookHelp>}
    {value?.action_state==='unavailable'&&<BookHelp>Личные задачи сейчас недоступны. Пустой список не означает отсутствие дел.</BookHelp>}
    {today.loading&&!value&&<p role="status">Загружаем сохранённые задачи…</p>}
    {value&&personal.length>0?<><BookTaskList cards={personal.slice(0,3)} projection={value} current={actions.current}/><div className="book-today__start">{first?.href&&<a className="btn btn--primary" href={first.href}>Начать первую задачу<ArrowRight size={20}/></a>}<p><Clock size={20}/>Обновляй статус в карточке задачи. Университет не подтверждает готовность документа через эту отметку.</p></div></>:!today.loading&&value?.action_state!=='unavailable'&&<section className="panel book-today__empty"><CalendarBlank size={38}/><h2>Личных задач пока нет</h2><p>Добавь напоминание к документу или заявке. Неизвестные требования остаются вопросами для проверки.</p><a className="btn btn--primary" href="#/documents">Добавить задачу по документам<ArrowRight size={18}/></a></section>}
    <section className="book-today__later"><Clock size={36}/><div><h2>Остальное можно позже</h2><p>Другие задачи появятся по мере приближения их сроков или после добавления новых записей.</p>{value&&personal.length>3&&<details><summary>Остальные личные задачи ({personal.length-3})</summary><BookTaskList cards={personal.slice(3)} projection={value} current={actions.current} compact/></details>}{value&&study.length>0&&<details><summary>Дополнительная подготовка ({study.length})</summary><p>Занятия по выбранному тобой плану. Они не заменяют требования и не обязательны для использования Unimatch.</p><BookTaskList cards={study} projection={value} current={actions.current} compact/></details>}</div></section>
    <footer className="book-today__footer"><button className="book-text-action" disabled={today.loading} onClick={()=>{void today.refresh();void actions.refresh();}}>Обновить план</button><a href="#/approved">Мой план поступления</a><a href="#/applications">Мои заявки</a></footer>
  </div>;
}

import { ArrowRight, ArrowClockwise } from '@phosphor-icons/react';
import { useAdmissionsToday } from '@/lib/useAdmissionsToday';
import { useAdmissionsActions } from '@/lib/useAdmissionsActions';
import { BookTaskList } from './BookTaskList';

/** Show the server's personal agenda, with the same exact targets as Plan. */
export function HomeAgenda() {
  const today = useAdmissionsToday();
  const actions = useAdmissionsActions();
  const value = today.value;
  const cards = value ? [...value.overdue_personal, ...value.today_personal,
    ...value.future.filter(card => card.reason !== 'accepted_study_action'), ...value.undated_personal] : [];
  const unavailable = today.error || actions.error || value?.action_state === 'unavailable';
  return <section className="workspace-agenda" aria-labelledby="agenda-title">
    <header><div><h2 id="agenda-title">С чего начнём?</h2><p>Личные задачи и сроки из твоего плана.</p></div><a className="book-text-action" href="#/approved">Весь план<ArrowRight size={17}/></a></header>
    {today.loading && !value && <p role="status">Читаем твой план…</p>}
    {unavailable && <div className="notice notice--warn" role="status"><p>Не удалось обновить план. {value ? 'Ниже последние подтверждённые данные.' : 'Попробуй ещё раз.'}</p><button className="btn btn--sm" disabled={today.loading || actions.loading} onClick={() => { void today.refresh(); void actions.refresh(); }}><ArrowClockwise size={17}/>Обновить план</button></div>}
    {value?.needs_refresh && <p className="notice notice--warn">План изменился. Обнови данные, чтобы открыть актуальные задачи.</p>}
    {value && cards.length > 0 && <BookTaskList cards={cards.slice(0, 3)} projection={value} current={actions.current} compact/>}
    {!today.loading && !unavailable && value && cards.length === 0 && <div className="workspace-empty"><h3>Добавь первое дело</h3><p>Например, запросить выписку оценок или подготовить перевод. Укажи свой срок и отмечай результат в карточке.</p><a className="btn btn--primary" href="#/documents">Добавить задачу по документам<ArrowRight size={17}/></a></div>}
    <footer><a href="#/documents">Документы и задачи</a><a href="#/applications">Заявки и статусы</a><a href="#/calendar">Календарь сроков</a><button className="book-text-action" disabled={today.loading || actions.loading} aria-label="Обновить задачи" onClick={() => { void today.refresh(); void actions.refresh(); }}><ArrowClockwise size={17}/>{today.loading ? 'Обновляем…' : 'Обновить'}</button></footer>
  </section>;
}

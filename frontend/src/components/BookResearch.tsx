import { ArrowRight, BookOpen } from '@phosphor-icons/react';
import type { RunView } from '@/types';
import { dateTime } from '@/lib/format';
import { BookGlobe, BookHelp, BookLogo, BookWorkflow } from './BookUI';
import { SourceLink } from './primitives';

const STAGES: Record<string,string> = {
  queued:'Готовим очередь исследования', profile_validation:'Проверяем профиль',
  candidate_discovery:'Ищем университеты', program_verification:'Читаем страницы программ',
  funding_discovery:'Изучаем финансирование', assessment:'Сравниваем требования с профилем',
  awaiting_user_decision:'Проверь найденные программы', document_collection:'Собираем требования к документам', completed:'Исследование завершено',
  failed:'Исследование требует внимания', retryable_failed:'Исследование прервалось', cancelled:'Исследование остановлено',
};
export function BookResearch({ run, count, onDone, onCancel }: {
  run: RunView; count: number; onDone: () => void; onCancel: () => Promise<void>;
}) {
  const finished=['awaiting_user_decision','completed'].includes(run.stage);
  const stopped=['failed','retryable_failed','cancelled'].includes(run.stage) || run.stale;
  const observations=run.programme_observations??[];
  return <div className="book-research">
    <header className="book-research__hero"><div><p className="screen__eyebrow">Подбор программ</p><h1 className="screen__title">{stopped?'Исследование требует внимания':finished?'Проверь найденные программы':<>Проверяем программы<br/>и требования</>}</h1><p className="screen__lede">Мы изучаем официальные сайты вузов, проверяем требования, сроки, стоимость и нужные документы. Доступные находки можно просмотреть, пока остальные факты уточняются.</p></div><BookGlobe/></header>
    <section className="book-research__stage"><span className="book-icon-tile"><BookOpen size={28} weight="fill"/></span><div><small>Текущий этап</small><h2>{STAGES[run.stage]??run.stage}</h2><p>{finished?'Проверяй подтверждения и открытые вопросы в результатах.':stopped?'Сохранённые находки остаются доступны. Подробности и причины остановки — ниже.':'Проверяем информацию на сайтах вузов и программ. Это может занять некоторое время.'}</p></div><div><button className="btn btn--primary" type="button" disabled={count===0} onClick={onDone}>Посмотреть найденное<ArrowRight size={19}/></button>{!finished&&!stopped&&run.job_running&&<button className="book-text-action" type="button" onClick={()=>void onCancel()}>Остановить подбор</button>}</div></section>
    <BookWorkflow stage={1} resultCount={count} onNavigate={screen=>{window.location.hash=`#/${screen}`;}}/>
    <section className="panel book-research__sources"><h2>Проверяем источники</h2><p>Открываем официальные сайты, изучаем требования и собираем ключевую информацию.</p>{observations.length?observations.slice(0,8).map(observation=><article key={observation.id}><BookLogo university={observation.institution}/><div><strong>{observation.domain}</strong><small>{observation.institution}</small><SourceLink url={observation.programme_url}/></div><div><strong>Страница прочитана</strong><small>Требования и совместимость ещё не оценены</small></div><small>{observation.reads[0]?.fetched_at?dateTime(observation.reads[0].fetched_at):'Время чтения не записано'}</small><span className="chip">Наблюдение</span></article>):<div className="book-research__empty">{run.programme_observation_state==='unavailable'?'Наблюдения о страницах сейчас недоступны. Это ограничение результата.':'Ранние наблюдения о страницах пока не зафиксированы. Счётчики и журнал этапов доступны ниже.'}</div>}
      <BookHelp>Подтверждённая страница программы ещё не означает, что все требования прочитаны или что профиль им соответствует.</BookHelp>
    </section>
  </div>;
}

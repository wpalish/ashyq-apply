import { CalendarBlank, CaretRight, Circle, FileText, GraduationCap } from '@phosphor-icons/react';
import { bookTaskView } from '@/lib/bookPlanPresentation';
import { localDate } from '@/lib/format';
import type { ActionsCurrentOut, TodayCardV1, TodayProjectionV1 } from '@/types/admissionsActions';

export function BookTaskList({ cards, projection, current, compact=false }: {
  cards:TodayCardV1[]; projection:TodayProjectionV1; current:ActionsCurrentOut|null; compact?:boolean;
}) {
  return <div className={`book-tasks${compact?' book-tasks--compact':''}`}>{cards.map(card=>{
    const view=bookTaskView(card,projection,current);
    const body=<><Circle className="book-tasks__circle" size={22} aria-hidden="true"/>{!compact&&<span className="book-icon-tile">{card.reason==='accepted_study_action'?<GraduationCap size={28}/>:<FileText size={28}/>}</span>}<div className="book-tasks__copy"><h3>{view.label}</h3><p>{card.reason==='accepted_study_action'?'По выбранному тобой учебному плану. Подготовка необязательна.':'Открой карточку, чтобы проверить условия и обновить свой личный статус.'}</p><div className="book-tasks__meta"><span><CalendarBlank size={16}/>{card.date.local_date?localDate(card.date.local_date,'ru-RU'):'Без личного срока'}</span><span>{view.sourceLabel}</span>{card.dependency_reasons.length>0&&<span className="chip chip--warn">Проверь зависимости</span>}</div><small>{card.date.timezone??'Часовой пояс не подтверждён'}{card.date.fallback_display_only?' · дата только для отображения':''}</small></div><CaretRight className="book-tasks__chevron" size={20} aria-hidden="true"/></>;
    return view.href?<a href={view.href} key={card.id} className="book-tasks__item">{body}</a>:<article key={card.id} className="book-tasks__item">{body}<p className="book-tasks__unavailable">Переход недоступен. Обнови план и проверь исходную задачу.</p></article>;
  })}</div>;
}

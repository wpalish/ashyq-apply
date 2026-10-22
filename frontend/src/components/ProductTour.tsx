import { useState } from 'react';
import { ArrowRight, CalendarBlank, Check, FileText, GraduationCap, Link as LinkIcon, User } from '@phosphor-icons/react';
import { BookTransition } from './BookTransition';

/** A labelled product explanation, never an applicant record or research result. */
export function ProductTour({ english = false }: { english?: boolean }) {
  const [step, setStep] = useState(0);
  const steps = english ? [
    { title: 'Your profile', heading: 'Start with what matters to you.', description: 'Your education, interests and budget give your research a starting point.', Icon: User, rows: ['Education and qualifications', 'Study interests', 'Budget and preferences'] },
    { title: 'Programmes', heading: 'See the options. Ask better questions.', description: 'Compare programmes and separate confirmed conditions from information that still needs checking.', Icon: GraduationCap, rows: ['Degree and teaching language', 'Costs with currency and period', 'Open questions and sources'] },
    { title: 'Evidence', heading: 'Read the reason behind the result.', description: 'Official links, excerpts and scope help you review what a source actually confirms.', Icon: LinkIcon, rows: ['Official source', 'Quoted evidence and scope', 'What remains unknown'] },
    { title: 'Your plan', heading: 'Turn a choice into a next step.', description: 'Keep personal document tasks, applications and dates connected to your selected programme.', Icon: CalendarBlank, rows: ['Document tasks', 'Application notes', 'Personal dates and official deadlines'] },
  ] as const : [
    { title: 'Твой профиль', heading: 'Начни с того, что важно тебе.', description: 'Образование, интересы и бюджет задают отправную точку для поиска.', Icon: User, rows: ['Образование и экзамены', 'Интересы и направления', 'Бюджет и предпочтения'] },
    { title: 'Программы', heading: 'Увидеть варианты. Понять различия.', description: 'Сравни программы и отдели подтверждённые условия от вопросов, которые ещё нужно проверить.', Icon: GraduationCap, rows: ['Уровень и язык обучения', 'Расходы с валютой и периодом', 'Открытые вопросы и источники'] },
    { title: 'Источники', heading: 'За каждым решением — основание.', description: 'Официальная ссылка, цитата и контекст помогают проверить, что именно подтверждает страница.', Icon: LinkIcon, rows: ['Официальный источник', 'Цитата и область действия', 'Что остаётся неизвестным'] },
    { title: 'Твой план', heading: 'Преврати выбор в следующий шаг.', description: 'Свяжи выбранную программу с личными задачами по документам, заявкой и датами.', Icon: CalendarBlank, rows: ['Задачи по документам', 'Заметки к заявке', 'Личные даты и официальные сроки'] },
  ] as const;
  const current = steps[step] ?? steps[0];
  return <section className="product-tour" id="how-it-works" aria-labelledby="product-tour-title">
    <header className="editorial-section-heading"><h2 id="product-tour-title">{english ? <>One journey.<br/>A clearer next step.</> : <>Всё складывается<br/>в твой маршрут.</>}</h2><p>{english ? 'Explore how the workspace connects your choices. This is a product guide, not a research result.' : 'Посмотри, как связаны разделы. Это знакомство с продуктом, а не результат подбора.'}</p></header>
    <div className="product-tour__body">
      <nav className="product-tour__steps" aria-label={english ? 'Explore the product' : 'Знакомство с продуктом'}>{steps.map(({ title, Icon }, index) => <button key={title} type="button" aria-pressed={step === index} aria-controls="product-tour-detail" onClick={() => setStep(index)}><Icon size={22} aria-hidden="true"/><span>{title}</span><ArrowRight size={18} aria-hidden="true"/></button>)}</nav>
      <BookTransition motionKey={String(step)} className="product-tour__surface"><div id="product-tour-detail" role="region" aria-labelledby="product-tour-active-title"><span className="product-tour__symbol" aria-hidden="true"><current.Icon size={34}/></span><h3 id="product-tour-active-title">{current.heading}</h3><p>{current.description}</p><ul>{current.rows.map(row => <li key={row}><Check size={17} aria-hidden="true"/>{row}</li>)}</ul><small><FileText size={15} aria-hidden="true"/>{english ? 'Guide to the workspace · your data stays in your own case' : 'Обзор разделов · личные данные остаются в твоём кейсе'}</small></div></BookTransition>
    </div>
    <p role="status" className="visually-hidden">{english ? 'Section: ' : 'Раздел: '}{current.title}</p>
  </section>;
}

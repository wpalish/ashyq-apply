import { ProgrammeJourney } from './ProgrammeJourney';
import { journeyHref } from '@/lib/programmeJourney';
import { m, useReducedMotion } from 'motion/react';
import { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, CalendarBlank, Check, Question, Plus, BookmarkSimple, X } from '@phosphor-icons/react';
import type { ProgramResult, UserDecision } from '@/types';
import { date, money } from '@/lib/format';
import { programmeLanguage, requirementName } from '@/lib/bookPresentation';
import { BookGlobe, BookLogo } from './BookUI';
import { ResultDetail } from './ResultDetail';
import { SourceLink } from './primitives';

const TABS = ['Обзор', 'Требования', 'Стоимость', 'Документы', 'Источники'] as const;

/** The selected result is the same case-owned object as the list. No new research. */
export function BookProgramme({ result, onBack, onDecision, compared, onCompare, backLabel, profileId, initialTab='Обзор' }: {
  result: ProgramResult;
  onBack: () => void;
  backLabel?: string;
  profileId?: string;
  initialTab?: (typeof TABS)[number];
  onDecision: (decision: UserDecision, reason: string) => Promise<void>;
  compared: boolean;
  onCompare: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const [tab, setTab] = useState<(typeof TABS)[number]>(initialTab);
  useEffect(()=>{setTab(initialTab);},[initialTab]);
  const changeTab=(value:(typeof TABS)[number])=>{setTab(value);if(profileId){const screen=window.location.hash.startsWith('#/shortlist')?'shortlist':'approved';const view=value==='Требования'?'requirements':value==='Стоимость'?'costs':value==='Документы'?'documents':value==='Источники'?'sources':undefined;window.location.hash=journeyHref({screen,profileId,resultId:result.id,view});}};
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  const [detail, setDetail] = useState(false);
  const language = programmeLanguage(result);
  const checklist = result.checklist?.result_id === result.id ? result.checklist : null;
  const documents = checklist?.admission_documents ?? [];
  const choose = async (decision: UserDecision) => {
    setBusy(true); setError('');
    try { await onDecision(decision, decision === 'rejected' ? reason : ''); setRejecting(false); }
    catch (failure) { setError(failure instanceof Error ? failure.message : String(failure)); }
    finally { setBusy(false); }
  };
  const requirements = <section className="book-programme__requirements panel"><h2>Требования и мой профиль</h2>
    {result.requirement_checks.length ? result.requirement_checks.map((check, index) => <article key={index}>
      <span>{requirementName(check.requirement)}</span><i className={check.status === 'MET' ? 'is-met' : ''}>{check.status === 'MET' ? <Check size={19}/> : <Question size={19}/>}</i>
      <div><strong>{check.published_value == null ? 'Требование уточняется' : typeof check.published_value === 'object' ? JSON.stringify(check.published_value) : String(check.published_value)}</strong><p>{check.explanation}</p>{check.published_scope && <small>{check.published_scope}</small>}</div>
    </article>) : <p className="muted small">Опубликованные требования пока не подтверждены. Это не означает соответствие.</p>}
  </section>;
  const costs = <section className="panel book-programme__costs"><h2>Стоимость обучения и жизни</h2><div className="book-help"><strong>{result.funding_gap?.computable ? 'Оставшиеся расходы' : 'Расчёт неполный'}</strong><p>{result.funding_gap?.computable && result.funding_gap.gap ? money(result.funding_gap.gap) : 'Добавь недостающие данные и проверь источники.'}</p></div>
    <dl>{(['tuition', 'housing', 'meals', 'health_insurance', 'mandatory_fees'] as const).map(key => <div key={key}><dt>{{tuition:'Стоимость обучения', housing:'Проживание', meals:'Питание', health_insurance:'Страховка', mandatory_fees:'Обязательные сборы'}[key]}</dt><dd>{result.costs?.items[key] ? money(result.costs.items[key]) : 'Не указано'}</dd></div>)}</dl>
    <p className="small muted">Период и валюта сохраняются из источника. Стипендия требует отдельной проверки.</p>
    {result.costs?.source_urls.map(url => <SourceLink key={url} url={url}/>)}
  </section>;
  const documentPanel = <section className="panel"><h2>Документы</h2>{documents.length ? documents.map((document, index) => <article className="book-programme__document" key={index}><span className="book-icon-tile"><BookmarkSimple size={18}/></span><div><strong>{document.name}</strong><small>{document.required ? 'Требуется по собранным источникам' : 'Уточни применимость'} · {document.owner}</small></div>{document.source_url && <SourceLink url={document.source_url}/>}</article>) : <p className="muted small">Список документов ещё не собран. Добавь программу в план и открой документы.</p>}<p className="small muted">Наличие требования не означает, что личный документ уже готов.</p></section>;
  return <div className="book-programme">
    <button className="book-text-action book-programme__back" type="button" onClick={onBack}><ArrowLeft size={17}/>{backLabel ?? `Подбор › Результаты › ${result.university}`}</button>
    <header className="book-programme__hero"><div className="book-programme__identity"><BookLogo university={result.university}/><div><h1 id="book-programme-title" tabIndex={-1}>{result.university}</h1><p>{result.program}</p></div></div><div className="book-programme__tags"><span>{result.country}</span><span>{result.degree === 'bachelor' ? 'Программа бакалавриата' : result.degree === 'master' ? 'Магистратура' : result.degree}</span><span>{language ? language === 'english' ? 'Обучение на английском' : language : 'Язык уточняется'}</span><span><CalendarBlank size={15}/> {result.intake || 'Период уточняется'}</span></div><p>Сравни подтверждённые условия программы со своим профилем. Открытые вопросы требуют проверки.</p><BookGlobe compact/>
      <div className="row">{result.program_url && <SourceLink url={result.program_url}/>}<button className="btn btn--sm" type="button" aria-pressed={compared} onClick={onCompare}>{compared ? 'Убрать из сравнения' : 'Добавить в сравнение'}</button></div>
      <div className="book-programme__decisions"><button className="btn btn--primary" type="button" disabled={busy} onClick={() => void choose(result.user_decision === 'approved' ? 'undecided' : 'approved')}><Plus size={20}/>{result.user_decision === 'approved' ? 'В твоём плане · убрать' : 'Добавить в план'}</button><button className="btn" disabled={busy} type="button" onClick={() => void choose(result.user_decision === 'maybe' ? 'undecided' : 'maybe')}><BookmarkSimple size={20}/>{result.user_decision === 'maybe' ? 'Рассматриваю · убрать' : 'Возможно'}</button><button className="btn" type="button" disabled={busy} onClick={() => setRejecting(value => !value)}><X size={20}/>Не подходит</button></div>
      {rejecting && <form className="book-programme__rejection" onSubmit={event => { event.preventDefault(); void choose('rejected'); }}><label className="field"><span>Почему программа не подходит?</span><input required maxLength={500} value={reason} onChange={event => setReason(event.target.value)}/></label><button className="btn" disabled={busy}>Сохранить решение</button></form>}
      {busy && <p role="status">Сохраняем решение…</p>}{error && <p role="alert">{error}</p>}
    </header>
    {profileId&&<ProgrammeJourney profileId={profileId} resultId={result.id} current="requirements"/>}
    {profileId&&<section className="programme-next-action"><div><h2>{['approved','maybe'].includes(result.user_decision)?'Следующий шаг — документы':'Выбери программу для своего плана'}</h2><p>{['approved','maybe'].includes(result.user_decision)?'Проверь требования и открытые вопросы. Затем добавь связанные задачи по документам.':'Добавь программу в план или к рассматриваемым, чтобы продолжить подготовку.'}</p></div>{['approved','maybe'].includes(result.user_decision)&&<a className="btn btn--primary" href={journeyHref({screen:'documents',profileId,resultId:result.id})}>К документам этой программы<ArrowRight size={17}/></a>}</section>}
    <nav className="book-programme__tabs" aria-label="Разделы программы">{TABS.map(value => <button key={value} type="button" aria-current={tab === value ? 'page' : undefined} onClick={() => changeTab(value)}>{value}</button>)}</nav>
    <m.div key={tab} initial={false} animate={{opacity:1,y:0}} transition={{duration:reduceMotion?0:.18}}>{tab === 'Обзор' ? <div className="book-programme__grid"><section className="panel book-programme__facts"><h2>Ключевая информация</h2><dl><dt>Степень</dt><dd>{result.degree}</dd><dt>Язык преподавания</dt><dd>{language || 'Уточняется'}</dd><dt>Начало программы</dt><dd>{result.intake || 'Уточняется'}</dd><dt>Срок подачи заявки</dt><dd>{result.admission_deadline ? date(result.admission_deadline) : 'Срок уточняется'}</dd><dt>Часовой пояс срока</dt><dd>{result.admission_deadline_timezone || 'Не указан'}</dd></dl></section><section className="panel"><h2>О программе</h2><p className="small muted">{result.program}. {result.city}, {result.country}.</p><p className="small muted">Официальное описание и применимость к твоему периоду поступления проверяй в источнике.</p>{result.program_url && <SourceLink url={result.program_url}/>}</section><section className="panel"><h2>Следующие шаги</h2><ol className="book-programme__next"><li>Проверь требования и открытые вопросы.</li><li>Собери личные документы.</li><li>Уточни сроки подачи на сайте вуза.</li><li>{['approved','maybe'].includes(result.user_decision)?'Программа сохранена в твоём плане.':'Добавь программу в свой план.'}</li></ol><button className="book-text-action" type="button" onClick={() => changeTab('Источники')}>Проверить источники <ArrowRight size={16}/></button></section></div> : tab === 'Требования' ? requirements : tab === 'Стоимость' ? costs : tab === 'Документы' ? documentPanel : <section className="panel"><h2>Источники и проверка</h2><p className="small muted">Последняя проверка: {result.last_verified ? date(result.last_verified) : 'Не зафиксирована'}. {result.conflicts.length} расхождений · {result.unresolved.length} открытых вопросов.</p>{result.claims.map(claim => <details className="book-programme__claim" key={claim.id}><summary>{requirementName(claim.claim_type)} · {claim.status}{claim.is_stale ? ' · Требует обновления' : ''}</summary><blockquote>{claim.original_text_excerpt}</blockquote><SourceLink url={claim.source_url}/><p>{claim.page_title} · {claim.relevant_section}</p><small>Прочитано: {date(claim.accessed_at)} · {claim.program || 'Программа в цитате не указана'}</small></details>)}</section>}</m.div>
    <details className="book-programme__raw" open={detail} onToggle={event => setDetail(event.currentTarget.open)}><summary>Все расчёты, условия финансирования и исходные свидетельства</summary><ResultDetail result={result}/></details>
  </div>;
}

import { BookTabRail } from '@/components/BookTabRail';
import { BookTransition } from '@/components/BookTransition';
import { useState } from 'react';
import { ArrowRight, Info } from '@phosphor-icons/react';
import { BookGlobe, BookIntake, BookLogo } from '@/components/BookUI';
import { ResultDetail } from '@/components/ResultDetail';
import { SourceLink } from '@/components/primitives';
import { money } from '@/lib/format';
import { useStore } from '@/lib/store';

const FUNDING_TABS = ['Программы','Стипендии','Расходы на жизнь','Полезные ресурсы'] as const;

export function BookFundingScreen({ onPreferences }: { onPreferences?: () => void }) {
  const { results, profileDraft, capabilities } = useStore();
  const [tab, setTab] = useState<(typeof FUNDING_TABS)[number]>('Программы');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [savedOnly, setSavedOnly] = useState(true);
  const funding = (profileDraft?.funding ?? {}) as { max_annual_budget?: number; budget_currency?: string };
  const context = (profileDraft?.context ?? {}) as { intake_year?: number; intake_term?: string };
  const chosen = results.filter(result => ['approved','maybe'].includes(result.user_decision));
  const rows = savedOnly && chosen.length ? chosen : results;
  const comparable = rows.filter(result => result.funding_gap?.computable && result.funding_gap.gap?.currency === funding.budget_currency && funding.max_annual_budget != null);
  const withinBudget = comparable.filter(result => result.funding_gap!.gap!.amount <= funding.max_annual_budget!).length;
  const scholarships = rows.flatMap(result => result.scholarships.map(scholarship => ({ result, scholarship })));
  return <div className="book-funding">
    <header className="book-funding__hero"><p className="screen__eyebrow">План / Стипендии и расходы</p><h1 className="screen__title">Стипендии и расходы</h1><p className="screen__lede">Оцени стоимость обучения и жизни, найди доступные стипендии<br className="desktop-only"/>и пойми, какие программы укладываются в твой бюджет.</p><BookIntake year={context.intake_year} term={context.intake_term}/><BookGlobe compact/></header>
    {capabilities?.currency?.stale_warning && <p className="notice notice--warn">{capabilities.currency.stale_warning}</p>}
    <section className="book-funding__summary panel"><div><h2>Твой бюджет</h2><strong>{funding.max_annual_budget == null ? 'Не указан' : `${funding.budget_currency ?? ''} ${funding.max_annual_budget.toLocaleString()}`}</strong><small>в год</small>{onPreferences && <button className="book-text-action" type="button" onClick={onPreferences}>Изменить</button>}</div><div className="is-within"><span>В бюджете</span><strong>{withinBudget}</strong><small>программ</small></div><div><span>Выше бюджета</span><strong>{comparable.length - withinBudget}</strong><small>программ</small></div><div><span>Расчёт неполный</span><strong>{rows.length - comparable.length}</strong><small>программ</small></div></section>
    <BookTabRail items={FUNDING_TABS} value={tab} onChange={setTab} label="Финансирование"/>
    <BookTransition motionKey={tab}><div className="book-funding__heading"><h2>{tab === 'Программы' ? 'Программы и финансирование' : tab}</h2><label><input type="checkbox" checked={savedOnly} onChange={event => setSavedOnly(event.target.checked)}/> Только сохранённые</label></div>
    {tab === 'Программы' ? <section className="panel book-funding__programmes">{rows.map(result => <article key={result.id}><div className="book-funding__row"><BookLogo university={result.university}/><div><h3>{result.university}</h3><p>{result.program}</p><span className="chip">{result.funding_gap?.computable ? 'Расчёт доступен' : 'Расчёт неполный'}</span></div><div><small>Ориентировочные расходы в год</small><strong>{result.funding_gap?.total_cost ? money(result.funding_gap.total_cost) : 'Не установлены'}</strong><button type="button" className="book-text-action" onClick={() => setExpanded(expanded === result.id ? null : result.id)}>Показать разбивку</button></div><div><small>Стипендии</small><strong>{result.scholarships.length ? `${result.scholarships.length} вариантов` : 'Условия уточняются'}</strong><small>Проверь применимость</small></div><button className="btn" type="button" aria-expanded={expanded === result.id} onClick={() => setExpanded(expanded === result.id ? null : result.id)}>Разобрать финансирование<ArrowRight size={18}/></button></div>{expanded === result.id && <ResultDetail result={result} initialTab="funding"/>}</article>)}</section> : tab === 'Стипендии' ? <section className="panel">{scholarships.length ? scholarships.map(({ result, scholarship }) => <article className="book-funding__scholarship" key={`${result.id}:${scholarship.id}`}><h3>{scholarship.name}</h3><p>{result.university} · {scholarship.classification}</p><p>{scholarship.classification_reason}</p><strong>{scholarship.amount ? money(scholarship.amount) : 'Сумма не подтверждена'}</strong>{scholarship.source_urls.map(url => <SourceLink key={url} url={url}/>)}</article>) : <p>Официальные сведения о стипендиях пока не подтверждены. Это не означает, что стипендий нет.</p>}</section> : tab === 'Расходы на жизнь' ? <section className="panel"><h3>Проживание и повседневные расходы</h3><p className="small muted">Суммы сохраняют валюту и учебный год источника. Отсутствующие категории остаются неизвестными.</p>{rows.map(result => <article className="book-funding__scholarship" key={result.id}><h3>{result.university}</h3><dl>{(['housing','meals','health_insurance','personal'] as const).map(key => <div key={key}><dt>{{housing:'Проживание',meals:'Питание',health_insurance:'Страховка',personal:'Личные расходы'}[key]}</dt><dd>{result.costs?.items[key] ? money(result.costs.items[key]) : 'Не указано'}</dd></div>)}</dl></article>)}</section> : <section className="panel"><h3>Источники расчёта</h3>{[...new Set(rows.flatMap(result => result.costs?.source_urls ?? []))].map(url => <SourceLink key={url} url={url}/>)}</section>}
    </BookTransition>
    <aside className="book-help"><Info size={22}/><span>Указанные суммы — ориентировочные. Точные расходы зависят от программы, города и образа жизни. Стипендия не гарантируется и может требовать отдельной заявки.</span></aside>
  </div>;
}

import { Fragment, useMemo, useState } from 'react';
import { CaretDown, CheckCircle, Question } from '@phosphor-icons/react';
import type { ClaimOut, ProgramResult } from '@/types';
import { date } from '@/lib/format';
import { requirementName } from '@/lib/bookPresentation';
import { SourceLink } from '@/components/primitives';

function category(claim: ClaimOut): string {
  if (/scholarship|funding|award/i.test(claim.claim_type)) return 'Стипендии';
  if (/program_exists/i.test(claim.claim_type)) return 'Программы';
  if (/visa/i.test(claim.claim_type)) return 'Визы';
  return 'Требования';
}
function status(claim: ClaimOut): string {
  if (claim.is_stale || claim.status === 'POSSIBLY_STALE') return 'Требует обновления';
  return claim.status === 'VERIFIED_CURRENT' ? 'Подтверждено' : claim.status === 'CONFLICTING' ? 'Есть расхождение' : 'Нужно уточнить';
}
function host(url: string): string {
  try { return new URL(url).hostname || 'Демонстрационный источник'; }
  catch { return 'Адрес источника'; }
}

export function BookSourcesScreen({ results, limits, demo, onProgress }: {
  results: ProgramResult[]; limits: string[]; demo?: boolean; onProgress?: () => void;
}) {
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState('Все источники');
  const [state, setState] = useState('');
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(results[0]?.claims[0]?.id ? `${results[0].id}:${results[0].claims[0].id}` : null);
  const all = useMemo(() => results.flatMap(result => result.claims.map(claim => ({ result, claim }))), [results]);
  const rows = all.filter(({ result, claim }) => (kind === 'Все источники' || category(claim) === kind) && (!state || status(claim) === state) && (!query.trim() || `${result.university} ${result.program} ${claim.claim_type} ${claim.page_title} ${claim.original_text_excerpt}`.toLowerCase().includes(query.trim().toLowerCase())));
  const lastVerified = all.map(({ claim }) => claim.accessed_at).filter(Boolean).sort().at(-1);
  const questions = results.flatMap(result => result.unresolved.map(question => ({ result, question })));
  const conflicts = results.flatMap(result => result.conflicts.map(conflict => ({ result, conflict })));
  const pages = Math.max(1, Math.ceil(rows.length / 6));
  const shownPage = Math.min(page, pages - 1);
  return <div className="book-sources">
    <header className="screen__head"><div><h1 className="screen__title">Источники и проверка</h1><p className="screen__lede">Мы собираем информацию из официальных источников и помогаем проверить ключевые факты.</p></div><small>Последнее чтение: {lastVerified ? date(lastVerified) : 'Не зафиксировано'}</small></header>
    {demo && <p className="book-demo-caption">Демонстрационные данные. Цитаты и адреса относятся к синтетическому корпусу.</p>}
    {limits.length > 0 && <aside className="notice notice--warn"><strong>Ограничения исследования</strong><p>Не все официальные страницы удалось проверить. Отсутствие вопроса у программы не означает полноту проверки.</p><details><summary>Показать ограничения ({limits.length})</summary><ul>{limits.map((limit, index) => <li key={index}>{limit}</li>)}</ul></details>{onProgress && <button className="btn btn--sm" type="button" onClick={onProgress}>Открыть ход исследования</button>}</aside>}
    <div className="book-sources__toolbar"><nav aria-label="Тип источника">{['Все источники','Программы','Стипендии','Требования','Визы'].map(value => <button type="button" key={value} aria-current={kind === value ? 'page' : undefined} onClick={() => { setKind(value); setPage(0); }}>{value}<span>{value === 'Все источники' ? all.length : all.filter(({ claim }) => category(claim) === value).length}</span></button>)}</nav><label><span className="visually-hidden">Поиск по источникам</span><input type="search" placeholder="Поиск по программам, вузам или темам…" value={query} onChange={event => { setQuery(event.target.value); setPage(0); }}/></label><label><span className="visually-hidden">Статус факта</span><select value={state} onChange={event => { setState(event.target.value); setPage(0); }}><option value="">Все статусы</option>{['Подтверждено','Нужно уточнить','Есть расхождение','Требует обновления'].map(value => <option key={value}>{value}</option>)}</select></label></div>
    <div className="book-sources__scroll"><table className="book-sources__table"><thead><tr><th>Тема / факт</th><th>Источник</th><th>Тип</th><th>Дата чтения</th><th>Статус</th></tr></thead><tbody>{rows.slice(shownPage * 6, shownPage * 6 + 6).map(({ result, claim }) => <Fragment key={`${result.id}:${claim.id}`}><tr className={expanded === `${result.id}:${claim.id}` ? 'is-expanded' : ''}><th scope="row"><button type="button" onClick={() => setExpanded(expanded === `${result.id}:${claim.id}` ? null : `${result.id}:${claim.id}`)} aria-expanded={expanded === `${result.id}:${claim.id}`} aria-controls={`book-source-${result.id}-${claim.id}`}><strong>{requirementName(claim.claim_type)}</strong><small>{result.university} · {result.program}</small></button></th><td><SourceLink url={claim.source_url}/><small>{claim.page_title || host(claim.source_url)}</small></td><td><span className="chip">{category(claim)}</span></td><td>{date(claim.accessed_at)}</td><td><span className={`book-sources__status ${status(claim) === 'Подтверждено' ? 'is-confirmed' : ''}`}>{status(claim) === 'Подтверждено' ? <CheckCircle size={20} weight="fill"/> : <Question size={20} weight="fill"/>}{status(claim)}</span><button type="button" className="book-sources__expand" aria-label={`Раскрыть факт: ${requirementName(claim.claim_type)}`} onClick={() => setExpanded(expanded === `${result.id}:${claim.id}` ? null : `${result.id}:${claim.id}`)}><CaretDown size={18}/></button></td></tr>{expanded === `${result.id}:${claim.id}` && <tr className="book-sources__detail" id={`book-source-${result.id}-${claim.id}`}><td colSpan={5}><div><section><h2>Выдержка из источника</h2><blockquote>{claim.original_text_excerpt || 'Цитата не записана — факт требует проверки.'}</blockquote><SourceLink url={claim.source_url}/></section><section><h2>Программа / финансирование</h2><p>{claim.program || 'Программа в факте не указана'}</p><h2>Раздел на сайте</h2><p>{claim.relevant_section || 'Раздел не записан'}</p><p>{claim.intake || claim.academic_year || 'Период применимости не указан'}</p>{claim.notes && <p>{claim.notes}</p>}<small>{claim.official_domain ? 'Официальный домен' : 'Официальность домена не подтверждена'} · {claim.source_specificity}</small></section></div></td></tr>}</Fragment>)}</tbody></table>{!rows.length && <p className="book-sources__empty">По выбранным фильтрам фактов нет. Попробуй изменить поиск.</p>}</div>
    {pages > 1 && <nav className="book-pagination" aria-label="Страницы фактов"><button className="btn btn--sm" type="button" disabled={shownPage === 0} onClick={() => setPage(shownPage - 1)}>Назад</button><span>{shownPage + 1} / {pages}</span><button className="btn btn--sm" type="button" disabled={shownPage + 1 >= pages} onClick={() => setPage(shownPage + 1)}>Дальше</button></nav>}
    <details className="book-sources__questions"><summary>Расхождения ({conflicts.length}) и открытые вопросы ({questions.length})</summary>{conflicts.map(({ result, conflict }, index) => <article key={`c-${index}`}><h2>{result.university} · {conflict.subject}</h2>{conflict.values.map((value, valueIndex) => <p key={valueIndex}>{String(value)} · {conflict.claim_ids[valueIndex] === conflict.preferred_claim_id ? 'Более конкретный источник' : 'Альтернативный источник'}<SourceLink url={conflict.source_urls[valueIndex] ?? ''}/></p>)}<p>{conflict.resolution_rule}</p><blockquote>{conflict.question_for_admissions}</blockquote></article>)}{questions.map(({ result, question }, index) => <article key={`q-${index}`}><h2>{question.question}</h2><p>{result.university} · {question.why_it_matters}</p></article>)}</details>
  </div>;
}

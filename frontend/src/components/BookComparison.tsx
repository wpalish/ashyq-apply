import { useState } from 'react';
import type { ProgramResult } from '@/types';
import { date, money } from '@/lib/format';
import { programmeLanguage } from '@/lib/bookPresentation';
import { BookLogo } from './BookUI';
import { SourceLink } from './primitives';

export function BookComparison({ results, onRemove, onClear, onAdd }: {
  results: ProgramResult[]; onRemove: (id: string) => void; onClear: () => void;
  onAdd?: (result: ProgramResult) => Promise<void>;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState('');
  const add = async (result: ProgramResult) => {
    setBusy(result.id); setError('');
    try { await onAdd?.(result); }
    catch (failure) { setError(failure instanceof Error ? failure.message : String(failure)); }
    finally { setBusy(null); }
  };
  const rows = [
    { name: 'Статус соответствия', read: (result: ProgramResult) => result.eligibility === 'MET' ? 'Проверенные требования выполнены' : result.eligibility === 'GAP' ? 'Есть несоответствие требованию' : 'Нужна проверка' },
    { name: 'Требования', read: (result: ProgramResult) => `${result.requirement_checks.length} проверок · ${result.unresolved.length} открытых вопросов` },
    { name: 'Язык обучения', read: (result: ProgramResult) => programmeLanguage(result) || 'Не подтверждён' },
    { name: 'Финансирование', read: (result: ProgramResult) => result.scholarships.length ? `${result.scholarships.length} вариантов — проверь условия` : 'Данные не подтверждены' },
    { name: 'Покрываемые расходы', read: (result: ProgramResult) => result.funding_gap?.confirmed_aid ? money(result.funding_gap.confirmed_aid) : 'Неизвестно' },
    { name: 'Оставшиеся расходы', read: (result: ProgramResult) => result.funding_gap?.computable && result.funding_gap.gap ? money(result.funding_gap.gap) : 'Неизвестно' },
    { name: 'Ближайшие даты', read: (result: ProgramResult) => result.admission_deadline ? `${date(result.admission_deadline)} · ${result.admission_deadline_timezone || 'Часовой пояс не указан'}` : 'Даты не указаны' },
  ];
  return <section className="book-comparison" data-count={results.length} aria-label="Compare selected programmes">
    {results.length>2&&<p className="book-comparison__scroll-hint">Три программы: таблицу можно прокрутить горизонтально.</p>}
    <div className="book-comparison__scroll" tabIndex={0} role="region" aria-label="Таблица сравнения программ"><table><thead><tr><th scope="col">Параметр</th>{results.map(result => <th scope="col" key={result.id}><div className="book-comparison__identity"><BookLogo university={result.university}/><div><strong>{result.university}</strong><p>{result.program}</p><small>{result.city}, {result.country}</small></div></div></th>)}</tr></thead><tbody>
      {rows.map(row => <tr key={row.name}><th scope="row">{row.name}</th>{results.map(result => <td key={result.id}><span className="book-comparison__value">{row.read(result)}</span></td>)}</tr>)}
      <tr><th scope="row">Источник информации</th>{results.map(result => <td key={result.id}>{result.program_url ? <SourceLink url={result.program_url}/> : 'Источник не записан'}<small>Последняя проверка: {result.last_verified ? date(result.last_verified) : 'Не указана'}</small></td>)}</tr>
      <tr><th scope="row">Твой выбор</th>{results.map(result => <td key={result.id}><div className="book-comparison__actions">{onAdd && <button className="btn btn--sm" type="button" disabled={Boolean(busy) || result.user_decision === 'approved'} onClick={() => void add(result)}>{busy === result.id ? 'Сохраняем…' : result.user_decision === 'approved' ? 'В твоём плане' : 'Добавить в план'}</button>}<button className="book-text-action" type="button" onClick={() => onRemove(result.id)}>Убрать из сравнения</button></div></td>)}</tr>
    </tbody></table></div>{error && <p role="alert">{error}</p>}<footer><p>Сравнение опирается на собранные источники. Неизвестное не означает отказ или отсутствие стипендий.</p><button type="button" className="btn" onClick={onClear}>Очистить сравнение</button></footer>
  </section>;
}

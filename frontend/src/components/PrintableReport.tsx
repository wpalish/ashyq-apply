import { BookExportControls } from './BookExportControls';
import { useTranslation } from '@/lib/useTranslation';
import { useState } from 'react';
import type { ProgramResult } from '@/types';
import { Panel, SourceLink, StatusChip } from './primitives';
import { date, eligibilityTone, money } from '@/lib/format';

/** A local print view of the currently loaded snapshot, never a new assessment. */
export function PrintableReport({ results, name, demo, onCSV }: { results: ProgramResult[]; name?: string; demo: boolean; onCSV?:()=>void }) {
  const {locale}=useTranslation(); const ru=locale!=='en';
  const [format,setFormat]=useState<'pdf'|'csv'>('pdf');
  const [scope, setScope] = useState('saved');
  const [includeName, setIncludeName] = useState(false);
  const [open, setOpen] = useState(false);
  const [preparedAt, setPreparedAt] = useState('');
  const selected = scope === 'all' ? results : results.filter(result => ['approved', 'maybe'].includes(result.user_decision));
  return <>
    <div className="print-controls">{ru?<BookExportControls count={selected.length} names={selected.map(item=>item.university)} scope={scope} setScope={value=>{setScope(value);setOpen(false);}} includeName={includeName} setIncludeName={value=>{setIncludeName(value);setOpen(false);}} hasName={Boolean(name)} format={format} setFormat={setFormat} onCSV={onCSV} disabled={format==='pdf'?!selected.length && !(includeName && name):!onCSV} onPreview={()=>{setPreparedAt(new Date().toLocaleString());setOpen(true);}}/>:<Panel title="Printable report" hint="Preview your loaded findings, then use the print dialog to print or save as PDF. No report is published or sent automatically.">
      <div className="stack"><label className="field"><span className="field__label">Programmes to include</span><select value={scope} onChange={event => { setScope(event.target.value); setOpen(false); }}><option value="saved">Saved programmes</option><option value="all">All research findings</option></select></label>
        <label className="row small"><input type="checkbox" disabled={!name} checked={includeName} onChange={event => { setIncludeName(event.target.checked); setOpen(false); }} />Include applicant display name</label>
        <p className="small muted">{selected.length} programmes selected. Grades, budget and private files are excluded.</p>
        <button className="btn btn--primary" disabled={!selected.length && !(includeName && name)} onClick={() => { setPreparedAt(new Date().toLocaleString()); setOpen(true); }}>Preview printable report</button>
      </div>
    </Panel>}</div>
    {open && <article className="print-report panel" aria-label={ru?'Предпросмотр отчёта':'Printable report preview'}>
      <header><span className="landing__brand"><img src="/brand/unimatch-orbit.svg" alt="" />unimatch</span><h2>{ru?'Твой отчёт по поступлению':'Your study report'}</h2><p className="small muted">{ru?'Подготовлен на этом устройстве:':'Prepared on this device:'} {preparedAt}</p>{includeName && name && <p>{name}</p>}
        <p className="small">{demo ? ru?'Синтетические демонстрационные результаты. Это не подтверждённые требования университетов.':'Synthetic demonstration findings. These are not verified university requirements.' : ru?'Сохранённый снимок исследования, а не новая проверка и не прогноз поступления.':'A saved research snapshot, not a new verification or a prediction of admission.'}</p>
        <p className="small">{ru?'Неизвестные данные остаются неизвестными. Выбор программы не означает поступление или поданную заявку.':'Unknowns remain unknown. Choosing a programme does not mean an admission offer or a completed application.'}</p>
      </header>
      <div className="row print-report__actions"><button className="btn btn--primary" onClick={() => window.print()}>{ru?'Печать / Сохранить PDF':'Print / Save as PDF'}</button><button className="btn" onClick={() => setOpen(false)}>{ru?'Закрыть предпросмотр':'Close report preview'}</button></div>
      {selected.map(result => <section className="print-report__programme" key={result.id}>
        <h3>{result.university}</h3><p>{result.program} · {result.city}, {result.country}</p>
        <dl><dt>{ru?'Условия в этом снимке':'Eligibility in this snapshot'}</dt><dd><StatusChip status={result.eligibility} tone={eligibilityTone[result.eligibility]} /></dd><dt>{ru?'Непокрытые расходы за год':'Remaining cost per year'}</dt><dd>{result.funding_gap?.computable && result.funding_gap.gap ? money(result.funding_gap.gap) : ru?'Недостаточно сопоставимых данных':'Not enough comparable data'}</dd><dt>{ru?'Дата подачи в снимке':'Admission date recorded'}</dt><dd>{result.admission_deadline ? `${date(result.admission_deadline)} · ${result.admission_deadline_timezone ?? 'timezone not confirmed'}` : 'Not confirmed'}</dd></dl>
        <p className="small">{result.conflicts.length} conflicts · {result.unresolved.length} open questions</p>
        {result.unresolved.length > 0 && <ul className="small">{result.unresolved.map((question,index) => <li key={index}>{question.question}</li>)}</ul>}
        <h4>{ru?'Записанные источники':'Recorded sources'}</h4>{!result.source_urls.length ? <p className="small muted">No source URL recorded.</p> : <ul>{result.source_urls.map(url => <li key={url}><SourceLink url={url} /></li>)}</ul>}
      </section>)}
    </article>}
  </>;
}

import { useMemo, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, CalendarBlank, DownloadSimple, ShareNetwork } from '@phosphor-icons/react';
import type { ScreenId } from '@/App';
import { useStore } from '@/lib/store';
import { useTranslation } from '@/lib/useTranslation';
import { BookToday } from '@/components/BookToday';
import { BookCalendar } from '@/components/BookCalendar';
import { bookTaskView } from '@/lib/bookPlanPresentation';
import { useAdmissionsToday } from '@/lib/useAdmissionsToday';
import { AdmissionsTodayPanel } from '@/components/AdmissionsTodayPanel';
import { ApplicationsPanel } from './ApplicationsPanel';
import { Empty, Notice, Panel } from '@/components/primitives';
import { api } from '@/api/client';

type Navigate = { onNavigate: (screen: ScreenId) => void };
function Heading({ title, children }: { title: string; children: string }) {
  return <header className="screen__head"><h1 className="screen__title">{title}</h1><p className="screen__lede">{children}</p></header>;
}
export function TodayScreen({ onNavigate }: Navigate) {
  const { savedProfile } = useStore(); const { locale }=useTranslation();
  if(locale!=='en'&&savedProfile) return <BookToday/>;
  return <div className="stack stack--loose"><Heading title="Today">A clear next step, based on your saved plan. Optional study stays separate from admissions tasks.</Heading>
    {savedProfile ? <AdmissionsTodayPanel /> : <Panel><Empty title="Your day starts with your profile">Save an applicant case to keep your tasks, documents and deadlines together.</Empty><button className="btn btn--primary" onClick={() => onNavigate('profile')}>Create profile</button></Panel>}
    <div className="row"><button className="btn" onClick={() => onNavigate('calendar')}><CalendarBlank size={18} />Open calendar</button><button className="btn btn--ghost" onClick={() => onNavigate('approved')}>View full plan</button></div>
  </div>;
}
export function ApplicationsScreen({ onNavigate }: Navigate) {
  const { savedProfile } = useStore();
  return <div className="stack stack--loose"><Heading title="Your applications">Track your own progress and open official application portals. A recorded status is your declaration, not a university confirmation.</Heading>
    {savedProfile ? <ApplicationsPanel /> : <Panel><Empty title="No applicant case yet">Save a profile before adding an application.</Empty><button className="btn btn--primary" onClick={() => onNavigate('profile')}>Create profile</button></Panel>}
  </div>;
}
type CalendarEntry = { id: string; day: string; title: string; context: string; type: 'source' | 'personal'; zone: string | null; href?: string|null };
const dayKey = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
export function CalendarScreen() {
  const { run, results } = useStore(); const { locale }=useTranslation();
  const today = useAdmissionsToday();
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [selected, setSelected] = useState(() => dayKey(new Date()));
  const entries = useMemo(() => {
    const out: CalendarEntry[] = [];
    for (const result of results) {
      if(locale!=='en'&&!['approved','maybe'].includes(result.user_decision))continue;
      if (result.admission_deadline) out.push({ id: result.id, day: result.admission_deadline.slice(0, 10), title: locale==='en'?'Application deadline':'Дедлайн подачи', context: `${result.university} · ${result.program}`, type: 'source', zone: result.admission_deadline_timezone ?? null });
      for (const award of result.scholarships) if (award.deadline) out.push({ id: `${result.id}:${award.name}`, day: award.deadline.slice(0, 10), title: award.name, context: result.university, type: 'source', zone: award.deadline_timezone ?? null });
    }
    if (today.value) {
      const projection = today.value;
      const cards = [...projection.overdue_personal, ...projection.today_personal, ...projection.today_study, ...projection.future];
      const seen = new Set<string>();
      for (const card of cards) {
        if (!card.date.local_date || seen.has(card.id)) continue;
        seen.add(card.id);
        const name = card.target?.kind === 'application' ? projection.application_summaries.find(app => app.id === card.target?.id)?.label : null;
        out.push({ id: `personal:${card.id}`, day: card.date.local_date, title: name || (card.reason === 'accepted_study_action' ? (locale==='en'?'Optional study':'Дополнительная подготовка') : card.reason === 'personal_document_action' ? (locale==='en'?'Document task':'Задача по документам') : (locale==='en'?'Application task':'Задача по заявке')), context: locale==='en'?'Your plan · applicant-entered date':'Твой план · личная дата', type: 'personal', zone: card.date.timezone, href:bookTaskView(card,projection,null).href });
      }
    }
    return out.sort((a, b) => a.day.localeCompare(b.day));
  }, [results, today.value, locale]);
  const offset = (month.getDay() + 6) % 7;
  const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const activeEntries = entries.filter(entry => entry.day === selected);
  const shift = (direction: number) => { const next = new Date(month.getFullYear(), month.getMonth() + direction, 1); setMonth(next); setSelected(dayKey(next)); };
  if(locale!=='en') return <BookCalendar month={month} selected={selected} entries={entries} onSelect={setSelected} onShift={shift} onToday={()=>{const now=new Date();setMonth(new Date(now.getFullYear(),now.getMonth(),1));setSelected(dayKey(now));}} error={today.error} hasPrevious={Boolean(today.value)} onRefresh={()=>void today.refresh()} exportUrl={run&&entries.some(entry=>entry.type==='source')?api.deadlinesUrl(run.id):null}/>;
  return <div className="stack stack--loose"><Heading title="Deadline calendar">Official source dates and your personal reminders, shown separately. Dates without a timezone do not establish an exact closing time.</Heading>
    {today.error && <Notice kind="warn">Personal tasks could not be refreshed. {today.value ? 'Last confirmed tasks remain visible.' : 'The calendar may be incomplete.'}<button className="btn btn--sm" onClick={() => void today.refresh()}>Retry</button></Notice>}
    <div className="calendar-layout"><section className="panel calendar" aria-label="Calendar">
      <div className="calendar__header"><button className="btn btn--ghost" aria-label="Previous month" onClick={() => shift(-1)}><ArrowLeft size={20} /></button><h2 aria-live="polite">{month.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</h2><button className="btn btn--ghost" aria-label="Next month" onClick={() => shift(1)}><ArrowRight size={20} /></button></div>
      <div className="calendar__grid">{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => <span className="calendar__weekday" key={day}>{day}</span>)}
        {Array.from({ length: offset }, (_, i) => <span key={`empty-${i}`} />)}
        {Array.from({ length: days }, (_, i) => { const d = new Date(month.getFullYear(), month.getMonth(), i + 1); const key = dayKey(d); const count = entries.filter(entry => entry.day === key).length;
          return <button className="calendar__day" key={key} type="button" aria-pressed={selected === key} aria-current={key === dayKey(new Date()) ? 'date' : undefined} aria-label={`${d.toLocaleDateString(undefined, { dateStyle: 'long' })}${count ? `, ${count} events` : ''}`} onClick={() => setSelected(key)}><span>{i + 1}</span>{count > 0 && <span className="calendar__event-dot" aria-hidden="true" />}</button>;
        })}
      </div><div className="calendar__legend"><span><i />Source deadline</span><span>Your personal plan is also included</span></div>
      <button className="btn btn--ghost" onClick={() => { const now = new Date(); setMonth(new Date(now.getFullYear(), now.getMonth(), 1)); setSelected(dayKey(now)); }}>Jump to today</button>
    </section><section className="panel calendar-agenda" aria-label="Selected date"><h2>{new Date(`${selected}T12:00:00`).toLocaleDateString(undefined, { dateStyle: 'long' })}</h2>
      {activeEntries.length === 0 ? <Empty title="No dated tasks here">Choose another day, or add a personal task in Documents or Applications.</Empty> : <ul className="calendar-agenda__items">{activeEntries.map(entry => <li key={entry.id}><span className={`chip chip--${entry.type === 'source' ? 'info' : 'accent'}`}>{entry.type === 'source' ? 'From research' : 'Personal plan'}</span><h3>{entry.title}</h3><p className="small muted">{entry.context}</p><p className="xs muted">{entry.zone ?? 'Timezone not confirmed'}</p></li>)}</ul>}
      <a className="btn" href="#/documents">Add document task</a>
    </section></div>
    <Panel title="All known dates"><p className="small muted">A missing date means it has not been confirmed. It does not mean applications are open.</p>
      {entries.length === 0 ? <Empty title="No confirmed dates yet">Add a personal task or research a programme to build your calendar.</Empty> : <ul className="calendar-date-list">{entries.map(entry => <li key={entry.id}><button className="btn btn--ghost" onClick={() => { const d = new Date(`${entry.day}T12:00:00`); setMonth(new Date(d.getFullYear(), d.getMonth(), 1)); setSelected(entry.day); }}>{entry.day}</button><div><strong>{entry.title}</strong><p className="small muted">{entry.context}</p></div><span className="chip">{entry.type === 'source' ? 'Source date' : 'Personal'}</span></li>)}</ul>}
      {run && entries.some(entry => entry.type === 'source') && <a className="btn" href={api.deadlinesUrl(run.id)} download>Download source dates (.ics)</a>}
    </Panel>
  </div>;
}

/** User-controlled, local sharing. Never creates a public profile link or sends applicant data. */
export function ShareScreen({ onNavigate }: Navigate) {
  const { results, savedProfile } = useStore();
  const programmes = results.filter(result => ['approved', 'maybe'].includes(result.user_decision));
  const [includeName, setIncludeName] = useState(false);
  const [includeProgrammes, setIncludeProgrammes] = useState(true);
  const [message, setMessage] = useState('');
  const canvas = useRef<HTMLCanvasElement>(null);
  const text = ['My study route · Unimatch', ...(includeName && savedProfile ? [savedProfile.display_name] : []), ...(includeProgrammes ? programmes.map(item => `${item.university} · ${item.program} · ${item.country}`) : []), 'Exploring possibilities. Selection is not an admission offer.'].join('\n');
  const download = () => {
    const element = canvas.current; if (!element) return;
    const ctx = element.getContext('2d'); if (!ctx) { setMessage('Image export is unavailable in this browser. Copy the text instead.'); return; }
    ctx.font = '400 30px Inter, sans-serif';
    const lines: (string | null)[] = [];
    for (const line of text.split('\n').slice(1)) {
      let current = '';
      for (const word of line.split(' ')) { const next = `${current} ${word}`.trim(); if (ctx.measureText(next).width > 1050) { lines.push(current); current = word; } else current = next; }
      lines.push(current, null);
    }
    const height = Math.max(760, 500 + lines.reduce((total, line) => total + (line === null ? 32 : 46), 0));
    if (height > 16000) { setMessage('This route is too long for one image. Copy the complete route text instead.'); return; }
    element.height = height;
    ctx.fillStyle = '#f5f9ff'; ctx.fillRect(0, 0, 1200, height);
    ctx.strokeStyle = '#1454ff'; ctx.lineWidth = 7; ctx.beginPath(); ctx.arc(82, 68, 18, -.9, 4.9); ctx.stroke();
    ctx.fillStyle = '#1454ff'; ctx.beginPath(); ctx.arc(95, 53, 5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#0b1739'; ctx.font = '700 48px Inter, sans-serif'; ctx.fillText('unimatch', 64, 164);
    ctx.font = '700 64px Inter, sans-serif'; ctx.fillText('My study route', 64, 300);
    ctx.font = '400 30px Inter, sans-serif';
    let y = 400;
    for (const line of lines) { if (line !== null) ctx.fillText(line, 64, y); y += line === null ? 32 : 46; }
    element.toBlob(blob => { if (!blob) { setMessage('Image export failed. Copy the text instead.'); return; } const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = 'unimatch-study-route.png'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); setMessage('Image prepared for download.'); }, 'image/png');
  };
  return <div className="stack stack--loose"><Heading title="Share your route">Choose what to include. Your card is created on this device and is never published automatically.</Heading>
    <div className="share-layout"><article className="route-card" aria-label="Share preview"><ShareNetwork size={32} /><span>unimatch</span><h2>My study route</h2>{includeName && savedProfile && <p>{savedProfile.display_name}</p>}{includeProgrammes && <ul>{programmes.map(item => <li key={item.id}><strong>{item.university}</strong><span>{item.program} · {item.country}</span></li>)}</ul>}{!programmes.length && <p>Select a programme to add your destinations.</p>}<p className="route-card__note">Exploring possibilities. Selection is not an admission offer.</p></article>
      <Panel title="What appears on your card"><div className="stack"><label className="row"><input type="checkbox" checked={includeName} disabled={!savedProfile} onChange={event => setIncludeName(event.target.checked)} />Include my name</label><label className="row"><input type="checkbox" checked={includeProgrammes} onChange={event => setIncludeProgrammes(event.target.checked)} />Selected programmes and countries</label><p className="small muted">Grades, budget, private documents, email and case identifiers are excluded.</p><button className="btn btn--primary" onClick={download}><DownloadSimple size={18} />Download card (.png)</button><button className="btn" onClick={async () => { try { await navigator.clipboard.writeText(text); setMessage('Route text copied.'); } catch { setMessage('Clipboard is unavailable. Select and copy the preview text below.'); } }}>Copy route text</button><button className="btn btn--ghost" onClick={() => onNavigate('shortlist')}>Choose programmes</button><p role="status">{message}</p><details><summary>Text preview</summary><pre className="share-text">{text}</pre></details></div></Panel>
    </div><canvas ref={canvas} width={1200} height={1500} hidden />
  </div>;
}

/**
 * Screen 08 — Documents and deadlines.
 *
 * Grouped by who has to act, and ordered by lead time rather than by deadline.
 * A reference letter with a thirty-day lead time is the thing that actually
 * sinks an application, not the form you can fill in on the last evening.
 *
 * Round 7's documents screen: each programme says how much of its list is
 * ready and how much is still missing, and each document says when to start
 * it - its due date (its own, or the programme's admission deadline) minus
 * the time it takes. "Ready" is the applicant's own tick: the product never
 * uploads or submits anything.
 */

import { useMemo, useState } from 'react';
import { Chip, Empty, Notice, Panel } from '@/components/primitives';
import { calendarDay, daysUntil, startBy } from '@/lib/deadlines';
import { date, dateTime } from '@/lib/format';
import { api } from '@/api/client';
import { useStore } from '@/lib/store';
import type { DocumentItem, ProgramResult } from '@/types';

const OWNER_LABEL: Record<string, string> = {
  applicant: 'You',
  school: 'Your school',
  recommender: 'Your referee',
  third_party: 'A third party (translator, WES/ECE, notary)',
};

const DONE_KEY = 'ashyq.docsDone';

/** Every document on a checklist, once: the four groups split it by who acts. */
function itemsOf(result: ProgramResult): DocumentItem[] {
  const c = result.checklist;
  if (!c) return [];
  return [...c.recommender_actions, ...c.school_actions, ...c.certification_actions, ...c.applicant_actions];
}

function doneKey(result: ProgramResult, item: DocumentItem): string {
  return `${result.id}::${item.name}`;
}

function loadDone(): Record<string, boolean> {
  try {
    return JSON.parse(window.localStorage.getItem(DONE_KEY) ?? '{}');
  } catch {
    return {};
  }
}

export function DocumentsScreen() {
  const { results, run } = useStore();
  const withChecklists = results.filter((r) => r.checklist);
  const [selected, setSelected] = useState<string>(withChecklists[0]?.id ?? '');
  const [done, setDone] = useState<Record<string, boolean>>(loadDone);

  const toggle = (key: string) => {
    setDone((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      try {
        window.localStorage.setItem(DONE_KEY, JSON.stringify(next));
      } catch {
        /* progress ticks are a convenience; storage being unavailable is fine */
      }
      return next;
    });
  };

  const deadlines = useMemo(() => {
    const items: { when: string; what: string; where: string; past: boolean }[] = [];
    const today = new Date().toISOString().slice(0, 10);
    // Every row on the shortlist, not only the ones with a checklist: the
    // panel says "across your shortlist" and a deadline matters whether or not
    // documents have been collected for it yet.
    for (const r of results) {
      if (r.admission_deadline) {
        items.push({
          when: r.admission_deadline,
          what: `Admission application${r.admission_deadline_timezone ? ` (${r.admission_deadline_timezone})` : ''}`,
          where: `${r.university} — ${r.program}`,
          past: r.admission_deadline < today,
        });
      }
      for (const s of r.scholarships) {
        if (s.deadline) {
          items.push({
            when: s.deadline,
            what: `${s.name}${s.deadline_timezone ? ` (${s.deadline_timezone})` : ''}`,
            where: r.university,
            past: s.deadline < today,
          });
        }
      }
    }
    return items.sort((a, b) => a.when.localeCompare(b.when));
  }, [results]);

  if (withChecklists.length === 0) {
    return (
      <Empty title="No checklists yet">
        Approve programmes on the shortlist, then run “Collect documents” from the approved screen.
      </Empty>
    );
  }

  const current = withChecklists.find((r) => r.id === selected) ?? withChecklists[0]!;

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">Documents</p>
        <h1 className="screen__title">What to prepare, and when</h1>
        <p className="screen__lede">
          Ordered by lead time, not by deadline. The items at the top depend on other people, so
          they are the ones that need starting first.
        </p>
      </div>

      <div className="stack stack--loose">
        <div className="doc-progs" role="group" aria-label="Programmes with a document list">
          {withChecklists.map((r) => {
            const items = itemsOf(r);
            const ready = items.filter((d) => done[doneKey(r, d)]).length;
            const on = r.id === current.id;
            return (
              <button
                key={r.id}
                type="button"
                className={`doc-prog${on ? ' is-on' : ''}`}
                aria-pressed={on}
                onClick={() => setSelected(r.id)}
                data-testid={`doc-tab-${r.id}`}
              >
                <span className="doc-prog__uni">{r.university}</span>
                <span className="doc-prog__name">{r.program}</span>
                <span className="doc-prog__meter" aria-hidden="true">
                  <span style={{ width: `${items.length ? (ready / items.length) * 100 : 0}%` }} />
                </span>
                <span className="doc-prog__count">
                  {ready} of {items.length} ready
                  {items.length - ready > 0 && <> · {items.length - ready} still missing</>}
                </span>
              </button>
            );
          })}
        </div>

        <ChecklistFor result={current} done={done} toggle={toggle} />

        <Panel
          title="Every deadline across your shortlist"
          sunken
          actions={
            run && deadlines.length > 0 ? (
              <a
                className="btn btn--sm"
                href={api.deadlinesUrl(run.id)}
                download
                data-testid="download-ics"
              >
                Add to calendar (.ics)
              </a>
            ) : undefined
          }
        >
          <div className="timeline">
            {deadlines.map((d, i) => (
              <div key={i} className={`timeline__item ${d.past ? 'timeline__item--past' : ''}`}>
                <span className="timeline__date">{date(d.when)}</span>
                <div className="timeline__what">
                  <div className="small"><strong>{d.what}</strong></div>
                  <div className="xs muted">{d.where}</div>
                </div>
                {d.past && <span className="timeline__flag"><Chip tone="risk">passed</Chip></span>}
              </div>
            ))}
            {deadlines.length === 0 && <p className="muted small">No dated deadlines were found.</p>}
          </div>
        </Panel>
      </div>
    </>
  );
}

function ChecklistFor({
  result, done, toggle,
}: { result: ProgramResult; done: Record<string, boolean>; toggle: (k: string) => void }) {
  const c = result.checklist!;

  // Longest lead time first, both between groups and inside them. What the
  // screen promises is "start with what depends on other people", and a
  // referee letter at thirty days must not sit below a passport scan.
  const byLeadTime = (items: DocumentItem[]) =>
    [...items].sort((a, b) => (b.lead_time_days ?? 0) - (a.lead_time_days ?? 0));
  const maxLead = (items: DocumentItem[]) =>
    items.reduce((n, d) => Math.max(n, d.lead_time_days ?? 0), 0);

  const groups: [string, DocumentItem[]][] = (
    [
      ['recommender', byLeadTime(c.recommender_actions)],
      ['school', byLeadTime(c.school_actions)],
      ['third_party', byLeadTime(c.certification_actions)],
      ['applicant', byLeadTime(c.applicant_actions)],
    ] as [string, DocumentItem[]][]
  ).sort((a, b) => maxLead(b[1]) - maxLead(a[1]));
  const total = groups.reduce((n, [, items]) => n + items.length, 0);
  const completed = groups.reduce(
    (n, [, items]) => n + items.filter((d) => done[doneKey(result, d)]).length, 0,
  );

  // When to begin each document: its due date - its own, or the programme's
  // admission deadline - minus the time it takes. Nothing is dated when either
  // is unknown, and nothing is dated for a deadline that has already passed.
  const today = new Date();
  const admission = calendarDay(result.admission_deadline);
  const timing = (d: DocumentItem) => {
    const due = calendarDay(d.deadline) ?? admission;
    if (!due || !d.lead_time_days || daysUntil(due, today) < 0) return null;
    const start = startBy(due, d.lead_time_days);
    return { due, start, late: daysUntil(start, today) < 0 };
  };
  const first = groups
    .flatMap(([, items]) => items)
    .filter((d) => !done[doneKey(result, d)])
    .map((d) => ({ d, t: timing(d) }))
    .filter((x): x is { d: DocumentItem; t: NonNullable<ReturnType<typeof timing>> } => x.t !== null)
    .sort((a, b) => a.t.start.localeCompare(b.t.start))[0];

  return (
    <div className="stack">
      <Panel
        title={`${result.university} — ${result.program}`}
        hint={`${completed} of ${total} items ticked off. Generated ${dateTime(c.generated_at)}.`}
        actions={
          <Chip tone={c.completeness === 'official' ? 'ok' : c.completeness === 'partial' ? 'warn' : 'risk'}>
            {c.completeness === 'official' ? 'from official pages'
              : c.completeness === 'partial' ? 'partially read' : 'no official list found'}
          </Chip>
        }
      >
        <div className="meter" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="meter__fill" style={{ width: `${total ? (completed / total) * 100 : 0}%` }} />
        </div>

        {total > 0 && completed === total ? (
          <p className="doc-first" data-testid="doc-first">Everything on this list is ticked off.</p>
        ) : first ? (
          <p className="doc-first" data-testid="doc-first">
            <strong>Start first: {first.d.name}.</strong>{' '}
            {first.t.late
              ? <>It takes about {first.d.lead_time_days} days and is due {date(first.t.due)}, so it needs starting now.</>
              : <>It takes about {first.d.lead_time_days} days: begin by {date(first.t.start)} to have it by {date(first.t.due)}.</>}
          </p>
        ) : null}

        {groups.map(([owner, items]) =>
          items.length === 0 ? null : (
            <div key={owner} className="stack stack--tight" style={{ marginBottom: 'var(--space-5)' }}>
              <h3 style={{ fontSize: 'var(--text-base)' }}>{OWNER_LABEL[owner]}</h3>
              {items.map((d) => {
                const key = doneKey(result, d);
                const t = timing(d);
                return (
                  <label key={key} className={`doc ${done[key] ? 'doc--done' : ''}`}>
                    <input type="checkbox" checked={Boolean(done[key])} onChange={() => toggle(key)} />
                    <div>
                      <div className="doc__name">{d.name}</div>
                      <div className="doc__meta">
                        {[
                          d.purpose === 'scholarship' ? 'for a scholarship' : 'for admission',
                          d.lead_time_days ? `allow ~${d.lead_time_days} day${d.lead_time_days === 1 ? '' : 's'}` : null,
                          d.word_limit ? `max ${d.word_limit} words` : null,
                          d.max_pages ? `max ${d.max_pages} pages` : null,
                          d.max_file_size_mb ? `max ${d.max_file_size_mb} MB` : null,
                          d.format_notes || null,
                          d.needs_translation ? 'certified translation required' : null,
                          d.needs_notarization ? 'notarisation required' : null,
                          d.needs_apostille ? 'apostille required' : null,
                          d.needs_credential_evaluation ? 'credential evaluation required' : null,
                          d.deadline ? `due ${date(d.deadline)}` : null,
                        ].filter(Boolean).join(' · ')}
                      </div>
                      {t && !done[key] && (
                        <div className={`doc__start${t.late ? ' doc__start--late' : ''}`}>
                          {t.late ? 'start now' : `start by ${date(t.start)}`}
                        </div>
                      )}
                      {d.prompt_text && (
                        <p className="xs faint" style={{ margin: '4px 0 0' }}>{d.prompt_text}</p>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          ),
        )}

        {c.unresolved.length > 0 && (
          <div className="stack stack--tight">
            <h3 style={{ fontSize: 'var(--text-base)' }}>Still to confirm</h3>
            {c.unresolved.map((q, i) => (
              <Notice key={i} kind={q.blocking ? 'risk' : 'warn'}>
                <div>
                  <strong>{q.question}</strong>
                  <div className="xs" style={{ marginTop: 3 }}>{q.why_it_matters}</div>
                  {q.suggested_contact && <div className="xs">Ask: {q.suggested_contact}</div>}
                </div>
              </Notice>
            ))}
          </div>
        )}
      </Panel>

      <Notice kind="info">
        <div>
          ASHYQ Apply prepares this list. It does not upload documents, submit an application, sign
          anything on your behalf, or pay a fee. Those steps stay with you.
        </div>
      </Notice>
    </div>
  );
}

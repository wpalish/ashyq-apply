/**
 * Screen 08 — Documents and deadlines.
 *
 * Grouped by who has to act, and ordered by lead time rather than by deadline.
 * A reference letter with a thirty-day lead time is the thing that actually
 * sinks an application, not the form you can fill in on the last evening.
 */

import { PersonalDocumentsPanel } from './PersonalDocumentsPanel';
import { useTranslation } from '@/lib/useTranslation';
import { useMemo, useRef, useState } from 'react';
import { Chip, Empty, Notice, Panel } from '@/components/primitives';
import { date, dateTime } from '@/lib/format';
import { api } from '@/api/client';
import { useStore } from '@/lib/store';
import { applicantStorageKey } from '@/lib/applicantStorage';
import type { DocumentItem, ProgramResult } from '@/types';
import type { ScreenId } from '@/App';

const OWNER_LABEL: Record<string, string> = {
  applicant: 'You',
  school: 'Your school',
  recommender: 'Your referee',
  third_party: 'A third party (translator, WES/ECE, notary)',
};

const DONE_KEY = 'ashyq.docsDone';

function loadDone(): { marks: Record<string, boolean>; invalid: boolean } {
  try {
    const scoped = applicantStorageKey(DONE_KEY);
    if (scoped === null) return { marks: {}, invalid: false };
    const raw = window.localStorage.getItem(scoped);
    if (raw === null) return { marks: {}, invalid: false };
    if (new TextEncoder().encode(raw).length > 256 * 1024) return { marks: {}, invalid: true };
    const value: unknown = JSON.parse(raw);
    if (typeof value !== 'object' || value === null || Array.isArray(value)
      || Object.keys(value).length > 4000) return { marks: {}, invalid: true };
    const marks: Record<string, boolean> = Object.create(null);
    for (const [key, mark] of Object.entries(value)) {
      if (typeof mark !== 'boolean' || Array.from(key).length > 1000) return { marks: {}, invalid: true };
      marks[key] = mark;
    }
    return { marks, invalid: false };
  } catch { return { marks: {}, invalid: true }; }
}

export function DocumentsScreen({ onNavigate }: { onNavigate?: (screen: ScreenId) => void }) {
  const { results, run, savedProfile } = useStore();
  const { t } = useTranslation();
  const withChecklists = results.filter((r) => r.checklist);
  const chosen = results.some((r) => r.user_decision === 'approved' || r.user_decision === 'maybe');
  const activeJob = run?.job_running || run?.job_status === 'queued' || run?.job_status === 'running';
  const needsAttention = run && (run.stale || run.cancelled
    || ['failed', 'dead', 'cancelled'].includes(run.job_status ?? '')
    || (!activeJob && ['failed', 'retryable_failed', 'cancelled'].includes(run.stage)));
  const busy = !needsAttention && activeJob;
  const [selected, setSelected] = useState<string>(withChecklists[0]?.id ?? '');
  const [legacySnapshot] = useState(loadDone);
  const [done, setDone] = useState<Record<string, boolean>>(legacySnapshot.marks);
  const doneStorageKey = useRef(applicantStorageKey(DONE_KEY));

  const toggle = (key: string) => {
    if (legacySnapshot.invalid) return;
    const scoped = applicantStorageKey(DONE_KEY);
    if (scoped === null || scoped !== doneStorageKey.current) return;
    setDone((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      try {
        window.localStorage.setItem(scoped, JSON.stringify(next));
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

  const current = withChecklists.find((r) => r.id === selected) ?? withChecklists[0];

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">Documents & deadlines</p>
        <h1 className="screen__title">Prepare with <span className="find-yellow">confidence.</span></h1>
        <p className="screen__lede">
          Ordered by lead time, not by deadline. The items at the top depend on other people, so
          they are the ones that need starting first.
        </p>
      </div>

      <div className="stack stack--loose">
        {savedProfile ? <PersonalDocumentsPanel /> : <Notice>{t('documents.saveCaseFirst')}</Notice>}
        <Notice>{t('documents.legacyHint')}</Notice>
        {legacySnapshot.invalid && <Notice kind="warn"><span data-testid="legacy-document-storage-invalid">{t('documents.legacyInvalid')}</span></Notice>}
        {(busy || needsAttention) && (
          <Notice kind={needsAttention ? 'warn' : 'info'}>
            <div role="status">
              <strong>{needsAttention ? 'Research needs attention.' : run?.stage === 'document_collection' ? 'Document collection is in progress.' : 'Research is in progress.'}</strong>
              {' '}{needsAttention ? 'Review the stopped stage and source limitations. Existing findings remain available below.' : 'New requirements will appear here when collection finishes. Existing findings remain available below.'}
              {onNavigate && <button className="btn btn--sm" type="button" onClick={() => onNavigate('progress')}>View research progress</button>}
            </div>
          </Notice>
        )}
        {!current && !busy && !needsAttention && (
          <Panel>
            <Empty title="No checklists yet">{chosen ? 'Collect official requirements for your selected programmes from Plan.' : 'Choose a programme in Find, then collect its official requirements from Plan.'}</Empty>
            {onNavigate && <button className="btn btn--primary" type="button" onClick={() => onNavigate(chosen ? 'approved' : 'shortlist')}>{chosen ? 'Open plan' : 'Choose programmes'}</button>}
          </Panel>
        )}

        {results.length > 0 && <details className="documents-deadlines" open={!current}>
          <summary>Calendar and deadlines across your shortlist ({deadlines.length})</summary>
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
                <div>
                  <div className="small"><strong>{d.what}</strong></div>
                  <div className="xs muted">{d.where}</div>
                </div>
                {d.past && <Chip tone="risk">passed</Chip>}
              </div>
            ))}
            {deadlines.length === 0 && <p className="muted small">No dated deadlines were found.</p>}
          </div>
        </Panel>
        </details>}

        {current && <div className="row">
          {withChecklists.map((r) => (
            <button
              key={r.id}
              className="btn btn--sm"
              style={r.id === current.id ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : undefined}
              onClick={() => setSelected(r.id)}
              data-testid={`doc-tab-${r.id}`}
            >
              {r.university}
            </button>
          ))}
        </div>}

        {current && <ChecklistFor result={current} done={done} toggle={toggle} marksInvalid={legacySnapshot.invalid} />}
      </div>
    </>
  );
}

function ChecklistFor({
  result, done, toggle, marksInvalid,
}: { result: ProgramResult; done: Record<string, boolean>; toggle: (k: string) => void; marksInvalid: boolean }) {
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
    (n, [, items]) => n + items.filter((d) => done[`${result.id}::${d.name}`]).length, 0,
  );

  return (
    <div className="stack">
      <Panel
        title={`${result.university} — ${result.program}`}
        hint={`${completed} of ${total} legacy browser marks. Generated ${dateTime(c.generated_at)}.`}
        actions={
          <Chip tone={c.completeness === 'official' ? 'ok' : c.completeness === 'partial' ? 'warn' : 'risk'}>
            {c.completeness === 'official' ? 'from official pages'
              : c.completeness === 'partial' ? 'partially read' : 'official list not confirmed'}
          </Chip>
        }
      >
        <div className="meter" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="meter__fill" style={{ width: `${total ? (completed / total) * 100 : 0}%` }} />
        </div>

        {groups.map(([owner, items]) =>
          items.length === 0 ? null : (
            <div key={owner} className="stack stack--tight" style={{ marginBottom: 'var(--space-5)' }}>
              <h3 style={{ fontSize: 'var(--text-base)' }}>{OWNER_LABEL[owner]}</h3>
              {items.map((d) => {
                const key = `${result.id}::${d.name}`;
                return (
                  <label key={key} className={`doc ${done[key] ? 'doc--done' : ''}`}>
                    <input type="checkbox" disabled={marksInvalid} checked={Boolean(done[key])} onChange={() => toggle(key)} />
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
          Unimatch prepares this list. It does not upload documents, submit an application, sign
          anything on your behalf, or pay a fee. Those steps stay with you.
        </div>
      </Notice>
    </div>
  );
}

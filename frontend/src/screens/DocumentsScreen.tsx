/**
 * Screen 08 — Documents and deadlines.
 *
 * Grouped by who has to act, and ordered by lead time rather than by deadline.
 * A reference letter with a thirty-day lead time is the thing that actually
 * sinks an application, not the form you can fill in on the last evening.
 *
 * Every fixed label goes through `t()` (I18N-2). A document name from our
 * 18-kind vocabulary and the sentences the backend writes into `format_notes`
 * (optional, conditional, possibly outdated) come with keys and are said in
 * the reader's language (I18N-3); anything unkeyed — a prompt, a name a live
 * page used, a condition as the university wrote it — stays as published.
 */

import { useMemo, useState } from 'react';
import { Chip, Empty, Notice, Panel } from '@/components/primitives';
import { date, dateTime } from '@/lib/format';
import type { MessageKey } from '@/lib/i18n';
import { localize } from '@/lib/messages';
import { api } from '@/api/client';
import { useStore } from '@/lib/store';
import { rich, useTranslation } from '@/lib/useTranslation';
import type { DocumentItem, ProgramResult } from '@/types';

const OWNER_LABEL: Record<string, MessageKey> = {
  applicant: 'detail.docs.step.applicant',
  school: 'detail.docs.owner.school',
  recommender: 'detail.docs.owner.recommender',
  third_party: 'documents.owner.thirdParty',
};

const DONE_KEY = 'ashyq.docsDone';

function loadDone(): Record<string, boolean> {
  try {
    return JSON.parse(window.localStorage.getItem(DONE_KEY) ?? '{}');
  } catch {
    return {};
  }
}

export function DocumentsScreen() {
  const { t, tf } = useTranslation();
  const { results, run, capabilities } = useStore();
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
    const items: { when: string; what: string; where: string; past: boolean; admission: boolean }[] = [];
    const today = new Date().toISOString().slice(0, 10);
    // Every row on the shortlist, not only the ones with a checklist: the
    // panel says "across your shortlist" and a deadline matters whether or not
    // documents have been collected for it yet.
    for (const r of results) {
      if (r.admission_deadline) {
        items.push({
          when: r.admission_deadline,
          what: r.admission_deadline_timezone ? ` (${r.admission_deadline_timezone})` : '',
          where: `${r.university} — ${r.program}`,
          past: r.admission_deadline < today,
          admission: true,
        });
      }
      for (const s of r.scholarships) {
        if (s.deadline) {
          items.push({
            when: s.deadline,
            what: `${s.name}${s.deadline_timezone ? ` (${s.deadline_timezone})` : ''}`,
            where: r.university,
            past: s.deadline < today,
            admission: false,
          });
        }
      }
    }
    return items.sort((a, b) => a.when.localeCompare(b.when));
  }, [results]);

  const title = rich(t('documents.title'), {
    accent: <span className="find-yellow">{t('documents.titleAccent')}</span>,
  });

  if (withChecklists.length === 0) {
    return (
      <div className="find-page">
        <div className="screen__head">
          <p className="screen__eyebrow">{t('documents.eyebrow').toLocaleUpperCase()}</p>
          <h1 className="screen__title">{title}</h1>
          <p className="screen__lede">{t('documents.emptyLede')}</p>
        </div>
        <div className="find-empty"><Empty title={t('documents.emptyTitle')}>{t('documents.emptyBody')}</Empty></div>
      </div>
    );
  }

  const current = withChecklists.find((r) => r.id === selected) ?? withChecklists[0]!;

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">{t('documents.eyebrow')}</p>
        <h1 className="screen__title">{title}</h1>
        <p className="screen__lede">{t('documents.lede')}</p>
      </div>

      <div className="stack stack--loose">
        <details className="documents-deadlines">
          <summary>{tf('documents.calendarSummary', { n: deadlines.length })}</summary>
        <Panel
          title={t('documents.calendarTitle')}
          sunken
          actions={
            run && deadlines.length > 0 ? (
              <a
                className="btn btn--sm"
                href={api.deadlinesUrl(run.id)}
                download
                data-testid="download-ics"
              >
                {t('documents.addToCalendar')}
              </a>
            ) : undefined
          }
        >
          <div className="timeline">
            {deadlines.map((d, i) => (
              <div key={i} className={`timeline__item ${d.past ? 'timeline__item--past' : ''}`}>
                <span className="timeline__date">{date(d.when)}</span>
                <div>
                  <div className="small">
                    <strong>{d.admission ? `${t('documents.admissionApplication')}${d.what}` : d.what}</strong>
                  </div>
                  <div className="xs muted">{d.where}</div>
                </div>
                {d.past && <Chip tone="risk">{t('documents.passed')}</Chip>}
              </div>
            ))}
            {deadlines.length === 0 && <p className="muted small">{t('documents.noDeadlines')}</p>}
          </div>
        </Panel>
        </details>

        <div className="row">
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
        </div>

        <ChecklistFor result={current} done={done} toggle={toggle} kb={capabilities?.knowledge_mode === 'kb'} />
      </div>
    </>
  );
}

/** What a document asks for beyond its name, in the reader's language. */
type Say = Pick<ReturnType<typeof useTranslation>, 't' | 'tf' | 'tn'>;

/**
 * `format_notes` sentence by sentence, each in the reader's language when the
 * backend keyed it. The cut is the backend's (`message_keys._NOTE_END`: a full
 * stop, spaces, a capital), so the n-th sentence meets the n-th key; when the
 * counts differ the served English is shown whole.
 */
function localNotes(d: Pick<DocumentItem, 'format_notes' | 'notes_messages'>): string {
  const notes = d.format_notes.trim();
  const keyed = d.notes_messages;
  if (!notes || !keyed) return notes;
  const sentences = notes.split(/(?<=\.) +(?=[A-Z])/);
  if (sentences.length !== keyed.length) return notes;
  return sentences.map((sentence, i) => localize(keyed[i], sentence)).join(' ');
}

function documentMeta(d: DocumentItem, { t, tf, tn }: Say): string {
  return [
    d.purpose === 'scholarship' ? t('documents.forScholarship') : t('documents.forAdmission'),
    d.lead_time_days ? tn('detail.docs.leadTime', d.lead_time_days) : null,
    d.word_limit ? tf('documents.maxWords', { n: d.word_limit }) : null,
    d.max_pages ? tf('documents.maxPages', { n: d.max_pages }) : null,
    d.max_file_size_mb ? tf('documents.maxSize', { n: d.max_file_size_mb }) : null,
    localNotes(d) || null,
    d.needs_translation ? t('documents.translation') : null,
    d.needs_notarization ? t('documents.notarisation') : null,
    d.needs_apostille ? t('documents.apostille') : null,
    d.needs_credential_evaluation ? t('documents.credentialEvaluation') : null,
    d.deadline ? tf('documents.due', { date: date(d.deadline) }) : null,
  ].filter(Boolean).join(' · ');
}

function completenessKey(kb: boolean, completeness: string): MessageKey {
  if (kb) return `detail.docs.kb.${completeness}` as MessageKey;
  return `documents.completeness.${completeness}` as MessageKey;
}

function ChecklistFor({
  result, done, toggle, kb,
}: { result: ProgramResult; done: Record<string, boolean>; toggle: (k: string) => void; kb: boolean }) {
  const { t, tf, tn } = useTranslation();
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
        hint={tf('documents.ticked', { done: completed, total, when: dateTime(c.generated_at) })}
        actions={
          <Chip tone={c.completeness === 'official' ? 'ok' : c.completeness === 'partial' ? 'warn' : 'risk'}>
            {t(completenessKey(kb, c.completeness))}
          </Chip>
        }
      >
        <div className="meter" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="meter__fill" style={{ width: `${total ? (completed / total) * 100 : 0}%` }} />
        </div>

        {groups.map(([owner, items]) =>
          items.length === 0 ? null : (
            <div key={owner} className="stack stack--tight" style={{ marginBottom: 'var(--space-5)' }}>
              <h3 style={{ fontSize: 'var(--text-base)' }}>{OWNER_LABEL[owner] ? t(OWNER_LABEL[owner]) : owner}</h3>
              {items.map((d) => {
                const key = `${result.id}::${d.name}`;
                return (
                  <label key={key} className={`doc ${done[key] ? 'doc--done' : ''}`}>
                    <input type="checkbox" checked={Boolean(done[key])} onChange={() => toggle(key)} />
                    <div>
                      <div className="doc__name">{localize(d.name_message, d.name)}</div>
                      <div className="doc__meta">{documentMeta(d, { t, tf, tn })}</div>
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
            <h3 style={{ fontSize: 'var(--text-base)' }}>{t('documents.stillToConfirm')}</h3>
            {c.unresolved.map((q, i) => (
              <Notice key={i} kind={q.blocking ? 'risk' : 'warn'}>
                <div>
                  <strong>{localize(q.question_message, q.question)}</strong>
                  <div className="xs" style={{ marginTop: 3 }}>{localize(q.why_message, q.why_it_matters)}</div>
                  {q.suggested_contact && (
                    <div className="xs">{tf('documents.ask', { contact: q.suggested_contact })}</div>
                  )}
                </div>
              </Notice>
            ))}
          </div>
        )}
      </Panel>

      <Notice kind="info">
        <div>{t('documents.notice')}</div>
      </Notice>
    </div>
  );
}

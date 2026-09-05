/**
 * The moderation queue.
 *
 * Reachable only by an account the deployment names in its settings, and the
 * screen says so rather than pretending it does not exist: a person who is not
 * a moderator gets an explanation, not a blank page.
 *
 * The queue is oldest-first, because it is work rather than news, and each
 * report carries the words the content had when it was reported — the content
 * itself is often gone by the time anyone looks, either removed or deleted by
 * its own author.
 */

import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { Empty, Loading, Notice, Panel } from '@/components/primitives';
import { when } from '@/components/social';
import { useTranslation } from '@/lib/useTranslation';
import type { ReportStatus, ReportView } from '@/types';

const TABS: ReportStatus[] = ['open', 'actioned', 'dismissed'];

const SUBJECT_KEY = {
  post: 'moderation.subjectPost',
  reply: 'moderation.subjectReply',
  message: 'moderation.subjectMessage',
  profile: 'moderation.subjectProfile',
} as const;

function Report({ report, onResolved }: { report: ReportView; onResolved: () => void }) {
  const { t } = useTranslation();
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const moment = when(report.created_at);

  const resolve = async (action: 'remove' | 'dismiss') => {
    setBusy(true);
    try {
      await api.resolveReport(report.id, action, note.trim());
      onResolved();
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : 'Could not resolve that.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="report-row" data-testid={`report-${report.id}`}>
      <div className="row row--tight">
        <strong className="small">{t(`report.${report.reason}` as never)}</strong>
        <span className="xs faint">
          {t('moderation.about')} — {t(SUBJECT_KEY[report.subject_type])}
        </span>
        <time className="xs faint" dateTime={report.created_at} title={moment.exact}>
          {moment.label}
        </time>
      </div>

      <p className="report-row__excerpt">
        {report.excerpt || <span className="faint">{t('moderation.gone')}</span>}
      </p>

      <div className="xs muted">
        {t('moderation.reportedBy')}: {report.reporter.display_name}
        {report.subject_author && <> · {report.subject_author.display_name}</>}
      </div>
      {report.note && <p className="small">{report.note}</p>}

      {error && <Notice kind="risk">{error}</Notice>}

      {report.status === 'open' ? (
        <div className="stack stack--tight">
          <div className="field">
            <label className="field__label xs" htmlFor={`resolution-${report.id}`}>
              {t('moderation.resolutionNote')}
            </label>
            <input
              id={`resolution-${report.id}`}
              value={note}
              maxLength={500}
              onChange={(event) => setNote(event.target.value)}
            />
          </div>
          <div className="row row--tight">
            <button
              className="btn btn--sm btn--danger"
              type="button"
              disabled={busy}
              onClick={() => resolve('remove')}
            >
              {t('moderation.remove')}
            </button>
            <button
              className="btn btn--sm"
              type="button"
              disabled={busy}
              onClick={() => resolve('dismiss')}
            >
              {t('moderation.dismiss')}
            </button>
          </div>
        </div>
      ) : (
        <div className="xs faint">
          {t('moderation.resolvedBy')}: {report.resolved_by}
          {report.resolution_note && <> — {report.resolution_note}</>}
        </div>
      )}
    </article>
  );
}

export function ModerationScreen() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<ReportStatus>('open');
  const [items, setItems] = useState<ReportView[]>([]);
  const [state, setState] = useState<'loading' | 'ready' | 'forbidden' | 'error'>('loading');
  const [message, setMessage] = useState('');

  const load = useCallback(async (status: ReportStatus) => {
    setState('loading');
    try {
      setItems((await api.moderationQueue(status)).items);
      setState('ready');
    } catch (problem) {
      if (problem instanceof ApiError && problem.status === 403) {
        setState('forbidden');
        setMessage(problem.message);
        return;
      }
      setMessage(problem instanceof ApiError ? problem.message : 'Could not load the queue.');
      setState('error');
    }
  }, []);

  useEffect(() => { void load(tab); }, [load, tab]);

  if (state === 'forbidden') {
    return <Notice kind="info">{message}</Notice>;
  }

  return (
    <div className="stack community-column">
      <div className="screen__head">
        <h1 className="screen__title">{t('moderation.title')}</h1>
        <p className="screen__lede">{t('moderation.lede')}</p>
      </div>

      <div className="tabs">
        {TABS.map((status) => (
          <button
            key={status}
            type="button"
            className="tab"
            aria-selected={tab === status}
            onClick={() => setTab(status)}
          >
            {t(`moderation.${status}` as never)}
          </button>
        ))}
      </div>

      {state === 'error' && <Notice kind="risk">{message}</Notice>}
      {state === 'loading' && <Loading label={t('moderation.loading')} />}

      {state === 'ready' && items.length === 0 && (
        <Empty title={t('moderation.empty')}>
          <p className="small">{t('moderation.emptyHint')}</p>
        </Empty>
      )}

      {items.map((report) => (
        <Panel key={report.id}>
          <Report report={report} onResolved={() => load(tab)} />
        </Panel>
      ))}
    </div>
  );
}

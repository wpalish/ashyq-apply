/**
 * Reporting and blocking, as they appear beside the thing being acted on.
 *
 * The two are deliberately not the same weight. Blocking is a decision the
 * person makes and it takes effect at once; reporting is a request to somebody
 * else and will take as long as a human takes. The report dialog says so,
 * because a person being harassed right now needs to know which of the two
 * actually stops it.
 */

import { useState } from 'react';
import { api, ApiError } from '@/api/client';
import { Notice } from '@/components/primitives';
import { t } from '@/lib/i18n';
import type { ReportReason, ReportTarget } from '@/types';

const REASONS: ReportReason[] = [
  'harassment',
  'personal_information',
  'impersonation',
  'misleading_advice',
  'spam',
  'other',
];

export function ReportButton({
  subjectType, subjectId,
}: { subjectType: ReportTarget; subjectId: string }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<ReportReason>('harassment');
  const [note, setNote] = useState('');
  const [state, setState] = useState<'idle' | 'sending' | 'sent'>('idle');
  const [error, setError] = useState('');

  if (state === 'sent') {
    return <span className="xs muted">{t('report.sent')}</span>;
  }

  if (!open) {
    return (
      <button type="button" className="linkish linkish--quiet" onClick={() => setOpen(true)}>
        {t('report.action')}
      </button>
    );
  }

  return (
    <form
      className="stack stack--tight report"
      onSubmit={async (event) => {
        event.preventDefault();
        setState('sending');
        try {
          await api.reportContent({
            subject_type: subjectType,
            subject_id: subjectId,
            reason,
            note: note.trim(),
          });
          setState('sent');
        } catch (problem) {
          setError(
            problem instanceof ApiError && problem.status === 409
              ? t('report.already')
              : problem instanceof ApiError
                ? problem.message
                : 'Could not send that report.',
          );
          setState('idle');
        }
      }}
    >
      <strong className="small">{t('report.title')}</strong>
      {error && <Notice kind="risk">{error}</Notice>}
      <div className="field">
        <label className="field__label xs" htmlFor={`report-reason-${subjectId}`}>
          {t('report.reason')}
        </label>
        <select
          id={`report-reason-${subjectId}`}
          value={reason}
          onChange={(event) => setReason(event.target.value as ReportReason)}
        >
          {REASONS.map((value) => (
            <option key={value} value={value}>{t(`report.${value}` as never)}</option>
          ))}
        </select>
      </div>
      <div className="field">
        <label className="field__label xs" htmlFor={`report-note-${subjectId}`}>
          {t('report.note')}
        </label>
        <input
          id={`report-note-${subjectId}`}
          value={note}
          maxLength={500}
          onChange={(event) => setNote(event.target.value)}
        />
      </div>
      {/* Said before they send, not after: someone in trouble needs to know
          that the fast tool is the other one. */}
      <p className="xs faint">{t('report.slow')}</p>
      <div className="row row--tight">
        <button className="btn btn--sm btn--primary" type="submit" disabled={state === 'sending'}>
          {state === 'sending' ? t('report.sending') : t('report.send')}
        </button>
        <button className="btn btn--sm" type="button" onClick={() => setOpen(false)}>
          {t('report.cancel')}
        </button>
      </div>
    </form>
  );
}

export function BlockButton({
  userId, blocked, onChanged,
}: { userId: string; blocked: boolean; onChanged: () => void }) {
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);

  if (blocked) {
    return (
      <button
        type="button"
        className="btn btn--sm"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await api.unblockPerson(userId);
            onChanged();
          } finally {
            setBusy(false);
          }
        }}
      >
        {t('block.unblock')}
      </button>
    );
  }

  if (!asking) {
    return (
      <button type="button" className="btn btn--sm btn--danger" onClick={() => setAsking(true)}>
        {t('block.action')}
      </button>
    );
  }

  return (
    <span className="stack stack--tight">
      <strong className="small">{t('block.confirm')}</strong>
      <span className="xs muted">{t('block.explain')}</span>
      <span className="row row--tight">
        <button
          type="button"
          className="btn btn--sm btn--danger"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await api.blockPerson(userId);
              onChanged();
            } finally {
              setBusy(false);
              setAsking(false);
            }
          }}
        >
          {t('block.action')}
        </button>
        <button type="button" className="btn btn--sm" onClick={() => setAsking(false)}>
          {t('report.cancel')}
        </button>
      </span>
    </span>
  );
}

/** Durable personal metadata through native G3; no private-file or course dependency. */
import { useRef, useState } from 'react';
import { AdmissionsRecoveryPanel } from '@/components/AdmissionsRecoveryPanel';
import { Loading, Notice, Panel } from '@/components/primitives';
import { dateTime } from '@/lib/format';
import { useAdmissionsActions } from '@/lib/useAdmissionsActions';
import { useTranslation } from '@/lib/useTranslation';
import type { MessageKey } from '@/lib/i18n';
import type { ActionPersonalDetailsV1, ActionRequestV1, DocumentReportState, DocumentTaskV1, ResponsibleActor } from '@/types/admissionsActions';

type Draft = { caseKey: string; baseRevision: number; mode: 'new' | 'details' | 'report'; taskId: string | null;
  label: string; responsible: ResponsibleActor; applicationId: string; notes: string; due: string; zone: string;
  report: DocumentReportState; reportedOn: string; confirmed: boolean };
const reportKeys: Record<DocumentReportState, MessageKey> = { not_started: 'documents.notStarted', in_progress: 'documents.inProgress',
  prepared_reported: 'documents.prepared', sent_reported: 'documents.sent', received_reported: 'documents.received', not_needed_reported: 'documents.notNeeded' };
const actorKeys: Record<ResponsibleActor, MessageKey> = { applicant: 'documents.you', school: 'documents.school', recommender: 'documents.recommender', third_party: 'documents.thirdParty' };

export function PersonalDocumentsPanel() {
  const actions = useAdmissionsActions(); const { t } = useTranslation();
  const liveKey = useRef(actions.caseKey); liveKey.current = actions.caseKey;
  const [storedDraft, setDraft] = useState<Draft | null>(null);
  const [feedback, setFeedback] = useState<{ key: string; value: 'saved' | 'unknown' | 'invalid' } | null>(null);
  const [historyTask, setHistoryTask] = useState<{ key: string; id: string } | null>(null);
  const draft = storedDraft?.caseKey === actions.caseKey ? storedDraft : null;
  const tasks = actions.current?.state?.document_tasks ?? [];
  const applications = actions.current?.state?.applications ?? [];
  const canEdit = actions.current !== null && !actions.loading && !actions.sending && actions.journalError === null;
  const open = (mode: Draft['mode'], task?: DocumentTaskV1) => {
    if (!actions.current || !canEdit) return;
    setFeedback(null);
    setDraft({ caseKey: actions.caseKey, baseRevision: actions.current.revision, mode, taskId: task?.id ?? null,
      label: task?.personal.label ?? '', responsible: task?.personal.responsible_actor ?? 'applicant',
      applicationId: task?.application_id ?? '', notes: task?.personal.details.notes ?? '',
      due: task?.personal.details.due?.local_date ?? '', zone: mode === 'report' ? task?.report.entered_at?.timezone ?? '' : task?.personal.details.due?.timezone ?? '',
      report: task?.report.state ?? 'not_started', reportedOn: task?.report.entered_at?.local_date ?? '', confirmed: false });
  };
  const change = (patch: Partial<Draft>) => setDraft(old => old?.caseKey === actions.caseKey ? { ...old, ...patch } : old);
  const save = async () => {
    if (!draft || !canEdit || (draft.mode === 'report' && !draft.confirmed)) return;
    const captured = draft;
    try {
      const details: ActionPersonalDetailsV1 = { notes: captured.notes, due: captured.due ? {
        origin: 'applicant_entered', local_date: captured.due, timezone: captured.zone || null, official_deadline: false,
      } : null };
      const base = { schema_version: 'admissions-actions-v1' as const, client_write_uuid: crypto.randomUUID(), expected_revision: captured.baseRevision };
      let body: ActionRequestV1;
      if (captured.mode === 'new') body = { ...base, kind: 'create_personal_task', application_id: captured.applicationId || null,
        personal: { label: captured.label, responsible_actor: captured.responsible, details, depends_on_task_ids: [] } };
      else if (captured.mode === 'details' && captured.taskId) body = { ...base, kind: 'set_personal_details',
        target: { kind: 'document_task', id: captured.taskId }, details };
      else if (captured.mode === 'report' && captured.taskId) body = { ...base, kind: 'set_document_self_report', task_id: captured.taskId,
        report: { state: captured.report, confirmed_personal_report: true, entered_at: captured.reportedOn ? {
          local_date: captured.reportedOn, local_time: null, timezone: captured.zone || null, origin: 'applicant_entered',
        } : null } };
      else return;
      const outcome = await actions.submit(body);
      if (liveKey.current !== captured.caseKey) return;
      setFeedback({ key: captured.caseKey, value: outcome.accepted ? 'saved' : 'unknown' });
      if (outcome.accepted) setDraft(old => old === captured ? null : old);
    } catch { if (liveKey.current === captured.caseKey) setFeedback({ key: captured.caseKey, value: 'invalid' }); }
  };

  return <div className="stack stack--loose" data-testid="personal-documents">
    <Panel title={t('documents.personalTitle')}>
      <div className="stack">
        <p className="small muted">{t('documents.personalHint')}</p>
        {actions.loading && <Loading label={t('documents.loading')} />}
        {actions.error && <Notice kind="risk">{actions.error}</Notice>}
        {feedback?.key === actions.caseKey && <Notice kind={feedback.value === 'saved' ? 'info' : 'warn'}>
          {feedback.value === 'saved' ? t('documents.saved') : feedback.value === 'invalid' ? t('documents.invalid') : t('documents.saveUnknown')}
        </Notice>}
        {actions.current !== null && tasks.length === 0 && <p className="muted">{t('documents.emptyPersonal')}</p>}
        <button type="button" className="btn btn--primary" disabled={!canEdit} onClick={() => open('new')}>{t('documents.addPersonal')}</button>
        {tasks.map(task => <article key={task.id} className="stack stack--tight" data-testid="personal-document-task">
          <h3>{task.personal.label}</h3>
          <span className="small">{t(actorKeys[task.personal.responsible_actor])} · {t(reportKeys[task.report.state])}</span>
          {task.personal.details.due && <span className="small">{t('documents.personalDate')}: {task.personal.details.due.local_date}
            {' · '}{task.personal.details.due.timezone ?? t('documents.zoneUnknown')}</span>}
          {task.personal.details.notes && <p className="small">{task.personal.details.notes}</p>}
          {task.binding && <span className="small muted">{t('documents.linkedRequirement')}</span>}
          {actions.current?.document_report_reviews.some(review => review.task_id === task.id && review.reasons.length > 0)
            && <Notice kind="warn">{t('documents.reportReview')}</Notice>}
          <span className="xs muted">{t('documents.selfReportHint')}</span>
          <div className="row">
            <button type="button" className="btn btn--ghost" disabled={!canEdit} onClick={() => open('details', task)}>{t('documents.editDetails')}</button>
            <button type="button" className="btn btn--ghost" disabled={!canEdit} onClick={() => open('report', task)}>{t('documents.updateReport')}</button>
            <button type="button" className="btn btn--ghost" onClick={async () => {
              const capturedKey = actions.caseKey;
              if (await actions.loadHistory() && liveKey.current === capturedKey) setHistoryTask({ key: capturedKey, id: task.id });
            }}>{t('documents.history')}</button>
          </div>
        </article>)}
      </div>
    </Panel>
    {draft && <Panel title={draft.mode === 'new' ? t('documents.addPersonal') : draft.label}>
      <form className="stack" onSubmit={event => { event.preventDefault(); void save(); }}>
        {draft.baseRevision !== actions.current?.revision && <Notice kind="warn">{t('documents.draftConflict')}</Notice>}
        {draft.mode === 'new' && <>
          <label className="stack stack--tight">{t('documents.taskName')}<input autoFocus required maxLength={200} value={draft.label} onChange={event => change({ label: event.target.value })} /></label>
          <label className="stack stack--tight">{t('documents.responsible')}<select value={draft.responsible} onChange={event => change({ responsible: event.target.value as ResponsibleActor })}>
            {Object.entries(actorKeys).map(([actor, key]) => <option key={actor} value={actor}>{t(key)}</option>)}
          </select></label>
          <label className="stack stack--tight">{t('documents.application')}<select value={draft.applicationId} onChange={event => change({ applicationId: event.target.value })}>
            <option value="">{t('documents.noApplication')}</option>{applications.map(app => <option key={app.id} value={app.id}>{app.label}</option>)}
          </select></label>
        </>}
        {draft.mode !== 'report' ? <>
          <label className="stack stack--tight">{t('documents.personalDate')}<input type="date" value={draft.due} onChange={event => change({ due: event.target.value })} /></label>
          <label className="stack stack--tight">{t('documents.notes')}<textarea maxLength={2000} value={draft.notes} onChange={event => change({ notes: event.target.value })} /></label>
        </> : <>
          <label className="stack stack--tight">{t('documents.reportStatus')}<select value={draft.report} onChange={event => change({ report: event.target.value as DocumentReportState })}>
            {Object.entries(reportKeys).map(([status, key]) => <option key={status} value={status}>{t(key)}</option>)}
          </select></label>
          <label className="stack stack--tight">{t('documents.reportedOn')}<input type="date" value={draft.reportedOn} onChange={event => change({ reportedOn: event.target.value })} /></label>
          <label className="row"><input type="checkbox" checked={draft.confirmed} onChange={event => change({ confirmed: event.target.checked })} />{t('documents.confirmReport')}</label>
        </>}
        <label className="stack stack--tight">{t('documents.timezone')}<input maxLength={80} placeholder="Asia/Almaty" value={draft.zone} onChange={event => change({ zone: event.target.value })} /></label>
        <p className="small muted">{t('documents.dateHint')}</p>
        <div className="row">
          <button type="submit" className="btn btn--primary" disabled={!canEdit || (draft.mode === 'report' && !draft.confirmed)}>{t('documents.save')}</button>
          <button type="button" className="btn btn--ghost" disabled={actions.sending} onClick={() => setDraft(null)}>{t('documents.cancel')}</button>
        </div>
      </form>
    </Panel>}
    {historyTask?.key === actions.caseKey && actions.historyPage && <Panel title={t('documents.history')}>
      <div className="stack">
        {actions.historyPage.events.filter(event => event.affected_refs.document_task_ids.includes(historyTask.id)).map(event => <div key={event.event_id} className="small">
          {t('documents.recordedAt')}: {dateTime(event.accepted_at)}
          {' · '}{'personal' in event.request ? event.request.personal.label : t('documents.personalChange')}
        </div>)}
        {actions.historyPage.next_after_revision !== null && <button type="button" className="btn btn--ghost"
          onClick={() => { void actions.loadHistory(actions.historyPage?.next_after_revision ?? 0); }}>{t('documents.moreHistory')}</button>}
      </div>
    </Panel>}
    <AdmissionsRecoveryPanel controller={actions} />
  </div>;
}

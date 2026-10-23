import { targetHref } from '@/lib/admissionsNavigation';
/** Exact original occurrence selection; names are presentation only. */
import { useRef, useState } from 'react';
import { api } from '@/api/client';
import { Notice, Panel, SourceLink } from '@/components/primitives';
import { useStore } from '@/lib/store';
import { useTranslation } from '@/lib/useTranslation';
import type { AdmissionsActionsController } from '@/lib/useAdmissionsActions';
import type { MessageKey } from '@/lib/i18n';
import type { GraphChecklistLocation } from '@/types';
import { isSourceBindingPreviewOutV1, type SourceBindingPreviewOutV1 } from '@/types/admissionsActions';
const locationLabels: Record<GraphChecklistLocation, MessageKey> = { admission_documents: 'documents.admissionList', scholarship_documents: 'documents.scholarshipList', applicant_actions: 'documents.applicantList', school_actions: 'documents.schoolList', recommender_actions: 'documents.recommenderList', certification_actions: 'documents.certificationList' };
const locations: readonly GraphChecklistLocation[] = ['admission_documents', 'scholarship_documents', 'applicant_actions', 'school_actions', 'recommender_actions', 'certification_actions'];
type Preview = { attempted: boolean; key: string; sequence: number; revision: number; taskId: string; resultId: string; applicationId: string|null; label: string; value: SourceBindingPreviewOutV1 };
export function DocumentSourceBindings({ controller, programmeId, applicationId }: { controller: AdmissionsActionsController; programmeId?:string; applicationId?:string }) {
  const { savedProfile, run, results, currentAdmissionsCase } = useStore(); const { t, locale } = useTranslation();
  const [choice, setChoice] = useState<{ key: string; occurrence: string; taskId: string }>({ key: controller.caseKey, occurrence: '', taskId: '' });
  const [preview, setPreview] = useState<Preview | null>(null);
  const [status, setStatus] = useState<{ key: string; kind: 'loading' | 'error' | 'saved' | 'unknown' } | null>(null);
  const [savedTask,setSavedTask]=useState<{key:string;id:string}|null>(null);
  const attemptedPreview = useRef<Preview | null>(null); const sequence = useRef(0); const keyRef = useRef(controller.caseKey); keyRef.current = controller.caseKey;
  const owned = controller.activeCase === savedProfile?.id && run?.profile_id === savedProfile?.id ? results.filter(result => result.run_id === run.id
    && (!programmeId||result.id===programmeId) && (result.user_decision === 'approved' || result.user_decision === 'maybe') && result.checklist) : [];
  const options = owned.flatMap(result => locations.flatMap(location => (result.checklist?.[location] ?? []).map((item, index) => ({
    token: JSON.stringify([result.id, location, index]), resultId: result.id, location, index, name: item.name,
    purpose: item.purpose, label: `${result.university} · ${result.program} · ${item.name} · ${t(locationLabels[location])} #${index + 1}`,
  }))));
  const selected = choice.key === controller.caseKey ? choice : { key: controller.caseKey, occurrence: '', taskId: '' };
  const option = options.find(value => value.token === selected.occurrence);
  const validApplication=!applicationId||Boolean(option&&controller.current?.state?.applications.some(app=>app.id===applicationId&&app.target.result_id===option.resultId));
  const currentPreview = preview?.key === controller.caseKey && preview.sequence === sequence.current && preview.resultId === option?.resultId ? preview : null;
  const eligibleTasks = (controller.current?.state?.document_tasks ?? []).filter(task => task.application_id === null
    || controller.current?.state?.applications.some(app => app.id === task.application_id && (!applicationId||app.id===applicationId) && app.target.result_id === option?.resultId));
  const select = (next: { occurrence: string; taskId: string }) => { ++sequence.current; setPreview(null); setStatus(null); setChoice({ key: controller.caseKey, ...next }); };
  const check = async () => {
    if (!option || !controller.current || controller.sending || applicationId&&!controller.current.state?.applications.some(app=>app.id===applicationId&&app.target.result_id===option.resultId)) return;
    const capturedKey = controller.caseKey; const serial = ++sequence.current; const revision = controller.current.revision;
    const identity = currentAdmissionsCase();
    setPreview(null); setStatus({ key: capturedKey, kind: 'loading' });
    try {
      const value = await api.previewAdmissionsSource(controller.activeCase ?? '', { result_id: option.resultId,
        purpose: option.purpose, award_id: null, occurrences: [{ location: option.location, index: option.index }] });
      if (keyRef.current !== capturedKey || sequence.current !== serial || JSON.stringify(currentAdmissionsCase()) !== JSON.stringify(identity)) return;
      if (!isSourceBindingPreviewOutV1(value) || value.profile_id !== controller.activeCase || value.result_id !== option.resultId
        || value.selection.occurrences.length !== 1 || value.selection.occurrences[0]?.location !== option.location
        || value.selection.occurrences[0]?.index !== option.index) throw new Error('Source preview mismatch');
      setPreview({ attempted: false, key: capturedKey, sequence: serial, revision, taskId: selected.taskId, resultId: option.resultId, applicationId:applicationId??null, label: option.name, value });
      setStatus(null);
    } catch { if (keyRef.current === capturedKey && sequence.current === serial) setStatus({ key: capturedKey, kind: 'error' }); }
  };
  const bind = async () => {
    if (!currentPreview || currentPreview.attempted || attemptedPreview.current === currentPreview || controller.sending || controller.current?.revision !== currentPreview.revision) return;
    const captured = currentPreview;
    try {
      const base = { schema_version: 'admissions-actions-v1' as const, client_write_uuid: crypto.randomUUID(), expected_revision: captured.revision };
      const source = { source: captured.value.selection, source_preview_digest: captured.value.source_preview_digest };
      if(captured.applicationId&&!controller.current.state?.applications.some(app=>app.id===captured.applicationId&&app.target.result_id===captured.resultId))throw new Error('Application context changed');
      const task = controller.current.state?.document_tasks.find(item => item.id === captured.taskId);
      if (captured.taskId && !task) throw new Error('Selected own task disappeared');
      const pending = { ...captured, attempted: true }; attemptedPreview.current = captured;
      setPreview(old => old === captured ? pending : old);
      const result = captured.taskId ? task && await controller.submit({ ...base, ...source, kind: 'rebind_source_task', task_id: task.id, expected_binding_digest: task.binding?.binding_digest ?? null })
        : await controller.submit({ ...base, ...source, kind: 'bind_source_task', application_id: captured.applicationId,
          personal: { label: captured.label, responsible_actor: 'applicant', details: { due: null, notes: '' }, depends_on_task_ids: [] } });
      if (keyRef.current !== captured.key || sequence.current !== captured.sequence) return;
      if (result?.accepted) { const saved=result.receipt?.applied_delta.document_tasks[0];if(saved)setSavedTask({key:captured.key,id:saved.id});setPreview(old => old === pending ? null : old); setStatus({ key: captured.key, kind: 'saved' }); }
      else setStatus({ key: captured.key, kind: 'unknown' });
    } catch { if (keyRef.current === captured.key && sequence.current === captured.sequence) setStatus({ key: captured.key, kind: 'error' }); }
  };
  return <Panel title={programmeId&&locale!=='en'?'Создать задачу по требованию':t('documents.sourceTitle')}>
    <div className="stack">
      <p className="small muted">{programmeId&&locale!=='en'?'Выбери документ. Проверь текущее требование, затем сохрани связанную личную задачу.':t('documents.sourceHint')}</p>
      {!options.length && <p className="small muted">{t('documents.noOwnedRequirements')}</p>}
      <label className="stack stack--tight">{t('documents.chooseOccurrence')}<select value={selected.occurrence} onChange={event => select({ occurrence: event.target.value, taskId: '' })}>
        <option value="">{t('documents.chooseOccurrence')}</option>{options.map(item => <option key={item.token} value={item.token}>{item.label}</option>)}
      </select></label>
      <label className="stack stack--tight">{t('documents.chooseTaskBinding')}<select value={selected.taskId} onChange={event => select({ ...selected, taskId: event.target.value })}>
        <option value="">{t('documents.createLinkedTask')}</option>{eligibleTasks.map(task => <option key={task.id} value={task.id}>{task.personal.label}</option>)}
      </select></label>
      {option&&!validApplication&&<Notice kind="warn">Связь заявки с программой изменилась. Открой документы из актуальной заявки.</Notice>}
      <button type="button" className="btn btn--ghost" disabled={!option || !controller.current || !validApplication || controller.sending || status?.kind === 'loading'} onClick={() => { void check(); }}>{t('documents.checkSource')}</button>
      {status?.key === controller.caseKey && status.kind === 'error' && <Notice kind="warn">{t('documents.sourceUnavailable')}</Notice>}
      {status?.key === controller.caseKey && status.kind === 'unknown' && <Notice kind="warn">{t('documents.saveUnknown')}</Notice>}
      {status?.key === controller.caseKey && status.kind === 'saved' && <Notice>{t('documents.saved')}{savedTask?.key===controller.caseKey&&<a className="btn btn--sm" href={targetHref({screen:'documents',profileId:controller.activeCase!,target:{kind:'document_task',id:savedTask.id}})}>Открыть связанную задачу</a>}</Notice>}
      {currentPreview && <div className="stack stack--tight">
        <h3>{currentPreview.label}</h3><p className="small">{t('documents.sourceReviewHint')}</p><p className="small">{currentPreview.taskId?'Связь выбранной задачи с требованием обновится. Заявка задачи не меняется.':currentPreview.applicationId?'Новая задача будет связана с выбранной заявкой.':'Новая задача сохранится по программе. Её можно связать с заявкой позже.'}</p>
        <p className="small muted">{currentPreview.value.source_status.reasons.length > 0 ? t('documents.sourceNeedsReview') : t('documents.sourceReference')}</p>
        {owned.find(result=>result.id===currentPreview.resultId)?.claims?.filter(claim=>currentPreview.value.selection.original_claim_ids.includes(claim.id)).slice(0,3).map(claim=><blockquote className="requirement-proof" key={claim.id}><p>{claim.original_text_excerpt}</p><SourceLink url={claim.source_url}/></blockquote>)}
        {controller.current?.revision !== currentPreview.revision && <Notice kind="warn">{t('documents.draftConflict')}</Notice>}
        <button type="button" className="btn btn--primary" disabled={currentPreview.attempted || controller.sending || controller.journalError !== null || controller.current?.revision !== currentPreview.revision}
          onClick={() => { void bind(); }}>{programmeId&&locale!=='en'?currentPreview.taskId?'Обновить связь с требованием':'Создать задачу по проверенному требованию':t('documents.bindReviewed')}</button>
      </div>}
    </div>
  </Panel>;
}

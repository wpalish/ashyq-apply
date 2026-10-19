import { ProgrammeJourney } from '@/components/ProgrammeJourney';
import { journeyHref, useJourneyRoute } from '@/lib/programmeJourney';
import { targetHref } from '@/lib/admissionsNavigation';
import { useStore } from '@/lib/store';
/** Durable personal metadata through native G3; no private-file or course dependency. */
import { DocumentSourceBindings } from './DocumentSourceBindings';
import { LegacyDocumentImport } from './LegacyDocumentImport';
import { BookDocumentsTable } from '@/components/BookDocumentsTable';
import { LocalDocumentPreview } from '@/components/LocalDocumentPreview';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AdmissionsRecoveryPanel } from '@/components/AdmissionsRecoveryPanel';
import { Loading, Notice, Panel } from '@/components/primitives';
import { dateTime } from '@/lib/format';
import { useAdmissionsActions } from '@/lib/useAdmissionsActions';
import { useAdmissionsTarget } from '@/lib/admissionsNavigation';
import { useTranslation } from '@/lib/useTranslation';
import type { MessageKey } from '@/lib/i18n';
import { isActionRequest } from '@/types/admissionsActions';
import type { ActionPersonalDetailsV1, ActionRequest, DocumentReportState, DocumentTaskV1, ResponsibleActor } from '@/types/admissionsActions';

type Draft = { caseKey: string; baseRevision: number; mode: 'new' | 'details' | 'report' | 'remove'; taskId: string | null;
  label: string; responsible: ResponsibleActor; applicationId: string; dependencies: string[]; notes: string; due: string; zone: string;
  report: DocumentReportState; reportedOn: string; confirmed: boolean; attempted: boolean };
const reportKeys: Record<DocumentReportState, MessageKey> = { not_started: 'documents.notStarted', in_progress: 'documents.inProgress',
  prepared_reported: 'documents.prepared', sent_reported: 'documents.sent', received_reported: 'documents.received', not_needed_reported: 'documents.notNeeded' };
const actorKeys: Record<ResponsibleActor, MessageKey> = { applicant: 'documents.you', school: 'documents.school', recommender: 'documents.recommender', third_party: 'documents.thirdParty' };

export function PersonalDocumentsPanel({ onDetailChange }: { onDetailChange?:(opened:boolean)=>void } = {}) {
  const actions = useAdmissionsActions(); const { t, locale } = useTranslation();
  const [bookOpened,setBookOpened]=useState<{key:string;id:string}|null>(null);
  const journey=useJourneyRoute();
  const {results=[],run,savedProfile}=useStore();
  const target = useAdmissionsTarget(); const openedTarget = useRef<string | null>(null);
  const attemptedDraft = useRef<Draft | null>(null);
  const liveKey = useRef(actions.caseKey); liveKey.current = actions.caseKey;
  const editorRef=useRef<HTMLFormElement>(null);
  const [storedDraft, setDraft] = useState<Draft | null>(null);
  const [feedback, setFeedback] = useState<{ key: string; value: 'saved' | 'unknown' | 'invalid' } | null>(null);
  const [historyTask, setHistoryTask] = useState<{ key: string; id: string } | null>(null);
  const draft = storedDraft?.caseKey === actions.caseKey ? storedDraft : null;
  const editorKey=draft?JSON.stringify([draft.caseKey,draft.mode,draft.taskId]):null;
  const focusEditor=Boolean(draft&&!draft.attempted);
  useEffect(()=>{
    if(!focusEditor)return;
    const frame=window.requestAnimationFrame(()=>editorRef.current?.querySelector<HTMLElement>('input:not([type="checkbox"]):not(:disabled),select:not(:disabled),textarea:not(:disabled)')?.focus());
    return()=>window.cancelAnimationFrame(frame);
  },[editorKey,focusEditor]);

  const currentTasks = actions.current?.state?.document_tasks;
  const tasks = useMemo(() => currentTasks ?? [], [currentTasks]);
  const applications = actions.current?.state?.applications ?? [];
  const routeOwned=journey?.screen==='documents'&&journey.profileId===actions.activeCase;
  const ownedResults=run&&savedProfile&&run.profile_id===savedProfile.id&&actions.activeCase===savedProfile.id?results:[];
  const focusedTask=target?.target.kind==='document_task'&&target.profileId===actions.activeCase?tasks.find(task=>task.id===target.target.id):undefined;
  const contextApp=(routeOwned?applications.find(app=>app.id===journey.applicationId):undefined)??applications.find(app=>app.id===focusedTask?.application_id);
  const resultContextId=(routeOwned?journey.resultId:undefined)??contextApp?.target.result_id??focusedTask?.binding?.result_id;
  const contextResult=ownedResults.find(result=>result.id===resultContextId&&(['approved','maybe'].includes(result.user_decision)||contextApp?.target.result_id===result.id||focusedTask?.binding?.result_id===result.id));
  const contextMissing=Boolean(journey?.screen==='documents'&&(!routeOwned||actions.current!==null&&(journey.applicationId&&!contextApp||journey.resultId&&!contextResult||contextApp&&journey.resultId&&contextApp.target.result_id!==journey.resultId)));
  const relatedApps=contextResult?applications.filter(app=>app.target.result_id===contextResult.id):[];
  const selectedApp=!contextMissing?(contextApp??(relatedApps.length===1?relatedApps[0]:undefined)):undefined;
  const shownTasks=contextMissing?tasks:contextApp?tasks.filter(task=>task.application_id===contextApp.id||task.application_id===null&&Boolean(contextResult)&&task.binding?.result_id===contextResult?.id):contextResult?tasks.filter(task=>task.binding?.result_id===contextResult.id||relatedApps.some(app=>app.id===task.application_id)):tasks;
  const bookDetail=locale!=='en'&&bookOpened?.key===actions.caseKey&&tasks.some(task=>task.id===bookOpened.id);
  useEffect(()=>{onDetailChange?.(bookDetail);},[bookDetail,onDetailChange]);
  const canEdit = actions.current !== null && !actions.loading && !actions.sending && actions.journalError === null;
  const open = useCallback((mode: Draft['mode'], task?: DocumentTaskV1) => {
    if (!actions.current || !canEdit) return;
    setFeedback(null);
    if(locale!=='en'&&task)setBookOpened({key:actions.caseKey,id:task.id});
    setDraft({ caseKey: actions.caseKey, baseRevision: actions.current.revision, mode, taskId: task?.id ?? null,
      label: task?.personal.label ?? '', responsible: task?.personal.responsible_actor ?? 'applicant',
      applicationId: task?.application_id ?? ((mode==='new'||mode==='details'&&contextApp)?selectedApp?.id??'':''), dependencies: [...(task?.personal.depends_on_task_ids ?? [])], notes: task?.personal.details.notes ?? '',
      due: task?.personal.details.due?.local_date ?? '', zone: mode === 'report' ? task?.report.entered_at?.timezone ?? '' : task?.personal.details.due?.timezone ?? '',
      report: task?.report.state ?? 'not_started', reportedOn: task?.report.entered_at?.local_date ?? '', confirmed: false, attempted: false });
  }, [actions, canEdit, locale, selectedApp?.id, contextApp]);
  const change = (patch: Partial<Draft>) => setDraft(old => old?.caseKey === actions.caseKey && !old.attempted ? { ...old, ...patch } : old);
  const targetKey = target?.target.kind === 'document_task' ? JSON.stringify([actions.caseKey, target]) : null;
  const targetMissing = targetKey !== null && (target?.profileId !== actions.activeCase || (actions.current !== null && !tasks.some(item => item.id === target?.target.id)));
  useEffect(() => {
    if (!targetKey || openedTarget.current === targetKey || targetMissing || !canEdit || target?.profileId !== actions.activeCase) return;
    const exact = tasks.find(item => item.id === target?.target.id); if (!exact) return;
    openedTarget.current = targetKey; if(locale!=='en')setBookOpened({key:actions.caseKey,id:exact.id});else open('details', exact);
  }, [targetKey, targetMissing, canEdit, target, actions.activeCase, tasks, open, locale, actions.caseKey]);
  const save = async () => {
    if (!draft || draft.attempted || attemptedDraft.current === draft || !canEdit || (draft.mode !== 'new' && !draft.confirmed)) return;
    const captured = draft;
    try {
      const details: ActionPersonalDetailsV1 = { notes: captured.notes, due: captured.due ? {
        origin: 'applicant_entered', local_date: captured.due, timezone: captured.zone || null, official_deadline: false,
      } : null };
      const base = { schema_version: 'admissions-actions-v1' as const, client_write_uuid: crypto.randomUUID(), expected_revision: captured.baseRevision };
      let body: ActionRequest;
      if (captured.mode === 'new') body = { ...base, kind: 'create_personal_task', application_id: captured.applicationId || null,
        personal: { label: captured.label, responsible_actor: captured.responsible, details, depends_on_task_ids: captured.dependencies } };
      else if (captured.mode === 'details' && captured.taskId) body = { ...base, schema_version: 'admissions-actions-v2', kind: 'set_personal_details', operation: 'document_metadata',
        target: { kind: 'document_task', id: captured.taskId }, application_id: captured.applicationId || null,
        personal: { label: captured.label, responsible_actor: captured.responsible, details, depends_on_task_ids: captured.dependencies }, confirmed_personal_metadata: true };
      else if (captured.mode === 'remove' && captured.taskId) body = { ...base, schema_version: 'admissions-actions-v2', kind: 'remove_personal_action',
        target: { kind: 'document_task', id: captured.taskId }, confirmed_personal_removal: true };
      else if (captured.mode === 'report' && captured.taskId) body = { ...base, kind: 'set_document_self_report', task_id: captured.taskId,
        report: { state: captured.report, confirmed_personal_report: true, entered_at: captured.reportedOn ? {
          local_date: captured.reportedOn, local_time: null, timezone: captured.zone || null, origin: 'applicant_entered',
        } : null } };
      else return;
      if (!isActionRequest(body)) throw new Error('Entered fields are invalid');
      const pending = { ...captured, attempted: true }; attemptedDraft.current = captured;
      setDraft(old => old === captured ? pending : old);
      const outcome = await actions.submit(body);
      if (liveKey.current !== captured.caseKey) return;
      setFeedback({ key: captured.caseKey, value: outcome.accepted ? 'saved' : 'unknown' });
      if (outcome.accepted) {
        setDraft(old => old === pending ? null : old);
        if (captured.mode === 'remove' && captured.taskId && await actions.loadHistory() && liveKey.current === captured.caseKey)
          setHistoryTask({ key: captured.caseKey, id: captured.taskId });
      }
    } catch { if (liveKey.current === captured.caseKey) setFeedback({ key: captured.caseKey, value: 'invalid' }); }
  };

  return <div className="stack stack--loose" data-testid="personal-documents">
    {locale==='en'?<Panel title={t('documents.personalTitle')}>
      <div className="stack">
        <p className="small muted">{t('documents.personalHint')}</p>
        {targetMissing && <Notice kind="warn">{t('today.targetMissing')}</Notice>}
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
          <details><summary>Inspect a document file</summary><LocalDocumentPreview key={`${actions.caseKey}:${task.id}`} label={task.personal.label} /></details>
          <div className="row">
            <button type="button" className="btn btn--ghost" disabled={!canEdit} onClick={() => open('details', task)}>{t('documents.editMetadata')}</button>
            <button type="button" className="btn btn--ghost" disabled={!canEdit} onClick={() => open('report', task)}>{t('documents.updateReport')}</button>
            <button type="button" className="btn btn--ghost" disabled={!canEdit} onClick={() => open('remove', task)}>{t('actions.removePersonal')}</button>
            <button type="button" className="btn btn--ghost" onClick={async () => {
              const capturedKey = actions.caseKey;
              if (await actions.loadHistory() && liveKey.current === capturedKey) setHistoryTask({ key: capturedKey, id: task.id });
            }}>{t('documents.history')}</button>
          </div>
        </article>)}
      </div>
    </Panel>:<>
      {contextMissing&&<Notice kind="warn">Контекст программы или заявки не подтверждён для текущего профиля. Открой свою программу в подборе.</Notice>}
      {!contextMissing&&(contextResult||contextApp)&&<section className="journey-context"><ProgrammeJourney profileId={actions.activeCase!} resultId={contextResult?.id} applicationId={contextApp?.id} current="documents"/><h2>{contextResult?.university??contextApp?.label}</h2><p>{contextResult?.program}</p><div className="row">{relatedApps.map(app=><a className="btn btn--sm" key={app.id} href={targetHref({screen:'applications',profileId:app.profile_id,target:{kind:'application',id:app.id}})}>Открыть заявку: {app.label}</a>)}{contextResult&&actions.current&&<a className="btn btn--sm" href={journeyHref({screen:'applications',profileId:actions.activeCase!,resultId:contextResult.id,action:'new'})}>Создать заявку по программе</a>}<a href="#/documents">Все документы</a></div></section>}
      {contextResult&&!contextMissing&&!bookDetail&&<details className="journey-task-create"><summary>Добавить задачу по требованию программы</summary><DocumentSourceBindings key={`${actions.caseKey}:${contextResult.id}:${selectedApp?.id??''}`} controller={actions} programmeId={contextResult.id} applicationId={selectedApp?.id}/></details>}
      {targetMissing&&<Notice kind="warn">{t('today.targetMissing')}</Notice>}
      {actions.loading&&<Loading label={t('documents.loading')}/>}
      {actions.error&&<Notice kind="risk">{actions.error}</Notice>}
      {feedback?.key===actions.caseKey&&<Notice kind={feedback.value==='saved'?'info':'warn'}>{feedback.value==='saved'?t('documents.saved'):feedback.value==='invalid'?t('documents.invalid'):t('documents.saveUnknown')}</Notice>}
      {(!actions.loading||actions.current)&&<BookDocumentsTable key={actions.caseKey} tasks={shownTasks} applicationId={selectedApp?.id} opened={bookOpened?.key===actions.caseKey?tasks.find(task=>task.id===bookOpened.id)??null:null} canEdit={canEdit} reviews={actions.current?.document_report_reviews.filter(review=>review.reasons.length>0).map(review=>review.task_id)??[]}
        onOpen={task=>{setBookOpened({key:actions.caseKey,id:task.id});window.location.hash=targetHref({screen:'documents',profileId:task.profile_id,target:{kind:'document_task',id:task.id}});}} onBack={()=>{setBookOpened(null);setDraft(null);window.location.hash=selectedApp?journeyHref({screen:'documents',profileId:actions.activeCase!,resultId:contextResult?.id,applicationId:selectedApp.id}):'#/documents';}} onAdd={()=>open('new')} onEdit={task=>{open('details',task);if(selectedApp&&task.application_id===null)setDraft(old=>old?{...old,applicationId:selectedApp.id}:old);}} onReport={task=>open('report',task)} onRemove={task=>open('remove',task)} onHistory={async task=>{const key=actions.caseKey;if(await actions.loadHistory()&&liveKey.current===key)setHistoryTask({key,id:task.id});}}/>}
    </>}
    {draft && <Panel title={draft.mode === 'new' ? t('documents.addPersonal') : draft.label}>
      <form ref={editorRef} className="stack journey-editor" onSubmit={event => { event.preventDefault(); void save(); }}>
        <fieldset className="stack" disabled={draft.attempted || actions.sending} style={{ border: 0, margin: 0, padding: 0, minWidth: 0 }}>
        {draft.baseRevision !== actions.current?.revision && <Notice kind="warn">{t('documents.draftConflict')}</Notice>}
        {(draft.mode === 'new' || draft.mode === 'details') && <>
          <label className="stack stack--tight">{t('documents.taskName')}<input autoFocus required maxLength={200} value={draft.label} onChange={event => change({ label: event.target.value })} /></label>
          <label className="stack stack--tight">{t('documents.responsible')}<select value={draft.responsible} onChange={event => change({ responsible: event.target.value as ResponsibleActor })}>
            {Object.entries(actorKeys).map(([actor, key]) => <option key={actor} value={actor}>{t(key)}</option>)}
          </select></label>
          <label className="stack stack--tight">{t('documents.application')}<select value={draft.applicationId} onChange={event => change({ applicationId: event.target.value })}>
            <option value="">{t('documents.noApplication')}</option>{applications.map(app => <option key={app.id} value={app.id}>{app.label}</option>)}
          </select></label>
          <fieldset className="stack"><legend>{t('documents.dependencies')}</legend>
            {tasks.filter(task => task.id !== draft.taskId).map(task => <label className="row" key={task.id}><input type="checkbox" checked={draft.dependencies.includes(task.id)} onChange={event => change({ dependencies: event.target.checked ? [...draft.dependencies, task.id] : draft.dependencies.filter(id => id !== task.id) })} />{task.personal.label}</label>)}
            {draft.dependencies.filter(id => !tasks.some(task => task.id === id)).map(id => <label className="row" key={id}><input type="checkbox" checked onChange={() => change({ dependencies: draft.dependencies.filter(item => item !== id) })} />{t('documents.missingDependency')}</label>)}
          </fieldset>
        </>}
        {draft.mode === 'remove' ? <Notice kind="warn">{t('actions.removalHint')}</Notice> : draft.mode !== 'report' ? <>
          <label className="stack stack--tight">{t('documents.personalDate')}<input type="date" value={draft.due} onChange={event => change({ due: event.target.value })} /></label>
          <label className="stack stack--tight">{t('documents.notes')}<textarea maxLength={2000} value={draft.notes} onChange={event => change({ notes: event.target.value })} /></label>
        </> : <>
          <label className="stack stack--tight">{t('documents.reportStatus')}<select value={draft.report} onChange={event => change({ report: event.target.value as DocumentReportState })}>
            {Object.entries(reportKeys).map(([status, key]) => <option key={status} value={status}>{t(key)}</option>)}
          </select></label>
          <label className="stack stack--tight">{t('documents.reportedOn')}<input type="date" value={draft.reportedOn} onChange={event => change({ reportedOn: event.target.value })} /></label>
        </>}
        {draft.mode !== 'remove' && <><label className="stack stack--tight">{t('documents.timezone')}<input maxLength={80} placeholder="Asia/Almaty" value={draft.zone} onChange={event => change({ zone: event.target.value })} /></label>
        <p className="small muted">{t('documents.dateHint')}</p></>}
        {draft.mode !== 'new' && <label className="row"><input type="checkbox" checked={draft.confirmed} onChange={event => change({ confirmed: event.target.checked })} />{t(draft.mode === 'report' ? 'documents.confirmReport' : draft.mode === 'remove' ? 'actions.confirmRemoval' : 'documents.confirmMetadata')}</label>}
        </fieldset>
        <div className="row">
          <button type="submit" className="btn btn--primary" disabled={!canEdit || draft.attempted || (draft.mode !== 'new' && !draft.confirmed)}>{t('documents.save')}</button>
          <button type="button" className="btn btn--ghost" disabled={actions.sending} onClick={() => setDraft(null)}>{t('documents.cancel')}</button>
        </div>
      </form>
    </Panel>}
    {historyTask?.key === actions.caseKey && actions.historyPage && <Panel title={t('documents.history')}>
      <div className="stack">
        {actions.historyPage.events.filter(event => event.affected_refs.document_task_ids.includes(historyTask.id)).map(event => <div key={event.event_id} className="small">
          {t('documents.recordedAt')}: {dateTime(event.accepted_at)}
          {' · '}{event.applied_delta.removed_document_task ? `${t('actions.removedPersonal')}: ${event.applied_delta.removed_document_task.personal.label}` : 'personal' in event.request ? event.request.personal.label : t('documents.personalChange')}
        </div>)}
        {actions.historyPage.next_after_revision !== null && <button type="button" className="btn btn--ghost"
          onClick={() => { void actions.loadHistory(actions.historyPage?.next_after_revision ?? 0); }}>{t('documents.moreHistory')}</button>}
      </div>
    </Panel>}
    {locale==='en'?<><DocumentSourceBindings controller={actions}/><LegacyDocumentImport controller={actions}/></>:<details className="book-documents__bindings"><summary>Требования, привязки к источникам и прежние отметки</summary>{!contextResult&&<DocumentSourceBindings controller={actions}/>}<LegacyDocumentImport controller={actions}/></details>}
    <AdmissionsRecoveryPanel controller={actions} />
  </div>;
}

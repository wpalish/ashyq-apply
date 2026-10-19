import { catalogueUserNotes,preserveCatalogueNotes,catalogueNoteSpace } from '@/lib/officialProgrammes';
import { ProgrammeJourney } from '@/components/ProgrammeJourney';
import { useJourneyRoute } from '@/lib/programmeJourney';
import { targetHref } from '@/lib/admissionsNavigation';
/** Own G3 application actions. University submission is never performed here. */
import { BookApplications } from '@/components/BookApplications';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import './ApplicationsPanel.css';
import { AdmissionsRecoveryPanel } from '@/components/AdmissionsRecoveryPanel';
import { isSafeHref, Loading, Notice, Panel } from '@/components/primitives';
import { dateTime } from '@/lib/format';
import { useAdmissionsActions } from '@/lib/useAdmissionsActions';
import { useStore } from '@/lib/store';
import { useAdmissionsTarget } from '@/lib/admissionsNavigation';
import { useTranslation } from '@/lib/useTranslation';
import type { MessageKey } from '@/lib/i18n';
import { isActionRequest } from '@/types/admissionsActions';
import type { ActionEventRefV1, ActionRequest, ApplicationRecord, ApplicationStatus, EnteredOrUnknownText } from '@/types/admissionsActions';

type Draft = { caseKey: string; revision: number; mode: 'new' | 'details' | 'context' | 'remove' | 'submission' | 'withdrawal' | 'correction';
  appId: string | null; awardId: string | null; label: string; resultId: string; university: string; programme: string; award: string;
  purpose: 'admission' | 'scholarship'; intake: string; route: string; due: string; zone: string; notes: string;
  on: string; time: string; channel: string; reference: string; documents: string[]; confirmed: boolean;
  attempted: boolean; prior: ActionEventRefV1 | null; replacement: 'submission' | 'withdrawal' | 'planning' };
const statusKeys: Record<ApplicationStatus, MessageKey> = { planning: 'applications.planning', preparing: 'applications.preparing',
  submitted_declared: 'applications.submitted', withdrawn_declared: 'applications.withdrawn' };
const entered = (value: string): EnteredOrUnknownText => value ? { state: 'applicant_entered', value } : { state: 'unknown' };

export function ApplicationsPanel({pageHeading=false}:{pageHeading?:boolean}={}) {
  const actions = useAdmissionsActions(); const store = useStore(); const { t, locale } = useTranslation();
  const [bookOpened,setBookOpened]=useState<{key:string;id:string}|null>(null);
  const journey=useJourneyRoute(); const openedJourney=useRef<string|null>(null);
  const target = useAdmissionsTarget(); const openedTarget = useRef<string | null>(null);
  const attemptedDraft = useRef<Draft | null>(null);
  const liveKey = useRef(actions.caseKey); liveKey.current = actions.caseKey;
  const editorRef=useRef<HTMLFormElement>(null);
  const [storedDraft, setDraft] = useState<Draft | null>(null);
  const [feedback, setFeedback] = useState<{ key: string; value: 'saved' | 'unknown' | 'invalid' } | null>(null);
  const [historyFor, setHistoryFor] = useState<{ key: string; id: string } | null>(null);
  const draft = storedDraft?.caseKey === actions.caseKey ? storedDraft : null;
  const editorKey=draft?JSON.stringify([draft.caseKey,draft.mode,draft.appId]):null;
  const focusEditor=Boolean(draft&&!draft.attempted);
  useEffect(()=>{
    if(!focusEditor)return;
    const frame=window.requestAnimationFrame(()=>editorRef.current?.querySelector<HTMLElement>('input:not([type="checkbox"]):not(:disabled),select:not(:disabled),textarea:not(:disabled)')?.focus());
    return()=>window.cancelAnimationFrame(frame);
  },[editorKey,focusEditor]);

  const currentApplications = actions.current?.state?.applications;
  const applications = useMemo(() => currentApplications ?? [], [currentApplications]);
  const tasks = actions.current?.state?.document_tasks ?? [];
  const selectedResults = store.run?.profile_id === actions.activeCase
    ? store.results.filter(result => result.user_decision === 'approved' || result.user_decision === 'maybe') : [];
  const journeyOwned=journey?.screen==='applications'&&journey.profileId===actions.activeCase;
  const contextApplication=journeyOwned?applications.find(app=>app.id===journey.applicationId):undefined;
  const contextResult=journeyOwned&&store.run?.profile_id===actions.activeCase?store.results.find(result=>result.id===journey.resultId&&(selectedResults.some(row=>row.id===result.id)||contextApplication?.target.result_id===result.id)):undefined;
  const contextMissing=Boolean(journey?.screen==='applications'&&(!journeyOwned||actions.current!==null&&(journey.resultId&&!contextResult||journey.applicationId&&!contextApplication||contextApplication&&journey.resultId&&contextApplication.target.result_id!==journey.resultId)));
  const shownApplications=contextResult&&!contextMissing?applications.filter(app=>app.target.result_id===contextResult.id):applications;
  const canEdit = actions.current !== null && !actions.loading && !actions.sending && actions.journalError === null;
  const change = (patch: Partial<Draft>) => setDraft(old => old?.caseKey === actions.caseKey && !old.attempted ? { ...old, ...patch } : old);
  const open = useCallback((mode: Draft['mode'], app?: ApplicationRecord, prior?: ActionEventRefV1) => {
    if (!actions.current || !canEdit) return;
    if (prior && prior.revision > actions.current.revision) { void actions.refresh(); return; }
    const target = app?.target;
    setFeedback(null);
    if(locale!=='en'&&app)setBookOpened({key:actions.caseKey,id:app.id});
    setDraft({ caseKey: actions.caseKey, revision: actions.current.revision, mode, appId: app?.id ?? null, awardId: target?.award_id ?? null,
      label: app?.label ?? '', resultId: target?.result_id ?? '', university: target && 'university' in target ? target.university : '',
      programme: target && 'programme' in target && target.programme.state === 'applicant_entered' ? target.programme.value : '',
      award: target && 'award' in target && target.award.state === 'applicant_entered' ? target.award.value : '', purpose: target?.purpose ?? 'admission', intake: target?.intake.state === 'applicant_entered' ? target.intake.value : '',
      route: target?.route.state === 'applicant_entered' ? target.route.value : '',
      due: app?.details.due?.local_date ?? '', notes: app?catalogueUserNotes(app.details.notes):'',
      zone: mode === 'details' || mode === 'context' ? app?.details.due?.timezone ?? '' : '', on: '', time: '', channel: '', reference: '',
      documents: [], confirmed: false, attempted: false, prior: prior ?? null, replacement: 'planning' });
  }, [actions, canEdit, locale]);
  const targetKey = target?.target.kind === 'application' ? JSON.stringify([actions.caseKey, target]) : null;
  const targetMissing = targetKey !== null && (target?.profileId !== actions.activeCase || (actions.current !== null && !applications.some(item => item.id === target?.target.id)));
  useEffect(() => {
    if (!targetKey || openedTarget.current === targetKey || targetMissing || !canEdit || target?.profileId !== actions.activeCase) return;
    const exact = applications.find(item => item.id === target?.target.id); if (!exact) return;
    openedTarget.current = targetKey; if(locale!=='en')setBookOpened({key:actions.caseKey,id:exact.id});else open('details', exact);
  }, [targetKey, targetMissing, canEdit, target, actions.activeCase, applications, open, locale, actions.caseKey]);
  const journeyKey=journeyOwned&&!contextMissing?JSON.stringify([actions.caseKey,journey]):null;
  useEffect(()=>{
    if(!journeyKey||openedJourney.current===journeyKey||!canEdit)return;
    if(contextApplication){openedJourney.current=journeyKey;setBookOpened({key:actions.caseKey,id:contextApplication.id});}
    else if(contextResult&&journey?.action==='new'){
      openedJourney.current=journeyKey;open('new');
      setDraft(old=>old?.caseKey===actions.caseKey?{...old,resultId:contextResult.id,label:`${contextResult.university} - ${contextResult.program}`,intake:contextResult.intake??''}:old);
    }
  },[journeyKey,canEdit,contextApplication,contextResult,journey?.action,open,actions.caseKey]);
  const startPreparing = async (app: ApplicationRecord) => {
    if (!canEdit || !actions.current || app.status !== 'planning') return;
    const key = actions.caseKey; const revision = actions.current.revision;
    try {
      const outcome = await actions.submit({ schema_version: 'admissions-actions-v1', kind: 'set_planning_status',
        application_id: app.id, status: 'preparing', expected_revision: revision, client_write_uuid: crypto.randomUUID() });
      if (liveKey.current === key) setFeedback({ key, value: outcome.accepted ? 'saved' : 'unknown' });
    } catch { if (liveKey.current === key) setFeedback({ key, value: 'invalid' }); }
  };
  const save = async () => {
    if (!draft || draft.attempted || attemptedDraft.current === draft || !canEdit || (draft.mode !== 'details' && !draft.confirmed)) return;
    const captured = draft;
    try {
      const base = { schema_version: 'admissions-actions-v1' as const, client_write_uuid: crypto.randomUUID(), expected_revision: captured.revision };
      const originalNotes=applications.find(app=>app.id===captured.appId)?.details.notes;
      const savedNotes=originalNotes?preserveCatalogueNotes(originalNotes,captured.notes):captured.notes;
      if(savedNotes.length>2000)throw new Error('Notes exceed available space');
      const details = { notes: savedNotes, due: captured.due ? { origin: 'applicant_entered' as const,
        local_date: captured.due, timezone: captured.zone || null, official_deadline: false as const } : null };
      const moment = captured.on ? { local_date: captured.on, local_time: captured.time || null,
        timezone: captured.zone || null, origin: 'applicant_entered' as const } : null;
      const submission = moment ? { entered_at: moment, channel: captured.channel, reference: captured.reference,
        document_task_ids: captured.documents, confirmed_applicant_declaration: true as const } : null;
      const withdrawal = { entered_at: moment, notes: captured.notes, confirmed_applicant_declaration: true as const };
      let body: ActionRequest;
      if (captured.mode === 'new' || captured.mode === 'context') {
        if (captured.resultId) {
          // The exact own saved result is reviewed again on the server. No name matching.
          const retained = applications.find(app => app.id === captured.appId)?.target;
          if (!selectedResults.some(result => result.id === captured.resultId) && !(captured.mode === 'context' && retained?.result_id === captured.resultId)) throw new Error('Target changed');
          body = { ...base, kind: 'create_application', label: captured.label, details,
            target: { result_id: captured.resultId, purpose: captured.purpose, award_id: captured.awardId,
              intake: entered(captured.intake), route: entered(captured.route), confirmed_entered_context: true } };
        } else body = { ...base, schema_version: 'admissions-actions-v2', kind: 'create_application', label: captured.label, details,
          target: { origin: 'applicant_entered', result_id: null, award_id: null, purpose: captured.purpose,
            university: captured.university, programme: entered(captured.programme), award: entered(captured.award),
            intake: entered(captured.intake), route: entered(captured.route), confirmed_entered_context: true, official_verification: 'not_performed' } };
        if (captured.mode === 'context' && captured.appId) body = { ...base, schema_version: 'admissions-actions-v2', kind: 'set_personal_details',
          operation: 'application_context', target: { kind: 'application', id: captured.appId }, application_target: body.target,
          label: captured.label, details, confirmed_personal_context: true };
      } else if (captured.mode === 'remove' && captured.appId) body = { ...base, schema_version: 'admissions-actions-v2', kind: 'remove_personal_action',
        target: { kind: 'application', id: captured.appId }, confirmed_personal_removal: true };
      else if (captured.mode === 'details' && captured.appId) body = { ...base, kind: 'set_personal_details', target: { kind: 'application', id: captured.appId }, details };
      else if (captured.mode === 'submission' && captured.appId && submission) body = { ...base, kind: 'declare_submission', application_id: captured.appId, submission };
      else if (captured.mode === 'withdrawal' && captured.appId) body = { ...base, kind: 'declare_withdrawal', application_id: captured.appId, withdrawal };
      else if (captured.mode === 'correction' && captured.appId && captured.prior) {
        if (captured.replacement === 'submission' && !submission) throw new Error('Enter the event date');
        body = { ...base, kind: 'correct_declaration', application_id: captured.appId, prior_declaration: captured.prior,
          confirmed_correction: true, replacement: captured.replacement === 'submission' && submission ? { kind: 'submission', submission }
            : captured.replacement === 'withdrawal' ? { kind: 'withdrawal', withdrawal } : { kind: 'planning', status: 'preparing' } };
      } else return;
      if (!isActionRequest(body)) throw new Error('Entered fields are invalid');
      const pending = { ...captured, attempted: true }; attemptedDraft.current = captured;
      setDraft(old => old === captured ? pending : old);
      const outcome = await actions.submit(body);
      if (liveKey.current !== captured.caseKey) return;
      setFeedback({ key: captured.caseKey, value: outcome.accepted ? 'saved' : 'unknown' });
      if (outcome.accepted) {
        setDraft(old => old === pending ? null : old);
        const created=outcome.receipt?.kind==='create_application'?outcome.receipt.applied_delta.applications[0]:null;
        if(locale!=='en'&&captured.mode==='new'&&created&&outcome.currentRefreshed)window.location.hash=targetHref({screen:'applications',profileId:created.profile_id,target:{kind:'application',id:created.id}});
        if (captured.mode === 'remove' && captured.appId && await actions.loadHistory() && liveKey.current === captured.caseKey)
          setHistoryFor({ key: captured.caseKey, id: captured.appId });
      }
    } catch { if (liveKey.current === captured.caseKey) setFeedback({ key: captured.caseKey, value: 'invalid' }); }
  };
  const events = historyFor?.key === actions.caseKey ? actions.historyPage?.events.filter(event => event.affected_refs.application_ids.includes(historyFor.id)) ?? [] : [];
  const submissionForm = draft?.mode === 'submission' || (draft?.mode === 'correction' && draft.replacement === 'submission');
  const declarationForm = draft?.mode === 'submission' || draft?.mode === 'withdrawal' || draft?.mode === 'correction';
  const declaredContext = draft?.mode === 'context' && applications.some(app => app.id === draft.appId && (app.status === 'submitted_declared' || app.status === 'withdrawn_declared'));
  const removalHasLinks = draft?.mode === 'remove' && tasks.some(task => task.application_id === draft.appId);

  return <div className="stack stack--loose personal-applications" data-testid="personal-applications">
    {locale==='en'?<Panel title={t('applications.title')}>
      <div className="stack">
        <p className="small muted">{t('applications.hint')}</p>
        {targetMissing && <Notice kind="warn">{t('today.targetMissing')}</Notice>}
        {actions.loading && <Loading label={t('documents.loading')} />}
        {actions.error && <Notice kind="risk">{actions.error}</Notice>}
        {feedback?.key === actions.caseKey && <Notice kind={feedback.value === 'saved' ? 'info' : 'warn'}>{t(feedback.value === 'saved' ? 'documents.saved' : feedback.value === 'invalid' ? 'documents.invalid' : 'documents.saveUnknown')}</Notice>}
        {actions.current && applications.length === 0 && <p className="muted">{t('applications.empty')}</p>}
        <button type="button" className="btn btn--primary" disabled={!canEdit} onClick={() => open('new')}>{t('applications.add')}</button>
        {applications.map(app => {
          const linked = tasks.filter(task => task.application_id === app.id);
          const link = actions.current?.action_links.find(item => item.result_id === app.target.result_id)?.programme_information;
          return <article key={app.id} className="stack stack--tight" data-testid="personal-application">
            <h3>{app.label}</h3><p className="small">{t(statusKeys[app.status])}</p>
            {'university' in app.target && <p className="small">{app.target.university}{app.target.programme.state === 'applicant_entered' ? ` · ${app.target.programme.value}` : ''}</p>}
            <p className="small muted">{t('applications.context')}: {app.target.intake.state === 'applicant_entered' ? app.target.intake.value : t('applications.unknown')} · {app.target.route.state === 'applicant_entered' ? app.target.route.value : t('applications.unknown')}</p>
            {app.details.due && <p className="small">{t('documents.personalDate')}: {app.details.due.local_date} · {app.details.due.timezone ?? t('documents.zoneUnknown')}</p>}
            {app.details.notes && <p className="small">{app.details.notes}</p>}
            {link?.state === 'actionable_unverified' && link.href && isSafeHref(link.href)
              ? <a href={link.href} target="_blank" rel="noopener noreferrer">{t('applications.programmeLink')}</a> : <p className="small muted">{t('applications.requirementsUnknown')}</p>}
            {linked.length > 0 && <ul>{linked.map(task => <li key={task.id}>{task.personal.label}</li>)}</ul>}
            <div className="row">
              {app.status === 'planning' && <button type="button" className="btn" disabled={!canEdit} onClick={() => void startPreparing(app)}>{t('applications.startPreparing')}</button>}
              <button type="button" className="btn" disabled={!canEdit} onClick={() => open('details', app)}>{t('documents.editDetails')}</button>
              <button type="button" className="btn" disabled={!canEdit} onClick={() => open('context', app)}>{t('applications.editContext')}</button>
              <button type="button" className="btn" disabled={!canEdit} onClick={() => open('remove', app)}>{t('actions.removePersonal')}</button>
              {(app.status === 'planning' || app.status === 'preparing') && <button type="button" className="btn" disabled={!canEdit} onClick={() => open('submission', app)}>{t('applications.declareSubmission')}</button>}
              {app.status !== 'withdrawn_declared' && <button type="button" className="btn" disabled={!canEdit} onClick={() => open('withdrawal', app)}>{t('applications.declareWithdrawal')}</button>}
              <button type="button" className="btn" disabled={actions.loading} onClick={async () => { const key = actions.caseKey; if (await actions.loadHistory() && liveKey.current === key) setHistoryFor({ key, id: app.id }); }}>{t('documents.history')}</button>
            </div>
          </article>;
        })}
      </div>
    </Panel>:<>
      {contextMissing&&<Notice kind="warn">Программа или заявка недоступна в текущем профиле. Выбери свою запись ниже.</Notice>}
      {contextResult&&!contextMissing&&<div className="journey-context"><ProgrammeJourney profileId={actions.activeCase!} resultId={contextResult.id} applicationId={contextApplication?.id} current="applications"/><h2>{contextResult.university}</h2><p>{contextResult.program}</p><a href="#/applications">Все заявки</a></div>}
      {targetMissing&&<Notice kind="warn">{t('today.targetMissing')}</Notice>}
      {actions.loading&&<Loading label={t('documents.loading')}/>}
      {actions.error&&<Notice kind="risk">{actions.error}</Notice>}
      {feedback?.key===actions.caseKey&&<Notice kind={feedback.value==='saved'?'info':'warn'}>{t(feedback.value==='saved'?'documents.saved':feedback.value==='invalid'?'documents.invalid':'documents.saveUnknown')}</Notice>}
      {(!actions.loading||actions.current)&&<BookApplications controller={actions} reviews={actions.current?.document_report_reviews.filter(review=>review.reasons.length>0).map(review=>review.task_id)??[]} key={actions.caseKey} applications={shownApplications} tasks={tasks} results={store.run?.profile_id===actions.activeCase?store.results:[]} links={actions.current?.action_links??[]} canEdit={canEdit} pageHeading={pageHeading}
        opened={bookOpened?.key===actions.caseKey?applications.find(app=>app.id===bookOpened.id)??null:null} onOpen={app=>{setBookOpened({key:actions.caseKey,id:app.id});window.location.hash=targetHref({screen:'applications',profileId:app.profile_id,target:{kind:'application',id:app.id}});}} onBack={()=>{setBookOpened(null);setDraft(null);window.location.hash='#/applications';}} onAdd={()=>{open('new');if(contextResult&&!contextMissing)setDraft(old=>old?{...old,resultId:contextResult.id,label:`${contextResult.university} - ${contextResult.program}`,intake:contextResult.intake??''}:old);}} onEdit={open} onPrepare={app=>void startPreparing(app)} onHistory={async app=>{const key=actions.caseKey;if(await actions.loadHistory()&&liveKey.current===key)setHistoryFor({key,id:app.id});}}/>}
    </>}
    {draft && <Panel title={draft.mode === 'new' ? t('applications.add') : draft.label}>
      <form ref={editorRef} className="stack journey-editor" onSubmit={event => { event.preventDefault(); void save(); }}>
        <fieldset className="stack" disabled={draft.attempted || actions.sending} style={{ border: 0, margin: 0, padding: 0, minWidth: 0 }}>
        {draft.revision !== actions.current?.revision && <Notice kind="warn">{t('documents.draftConflict')}</Notice>}
        {(draft.mode === 'new' || draft.mode === 'context') && <>
          <label className="stack stack--tight">{t('applications.label')}<input autoFocus required maxLength={200} value={draft.label} onChange={event => change({ label: event.target.value })} /></label>
          {draft.mode === 'context' && <Notice kind="warn">{t('applications.contextReviewHint')}</Notice>}
          <fieldset className="stack" disabled={declaredContext} style={{ border: 0, margin: 0, padding: 0, minWidth: 0 }}>
          {declaredContext && <p className="small">{t('applications.declaredContextLocked')}</p>}
          <label className="stack stack--tight">{t('applications.target')}<select value={draft.resultId} onChange={event => change({ resultId: event.target.value, purpose: 'admission', award: '', awardId: null })}>
            <option value="">{t('applications.manual')}</option>
            {draft.resultId && !selectedResults.some(result => result.id === draft.resultId) && <option value={draft.resultId}>{t('applications.retainedReference')}</option>}{selectedResults.map(result => <option key={result.id} value={result.id}>{result.university} · {result.program}</option>)}
          </select></label>
          {!draft.resultId && <>
            <label className="stack stack--tight">{t('applications.university')}<input required maxLength={200} value={draft.university} onChange={event => change({ university: event.target.value })} /></label>
            <label className="stack stack--tight">{t('applications.programme')}<input maxLength={200} value={draft.programme} onChange={event => change({ programme: event.target.value })} /></label>
            <label className="stack stack--tight">{t('applications.purpose')}<select value={draft.purpose} onChange={event => change({ purpose: event.target.value as Draft['purpose'], award: '' })}>
              <option value="admission">{t('applications.admission')}</option><option value="scholarship">{t('applications.scholarship')}</option>
            </select></label>
            {draft.purpose === 'scholarship' && <label className="stack stack--tight">{t('applications.award')}<input maxLength={200} value={draft.award} onChange={event => change({ award: event.target.value })} /></label>}
          </>}
          <label className="stack stack--tight">{t('applications.intake')}<input maxLength={200} value={draft.intake} onChange={event => change({ intake: event.target.value })} /></label>
          <label className="stack stack--tight">{t('applications.route')}<input maxLength={200} value={draft.route} onChange={event => change({ route: event.target.value })} /></label>
          </fieldset>
        </>}
        {draft.mode === 'correction' && <label className="stack stack--tight">{t('applications.replacement')}<select value={draft.replacement} onChange={event => change({ replacement: event.target.value as Draft['replacement'] })}>
          <option value="planning">{t('applications.preparing')}</option><option value="submission">{t('applications.submitted')}</option><option value="withdrawal">{t('applications.withdrawn')}</option>
        </select></label>}
        {draft.mode === 'remove' ? <><Notice kind="warn">{t('actions.removalHint')}</Notice>{removalHasLinks && <Notice kind="warn">{t('applications.removalHasLinks')}</Notice>}</> : declarationForm ? <>
          <Notice kind="warn">{t('applications.declarationHint')}</Notice>
          <label className="stack stack--tight">{t('documents.reportedOn')}<input autoFocus required={submissionForm} type="date" value={draft.on} onChange={event => change({ on: event.target.value })} /></label>
          <label className="stack stack--tight">{t('applications.eventTime')}<input type="time" value={draft.time} onChange={event => change({ time: event.target.value })} /></label>
          {submissionForm && <>
            <label className="stack stack--tight">{t('applications.channel')}<input required maxLength={200} value={draft.channel} onChange={event => change({ channel: event.target.value })} /></label>
            <label className="stack stack--tight">{t('applications.reference')}<input maxLength={2000} value={draft.reference} onChange={event => change({ reference: event.target.value })} /></label>
            {tasks.filter(task => task.application_id === draft.appId).map(task => <label className="row" key={task.id}><input type="checkbox" checked={draft.documents.includes(task.id)} onChange={event => change({ documents: event.target.checked ? [...draft.documents, task.id] : draft.documents.filter(id => id !== task.id) })} />{task.personal.label}</label>)}
          </>}
        </> : <label className="stack stack--tight">{t('documents.personalDate')}<input autoFocus={draft.mode==='details'} type="date" value={draft.due} onChange={event => change({ due: event.target.value })} /></label>}
        {draft.mode !== 'remove' && <><label className="stack stack--tight">{t('documents.timezone')}<input maxLength={80} placeholder="Asia/Almaty" value={draft.zone} onChange={event => change({ zone: event.target.value })} /></label>
        <p className="small muted">{t('documents.zoneUnknown')}</p>
        <label className="stack stack--tight">{t('documents.notes')}<textarea maxLength={catalogueNoteSpace(applications.find(app=>app.id===draft.appId)?.details.notes??'')} value={draft.notes} onChange={event => change({ notes: event.target.value })} /></label></>}
        {draft.mode !== 'details' && <label className="row"><input type="checkbox" checked={draft.confirmed} onChange={event => change({ confirmed: event.target.checked })} />{t(draft.mode === 'remove' ? 'actions.confirmRemoval' : 'applications.confirm')}</label>}
        </fieldset>
        <div className="row"><button type="submit" className="btn btn--primary" disabled={!canEdit || draft.attempted || removalHasLinks || (draft.mode !== 'details' && !draft.confirmed)}>{t('documents.save')}</button>
          <button type="button" className="btn" disabled={actions.sending} onClick={() => setDraft(null)}>{t('documents.cancel')}</button></div>
      </form>
    </Panel>}
    {historyFor?.key === actions.caseKey && <Panel title={t('documents.history')}><div className="stack">
      {events.length === 0 && <p>{t('applications.noHistory')}</p>}
      {events.map(event => <article key={event.event_id} className="stack stack--tight"><p>{dateTime(event.accepted_at)} · {t('applications.serverEvent')}</p>
        {event.applied_delta.removed_application ? <p>{t('actions.removedPersonal')}: {event.applied_delta.removed_application.label}</p>
          : <p>{t(statusKeys[event.applied_delta.applications[0]?.status ?? 'planning'])}</p>}
        {event.applied_delta.declaration?.entered.entered_at && <p>{t('documents.reportedOn')}: {event.applied_delta.declaration.entered.entered_at.local_date} · {event.applied_delta.declaration.entered.entered_at.timezone ?? t('documents.zoneUnknown')}</p>}
        {(event.kind === 'declare_submission' || event.kind === 'declare_withdrawal' || event.kind === 'correct_declaration') && <button type="button" className="btn" disabled={!canEdit} onClick={() => {
          const app = applications.find(item => item.id === historyFor.id); if (app && (event.kind === 'declare_submission' || event.kind === 'declare_withdrawal' || event.kind === 'correct_declaration')) open('correction', app, { event_id: event.event_id, revision: event.revision, kind: event.kind });
        }}>{t('applications.correct')}</button>}
      </article>)}
      {actions.historyPage?.next_after_revision !== null && actions.historyPage?.next_after_revision !== undefined && <button type="button" className="btn" onClick={() => void actions.loadHistory(actions.historyPage?.next_after_revision ?? 0)}>{t('applications.moreHistory')}</button>}
    </div></Panel>}
    <AdmissionsRecoveryPanel controller={actions} />
  </div>;
}

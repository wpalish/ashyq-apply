import { Chip, Loading, Notice, Panel } from './primitives';
import { useAdmissionsToday } from '@/lib/useAdmissionsToday';
import { useAdmissionsActions } from '@/lib/useAdmissionsActions';
import { targetHref } from '@/lib/admissionsNavigation';
import { dateTime, localDate } from '@/lib/format';
import { useTranslation } from '@/lib/useTranslation';
import type { TodayCardV1 } from '@/types/admissionsActions';
import type { MessageKey } from '@/lib/i18n';
const reasons: Record<TodayCardV1['dependency_reasons'][number], MessageKey> = {
  dependency_missing: 'today.dependencyMissing', dependency_cycle: 'today.dependencyCycle', dependency_not_reported_ready: 'today.dependencyNotReady',
  report_refers_to_previous_binding: 'today.previousBinding', not_needed_is_not_a_waiver: 'today.notWaiver', application_context_changed: 'today.contextChanged',
};
export function AdmissionsTodayPanel() {
  const today = useAdmissionsToday(); const actions = useAdmissionsActions(); const { t } = useTranslation();
  const value = today.value;
  if (!today.profileId) return null;
  const groups: { title: MessageKey; cards: TodayCardV1[] }[] = value ? [
    { title: 'today.earlierDates', cards: value.overdue_personal }, { title: 'today.current', cards: value.today_personal },
    { title: 'today.future', cards: value.future.filter(card => card.reason !== 'accepted_study_action') }, { title: 'today.undated', cards: value.undated_personal },
  ] : [];
  const study = value ? [...value.today_study, ...value.future.filter(card => card.reason === 'accepted_study_action')] : [];
  const matchingDetails = value && actions.current?.profile_id === value.profile_id && actions.current.revision === value.action_revision;
  const renderCard = (card: TodayCardV1) => {
    const ref = card.target;
    const name = matchingDetails && ref?.kind === 'document_task' ? actions.current?.state?.document_tasks.find(task => task.id === ref.id)?.personal.label
      : ref?.kind === 'application' ? value?.application_summaries.find(app => app.id === ref.id)?.label : null;
    const href = value && ref && card.actionable && !value.needs_refresh ? ref.kind === 'document_task' ? targetHref({ profileId: value.profile_id, screen: 'documents', target: ref })
      : ref.kind === 'application' ? targetHref({ profileId: value.profile_id, screen: 'approved', target: ref })
        : ref.kind === 'lesson' || ref.kind === 'attempt_review' ? targetHref({ profileId: value.profile_id, screen: 'preparation', target: ref }) : null : null;
    return <article className="stack stack--tight" key={card.id} data-testid="today-action">
      <h4>{name || t(card.reason === 'personal_application_action' ? 'today.application' : card.reason === 'personal_document_action' ? 'today.document' : 'today.study')}</h4>
      <p className="small">{card.date.local_date ? localDate(card.date.local_date) : t('today.dateUnknown')} · {card.date.timezone ?? t('dates.zoneUnknown')}</p>
      {card.date.fallback_display_only && <p className="xs muted">{t('today.fallbackDate')}</p>}
      {card.planned_minutes !== null && <p className="small">{card.planned_minutes} {t('today.minutes')}</p>}
      {card.dependency_reasons.length > 0 && <ul className="small">{card.dependency_reasons.map(reason => <li key={reason}>{t(reasons[reason])}</li>)}</ul>}
      {card.source_state !== 'applicant_entered' && card.source_state !== 'current_reference' && <Chip tone="warn">{t('today.sourceReview')}</Chip>}
      <div className="row">{href ? <a className="btn btn--sm" href={href}>{t('today.openExact')}</a> : <span className="small muted">{t('today.targetUnavailable')}</span>}
        {value && card.target_result_id && <a className="btn btn--sm btn--ghost" href={targetHref({ profileId: value.profile_id, screen: 'sources', target: { kind: 'result', id: card.target_result_id } })}>{t('today.openEvidence')}</a>}</div>
    </article>;
  };
  return <Panel title={t('today.title')}><div className="stack" data-testid="admissions-today">
    <p className="small muted">{t('today.hint')}</p>
    {today.loading && <Loading label={t('today.loading')} />}
    {today.error && <Notice kind="warn">{today.error}{value && ` ${t('today.lastConfirmed')}`}</Notice>}
    {value && <>
      <p className="xs muted">{t('today.observed')}: {dateTime(value.as_of)}</p>
      {(value.needs_refresh || (actions.current && !matchingDetails)) && <Notice kind="warn">{t('today.refreshNeeded')}</Notice>}
      {value.action_state === 'unavailable' && <Notice kind="warn">{t('today.unavailable')}</Notice>}
      {groups.every(group => group.cards.length === 0) && value.action_state !== 'unavailable' && <p>{t('today.empty')}</p>}
      {groups.filter(group => group.cards.length > 0).map(group => <section className="stack" key={group.title}><h3>{t(group.title)}</h3>{group.cards.map(renderCard)}</section>)}
      {study.length > 0 && <details><summary>{t('today.optionalStudy')}</summary><p className="small muted">{t('preparation.optionalHint')}</p><div className="stack">{study.map(renderCard)}</div></details>}
    </>}
    <div className="row"><button type="button" className="btn btn--sm" disabled={today.loading} onClick={() => { void today.refresh(); void actions.refresh(); }}>{t('today.refresh')}</button>
      <a className="btn btn--sm" href="#/documents">{t('documents.addPersonal')}</a><a className="btn btn--sm" href="#/approved">{t('applications.add')}</a></div>
  </div></Panel>;
}

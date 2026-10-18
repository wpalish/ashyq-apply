/** Read-only presentation of the existing, validated Today projection. */
import { targetHref } from './admissionsNavigation';
import type { ActionsCurrentOut, TodayCardV1, TodayProjectionV1 } from '@/types/admissionsActions';

export function bookTaskView(card: TodayCardV1, projection: TodayProjectionV1, current: ActionsCurrentOut | null) {
  const ref = card.target;
  const aligned = current?.profile_id === projection.profile_id && current.revision === projection.action_revision;
  const personal = aligned && ref?.kind === 'document_task'
    ? current.state?.document_tasks.find(task => task.id === ref.id) : null;
  const application = ref?.kind === 'application'
    ? projection.application_summaries.find(item => item.id === ref.id) : null;
  const label = personal?.personal.label || application?.label
    || (card.reason === 'personal_document_action' ? 'Задача по документам' : card.reason === 'accepted_study_action' ? 'Дополнительная подготовка' : 'Задача по заявке');
  let href: string | null = null;
  if (ref && card.actionable && !projection.needs_refresh && projection.consistency !== 'mixed_revision') {
    if (ref.kind === 'document_task') href = targetHref({ profileId:projection.profile_id, screen:'documents', target:ref });
    else if (ref.kind === 'application') href = targetHref({ profileId:projection.profile_id, screen:'approved', target:ref });
    else href = targetHref({ profileId:projection.profile_id, screen:'preparation', target:ref });
  }
  return { label, href, detailsAligned:aligned, sourceLabel:card.source_state === 'applicant_entered' ? 'Личная задача' : card.source_state === 'current_reference' ? 'Связано с источником' : 'Нужна проверка источника' };
}

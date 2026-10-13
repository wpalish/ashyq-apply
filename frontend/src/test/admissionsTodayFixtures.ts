/** Synthetic read-only Today DTO, no native API acceptance claim. */
import { emptyActions } from './admissionsFixtures';
import type { TodayProjectionV1 } from '@/types/admissionsActions';
export function emptyToday(profile = 'A'): TodayProjectionV1 {
  const time = emptyActions().observed_at;
  return { schema_version: 'admissions-today-v1', profile_id: profile, as_of: time, display_timezone: 'UTC', action_state: 'absent', action_revision: 0, action_digest: null, action_observed_at: time,
    active_plan: { origin: 'none', selection_source: 'derived_backward_default', state: 'absent', selection: null, current_observed_head: null, observed_at: time, goal_result_ids: [], study_actions: [], allocated_minutes: null, needs_review: false },
    preparation_access: { allowed: false, reason: 'unavailable', starts_at: null, ends_at: null, development_only: false, observed_at: time },
    current_source_statuses: [], consistency: 'component_reads', needs_refresh: false, notices: [], overdue_personal: [], today_study: [], today_personal: [], future: [], undated_personal: [], application_summaries: [], workload: 'unknown', allocated_study_minutes: null, personal_minutes: 'not_estimated', readiness: 'not_assessed' };
}

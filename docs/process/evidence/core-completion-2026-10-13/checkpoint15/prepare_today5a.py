from pathlib import Path
import hashlib,json
s=Path(__file__).resolve().parent;b=s.parents[1];repo=b/'work/unimatch-calendar-materials';out=s/'today5a-proposal';out.mkdir(exist_ok=False)
paths=['frontend/src/types/admissionsActions.ts','frontend/src/lib/useAdmissionsToday.ts','frontend/src/lib/useAdmissionsToday.test.tsx','frontend/src/lib/admissionsNavigation.ts','frontend/src/lib/admissionsNavigation.test.ts','frontend/src/components/AdmissionsTodayPanel.tsx','frontend/src/components/AdmissionsTodayPanel.test.tsx','frontend/src/test/admissionsTodayFixtures.ts','frontend/src/screens/HomeScreen.tsx','frontend/src/screens/PersonalDocumentsPanel.tsx','frontend/src/screens/PersonalDocumentsPanel.test.tsx','frontend/src/screens/ApplicationsPanel.tsx','frontend/src/screens/ApplicationsPanel.test.tsx','frontend/src/screens/SourcesScreen.tsx','frontend/src/screens/SourcesScreen.test.tsx','frontend/src/screens/PreparationScreen.tsx','frontend/src/lib/i18n.ts'];rows={};h=lambda raw:hashlib.sha256(raw).hexdigest()
for p in paths:
 f=repo/p;raw=f.read_bytes() if f.exists() else None;rows[p]=h(raw) if raw is not None else None
 if raw is not None:q=s/'today5a-preimages'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
(s/'TODAY_5A_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_ONLY_NOT_GRANTED_NOT_APPLIED','baseline':'9e23e552','paths':rows,'scope':'Server Today only, owned rendered/synchronous case+serial; actual native order, optional study separate. Exact internal case/target hash navigation and missing/foreign target states, no first name fallback. Existing forms/source and learning opener reuse. No new API/server/allocator/dependencies/live/main/prod.'},indent=2)+'\n')
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p=paths[0];t=(repo/p).read_text();t+='''
/** Read-only Today wire; no personal state, receipt or workload is invented by the client. */
export function isLearningActionRef(v: unknown): v is LearningTaskRef {
  if (!object(v) || !exact(v.id, 200)) return false;
  if (v.kind === 'lesson') return fields(v, ['kind', 'id', 'lesson_id', 'content_version']) && exact(v.lesson_id, 200) && exact(v.content_version, 200);
  if (v.kind === 'attempt_review') return fields(v, ['kind', 'id', 'attempt_id', 'lesson_id', 'content_version']) && uuid(v.attempt_id) && exact(v.lesson_id, 200) && exact(v.content_version, 200);
  return (v.kind === 'assessment' || v.kind === 'external_resource') && fields(v, ['kind', 'id', 'version']) && exact(v.version, 200);
}
const todayDate = (v: unknown) => object(v) && fields(v, ['local_date', 'timezone', 'certainty', 'comparison_zone', 'fallback_display_only', 'official_closure'])
  && nullable(v.local_date, date) && nullable(v.timezone, zone) && zone(v.comparison_zone) && typeof v.fallback_display_only === 'boolean'
  && ['applicant_entered', 'date_only_timezone_unknown', 'source_date_only', 'previous_cycle', 'unknown'].some(value => value === v.certainty) && v.official_closure === 'not_assessed';
const todayCard = (v: unknown) => object(v) && fields(v, ['id', 'reason', 'target', 'target_result_id', 'date', 'dependency_reasons', 'workload_origin', 'planned_minutes', 'source_state', 'actionable'])
  && exact(v.id, 200) && ['personal_document_action', 'personal_application_action', 'accepted_study_action'].some(value => value === v.reason)
  && nullable(v.target, value => actionRef(value) || isLearningActionRef(value)) && nullable(v.target_result_id, exact) && todayDate(v.date)
  && uniqueList(v.dependency_reasons, value => ['dependency_missing', 'dependency_cycle', 'dependency_not_reported_ready', 'report_refers_to_previous_binding', 'not_needed_is_not_a_waiver', 'application_context_changed'].some(item => item === value), 6)
  && ['g2', 'legacy_v2', 'legacy_v1', 'personal_unallocated'].some(value => value === v.workload_origin)
  && nullable(v.planned_minutes, value => integer(value, 0, 180)) && (v.workload_origin === 'personal_unallocated') === (v.planned_minutes === null)
  && ['applicant_entered', 'not_evaluated', 'research_locked', 'current_reference', 'source_changed', 'evidence_unknown'].some(value => value === v.source_state)
  && typeof v.actionable === 'boolean' && (!v.actionable || v.target !== null)
  && (v.reason !== 'personal_document_action' || (object(v.target) && v.target.kind === 'document_task'))
  && (v.reason !== 'personal_application_action' || (object(v.target) && v.target.kind === 'application'));
export function isTodayProjection(v: unknown): v is TodayProjectionV1 {
  if (!object(v) || !fields(v, ['schema_version', 'profile_id', 'as_of', 'display_timezone', 'action_state', 'action_revision', 'action_digest', 'action_observed_at', 'active_plan', 'preparation_access', 'current_source_statuses', 'consistency', 'needs_refresh', 'notices', 'overdue_personal', 'today_study', 'today_personal', 'future', 'undated_personal', 'application_summaries', 'workload', 'allocated_study_minutes', 'personal_minutes', 'readiness'])
    || v.schema_version !== 'admissions-today-v1' || !exact(v.profile_id) || !utc(v.as_of) || !zone(v.display_timezone) || !utc(v.action_observed_at)
    || !['readable', 'absent', 'unavailable'].some(value => value === v.action_state) || !nullable(v.action_revision, value => integer(value, 0, ACTION_REVISION_MAX)) || !nullable(v.action_digest, digest)
    || !list(v.current_source_statuses, sourceRead, 0, 40) || !['component_reads', 'mixed_revision'].some(value => value === v.consistency) || typeof v.needs_refresh !== 'boolean'
    || !list(v.notices, value => object(value) && fields(value, ['code', 'record_id']) && nullable(value.record_id, id => exact(id, 200)) && ['mixed_revision', 'actions_unavailable', 'plan_unavailable', 'plan_needs_review', 'preparation_locked', 'source_review', 'dependency_review'].some(code => code === value.code), 0, 1000)
    || !list(v.application_summaries, anyApplicationRecord, 0, 20) || !v.application_summaries.every(value => object(value) && value.profile_id === v.profile_id)
    || !['one_selected_plan', 'unknown'].some(value => value === v.workload) || !nullable(v.allocated_study_minutes, value => integer(value, 0, 72000))
    || v.personal_minutes !== 'not_estimated' || v.readiness !== 'not_assessed') return false;
  const groups = [v.overdue_personal, v.today_study, v.today_personal, v.future, v.undated_personal];
  if (!groups.every(value => list(value, todayCard, 0, 820))) return false;
  const cards = groups.flatMap(value => Array.isArray(value) ? value : []);
  if (cards.length > 820 || new Set(cards.map(value => object(value) ? value.id : null)).size !== cards.length) return false;
  const access = v.preparation_access; const plan = v.active_plan;
  if (!object(access) || !fields(access, ['allowed', 'reason', 'starts_at', 'ends_at', 'development_only', 'observed_at']) || typeof access.allowed !== 'boolean'
    || typeof access.development_only !== 'boolean' || !['active', 'expired', 'not_started', 'unavailable', 'development'].some(value => value === access.reason)
    || !nullable(access.starts_at, utc) || !nullable(access.ends_at, utc) || !utc(access.observed_at)) return false;
  if (!object(plan) || !fields(plan, ['origin', 'selection_source', 'state', 'selection', 'current_observed_head', 'observed_at', 'goal_result_ids', 'study_actions', 'allocated_minutes', 'needs_review'])
    || !['none', 'g2', 'legacy_v2', 'legacy_v1', 'unknown'].some(value => value === plan.origin) || !['accepted_g3_event', 'derived_backward_default', 'unavailable'].some(value => value === plan.selection_source)
    || !['available', 'needs_review', 'unavailable', 'absent'].some(value => value === plan.state) || !nullable(plan.selection, selection)
    || !nullable(plan.current_observed_head, isNativeHeadV1) || !utc(plan.observed_at) || !uniqueList(plan.goal_result_ids, exact, 20)
    || typeof plan.needs_review !== 'boolean' || !nullable(plan.allocated_minutes, value => integer(value, 0, 72000))
    || !list(plan.study_actions, value => object(value) && fields(value, ['id', 'local_date', 'timezone', 'ref', 'planned_minutes', 'availability', 'completion'])
      && exact(value.id, 200) && date(value.local_date) && zone(value.timezone) && nullable(value.ref, isLearningActionRef) && integer(value.planned_minutes, 0, 180)
      && ['available', 'unavailable', 'unsupported'].some(item => item === value.availability) && ['not_projected', 'self_reported_complete'].some(item => item === value.completion), 0, 400)) return false;
  if (object(plan.current_observed_head) && plan.current_observed_head.profile_id !== v.profile_id) return false;
  if (object(plan.selection) && object(plan.selection.observed_head) && plan.selection.observed_head.profile_id !== v.profile_id) return false;
  return v.consistency !== 'mixed_revision' || v.needs_refresh === true;
}
''';put(p,t)
put(paths[1],'''import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { useStore } from './store';
import { isTodayProjection, type TodayProjectionV1 } from '@/types/admissionsActions';
import { t } from './i18n';
const caseKey = (v: ReturnType<ReturnType<typeof useStore>['currentAdmissionsCase']>) => JSON.stringify([v.scope === undefined ? 'demo' : v.scope, v.profile_id, v.case_epoch]);
export function useAdmissionsToday() {
  const { currentAdmissionsCase } = useStore(); const live = currentAdmissionsCase(); const key = caseKey(live);
  const getter = useRef(currentAdmissionsCase); getter.current = currentAdmissionsCase;
  const mounted = useRef(true); const serial = useRef(0);
  const [stored, setStored] = useState<{ key: string; value: TodayProjectionV1 | null; loading: boolean; error: string } | null>(null);
  const active = useCallback(() => mounted.current && key === caseKey(getter.current()), [key]);
  const refresh = useCallback(async () => {
    const captured = getter.current(); if (!active() || captured.scope === null || captured.profile_id === null) return false;
    const request = ++serial.current; setStored(old => ({ key, value: old?.key === key ? old.value : null, loading: true, error: '' }));
    try {
      let timezone: string | null = null; try { timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || null; } catch { /* server uses explicit fallback */ }
      const out: unknown = await api.admissionsToday(captured.profile_id, timezone);
      if (!active() || request !== serial.current) return false;
      if (!isTodayProjection(out) || out.profile_id !== captured.profile_id) throw new Error('Unconfirmed Today response');
      setStored({ key, value: out, loading: false, error: '' }); return true;
    } catch {
      if (active() && request === serial.current) setStored(old => ({ key, value: old?.key === key ? old.value : null, loading: false, error: t('today.unavailable') }));
      return false;
    }
  }, [active, key]);
  useEffect(() => { const token = serial; mounted.current = true; return () => { mounted.current = false; ++token.current; }; }, []);
  useEffect(() => { const token = serial; void refresh(); return () => { ++token.current; }; }, [refresh]);
  const view = stored?.key === key ? stored : null;
  return { caseKey: key, profileId: live.profile_id, value: view?.value ?? null, loading: view?.loading ?? (live.profile_id !== null && live.scope !== null), error: view?.error ?? '', refresh };
}
''')
put(paths[3],'''/** Internal exact IDs only; a URL never switches cases or grants access. */
import { useSyncExternalStore } from 'react';
import type { LearningTaskRef } from '@/types';
import { isLearningActionRef } from '@/types/admissionsActions';
export type AdmissionsTarget = { profileId: string; screen: 'documents' | 'approved' | 'sources' | 'preparation'; target: { kind: 'document_task' | 'application' | 'result'; id: string } | LearningTaskRef };
const exact = (value: string | null) => value !== null && value.length > 0 && value.length <= 200 && value === value.trim() && !/[\\x00-\\x1f\\x7f]/.test(value);
export function targetHref(value: AdmissionsTarget): string {
  const query = new URLSearchParams({ case: value.profileId, kind: value.target.kind, id: value.target.id });
  if ('lesson_id' in value.target) { query.set('lesson', value.target.lesson_id); query.set('version', value.target.content_version); }
  if ('attempt_id' in value.target) query.set('attempt', value.target.attempt_id);
  return `#/${value.screen}?${query}`;
}
export function parseAdmissionsTarget(hash: string): AdmissionsTarget | null {
  if (hash.length > 1500) return null;
  const [path, search] = hash.split('?'); const screen = path?.replace(/^#\\//, ''); if (!search || !['documents', 'approved', 'sources', 'preparation'].includes(screen ?? '')) return null;
  const q = new URLSearchParams(search); const entries = [...q.entries()]; if (new Set(entries.map(([name]) => name)).size !== entries.length) return null;
  const profileId = q.get('case'); const kind = q.get('kind'); const id = q.get('id'); if (!exact(profileId) || !exact(id) || profileId === null || id === null) return null;
  const keys = entries.map(([name]) => name); const allowed = ['case', 'kind', 'id', 'lesson', 'version', 'attempt']; if (keys.some(name => !allowed.includes(name))) return null;
  if (screen === 'documents' && kind === 'document_task' && keys.length === 3) return { screen, profileId, target: { kind, id } };
  if (screen === 'approved' && kind === 'application' && keys.length === 3) return { screen, profileId, target: { kind, id } };
  if (screen === 'sources' && kind === 'result' && keys.length === 3) return { screen, profileId, target: { kind, id } };
  if (screen !== 'preparation') return null;
  const ref: unknown = kind === 'lesson' ? { kind, id, lesson_id: q.get('lesson'), content_version: q.get('version') }
    : kind === 'attempt_review' ? { kind, id, attempt_id: q.get('attempt'), lesson_id: q.get('lesson'), content_version: q.get('version') } : null;
  return isLearningActionRef(ref) && keys.length === (kind === 'lesson' ? 5 : 6) ? { screen, profileId, target: ref } : null;
}
const subscribe = (fn: () => void) => { window.addEventListener('hashchange', fn); return () => window.removeEventListener('hashchange', fn); };
export function useAdmissionsTarget() { const hash = useSyncExternalStore(subscribe, () => window.location.hash); return parseAdmissionsTarget(hash); }
''')
put(paths[7],'''/** Synthetic read-only Today DTO, no native API acceptance claim. */
import { emptyActions } from './admissionsFixtures';
import type { TodayProjectionV1 } from '@/types/admissionsActions';
export function emptyToday(profile = 'A'): TodayProjectionV1 {
  const time = emptyActions().observed_at;
  return { schema_version: 'admissions-today-v1', profile_id: profile, as_of: time, display_timezone: 'UTC', action_state: 'absent', action_revision: 0, action_digest: null, action_observed_at: time,
    active_plan: { origin: 'none', selection_source: 'derived_backward_default', state: 'absent', selection: null, current_observed_head: null, observed_at: time, goal_result_ids: [], study_actions: [], allocated_minutes: null, needs_review: false },
    preparation_access: { allowed: false, reason: 'unavailable', starts_at: null, ends_at: null, development_only: false, observed_at: time },
    current_source_statuses: [], consistency: 'component_reads', needs_refresh: false, notices: [], overdue_personal: [], today_study: [], today_personal: [], future: [], undated_personal: [], application_summaries: [], workload: 'unknown', allocated_study_minutes: null, personal_minutes: 'not_estimated', readiness: 'not_assessed' };
}
''')
print('External Today validator, own read hook, exact internal navigation and fixture prepared; other declared files pending. No source application.')

/** Internal exact IDs only; a URL never switches cases or grants access. */
import { useSyncExternalStore } from 'react';
import type { LearningTaskRef } from '@/types';
import { isLearningActionRef } from '@/types/admissionsActions';
export type AdmissionsTarget = { profileId: string; screen: 'documents' | 'approved' | 'applications' | 'sources' | 'preparation'; target: { kind: 'document_task' | 'application' | 'result'; id: string } | LearningTaskRef };
const exact = (value: string | null) => value !== null && value.length > 0 && value.length <= 200 && value === value.trim() && !Array.from(value).some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127);
export function targetHref(value: AdmissionsTarget): string {
  const query = new URLSearchParams({ case: value.profileId, kind: value.target.kind, id: value.target.id });
  if ('lesson_id' in value.target) { query.set('lesson', value.target.lesson_id); query.set('version', value.target.content_version); }
  if ('attempt_id' in value.target) query.set('attempt', value.target.attempt_id);
  return `#/${value.screen}?${query}`;
}
export function parseAdmissionsTarget(hash: string): AdmissionsTarget | null {
  if (hash.length > 1500) return null;
  const [path, search] = hash.split('?'); const screen = path?.replace(/^#\//, ''); if (!search || !['documents', 'approved', 'applications', 'sources', 'preparation'].includes(screen ?? '')) return null;
  const q = new URLSearchParams(search); const entries = [...q.entries()]; if (new Set(entries.map(([name]) => name)).size !== entries.length) return null;
  const profileId = q.get('case'); const kind = q.get('kind'); const id = q.get('id'); if (!exact(profileId) || !exact(id) || profileId === null || id === null) return null;
  const keys = entries.map(([name]) => name); const allowed = ['case', 'kind', 'id', 'lesson', 'version', 'attempt']; if (keys.some(name => !allowed.includes(name))) return null;
  if (screen === 'documents' && kind === 'document_task' && keys.length === 3) return { screen, profileId, target: { kind, id } };
  if ((screen === 'approved' || screen === 'applications') && kind === 'application' && keys.length === 3) return { screen, profileId, target: { kind, id } };
  if (screen === 'sources' && kind === 'result' && keys.length === 3) return { screen, profileId, target: { kind, id } };
  if (screen !== 'preparation') return null;
  const ref: unknown = kind === 'lesson' ? { kind, id, lesson_id: q.get('lesson'), content_version: q.get('version') }
    : kind === 'attempt_review' ? { kind, id, attempt_id: q.get('attempt'), lesson_id: q.get('lesson'), content_version: q.get('version') } : null;
  return isLearningActionRef(ref) && keys.length === (kind === 'lesson' ? 5 : 6) ? { screen, profileId, target: ref } : null;
}
const subscribe = (fn: () => void) => { window.addEventListener('hashchange', fn); return () => window.removeEventListener('hashchange', fn); };
export function useAdmissionsTarget() { const hash = useSyncExternalStore(subscribe, () => window.location.hash); return parseAdmissionsTarget(hash); }

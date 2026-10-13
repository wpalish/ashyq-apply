import { expect, it } from 'vitest';
import { parseAdmissionsTarget, targetHref } from './admissionsNavigation';
it.each(['document_task', 'application', 'result'] as const)('preserves exact own %s IDs with reserved characters', kind => {
  const value = { profileId: 'A', screen: kind === 'document_task' ? 'documents' as const : kind === 'application' ? 'approved' as const : 'sources' as const, target: { kind, id: 'same/name+second' } };
  expect(parseAdmissionsTarget(targetHref(value))).toEqual(value);
});
it('preserves an exact lesson/version and rejects duplicate, unsupported or mismatched parameters', () => {
  const value = { profileId: 'A', screen: 'preparation' as const, target: { kind: 'lesson' as const, id: 'task-1', lesson_id: 'lesson-1', content_version: 'v1' } };
  expect(parseAdmissionsTarget(targetHref(value))).toEqual(value);
  expect(parseAdmissionsTarget('#/documents?case=A&kind=document_task&id=1&id=2')).toBeNull();
  expect(parseAdmissionsTarget('#/documents?case=A&kind=application&id=1')).toBeNull();
  expect(parseAdmissionsTarget('#/sources?case=A&kind=result&id=1&name=University')).toBeNull();
});

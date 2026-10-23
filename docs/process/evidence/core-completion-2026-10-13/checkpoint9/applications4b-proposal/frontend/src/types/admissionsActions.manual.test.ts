import { expect, it } from 'vitest';
import { manualFixture } from '@/test/manualAdmissionsFixtures';
import { acceptedActions } from '@/test/admissionsFixtures';
import { isActionRequest, isActionRequestV1, isActionWriteReceiptShape, isActionWriteReceiptShapeV1, isActionsCurrentOut, isActionsCurrentOutV1, isActionsHistoryOut } from './admissionsActions';

it('accepts explicit manual V2 while frozen V1 guards remain closed', () => {
  const { body, receipt, current } = manualFixture();
  expect(isActionRequest(body)).toBe(true); expect(isActionRequestV1(body)).toBe(false);
  expect(isActionWriteReceiptShape(receipt)).toBe(true); expect(isActionWriteReceiptShapeV1(receipt)).toBe(false);
  expect(isActionsCurrentOut(current)).toBe(true); expect(isActionsCurrentOutV1(current)).toBe(false);
  expect(isActionsHistoryOut({ profile_id: 'A', events: [receipt], next_after_revision: null, source_evaluation: 'not_evaluated' })).toBe(true);
  const old = acceptedActions(); expect(isActionRequest(old.body)).toBe(true); expect(isActionsCurrentOut(old.current)).toBe(true);
});
it('rejects invented result IDs, official verification and unconfirmed manual context', () => {
  const { body } = manualFixture();
  for (const patch of [{ result_id: 'foreign-result' }, { award_id: 'foreign-award' }, { official_verification: 'performed' }, { confirmed_entered_context: false }]) {
    expect(isActionRequest({ ...body, target: { ...body.target, ...patch } })).toBe(false);
  }
  expect(isActionRequest({ ...body, schema_version: 'admissions-actions-v1' })).toBe(false);
});
it('rejects contradictory V2 receipt target and outer schema', () => {
  const { receipt, current } = manualFixture();
  const changed = structuredClone(receipt); const app = changed.applied_delta.applications[0];
  if (!app || !('university' in app.target)) throw new Error('Synthetic manual target');
  app.target.university = 'Synthetic other target';
  expect(isActionWriteReceiptShape(changed)).toBe(false);
  expect(isActionWriteReceiptShape({ ...receipt, schema_version: 'admissions-actions-v1' })).toBe(false);
  expect(isActionsCurrentOut({ ...current, state: { ...current.state, schema_version: 'admissions-actions-v1' } })).toBe(false);
});

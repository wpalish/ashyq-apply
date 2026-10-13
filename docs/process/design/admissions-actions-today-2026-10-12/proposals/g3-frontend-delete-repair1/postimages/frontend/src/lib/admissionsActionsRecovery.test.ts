import { createHash, webcrypto } from 'node:crypto';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  acknowledgeAdmissionsAction, acknowledgeAdmissionsCaseDeletion, admissionsActionRetryBody,
  G3_RECOVERY_ENTRY_BYTES, G3_RECOVERY_INDEX_BYTES, g3Canonical, g3RequestDigest,
  journalAdmissionsAction, markAdmissionsActionState, openAdmissionsActionsRecovery,
  readAdmissionsActionsRecovery, readAdmissionsLegacyCandidates, reconcileAdmissionsActionsIndex,
  type G3IntentEntryV1, type G3LiveCaseIdentity, type G3RecoveryBinding, type G3RecoveryResult,
} from './admissionsActionsRecovery';
import { bindApplicantOwner, forgetApplicantBrowserData } from './applicantStorage';
import type { AuthStatus } from '@/types';
import type { ActionRequestV1, ActionWriteReceiptV1, CreatePersonalTaskV1, DocumentTaskV1 } from '@/types/admissionsActions';

const OWNER = 'ashyq.applicantOwner';
const firstUuid = '11111111-2222-4333-8444-555555555555';
const secondUuid = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee';
let live: G3LiveCaseIdentity;
const personal = { label: '  Synthetic document task  ', responsible_actor: 'applicant' as const,
  details: { due: null, notes: '  Жеке / личные сведения  ' }, depends_on_task_ids: [] };
function command(id = firstUuid, revision = 0): CreatePersonalTaskV1 {
  return { schema_version: 'admissions-actions-v1', kind: 'create_personal_task', client_write_uuid: id,
    expected_revision: revision, application_id: null, personal: structuredClone(personal) };
}
function value<T>(result: G3RecoveryResult<T>): T {
  if (!result.ok) throw new Error(`Synthetic fixture failed: ${result.reason}`); return result.value;
}
function owner(binding = 'demo') { localStorage.setItem(OWNER, binding); sessionStorage.setItem(OWNER, binding); }
function opened(profile = 'case-a', scope: string | undefined = undefined): G3RecoveryBinding {
  live = { scope, profile_id: profile, case_epoch: live?.case_epoch ?? 1 };
  return value(openAdmissionsActionsRecovery(scope, profile, live.case_epoch, () => live));
}
const entryKey = (binding: G3RecoveryBinding, id = firstUuid) => `${binding.family}intent.${id}`;
const indexKey = (binding: G3RecoveryBinding) => `${binding.family}index`;
async function saved(binding: G3RecoveryBinding, body: ActionRequestV1 = command(), generation = 1) {
  return value(await journalAdmissionsAction(binding, body, generation));
}
/** Synthetic server ACKs are separately signed with Node SHA256; no server or provider is contacted. */
async function receipt(body: ActionRequestV1, profile = 'case-a', eventId = 'event-a'): Promise<ActionWriteReceiptV1> {
  const ref = { event_id: eventId, revision: body.expected_revision + 1, kind: body.kind };
  const actor = { schema_version: 'g3-actor-reference-v1' as const, actor_kind: 'authenticated_principal' as const, actor_ref_digest: 'a'.repeat(64) };
  const create = body.kind === 'create_personal_task';
  const taskPersonal = body.kind === 'create_personal_task' ? body.personal : structuredClone(personal);
  const taskIds = body.kind === 'import_legacy_marks' ? body.mappings.map(mapping => mapping.task_id) : ['task-a'];
  const tasks: DocumentTaskV1[] = taskIds.map(id => ({ id, profile_id: profile, application_id: null, origin: 'applicant_entered',
    personal: taskPersonal, binding: null,
    report: create ? { state: 'not_started', entered_at: null, accepted_at: null, actor: null, event_ref: null,
      binding_digest_at_report: null, origin: 'unreported', official_verification: 'not_performed' }
      : { state: 'prepared_reported', entered_at: null, accepted_at: '2026-10-12T00:00:00+00:00', actor, event_ref: ref,
        binding_digest_at_report: null, origin: 'explicit_browser_mark_import', official_verification: 'not_performed' },
    created_ref: create ? ref : { event_id: 'prior-event', revision: 1, kind: 'create_personal_task' }, latest_ref: ref, binding_ref: null }));
  const request = { ...body, client_write_uuid: body.client_write_uuid.toLowerCase() };
  const payload: Omit<ActionWriteReceiptV1, 'receipt_digest'> = {
    schema_version: 'admissions-actions-v1', event_id: eventId, profile_id: profile, kind: body.kind,
    revision: body.expected_revision + 1, expected_revision: body.expected_revision, client_write_uuid: body.client_write_uuid.toLowerCase(),
    request, canonical_request_digest: await g3RequestDigest(profile, body), accepted_at: '2026-10-12T00:00:00+00:00', actor,
    predecessor_event_id: body.expected_revision === 0 ? null : 'prior-event', before_state_digest: body.expected_revision === 0 ? null : 'b'.repeat(64),
    after_state_digest: 'c'.repeat(64), applied_delta: { applications: [], document_tasks: tasks, active_preparation: null,
      corrected_declaration: null, previous_binding_digest: null, declaration: null },
    affected_refs: { application_ids: [], document_task_ids: taskIds, active_selector_changed: false },
  };
  return { ...payload, receipt_digest: createHash('sha256').update(g3Canonical({ schema_version: 'g3-action-receipt-digest-v1', receipt: payload })).digest('hex') };
}
beforeEach(() => { vi.stubGlobal('crypto', webcrypto); localStorage.clear(); sessionStorage.clear(); owner(); live = { scope: undefined, profile_id: 'case-a', case_epoch: 1 }; });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('G3 own case UUID recovery without automatic dispatch', () => {
  it('requires explicit native demo or the exact tree owner, never anonymous/foreign storage adoption', () => {
    localStorage.clear(); sessionStorage.clear();
    expect(openAdmissionsActionsRecovery(undefined, 'case-a', 1, () => live)).toEqual({ ok: false, reason: 'owner' });
    owner('auth:["a","org-a"]');
    expect(openAdmissionsActionsRecovery(undefined, 'case-a', 1, () => live)).toEqual({ ok: false, reason: 'owner' });
    expect(openAdmissionsActionsRecovery(null, 'case-a', 1, () => live).ok).toBe(false);
    live = { scope: '["a","org-a"]', profile_id: 'case-a', case_epoch: 1 };
    expect(openAdmissionsActionsRecovery(live.scope, 'case-a', 1, () => live).ok).toBe(true);
  });
  it('journals before dispatch and returns the exact original UUID/body for an explicit unknown-ACK retry', async () => {
    const binding = opened(); const body = command(); const transport = vi.fn();
    const original = await saved(binding, body); body.personal.details.notes = 'Later unsent edit';
    const uncertain = value(await markAdmissionsActionState(binding, firstUuid, original.raw, 'uncertain'));
    const retry = value(await admissionsActionRetryBody(binding, firstUuid, uncertain.raw));
    expect(retry).toEqual(command()); expect(retry.client_write_uuid).toBe(firstUuid); expect(retry.expected_revision).toBe(0);
    expect(value(await readAdmissionsActionsRecovery(binding)).entries[0]?.pending_state).toBe('uncertain');
    expect(transport).not.toHaveBeenCalled();
    expect(Object.keys(JSON.parse(uncertain.raw))).not.toEqual(expect.arrayContaining(['current', 'today', 'source', 'material']));
  });
  it('rejects changed body/CAS under a pending UUID without discarding the original intent', async () => {
    const binding = opened(); const original = await saved(binding);
    expect(await journalAdmissionsAction(binding, { ...command(), expected_revision: 1 }, 2)).toEqual({ ok: false, reason: 'changed' });
    expect(localStorage.getItem(entryKey(binding))).toBe(original.raw);
    const conflict = value(await markAdmissionsActionState(binding, firstUuid, original.raw, 'conflict'));
    expect(await admissionsActionRetryBody(binding, firstUuid, conflict.raw)).toEqual({ ok: false, reason: 'changed' });
    expect(localStorage.getItem(entryKey(binding))).toBe(conflict.raw);
  });
  it('retires an old matching ACK reference while preserving a newer pending UUID and another case', async () => {
    const binding = opened(); const original = await saved(binding);
    const newer = await saved(binding, { ...command(secondUuid, 1), personal: { ...personal, label: 'Newer unsent edit' } }, 2);
    const otherLive: G3LiveCaseIdentity = { scope: undefined, profile_id: 'case-b', case_epoch: 2 };
    const other = value(openAdmissionsActionsRecovery(undefined, 'case-b', 2, () => otherLive)); await saved(other, command(secondUuid));
    const otherBytes = localStorage.getItem(entryKey(other, secondUuid));
    const acknowledged = value(await acknowledgeAdmissionsAction(binding, command(), await receipt(command())));
    expect(acknowledged.entry.descriptor.status).toBe('acknowledged'); expect(acknowledged.entry.pending_state).toBeNull();
    expect(Object.keys(acknowledged.entry.descriptor.receipt_ref ?? {}).sort()).toEqual(['canonical_request_digest', 'event_id', 'receipt_digest', 'revision']);
    expect(localStorage.getItem(entryKey(binding, secondUuid))).toBe(newer.raw); expect(localStorage.getItem(entryKey(other, secondUuid))).toBe(otherBytes);
    expect(value(await readAdmissionsActionsRecovery(binding)).entries).toHaveLength(2);
    expect(acknowledged.entry.body).toEqual(original.entry.body);
    const replay = value(await acknowledgeAdmissionsAction(binding, command(), await receipt(command()))); expect(replay.raw).toBe(acknowledged.raw);
  });
  it.each(['profile', 'uuid', 'kind', 'request', 'hash', 'actor-extra', 'delta-extra', 'record-profile'])('refuses %s ACK corruption without retiring pending bytes', async corruption => {
    const binding = opened(); const original = await saved(binding); const ack = await receipt(command());
    const mutable = ack as unknown as Record<string, unknown>;
    if (corruption === 'profile') ack.profile_id = 'case-b';
    if (corruption === 'uuid') ack.client_write_uuid = secondUuid;
    if (corruption === 'kind') ack.kind = 'declare_submission';
    if (corruption === 'request') ack.request = { ...command(), expected_revision: 1 };
    if (corruption === 'hash') ack.receipt_digest = 'd'.repeat(64);
    if (corruption === 'actor-extra') mutable.actor = { ...ack.actor, email: 'must-not-be-stored@example.test' };
    if (corruption === 'delta-extra') mutable.applied_delta = { ...ack.applied_delta, material_snapshot: 'Must not be adopted' };
    if (corruption === 'record-profile') ack.applied_delta.document_tasks[0]!.profile_id = 'case-b';
    expect((await acknowledgeAdmissionsAction(binding, command(), ack)).ok).toBe(false);
    expect(localStorage.getItem(entryKey(binding))).toBe(original.raw);
  });
  it('accepts schema UUID normalization without rewriting the original submitted uppercase body', async () => {
    const binding = opened(); const body = command(secondUuid.toUpperCase()); const original = await saved(binding, body);
    const acknowledged = value(await acknowledgeAdmissionsAction(binding, body, await receipt(body)));
    expect(acknowledged.entry.body.client_write_uuid).toBe(secondUuid.toUpperCase()); expect(acknowledged.entry.body).toEqual(original.entry.body);
    expect(acknowledged.entry.descriptor.client_write_uuid).toBe(secondUuid);
  });
  it.each(['owner', 'case', 'epoch', 'ABA'])('rejects stale %s callbacks and keeps pending bytes', async changed => {
    const binding = opened(); const original = await saved(binding);
    if (changed === 'owner') owner('auth:["b","org-b"]');
    if (changed === 'case') live = { ...live, profile_id: 'case-b' };
    if (changed === 'epoch') live = { ...live, case_epoch: 2 };
    if (changed === 'ABA') { owner('auth:["b","org-b"]'); owner(); live = { ...live, case_epoch: 3 }; }
    expect((await readAdmissionsActionsRecovery(binding)).ok).toBe(false);
    expect((await acknowledgeAdmissionsAction(binding, command(), await receipt(command()))).ok).toBe(false);
    expect(localStorage.getItem(entryKey(binding))).toBe(original.raw);
  });
  it('rejects native auth A→B→A old family even if the caller reused an epoch', async () => {
    const status = (user: string, org: string): AuthStatus => ({ enabled: true, authenticated: true, registration_enabled: false,
      principal: { user_id: user, organization_id: org, email: 'synthetic@example.test', display_name: 'Synthetic', organization_name: 'Synthetic', role: 'owner', local_development: false } });
    bindApplicantOwner(status('a', 'org-a')); const binding = opened('case-a', '["a","org-a"]'); await saved(binding);
    bindApplicantOwner(status('b', 'org-b')); bindApplicantOwner(status('a', 'org-a'));
    const replacement = opened('case-a', '["a","org-a"]'); expect(replacement.generation).not.toBe(binding.generation);
    expect(await readAdmissionsActionsRecovery(binding)).toEqual({ ok: false, reason: 'generation' });
    expect((await journalAdmissionsAction(replacement, command(secondUuid), 1)).ok).toBe(true);
  });
  it('fences owner changes around asynchronous hashing before a journal can be dispatched', async () => {
    const binding = opened(); const originalDigest = crypto.subtle.digest.bind(crypto.subtle);
    vi.spyOn(crypto.subtle, 'digest').mockImplementation(async (algorithm, data) => {
      const result = await originalDigest(algorithm, data); owner('auth:["b","org-b"]'); return result;
    });
    expect((await journalAdmissionsAction(binding, command(), 1)).ok).toBe(false);
    expect(localStorage.getItem(entryKey(binding))).toBeNull();
  });
  it.each(['foreign-index', 'foreign-entry', 'extra-entry', 'digest', 'malformed', 'oversize-entry', 'oversize-index'])('retains %s bytes and refuses automatic adoption/reset', async corruption => {
    const binding = opened(); const original = await saved(binding);
    const entry = JSON.parse(original.raw) as Record<string, unknown>;
    const index = JSON.parse(original.index_raw) as Record<string, unknown>;
    if (corruption === 'foreign-index') index.profile_id = 'case-b';
    if (corruption === 'foreign-entry') entry.owner_binding = 'foreign';
    if (corruption === 'extra-entry') entry.current_snapshot = { secret: 'Never adopt' };
    if (corruption === 'digest') entry.body = { ...command(), personal: { ...personal, label: 'Edited without matching digest' } };
    const entryBytes = corruption === 'malformed' ? '{' : corruption === 'oversize-entry' ? ' '.repeat(G3_RECOVERY_ENTRY_BYTES + 1) : JSON.stringify(entry);
    const indexBytes = corruption === 'oversize-index' ? ' '.repeat(G3_RECOVERY_INDEX_BYTES + 1) : JSON.stringify(index);
    localStorage.setItem(entryKey(binding), entryBytes); localStorage.setItem(indexKey(binding), indexBytes);
    expect((await readAdmissionsActionsRecovery(binding)).ok).toBe(false);
    expect((await reconcileAdmissionsActionsIndex(binding, indexBytes)).ok).toBe(false);
    expect(localStorage.getItem(entryKey(binding))).toBe(entryBytes); expect(localStorage.getItem(indexKey(binding))).toBe(indexBytes);
  });
  it('keeps both own UUID entries after index loss and requires an explicit reviewed reconciliation', async () => {
    const binding = opened(); const first = await saved(binding); const second = await saved(binding, command(secondUuid));
    localStorage.removeItem(indexKey(binding));
    expect(await readAdmissionsActionsRecovery(binding)).toEqual({ ok: false, reason: 'index_missing' });
    expect(localStorage.getItem(entryKey(binding))).toBe(first.raw); expect(localStorage.getItem(entryKey(binding, secondUuid))).toBe(second.raw);
    const recovered = value(await reconcileAdmissionsActionsIndex(binding, null)); expect(recovered.entries).toHaveLength(2);
    expect(recovered.entries.map(entry => entry.descriptor.status)).toEqual(['pending', 'pending']);
  });
  it('preserves a sibling UUID inserted during an index write instead of claiming localStorage atomic CAS', async () => {
    const binding = opened(); const body = command(secondUuid); const payloadDigest = await g3RequestDigest('case-a', body);
    const sibling: G3IntentEntryV1 = { schema_version: 'g3-personal-intent-entry-v1', owner_binding: 'demo', profile_id: 'case-a', generation: binding.generation,
      draft_generation: 2, entry_revision: 0, body, pending_state: 'uncertain', descriptor: { client_write_uuid: secondUuid,
        payload_digest: payloadDigest, base_server_revision: 0, kind: 'create_personal_task', application_ids: [], document_task_ids: [],
        result_ids: [], source_preview_digests: [], status: 'pending', receipt_ref: null } };
    const originalSet = Storage.prototype.setItem; let inserted = false;
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key: string, raw: string) {
      originalSet.call(this, key, raw);
      if (key === indexKey(binding) && !inserted) { inserted = true; originalSet.call(this, entryKey(binding, secondUuid), JSON.stringify(sibling)); }
    });
    expect(await journalAdmissionsAction(binding, command(), 1)).toEqual({ ok: false, reason: 'index_mismatch' });
    expect(localStorage.getItem(entryKey(binding))).not.toBeNull(); expect(localStorage.getItem(entryKey(binding, secondUuid))).toBe(JSON.stringify(sibling));
    const indexRaw = localStorage.getItem(indexKey(binding));
    expect(value(await reconcileAdmissionsActionsIndex(binding, indexRaw)).entries).toHaveLength(2);
  });
  it('does not recreate a missing family fence over existing pending entries', async () => {
    const binding = opened(); const original = await saved(binding); localStorage.removeItem(`${binding.family}fence`);
    expect(openAdmissionsActionsRecovery(undefined, 'case-a', 1, () => live)).toEqual({ ok: false, reason: 'generation' });
    expect(localStorage.getItem(entryKey(binding))).toBe(original.raw);
  });
  it('reports index persistence failure, preserves the entry, and permits only explicit reconciliation', async () => {
    const binding = opened(); const originalSet = Storage.prototype.setItem;
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key: string, raw: string) {
      if (key === indexKey(binding)) throw new Error('Synthetic quota refusal'); originalSet.call(this, key, raw);
    });
    expect(await journalAdmissionsAction(binding, command(), 1)).toEqual({ ok: false, reason: 'storage' });
    expect(localStorage.getItem(entryKey(binding))).not.toBeNull(); vi.restoreAllMocks();
    expect(await readAdmissionsActionsRecovery(binding)).toEqual({ ok: false, reason: 'index_missing' });
    expect(value(await reconcileAdmissionsActionsIndex(binding, null)).entries).toHaveLength(1);
  });
  it('refuses storage read errors and oversized pending inputs without a durable-success claim', async () => {
    const binding = opened();
    expect(await journalAdmissionsAction(binding, { ...command(), personal: { ...personal, details: { due: null, notes: 'x'.repeat(2001) } } }, 1)).toEqual({ ok: false, reason: 'invalid' });
    const read = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('Synthetic refusal'); });
    expect((await readAdmissionsActionsRecovery(binding)).ok).toBe(false); read.mockRestore();
  });
  it('creates a case tombstone only after a matching successful deletion ACK and preserves siblings/unrelated marks', async () => {
    const binding = opened(); await saved(binding);
    const otherLive: G3LiveCaseIdentity = { scope: undefined, profile_id: 'case-b', case_epoch: 1 };
    const other = value(openAdmissionsActionsRecovery(undefined, 'case-b', 1, () => otherLive)); const sibling = await saved(other, command(secondUuid));
    localStorage.setItem('ashyq.docsDone', '{"raw::document":true}'); localStorage.setItem('unrelated', 'keep');
    expect(acknowledgeAdmissionsCaseDeletion(binding, 'case-b')).toMatchObject({ tombstoned: false, reason: 'ack' });
    expect(localStorage.getItem(`${binding.family}tombstone`)).toBeNull();
    expect(acknowledgeAdmissionsCaseDeletion(binding, 'case-a')).toMatchObject({ tombstoned: true, cleanup: 'completed_best_effort' });
    expect(localStorage.getItem(entryKey(binding))).toBeNull(); expect(localStorage.getItem(entryKey(other, secondUuid))).toBe(sibling.raw);
    expect(localStorage.getItem('ashyq.docsDone')).toBe('{"raw::document":true}'); expect(localStorage.getItem('unrelated')).toBe('keep');
    expect(await readAdmissionsActionsRecovery(binding)).toEqual({ ok: false, reason: 'deleted' });
    expect(openAdmissionsActionsRecovery(undefined, 'case-a', 1, () => live)).toEqual({ ok: false, reason: 'deleted' });
  });
  it('cleans captured authenticated case A after its successful DELETE while live case B and its epoch remain active', async () => {
    const status: AuthStatus = { enabled: true, authenticated: true, registration_enabled: false,
      principal: { user_id: 'a', organization_id: 'org-a', email: 'synthetic@example.test', display_name: 'Synthetic',
        organization_name: 'Synthetic', role: 'owner', local_development: false } };
    bindApplicantOwner(status); const scope = '["a","org-a"]';
    const capturedA = opened('case-a', scope); const originalA = await saved(capturedA);
    const ack = await receipt(command());
    live = { scope, profile_id: 'case-b', case_epoch: 2 };
    const activeB = value(openAdmissionsActionsRecovery(scope, 'case-b', 2, () => live));
    await saved(activeB, command(secondUuid));
    const keysB = [`${activeB.family}fence`, indexKey(activeB), entryKey(activeB, secondUuid)];
    const bytesB = keysB.map(key => localStorage.getItem(key));
    const legacyKey = `ashyq.owner.${encodeURIComponent(capturedA.owner_binding)}.ashyq.docsDone`;
    const legacyRaw = '{"a::Transcript":true,"b::CV":true,"unrelated::Other":false}';
    localStorage.setItem(legacyKey, legacyRaw); localStorage.setItem('unrelated-app', 'keep exactly');
    // Current-case guards stay strict for ordinary hydration, journaling, retry and command ACK.
    expect(await readAdmissionsActionsRecovery(capturedA)).toEqual({ ok: false, reason: 'case' });
    expect(await journalAdmissionsAction(capturedA, command(secondUuid), 2)).toEqual({ ok: false, reason: 'case' });
    expect(await admissionsActionRetryBody(capturedA, firstUuid, originalA.raw)).toEqual({ ok: false, reason: 'case' });
    expect(await acknowledgeAdmissionsAction(capturedA, command(), ack)).toEqual({ ok: false, reason: 'case' });
    expect(acknowledgeAdmissionsCaseDeletion(capturedA, 'case-b')).toMatchObject({ tombstoned: false, reason: 'ack' });
    expect(localStorage.getItem(`${capturedA.family}tombstone`)).toBeNull();
    expect(acknowledgeAdmissionsCaseDeletion(capturedA, 'case-a')).toEqual({ tombstoned: true, cleanup: 'completed_best_effort', reason: null });
    expect(localStorage.getItem(entryKey(capturedA))).toBeNull(); expect(localStorage.getItem(indexKey(capturedA))).toBeNull();
    expect(keysB.map(key => localStorage.getItem(key))).toEqual(bytesB);
    expect(localStorage.getItem(legacyKey)).toBe(legacyRaw); expect(localStorage.getItem('unrelated-app')).toBe('keep exactly');
    expect(live).toEqual({ scope, profile_id: 'case-b', case_epoch: 2 });
    expect((await readAdmissionsActionsRecovery(activeB)).ok).toBe(true);
    live = { scope, profile_id: 'case-a', case_epoch: 3 };
    expect(openAdmissionsActionsRecovery(scope, 'case-a', 3, () => live)).toEqual({ ok: false, reason: 'deleted' });
  });
  it('refuses captured case DELETE after the native owner changes even when its captured scope callback stays unchanged', async () => {
    const capturedA = opened(); const original = await saved(capturedA);
    live = { scope: undefined, profile_id: 'case-b', case_epoch: 2 };
    owner('auth:["b","org-b"]');
    expect(acknowledgeAdmissionsCaseDeletion(capturedA, 'case-a')).toEqual({ tombstoned: false, cleanup: 'residual_unknown', reason: 'owner' });
    expect(localStorage.getItem(entryKey(capturedA))).toBe(original.raw);
    expect(localStorage.getItem(indexKey(capturedA))).toBe(original.index_raw);
    expect(localStorage.getItem(`${capturedA.family}tombstone`)).toBeNull();
  });
  it.each(['foreign-fence', 'changed-generation', 'malformed-fence', 'foreign-tombstone', 'malformed-tombstone'])('preserves %s deletion authority bytes without overwriting or adopting them', async corruption => {
    const capturedA = opened(); const original = await saved(capturedA);
    live = { scope: undefined, profile_id: 'case-b', case_epoch: 2 };
    const key = `${capturedA.family}${corruption.includes('tombstone') ? 'tombstone' : 'fence'}`;
    const fence = JSON.parse(localStorage.getItem(`${capturedA.family}fence`)!) as Record<string, unknown>;
    if (corruption === 'foreign-fence') fence.owner_binding = 'auth:foreign';
    if (corruption === 'changed-generation') fence.generation = secondUuid;
    if (corruption === 'foreign-tombstone') { fence.profile_id = 'case-b'; fence.deleted = true; }
    const corruptRaw = corruption.startsWith('malformed') ? '{unreadable' : JSON.stringify(fence);
    localStorage.setItem(key, corruptRaw);
    expect(acknowledgeAdmissionsCaseDeletion(capturedA, 'case-a')).toMatchObject({ tombstoned: false, cleanup: 'residual_unknown' });
    expect(localStorage.getItem(key)).toBe(corruptRaw); expect(localStorage.getItem(entryKey(capturedA))).toBe(original.raw);
    expect(localStorage.getItem(indexKey(capturedA))).toBe(original.index_raw);
  });
  it.each(['foreign-entry', 'foreign-index', 'generation-entry', 'malformed-entry'])('tombstones the deleted captured family but retains %s for investigation', async corruption => {
    const capturedA = opened(); const original = await saved(capturedA);
    live = { scope: undefined, profile_id: 'case-b', case_epoch: 2 };
    const entry = JSON.parse(original.raw) as Record<string, unknown>;
    const index = JSON.parse(original.index_raw) as Record<string, unknown>;
    if (corruption === 'foreign-entry') entry.owner_binding = 'foreign';
    if (corruption === 'generation-entry') entry.generation = secondUuid;
    if (corruption === 'foreign-index') index.profile_id = 'case-b';
    const entryRaw = corruption === 'malformed-entry' ? '{' : JSON.stringify(entry);
    const indexRaw = JSON.stringify(index);
    localStorage.setItem(entryKey(capturedA), entryRaw); localStorage.setItem(indexKey(capturedA), indexRaw);
    expect(acknowledgeAdmissionsCaseDeletion(capturedA, 'case-a')).toEqual({ tombstoned: true, cleanup: 'residual_unknown', reason: 'invalid' });
    expect(localStorage.getItem(entryKey(capturedA))).toBe(entryRaw); expect(localStorage.getItem(indexKey(capturedA))).toBe(indexRaw);
    live = { scope: undefined, profile_id: 'case-a', case_epoch: 3 };
    expect(openAdmissionsActionsRecovery(undefined, 'case-a', 3, () => live)).toEqual({ ok: false, reason: 'deleted' });
  });
  it('rechecks native owner during the deletion-only family scan before writing any tombstone', async () => {
    const capturedA = opened(); const original = await saved(capturedA); const originalKey = Storage.prototype.key; let changed = false;
    live = { scope: undefined, profile_id: 'case-b', case_epoch: 2 };
    vi.spyOn(Storage.prototype, 'key').mockImplementation(function (this: Storage, index: number) {
      const result = originalKey.call(this, index);
      if (!changed) { changed = true; owner('auth:["b","org-b"]'); }
      return result;
    });
    expect(acknowledgeAdmissionsCaseDeletion(capturedA, 'case-a')).toMatchObject({ tombstoned: false, cleanup: 'residual_unknown', reason: 'owner' });
    expect(localStorage.getItem(entryKey(capturedA))).toBe(original.raw); expect(localStorage.getItem(`${capturedA.family}tombstone`)).toBeNull();
  });
  it('refuses a changed captured generation after an entry read during deletion preparation', async () => {
    const capturedA = opened(); const original = await saved(capturedA); const originalGet = Storage.prototype.getItem; let changed = false;
    live = { scope: undefined, profile_id: 'case-b', case_epoch: 2 };
    const fenceKey = `${capturedA.family}fence`;
    const replacement = { ...JSON.parse(localStorage.getItem(fenceKey)!) as Record<string, unknown>, generation: secondUuid };
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(function (this: Storage, key: string) {
      const result = originalGet.call(this, key);
      if (key === entryKey(capturedA) && !changed) { changed = true; localStorage.setItem(fenceKey, JSON.stringify(replacement)); }
      return result;
    });
    expect(acknowledgeAdmissionsCaseDeletion(capturedA, 'case-a')).toMatchObject({ tombstoned: false, cleanup: 'residual_unknown', reason: 'generation' });
    expect(localStorage.getItem(entryKey(capturedA))).toBe(original.raw); expect(localStorage.getItem(`${capturedA.family}tombstone`)).toBeNull();
  });
  it('retains an interleaved replacement intent and reports unknown residuals instead of clearing newer bytes', async () => {
    const capturedA = opened(); const original = await saved(capturedA); const originalSet = Storage.prototype.setItem;
    const replacement = JSON.stringify({ ...original.entry, draft_generation: 2, entry_revision: 1 });
    live = { scope: undefined, profile_id: 'case-b', case_epoch: 2 };
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key: string, raw: string) {
      originalSet.call(this, key, raw);
      if (key === `${capturedA.family}tombstone`) originalSet.call(this, entryKey(capturedA), replacement);
    });
    expect(acknowledgeAdmissionsCaseDeletion(capturedA, 'case-a')).toEqual({ tombstoned: true, cleanup: 'residual_unknown', reason: 'changed' });
    expect(localStorage.getItem(entryKey(capturedA))).toBe(replacement);
  });
  it('stops cleanup after the native owner changes during a tombstone write and preserves captured intent bytes', async () => {
    const capturedA = opened(); const original = await saved(capturedA); const originalSet = Storage.prototype.setItem;
    live = { scope: undefined, profile_id: 'case-b', case_epoch: 2 };
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key: string, raw: string) {
      originalSet.call(this, key, raw);
      if (key === `${capturedA.family}tombstone`) owner('auth:["b","org-b"]');
    });
    expect(acknowledgeAdmissionsCaseDeletion(capturedA, 'case-a')).toMatchObject({ cleanup: 'residual_unknown', reason: 'owner' });
    expect(localStorage.getItem(entryKey(capturedA))).toBe(original.raw); expect(localStorage.getItem(indexKey(capturedA))).toBe(original.index_raw);
    expect(localStorage.getItem(`${capturedA.family}tombstone`)).not.toBeNull();
  });
  it('blocks a late intent write after the tombstone even if residual bytes arrive after cleanup', async () => {
    const binding = opened(); const originalSet = Storage.prototype.setItem; let deleted = false;
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key: string, raw: string) {
      if (key === entryKey(binding) && !deleted) { deleted = true; expect(acknowledgeAdmissionsCaseDeletion(binding, 'case-a').tombstoned).toBe(true); }
      originalSet.call(this, key, raw);
    });
    expect((await journalAdmissionsAction(binding, command(), 1)).ok).toBe(false);
    expect(localStorage.getItem(entryKey(binding))).not.toBeNull();
    expect(await readAdmissionsActionsRecovery(binding)).toEqual({ ok: false, reason: 'deleted' });
  });
  it('keeps an immutable deletion tombstone over a late alive-fence initializer', async () => {
    const binding = opened(); const alive = localStorage.getItem(`${binding.family}fence`);
    expect(acknowledgeAdmissionsCaseDeletion(binding, 'case-a').tombstoned).toBe(true);
    localStorage.setItem(`${binding.family}fence`, alive!);
    expect(openAdmissionsActionsRecovery(undefined, 'case-a', 1, () => live)).toEqual({ ok: false, reason: 'deleted' });
  });
  it('returns residual_unknown when deletion cleanup fails, while the surviving tombstone denies hydration', async () => {
    const binding = opened(); await saved(binding);
    const originalRemove = Storage.prototype.removeItem;
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(function (this: Storage, key: string) {
      if (key === entryKey(binding)) throw new Error('Synthetic cleanup refusal'); originalRemove.call(this, key);
    });
    expect(acknowledgeAdmissionsCaseDeletion(binding, 'case-a')).toMatchObject({ tombstoned: true, cleanup: 'residual_unknown', reason: 'storage' });
    expect(localStorage.getItem(entryKey(binding))).not.toBeNull(); expect((await readAdmissionsActionsRecovery(binding)).ok).toBe(false);
  });
  it('tombstones a deleted own case even when malformed family bytes prevent complete cleanup', async () => {
    const binding = opened(); localStorage.setItem(`${binding.family}unexpected-private-entry`, 'preserve for investigation');
    expect(acknowledgeAdmissionsCaseDeletion(binding, 'case-a')).toMatchObject({ tombstoned: true, cleanup: 'residual_unknown' });
    expect(await readAdmissionsActionsRecovery(binding)).toEqual({ ok: false, reason: 'deleted' });
  });
  it('legacy import ACK retains raw marks, false-to-true edits and unrelated browser keys exactly', async () => {
    const binding = opened(); const raw = '{"a::Transcript":true,"b::CV":false,"unrelated::Other":true}'; localStorage.setItem('ashyq.docsDone', raw);
    const captured = value(await readAdmissionsLegacyCandidates(binding)); expect(captured.candidates).toHaveLength(2);
    expect(captured.candidates.every(candidate => candidate.legacy_value === true && candidate.source_version === 'unknown' && candidate.original_reported_at === null)).toBe(true);
    const body: ActionRequestV1 = { schema_version: 'admissions-actions-v1', client_write_uuid: firstUuid, expected_revision: 1,
      kind: 'import_legacy_marks', legacy_snapshot_digest: captured.legacy_snapshot_digest,
      mappings: [{ task_id: 'task-a', legacy_key_digest: captured.candidates[0]!.legacy_key_digest, expected_binding_digest: null,
        source_preview_digest: null, legacy_value: true, confirmed_prepared_report: true, source_version: 'unknown', original_reported_at: null }], entered_at: null };
    await saved(binding, body); const changedRaw = '{"a::Transcript":true,"b::CV":true,"unrelated::Other":true}';
    localStorage.setItem('ashyq.docsDone', changedRaw); localStorage.setItem('unrelated-app', 'keep');
    expect((await acknowledgeAdmissionsAction(binding, body, await receipt(body))).ok).toBe(true);
    expect(localStorage.getItem('ashyq.docsDone')).toBe(changedRaw); expect(localStorage.getItem('unrelated-app')).toBe('keep');
    expect(value(await readAdmissionsLegacyCandidates(binding)).candidates).toHaveLength(3);
  });
  it('legacy candidates never coerce false, numbers or strings into prepared reports', async () => {
    const binding = opened(); localStorage.setItem('ashyq.docsDone', '{"a":false,"b":1,"c":"true","d":true}');
    expect(value(await readAdmissionsLegacyCandidates(binding)).candidates).toHaveLength(1);
  });
  it('native acknowledged logout clears this scoped G3 family without changing unrelated appearance data', async () => {
    const binding = opened(); await saved(binding); localStorage.setItem('ashyq.theme', 'dark');
    forgetApplicantBrowserData(); expect(localStorage.getItem(entryKey(binding))).toBeNull();
    expect(localStorage.getItem(`${binding.family}fence`)).toBeNull(); expect(localStorage.getItem('ashyq.theme')).toBe('dark');
    expect((await readAdmissionsActionsRecovery(binding)).ok).toBe(false);
  });
  it('normalizes typed UTC only for server digest comparison while preserving transmitted Z and microseconds', async () => {
    const binding = opened(); const body = command(); await saved(binding, body); const ack = await receipt(body);
    ack.accepted_at = ack.accepted_at.replace('+00:00', 'Z');
    expect((await acknowledgeAdmissionsAction(binding, body, ack)).ok).toBe(true);
    const selector: ActionRequestV1 = { schema_version: 'admissions-actions-v1', kind: 'select_active_preparation', client_write_uuid: secondUuid,
      expected_revision: 1, origin: 'g2', policy: 'follow_current_accepted', observed_head: { origin: 'g2', profile_id: 'case-a',
        native_schema_version: 'shared-route-v1', revision: 1, client_write_uuid: firstUuid,
        snapshot_digest: 'a'.repeat(64), allocation_digest: 'b'.repeat(64), accepted_at: '2026-10-12T00:00:00.123456Z' } };
    const canonical = { ...selector, observed_head: { ...selector.observed_head, accepted_at: '2026-10-12T00:00:00.123456+00:00' } };
    expect(await g3RequestDigest('case-a', selector)).toBe(await g3RequestDigest('case-a', canonical));
    expect(selector.observed_head.accepted_at).toBe('2026-10-12T00:00:00.123456Z');
  });
  it('rechecks the exact owner after a local-storage read and keeps the original bytes', async () => {
    const binding = opened(); const original = await saved(binding); const originalGet = Storage.prototype.getItem; let changed = false;
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(function (this: Storage, key: string) {
      const result = originalGet.call(this, key);
      if (key === indexKey(binding) && !changed) { changed = true; owner('auth:[\"b\",\"org-b\"]'); }
      return result;
    });
    expect((await readAdmissionsActionsRecovery(binding)).ok).toBe(false);
    expect(localStorage.getItem(entryKey(binding))).toBe(original.raw);
  });
  it('refuses a late own ACK after its case epoch changes during digest validation', async () => {
    const binding = opened(); const original = await saved(binding); const ack = await receipt(command());
    const originalDigest = crypto.subtle.digest.bind(crypto.subtle); let reads = 0;
    vi.spyOn(crypto.subtle, 'digest').mockImplementation(async (algorithm, data) => {
      const result = await originalDigest(algorithm, data); reads += 1;
      if (reads === 2) live = { ...live, case_epoch: 2 }; return result;
    });
    expect((await acknowledgeAdmissionsAction(binding, command(), ack)).ok).toBe(false);
    expect(localStorage.getItem(entryKey(binding))).toBe(original.raw);
  });
  it('refuses a family beyond the finite UUID limit without truncating or rewriting it', async () => {
    const binding = opened();
    for (let index = 0; index < 65; index += 1) localStorage.setItem(`${binding.family}intent.${index.toString(16).padStart(8, '0')}-2222-4333-8444-555555555555`, 'unreadable original');
    expect(await readAdmissionsActionsRecovery(binding)).toEqual({ ok: false, reason: 'limit' });
    expect(localStorage.getItem(indexKey(binding))).toBeNull(); expect(localStorage.length).toBe(67);
  });

  it('validates a select-plan ACK against canonical native UTC hashes without storing its full server receipt', async () => {
    const binding = opened();
    const observed = { origin: 'g2' as const, profile_id: 'case-a', native_schema_version: 'shared-route-v1' as const, revision: 1,
      client_write_uuid: secondUuid, snapshot_digest: 'a'.repeat(64), allocation_digest: 'b'.repeat(64), accepted_at: '2026-10-12T00:00:00.123456Z' };
    const body: ActionRequestV1 = { schema_version: 'admissions-actions-v1', kind: 'select_active_preparation', client_write_uuid: firstUuid,
      expected_revision: 0, origin: 'g2', policy: 'follow_current_accepted', observed_head: observed };
    const original = await saved(binding, body);
    // Explicit typed Python datetime.isoformat values in the synthetic server canonical payload.
    const canonicalHead = { ...observed, accepted_at: '2026-10-12T00:00:00.123456+00:00' };
    const canonicalRequest = { ...body, observed_head: canonicalHead };
    const requestHash = createHash('sha256').update(g3Canonical({ schema_version: 'g3-action-request-digest-v1', profile_id: 'case-a', request: canonicalRequest })).digest('hex');
    const payload: Omit<ActionWriteReceiptV1, 'receipt_digest'> = { schema_version: 'admissions-actions-v1', event_id: 'selector-event', profile_id: 'case-a',
      kind: 'select_active_preparation', revision: 1, expected_revision: 0, client_write_uuid: firstUuid, request: canonicalRequest,
      canonical_request_digest: requestHash, accepted_at: '2026-10-12T01:02:03.400000+00:00',
      actor: { schema_version: 'g3-actor-reference-v1', actor_kind: 'authenticated_principal', actor_ref_digest: 'c'.repeat(64) },
      predecessor_event_id: null, before_state_digest: null, after_state_digest: 'd'.repeat(64),
      applied_delta: { applications: [], document_tasks: [], active_preparation: { origin: 'g2', policy: 'follow_current_accepted', observed_head: canonicalHead,
        event_ref: { event_id: 'selector-event', revision: 1, kind: 'select_active_preparation' } }, corrected_declaration: null, previous_binding_digest: null, declaration: null },
      affected_refs: { application_ids: [], document_task_ids: [], active_selector_changed: true } };
    const ack: ActionWriteReceiptV1 = { ...payload, request: body, accepted_at: '2026-10-12T01:02:03.4Z',
      applied_delta: { ...payload.applied_delta, active_preparation: { ...payload.applied_delta.active_preparation!, observed_head: observed } },
      receipt_digest: createHash('sha256').update(g3Canonical({ schema_version: 'g3-action-receipt-digest-v1', receipt: payload })).digest('hex') };
    const confirmed = value(await acknowledgeAdmissionsAction(binding, body, ack));
    expect(confirmed.entry.body).toEqual(original.entry.body); expect(confirmed.entry.descriptor.receipt_ref?.canonical_request_digest).toBe(requestHash);
    expect(Object.keys(confirmed.entry)).toEqual(['schema_version', 'owner_binding', 'profile_id', 'generation', 'draft_generation', 'entry_revision', 'descriptor', 'body', 'pending_state']);
    expect(Object.keys(confirmed.entry.descriptor.receipt_ref ?? {})).toHaveLength(4);
  });
  it('separates exact case families even when identifiers contain the key delimiter', async () => {
    const binding = opened(); const subLive: G3LiveCaseIdentity = { scope: undefined, profile_id: 'case-a.more', case_epoch: 1 };
    const sibling = value(openAdmissionsActionsRecovery(undefined, 'case-a.more', 1, () => subLive));
    const storedSibling = await saved(sibling, command(secondUuid)); await saved(binding);
    expect(sibling.family.startsWith(binding.family)).toBe(false);
    expect(acknowledgeAdmissionsCaseDeletion(binding, 'case-a').tombstoned).toBe(true);
    expect(localStorage.getItem(entryKey(sibling, secondUuid))).toBe(storedSibling.raw);
    expect((await readAdmissionsActionsRecovery(sibling)).ok).toBe(true);
  });

  it('captures the acknowledged intent and immutable receipt before asynchronous caller-side edits', async () => {
    const binding = opened(); const original = await saved(binding); const body = command(); const ack = await receipt(body);
    const originalDigest = crypto.subtle.digest.bind(crypto.subtle); let changed = false;
    vi.spyOn(crypto.subtle, 'digest').mockImplementation(async (algorithm, data) => {
      const result = await originalDigest(algorithm, data);
      if (!changed) { changed = true; body.personal.label = 'Newer unsent edit'; ack.event_id = 'Mutated caller receipt'; }
      return result;
    });
    const confirmed = value(await acknowledgeAdmissionsAction(binding, body, ack));
    expect(confirmed.entry.body).toEqual(original.entry.body);
    expect(confirmed.entry.descriptor.receipt_ref?.event_id).toBe('event-a');
    expect(body.personal.label).toBe('Newer unsent edit');
  });

});

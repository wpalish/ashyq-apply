/** Personal inputs + references only. No dispatch, current-state cache or admission claim. */
import { currentApplicantOwner } from './applicantStorage';
import {
  ACTION_EXPECTED_REVISION_MAX, ACTION_REVISION_MAX, isActionRequestV1, isActionWriteReceiptShapeV1,
  type ActionCommandKind, type ActionRequestV1, type ActionWriteReceiptV1, type NativeHeadV1,
} from '@/types/admissionsActions';

export const G3_RECOVERY_ENTRY_BYTES = 256 * 1024;
export const G3_RECOVERY_INDEX_BYTES = 128 * 1024;
export const G3_RECOVERY_ENTRIES_MAX = 64;
const FAMILY = 'ashyq.admissionsActionsRecovery.v1.';
const MAX_COUNTER = Number.MAX_SAFE_INTEGER - 1;
export interface G3LiveCaseIdentity { scope: string | undefined | null; profile_id: string | null; case_epoch: number }
export interface G3RecoveryBinding {
  readonly owner_binding: string; readonly profile_id: string; readonly case_epoch: number;
  readonly generation: string; readonly family: string;
  /** The owning tree increments its epoch on every owner/case activation, including A→B→A. */
  readonly current: () => G3LiveCaseIdentity;
}
export interface G3AckReferenceV1 {
  event_id: string; revision: number; canonical_request_digest: string; receipt_digest: string;
}
export type G3PendingState = 'not_sent' | 'sending' | 'uncertain' | 'conflict';
export interface G3EntryDescriptorV1 {
  client_write_uuid: string; payload_digest: string; base_server_revision: number; kind: ActionCommandKind;
  application_ids: string[]; document_task_ids: string[]; result_ids: string[]; source_preview_digests: string[];
  status: 'pending' | 'acknowledged'; receipt_ref: G3AckReferenceV1 | null;
}
export interface G3CaseLocalIndexV1 {
  schema_version: 'g3-case-local-index-v1'; owner_binding: string; profile_id: string;
  generation: string; entries: G3EntryDescriptorV1[];
}
export interface G3IntentEntryV1 {
  schema_version: 'g3-personal-intent-entry-v1'; owner_binding: string; profile_id: string; generation: string;
  draft_generation: number; entry_revision: number; descriptor: G3EntryDescriptorV1;
  body: ActionRequestV1; pending_state: G3PendingState | null;
}
interface G3FamilyFenceV1 {
  schema_version: 'g3-case-family-fence-v1'; owner_binding: string; profile_id: string;
  generation: string; deleted: boolean;
}
export type G3RecoveryFailure = 'owner' | 'case' | 'generation' | 'deleted' | 'storage' | 'invalid'
  | 'changed' | 'index_missing' | 'index_mismatch' | 'oversize' | 'limit' | 'digest' | 'ack';
export type G3RecoveryResult<T> = { ok: true; value: T } | { ok: false; reason: G3RecoveryFailure };
export interface G3RecoveredCaseV1 { index: G3CaseLocalIndexV1; index_raw: string | null; entries: G3IntentEntryV1[] }
export interface G3SavedIntentV1 { entry: G3IntentEntryV1; raw: string; index_raw: string }
export interface G3DeleteCleanupV1 {
  tombstoned: boolean; cleanup: 'completed_best_effort' | 'residual_unknown'; reason: G3RecoveryFailure | null;
}
const object = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const fields = (v: Record<string, unknown>, names: readonly string[]) => Object.keys(v).length === names.length && names.every(k => Object.hasOwn(v, k));
const exact = (v: unknown, max = 32): v is string => typeof v === 'string' && Array.from(v).length >= 1
  && Array.from(v).length <= max && v === v.trim() && !Array.from(v).some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127);
const integer = (v: unknown, max = MAX_COUNTER): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 && v <= max;
const digest = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{64}$/.test(v);
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v);
const bytes = (v: string) => new TextEncoder().encode(v).length;
const fail = <T>(reason: G3RecoveryFailure): G3RecoveryResult<T> => ({ ok: false, reason });
const success = <T>(value: T): G3RecoveryResult<T> => ({ ok: true, value });

/** Known G3 object field names are ASCII; sorted keys match server canonical JSON, arrays retain order. */
export function g3Canonical(value: unknown): string {
  const clean = (v: unknown, depth = 0): unknown => {
    if (depth > 64) throw new Error('Unsupported personal input structure');
    if (v === null || typeof v === 'string' || typeof v === 'boolean') return v;
    if (typeof v === 'number' && Number.isFinite(v)) return v;
    if (Array.isArray(v)) return v.map(item => clean(item, depth + 1));
    if (object(v) && (Object.getPrototypeOf(v) === Object.prototype || Object.getPrototypeOf(v) === null)) {
      return Object.fromEntries(Object.keys(v).sort().map(key => [key, clean(v[key], depth + 1)]));
    }
    throw new Error('Unsupported personal input value');
  };
  const serialized = JSON.stringify(clean(value));
  if (typeof serialized !== 'string') throw new Error('Unsupported personal input value');
  return serialized;
}
async function hash(value: unknown): Promise<string> {
  const result = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(g3Canonical(value)));
  return Array.from(new Uint8Array(result), part => part.toString(16).padStart(2, '0')).join('');
}
/** Python's typed UTC canonical form keeps all six microsecond digits, without changing local dates. */
function canonicalUtc(value: string): string {
  const matched = /^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.([0-9]{1,6}))?(?:Z|\+00:00)$/.exec(value);
  if (!matched?.[1] || Number.isNaN(Date.parse(value))) throw new Error('Invalid typed UTC instant');
  const fraction = matched[2]?.padEnd(6, '0');
  return `${matched[1]}${fraction && /[1-9]/.test(fraction) ? `.${fraction}` : ''}+00:00`;
}
function headSemantics(head: NativeHeadV1): NativeHeadV1 {
  return head.origin === 'g2' ? { ...head, client_write_uuid: head.client_write_uuid.toLowerCase(), accepted_at: canonicalUtc(head.accepted_at) } : head;
}
/** Schema UUID/UTC parsing affects comparison only; the journal retains the original submitted body. */
function requestSemantics(body: ActionRequestV1): ActionRequestV1 {
  const base = { ...body, client_write_uuid: body.client_write_uuid.toLowerCase() };
  return base.kind === 'select_active_preparation' ? { ...base, observed_head: headSemantics(base.observed_head) } : base;
}
function receiptSemantics(receipt: ActionWriteReceiptV1): ActionWriteReceiptV1 {
  const delta = receipt.applied_delta;
  return { ...receipt, accepted_at: canonicalUtc(receipt.accepted_at), request: requestSemantics(receipt.request),
    applied_delta: { ...delta,
      document_tasks: delta.document_tasks.map(task => ({ ...task,
        binding: task.binding === null ? null : { ...task.binding, accepted_at: canonicalUtc(task.binding.accepted_at) },
        report: { ...task.report, accepted_at: task.report.accepted_at === null ? null : canonicalUtc(task.report.accepted_at) } })),
      active_preparation: delta.active_preparation === null ? null : { ...delta.active_preparation, observed_head: headSemantics(delta.active_preparation.observed_head) },
      declaration: delta.declaration === null ? null : { ...delta.declaration, accepted_at: canonicalUtc(delta.declaration.accepted_at) },
    } };
}
export function g3RequestDigest(profileId: string, body: ActionRequestV1): Promise<string> {
  return hash({ schema_version: 'g3-action-request-digest-v1', profile_id: profileId, request: requestSemantics(body) });
}
function family(owner: string, profileId: string): string {
  const caseToken = encodeURIComponent(profileId).replace(/\./g, '%2E');
  return `ashyq.owner.${encodeURIComponent(owner)}.${FAMILY}${caseToken}.`;
}
const fenceKey = (binding: G3RecoveryBinding) => `${binding.family}fence`;
const indexKey = (binding: G3RecoveryBinding) => `${binding.family}index`;
const tombstoneKey = (binding: G3RecoveryBinding) => `${binding.family}tombstone`;
const entryKey = (binding: G3RecoveryBinding, intentUuid: string) => `${binding.family}intent.${intentUuid}`;
function identityFailure(binding: G3RecoveryBinding): G3RecoveryFailure | null {
  try {
    const live = binding.current();
    const owner = live.scope === undefined ? 'demo' : live.scope === null ? null : `auth:${live.scope}`;
    if (owner !== binding.owner_binding || currentApplicantOwner() !== binding.owner_binding) return 'owner';
    if (live.profile_id !== binding.profile_id || live.case_epoch !== binding.case_epoch) return 'case';
    if (!exact(binding.profile_id) || !integer(binding.case_epoch)
      || binding.family !== family(binding.owner_binding, binding.profile_id)) return 'invalid';
    return null;
  } catch { return 'owner'; }
}
function parse(raw: string): unknown { return JSON.parse(raw) as unknown; }
function validFence(v: unknown, binding: G3RecoveryBinding): v is G3FamilyFenceV1 {
  return object(v) && fields(v, ['schema_version', 'owner_binding', 'profile_id', 'generation', 'deleted'])
    && v.schema_version === 'g3-case-family-fence-v1' && v.owner_binding === binding.owner_binding
    && v.profile_id === binding.profile_id && uuid(v.generation) && typeof v.deleted === 'boolean';
}
function fenceFailure(binding: G3RecoveryBinding): G3RecoveryFailure | null {
  const identity = identityFailure(binding); if (identity) return identity;
  try {
    const tombstoneRaw = window.localStorage.getItem(tombstoneKey(binding));
    if (tombstoneRaw !== null) {
      if (bytes(tombstoneRaw) > 2048) return 'invalid';
      const tombstone = parse(tombstoneRaw);
      return validFence(tombstone, binding) && tombstone.deleted ? 'deleted' : 'invalid';
    }
    const raw = window.localStorage.getItem(fenceKey(binding));
    if (identityFailure(binding)) return 'owner';
    if (raw === null || bytes(raw) > 2048) return 'generation';
    const value = parse(raw);
    if (!validFence(value, binding)) return 'invalid';
    if (value.deleted) return 'deleted';
    return value.generation === binding.generation ? null : 'generation';
  } catch { return 'storage'; }
}
function active(binding: G3RecoveryBinding): G3RecoveryResult<true> {
  const error = fenceFailure(binding); return error ? fail(error) : success(true);
}
/** Reads are fenced on both sides; invalid bytes remain available for explicit investigation. */
function readRaw(binding: G3RecoveryBinding, key: string): G3RecoveryResult<string | null> {
  const check = active(binding); if (!check.ok) return check;
  try {
    const raw = window.localStorage.getItem(key);
    const after = active(binding); return after.ok ? success(raw) : after;
  } catch { return fail('storage'); }
}
function writeRaw(binding: G3RecoveryBinding, key: string, raw: string, expectedRaw: string | null): G3RecoveryResult<true> {
  const check = active(binding); if (!check.ok) return check;
  try {
    if (window.localStorage.getItem(key) !== expectedRaw) return fail('changed');
    const before = active(binding); if (!before.ok) return before;
    window.localStorage.setItem(key, raw);
    const after = active(binding); if (!after.ok) return after;
    return window.localStorage.getItem(key) === raw && active(binding).ok ? success(true) : fail('changed');
  } catch { return fail('storage'); }
}
function ownFamilyKeys(binding: G3RecoveryBinding): G3RecoveryResult<string[]> {
  const check = active(binding); if (!check.ok) return check;
  try {
    const keys = Array.from({ length: window.localStorage.length }, (_, i) => window.localStorage.key(i))
      .filter((key): key is string => key !== null && key.startsWith(binding.family));
    const after = active(binding); if (!after.ok) return after;
    if (keys.length > G3_RECOVERY_ENTRIES_MAX + 3) return fail('limit');
    if (keys.some(key => key !== fenceKey(binding) && key !== indexKey(binding) && key !== tombstoneKey(binding)
      && !uuid(key.slice(`${binding.family}intent.`.length)))
      || keys.some(key => key !== fenceKey(binding) && key !== indexKey(binding) && key !== tombstoneKey(binding) && !key.startsWith(`${binding.family}intent.`))) return fail('invalid');
    return success(keys.filter(key => key.startsWith(`${binding.family}intent.`)).sort());
  } catch { return fail('storage'); }
}
/** Creation only in a genuinely empty own family. A lost/corrupt fence is never recreated over entries. */
export function openAdmissionsActionsRecovery(
  scope: string | undefined | null, profileId: string, caseEpoch: number, current: () => G3LiveCaseIdentity,
): G3RecoveryResult<G3RecoveryBinding> {
  if (scope === null || !exact(profileId) || !integer(caseEpoch)) return fail('invalid');
  const owner = scope === undefined ? 'demo' : `auth:${scope}`;
  let instance: string;
  try { instance = crypto.randomUUID(); } catch { return fail('digest'); }
  const provisional: G3RecoveryBinding = { owner_binding: owner, profile_id: profileId, case_epoch: caseEpoch,
    generation: instance, family: family(owner, profileId), current };
  const identity = identityFailure(provisional); if (identity) return fail(identity);
  try {
    const deletedRaw = window.localStorage.getItem(tombstoneKey(provisional));
    if (deletedRaw !== null) {
      if (bytes(deletedRaw) > 2048) return fail('oversize');
      const tombstone = parse(deletedRaw);
      return validFence(tombstone, provisional) && tombstone.deleted ? fail('deleted') : fail('invalid');
    }
    const raw = window.localStorage.getItem(fenceKey(provisional));
    if (identityFailure(provisional)) return fail('owner');
    if (raw !== null) {
      if (bytes(raw) > 2048) return fail('oversize');
      const value = parse(raw);
      if (!validFence(value, provisional)) return fail('invalid');
      if (value.deleted) return fail('deleted');
      const binding = { ...provisional, generation: value.generation };
      const checked = active(binding); return checked.ok ? success(binding) : checked;
    }
    const hasFamily = Array.from({ length: window.localStorage.length }, (_, i) => window.localStorage.key(i))
      .some(key => key?.startsWith(provisional.family));
    if (hasFamily) return fail('generation');
    const initial: G3FamilyFenceV1 = { schema_version: 'g3-case-family-fence-v1', owner_binding: owner,
      profile_id: profileId, generation: provisional.generation, deleted: false };
    if (identityFailure(provisional) || window.localStorage.getItem(fenceKey(provisional)) !== null) return fail('changed');
    window.localStorage.setItem(fenceKey(provisional), JSON.stringify(initial));
    const checked = active(provisional); return checked.ok ? success(provisional) : checked;
  } catch { return fail('storage'); }
}
function references(body: ActionRequestV1): Pick<G3EntryDescriptorV1, 'application_ids' | 'document_task_ids' | 'result_ids' | 'source_preview_digests'> {
  const applications: string[] = []; const tasks: string[] = []; const results: string[] = []; const previews: string[] = [];
  if ('application_id' in body && body.application_id !== null) applications.push(body.application_id);
  if ('task_id' in body) tasks.push(body.task_id);
  if (body.kind === 'set_personal_details') (body.target.kind === 'application' ? applications : tasks).push(body.target.id);
  if (body.kind === 'create_application') results.push(body.target.result_id);
  if ('source' in body) { results.push(body.source.result_id); previews.push(body.source_preview_digest); }
  if (body.kind === 'declare_submission') tasks.push(...body.submission.document_task_ids);
  if (body.kind === 'correct_declaration' && body.replacement.kind === 'submission') tasks.push(...body.replacement.submission.document_task_ids);
  if (body.kind === 'import_legacy_marks') for (const mapping of body.mappings) {
    tasks.push(mapping.task_id); if (mapping.source_preview_digest !== null) previews.push(mapping.source_preview_digest);
  }
  if ('personal' in body) tasks.push(...body.personal.depends_on_task_ids);
  return { application_ids: [...new Set(applications)], document_task_ids: [...new Set(tasks)], result_ids: [...new Set(results)], source_preview_digests: [...new Set(previews)] };
}
function descriptor(body: ActionRequestV1, payloadDigest: string): G3EntryDescriptorV1 {
  return { client_write_uuid: body.client_write_uuid.toLowerCase(), payload_digest: payloadDigest,
    base_server_revision: body.expected_revision, kind: body.kind, ...references(body), status: 'pending', receipt_ref: null };
}
function validAckRef(v: unknown): v is G3AckReferenceV1 {
  return object(v) && fields(v, ['event_id', 'revision', 'canonical_request_digest', 'receipt_digest']) && exact(v.event_id)
    && integer(v.revision, ACTION_REVISION_MAX) && v.revision >= 1 && digest(v.canonical_request_digest) && digest(v.receipt_digest);
}
function validDescriptor(v: unknown): v is G3EntryDescriptorV1 {
  const ids = (value: unknown, max: number) => Array.isArray(value) && value.length <= max
    && value.every(item => exact(item)) && new Set(value).size === value.length;
  return object(v) && fields(v, ['client_write_uuid', 'payload_digest', 'base_server_revision', 'kind', 'application_ids',
    'document_task_ids', 'result_ids', 'source_preview_digests', 'status', 'receipt_ref']) && uuid(v.client_write_uuid)
    && digest(v.payload_digest) && integer(v.base_server_revision, ACTION_EXPECTED_REVISION_MAX)
    && typeof v.kind === 'string' && ['create_application', 'create_personal_task', 'bind_source_task', 'rebind_source_task',
      'set_document_self_report', 'set_personal_details', 'set_planning_status', 'declare_submission', 'declare_withdrawal',
      'correct_declaration', 'import_legacy_marks', 'select_active_preparation'].includes(v.kind)
    && ids(v.application_ids, 1) && ids(v.document_task_ids, 400) && ids(v.result_ids, 1)
    && Array.isArray(v.source_preview_digests) && v.source_preview_digests.length <= 50
    && v.source_preview_digests.every(digest) && new Set(v.source_preview_digests).size === v.source_preview_digests.length
    && ((v.status === 'pending' && v.receipt_ref === null) || (v.status === 'acknowledged' && validAckRef(v.receipt_ref)
      && v.receipt_ref.revision === v.base_server_revision + 1 && v.receipt_ref.canonical_request_digest === v.payload_digest));
}
function validIndex(v: unknown, binding: G3RecoveryBinding): v is G3CaseLocalIndexV1 {
  return object(v) && fields(v, ['schema_version', 'owner_binding', 'profile_id', 'generation', 'entries'])
    && v.schema_version === 'g3-case-local-index-v1' && v.owner_binding === binding.owner_binding
    && v.profile_id === binding.profile_id && v.generation === binding.generation && Array.isArray(v.entries)
    && v.entries.length <= G3_RECOVERY_ENTRIES_MAX && v.entries.every(validDescriptor)
    && new Set(v.entries.map(entry => entry.client_write_uuid)).size === v.entries.length;
}
function validEntry(v: unknown, binding: G3RecoveryBinding): v is G3IntentEntryV1 {
  if (!object(v) || !fields(v, ['schema_version', 'owner_binding', 'profile_id', 'generation', 'draft_generation', 'entry_revision',
    'descriptor', 'body', 'pending_state']) || v.schema_version !== 'g3-personal-intent-entry-v1'
    || v.owner_binding !== binding.owner_binding || v.profile_id !== binding.profile_id || v.generation !== binding.generation
    || !integer(v.draft_generation) || !integer(v.entry_revision) || !validDescriptor(v.descriptor) || !isActionRequestV1(v.body)) return false;
  const expected = descriptor(v.body, v.descriptor.payload_digest);
  const identity = { ...v.descriptor, status: 'pending', receipt_ref: null };
  return g3Canonical(identity) === g3Canonical(expected)
    && ((v.descriptor.status === 'acknowledged' && v.pending_state === null)
      || (v.descriptor.status === 'pending' && typeof v.pending_state === 'string' && ['not_sent', 'sending', 'uncertain', 'conflict'].includes(v.pending_state)));
}
async function scan(binding: G3RecoveryBinding): Promise<G3RecoveryResult<{ entries: G3IntentEntryV1[]; raws: Map<string, string> }>> {
  const keys = ownFamilyKeys(binding); if (!keys.ok) return keys;
  const entries: G3IntentEntryV1[] = []; const raws = new Map<string, string>();
  for (const key of keys.value) {
    const raw = readRaw(binding, key); if (!raw.ok) return raw;
    if (raw.value === null) return fail('changed');
    if (bytes(raw.value) > G3_RECOVERY_ENTRY_BYTES) return fail('oversize');
    let entry: unknown;
    try { entry = parse(raw.value); } catch { return fail('invalid'); }
    if (!validEntry(entry, binding) || key !== entryKey(binding, entry.descriptor.client_write_uuid)) return fail('invalid');
    let actualDigest: string;
    try { actualDigest = await g3RequestDigest(binding.profile_id, entry.body); } catch { return fail('digest'); }
    const after = readRaw(binding, key); if (!after.ok) return after;
    if (after.value !== raw.value) return fail('changed');
    if (actualDigest !== entry.descriptor.payload_digest) return fail('digest');
    entries.push(entry); raws.set(entry.descriptor.client_write_uuid, raw.value);
  }
  for (const [id, raw] of raws) {
    const finalRaw = readRaw(binding, entryKey(binding, id)); if (!finalRaw.ok) return finalRaw;
    if (finalRaw.value !== raw) return fail('changed');
  }
  const again = ownFamilyKeys(binding); if (!again.ok) return again;
  if (g3Canonical(keys.value) !== g3Canonical(again.value)) return fail('changed');
  return success({ entries, raws });
}
function indexFor(binding: G3RecoveryBinding, entries: G3IntentEntryV1[]): G3CaseLocalIndexV1 {
  return { schema_version: 'g3-case-local-index-v1', owner_binding: binding.owner_binding, profile_id: binding.profile_id,
    generation: binding.generation, entries: entries.map(entry => entry.descriptor).sort((a, b) => a.client_write_uuid < b.client_write_uuid ? -1 : a.client_write_uuid > b.client_write_uuid ? 1 : 0) };
}
async function inspectCase(binding: G3RecoveryBinding): Promise<G3RecoveryResult<G3RecoveredCaseV1>> {
  const raw = readRaw(binding, indexKey(binding)); if (!raw.ok) return raw;
  if (raw.value !== null && bytes(raw.value) > G3_RECOVERY_INDEX_BYTES) return fail('oversize');
  let index: unknown;
  try { index = raw.value === null ? null : parse(raw.value); } catch { return fail('invalid'); }
  if (index !== null && !validIndex(index, binding)) return fail('invalid');
  const data = await scan(binding); if (!data.ok) return data;
  const after = readRaw(binding, indexKey(binding)); if (!after.ok) return after;
  if (after.value !== raw.value) return fail('changed');
  const expected = indexFor(binding, data.value.entries);
  if (index === null && data.value.entries.length) return fail('index_missing');
  if (index !== null && g3Canonical(index) !== g3Canonical(expected)) return fail('index_mismatch');
  return success({ index: expected, index_raw: raw.value, entries: data.value.entries });
}
/** Hydration is display-only: no send, automatic retry, current replacement or invalid-byte cleanup. */
export function readAdmissionsActionsRecovery(binding: G3RecoveryBinding): Promise<G3RecoveryResult<G3RecoveredCaseV1>> {
  return inspectCase(binding);
}
/** Explicit reviewed reconciliation can recover own sibling entries after index loss/interleaving. */
export async function reconcileAdmissionsActionsIndex(
  binding: G3RecoveryBinding, expectedIndexRaw: string | null,
): Promise<G3RecoveryResult<G3RecoveredCaseV1>> {
  const raw = readRaw(binding, indexKey(binding)); if (!raw.ok) return raw;
  if (raw.value !== expectedIndexRaw) return fail('changed');
  if (raw.value !== null) {
    if (bytes(raw.value) > G3_RECOVERY_INDEX_BYTES) return fail('oversize');
    let parsed: unknown; try { parsed = parse(raw.value); } catch { return fail('invalid'); }
    if (!validIndex(parsed, binding)) return fail('invalid');
  }
  const scanned = await scan(binding); if (!scanned.ok) return scanned;
  const next = JSON.stringify(indexFor(binding, scanned.value.entries));
  if (bytes(next) > G3_RECOVERY_INDEX_BYTES) return fail('oversize');
  const written = writeRaw(binding, indexKey(binding), next, expectedIndexRaw); if (!written.ok) return written;
  return inspectCase(binding);
}
/** Must complete successfully before the caller is allowed to dispatch this exact UUID/body. */
export async function journalAdmissionsAction(
  binding: G3RecoveryBinding, body: ActionRequestV1, draftGeneration: number,
): Promise<G3RecoveryResult<G3SavedIntentV1>> {
  if (!isActionRequestV1(body) || !integer(draftGeneration)) return fail('invalid');
  if (body.kind === 'select_active_preparation' && body.observed_head.profile_id !== binding.profile_id) return fail('invalid');
  let captured: ActionRequestV1;
  try { captured = JSON.parse(JSON.stringify(body)) as ActionRequestV1; } catch { return fail('invalid'); }
  if (!isActionRequestV1(captured) || (captured.kind === 'select_active_preparation' && captured.observed_head.profile_id !== binding.profile_id)) return fail('invalid');
  if (bytes(JSON.stringify(captured)) > G3_RECOVERY_ENTRY_BYTES - 4096) return fail('oversize');
  const state = await inspectCase(binding); if (!state.ok) return state;
  const id = captured.client_write_uuid.toLowerCase();
  if (state.value.entries.some(entry => entry.descriptor.client_write_uuid === id)) return fail('changed');
  if (state.value.entries.length >= G3_RECOVERY_ENTRIES_MAX) return fail('limit');
  let payloadDigest: string;
  try { payloadDigest = await g3RequestDigest(binding.profile_id, captured); } catch { return fail('digest'); }
  const entry: G3IntentEntryV1 = { schema_version: 'g3-personal-intent-entry-v1', owner_binding: binding.owner_binding,
    profile_id: binding.profile_id, generation: binding.generation, draft_generation: draftGeneration,
    entry_revision: 0, descriptor: descriptor(captured, payloadDigest), body: captured, pending_state: 'not_sent' };
  const raw = JSON.stringify(entry); if (bytes(raw) > G3_RECOVERY_ENTRY_BYTES) return fail('oversize');
  const current = await inspectCase(binding); if (!current.ok) return current;
  if (current.value.index_raw !== state.value.index_raw) return fail('changed');
  const combined = [...current.value.entries, entry];
  const nextIndex = JSON.stringify(indexFor(binding, combined));
  if (bytes(nextIndex) > G3_RECOVERY_INDEX_BYTES) return fail('oversize');
  const stored = writeRaw(binding, entryKey(binding, id), raw, null); if (!stored.ok) return stored;
  // Entry first: an index-write failure preserves the body for explicit reconciliation; dispatch is refused.
  const indexed = writeRaw(binding, indexKey(binding), nextIndex, current.value.index_raw); if (!indexed.ok) return indexed;
  const verified = await inspectCase(binding); if (!verified.ok) return verified;
  return success({ entry, raw, index_raw: nextIndex });
}
/** Changing body/CAS needs explicit review and a new UUID; this only marks an existing intent. */
export async function markAdmissionsActionState(
  binding: G3RecoveryBinding, intentUuid: string, expectedRaw: string, state: Exclude<G3PendingState, 'not_sent'>,
): Promise<G3RecoveryResult<G3SavedIntentV1>> {
  if (!uuid(intentUuid) || !['sending', 'uncertain', 'conflict'].includes(state)) return fail('invalid');
  const current = await inspectCase(binding); if (!current.ok) return current;
  const original = current.value.entries.find(entry => entry.descriptor.client_write_uuid === intentUuid);
  if (!original || original.descriptor.status !== 'pending') return fail('changed');
  const raw = readRaw(binding, entryKey(binding, intentUuid)); if (!raw.ok) return raw;
  if (raw.value !== expectedRaw || raw.value === null || original.entry_revision >= MAX_COUNTER) return fail('changed');
  try { if (g3Canonical(parse(raw.value)) !== g3Canonical(original)) return fail('changed'); } catch { return fail('invalid'); }
  const next: G3IntentEntryV1 = { ...original, entry_revision: original.entry_revision + 1, pending_state: state };
  const nextRaw = JSON.stringify(next); const write = writeRaw(binding, entryKey(binding, intentUuid), nextRaw, expectedRaw);
  if (!write.ok) return write;
  const verified = await inspectCase(binding); if (!verified.ok) return verified;
  return success({ entry: next, raw: nextRaw, index_raw: current.value.index_raw ?? '' });
}
/** Explicit retry returns exactly the original submitted body, with no revision/preview/UUID refresh. */
export async function admissionsActionRetryBody(
  binding: G3RecoveryBinding, intentUuid: string, expectedRaw: string,
): Promise<G3RecoveryResult<ActionRequestV1>> {
  if (!uuid(intentUuid)) return fail('invalid');
  const current = await inspectCase(binding); if (!current.ok) return current;
  const entry = current.value.entries.find(item => item.descriptor.client_write_uuid === intentUuid);
  const raw = readRaw(binding, entryKey(binding, intentUuid)); if (!raw.ok) return raw;
  if (!entry || entry.descriptor.status !== 'pending' || entry.pending_state === 'conflict' || raw.value !== expectedRaw) return fail('changed');
  return success(JSON.parse(JSON.stringify(entry.body)) as ActionRequestV1);
}
function receiptHeader(receipt: unknown, profileId: string, body: ActionRequestV1): receipt is ActionWriteReceiptV1 {
  if (!isActionWriteReceiptShapeV1(receipt) || !object(receipt) || !fields(receipt, ['schema_version', 'event_id', 'profile_id', 'kind', 'revision', 'expected_revision',
    'client_write_uuid', 'request', 'canonical_request_digest', 'accepted_at', 'actor', 'predecessor_event_id', 'before_state_digest',
    'after_state_digest', 'applied_delta', 'affected_refs', 'receipt_digest']) || receipt.schema_version !== 'admissions-actions-v1'
    || receipt.profile_id !== profileId || !exact(receipt.event_id) || receipt.kind !== body.kind
    || receipt.expected_revision !== body.expected_revision || receipt.revision !== body.expected_revision + 1
    || receipt.client_write_uuid !== body.client_write_uuid.toLowerCase() || !isActionRequestV1(receipt.request)
    || g3Canonical(requestSemantics(receipt.request)) !== g3Canonical(requestSemantics(body))
    || !digest(receipt.canonical_request_digest) || !digest(receipt.after_state_digest) || !digest(receipt.receipt_digest)
    || typeof receipt.accepted_at !== 'string' || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}T.+(?:Z|\+00:00)$/.test(receipt.accepted_at)
    || Number.isNaN(Date.parse(receipt.accepted_at)) || !object(receipt.actor)
    || !fields(receipt.actor, ['schema_version', 'actor_kind', 'actor_ref_digest']) || receipt.actor.schema_version !== 'g3-actor-reference-v1'
    || (receipt.actor.actor_kind !== 'authenticated_principal' && receipt.actor.actor_kind !== 'local_development')
    || !digest(receipt.actor.actor_ref_digest) || !object(receipt.applied_delta) || !object(receipt.affected_refs)) return false;
  if (body.expected_revision === 0 ? receipt.predecessor_event_id !== null || receipt.before_state_digest !== null
    : !exact(receipt.predecessor_event_id) || !digest(receipt.before_state_digest)) return false;
  return fields(receipt.applied_delta, ['applications', 'document_tasks', 'active_preparation', 'corrected_declaration', 'previous_binding_digest', 'declaration'])
    && fields(receipt.affected_refs, ['application_ids', 'document_task_ids', 'active_selector_changed'])
    && Array.isArray(receipt.applied_delta.applications) && receipt.applied_delta.applications.length <= 20
    && Array.isArray(receipt.applied_delta.document_tasks) && receipt.applied_delta.document_tasks.length <= 50
    && Array.isArray(receipt.affected_refs.application_ids) && receipt.affected_refs.application_ids.every(item => exact(item))
    && Array.isArray(receipt.affected_refs.document_task_ids) && receipt.affected_refs.document_task_ids.every(item => exact(item))
    && typeof receipt.affected_refs.active_selector_changed === 'boolean';
}
/** A matching own ACK retires only its UUID. It intentionally cannot replace server current or another draft. */
export async function acknowledgeAdmissionsAction(
  binding: G3RecoveryBinding, submittedBody: ActionRequestV1, incomingReceipt: ActionWriteReceiptV1,
): Promise<G3RecoveryResult<G3SavedIntentV1>> {
  let originalBody: ActionRequestV1; let receipt: ActionWriteReceiptV1;
  try {
    originalBody = JSON.parse(JSON.stringify(submittedBody)) as ActionRequestV1;
    receipt = JSON.parse(JSON.stringify(incomingReceipt)) as ActionWriteReceiptV1;
  } catch { return fail('ack'); }
  if (!isActionRequestV1(originalBody) || !receiptHeader(receipt, binding.profile_id, originalBody)) return fail('ack');
  const current = await inspectCase(binding); if (!current.ok) return current;
  const id = originalBody.client_write_uuid.toLowerCase();
  const entry = current.value.entries.find(item => item.descriptor.client_write_uuid === id);
  if (!entry || g3Canonical(requestSemantics(entry.body)) !== g3Canonical(requestSemantics(originalBody))) return fail('changed');
  let requestHash: string; let receiptHash: string;
  try {
    requestHash = await g3RequestDigest(binding.profile_id, originalBody);
    const { receipt_digest: omitted, ...wire } = receiptSemantics(receipt);
    if (omitted !== receipt.receipt_digest) return fail('ack');
    receiptHash = await hash({ schema_version: 'g3-action-receipt-digest-v1', receipt: wire });
  } catch { return fail('digest'); }
  if (requestHash !== receipt.canonical_request_digest || requestHash !== entry.descriptor.payload_digest || receiptHash !== receipt.receipt_digest) return fail('ack');
  const ref: G3AckReferenceV1 = { event_id: receipt.event_id, revision: receipt.revision,
    canonical_request_digest: requestHash, receipt_digest: receiptHash };
  if (entry.descriptor.status === 'acknowledged') {
    if (g3Canonical(entry.descriptor.receipt_ref) !== g3Canonical(ref)) return fail('ack');
    const raw = readRaw(binding, entryKey(binding, id)); if (!raw.ok) return raw;
    if (raw.value === null) return fail('changed');
    try { if (g3Canonical(parse(raw.value)) !== g3Canonical(entry)) return fail('changed'); } catch { return fail('invalid'); }
    return success({ entry, raw: raw.value, index_raw: current.value.index_raw ?? '' });
  }
  const latest = await inspectCase(binding); if (!latest.ok) return latest;
  const latestEntry = latest.value.entries.find(item => item.descriptor.client_write_uuid === id);
  if (!latestEntry || g3Canonical(latestEntry) !== g3Canonical(entry) || latestEntry.entry_revision >= MAX_COUNTER) return fail('changed');
  const oldRaw = readRaw(binding, entryKey(binding, id)); if (!oldRaw.ok || oldRaw.value === null) return oldRaw.ok ? fail('changed') : oldRaw;
  try { if (g3Canonical(parse(oldRaw.value)) !== g3Canonical(latestEntry)) return fail('changed'); } catch { return fail('invalid'); }
  const next: G3IntentEntryV1 = { ...latestEntry, entry_revision: latestEntry.entry_revision + 1, pending_state: null,
    descriptor: { ...latestEntry.descriptor, status: 'acknowledged', receipt_ref: ref } };
  const nextRaw = JSON.stringify(next);
  const nextIndex = JSON.stringify(indexFor(binding, latest.value.entries.map(item => item.descriptor.client_write_uuid === id ? next : item)));
  if (bytes(nextRaw) > G3_RECOVERY_ENTRY_BYTES || bytes(nextIndex) > G3_RECOVERY_INDEX_BYTES) return fail('oversize');
  const written = writeRaw(binding, entryKey(binding, id), nextRaw, oldRaw.value); if (!written.ok) return written;
  const indexed = writeRaw(binding, indexKey(binding), nextIndex, latest.value.index_raw); if (!indexed.ok) return indexed;
  const verified = await inspectCase(binding); if (!verified.ok) return verified;
  return success({ entry: next, raw: nextRaw, index_raw: nextIndex });
}
/** Successful DELETE retires its captured case even if the same owner has opened another case. */
function deletionIdentityFailure(binding: G3RecoveryBinding): G3RecoveryFailure | null {
  try {
    const scope = binding.current().scope;
    const owner = scope === undefined ? 'demo' : scope === null ? null : `auth:${scope}`;
    if (owner !== binding.owner_binding || currentApplicantOwner() !== binding.owner_binding) return 'owner';
    if (!exact(binding.profile_id) || !integer(binding.case_epoch) || !uuid(binding.generation)
      || binding.family !== family(binding.owner_binding, binding.profile_id)) return 'invalid';
    return null;
  } catch { return 'owner'; }
}
/** Deletion-only guard: verifies captured generation and exact fence/tombstone bytes, never live case/epoch. */
function deletionFenceFailure(
  binding: G3RecoveryBinding, expectedFenceRaw?: string, expectedTombstoneRaw: string | null = null,
): G3RecoveryFailure | null {
  const identity = deletionIdentityFailure(binding); if (identity) return identity;
  try {
    const tombstoneRaw = window.localStorage.getItem(tombstoneKey(binding));
    const afterTombstone = deletionIdentityFailure(binding); if (afterTombstone) return afterTombstone;
    if (tombstoneRaw !== null) {
      if (bytes(tombstoneRaw) > 2048) return 'invalid';
      const tombstone = parse(tombstoneRaw);
      if (!validFence(tombstone, binding) || !tombstone.deleted) return 'invalid';
      if (expectedTombstoneRaw === null) return 'deleted';
      if (tombstoneRaw !== expectedTombstoneRaw) return 'changed';
    } else if (expectedTombstoneRaw !== null) return 'changed';
    const raw = window.localStorage.getItem(fenceKey(binding));
    const afterFence = deletionIdentityFailure(binding); if (afterFence) return afterFence;
    if (raw === null || bytes(raw) > 2048) return 'generation';
    const fence = parse(raw);
    if (!validFence(fence, binding)) return 'invalid';
    if (fence.deleted) return 'deleted';
    if (fence.generation !== binding.generation) return 'generation';
    return expectedFenceRaw !== undefined && raw !== expectedFenceRaw ? 'changed' : null;
  } catch { return 'storage'; }
}
function deletionReadRaw(
  binding: G3RecoveryBinding, key: string, fenceRaw: string, tombstoneRaw: string | null,
): G3RecoveryResult<string | null> {
  const before = deletionFenceFailure(binding, fenceRaw, tombstoneRaw); if (before) return fail(before);
  try {
    const raw = window.localStorage.getItem(key);
    const after = deletionFenceFailure(binding, fenceRaw, tombstoneRaw);
    return after ? fail(after) : success(raw);
  } catch { return fail('storage'); }
}
/** Physically scans only the captured exact family, under the deletion-only guard on every storage I/O. */
function deletionFamilyKeys(
  binding: G3RecoveryBinding, fenceRaw: string, tombstoneRaw: string | null,
): G3RecoveryResult<string[]> {
  const before = deletionFenceFailure(binding, fenceRaw, tombstoneRaw); if (before) return fail(before);
  try {
    const length = window.localStorage.length;
    const afterLength = deletionFenceFailure(binding, fenceRaw, tombstoneRaw); if (afterLength) return fail(afterLength);
    const keys: string[] = [];
    for (let i = 0; i < length; i += 1) {
      const beforeKey = deletionFenceFailure(binding, fenceRaw, tombstoneRaw); if (beforeKey) return fail(beforeKey);
      const key = window.localStorage.key(i);
      const afterKey = deletionFenceFailure(binding, fenceRaw, tombstoneRaw); if (afterKey) return fail(afterKey);
      if (key !== null && key.startsWith(binding.family)) keys.push(key);
    }
    if (keys.length > G3_RECOVERY_ENTRIES_MAX + 3) return fail('limit');
    if (keys.some(key => key !== fenceKey(binding) && key !== indexKey(binding) && key !== tombstoneKey(binding)
      && (!key.startsWith(`${binding.family}intent.`) || !uuid(key.slice(`${binding.family}intent.`.length))))) return fail('invalid');
    return success(keys.filter(key => key.startsWith(`${binding.family}intent.`)).sort());
  } catch { return fail('storage'); }
}
/** Ownership/shape checks authorize best-effort cleanup; a browser digest is not server deletion proof. */
function deletionCandidates(binding: G3RecoveryBinding, fenceRaw: string): G3RecoveryResult<Map<string, string>> {
  const keys = deletionFamilyKeys(binding, fenceRaw, null); if (!keys.ok) return keys;
  const raws = new Map<string, string>();
  const indexRaw = deletionReadRaw(binding, indexKey(binding), fenceRaw, null); if (!indexRaw.ok) return indexRaw;
  if (indexRaw.value !== null) {
    if (bytes(indexRaw.value) > G3_RECOVERY_INDEX_BYTES) return fail('oversize');
    try { if (!validIndex(parse(indexRaw.value), binding)) return fail('invalid'); } catch { return fail('invalid'); }
    raws.set(indexKey(binding), indexRaw.value);
  }
  for (const key of keys.value) {
    const raw = deletionReadRaw(binding, key, fenceRaw, null); if (!raw.ok) return raw;
    if (raw.value === null) return fail('changed');
    if (bytes(raw.value) > G3_RECOVERY_ENTRY_BYTES) return fail('oversize');
    try {
      const entry = parse(raw.value);
      if (!validEntry(entry, binding) || key !== entryKey(binding, entry.descriptor.client_write_uuid)) return fail('invalid');
    } catch { return fail('invalid'); }
    raws.set(key, raw.value);
  }
  const again = deletionFamilyKeys(binding, fenceRaw, null); if (!again.ok) return again;
  if (g3Canonical(keys.value) !== g3Canonical(again.value)) return fail('changed');
  return success(raws);
}
/** Only call after native DELETE succeeds for this captured case, before Store's stale-generation return. */
export function acknowledgeAdmissionsCaseDeletion(
  binding: G3RecoveryBinding, acknowledgedProfileId: string,
): G3DeleteCleanupV1 {
  if (acknowledgedProfileId !== binding.profile_id) return { tombstoned: false, cleanup: 'residual_unknown', reason: 'ack' };
  const captured: G3RecoveryBinding = { owner_binding: binding.owner_binding, profile_id: binding.profile_id,
    case_epoch: binding.case_epoch, generation: binding.generation, family: binding.family, current: binding.current };
  const check = deletionFenceFailure(captured);
  if (check) return { tombstoned: false, cleanup: 'residual_unknown', reason: check };
  let nextGeneration: string;
  try { nextGeneration = crypto.randomUUID(); } catch { return { tombstoned: false, cleanup: 'residual_unknown', reason: 'digest' }; }
  const tombstone: G3FamilyFenceV1 = { schema_version: 'g3-case-family-fence-v1', owner_binding: captured.owner_binding,
    profile_id: captured.profile_id, generation: nextGeneration, deleted: true };
  let tombstoned = false;
  try {
    const beforeFenceRead = deletionFenceFailure(captured);
    if (beforeFenceRead) return { tombstoned, cleanup: 'residual_unknown', reason: beforeFenceRead };
    const fenceRaw = window.localStorage.getItem(fenceKey(captured));
    const afterFenceRead = deletionFenceFailure(captured, fenceRaw ?? undefined);
    if (afterFenceRead || fenceRaw === null) return { tombstoned, cleanup: 'residual_unknown', reason: afterFenceRead ?? 'generation' };
    const candidates = deletionCandidates(captured, fenceRaw);
    const beforeWrite = deletionFenceFailure(captured, fenceRaw);
    if (beforeWrite) return { tombstoned, cleanup: 'residual_unknown', reason: beforeWrite };
    const raw = JSON.stringify(tombstone);
    // Separate immutable tombstone cannot be overwritten by a late initial alive-fence write.
    window.localStorage.setItem(tombstoneKey(captured), raw);
    const afterWrite = deletionFenceFailure(captured, fenceRaw, raw);
    if (afterWrite) return { tombstoned, cleanup: 'residual_unknown', reason: afterWrite };
    tombstoned = true;
    if (!candidates.ok) return { tombstoned, cleanup: 'residual_unknown', reason: candidates.reason };
    for (const [key, expectedRaw] of candidates.value) {
      const current = deletionReadRaw(captured, key, fenceRaw, raw);
      if (!current.ok) return { tombstoned, cleanup: 'residual_unknown', reason: current.reason };
      if (current.value !== expectedRaw) return { tombstoned, cleanup: 'residual_unknown', reason: 'changed' };
      const beforeRemove = deletionFenceFailure(captured, fenceRaw, raw);
      if (beforeRemove) return { tombstoned, cleanup: 'residual_unknown', reason: beforeRemove };
      window.localStorage.removeItem(key);
      const afterRemove = deletionReadRaw(captured, key, fenceRaw, raw);
      if (!afterRemove.ok) return { tombstoned, cleanup: 'residual_unknown', reason: afterRemove.reason };
      if (afterRemove.value !== null) return { tombstoned, cleanup: 'residual_unknown', reason: 'changed' };
    }
    const finalKeys = deletionFamilyKeys(captured, fenceRaw, raw);
    if (!finalKeys.ok) return { tombstoned, cleanup: 'residual_unknown', reason: finalKeys.reason };
    const finalIndex = deletionReadRaw(captured, indexKey(captured), fenceRaw, raw);
    if (!finalIndex.ok) return { tombstoned, cleanup: 'residual_unknown', reason: finalIndex.reason };
    const residual = finalKeys.value.length > 0 || finalIndex.value !== null;
    return { tombstoned, cleanup: residual ? 'residual_unknown' : 'completed_best_effort', reason: residual ? 'changed' : null };
  } catch { return { tombstoned, cleanup: 'residual_unknown', reason: 'storage' }; }
}

export interface G3LegacyBrowserCandidateV1 {
  legacy_key_digest: string; legacy_value: true; source_version: 'unknown'; original_reported_at: null;
}
export interface G3LegacyBrowserSnapshotV1 {
  legacy_snapshot_digest: string; candidates: G3LegacyBrowserCandidateV1[];
}
/** Literal true candidates only. The caller explicitly chooses/matches own task IDs; no names or source versions are inferred. */
export async function readAdmissionsLegacyCandidates(
  binding: G3RecoveryBinding,
): Promise<G3RecoveryResult<G3LegacyBrowserSnapshotV1>> {
  const checked = active(binding); if (!checked.ok) return checked;
  const key = binding.owner_binding === 'demo' ? 'ashyq.docsDone'
    : `ashyq.owner.${encodeURIComponent(binding.owner_binding)}.ashyq.docsDone`;
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(key);
    const after = active(binding); if (!after.ok) return after;
    if (raw !== null && bytes(raw) > G3_RECOVERY_ENTRY_BYTES) return fail('oversize');
    const marks = raw === null ? {} : parse(raw);
    if (!object(marks) || Object.keys(marks).length > 4000 || Object.keys(marks).some(item => !exact(item, 1000))) return fail('invalid');
    const chosen = Object.entries(marks).filter(([, value]) => value === true);
    // No truncation or invented historical attribution. Large sets need an explicit smaller reviewed selection.
    if (chosen.length > 50) return fail('limit');
    const snapshotDigest = await hash({ schema_version: 'g3-legacy-browser-mark-snapshot-v1', raw });
    const candidates: G3LegacyBrowserCandidateV1[] = [];
    for (const [legacyKey] of chosen) {
      candidates.push({ legacy_key_digest: await hash({ schema_version: 'g3-legacy-browser-mark-key-v1', key: legacyKey }),
        legacy_value: true, source_version: 'unknown', original_reported_at: null });
      const current = active(binding); if (!current.ok) return current;
    }
    const final = active(binding); if (!final.ok) return final;
    if (window.localStorage.getItem(key) !== raw) return fail('changed');
    const last = active(binding); if (!last.ok) return last;
    return success({ legacy_snapshot_digest: snapshotDigest, candidates });
  } catch { return fail('storage'); }
}

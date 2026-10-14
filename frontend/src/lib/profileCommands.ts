/** Small per-tab, owner-bound original profile intents. No G3 protocol changes. */
import { applicantStorageKey, checkApplicantOwner, currentApplicantOwner } from './applicantStorage';
import type { ProfileCommandHeaders, StoredProfile } from '@/types';
export const PROFILE_COMMAND_LIMIT = 16;
export type ProfileCommandStatus = 'pending' | 'unknown' | 'conflict' | 'accepted' | 'failed' | 'reviewed';
export interface ProfileCommand {
  v: 1; owner: string | null; case_key: string; command: ProfileCommandHeaders;
  kind: 'create' | 'update' | 'persisted_rerank'; run_id?: string;
  body: Record<string, unknown>; draft: Record<string, unknown>; base: StoredProfile | null;
  status: ProfileCommandStatus;
  accepted_profile_id?: string;
  reviewed_conflict?: boolean;
  latest_draft?: Record<string, unknown>;
  reconciliation_required?: boolean;
}
function key(owner: string | null): string {
  checkApplicantOwner(owner);
  const result = applicantStorageKey('ashyq.draft.profileCommands.v1');
  if (result === null) throw new Error('Profile recovery storage is unavailable. Nothing was sent.');
  return result;
}
function object(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export function readProfileCommands(owner = currentApplicantOwner()): ProfileCommand[] {
  const raw = sessionStorage.getItem(key(owner));
  if (raw === null) return [];
  const parsed: unknown = JSON.parse(raw);
  if (!Array.isArray(parsed) || parsed.length > PROFILE_COMMAND_LIMIT) throw new Error('Profile recovery storage is corrupt. Export or clear it explicitly before saving.');
  const ids = new Set<string>();
  for (const item of parsed) {
    if (!object(item) || item.v !== 1 || item.owner !== owner || typeof item.case_key !== 'string'
      || !object(item.command) || typeof item.command.command_id !== 'string' || !uuid.test(item.command.command_id)
      || ids.has(item.command.command_id) || !object(item.body) || !object(item.draft)
      || !['create', 'update', 'persisted_rerank'].includes(String(item.kind))
      || !['pending', 'unknown', 'conflict', 'accepted', 'failed', 'reviewed'].includes(String(item.status))) throw new Error('Profile recovery storage is corrupt. Original data was retained.');
    if (item.latest_draft !== undefined && !object(item.latest_draft)) throw new Error('Latest profile draft is invalid. Original data was retained.');
    if (item.reconciliation_required !== undefined && typeof item.reconciliation_required !== 'boolean') throw new Error('Profile reconciliation state is invalid.');
    const cmd = item.command;
    if (item.kind === 'create' ? typeof cmd.creation_identity !== 'string' || !uuid.test(cmd.creation_identity)
      || item.base !== null : !object(item.base) || !Number.isInteger(cmd.expected_revision)
      || Number(cmd.expected_revision) < 1 || item.base.revision !== cmd.expected_revision
      || item.base.id !== item.case_key) throw new Error('Profile recovery identity is invalid. Nothing was sent.');
    if (item.kind === 'persisted_rerank' && typeof item.run_id !== 'string') throw new Error('Profile recovery target is invalid.');
    ids.add(cmd.command_id as string);
  }
  return parsed as ProfileCommand[];
}
export function unresolvedProfileCommand(item: ProfileCommand): boolean {
  return ['pending','unknown'].includes(item.status) || item.status === 'conflict' && !item.reviewed_conflict || item.status === 'accepted' && item.reconciliation_required === true;
}
export function serializeProfileCommands(owner = currentApplicantOwner()): string {
  return sessionStorage.getItem(key(owner)) ?? '[]'; // exact own bytes, including corrupt originals
}
function write(owner: string | null, entries: ProfileCommand[]): void {
  const slot = key(owner); const raw = JSON.stringify(entries);
  sessionStorage.setItem(slot, raw);
  checkApplicantOwner(owner);
  if (sessionStorage.getItem(slot) !== raw) throw new Error('Profile recovery could not be stored. Nothing was sent.');
}
export function saveProfileCommand(entry: ProfileCommand): void {
  const entries = readProfileCommands(entry.owner);
  const at = entries.findIndex(item => item.command.command_id === entry.command.command_id);
  if (at === -1) {
    if (entries.length >= PROFILE_COMMAND_LIMIT) throw new Error('Profile recovery is full. Clear confirmed entries before saving. Unresolved commands were kept.');
    if (entries.some(item => item.case_key === entry.case_key && unresolvedProfileCommand(item))) throw new Error('Resolve the original profile command before sending another.');
    entries.push(entry);
  } else {
    const before = entries[at];
    if (!before) throw new Error('Original profile command was not found. Nothing was sent.');
    if (before.accepted_profile_id && entry.accepted_profile_id && before.accepted_profile_id !== entry.accepted_profile_id) throw new Error('Accepted profile identity cannot change.');
    const original = (item: ProfileCommand) => {
      const value = { ...item } as Record<string, unknown>;
      for (const key of ['status','accepted_profile_id','reviewed_conflict','latest_draft','reconciliation_required']) delete value[key];
      return JSON.stringify(value);
    };
    if (original(before) !== original(entry)) throw new Error('Original profile command cannot change.');
    entries[at] = { ...before, ...entry,
      ...(before.latest_draft && !entry.latest_draft ? { latest_draft:before.latest_draft } : {}),
      ...(before.accepted_profile_id && !entry.accepted_profile_id ? { accepted_profile_id:before.accepted_profile_id } : {}) };
  }
  write(entry.owner, entries);
}
export function clearConfirmedProfileCommands(owner = currentApplicantOwner()): void {
  // Reviewed conflicts keep their original status history until explicit cleanup.
  write(owner, readProfileCommands(owner).filter(item => unresolvedProfileCommand(item) || !['accepted','reviewed','failed','conflict'].includes(item.status)));
}
export function forgetProfileCommands(caseKey: string, owner = currentApplicantOwner()): void {
  write(owner, readProfileCommands(owner).filter(item => item.case_key !== caseKey && item.accepted_profile_id !== caseKey));
}

export function rememberProfileDraft(caseKey: string, owner: string | null, draft: Record<string,unknown>): void {
  const entry = readProfileCommands(owner).find(item => (item.case_key === caseKey || item.accepted_profile_id === caseKey) && unresolvedProfileCommand(item));
  if (entry) saveProfileCommand({ ...entry, latest_draft:structuredClone(draft) });
}

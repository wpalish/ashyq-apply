/**
 * Per-case draft persistence and per-tab case pointers (T09 / FE01-FE03).
 *
 * Unsaved edits live in one envelope per case: `{ v, case_key, saved_at,
 * base_updated_at?, draft }`, stored under that case's own localStorage slot.
 * A shared global draft slot let two tabs overwrite each other's edits and let
 * one case's draft be layered onto another case after a reload; per-case slots
 * prevent those collisions, and an envelope is applied only when its
 * case_key names the case being hydrated.
 *
 * The active-case and active-run pointers are per-tab sessionStorage: a reload
 * reopens the case THIS tab was working on, while a new tab no longer resurrects
 * whatever case some other tab had open last (accepted behavior change). The
 * authenticated tree scopes both pointers and draft slots to its verified user
 * and organization. It never adopts older unowned browser data. Legacy callers
 * without a scope use the owner-checking adapter and retain the pre-T09
 * migration contract for explicit anonymous demo recovery tooling and fixtures;
 * they must not mount authenticated product state.
 */

import { applicantStorageKey, currentApplicantOwner } from '@/lib/applicantStorage';

/** Keys were `unimatch.*` before the product was named. */
export function legacyKey(key: string): string {
  return key.replace(/^ashyq\./, 'unimatch.');
}

export const ACTIVE_PROFILE_KEY = 'ashyq.activeProfile';
export const ACTIVE_RUN_KEY = 'ashyq.activeRun';

const DRAFT_SLOT_PREFIX = 'ashyq.draft.';
const LEGACY_DRAFT_KEY = 'ashyq.unsavedDraft';
const LOCAL_CASE_PREFIX = 'local:';

// Scope is a value passed by the owning React tree, never a shared current user.
// null means identity is unavailable, so browser persistence must fail closed.
export type DraftScope = string | null | undefined;
function ownedKey(key: string, scope: DraftScope): string | null {
  // Undefined is used only by explicitly anonymous demo/recovery callers.
  // The primary adapter still blocks stale tabs and scopes bound auth callers.
  if (scope === undefined) return applicantStorageKey(key);
  if (scope === null) return null;
  const expectedOwner = `auth:${scope}`;
  try {
    // Derive the key from the owning tree, then validate the live browser binding.
    // Never select a different account's namespace from a mutable global owner.
    if (currentApplicantOwner() !== expectedOwner) return null;
    return `ashyq.owner.${encodeURIComponent(expectedOwner)}.${key}`;
  } catch {
    return null;
  }
}

export interface DraftEnvelope {
  v: 1;
  case_key: string;
  saved_at: string;
  /** The server profile `updated_at` the draft was made against, when known. */
  base_updated_at?: string;
  base_revision?: number;
  base_draft?: Record<string, unknown>;
  draft: Record<string, unknown>;
}

/** A case that exists only in this browser until its first save. */
export function isLocalCaseKey(caseKey: string): boolean {
  return caseKey.startsWith(LOCAL_CASE_PREFIX);
}

export function newLocalCaseKey(): string {
  return `${LOCAL_CASE_PREFIX}${crypto.randomUUID()}`;
}

function readLocal(key: string, scope?: DraftScope): string | null {
  try {
    const owned = ownedKey(key, scope);
    return owned === null ? null : window.localStorage.getItem(owned);
  } catch {
    return null; // storage unavailable — never fatal
  }
}

function removeLocal(key: string, scope?: DraftScope): void {
  try {
    const owned = ownedKey(key, scope);
    if (owned !== null) window.localStorage.removeItem(owned);
  } catch {
    /* storage unavailable */
  }
}

function readSession(key: string, scope?: DraftScope): string | null {
  try {
    const owned = ownedKey(key, scope);
    return owned === null ? null : window.sessionStorage.getItem(owned);
  } catch {
    return null;
  }
}

function writeSession(key: string, value: string | null, scope?: DraftScope): void {
  try {
    const owned = ownedKey(key, scope);
    if (owned === null) return;
    if (value === null) window.sessionStorage.removeItem(owned);
    else window.sessionStorage.setItem(owned, value);
  } catch {
    /* per-tab state is best-effort */
  }
}

/**
 * Read the per-tab pointer, adopting a pre-T09 global localStorage pointer
 * (under either key name) once. The global keys are removed even when this tab
 * already has its own pointer: a leftover global pointer would otherwise leak
 * this case into the next tab that opens the app.
 */
export function adoptPointer(kind: 'profile' | 'run', scope?: DraftScope): string | null {
  if (scope === null) return null;
  const key = kind === 'profile' ? ACTIVE_PROFILE_KEY : ACTIVE_RUN_KEY;
  // Authenticated users can adopt only pointers already attributed to them.
  // Legacy unowned pointers/drafts cannot safely be assigned to the next login.
  if (scope !== undefined) return readSession(key, scope);
  let inherited: string | null = null;
  try {
    inherited = readLocal(key) ?? readLocal(legacyKey(key));
  } catch {
    inherited = null;
  }
  if (inherited !== null) {
    removeLocal(key);
    removeLocal(legacyKey(key));
  }
  const current = readSession(key);
  if (current !== null) return current;
  if (inherited === null) return null;
  writeSession(key, inherited);
  return inherited;
}

/** Pointers are written per-tab only; nothing global is ever (re)introduced. */
export function writePointer(kind: 'profile' | 'run', id: string | null, scope?: DraftScope): void {
  if (scope === null) return;
  writeSession(kind === 'profile' ? ACTIVE_PROFILE_KEY : ACTIVE_RUN_KEY, id, scope);
}

function slotKey(caseKey: string): string {
  return `${DRAFT_SLOT_PREFIX}${caseKey}`;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Validate an envelope of unknown provenance. An unknown schema version or a
 * malformed payload is rejected rather than silently cast into the draft shape.
 */
function parseEnvelope(parsed: unknown): DraftEnvelope | null {
  if (!isPlainObject(parsed)) return null;
  const { v, case_key, saved_at, base_updated_at, base_revision, base_draft, draft } = parsed;
  if (v !== 1) return null;
  if (typeof case_key !== 'string' || case_key === '') return null;
  if (typeof saved_at !== 'string') return null;
  if (base_updated_at !== undefined && typeof base_updated_at !== 'string') return null;
  if (!isPlainObject(draft)) return null;
  const envelope: DraftEnvelope = { v: 1, case_key, saved_at, draft };
  if (typeof base_updated_at === 'string') envelope.base_updated_at = base_updated_at;
  if (Number.isInteger(base_revision) && Number(base_revision) >= 1 && isPlainObject(base_draft)) {
    envelope.base_revision = Number(base_revision); envelope.base_draft = base_draft;
  }
  return envelope;
}

/**
 * Read the draft slot of one case. A corrupt or unsupported slot is removed so
 * the unreadable payload cannot resurface on every reload; an envelope that
 * names a DIFFERENT case is left alone — it is not this case's data to destroy.
 */
export function readDraftEnvelope(caseKey: string, scope?: DraftScope): DraftEnvelope | null {
  if (scope === null) return null;
  const key = slotKey(caseKey);
  const raw = readLocal(key, scope);
  if (raw === null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    removeLocal(key, scope);
    return null;
  }
  const envelope = parseEnvelope(parsed);
  if (envelope === null) {
    removeLocal(key, scope);
    return null;
  }
  if (envelope.case_key !== caseKey) return null;
  return envelope;
}

export function writeDraftEnvelope(
  caseKey: string,
  draft: Record<string, unknown>,
  baseUpdatedAt?: string | null,
  scope?: DraftScope,
  base?: { revision: number; draft: Record<string, unknown> },
): void {
  if (scope === null) return;
  const envelope: DraftEnvelope = {
    v: 1,
    case_key: caseKey,
    saved_at: new Date().toISOString(),
    draft,
  };
  if (baseUpdatedAt) envelope.base_updated_at = baseUpdatedAt;
  if (base) { envelope.base_revision = base.revision; envelope.base_draft = base.draft; }
  try {
    const owned = ownedKey(slotKey(caseKey), scope);
    if (owned !== null) window.localStorage.setItem(owned, JSON.stringify(envelope));
  } catch {
    /* storage unavailable — the draft still lives in memory this session */
  }
}

export function clearDraftSlot(caseKey: string, scope?: DraftScope): void {
  if (scope === null) return;
  removeLocal(slotKey(caseKey), scope);
}

/**
 * The pre-T09 build kept a bare draft (no envelope) under one global key. It is
 * re-wrapped under the case that was active when it was written; the legacy
 * keys are removed either way, so the migration runs exactly once. Without a
 * case to attribute it to it stays what it effectively was before: unrestorable
 * data, now dropped instead of left behind.
 */
export function migrateLegacyDraft(caseKey: string | null, scope?: DraftScope): void {
  // The security binding erases unowned data before authenticated hydration.
  // Explicit identities never adopt legacy slots; anonymous recovery stays below.
  if (scope !== undefined) return;
  const raw = readLocal(LEGACY_DRAFT_KEY) ?? readLocal(legacyKey(LEGACY_DRAFT_KEY));
  if (raw === null) return;
  removeLocal(LEGACY_DRAFT_KEY);
  removeLocal(legacyKey(LEGACY_DRAFT_KEY));
  if (caseKey === null) return;
  if (readLocal(slotKey(caseKey)) !== null) return; // a per-case slot wins
  try {
    const draft: unknown = JSON.parse(raw);
    if (isPlainObject(draft)) writeDraftEnvelope(caseKey, draft);
  } catch {
    /* unreadable legacy draft: dropped with its key */
  }
}

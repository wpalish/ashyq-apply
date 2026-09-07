/**
 * Per-case draft persistence and per-tab case pointers (T09 / FE01-FE03).
 *
 * Unsaved edits live in one envelope per case: `{ v, case_key, saved_at,
 * base_updated_at?, draft }`, stored under that case's own localStorage slot.
 * A shared global draft slot let two tabs overwrite each other's edits and let
 * one case's draft be layered onto another case after a reload; per-case slots
 * make both structurally impossible, and an envelope is applied only when its
 * case_key names the case being hydrated.
 *
 * The active-case and active-run pointers are per-tab sessionStorage: a reload
 * reopens the case THIS tab was working on, while a new tab no longer resurrects
 * whatever case some other tab had open last (accepted behavior change). The
 * pre-T09 global localStorage pointers are adopted into this tab once, then
 * removed, so an old build's pointer is not lost across the upgrade.
 */

/** Keys were `unimatch.*` before the product was named. */
export function legacyKey(key: string): string {
  return key.replace(/^ashyq\./, 'unimatch.');
}

export const ACTIVE_PROFILE_KEY = 'ashyq.activeProfile';
export const ACTIVE_RUN_KEY = 'ashyq.activeRun';

const DRAFT_SLOT_PREFIX = 'ashyq.draft.';
const LEGACY_DRAFT_KEY = 'ashyq.unsavedDraft';
const LOCAL_CASE_PREFIX = 'local:';

export interface DraftEnvelope {
  v: 1;
  case_key: string;
  saved_at: string;
  /** The server profile `updated_at` the draft was made against, when known. */
  base_updated_at?: string;
  draft: Record<string, unknown>;
}

/** A case that exists only in this browser until its first save. */
export function isLocalCaseKey(caseKey: string): boolean {
  return caseKey.startsWith(LOCAL_CASE_PREFIX);
}

export function newLocalCaseKey(): string {
  return `${LOCAL_CASE_PREFIX}${crypto.randomUUID()}`;
}

function readLocal(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null; // storage unavailable — never fatal
  }
}

function removeLocal(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* storage unavailable */
  }
}

function readSession(key: string): string | null {
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeSession(key: string, value: string | null): void {
  try {
    if (value === null) window.sessionStorage.removeItem(key);
    else window.sessionStorage.setItem(key, value);
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
export function adoptPointer(kind: 'profile' | 'run'): string | null {
  const key = kind === 'profile' ? ACTIVE_PROFILE_KEY : ACTIVE_RUN_KEY;
  let inherited: string | null = null;
  try {
    inherited = window.localStorage.getItem(key) ?? window.localStorage.getItem(legacyKey(key));
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
export function writePointer(kind: 'profile' | 'run', id: string | null): void {
  writeSession(kind === 'profile' ? ACTIVE_PROFILE_KEY : ACTIVE_RUN_KEY, id);
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
  const { v, case_key, saved_at, base_updated_at, draft } = parsed;
  if (v !== 1) return null;
  if (typeof case_key !== 'string' || case_key === '') return null;
  if (typeof saved_at !== 'string') return null;
  if (base_updated_at !== undefined && typeof base_updated_at !== 'string') return null;
  if (!isPlainObject(draft)) return null;
  const envelope: DraftEnvelope = { v: 1, case_key, saved_at, draft };
  if (typeof base_updated_at === 'string') envelope.base_updated_at = base_updated_at;
  return envelope;
}

/**
 * Read the draft slot of one case. A corrupt or unsupported slot is removed so
 * the unreadable payload cannot resurface on every reload; an envelope that
 * names a DIFFERENT case is left alone — it is not this case's data to destroy.
 */
export function readDraftEnvelope(caseKey: string): DraftEnvelope | null {
  const key = slotKey(caseKey);
  const raw = readLocal(key);
  if (raw === null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    removeLocal(key);
    return null;
  }
  const envelope = parseEnvelope(parsed);
  if (envelope === null) {
    removeLocal(key);
    return null;
  }
  if (envelope.case_key !== caseKey) return null;
  return envelope;
}

export function writeDraftEnvelope(
  caseKey: string,
  draft: Record<string, unknown>,
  baseUpdatedAt?: string | null,
): void {
  const envelope: DraftEnvelope = {
    v: 1,
    case_key: caseKey,
    saved_at: new Date().toISOString(),
    draft,
  };
  if (baseUpdatedAt) envelope.base_updated_at = baseUpdatedAt;
  try {
    window.localStorage.setItem(slotKey(caseKey), JSON.stringify(envelope));
  } catch {
    /* storage unavailable — the draft still lives in memory this session */
  }
}

export function clearDraftSlot(caseKey: string): void {
  removeLocal(slotKey(caseKey));
}

/**
 * The pre-T09 build kept a bare draft (no envelope) under one global key. It is
 * re-wrapped under the case that was active when it was written; the legacy
 * keys are removed either way, so the migration runs exactly once. Without a
 * case to attribute it to it stays what it effectively was before: unrestorable
 * data, now dropped instead of left behind.
 */
export function migrateLegacyDraft(caseKey: string | null): void {
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

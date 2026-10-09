/** Origin storage holds applicant data, so its owner is a server principal, not a case name. */
import type { AuthStatus } from '@/types';

export const APPLICANT_OWNER_KEY = 'ashyq.applicantOwner';
const SCOPED_PREFIX = 'ashyq.owner.';
const DEMO = 'demo';
const SIGNED_OUT = 'signed-out';

function isApplicantKey(key: string): boolean {
  return key.startsWith(SCOPED_PREFIX) || key.startsWith('ashyq.draft.')
    || key.startsWith('unimatch.draft.')
    || /^(?:ashyq|unimatch)\.(?:activeProfile|activeRun|unsavedDraft|docsDone)$/.test(key);
}

/** Remove applicant data only; appearance and unrelated origin storage are not ours. */
function removeApplicantData(): void {
  for (const storage of [window.localStorage, window.sessionStorage]) {
    const keys = Array.from({ length: storage.length }, (_, i) => storage.key(i));
    for (const key of keys) if (key && isApplicantKey(key)) storage.removeItem(key);
  }
}

export function bindApplicantOwner(status: AuthStatus): string {
  let owner = DEMO;
  if (status.enabled) {
    owner = SIGNED_OUT;
    if (status.authenticated) {
      const principal = status.principal;
      if (!principal?.user_id || !principal.organization_id || principal.local_development) {
        throw new Error('The server did not identify this workspace. Sign in again.');
      }
      owner = `auth:${JSON.stringify([principal.user_id, principal.organization_id])}`;
    }
  }
  // Fail closed if storage cannot be inspected/cleared: do not hydrate an unknown owner's draft.
  if (window.localStorage.getItem(APPLICANT_OWNER_KEY) !== owner) removeApplicantData();
  window.localStorage.setItem(APPLICANT_OWNER_KEY, owner);
  window.sessionStorage.setItem(APPLICANT_OWNER_KEY, owner);
  return owner;
}

/** Null means stale/signed-out: no applicant browser read or write is permitted. */
export function applicantStorageKey(key: string): string | null {
  try {
    const current = window.localStorage.getItem(APPLICANT_OWNER_KEY);
    const tab = window.sessionStorage.getItem(APPLICANT_OWNER_KEY);
    // Existing direct anonymous/demo controls have no authenticated binding.
    if (current === null && tab === null) return key;
    if (tab !== current || !tab || tab === SIGNED_OUT || tab.startsWith('transition:')) return null;
    return tab === DEMO ? key : `${SCOPED_PREFIX}${encodeURIComponent(tab)}.${key}`;
  } catch {
    return null;
  }
}

/** Capture/check around async I/O. A stale tab must not use another person's shared cookie. */
export function currentApplicantOwner(): string | null {
  const current = window.localStorage.getItem(APPLICANT_OWNER_KEY);
  const tab = window.sessionStorage.getItem(APPLICANT_OWNER_KEY);
  if (current === null && tab === null) return null;
  if (tab !== current || !tab || tab === SIGNED_OUT || tab.startsWith('transition:')) {
    throw new Error('The signed-in workspace changed. Reload to continue.');
  }
  return tab;
}

export function checkApplicantOwner(expected: string | null): void {
  if (currentApplicantOwner() !== expected) {
    throw new Error('The signed-in workspace changed. Reload to continue.');
  }
}

/** Lock other tabs before an auth call may replace the shared session cookie. */
export function beginApplicantTransition(): { check: () => void; restore: () => void } {
  const previous = window.localStorage.getItem(APPLICANT_OWNER_KEY);
  const pending = `transition:${crypto.randomUUID()}`;
  window.localStorage.setItem(APPLICANT_OWNER_KEY, pending);
  return { check: () => {
    if (window.localStorage.getItem(APPLICANT_OWNER_KEY) !== pending) {
      throw new Error('The signed-in workspace changed. Reload to continue.');
    }
  }, restore: () => {
    // A failed older request cannot overwrite a newer person's binding.
    if (window.localStorage.getItem(APPLICANT_OWNER_KEY) !== pending) return;
    if (previous === null) window.localStorage.removeItem(APPLICANT_OWNER_KEY);
    else window.localStorage.setItem(APPLICANT_OWNER_KEY, previous);
  } };
}

export function forgetApplicantBrowserData(): void {
  removeApplicantData();
  window.localStorage.setItem(APPLICANT_OWNER_KEY, SIGNED_OUT);
  window.sessionStorage.setItem(APPLICANT_OWNER_KEY, SIGNED_OUT);
}

/** A case deletion retires marks for its returned result ids, not another case's checklist. */
export function forgetDocumentMarks(resultIds: string[]): void {
  const key = applicantStorageKey('ashyq.docsDone');
  if (key === null) return;
  try {
    const marks: unknown = JSON.parse(window.localStorage.getItem(key) ?? '{}');
    if (!marks || typeof marks !== 'object' || Array.isArray(marks)) return;
    const kept = Object.fromEntries(Object.entries(marks).filter(([item]) =>
      !resultIds.some((id) => item.startsWith(`${id}::`))));
    window.localStorage.setItem(key, JSON.stringify(kept));
  } catch { /* unusable optional marks cannot block an acknowledged case deletion */ }
}

/** Non-private search preferences, held for one hour in this tab only.
 * Applying them to an applicant draft always requires an explicit action. */
export type PublicSearchIntent = { subject: string; country: string; budget: number | null };
const KEY = 'unimatch.public-search-intent';
export function savePublicSearchIntent(value: PublicSearchIntent): void {
  if (!value.subject.trim() || value.subject.length > 120 || value.country.length > 120
    || !(value.budget === null || (Number.isFinite(value.budget) && value.budget >= 0 && value.budget <= 1000000))) return;
  try { sessionStorage.setItem(KEY, JSON.stringify({ ...value, expires: Date.now() + 3600000 })); } catch { /* Search can still start from a blank profile. */ }
}
export function readPublicSearchIntent(): PublicSearchIntent | null {
  try {
    const raw = sessionStorage.getItem(KEY); if (!raw || raw.length > 2000) return null;
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== 'object') return null;
    const v = value as Record<string, unknown>;
    if (typeof v.expires !== 'number' || v.expires < Date.now() || typeof v.subject !== 'string' || !v.subject.trim() || v.subject.length > 120 || typeof v.country !== 'string' || v.country.length > 120 || !(v.budget === null || (typeof v.budget === 'number' && Number.isFinite(v.budget) && v.budget >= 0 && v.budget <= 1000000))) return null;
    return { subject: v.subject, country: v.country, budget: v.budget };
  } catch { return null; }
}
export function clearPublicSearchIntent(): void { try { sessionStorage.removeItem(KEY); } catch { /* Non-essential tab storage. */ } }

/**
 * Rendering the sentences the backend wrote, in the reader's language (gap B6).
 *
 * The API serves each sentence in English with a `MessageRef` beside it (a
 * stable key and its parameters; `backend/app/domain/message_keys.py`). Here
 * the key is looked up under `msg.<key>` and its parameters filled in. The
 * served English is the answer whenever anything is missing — no key, no
 * translation, an English reader — so a sentence is never shown in a form the
 * English does not back.
 */

import { fill, getLocale, t, tf, tn, translated, tOr } from '@/lib/i18n';
import { caveatText, staleChip, staleReason } from '@/lib/format';
import type { ClaimOut, MessageRef } from '@/types';

/** Parameters that are lists of cost categories, translated item by item. */
const CATEGORY_PARAMS = new Set(['categories', 'category']);

function param(ref: MessageRef, name: string): string | undefined {
  const parts = ref.parts?.[name];
  if (parts && parts.length > 0 && parts.every((p) => p && translated(`msg.${p.key}`))) {
    return parts.map((p) => localize(p, '')).join('; ');
  }
  const value = ref.params[name];
  if (value !== undefined && CATEGORY_PARAMS.has(name)) {
    return value
      .split(', ')
      .map((c) => tOr(`cost.${c.replace(/ /g, '_')}`, c).toLocaleLowerCase())
      .join(', ');
  }
  return value;
}

/** The sentence in the current locale, or `english` when it cannot be. */
export function localize(ref: MessageRef | null | undefined, english: string): string {
  if (!ref || getLocale() === 'en') return english;
  const template = translated(`msg.${ref.key}`);
  if (template === undefined) return english;
  const names = Array.from(template.matchAll(/\{(\w+)\}/g), (m) => m[1] ?? '');
  const params: Record<string, string> = {};
  for (const name of names) {
    const value = param(ref, name);
    if (value === undefined) return english;
    params[name] = value;
  }
  return fill(template, params);
}

/**
 * Why a claim is stale, in the current locale: each "; "-separated reason is
 * localised on its own, and one the backend gave no key keeps its English.
 */
export function localStaleReason(claim: Pick<ClaimOut, 'notes' | 'stale_messages'>): string | null {
  const english = staleReason(claim.notes);
  if (english === null) return null;
  const keyed = claim.stale_messages;
  if (!keyed || getLocale() === 'en') return english;
  const pieces = english.split('; ');
  if (pieces.length !== keyed.length) return english;
  return pieces.map((piece, i) => localize(keyed[i], piece)).join('; ');
}

/** A current KB fact's caveat, in the current locale; null when it has none. */
export function localCaveat(claim: Pick<ClaimOut, 'notes' | 'caveat_message'>): string | null {
  const english = caveatText(claim.notes);
  if (english === null) return null;
  return localize(claim.caveat_message, english);
}

/** format.ts's age chip ("12d old", "not current") in the current locale. */
export function localStaleChip(ageDays: number): string {
  if (getLocale() === 'en') return staleChip(ageDays);
  return ageDays > 0 ? tf('results.staleAge', { days: ageDays }) : t('results.staleNoAge');
}

/**
 * A step of the suggested order as the backend wrote it ("You: Portfolio
 * (allow ~30 days)"), with its lead time in the reader's language and plural.
 * The English said "allow ~1 days" for a one-day lead time (KB v10 smoke D4)
 * and a saved checklist keeps that text, so the count is read and said again.
 */
export function localStep(step: string): string {
  return step.replace(/\(allow ~(\d+) days?\)/, (_whole, n: string) =>
    `(${tn('detail.docs.leadTime', Number(n))})`);
}

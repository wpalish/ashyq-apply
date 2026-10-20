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

import { fill, getLocale, t, tf, tn, translated, tOr, type MessageKey } from '@/lib/i18n';
import { caveatText, staleChip, staleReason, unusedTuition, unusedTuitionLines } from '@/lib/format';
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

/**
 * format.ts's age chip ("12d old", "not current") in the current locale.
 * `reasoned`: the claim says why it is not current, so its age is not the point.
 */
export function localStaleChip(ageDays: number, reasoned = false): string {
  if (getLocale() === 'en') return staleChip(ageDays, reasoned);
  return ageDays > 0 && !reasoned ? tf('results.staleAge', { days: ageDays }) : t('results.staleNoAge');
}

/** Who acts on a step, as `web_documents._order_steps` writes it. */
const STEP_OWNERS: Record<string, MessageKey> = {
  'You': 'detail.docs.step.applicant',
  'Your school': 'detail.docs.step.school',
  'Your referee': 'detail.docs.step.recommender',
  'A third party': 'detail.docs.step.third_party',
};

/**
 * A step of the suggested order as the backend wrote it ("You: Portfolio
 * (allow ~30 days) — after Offer letter"), with who acts on it, its lead time
 * (in the reader's plural) and its prerequisite said in the reader's language.
 * The English said "allow ~1 days" for a one-day lead time (KB v10 smoke D4)
 * and a saved checklist keeps that text, so the count is read and said again.
 * The owner stayed English in ru and kk ("Your referee: …", KB v18 smoke U5).
 */
export function localStep(step: string): string {
  const owner = /^(You|Your school|Your referee|A third party): /.exec(step);
  const rest = owner ? step.slice(owner[0].length) : step;
  const said = rest
    .replace(/\(allow ~(\d+) days?\)/, (_whole, n: string) => `(${tn('detail.docs.leadTime', Number(n))})`)
    .replace(/ — after (.+)$/, (_whole, what: string) => ` — ${tf('detail.docs.after', { what })}`);
  const key = owner ? STEP_OWNERS[owner[1] ?? ''] : undefined;
  return key ? `${t(key)}: ${said}` : said;
}

/** A fee period as published, said in the reader's language when it is a known one. */
function localPeriod(period: string): string {
  if (period === 'semester') return t('detail.fee.period.semester');
  const programme = /^full programme \((\d+) years?\)$/.exec(period);
  if (programme) return tf('detail.fee.period.programme', { n: programme[1] ?? '' });
  return period;
}

/**
 * format.ts's `unusedTuitionLines` in the current locale. In ru and kk the
 * line ("2,190 CHF per semester, no academic year stated (published per
 * semester, …)") stayed English inside a translated sentence (KB v18 smoke U4).
 */
export function localUnusedTuitionLines(claims: ClaimOut[]): string[] {
  if (getLocale() === 'en') return unusedTuitionLines(claims);
  return unusedTuition(claims).map(({ claim, amount, period, year, reason }) => {
    const money = period
      ? tf('detail.fee.perPeriod', { amount, period: localPeriod(period) })
      : tf('detail.fee.perYear', { amount });
    const when = year ? tf('detail.fee.year', { year }) : t('detail.fee.noYear');
    const why = reason
      ? tf('detail.fee.notCurrent', { reason: localStaleReason(claim) ?? reason })
      : tf('detail.fee.notYearly', { period: localPeriod(period ?? '') });
    return `${money}, ${when} (${why})`;
  });
}

/** Gap reasons whose `{fees}` are the unused-fee lines (`app.knowledge.funding.explain_unused_tuition`). */
const FEE_REASONS = new Set(['gap.feeOtherYear', 'gap.feeNotYearly']);

/** The funding gap's reason in the current locale, its listed fees included. */
export function localGapReason(
  gap: { reason: string; reason_message?: MessageRef | null },
  claims: ClaimOut[],
): string {
  const ref = gap.reason_message;
  if (!ref || getLocale() === 'en' || !FEE_REASONS.has(ref.key)) return localize(ref, gap.reason);
  const lines = localUnusedTuitionLines(claims);
  if (lines.length === 0) return localize(ref, gap.reason);
  return localize({ ...ref, params: { ...ref.params, fees: lines.join('; ') } }, gap.reason);
}

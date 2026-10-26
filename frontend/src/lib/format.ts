/**
 * Display helpers.
 *
 * Every function here has one job: never invent a value. An absent number
 * renders as an explicit phrase ("not published") rather than a dash, a zero,
 * or an empty cell that could be read as "nothing to pay".
 */

import type {
  AdmissionsFit,
  Bucket,
  ClaimStatus,
  EligibilityStatus,
  FundingClassification,
  FundingFit,
  Money,
} from '@/types';

export type Tone = 'ok' | 'info' | 'warn' | 'risk' | 'neutral' | 'demo' | 'accent';

export const NOT_PUBLISHED = 'not published';
export const NOT_FOUND = 'not found';

/**
 * One locale for money and dates alike.
 *
 * Money was formatted en-US and dates en-GB, so the same screen showed
 * "1,234 EUR" beside "05 Mar 2027" — two conventions, neither chosen by the
 * reader. The browser's own locale is the honest default; en-GB is the
 * fallback because the product's copy is British English.
 */
export const DISPLAY_LOCALE =
  typeof navigator !== 'undefined' && navigator.language ? navigator.language : 'en-GB';

export function money(value: Money | null | undefined): string {
  if (!value) return NOT_FOUND;
  const base = `${Math.round(value.amount).toLocaleString(DISPLAY_LOCALE)} ${value.currency}`;
  const range =
    value.range_low != null && value.range_high != null && value.range_low !== value.range_high
      ? ` (${Math.round(value.range_low).toLocaleString(DISPLAY_LOCALE)}–${Math.round(value.range_high).toLocaleString(DISPLAY_LOCALE)})`
      : '';
  const year = value.academic_year ? ` · ${value.academic_year}` : '';
  const est = value.is_estimate ? ' est.' : '';
  return `${base}${range}${est}${year}`;
}

export function date(iso: string | null | undefined): string {
  if (!iso) return NOT_FOUND;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(DISPLAY_LOCALE, { day: '2-digit', month: 'short', year: 'numeric' });
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return 'never';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(DISPLAY_LOCALE, {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

/** Turn any SCREAMING_SNAKE or snake_case token into readable words. */
export function humanize(token: string): string {
  const spaced = token.replace(/_/g, ' ').toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export const eligibilityTone: Record<EligibilityStatus, Tone> = {
  MET: 'ok',
  PENDING: 'warn',
  GAP: 'risk',
  NOT_APPLICABLE: 'neutral',
  NEEDS_OFFICIAL_CLARIFICATION: 'neutral',
};

export const admissionsFitTone: Record<AdmissionsFit, Tone> = {
  STRONGER_FIT: 'ok',
  PLAUSIBLE_FIT: 'info',
  AMBITIOUS: 'warn',
  INSUFFICIENT_DATA: 'neutral',
};

export const fundingFitTone: Record<FundingFit, Tone> = {
  CONFIRMED_OPPORTUNITY: 'ok',
  COMPETITIVE_OPPORTUNITY: 'info',
  LIMITED_OPPORTUNITY: 'warn',
  NOT_ELIGIBLE: 'risk',
  UNKNOWN: 'neutral',
};

export const fundingClassTone: Record<FundingClassification, Tone> = {
  FULL_RIDE_CONFIRMED: 'ok',
  FULL_TUITION: 'info',
  LARGE_GRANT: 'info',
  PARTIAL: 'warn',
  NEED_BASED_POSSIBLE: 'warn',
  NOT_ELIGIBLE: 'risk',
  UNKNOWN: 'neutral',
};

export const bucketTone: Record<Bucket, Tone> = {
  WELL_PLACED: 'ok',
  PLAUSIBLE: 'info',
  AMBITIOUS: 'warn',
  OUT_OF_BUDGET: 'risk',
  NEEDS_CLARIFICATION: 'neutral',
  EXCLUDED: 'neutral',
};

export const claimStatusTone: Record<ClaimStatus, Tone> = {
  VERIFIED_CURRENT: 'ok',
  POSSIBLY_STALE: 'warn',
  CONFLICTING: 'risk',
  UNVERIFIED: 'neutral',
  NOT_FOUND: 'neutral',
  NEEDS_OFFICIAL_CLARIFICATION: 'warn',
  /** Historical record: same informational family as NOT_FOUND/UNVERIFIED. */
  SUPERSEDED: 'neutral',
};

/**
 * Short display labels.
 *
 * Only for the table, where column width is scarce. The full phrase stays in
 * STATUS_MEANING and is shown on hover, so the shortening never costs meaning.
 */
export const STATUS_LABEL: Record<string, string> = {
  NEEDS_OFFICIAL_CLARIFICATION: 'Unverified',
  INSUFFICIENT_DATA: 'No data',
  FULL_RIDE_CONFIRMED: 'Full ride',
  NEED_BASED_POSSIBLE: 'Need-based',
  CONFIRMED_OPPORTUNITY: 'Confirmed',
  COMPETITIVE_OPPORTUNITY: 'Competitive',
  LIMITED_OPPORTUNITY: 'Limited',
  STRONGER_FIT: 'Stronger',
  PLAUSIBLE_FIT: 'Plausible',
  NOT_APPLICABLE: 'N/A',
  VERIFIED_CURRENT: 'Verified',
  // Not "Ageing": a knowledge-base fact can be out of date on the day it was
  // verified (last year's fee), so age is not what the chip says.
  POSSIBLY_STALE: 'Possibly outdated',
};

/** Plain-English gloss for each status, shown as a tooltip and in the legend. */
export const STATUS_MEANING: Record<string, string> = {
  MET: 'Every published requirement that could be checked is satisfied.',
  PENDING: 'Nothing is failing, but something is still outstanding — a test, a document, or a profile field.',
  GAP: 'At least one published requirement is currently not met.',
  NOT_APPLICABLE: 'The requirement does not apply to this applicant.',
  NEEDS_OFFICIAL_CLARIFICATION: 'The published requirement could not be verified against an official source.',
  STRONGER_FIT: 'Scores sit clearly above the published minimums. Selection is still competitive.',
  PLAUSIBLE_FIT: 'Formal requirements are met. The outcome depends on competitive selection.',
  AMBITIOUS: 'The profile sits at or below the published range.',
  INSUFFICIENT_DATA: 'Not enough verified data to compare the profile against.',
  FULL_RIDE_CONFIRMED: 'An official source confirms tuition, mandatory fees, housing and meals (or a living stipend) are covered.',
  FULL_TUITION: 'Tuition is covered. Living costs are not fully covered.',
  LARGE_GRANT: 'A substantial award, but a meaningful part of the cost remains.',
  PARTIAL: 'Covers a limited share of the total cost.',
  NEED_BASED_POSSIBLE: 'Depends on a financial-need assessment that has not been filed, so it cannot be sized.',
  NOT_ELIGIBLE: 'Published conditions exclude this applicant.',
  UNKNOWN: 'Not enough official information to classify.',
  CONFIRMED_OPPORTUNITY: 'There is a confirmed opportunity to apply. The decision still rests with the university.',
  COMPETITIVE_OPPORTUNITY: 'Eligible to apply by published criteria; awarded competitively.',
  LIMITED_OPPORTUNITY: 'Funding exists but covers little, or cannot be assessed in advance.',
  VERIFIED_CURRENT: 'Read from an official page within its freshness window.',
  POSSIBLY_STALE: 'Read from an official page, but it may no longer be current (an earlier academic year, a passed date, or a long time since it was checked). Re-check it before relying on it.',
  CONFLICTING: 'Two official sources disagree. Neither has been chosen as correct.',
  UNVERIFIED: 'Not confirmed against an official source.',
  NOT_FOUND: 'No source published this value.',
  WELL_PLACED: 'Requirements met with room, funding confirmed, and the remaining cost within your ceiling.',
  PLAUSIBLE: 'Requirements and funding both look reachable on published data.',
  OUT_OF_BUDGET: 'What remains to pay is past the ceiling you stated. The row is kept, with the number.',
  EXCLUDED: 'A published requirement you do not meet, or a country you excluded. Listed, not ranked.',
  NEEDS_CLARIFICATION: 'Too little could be verified to place this row at all.',
};

/** The fit number never travels without this sentence. */
export const FIT_DISCLAIMER =
  'How well this matches your stated priorities, on confirmed data. Not a probability of admission.';

/** A fit or coverage value, or an explicit dash when nothing was known. */
export function ratio(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? '—' : value.toFixed(digits);
}

export function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`;
}

export function scorePercent(total: number, max: number): number {
  return max > 0 ? Math.round((total / max) * 100) : 0;
}

export function isDemoSource(urls: string[]): boolean {
  return urls.some((u) => u.startsWith('fixture://'));
}

/** A fixture URL is not clickable; say so rather than rendering a dead link. */
export function sourceLabel(url: string): string {
  if (url.startsWith('fixture://')) return `${url} (bundled demo page)`;
  try {
    const parsed = new URL(url);
    return parsed.hostname + parsed.pathname;
  } catch {
    return url;
  }
}

/**
 * A fee printed only as a range ("27,650–34,670 GBP"), from a money value or a
 * tuition claim's value (`range_low`/`range_high`); null when it is one figure.
 */
export function feeRange(v: unknown): string | null {
  if (!v || typeof v !== 'object') return null;
  const o = v as { range_low?: unknown; range_high?: unknown; currency?: unknown };
  if (typeof o.range_low !== 'number' || typeof o.range_high !== 'number' || o.range_low === o.range_high) return null;
  const n = (x: number) => Math.round(x).toLocaleString('en-US');
  return `${n(o.range_low)}–${n(o.range_high)} ${String(o.currency ?? '')}`.trim();
}

/** A claim's normalised value as text: money as "66,720 USD", objects as "key: value" pairs. */
export function claimValue(v: unknown): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'boolean') return v ? 'yes' : 'no';
  if (Array.isArray(v)) return v.map(claimValue).join(', ');
  if (typeof v === 'object') {
    const o = v as Record<string, unknown>;
    const range = feeRange(o);
    if (range) return range;
    if ('amount' in o && 'currency' in o) return `${Number(o.amount).toLocaleString('en-US')} ${o.currency}`;
    return Object.entries(o).map(([k, val]) => `${k}: ${claimValue(val)}`).join(', ');
  }
  return String(v);
}

const STALE_MARK = 'Stale, not current: ';

/**
 * Why a claim is stale, as the backend wrote it into its notes ("academic year
 * 2026/2027 is before the fall 2027 intake's 2027/28"); null when it gave none.
 *
 * A knowledge-base fact can be stale on the day it was verified (a fee for last
 * year), so its age alone ("0d old") says nothing: the reason is the caveat.
 */
export function staleReason(notes: string | null | undefined): string | null {
  const text = notes ?? '';
  const at = text.indexOf(STALE_MARK);
  if (at < 0) return null;
  const reason = text.slice(at + STALE_MARK.length).trim().replace(/\.$/, '');
  return reason || null;
}

const CAVEAT = /(?:^|\s)Caveat: ([^.]+)\./;

/**
 * The caveat on a knowledge-base fact that is current but not fully verified
 * ("year not printed on the page; assumed current application cycle"), as the
 * backend wrote it into the notes; null when there is none.
 */
export function caveatText(notes: string | null | undefined): string | null {
  return CAVEAT.exec(notes ?? '')?.[1]?.trim() || null;
}

const PER_PERIOD = /Amount per ([^,]+), as published/;

/**
 * Periods that are a unit of study (`app.knowledge.claims.PER_UNIT_PERIODS`): the
 * page printed a rate and no yearly figure, and nothing multiplies it out.
 */
export const PER_UNIT_PERIODS = new Set(['credit', 'credit hour', 'unit', 'point', 'credit point', 'course']);

export function isPerUnit(period: string | null): boolean {
  return period !== null && PER_UNIT_PERIODS.has(period.toLowerCase());
}

/**
 * Verified tuition the cost table does not use, one line each: a fee for
 * another academic year ("66,720 USD a year, academic year 2026/2027 (not
 * current: …)") or one not published per year. Read from the claim notes the
 * knowledge base writes, so a live read (no such notes) yields nothing.
 */
export function unusedTuitionLines(claims: TuitionClaim[]): string[] {
  return unusedTuition(claims).map(({ amount, range, period, year, reason }) => {
    const shown = range ? `published range ${range}` : amount;
    const money = `${shown}${period ? ` per ${period}` : ' a year'}`;
    const when = year ? `academic year ${year}` : 'no academic year stated';
    const why = reason
      ? `not current: ${reason}`
      : isPerUnit(period)
        ? `published per ${period} (no yearly figure printed)`
        : `published per ${period}, not as a yearly figure`;
    return `${money}, ${when} (${why})`;
  });
}

type TuitionClaim = { claim_type: string; normalized_value: unknown; academic_year: string | null; notes: string };

/** One verified fee the cost table does not use, in parts, so `lib/messages.ts` can word it per locale. */
export interface UnusedTuition<C extends TuitionClaim = TuitionClaim> {
  claim: C;
  amount: string;
  /** "27,650–34,670 GBP" when the page printed only a range; null for one figure. */
  range: string | null;
  /** As published ("semester", "full programme (3 years)"); null for a yearly fee. */
  period: string | null;
  year: string | null;
  /** The English stale reason; null for a current fee that is not per year. */
  reason: string | null;
}

/** The fees `unusedTuitionLines` words, before they are worded. */
export function unusedTuition<C extends TuitionClaim>(claims: C[]): UnusedTuition<C>[] {
  return claims
    .filter((c) => c.claim_type === 'tuition')
    .flatMap((c) => {
      const reason = staleReason(c.notes);
      const period = PER_PERIOD.exec(c.notes ?? '')?.[1] ?? null;
      if (!reason && !period) return [];
      const range = feeRange(c.normalized_value);
      return [{ claim: c, amount: claimValue(c.normalized_value), range, period, year: c.academic_year, reason }];
    });
}

/** The header chip: where this deployment's answers come from. */
export function sourceModeLabel(c: { demo_mode: boolean; knowledge_mode?: string }): string {
  if (c.demo_mode) return 'Demo data';
  return c.knowledge_mode === 'kb' ? 'Verified knowledge base' : 'Live sources';
}

/**
 * The chip beside a stale claim: its age when age is why it is stale, else
 * plainly "not current". A knowledge-base fact stale for a stated reason (a fee
 * for last year, a list for another cycle) is not stale for being old: verified
 * the day before, it read "1d old" beside "Not current: …" (KB v18 smoke U1).
 */
export function staleChip(ageDays: number, reasoned = false): string {
  return ageDays > 0 && !reasoned ? `${ageDays}d old` : 'not current';
}

/**
 * The open questions a row carries: its own and its document checklist's (a
 * stale list, for one). Counting only the row's own showed "1 open question"
 * beside two on the Documents tab (KB v10 smoke D6).
 */
export function openQuestionCount(result: {
  unresolved: unknown[];
  checklist?: { unresolved: unknown[] } | null;
}): number {
  return result.unresolved.length + (result.checklist?.unresolved.length ?? 0);
}

/** How a checklist item applies, as the official page states it. */
export type DocumentRequirement = 'required' | 'optional' | 'conditional';

/**
 * A checklist item's requirement, condition and its own claim.
 *
 * The item's claim is the `required_document` claim that names it: a plain
 * name for a required document, `{document, requirement, condition}` for an
 * optional or conditional one (the knowledge base's shape). Without such a
 * claim the item's own `required` flag decides, and no condition is invented.
 */
export function documentRequirement<C extends { claim_type: string; normalized_value: unknown }>(
  item: { name: string; required: boolean },
  claims: C[],
): { requirement: DocumentRequirement; condition: string | null; claim: C | null } {
  const claim = claims.find((c) => {
    if (c.claim_type !== 'required_document') return false;
    const v = c.normalized_value;
    if (typeof v === 'string') return v === item.name;
    return typeof v === 'object' && v !== null && (v as Record<string, unknown>).document === item.name;
  }) ?? null;
  const value = claim && typeof claim.normalized_value === 'object' && claim.normalized_value !== null
    ? (claim.normalized_value as Record<string, unknown>)
    : null;
  const stated = value?.requirement;
  const requirement: DocumentRequirement =
    stated === 'required' || stated === 'optional' || stated === 'conditional'
      ? stated
      : item.required ? 'required' : 'optional';
  const condition =
    requirement === 'conditional' && typeof value?.condition === 'string' && value.condition.trim()
      ? value.condition.trim()
      : null;
  return { requirement, condition, claim };
}

/**
 * Display helpers.
 *
 * Every function here has one job: never invent a value. An absent number
 * renders as an explicit phrase ("not published") rather than a dash, a zero,
 * or an empty cell that could be read as "nothing to pay".
 */

import type {
  AdmissionsFit,
  ClaimStatus,
  CoverageBreakdown,
  EligibilityStatus,
  FundingClassification,
  FundingFit,
  Money,
} from '@/types';

export type Tone = 'ok' | 'info' | 'warn' | 'risk' | 'neutral' | 'demo' | 'accent';

export const NOT_PUBLISHED = 'not published';
export const NOT_FOUND = 'not found';

/**
 * How a converted amount came to be, or null when the amount is as published.
 *
 * A student comparing a Dutch fee with a Canadian one sees both in their own
 * currency, and nothing else on screen distinguishes a figure a university
 * stated from one this product calculated. The rate, the day it was observed
 * and its source are all sent with the value, so all three are shown.
 */
export function conversionNote(value: Money | null | undefined): string | null {
  if (!value?.original_currency || value.original_amount == null) return null;
  const original = `${Math.round(value.original_amount).toLocaleString('en-US')} ${value.original_currency}`;
  const rate = value.rate != null ? ` at ${value.rate} ${value.original_currency}/${value.currency}` : '';
  const on = value.rate_date ? ` observed on ${value.rate_date}` : '';
  const from = value.rate_source ? ` — ${value.rate_source}` : '';
  return `Converted from ${original}${rate}${on}${from}`;
}

/**
 * Cost categories the university publishes that this award does not cover.
 *
 * A student was shown "Full ride" and, in the next column, a non-zero
 * remaining cost per year. Both were true — the award covers tuition, fees,
 * housing and meals, and the university also publishes insurance, books and
 * travel — but side by side with nothing joining them they read as a
 * contradiction, and the one a student is likelier to believe is the one that
 * says they have nothing left to pay.
 *
 * Anything not explicitly covered counts as uncovered, including `unknown`:
 * silence is not permission here any more than it is anywhere else in this
 * product. A category the university publishes no cost for is not listed —
 * there is nothing unpaid, and naming it would manufacture a worry.
 */
export function uncoveredCategories(
  coverage: CoverageBreakdown[],
  publishedCosts: Partial<Record<string, Money | null>>,
): string[] {
  const covered = new Set(
    coverage.filter((c) => c.covered === 'yes').map((c) => String(c.category)),
  );
  return Object.entries(publishedCosts)
    .filter(([category, amount]) => amount && !covered.has(category))
    .map(([category]) => category);
}

export function money(value: Money | null | undefined): string {
  if (!value) return NOT_FOUND;
  const base = `${Math.round(value.amount).toLocaleString('en-US')} ${value.currency}`;
  const range =
    value.range_low != null && value.range_high != null && value.range_low !== value.range_high
      ? ` (${Math.round(value.range_low).toLocaleString('en-US')}–${Math.round(value.range_high).toLocaleString('en-US')})`
      : '';
  const year = value.academic_year ? ` · ${value.academic_year}` : '';
  const est = value.is_estimate ? ' est.' : '';
  const conv = conversionNote(value) ? ' converted' : '';
  return `${base}${range}${est}${conv}${year}`;
}

export function date(iso: string | null | undefined): string {
  if (!iso) return NOT_FOUND;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return 'never';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('en-GB', {
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

export const claimStatusTone: Record<ClaimStatus, Tone> = {
  VERIFIED_CURRENT: 'ok',
  POSSIBLY_STALE: 'warn',
  CONFLICTING: 'risk',
  UNVERIFIED: 'neutral',
  NOT_FOUND: 'neutral',
  NEEDS_OFFICIAL_CLARIFICATION: 'warn',
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
  // Not "Full ride" unqualified. The award covers the four core
  // categories; a university that also publishes insurance, books or
  // travel leaves a real amount to pay, and the shortlist shows it in the
  // next column. A label that claims more than the award covers is the
  // half a student remembers.
  FULL_RIDE_CONFIRMED: 'Core costs covered',
  NEED_BASED_POSSIBLE: 'Need-based',
  CONFIRMED_OPPORTUNITY: 'Confirmed',
  COMPETITIVE_OPPORTUNITY: 'Competitive',
  LIMITED_OPPORTUNITY: 'Limited',
  STRONGER_FIT: 'Stronger',
  PLAUSIBLE_FIT: 'Plausible',
  NOT_APPLICABLE: 'N/A',
  VERIFIED_CURRENT: 'Verified',
  POSSIBLY_STALE: 'Ageing',
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
  FULL_RIDE_CONFIRMED:
    'An official source confirms tuition, mandatory fees, housing and meals '
    + '(or a living stipend) are covered. Anything else the university '
    + 'publishes — insurance, books, travel — is still yours to pay, and is '
    + 'in the remaining cost. Being eligible is not the same as being awarded.',
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
  POSSIBLY_STALE: 'Read from an official page, but long enough ago that it should be re-checked.',
  CONFLICTING: 'Two official sources disagree. Neither has been chosen as correct.',
  UNVERIFIED: 'Not confirmed against an official source.',
  NOT_FOUND: 'No source published this value.',
};

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

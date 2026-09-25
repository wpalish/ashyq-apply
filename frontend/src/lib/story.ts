/**
 * What a story card says (concept Q, screen 14): the student's own results,
 * in a form worth posting, with nothing the product does not know.
 *
 * Three cards:
 * - "My route": from the country of residence to a programme's city, with
 *   the grant it offers and where that was read.
 * - "Requirements met": only for a programme whose every checked requirement
 *   is met, with the published minimums and "the admission decision is the
 *   university's" beside the headline.
 * - "My application map": the run's counts, as the reveal shows them.
 * A fourth concept card, "application sent", is not here: the product has no
 * record of a sent application, and the card would have to invent one.
 *
 * Privacy for a 16-year-old (§15): the price after grants and the student's
 * own scores are off until switched on; the school, city and documents are
 * never on a card, and the route starts at the country, not the city. The
 * concept had the first name on by default, but the profile has no first-name
 * field: the name is the first word of the case's label, which on a Kazakh
 * document is the surname ("Sadykova Aruzhan"). So the name is off until the
 * student switches it on, seeing exactly the word that will print. Demo data
 * says so on the card.
 */

import { coverageOf } from '@/components/MoneyArithmetic';
import { groupByBudget, ceilingFrom } from '@/components/BudgetLadder';
import { urlHost } from '@/components/ResultCard';
import { calendarDay, spokenDate } from '@/lib/deadlines';
import { humanize, money } from '@/lib/format';
import { homeOf, placeOf, type LatLon } from '@/lib/globe';
import type { ProgramResult } from '@/types';

export type StoryKind = 'route' | 'requirements' | 'map';

export interface StoryOptions {
  /** The first word of the case's label: off by default, since it may be the surname. */
  name: boolean;
  /** What is left to pay a year after grants. */
  price: boolean;
  /** The student's own test scores beside the published minimums. */
  scores: boolean;
}

export const STORY_DEFAULTS: StoryOptions = { name: false, price: false, scores: false };

export const STORY_TITLE: Record<StoryKind, string> = {
  route: 'My route',
  requirements: 'Requirements met',
  map: 'My application map',
};

export interface StoryRow {
  label: string;
  detail: string;
}

export interface StoryModel {
  kind: StoryKind;
  /** The card's palette: night for the route, sun for requirements, day for the map. */
  tone: 'night' | 'sun' | 'day';
  /** "Aruzhan · 2027", "2027", or empty. */
  who: string;
  eyebrow: string;
  /** The headline, one entry per line. */
  title: string[];
  /** The route's two ends; the start is a country, never a city. */
  from?: string;
  to?: string;
  lines: string[];
  chip?: string;
  rows: StoryRow[];
  stats: { value: string; label: string }[];
  note?: string;
  source: string;
  /** Said beside the headline, so a cropped screenshot still carries it. */
  honesty?: string;
  demo: boolean;
  /** For the globe: home and the places the card is about. */
  globe?: { home: LatLon | null; places: (LatLon & { country?: string })[] };
}

export interface StoryInput {
  results: ProgramResult[];
  /** The programme, for the route and requirements cards. */
  result?: ProgramResult | null;
  profile: unknown;
  demo: boolean;
}

/** Words a card must never use: a card states facts, never an outcome. */
export const FORBIDDEN = /\bchances?\b|%|probab|will get in|guarantee|\baccepted\b|\badmitted\b|\bget in\b/i;

const PLACEHOLDER = /^(applicant|demo|student|case|test|synthetic|example)$/i;

/**
 * The first word of the case's label, if it looks like a name. The label is
 * the student's own ("Aruzhan S."), or a placeholder a counsellor or the demo
 * left ("Demo Applicant (synthetic)"), which is not a name to print.
 */
export function firstName(profile: unknown): string | null {
  const label = (profile as { display_name?: unknown } | null)?.display_name;
  if (typeof label !== 'string') return null;
  const first = label.trim().split(/\s+/)[0]?.replace(/[^\p{L}'-]/gu, '') ?? '';
  if (!first || PLACEHOLDER.test(first)) return null;
  return first;
}

function context(profile: unknown): Record<string, unknown> {
  return ((profile as { context?: Record<string, unknown> } | null)?.context) ?? {};
}

function intakeYear(profile: unknown): string {
  const year = context(profile).intake_year;
  return typeof year === 'number' ? String(year) : '';
}

function residence(profile: unknown): string | null {
  const country = context(profile).country_of_residence;
  return typeof country === 'string' && country.trim() ? country.trim() : null;
}

/** A cost category as a friend would say it. */
const COST_WORD: Record<string, string> = {
  mandatory_fees: 'fees', personal: 'personal costs', health_insurance: 'insurance', visa: 'the visa',
};
function costWord(category: string): string {
  return COST_WORD[category] ?? humanize(category).toLowerCase();
}

function capitalised(text: string): string {
  return text ? text[0]!.toUpperCase() + text.slice(1) : text;
}

function readOn(iso: string | null | undefined): string {
  const day = calendarDay(iso);
  return day ? `read ${spokenDate(day)}` : 'date not recorded';
}

/** "rug.nl · read 14 September 2026"; the demo corpus says it is the demo. */
function sourceLine(result: ProgramResult): string {
  const host = urlHost(result.source_urls?.[0]) || 'source not recorded';
  return `${host} · ${readOn(result.last_verified)}`;
}

/** A published minimum a friend can read: numbers and short words, not dates or lists. */
function minimumOf(value: unknown): string | null {
  if (typeof value === 'number' && Number.isFinite(value)) return `minimum ${Number.isInteger(value) ? value : value.toFixed(1)}`;
  return null;
}

function yours(value: unknown): string | null {
  if (typeof value === 'number' && Number.isFinite(value)) return Number.isInteger(value) ? String(value) : value.toFixed(1);
  return null;
}

/**
 * The requirements a friend recognises: an overall or total score or a grade
 * average first, then the rest; never a date (the deadline check is "met" too,
 * which on a card reads as nonsense).
 */
function headlineChecks(result: ProgramResult) {
  const met = (result.requirement_checks ?? [])
    .filter((c) => c.status === 'MET' && minimumOf(c.published_value));
  const rank = (name: string) => (/overall|total|gpa|average/i.test(name) ? 0 : 1);
  return [...met].sort((a, b) => rank(a.requirement) - rank(b.requirement)).slice(0, 3);
}

/** Whether a programme can have a "requirements met" card. */
export function requirementsShareable(result: ProgramResult | null | undefined): boolean {
  return Boolean(result && result.eligibility === 'MET' && headlineChecks(result).length > 0);
}

/** The kinds a sheet can offer for what it was opened on. */
export function storyKinds(result: ProgramResult | null | undefined): StoryKind[] {
  if (!result) return ['map'];
  return requirementsShareable(result) ? ['route', 'requirements', 'map'] : ['route', 'map'];
}

function who(profile: unknown, options: StoryOptions): string {
  const name = options.name ? firstName(profile) : null;
  return [name, intakeYear(profile)].filter(Boolean).join(' · ');
}

export function storyModel(kind: StoryKind, input: StoryInput, options: StoryOptions = STORY_DEFAULTS): StoryModel {
  const { results, profile, demo } = input;
  const result = input.result ?? null;
  const base = { who: who(profile, options), demo, rows: [], stats: [], lines: [] };

  if (kind === 'route' && result) {
    const { award, covered } = coverageOf(result);
    const gap = result.funding_gap;
    const lines = [result.university, `${result.program} · ${capitalised(result.intake)}`];
    if (options.price) {
      lines.push(gap?.computable && gap.gap
        ? `${money({ ...gap.gap, academic_year: null })} a year left to pay, if awarded`
        : 'Cost not computed');
    }
    const place = placeOf(result);
    return {
      ...base,
      kind,
      tone: 'night',
      eyebrow: STORY_TITLE.route,
      title: [],
      from: residence(profile) ?? undefined,
      to: result.city || result.country,
      lines,
      chip: award
        ? covered.length
          ? `${award.name} · covers ${covered.slice(0, 4).map(costWord).join(', ')}`
          : award.name
        : undefined,
      source: sourceLine(result),
      globe: place ? { home: homeOf(profile), places: [place] } : undefined,
    };
  }

  if (kind === 'requirements' && result && requirementsShareable(result)) {
    return {
      ...base,
      kind,
      tone: 'sun',
      eyebrow: result.university,
      title: ['Requirements', 'met'],
      lines: [result.program],
      rows: headlineChecks(result).map((c) => {
        const mine = options.scores ? yours(c.applicant_value) : null;
        return { label: c.requirement, detail: `${minimumOf(c.published_value)}${mine ? ` · mine ${mine}` : ''}` };
      }),
      source: `By the published requirements on ${sourceLine(result)}.`,
      honesty: "The admission decision is the university's.",
    };
  }

  // The map: the run's counts, as the reveal counts them.
  const countries = new Set(results.map((r) => r.country)).size;
  const ceiling = ceilingFrom(profile);
  const stats = [
    { value: String(results.length), label: results.length === 1 ? 'programme' : 'programmes' },
    { value: String(countries), label: countries === 1 ? 'country' : 'countries' },
  ];
  // As the reveal counts it: after grants that are mostly competitive.
  if (ceiling) stats.push({ value: String(groupByBudget(results, ceiling).within.length), label: 'within budget, if awarded' });
  const upcoming = results
    .filter((r) => !r.deadline_passed && calendarDay(r.admission_deadline))
    .sort((a, b) => calendarDay(a.admission_deadline)!.localeCompare(calendarDay(b.admission_deadline)!))[0];
  const oldest = results.map((r) => calendarDay(r.last_verified)).filter((d): d is string => Boolean(d)).sort()[0];
  const places = results.map((r) => placeOf(r)).filter((p): p is NonNullable<typeof p> => Boolean(p));
  return {
    ...base,
    kind: 'map',
    tone: 'day',
    eyebrow: STORY_TITLE.map,
    title: ['My application', 'map'],
    stats,
    note: upcoming
      ? `First deadline: ${spokenDate(calendarDay(upcoming.admission_deadline)!)}, ${upcoming.city || upcoming.country}`
      : undefined,
    source: `Prices and deadlines from the universities' own pages${oldest ? `, the oldest ${readOn(oldest)}` : ''}.`,
    globe: { home: homeOf(profile), places },
  };
}

/** Every string a card prints, for the wording check. */
export function storyText(model: StoryModel): string {
  return [
    model.demo ? 'Demo data, not real university pages' : '', model.who, model.eyebrow, model.title.join(' '),
    model.from && model.to ? `${model.from} to ${model.to}` : model.to, ...model.lines, model.chip,
    ...model.rows.map((r) => `${r.label}: ${r.detail}`), ...model.stats.map((s) => `${s.value} ${s.label}`),
    model.note, model.source, model.honesty,
  ].filter(Boolean).join('\n');
}

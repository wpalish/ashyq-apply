/**
 * What the research has found so far that the applicant should hear about.
 *
 * Round 7's "research running" screen told the night moment through three
 * findings, not a spinner: a programme a requirement rules out, a cost and an
 * award published for different years, and a site that did not answer. Each
 * one here is read off the run as it stands - a result's hard-filter failures,
 * its funding gap's year-mismatch flag, the run's fetch errors - so the list
 * grows while the research runs and never says anything the data does not.
 */

import { urlHost } from '@/components/ResultCard';
import type { ProgramResult } from '@/types';

export type FindingKind = 'exclusion' | 'year' | 'unreadable';

export interface Finding {
  kind: FindingKind;
  /** One or two words for what kind of thing this is. */
  label: string;
  /** The university, or the site when no result names it. */
  where: string;
  text: string;
}

export const FINDING_LABEL: Record<FindingKind, string> = {
  exclusion: 'Requirement not met',
  year: 'Different years',
  unreadable: 'Did not answer',
};

function firstSentence(text: string): string {
  const match = text.match(/^.*?[.!?](\s|$)/);
  return (match ? match[0] : text).trim();
}

const URL_IN_TEXT = /\b(?:fixture|https?):\/\/[^\s)]+/;

/** The site of a URL found in an error message, without the page path. */
function siteOf(url: string): string {
  if (url.startsWith('fixture://')) return url.slice('fixture://'.length).split('/')[0] ?? '';
  return urlHost(url);
}

export function findingsSoFar(
  errors: string[], results: ProgramResult[], perKind = 2, pagesFailed = 0,
): Finding[] {
  const exclusions: Finding[] = results
    .filter((r) => (r.hard_filter_failures ?? []).length > 0)
    .map((r) => ({
      kind: 'exclusion',
      label: FINDING_LABEL.exclusion,
      where: r.university,
      text: `not met: ${r.hard_filter_failures.join(', ')}`,
    }));

  const years: Finding[] = results
    .filter((r) => r.funding_gap?.year_mismatch)
    .map((r) => {
      const warning = (r.funding_gap?.warnings ?? []).find((w) => /year|\d{4}\/\d{2}/i.test(w));
      return {
        kind: 'year',
        label: FINDING_LABEL.year,
        where: r.university,
        text: warning ? firstSentence(warning) : 'The cost and the award are published for different years.',
      };
    });

  // One line per site, counting its distinct pages: the same page is often
  // reported twice, once by the fetch and once by the stage that wanted it.
  const pagesBySite = new Map<string, Set<string>>();
  for (const message of errors) {
    // "…/program-0.html: http_error" - the colon closes the sentence, not the URL.
    const url = message.match(URL_IN_TEXT)?.[0]?.replace(/[:.,;]+$/, '');
    if (!url) continue;
    const site = siteOf(url);
    if (!site) continue;
    if (!pagesBySite.has(site)) pagesBySite.set(site, new Set());
    pagesBySite.get(site)!.add(url);
  }
  const unreadable: Finding[] = [...pagesBySite.entries()].map(([site, pages]) => {
    // A site whose every page failed leaves no source on its result, but the
    // programme's own address still names it.
    const owner = results.find((r) => [...(r.source_urls ?? []), r.program_url ?? '']
      .some((u) => u.includes(`//${site}/`) || (u !== '' && urlHost(u) === site)));
    return {
      kind: 'unreadable',
      label: FINDING_LABEL.unreadable,
      where: owner?.university ?? site,
      text: `${pages.size} page${pages.size === 1 ? '' : 's'} could not be read; what they hold stays unknown.`,
    };
  });

  // The counter moves before the messages arrive: while no site can be named
  // yet, the count itself is the finding, so the list never says "nothing"
  // beside a number that says otherwise.
  if (unreadable.length === 0 && pagesFailed > 0) {
    unreadable.push({
      kind: 'unreadable',
      label: FINDING_LABEL.unreadable,
      where: 'The sites read so far',
      text: `${pagesFailed} page${pagesFailed === 1 ? '' : 's'} could not be read; what they hold stays unknown.`,
    });
  }

  return [
    ...exclusions.slice(0, perKind),
    ...years.slice(0, perKind),
    ...unreadable.slice(0, perKind),
  ];
}

/** How many of each kind there are in all, for "and N more". */
export function findingTotals(errors: string[], results: ProgramResult[], pagesFailed = 0): number {
  return findingsSoFar(errors, results, Number.POSITIVE_INFINITY, pagesFailed).length;
}

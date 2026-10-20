/**
 * The kb-mode browser journey (E2E-KB, docs/process/NEXT_CYCLES_2026-10-21.md #4).
 *
 * The two manual KB smokes (docs/process/KB_E2E_SMOKE_2026-10-19.md, KB v10
 * and v18) found 13 things an applicant saw wrong in kb mode and fixed them in
 * the frontend and the runner, each with a unit test. This spec re-walks the
 * smoke in a real browser against the real API and worker, so a regression of
 * any of them turns CI red where the applicant would see it:
 *
 *   D1 every checklist item has its Required / Optional / Conditional chip, owner, condition and link
 *   D2 an approved row without a KB list says why on its Documents tab, not "approve this row"
 *   D3 the checklist chip says "from the verified knowledge base" / "verified, some items not current"
 *   D4 a one-day lead time reads "~1 day", in the reader's plural
 *   D5 a university outside the KB gets the "no entry in the verified knowledge base" reason
 *   D6 the open-question count on the card and the hero includes the checklist's own questions
 *   U1 a fact stale for a stated reason reads "not current", never "1d old"
 *   U2 a passed deadline carries "deadline passed" on the card and the hero
 *   U3 a caveated fee in the cost table says so under the table
 *   U4 per-semester / per-programme fee lines and the gap reason's {fees} are in the reader's language
 *   U5 the suggested-order steps name who acts in the reader's language
 *   U6 "which certificate instead?" only where another language is named
 *   U8 a row with no KB fee says "no verified tuition fee in the knowledge base", not live-mode copy
 *
 * plus what landed since (REL-1's related-only route, WHY-1's unknown kinds,
 * CAT-1's catalogue chips and verified filter, a fee published as a range), in
 * en, ru and kk. Expected words come from the frontend's dictionaries
 * (src/lib/i18n.results.ts), so the spec checks which sentence is shown in which
 * language, not a copy of today's wording.
 *
 * One applicant: the CS-bachelor demo profile (Kazakhstan, fall 2027, IELTS
 * 7.0). Nine catalogue universities, each chosen for a case:
 */

import { readFileSync } from 'node:fs';
import { expect, test, type APIRequestContext, type Browser, type Locator, type Page } from '@playwright/test';
import { DEFAULT_PROFILE } from '../src/lib/defaultProfile';
import { EN_RESULTS, KK_RESULTS, RU_RESULTS, type ResultsKey } from '../src/lib/i18n.results';
import { caveatText, staleReason } from '../src/lib/format';
import type { UniversityCandidate, UniversityCatalogue } from '../src/api/client';
import type { ClaimOut, MessageRef, ProgramResult, RunView } from '../src/types';
import { NETGUARD_LOG } from './kb-env/paths';

const CASES = {
  stanford: 'Stanford University', // a caveated deadline (year inferred); a fee for another year; "no other language recorded"
  eth: 'ETH Zurich', // a standing fee per semester; "which certificate instead" (German)
  kth: 'KTH Royal Institute of Technology', // a standing fee per programme; related-only route (REL-1)
  kyoto: 'Kyoto University', // a standing yearly fee that enters the cost table, with its caveat
  fudan: 'Fudan University', // another cycle's document list; a checklist question
  oxford: 'University of Oxford', // a passed deadline; no fee; access-class unknowns (WHY-1)
  edinburgh: 'The University of Edinburgh', // plain and current: a full checklist with a one-day step
  sheffield: 'The University of Sheffield', // a fee published as a range; no document facts
  groningen: 'University of Groningen', // outside the KB
} as const;
type Case = keyof typeof CASES;

type Locale = 'en' | 'ru' | 'kk';
const LOCALES: Locale[] = ['en', 'ru', 'kk'];
const DICTIONARIES: Record<Locale, Record<string, string>> = { en: EN_RESULTS, ru: RU_RESULTS, kk: KK_RESULTS };

// ------------------------------------------------------------------ the words

function fill(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (whole, name: string) => (name in params ? String(params[name]) : whole));
}

/** What the frontend's `t`, `tf`, `tn` and `localize` say in `locale`, from the same dictionaries. */
function wordsFor(locale: Locale) {
  const dictionary = DICTIONARIES[locale];
  const t = (key: ResultsKey): string => dictionary[key] ?? EN_RESULTS[key];
  const tf = (key: ResultsKey, params: Record<string, string | number>): string => fill(t(key), params);
  const tn = (base: string, n: number, params: Record<string, string | number> = {}): string => {
    const exact = `${base}.${new Intl.PluralRules(locale).select(n)}`;
    const key = (exact in EN_RESULTS ? exact : `${base}.${n === 1 ? 'one' : 'other'}`) as ResultsKey;
    return tf(key, { n, ...params });
  };
  /** A sentence the backend wrote: its key's template here, or the served English. */
  const msg = (ref: MessageRef | null | undefined, english: string): string => {
    if (!ref || locale === 'en') return english;
    const template = dictionary[`msg.${ref.key}`];
    if (template === undefined) return english;
    const params: Record<string, string> = {};
    for (const [, name = ''] of template.matchAll(/\{(\w+)\}/g)) {
      const parts = ref.parts?.[name];
      if (parts && parts.length > 0 && parts.every((p) => p && dictionary[`msg.${p.key}`] !== undefined)) {
        params[name] = parts.map((p) => msg(p, '')).join('; ');
      } else if (ref.params[name] !== undefined) {
        params[name] = ref.params[name];
      } else {
        return english;
      }
    }
    return fill(template, params);
  };
  /** The age chip ("1d old", "1 дн. назад") as a pattern: never shown beside a stated reason (U1). */
  const ageChip = new RegExp(t('results.staleAge').replace(/[.*+?^$()|[\]\\]/g, '\\$&').replace('{days}', '\\d+'));
  return { locale, t, tf, tn, msg, ageChip };
}
type Words = ReturnType<typeof wordsFor>;

// ------------------------------------------------------------------ the run

interface Journey {
  profileId: string;
  run: RunView & { settings: Record<string, unknown> };
  rows: Record<Case, ProgramResult>;
  catalogue: Record<Case, UniversityCandidate>;
  catalogueTotal: number;
  kbTotal: number;
  verifiedTotal: number;
}

let journey: Journey;
const external: string[] = [];
const pageErrors: string[] = [];

async function json<T>(request: APIRequestContext, method: 'GET' | 'POST', url: string, data?: unknown): Promise<T> {
  const response = method === 'GET' ? await request.get(url) : await request.post(url, { data: data ?? {} });
  expect(response.ok(), `${method} ${url} → ${response.status()} ${await response.text()}`).toBe(true);
  return (await response.json()) as T;
}

async function settle(request: APIRequestContext, runId: string): Promise<RunView> {
  let run: RunView | undefined;
  await expect
    .poll(async () => {
      run = await json<RunView>(request, 'GET', `/api/runs/${runId}`);
      return run.job_running ? 'running' : run.stage;
    }, { timeout: 90_000, intervals: [500] })
    .toMatch(/^(completed|awaiting_user_decision|failed|cancelled)$/);
  return run!;
}

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ request }) => {
  const profile = await json<{ id: string }>(request, 'POST', '/api/profiles', DEFAULT_PROFILE);
  const catalogue = {} as Record<Case, UniversityCandidate>;
  let page: UniversityCatalogue | undefined;
  for (const [id, name] of Object.entries(CASES) as [Case, string][]) {
    page = await json<UniversityCatalogue>(
      request, 'GET', `/api/universities?q=${encodeURIComponent(name)}&limit=5&profile_id=${profile.id}`,
    );
    const hit = page.items.find((u) => u.name === name);
    expect(hit, `${name} is in the catalogue`).toBeTruthy();
    catalogue[id] = hit!;
  }
  const verified = await json<UniversityCatalogue>(request, 'GET', `/api/universities?verified=true&limit=1&profile_id=${profile.id}`);

  const started = await json<RunView>(request, 'POST', '/api/runs', {
    profile_id: profile.id,
    university_ids: Object.keys(CASES).map((id) => catalogue[id as Case].id),
  });
  await settle(request, started.id);
  // The smoke's step 4: approve every row, then collect documents.
  const first = await json<ProgramResult[]>(request, 'GET', `/api/runs/${started.id}/results`);
  for (const row of first) {
    await json(request, 'POST', `/api/runs/${started.id}/results/${row.id}/decision`, { decision: 'approved' });
  }
  await json(request, 'POST', `/api/runs/${started.id}/collect-documents`);
  await expect
    .poll(async () => (await json<ProgramResult[]>(request, 'GET', `/api/runs/${started.id}/results`))
      .filter((r) => r.checklist).length, { timeout: 90_000, intervals: [500] })
    .toBeGreaterThan(0);
  const run = (await settle(request, started.id)) as Journey['run'];
  const results = await json<ProgramResult[]>(request, 'GET', `/api/runs/${started.id}/results`);
  const rows = {} as Record<Case, ProgramResult>;
  for (const [id, name] of Object.entries(CASES) as [Case, string][]) {
    const row = results.find((r) => r.university === name);
    expect(row, `${name} has a result row`).toBeTruthy();
    rows[id] = row!;
  }
  journey = {
    profileId: profile.id,
    run,
    rows,
    catalogue,
    catalogueTotal: page!.catalogue_total,
    kbTotal: page!.kb_total ?? -1,
    verifiedTotal: verified.total,
  };
});

// ------------------------------------------------------------------ helpers

async function openPage(browser: Browser, locale: Locale, route: string): Promise<Page> {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.addInitScript(({ runId, profileId, loc }) => {
    window.localStorage.setItem('ashyq.activeRun', runId);
    window.localStorage.setItem('ashyq.activeProfile', profileId);
    window.localStorage.setItem('ashyq.locale', loc);
  }, { runId: journey.run.id, profileId: journey.profileId, loc: locale });
  // The smokes' browser fence: nothing leaves localhost, and anything that tries is counted.
  await context.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === '127.0.0.1' || url.hostname === 'localhost') return route.continue();
    external.push(`${locale}: ${url.href}`);
    return route.abort();
  });
  const page = await context.newPage();
  page.on('pageerror', (error) => pageErrors.push(`${locale} ${route}: ${error.message}`));
  await page.goto(route);
  return page;
}

function claimsOf(row: ProgramResult, type: string): ClaimOut[] {
  return row.claims.filter((c) => c.claim_type === type);
}

function question(row: ProgramResult, key: string) {
  const found = row.unresolved.find((q) => q.question_message?.key === key);
  expect(found, `${row.university} asks ${key}`).toBeTruthy();
  return found!;
}

/** The localised caveat of a claim, as `localCaveat` says it. */
function caveatOf(w: Words, claim: ClaimOut): string {
  const english = caveatText(claim.notes);
  expect(english, `${claim.claim_type} carries a caveat`).toBeTruthy();
  return w.msg(claim.caveat_message, english!);
}

/** The localised stale reason of a claim, as `localStaleReason` says it. */
function staleOf(w: Words, claim: ClaimOut): string {
  const english = staleReason(claim.notes);
  expect(english, `${claim.claim_type} says why it is not current`).toBeTruthy();
  const keyed = claim.stale_messages ?? [];
  const pieces = english!.split('; ');
  if (w.locale === 'en' || pieces.length !== keyed.length) return english!;
  return pieces.map((piece, i) => w.msg(keyed[i], piece)).join('; ');
}

async function text(locator: Locator): Promise<string> {
  return (await locator.innerText()).replace(/\s+/g, ' ');
}

async function openCard(page: Page, row: ProgramResult) {
  const card = page.getByTestId(`card-${row.id}`);
  await card.getByTestId(`card-expand-${row.id}`).click();
  const detail = card.getByTestId(`detail-${row.id}`);
  await expect(detail).toBeVisible();
  const tab = async (name: 'requirements' | 'costs' | 'documents' | 'sources') => {
    await detail.getByTestId(`tab-${name}`).click();
    await expect(detail.getByTestId(`tab-${name}`)).toHaveAttribute('aria-selected', 'true');
    return detail;
  };
  return { card, detail, tab, close: () => card.getByTestId(`card-expand-${row.id}`).click() };
}

/** Occurrences of `needle` in `haystack`. */
function count(haystack: string, needle: string): number {
  return haystack.split(needle).length - 1;
}

// ------------------------------------------------------------------ the checks

test('the run stays in kb mode and off the network', async () => {
  const { run, rows } = journey;
  expect(run.stage).toBe('completed');
  expect(run.errors).toEqual([]);
  expect(run.pages_checked).toBe(0);
  expect(run.fetch_tiers).toEqual({ fixture: 0, http: 0, browser: 0, pdf: 0 });
  expect(run.settings.knowledge_mode).toBe('kb');
  expect(String(run.settings.knowledge_base)).toMatch(/kb-cs-bachelor/);
  expect(Object.values(rows).every((r) => r.user_decision === 'approved')).toBe(true);
  // The cases the universities were chosen for are still cases on the committed KB.
  expect(rows.oxford.deadline_passed).toBe(true);
  expect(rows.fudan.checklist?.completeness).toBe('partial');
  expect(rows.fudan.checklist?.unresolved.length).toBeGreaterThan(0);
  expect(rows.sheffield.checklist).toBeFalsy();
  expect(rows.groningen.unresolved.some((q) => q.blocking && q.question_message?.key === 'question.noVerifiedDataInScope')).toBe(true);
  expect(claimsOf(rows.kyoto, 'tuition').some((c) => c.caveat_message?.key === 'caveat.feePolicy')).toBe(true);
  expect(Object.keys(rows.kyoto.costs.items)).toContain('tuition');
  expect(rows.sheffield.costs.items.tuition?.range_low).toBeTruthy();
  // U6, server side: "instead" only where another language is named.
  expect(rows.eth.unresolved.some((q) => q.question_message?.key === 'question.languageInstead')).toBe(true);
  for (const row of [rows.stanford, rows.kyoto]) {
    expect(row.unresolved.some((q) => q.question_message?.key === 'question.languageInstead')).toBe(false);
    question(row, 'question.languageNoneRecorded');
  }
  // D4, server side: the step says "~1 day".
  expect(rows.edinburgh.checklist?.ordered_steps.join('\n')).toContain('(allow ~1 day)');
  expect(rows.edinburgh.checklist?.ordered_steps.join('\n')).not.toContain('~1 days');
});

for (const locale of LOCALES) {
  test(`${locale}: the catalogue shows each university's verified knowledge and filters on it`, async ({ browser }) => {
    const w = wordsFor(locale);
    const { catalogue } = journey;
    const page = await openPage(browser, locale, '/#/shortlist');
    await page.locator('details.catalogue-expand > summary').filter({ hasText: w.t('shortlist.exploreCatalogue') }).click();
    const region = page.getByRole('region', { name: 'University catalogue' });
    await expect(region).toContainText(w.tf('catalogue.kb.coverage', { n: journey.kbTotal, total: journey.catalogueTotal }));
    const search = region.getByRole('searchbox');
    const cardOf = (name: string) => region.locator('article.catalogue-card').filter({ has: page.getByText(name, { exact: true }) });

    // KTH: related programme only, a fee per programme with its caveat.
    await search.fill('KTH');
    const kth = cardOf(CASES.kth);
    const kthKnowledge = catalogue.kth.knowledge!;
    await expect(kth).toContainText(w.t('catalogue.kb.chip'));
    await expect(kth).toContainText(w.tf('catalogue.kb.answers', { n: kthKnowledge.core_answered }));
    await expect(kth).toContainText(w.tn('catalogue.kb.documents', kthKnowledge.documents));
    expect(kthKnowledge.programme_page).toBe('related_only');
    await expect(kth).toContainText(w.t('catalogue.kb.programme.related_only'));
    await expect(kth).toContainText(w.tf('detail.fee.perPeriod', {
      amount: '453,000 SEK', period: w.tf('detail.fee.period.programme', { n: 3 }),
    }));
    await expect(kth).toContainText(w.tf('results.caveat', { caveat: w.msg(kthKnowledge.tuition!.caveat_message, kthKnowledge.tuition!.caveat!) }));

    // Stanford: last year's fee, not current, with its reason and the stale count.
    await search.fill('Stanford');
    const stanford = cardOf(CASES.stanford);
    const fee = catalogue.stanford.knowledge!.tuition!;
    expect(fee.stale).toBe(true);
    await expect(stanford).toContainText(w.t('results.staleNoAge'));
    await expect(stanford).toContainText(w.tf('results.notCurrent', { reason: w.msg(fee.stale_messages[0], fee.stale_reasons[0]!) }));
    await expect(stanford).toContainText(w.tn('catalogue.kb.staleCount', catalogue.stanford.knowledge!.stale_count));

    // Oxford: no fee in the KB.
    await search.fill('Oxford');
    await expect(cardOf(CASES.oxford)).toContainText(w.t('catalogue.kb.noFee'));

    // Groningen: outside the KB, and gone once the filter is on.
    await search.fill('Groningen');
    await expect(cardOf(CASES.groningen)).toContainText(w.t('catalogue.kb.none'));
    await region.getByRole('checkbox', { name: w.t('catalogue.kb.filter') }).check();
    await expect(region).toContainText('No universities match these filters.');
    await search.fill('');
    await expect(region.getByRole('status')).toHaveText(`${journey.verifiedTotal} universities found`);
    expect(journey.verifiedTotal).toBe(journey.kbTotal);
    await page.context().close();
  });

  test(`${locale}: the shortlist cards, the four detail tabs and the documents screen`, async ({ browser }) => {
    const w = wordsFor(locale);
    const { rows } = journey;
    const page = await openPage(browser, locale, '/#/shortlist');
    await expect(page.getByTestId(`card-${rows.edinburgh.id}`)).toBeVisible();

    // F3: the header names the knowledge base (English-only chip).
    await expect(page.locator('header').first()).toContainText('Verified knowledge base');
    await expect(page.locator('header').first()).not.toContainText('Live sources');

    // The cards: never a probability next to the ranking.
    expect(await text(page.locator('.find-results'))).not.toMatch(/%|chance|probabilit|шанс|вероятност|ықтимал/i);

    // U2: Oxford's passed deadline is flagged on its card.
    const oxfordCard = page.getByTestId(`card-${rows.oxford.id}`);
    await expect(oxfordCard.locator('.find-card__facts').getByTestId('deadline-passed')).toHaveText(w.t('detail.deadlinePassed'));
    // D6: Fudan's card counts its checklist's question too.
    const fudanQuestions = rows.fudan.unresolved.length + (rows.fudan.checklist?.unresolved.length ?? 0);
    await expect(page.getByTestId(`card-${rows.fudan.id}`).locator('.find-card__caution'))
      .toContainText(w.tn('results.questionCount', fudanQuestions));

    // ---- Oxford: passed deadline in the hero (U2), no fee (U8), access unknowns (WHY-1).
    {
      const { detail, tab, close } = await openCard(page, rows.oxford);
      await expect(detail.locator('.programme-facts').getByTestId('deadline-passed')).toHaveText(w.t('detail.deadlinePassed'));
      await tab('requirements');
      const access = rows.oxford.kb_unknown!.filter((u) => u.kind === 'access' && ['english', 'gpa', 'deadline'].includes(u.question));
      await expect(detail.getByTestId('kb-unknown-requirements')).toContainText(w.tf('detail.kbUnknown.access', {
        fields: access.map((u) => w.t(`detail.kbUnknown.field.${u.question}` as ResultsKey)).join(', '),
      }));
      await expect(detail).toContainText(w.t('detail.deadlinePassed'));
      await tab('costs');
      await expect(detail).toContainText(w.t('detail.noCostKb'));
      await expect(detail).toContainText(w.msg(rows.oxford.funding_gap!.reason_message, rows.oxford.funding_gap!.reason));
      await expect(detail.getByTestId('kb-unknown-costs')).toContainText(w.tf('detail.kbUnknown.access', { fields: w.t('detail.kbUnknown.field.tuition') }));
      expect(await text(detail)).not.toContain('Cost pages could not be verified');
      await tab('documents');
      await expect(detail).toContainText(w.t('detail.docs.kb.official'));
      await tab('sources');
      const deadline = claimsOf(rows.oxford, 'admission_deadline')[0]!;
      expect(deadline.status).toBe('POSSIBLY_STALE');
      await expect(detail).toContainText(w.tf('results.notCurrent', { reason: staleOf(w, deadline) }));
      await expect(detail).toContainText(w.tf('results.caveat', { caveat: caveatOf(w, deadline) }));
      expect(await text(detail)).not.toMatch(w.ageChip);
      await close();
    }

    // ---- Stanford: caveated deadline, "no other language recorded" (U6), a fee for another year.
    {
      const { detail, tab, close } = await openCard(page, rows.stanford);
      await tab('requirements');
      const deadline = claimsOf(rows.stanford, 'admission_deadline')[0]!;
      await expect(detail.getByTestId('deadline-caveat')).toHaveText(w.tf('results.caveat', { caveat: caveatOf(w, deadline) }));
      const none = question(rows.stanford, 'question.languageNoneRecorded');
      await expect(detail.getByTestId('requirement-questions')).toContainText(w.msg(none.question_message, none.question));
      // The "instead" question, with its statement left out: not asked here.
      const instead = fill(w.t('msg.question.languageInstead'), { statement: '', university: rows.stanford.university }).trim();
      expect(await text(detail.getByTestId('requirement-questions'))).not.toContain(instead);
      const gpa = rows.stanford.kb_unknown!.find((u) => u.question === 'gpa' && u.kind === 'not_published')!;
      await expect(detail.getByTestId('kb-unknown-requirements')).toContainText(w.tf('detail.kbUnknown.notPublished', {
        fields: w.t('detail.kbUnknown.field.gpa'), date: gpa.checked_on!,
      }));
      await tab('costs');
      const tuition = claimsOf(rows.stanford, 'tuition')[0]!;
      await expect(detail.getByTestId('unused-tuition')).toContainText(w.tf('detail.fee.notCurrent', { reason: staleOf(w, tuition) }));
      await tab('sources');
      await expect(detail).toContainText(w.t('results.staleNoAge'));
      expect(await text(detail)).not.toMatch(w.ageChip);
      await close();
    }

    // ---- ETH: standing fee per semester (U4), "which certificate instead" (U6), caveat chip.
    {
      const { detail, tab, close } = await openCard(page, rows.eth);
      await tab('requirements');
      const instead = question(rows.eth, 'question.languageInstead');
      await expect(detail.getByTestId('requirement-questions')).toContainText(w.msg(instead.question_message, instead.question));
      await tab('costs');
      const perSemester = w.tf('detail.fee.perPeriod', { amount: '2,190 CHF', period: w.t('detail.fee.period.semester') });
      await expect(detail.getByTestId('unused-tuition')).toContainText(perSemester);
      await expect(detail.getByTestId('unused-tuition')).toContainText(w.tf('detail.fee.notYearly', { period: w.t('detail.fee.period.semester') }));
      // The gap reason lists the same fee in the same words ({fees}, U4).
      expect(count(await text(detail), perSemester)).toBeGreaterThanOrEqual(2);
      if (locale !== 'en') expect(await text(detail)).not.toContain('per semester');
      await tab('sources');
      const fee = claimsOf(rows.eth, 'tuition')[0]!;
      expect(fee.status).toBe('VERIFIED_CURRENT');
      await expect(detail).toContainText(w.t('results.currentWithCaveat'));
      await expect(detail.getByTestId('claim-caveat').first()).toHaveText(w.tf('results.caveat', { caveat: caveatOf(w, fee) }));
      await close();
    }

    // ---- KTH: related-only route (REL-1), fee per programme (U4).
    {
      const { detail, tab, close } = await openCard(page, rows.kth);
      await tab('requirements');
      const related = question(rows.kth, 'question.programmeRelatedOnly');
      expect(related.blocking).toBe(false);
      await expect(detail.getByTestId('requirement-questions')).toContainText(w.msg(related.question_message, related.question));
      await expect(detail.getByTestId('requirement-questions')).toContainText(w.msg(related.why_message, related.why_it_matters));
      await tab('costs');
      const perProgramme = w.tf('detail.fee.perPeriod', { amount: '453,000 SEK', period: w.tf('detail.fee.period.programme', { n: 3 }) });
      expect(count(await text(detail), perProgramme)).toBeGreaterThanOrEqual(2);
      if (locale !== 'en') expect(await text(detail)).not.toContain('full programme');
      await close();
    }

    // ---- Kyoto: a standing yearly fee in the cost table, with its caveat (U3).
    {
      const { detail, tab, close } = await openCard(page, rows.kyoto);
      await tab('costs');
      const fee = claimsOf(rows.kyoto, 'tuition').find((c) => c.caveat_message)!;
      await expect(detail.getByTestId('cost-caveat')).toHaveText(w.tf('detail.costCaveat', { caveat: caveatOf(w, fee) }));
      await tab('requirements');
      const none = question(rows.kyoto, 'question.languageNoneRecorded');
      await expect(detail.getByTestId('requirement-questions')).toContainText(w.msg(none.question_message, none.question));
      await close();
    }

    // ---- Fudan: another cycle's list — "not current" with its reason (U1), the kb chip (D3),
    //      conditions (D1), localised steps (U5), the checklist question (D6's other half).
    {
      const { detail, tab, close } = await openCard(page, rows.fudan);
      await expect(detail.locator('.programme-facts')).toContainText(w.tn('results.questionCount', fudanQuestions));
      await tab('documents');
      const checklist = rows.fudan.checklist!;
      await expect(detail).toContainText(w.t('detail.docs.kb.partial'));
      expect(await text(detail)).not.toContain(w.t('detail.docs.partial'));
      const items = detail.getByTestId('document-item');
      await expect(items).toHaveCount(checklist.admission_documents.length + checklist.scholarship_documents.length);
      const stale = claimsOf(rows.fudan, 'required_document').find((c) => c.is_stale)!;
      await expect(items.first()).toContainText(w.t('results.staleNoAge'));
      await expect(items.first()).toContainText(w.tf('results.notCurrent', { reason: staleOf(w, stale) }));
      expect(await text(detail)).not.toMatch(w.ageChip);
      const conditional = claimsOf(rows.fudan, 'required_document')
        .map((c) => c.normalized_value as { requirement?: string; condition?: string } | string)
        .find((v): v is { requirement: string; condition: string } => typeof v === 'object' && v.requirement === 'conditional')!;
      await expect(detail).toContainText(w.t('detail.docs.conditional'));
      await expect(detail).toContainText(w.tf('detail.docs.condition', { condition: conditional.condition.replace(/\.$/, '') }));
      await expect(detail).toContainText(`${w.t('detail.docs.step.school')}: Secondary school diploma (certified copy) (${w.tn('detail.docs.leadTime', 21)})`);
      const listQuestion = checklist.unresolved[0]!;
      await expect(detail.getByTestId('document-questions')).toContainText(w.msg(listQuestion.question_message, listQuestion.question));
      await close();
    }

    // ---- Edinburgh: a full current checklist (D1, D3), a one-day step (D4), owners (U5), no fee (U8).
    {
      const { detail, tab, close } = await openCard(page, rows.edinburgh);
      await tab('documents');
      const checklist = rows.edinburgh.checklist!;
      await expect(detail).toContainText(w.t('detail.docs.kb.official'));
      const items = detail.getByTestId('document-item');
      await expect(items).toHaveCount(checklist.admission_documents.length + checklist.scholarship_documents.length);
      for (let i = 0; i < (await items.count()); i += 1) {
        const item = items.nth(i);
        await expect(item.locator('a[href^="http"]')).toHaveCount(1);
        expect(await text(item)).toMatch(new RegExp([
          w.t('detail.docs.required'), w.t('detail.docs.optional'), w.t('detail.docs.conditional'),
        ].map((s) => s.replace(/[.*+?^$()|[\]\\]/g, '\\$&')).join('|')));
      }
      const all = await text(detail);
      expect(count(all, w.t('detail.docs.owner.recommender'))).toBeGreaterThan(0);
      await expect(detail).toContainText(w.t('detail.docs.order'));
      await expect(detail).toContainText(`${w.t('detail.docs.step.applicant')}: Passport identity page (copy) (${w.tn('detail.docs.leadTime', 1)})`);
      await expect(detail).toContainText(`${w.t('detail.docs.step.recommender')}: Academic reference (${w.tn('detail.docs.leadTime', 30)})`);
      expect(all).not.toContain('~1 days');
      if (locale !== 'en') expect(all).not.toMatch(/(^|\s)(You|Your school|Your referee|A third party): /);
      await tab('costs');
      await expect(detail).toContainText(w.t('detail.noCostKb'));
      expect(await text(detail)).not.toContain('Cost pages could not be verified');
      await close();
    }

    // ---- Sheffield: a fee published as a range; approved, no KB list — the tab says why (D2).
    {
      const { detail, tab, close } = await openCard(page, rows.sheffield);
      await tab('costs');
      const tuition = rows.sheffield.costs.items.tuition!;
      const range = `${tuition.range_low!.toLocaleString('en-US')}–${tuition.range_high!.toLocaleString('en-US')} ${tuition.currency}`;
      await expect(detail).toContainText(w.tf('detail.fee.range', { range }));
      const rangeWarning = rows.sheffield.funding_gap!.warning_messages!.findIndex((m) => m?.key === 'gap.kbTuitionRange');
      expect(rangeWarning).toBeGreaterThanOrEqual(0);
      await expect(detail).toContainText(w.msg(
        rows.sheffield.funding_gap!.warning_messages![rangeWarning], rows.sheffield.funding_gap!.warnings[rangeWarning]!,
      ));
      await tab('documents');
      const documents = question(rows.sheffield, 'question.documents');
      expect(documents.why_message?.key).toBe('why.kbNoDocuments');
      await expect(detail.getByTestId('document-questions')).toContainText(w.msg(documents.question_message, documents.question));
      await expect(detail.getByTestId('document-questions')).toContainText(w.msg(documents.why_message, documents.why_it_matters));
      expect(await text(detail)).not.toContain(w.t('detail.documentsLater').slice(0, 30));
      await close();
    }

    // ---- Groningen: outside the KB — the document question gives that reason (D5).
    {
      const { detail, tab, close } = await openCard(page, rows.groningen);
      await tab('documents');
      const documents = question(rows.groningen, 'question.documents');
      expect(documents.why_message?.key).toBe('why.noKbEntry');
      await expect(detail.getByTestId('document-questions')).toContainText(w.msg(documents.why_message, documents.why_it_matters));
      expect(await text(detail)).not.toContain(w.t('msg.why.kbNoDocuments'));
      await tab('sources');
      const missing = question(rows.groningen, 'question.noVerifiedDataInScope');
      await expect(detail).toContainText(w.msg(missing.question_message, missing.question));
      await tab('requirements');
      await tab('costs');
      await expect(detail).toContainText(w.t('detail.noCostKb'));
      await close();
    }

    // ---- The Documents screen, in the locale (I18N-2): the kb chip (D3) and "~1 day" (D4).
    await page.getByTestId('nav-documents').click();
    const withChecklists = Object.values(rows).filter((r) => r.checklist);
    for (const row of withChecklists) await expect(page.getByTestId(`doc-tab-${row.id}`)).toBeVisible();
    await expect(page.getByTestId(`doc-tab-${rows.sheffield.id}`)).toHaveCount(0);
    await page.getByTestId(`doc-tab-${rows.fudan.id}`).click();
    await expect(page.locator('main')).toContainText(w.t('detail.docs.kb.partial'));
    await page.getByTestId(`doc-tab-${rows.edinburgh.id}`).click();
    await expect(page.locator('main')).toContainText(w.t('detail.docs.kb.official'));
    await expect(page.locator('main')).toContainText(w.tn('detail.docs.leadTime', 1));
    const screen = await text(page.locator('main'));
    expect(screen).not.toContain(w.t('documents.completeness.partial'));
    expect(screen).not.toContain('~1 days');
    await page.context().close();
  });
}

test('the browser made no external request, no page failed, and the guard blocked nothing', async () => {
  expect(external).toEqual([]);
  expect(pageErrors).toEqual([]);
  const log = readFileSync(NETGUARD_LOG, 'utf8').split('\n').filter(Boolean);
  // The probe proved the guard blocks before anything started ...
  expect(log).toContain('PROBE blocked');
  // ... the guard was loaded in the API and the worker ...
  expect(log.some((line) => line.startsWith('LOADED') && line.includes('uvicorn'))).toBe(true);
  expect(log.some((line) => line.startsWith('LOADED') && line.includes('app.jobs.worker'))).toBe(true);
  // ... and nothing else tried to leave the machine.
  expect(log.filter((line) => line.startsWith('BLOCKED') && !line.includes('netguard-probe.invalid'))).toEqual([]);
});

# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth-journey.spec.ts >> signing in again finds the work still there
- Location: e2e/auth-journey.spec.ts:77:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.find-card').first()
Expected: visible
Timeout: 20000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 20000ms
  - waiting for locator('.find-card').first()

```

```yaml
- complementary:
  - text: Unimatch
  - navigation "Main navigation":
    - button "Home"
    - button "Find"
    - button "Plan"
    - button "Documents"
    - button "Community"
  - paragraph:
    - text: Same students.
    - strong: Bigger horizons.
  - group: Preferences
- banner:
  - text: Demo data
  - group: Explore⌄
  - text: Applicant
  - combobox "Applicant":
    - option "New applicant" [selected]
    - option "Demo Applicant (synthetic) · 1 run"
  - button "New case"
  - button "Settings"
  - button "Sign out"
- main:
  - paragraph: FIND YOUR PATH
  - heading "Find your best matches." [level=1]
  - paragraph: Research begins with your profile and preferences.
  - paragraph: No results yet
  - text: Start research to find programmes supported by available sources.
  - button "Start research →"
  - region "University catalogue":
    - paragraph: EXPLORE UNIVERSITIES
    - heading "Find a place to begin." [level=2]
    - paragraph: Browse 501 universities, even when live research is unavailable. Select up to 5 to check against your profile.
    - text: 500 imported universities University, city or country
    - searchbox "University, city or country"
    - text: Country or region
    - combobox "Country or region":
      - option "All countries" [selected]
      - option "Europe"
      - option "Asia"
      - option "North America"
      - option "South America"
      - option "Oceania"
      - option "Africa"
      - option "Argentina"
      - option "Australia"
      - option "Austria"
      - option "Belgium"
      - option "Brazil"
      - option "Brunei Darussalam"
      - option "Canada"
      - option "Chile"
      - option "China"
      - option "Colombia"
      - option "Costa Rica"
      - option "Czechia"
      - option "Denmark"
      - option "Egypt"
      - option "Estonia"
      - option "Finland"
      - option "France"
      - option "Germany"
      - option "Greece"
      - option "Hong Kong"
      - option "India"
      - option "Indonesia"
      - option "Iran"
      - option "Ireland"
      - option "Israel"
      - option "Italy"
      - option "Japan"
      - option "Jordan"
      - option "Kazakhstan"
      - option "Lebanon"
      - option "Lithuania"
      - option "Luxembourg"
      - option "Macao"
      - option "Malaysia"
      - option "Mexico"
      - option "Netherlands"
      - option "New Zealand"
      - option "Norway"
      - option "Oman"
      - option "Pakistan"
      - option "Peru"
      - option "Philippines"
      - option "Poland"
      - option "Portugal"
      - option "Qatar"
      - option "Russia"
      - option "Saudi Arabia"
      - option "Singapore"
      - option "South Africa"
      - option "South Korea"
      - option "Spain"
      - option "Sweden"
      - option "Switzerland"
      - option "Taiwan"
      - option "Thailand"
      - option "Turkey"
      - option "United Arab Emirates"
      - option "United Kingdom"
      - option "United States"
      - option "Uzbekistan"
    - button "Complete profile to research"
    - paragraph: These are university candidates. Your requested programme, admission requirements, tuition and scholarships still need official verification. Missing information never means you are ineligible.
    - status: 501 universities found
    - article:
      - checkbox "Aalto University" [disabled]
      - strong: Aalto University
      - paragraph: Espoo · Finland
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #126 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Charles University" [disabled]
      - strong: Charles University
      - paragraph: Prague · Czechia
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #273 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Delft University of Technology" [disabled]
      - strong: Delft University of Technology
      - paragraph: Delft · Netherlands
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #48 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "KAIST" [disabled]
      - strong: KAIST
      - paragraph: Daejeon · South Korea
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #65 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Masaryk University" [disabled]
      - strong: Masaryk University
      - paragraph: Brno · Czechia
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #454 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Middle East Technical University" [disabled]
      - strong: Middle East Technical University
      - paragraph: Ankara · Turkey
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #305 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Nanyang Technological University" [disabled]
      - strong: Nanyang Technological University
      - paragraph: Singapore · Singapore
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #12 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Nazarbayev University" [disabled]
      - strong: Nazarbayev University
      - paragraph: Astana · Kazakhstan
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - group: Imported data & sources
    - article:
      - checkbox "Politecnico di Milano" [disabled]
      - strong: Politecnico di Milano
      - paragraph: Milan · Italy
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #87 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Sabanci University" [disabled]
      - strong: Sabanci University
      - paragraph: Istanbul · Turkey
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #357 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Technical University of Munich" [disabled]
      - strong: Technical University of Munich
      - paragraph: Munich · Germany
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #25 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "The University of Hong Kong" [disabled]
      - strong: The University of Hong Kong
      - paragraph: Hong Kong · Hong Kong
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #11 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "University of British Columbia" [disabled]
      - strong: University of British Columbia
      - paragraph: Vancouver · Canada
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #45 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "University of Groningen" [disabled]
      - strong: University of Groningen
      - paragraph: Groningen · Netherlands
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #157 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "University of Tartu" [disabled]
      - strong: University of Tartu
      - paragraph: Tartu · Estonia
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #367 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "University of Toronto" [disabled]
      - strong: University of Toronto
      - paragraph: Toronto · Canada
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #32 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "University of Vienna" [disabled]
      - strong: University of Vienna
      - paragraph: Vienna · Austria
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #140 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "University of Warsaw" [disabled]
      - strong: University of Warsaw
      - paragraph: Warsaw · Poland
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #289 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Vilnius University" [disabled]
      - strong: Vilnius University
      - paragraph: Vilnius · Lithuania
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #465 · imported ranking"
      - group: Imported data & sources
    - article:
      - checkbox "Aalborg University" [disabled]
      - strong: Aalborg University
      - paragraph: Aalborg · Denmark
      - text: Programme verification needed
      - term: Admission fit
      - definition: Not assessed
      - term: Tuition & funding
      - definition: Research required
      - paragraph: "QS 2027: #329 · imported ranking"
      - group: Imported data & sources
    - navigation "University catalogue pages":
      - button "Previous" [disabled]
      - text: 1–20 of 501
      - button "Next"
```

# Test source

```ts
  1  | import { expect, test, type Browser, type Page } from '@playwright/test';
  2  | 
  3  | const SHOT_ROOT = '../docs/screenshots';
  4  | 
  5  | /**
  6  |  * Screenshot path for the current project.
  7  |  *
  8  |  * Both projects run the same specs, so without namespacing the mobile run
  9  |  * silently overwrites the desktop captures with narrow-layout versions.
  10 |  */
  11 | export function shot(name: string): string {
  12 |   const project = test.info().project.name;
  13 |   return project === 'desktop-chromium'
  14 |     ? `${SHOT_ROOT}/${name}`
  15 |     : `${SHOT_ROOT}/mobile/${name}`;
  16 | }
  17 | 
  18 | /**
  19 |  * One browser page shared across a spec file.
  20 |  *
  21 |  * The research pipeline is the slow part, and re-running it per test would
  22 |  * turn a 30-second suite into a 10-minute one while testing nothing extra.
  23 |  * Sharing a page also mirrors how the product is actually used: one session
  24 |  * that walks the workflow from profile to export.
  25 |  */
  26 | export async function newSession(browser: Browser): Promise<Page> {
  27 |   // browser.newContext() ignores the project's `use` block, so the viewport and
  28 |   // device settings have to be carried across explicitly - otherwise the
  29 |   // desktop project silently renders at the default 1280x720 and the mobile
  30 |   // project loses its device emulation entirely.
  31 |   const { viewport, userAgent, deviceScaleFactor, isMobile, hasTouch } = test.info().project.use;
  32 |   const context = await browser.newContext({
  33 |     ...(viewport !== undefined ? { viewport } : {}),
  34 |     ...(userAgent ? { userAgent } : {}),
  35 |     ...(deviceScaleFactor ? { deviceScaleFactor } : {}),
  36 |     ...(isMobile !== undefined ? { isMobile } : {}),
  37 |     ...(hasTouch !== undefined ? { hasTouch } : {}),
  38 |   });
  39 |   return context.newPage();
  40 | }
  41 | 
  42 | export async function waitForResults(page: Page, timeout = 120_000): Promise<void> {
  43 |   await expect(page.getByTestId('stage-list')).toBeVisible({ timeout: 20_000 });
  44 |   await expect(page.getByTestId('to-shortlist')).toBeVisible({ timeout });
  45 | }
  46 | 
  47 | export async function runDemoResearch(page: Page): Promise<void> {
  48 |   await page.goto('/#/profile');
  49 |   await page.getByTestId('load-demo-profile').click();
  50 |   await page.goto('/#/preferences');
  51 |   await expect(page.getByTestId('start-research')).toBeEnabled();
  52 |   await page.getByTestId('start-research').click();
  53 |   await waitForResults(page);
  54 | }
  55 | 
  56 | export async function openShortlist(page: Page): Promise<void> {
  57 |   await page.goto('/#/shortlist');
> 58 |   await expect(page.locator('.find-card').first()).toBeVisible();
     |                                                    ^ Error: expect(locator).toBeVisible() failed
  59 |   const advanced = page.locator('.find-advanced');
  60 |   if (!(await advanced.evaluate((element: HTMLDetailsElement) => element.open))) await advanced.locator('summary').first().click();
  61 |   await expect(page.getByTestId('shortlist-table')).toBeVisible();
  62 | 
  63 |   // Out-of-budget, needs-clarification and excluded rows sit in sections that
  64 |   // are collapsed by design - the ranked table is the answer to "where can I
  65 |   // go", not "what exists". The journey asserts on rows from all of them, so
  66 |   // it opens every section rather than each test remembering to.
  67 |   const sections = page.locator('details[data-testid^="section-"]');
  68 |   for (let i = 0; i < (await sections.count()); i += 1) {
  69 |     const section = sections.nth(i);
  70 |     if (!(await section.evaluate((el: HTMLDetailsElement) => el.open))) {
  71 |       await section.locator('summary').click();
  72 |     }
  73 |   }
  74 | }
  75 | 
  76 | /** The shortlist row whose university cell carries `name`. */
  77 | export function rowFor(page: Page, name: string) {
  78 |   return page
  79 |     .locator('tbody tr')
  80 |     .filter({ has: page.getByRole('button', { name, exact: true }) })
  81 |     .first();
  82 | }
  83 | 
  84 | export async function expandRow(page: Page, name: string) {
  85 |   const row = rowFor(page, name);
  86 |   await expect(row).toBeVisible();
  87 |   if ((page.viewportSize()?.width ?? 0) <= 700) {
  88 |     const card = page.locator('.find-card').filter({ has: page.getByRole('heading', { name, exact: true }) }).first();
  89 |     await card.getByRole('button', { name: 'View details' }).click();
  90 |     return row;
  91 |   }
  92 |   await row.getByRole('button', { name, exact: true }).click();
  93 |   return row;
  94 | }
  95 | 
```
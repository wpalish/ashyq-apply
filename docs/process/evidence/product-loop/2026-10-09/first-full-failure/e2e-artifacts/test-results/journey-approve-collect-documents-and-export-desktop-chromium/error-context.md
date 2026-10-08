# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journey.spec.ts >> approve, collect documents, and export
- Location: e2e/journey.spec.ts:189:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('2 approved')
Expected: visible
Timeout: 20000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 20000ms
  - waiting for getByText('2 approved')

```

```yaml
- complementary:
  - text: Unimatch
  - navigation "Main navigation":
    - button "Home"
    - button "Find 20"
    - button "Plan 2"
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
    - option "New applicant"
    - option "Demo Applicant (synthetic) · 0 runs" [selected]
    - option "Demo Applicant (synthetic) · 1 run"
  - button "New case"
  - button "Settings"
  - button "Sign out"
- main:
  - paragraph: Your application journey
  - heading "A clearer plan. A brighter you." [level=1]
  - paragraph: Keep your chosen programmes together, check their deadlines and prepare what each one asks for. These are your choices, not admission offers.
  - region "Your next step":
    - text: NEXT STEP
    - 'heading "Next deadline: KU Leuven" [level=2]'
    - paragraph: Mar 01, 2027 · BSc Informatics
    - strong: "2"
    - text: programmes in your plan
  - text: 2 chosen by you 0 considering 0 ruled out 18 undecided
  - button "Collect documents for 2 programmes"
  - heading "Chosen by you (2)" [level=2]
  - text: University of Groningen BSc Computing Science · Groningen, Netherlands Chosen by you
  - button "Undo"
  - text: Pending Full ride remaining 1,848 USD · 2026/27 deadline May 01, 2027 KU Leuven BSc Informatics · Leuven, Belgium Chosen by you
  - button "Undo"
  - text: Met Full tuition remaining 7,554 USD · 2026/27 deadline Mar 01, 2027
```

# Test source

```ts
  99  |   const asu = rowFor(page, 'Arizona State University');
  100 |   await expect(asu).toBeVisible();
  101 |   // The corpus page for this award literally says "a full ride to an ASU degree".
  102 |   await expect(asu).toContainText('Full tuition');
  103 |   await expect(asu).not.toContainText('Full ride');
  104 |   // The tooltip still carries the full meaning behind the shortened chip.
  105 |   await expect(asu.getByTitle(/Tuition is covered/)).toBeVisible();
  106 | });
  107 | 
  108 | test('a previous-cycle deadline is shown as a guide, not as passed', async () => {
  109 |   await openShortlist(page);
  110 | 
  111 |   const melbourne = rowFor(page, 'University of Melbourne');
  112 |   await expect(melbourne).toContainText('previous cycle');
  113 |   await expect(melbourne).not.toContainText('passed');
  114 |   await expect(melbourne).toContainText('Gap');
  115 | });
  116 | 
  117 | test('a citizenship-restricted award is shown as not eligible', async () => {
  118 |   await openShortlist(page);
  119 | 
  120 |   await expandRow(page, 'KU Leuven');
  121 |   await page.getByTestId('tab-funding').click();
  122 | 
  123 |   const flemish = page.locator('.panel').filter({ hasText: 'Flemish Community Tuition Grant' }).first();
  124 |   await expect(flemish).toContainText('Not eligible');
  125 |   await expect(flemish).toContainText('European Economic Area');
  126 |   await page.screenshot({ path: shot('06-university-detail-funding.png'), fullPage: true });
  127 | });
  128 | 
  129 | test('an incomparable zero is refused rather than shown as nothing to pay', async () => {
  130 |   await openShortlist(page);
  131 | 
  132 |   // Toronto's award amount is published for 2024/25 while costs are 2026/27.
  133 |   const toronto = rowFor(page, 'University of Toronto');
  134 |   await expect(toronto).toContainText('not computable');
  135 | 
  136 |   await expandRow(page, 'University of Toronto');
  137 |   await page.getByTestId('tab-costs').click();
  138 |   await expect(page.getByText('Not computed.')).toBeVisible();
  139 |   await expect(page.getByText(/not directly comparable/)).toBeVisible();
  140 | });
  141 | 
  142 | test('a per-section IELTS minimum is enforced independently of the overall band', async () => {
  143 |   await openShortlist(page);
  144 | 
  145 |   // The demo applicant has overall 7.0 but writing 6.0; Delft requires 6.5 per band.
  146 |   const delft = rowFor(page, 'Delft University of Technology');
  147 |   await expect(delft).toContainText('Gap');
  148 | 
  149 |   await expandRow(page, 'Delft University of Technology');
  150 |   const barrier = page.locator('.notice--risk').filter({ hasText: 'Confirmed requirement not met' });
  151 |   await expect(barrier).toBeVisible();
  152 |   await expect(barrier).toContainText('IELTS writing');
  153 |   await page.screenshot({ path: shot('07-university-detail-requirements.png'), fullPage: true });
  154 | });
  155 | 
  156 | test('missing scholarship data reads as unknown, not as no funding', async () => {
  157 |   await openShortlist(page);
  158 | 
  159 |   const vienna = rowFor(page, 'University of Vienna');
  160 |   await expect(vienna).toContainText('Unknown');
  161 | 
  162 |   await expandRow(page, 'University of Vienna');
  163 |   await page.getByTestId('tab-funding').click();
  164 |   await expect(page.getByText(/that is not the same as there being none/)).toBeVisible();
  165 | });
  166 | 
  167 | test('conflicting official sources are shown with a drafted question', async () => {
  168 |   await openShortlist(page);
  169 |   await page.evaluate(() => { window.location.hash = '#/sources'; });
  170 | 
  171 |   await expect(page.getByRole('heading', { name: /See the proof behind every match/ })).toBeVisible();
  172 |   await expect(page.getByTestId('conflict-list')).toContainText('minimum overall IELTS band');
  173 |   await expect(page.getByTestId('conflict-list')).toContainText('more specific source');
  174 | 
  175 |   await page.getByText('Draft question for the admissions office').first().click();
  176 |   await expect(page.getByText('Dear Admissions Office,')).toBeVisible();
  177 |   await page.screenshot({ path: shot('09-sources-conflicts.png'), fullPage: true });
  178 | });
  179 | 
  180 | test('funding comparison hatches what it cannot compare', async () => {
  181 |   await openShortlist(page);
  182 |   await page.evaluate(() => { window.location.hash = '#/funding'; });
  183 | 
  184 |   await expect(page.getByRole('heading', { name: 'What you would actually pay' })).toBeVisible();
  185 |   await expect(page.locator('.fund-bar__unknown').first()).toBeVisible();
  186 |   await page.screenshot({ path: shot('08-funding-comparison.png'), fullPage: true });
  187 | });
  188 | 
  189 | test('approve, collect documents, and export', async () => {
  190 |   await openShortlist(page);
  191 | 
  192 |   // Approve the two best-funded rows.
  193 |   const rows = page.locator('tbody tr').filter({ has: page.locator('.decision-btn--approve') });
  194 |   await rows.nth(0).locator('.decision-btn--approve').click();
  195 |   await rows.nth(1).locator('.decision-btn--approve').click();
  196 |   await expect(rows.nth(0).locator('.decision-btn--approve')).toHaveAttribute('aria-pressed', 'true');
  197 | 
  198 |   await page.evaluate(() => { window.location.hash = '#/approved'; });
> 199 |   await expect(page.getByText('2 approved')).toBeVisible();
      |                                              ^ Error: expect(locator).toBeVisible() failed
  200 |   await page.screenshot({ path: shot('10-approved.png'), fullPage: true });
  201 | 
  202 |   await page.getByTestId('collect-documents').click();
  203 |   await expect(page.getByRole('heading', { name: /Prepare with confidence/ })).toBeVisible({
  204 |     timeout: 60_000,
  205 |   });
  206 |   await expect(page.locator('.doc').first()).toBeVisible({ timeout: 30_000 });
  207 |   // Lead-time ordering puts the referee first, because that is what sinks applications.
  208 |   await expect(page.locator('.doc').first()).toContainText(/reference|transcript|diploma|statement/i);
  209 |   await page.screenshot({ path: shot('11-documents.png'), fullPage: true });
  210 | 
  211 |   await page.evaluate(() => { window.location.hash = '#/export'; });
  212 |   await expect(page.getByRole('heading', { name: 'Take it with you, or erase it' })).toBeVisible();
  213 |   const download = page.waitForEvent('download');
  214 |   await page.getByTestId('export-csv').click();
  215 |   const file = await download;
  216 |   expect(file.suggestedFilename()).toMatch(/\.csv$/);
  217 |   await page.screenshot({ path: shot('12-export.png'), fullPage: true });
  218 | });
  219 | 
  220 | test('rejection is remembered with the row kept', async () => {
  221 |   await openShortlist(page);
  222 | 
  223 |   const first = page.locator('tbody tr').first();
  224 |   const name = await first.locator('.uni-cell__name').innerText();
  225 | 
  226 |   // Saying No asks why. The reason is optional, but the product promises that
  227 |   // whatever is given is kept with the row.
  228 |   await first.locator('.decision-btn--reject').click();
  229 |   const reason = first.locator('[data-testid^="reject-reason-"]');
  230 |   await expect(reason).toBeVisible();
  231 |   await reason.locator('button', { hasText: 'no funding' }).click();
  232 |   await reason.locator('[data-testid^="reject-save-"]').click();
  233 | 
  234 |   await expect(first.locator('.decision-btn--reject')).toHaveAttribute('aria-pressed', 'true');
  235 |   await expect(first).toHaveClass(/is-rejected/);
  236 |   await expect(first).toContainText('Rejected: no funding');
  237 | 
  238 |   await page.evaluate(() => { window.location.hash = '#/approved'; });
  239 |   await expect(page.getByText('Ruled out (1)')).toBeVisible();
  240 |   await expect(page.getByText(name)).toBeVisible();
  241 |   await expect(page.getByText('no funding')).toBeVisible();
  242 |   await expect(page.getByText(/not proposed again unless something material changes/)).toBeVisible();
  243 | 
  244 |   // And it survives a reload: the reason lives on the server, not in the tab.
  245 |   await page.reload();
  246 |   await page.evaluate(() => { window.location.hash = '#/approved'; });
  247 |   await expect(page.getByText('no funding')).toBeVisible();
  248 | });
  249 | 
  250 | test('screens have addresses: back, forward, reload and a gated link', async () => {
  251 |   await openShortlist(page);
  252 |   await expect(page).toHaveURL(/#\/shortlist$/);
  253 | 
  254 |   await page.evaluate(() => { window.location.hash = '#/funding'; });
  255 |   await expect(page).toHaveURL(/#\/funding$/);
  256 | 
  257 |   await page.goBack();
  258 |   await expect(page).toHaveURL(/#\/shortlist$/);
  259 |   await expect(page.getByRole('heading', { name: /Find your best matches/ })).toBeVisible();
  260 | 
  261 |   await page.goForward();
  262 |   await expect(page).toHaveURL(/#\/funding$/);
  263 | 
  264 |   // A reload lands on the same screen rather than back at step 01.
  265 |   await page.reload();
  266 |   await expect(page).toHaveURL(/#\/funding$/);
  267 |   await expect(page.getByRole('heading', { name: 'What you would actually pay' })).toBeVisible();
  268 | });
  269 | 
  270 | test('a link to a screen that is not reachable yet explains itself', async ({ browser }) => {
  271 |   // A bookmark made before there were any results, opened in a clean session.
  272 |   const fresh = await browser.newPage();
  273 |   await fresh.goto('/#/funding');
  274 |   await expect(fresh.getByTestId('redirect-notice')).toBeVisible();
  275 |   await expect(fresh.getByTestId('redirect-notice')).toContainText('No results yet');
  276 |   await expect(fresh).toHaveURL(/#\/profile$/);
  277 |   await fresh.close();
  278 | });
  279 | 
```
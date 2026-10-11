# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: accessibility.spec.ts >> no console errors during the full journey
- Location: ../../../../source/frontend/e2e/accessibility.spec.ts:179:1

# Error details

```
Error: console errors: Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden)

expect(received).toHaveLength(expected)

Expected length: 0
Received length: 16
Received array:  ["Failed to load resource: the server responded with a status of 403 (Forbidden)", "Failed to load resource: the server responded with a status of 403 (Forbidden)", "Failed to load resource: the server responded with a status of 403 (Forbidden)", "Failed to load resource: the server responded with a status of 403 (Forbidden)", "Failed to load resource: the server responded with a status of 403 (Forbidden)", "Failed to load resource: the server responded with a status of 403 (Forbidden)", "Failed to load resource: the server responded with a status of 403 (Forbidden)", "Failed to load resource: the server responded with a status of 403 (Forbidden)", "Failed to load resource: the server responded with a status of 403 (Forbidden)", "Failed to load resource: the server responded with a status of 403 (Forbidden)", …]
```

# Test source

```ts
  86  | test('the mobile shortlist becomes cards without an inner horizontal scroller', async () => {
  87  |   await openShortlist(page);
  88  |   await page.setViewportSize({ width: 375, height: 800 });
  89  | 
  90  |   // Every table on the screen, not just the first: the ranked list and the
  91  |   // out-of-budget / needs-clarification / excluded sections use the same
  92  |   // wrapper, and a card layout that only reaches one of them is not a fix.
  93  |   const wrappers = page.locator('.table-wrap');
  94  |   const count = await wrappers.count();
  95  |   expect(count).toBeGreaterThan(0);
  96  |   for (let i = 0; i < count; i += 1) {
  97  |     const layout = await wrappers.nth(i).evaluate((el) => ({
  98  |       overflow: getComputedStyle(el).overflowX,
  99  |       overflowPixels: el.scrollWidth - el.clientWidth,
  100 |     }));
  101 |     expect(layout.overflow, `table ${i} still scrolls sideways`).toBe('visible');
  102 |     expect(layout.overflowPixels).toBeLessThanOrEqual(1);
  103 |   }
  104 | });
  105 | 
  106 | test('the whole workflow is reachable by keyboard', async () => {
  107 |   // Tab into the page and confirm focus lands on real controls with visible rings.
  108 |   const focusable = await page.evaluate(() =>
  109 |     document.querySelectorAll('button:not([disabled]), a[href], input, select, textarea').length,
  110 |   );
  111 |   expect(focusable).toBeGreaterThan(10);
  112 | 
  113 |   await page.keyboard.press('Tab');
  114 |   const tag = await page.evaluate(() => document.activeElement?.tagName);
  115 |   expect(['BUTTON', 'A', 'INPUT', 'SELECT']).toContain(tag);
  116 | });
  117 | 
  118 | test('progress is announced to assistive technology', async () => {
  119 |   await page.evaluate(() => { window.location.hash = '#/progress'; });
  120 |   const bar = page.getByRole('progressbar', { name: 'Research progress' });
  121 |   await expect(bar).toBeVisible();
  122 |   await expect(bar).toHaveAttribute('aria-valuemax', '100');
  123 | });
  124 | 
  125 | test('the results table is labelled and its controls are named', async () => {
  126 |   await openShortlist(page);
  127 | 
  128 |   // Every table is captioned; the ranked one is the first.
  129 |   await expect(page.locator('table caption').first()).toContainText(
  130 |     'Shortlisted university programmes',
  131 |   );
  132 |   for (const caption of await page.locator('table caption').all()) {
  133 |     await expect(caption).toContainText('Shortlisted university programmes');
  134 |   }
  135 |   // Every decision control belongs to a named group, so a screen reader says
  136 |   // which university a "Yes" applies to.
  137 |   const group = page.getByRole('group', { name: /Decision for / }).first();
  138 |   await expect(group).toHaveAttribute('aria-label', /Decision for /);
  139 | 
  140 |   const expandable = page.locator('button[aria-expanded]').first();
  141 |   await expect(expandable).toHaveAttribute('aria-expanded', 'false');
  142 |   await expandable.click();
  143 |   await expect(expandable).toHaveAttribute('aria-expanded', 'true');
  144 | });
  145 | 
  146 | test('every reachable workflow screen has no serious axe violations', async () => {
  147 |   const screens = ['profile', 'preferences', 'progress', 'shortlist', 'funding', 'sources', 'approved', 'export'];
  148 | 
  149 |   for (const screen of screens) {
  150 |     await page.evaluate((destination) => { window.location.hash = `#/${destination}`; }, screen);
  151 |     const report = await new AxeBuilder({ page })
  152 |       .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
  153 |       .analyze();
  154 |     const serious = report.violations.filter(
  155 |       (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  156 |     );
  157 |     expect(serious, `${screen}: ${serious.map((v) => `${v.id} (${v.nodes.length})`).join(', ')}`).toEqual([]);
  158 |   }
  159 | });
  160 | 
  161 | test('both themes render with a painted background and readable text', async () => {
  162 |   await page.setViewportSize({ width: 1440, height: 900 });
  163 |   await openShortlist(page);
  164 | 
  165 |   await page.locator('.sidebar__settings summary').click();
  166 |   for (const theme of ['light', 'dark'] as const) {
  167 |     await page.selectOption('#theme', theme);
  168 |     await page.waitForTimeout(200);
  169 |     const { bg, fg } = await page.evaluate(() => {
  170 |       const s = getComputedStyle(document.body);
  171 |       return { bg: s.backgroundColor, fg: s.color };
  172 |     });
  173 |     expect(bg, `${theme} body must paint its own background`).not.toBe('rgba(0, 0, 0, 0)');
  174 |     expect(fg).not.toBe(bg);
  175 |     await page.screenshot({ path: shot(`theme-${theme}.png`), fullPage: false });
  176 |   }
  177 | });
  178 | 
  179 | test('no console errors during the full journey', async () => {
  180 |   await page.setViewportSize({ width: 1440, height: 900 });
  181 |   await openShortlist(page);
  182 |   await page.evaluate(() => { window.location.hash = '#/funding'; });
  183 |   await page.evaluate(() => { window.location.hash = '#/sources'; });
  184 |   await page.evaluate(() => { window.location.hash = '#/export'; });
  185 | 
> 186 |   expect(consoleErrors, `console errors: ${consoleErrors.join(' | ')}`).toHaveLength(0);
      |                                                                         ^ Error: console errors: Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden) | Failed to load resource: the server responded with a status of 403 (Forbidden)
  187 | });
  188 | 
```
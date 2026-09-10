import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('local case restores its step on reload and does not restore review mode', async ({ page }) => {
  await page.goto('/#/profile');
  await page.getByTestId('section-more').click();
  await page.getByRole('button', { name: 'New case', exact: true }).click();
  await page.getByLabel('Гражданство', { exact: true }).fill('Canada');
  await expect.poll(() => page.evaluate(() => {
    const key = sessionStorage.getItem('ashyq.activeProfile');
    return key ? localStorage.getItem(`ashyq.draft.${key}`) : null;
  })).toContain('Canada');
  await page.getByTestId('profile-step-4').click();
  await page.getByTestId('profile-show-all').click();
  await page.reload();
  await expect(page.getByTestId('profile-step-4')).toHaveAttribute('aria-current', 'step');
  await expect(page.getByTestId('profile-show-all')).toHaveAttribute('aria-pressed', 'false');
  await page.getByTestId('profile-step-0').click();
  await expect(page.getByLabel('Гражданство', { exact: true })).toHaveValue('Canada');
  await page.getByTestId('profile-step-3').click();
  await page.getByTestId('section-more').click();
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'New case', exact: true }).click();
  await expect(page.getByTestId('profile-step-0')).toHaveAttribute('aria-current', 'step');
});

test('profile locale switch preserves data, selections and responsive layout', async ({ page }, info) => {
  await page.emulateMedia({ reducedMotion: 'reduce', colorScheme: 'light' });
  await page.goto('/#/profile');
  await page.getByLabel('Гражданство', { exact: true }).fill('Canada');
  await page.locator('#level').selectOption({ label: 'Магистратура' });
  await page.getByTestId('section-more').click();
  await page.locator('#locale').selectOption('kk');
  await page.goto('/#/profile');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Талапкер профилі');
  await expect(page.getByLabel('Азаматтық', { exact: true })).toHaveValue('Canada');
  await expect(page.locator('#level')).toHaveValue('master');
  await expect(page.locator('#level option:checked')).toHaveText('Магистратура');
  await page.getByTestId('profile-show-all').click();
  await expect(page.getByLabel('IELTS: жалпы балл', { exact: true })).toBeVisible();
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath('profile-kazakh.png'), fullPage: true });
  await page.emulateMedia({ colorScheme: 'dark' });
  // Measure the settled theme, not intermediate colors during a CSS transition.
  await page.evaluate(async () => {
    await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
    await Promise.all(document.getAnimations().filter(animation => animation.effect?.getTiming().iterations !== Infinity).map(animation => animation.finished.catch(() => {})));
  });
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
  await page.emulateMedia({ colorScheme: 'light' });
  await page.getByTestId('section-more').click();
  await page.locator('#locale').selectOption('en');
  await page.goto('/#/profile');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Who is applying');
  await expect(page.getByLabel('Citizenship', { exact: true })).toHaveValue('Canada');
  await expect(page.locator('#level')).toHaveValue('master');
});

test('profile validation shows current server eligibility and recovers from unavailable checks', async ({ page }, info) => {
  let response: 'blocked' | 'ready' | 'error' = 'blocked';
  await page.route('**/api/profiles/validate', async (route) => {
    await route.fulfill({ status: response === 'error' ? 503 : 200, contentType: 'application/json',
      body: JSON.stringify(response === 'error' ? { detail: 'Unavailable' } : {
        gaps: [], summary: 'Server fixture', can_proceed: response === 'ready', blocking_count: response === 'blocked' ? 1 : 0,
      }) });
  });
  await page.goto('/#/profile');
  const status = page.getByTestId('profile-validation-status');
  await expect(status).toContainText('блокирующие пункты: 1');
  response = 'ready';
  await page.getByLabel('Гражданство', { exact: true }).fill('Canada');
  await expect(status).toContainText('Проверяем');
  await expect(status).toContainText('не означает, что анкета заполнена полностью');
  response = 'error';
  await page.getByLabel('Гражданство', { exact: true }).fill('KZ');
  await expect(status).toContainText('Проверка недоступна');
  response = 'ready';
  await status.getByRole('button', { name: 'Повторить проверку' }).click();
  await expect(status).toContainText('исследование можно запускать');
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await status.scrollIntoViewIfNeeded();
  await page.screenshot({ path: info.outputPath('profile-validation.png') });
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => { localStorage.setItem('ashyq.locale', 'ru'); });
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (!path.startsWith('/api/')) return route.continue();
    const bodies: Record<string, unknown> = {
      '/api/auth/status': { authenticated: true, auth_enabled: false },
      '/api/capabilities': { demo_mode: true }, '/api/cases': [],
      '/api/social/me': { joined: false, profile: null },
      '/api/social/messages/unread': { unread: 0 },
      '/api/social/discover': [],
      '/api/profiles/validate': { gaps: [], summary: 'Fixture validation', can_proceed: true, blocking_count: 0 },
      '/api/profiles/conversions/methods': { methods: [], note: '' },
    };
    await route.fulfill({ status: path in bodies ? 200 : 404, contentType: 'application/json', body: JSON.stringify(bodies[path] ?? { detail: 'Not found in fixture' }) });
  });
});

for (const theme of ['light', 'dark'] as const) {
  test(`case dashboard: ${theme}, navigation, accessibility and layout`, async ({ page }, info) => {
    await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' });
    await page.goto('/');
    await expect(page).toHaveURL(/#\/case$/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Большой путь');
    await page.evaluate(() => document.fonts.ready);
    await expect(page.getByRole('heading', { level: 1 })).toHaveCSS('font-family', /Prata/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveCSS('font-weight', '400');
    await expect(page.locator('body')).toHaveCSS('font-family', /Onest/);
    await expect(page.getByTestId('section-shortlist')).toBeDisabled();
    await expect(page.getByTestId('section-plan')).toBeDisabled();
    await expect(page.locator('#case-switcher')).toHaveCount(0);
    await expect(page.locator('.primary-nav__item')).toHaveCount(5);
    const violations = (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations;
    expect(violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    for (const item of await page.locator('.primary-nav__item').all()) {
      const box = await item.boundingBox();
      expect(box!.height).toBeGreaterThanOrEqual(44);
      expect(box!.width).toBeGreaterThanOrEqual(44);
    }
    await page.screenshot({ path: info.outputPath(`dashboard-${theme}.png`), fullPage: true });
    if (info.project.name === 'mobile') {
      await page.screenshot({ path: info.outputPath(`dashboard-${theme}-viewport.png`) });
    }
    await page.getByRole('button', { name: 'Заполнить профиль' }).click();
    await expect(page).toHaveURL(/#\/profile$/);
    await page.getByTestId('section-case').click();
    await expect(page).toHaveURL(/#\/case$/);
    await page.getByTestId('section-more').click();
    await expect(page.locator('#locale')).toBeVisible();
    await page.locator('#locale').selectOption('kk');
    await page.getByTestId('section-case').click();
    await expect(page.locator('.case-intro h1')).not.toContainText('Большой путь');
    await page.goBack();
    await expect(page.getByTestId('section-more')).toHaveAttribute('aria-current', 'page');
  });
}

test('profile wizard keeps edits across sections and supports review mode', async ({ page }, info) => {
  await page.goto('/#/profile');
  await expect(page.getByTestId('profile-step-0')).toHaveAttribute('aria-current', 'step');
  await page.getByLabel('Гражданство', { exact: true }).fill('Kazakhstan');
  await expect(page.getByLabel('GPA / средний балл')).toBeHidden();
  await page.getByTestId('profile-next-step').click();
  await page.getByLabel('GPA / средний балл').fill('4.8');
  await page.getByTestId('profile-step-2').click();
  await page.getByTestId('ielts-overall').fill('7');
  await page.getByTestId('profile-step-0').click();
  await expect(page.getByLabel('Гражданство', { exact: true })).toHaveValue('Kazakhstan');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const violations = (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations;
  expect(violations).toEqual([]);
  await page.screenshot({ path: `../docs/screenshots/profile-wizard-${info.project.name}.png`, fullPage: true });
  await page.getByTestId('profile-show-all').click();
  await expect(page.getByLabel('GPA / средний балл')).toHaveValue('4.8');
  await expect(page.getByTestId('ielts-overall')).toHaveValue('7');
  await expect(page.getByLabel('SAT: общий балл')).toBeVisible();
});

test('exam picker hides empty grids and retains scores across keyboard toggles', async ({ page }, info) => {
  await page.goto('/#/profile');
  await page.getByTestId('clear-profile').click();
  await page.getByTestId('profile-step-2').click();
  await expect(page.getByTestId('ielts-overall')).toBeHidden();
  await expect(page.locator('#toefl')).toBeHidden();
  await page.getByTestId('exam-toggle-toefl').focus();
  await page.keyboard.press('Space');
  await page.locator('#toefl').fill('105');
  await page.locator('#toefl-retake').fill('2027-03-01');
  await page.getByTestId('exam-toggle-toefl').click();
  await expect(page.locator('#toefl')).toBeHidden();
  await page.getByTestId('exam-toggle-toefl').click();
  await expect(page.locator('#toefl')).toHaveValue('105');
  await expect(page.locator('#toefl-retake')).toHaveValue('2027-03-01');
  await page.getByTestId('exam-toggle-duolingo').click();
  await page.locator('#duolingo-score').fill('130');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
  await page.screenshot({ path: `../docs/screenshots/exam-picker-${info.project.name}.png`, fullPage: true });
  await page.getByTestId('profile-step-3').click();
  await expect(page.getByTestId('exam-toggle-toefl')).toBeHidden();
  await page.getByTestId('exam-toggle-sat').click();
  await page.locator('#sat').fill('1450');
  await page.getByTestId('profile-show-all').click();
  await expect(page.locator('#toefl')).toHaveValue('105');
  await expect(page.locator('#sat')).toHaveValue('1450');
});

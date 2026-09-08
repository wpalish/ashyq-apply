import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

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
    await page.screenshot({ path: `../docs/screenshots/redesign-${info.project.name}-${theme}.png`, fullPage: true });
    if (info.project.name === 'mobile') {
      await page.screenshot({ path: `../docs/screenshots/redesign-mobile-${theme}-viewport.png` });
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

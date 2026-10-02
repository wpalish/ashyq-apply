import { expect, test } from '@playwright/test';

test('browse the local university catalogue before live research', async ({ page }) => {
  await page.goto('/#/shortlist');
  const catalogue = page.getByRole('region', { name: 'University catalogue' });
  await expect(catalogue).toBeVisible();
  await expect(catalogue.getByText('500 imported universities')).toBeVisible();
  await catalogue.getByRole('searchbox').fill('MIT');
  await expect(catalogue.getByText('Massachusetts Institute of Technology', { exact: true })).toBeVisible();
  await expect(catalogue.getByText('Not assessed').first()).toBeVisible();
  await catalogue.getByRole('searchbox').fill('');
  await catalogue.getByLabel('Country or region').selectOption('Canada');
  await expect(catalogue.getByText('University of Toronto', { exact: true })).toBeVisible();
  await expect(catalogue.getByText('Massachusetts Institute of Technology', { exact: true })).toHaveCount(0);
  await catalogue.getByRole('searchbox').fill('no-such-university-xyz');
  await expect(catalogue.getByText('No universities match these filters. Try another country or name.')).toBeVisible();
  const width = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }));
  expect(width.content).toBeLessThanOrEqual(width.viewport + 1);
});

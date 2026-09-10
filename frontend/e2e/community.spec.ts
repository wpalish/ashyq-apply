import { navigate } from './navigation';
/**
 * The community round trip: join, post, answer, and be findable.
 *
 * Runs against the dev principal, so there is one person in it. That is enough
 * to prove the wiring — the multi-person filtering is covered by the backend
 * suite, which can register several accounts without a browser.
 *
 * The dev database persists between runs, so everything here is either
 * idempotent or tagged with a unique run id.
 */

import { expect, test, type Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

const RUN = `e2e${Date.now().toString().slice(-7)}`;

/** Open the community profile, joining first if this database has no profile. */
async function ensureJoined(page: Page): Promise<void> {
  await page.goto('/');
  await navigate(page, "me");

  // The screen loads before it knows which of the two it is showing, so wait
  // for either rather than racing the spinner.
  const create = page.getByRole('button', { name: 'Create profile' });
  await expect(
    page.getByRole('button', { name: /^(Create profile|Edit profile)$/ }),
  ).toBeVisible();

  if (await create.isVisible().catch(() => false)) {
    await page.getByLabel('City you are applying to').fill('Astana');
    await page.getByLabel('Universities you are aiming at').fill('KBTU');
    await create.click();
  }
  await expect(page.getByRole('button', { name: 'Edit profile' })).toBeVisible();
}

test('joining publishes a profile that Discover can find', async ({ page }) => {
  await ensureJoined(page);

  await navigate(page, "discover");
  await page.getByLabel('City').fill('Astana');
  await page.getByLabel('University').click(); // blur commits the filter

  await expect(page.getByText('KBTU').first()).toBeVisible();
});

test('a post shows the tags it will publish, then carries them into the feed', async ({ page }) => {
  await page.goto('/');
  await navigate(page, 'feed');

  const composer = page.getByPlaceholder('Ask something, or say where you are applying');
  await composer.fill(`Кто сдаёт IELTS в #${RUN}?`);

  // The parse happens in front of the person writing, before anything is sent.
  await expect(page.getByText('Will be tagged')).toBeVisible();
  await expect(page.getByText(`#${RUN}`).first()).toBeVisible();

  await page.getByRole('button', { name: 'Post', exact: true }).click();
  await expect(composer).toHaveValue('');

  await expect(page.getByText(`Кто сдаёт IELTS в #${RUN}?`)).toBeVisible();
});

test('an answer opens in place under its post and is counted', async ({ page }) => {
  await page.goto('/');
  await navigate(page, "feed");

  // Scoped to this run's own post: the database keeps earlier ones, and
  // "Answer" is a substring of another post's "1 answer".
  const post = page.locator('.post').filter({ hasText: RUN });
  await post.getByRole('button', { name: 'Answer', exact: true }).click();
  await post.getByPlaceholder('Answer this').fill('6.0 overall, не ниже 5.5 по секциям.');
  await post.getByRole('button', { name: 'Reply' }).click();

  await expect(post.getByText('6.0 overall, не ниже 5.5 по секциям.')).toBeVisible();
  await expect(post.getByRole('button', { name: 'Hide answers' })).toBeVisible();
});

test('every community screen is reachable on a phone', async ({ page }) => {
  test.skip(
    (page.viewportSize()?.width ?? 0) >= 900,
    'the horizontal context navigation only applies below 900px',
  );
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto('/');
  await navigate(page, 'feed');

  const contextNavigation = page.locator('.context-nav');
  const layout = await contextNavigation.evaluate((nav) => ({
    overflowX: getComputedStyle(nav).overflowX,
    wrap: getComputedStyle(nav).flexWrap,
  }));
  expect(layout.overflowX).toBe('auto');
  expect(layout.wrap).toBe('nowrap');

  for (const label of ['Feed', 'Find applicants', 'Messages']) {
    const destination = page.getByRole('button', { name: label, exact: true });
    await destination.scrollIntoViewIfNeeded();
    await expect(destination).toBeInViewport();
    await destination.click();
    await expect(destination).toHaveAttribute('aria-current', 'page');
  }

  // The profile is account-adjacent in the redesigned shell and therefore
  // lives under More, rather than being a hidden fourth item in Community.
  await navigate(page, 'me');
  await expect(page.getByTestId('nav-me')).toHaveAttribute('aria-current', 'page');
});

test('an over-long post cannot be sent', async ({ page }) => {
  await page.goto('/');
  await navigate(page, "feed");

  await page.getByPlaceholder('Ask something, or say where you are applying').fill('x'.repeat(501));

  await expect(page.getByText('1 over')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Post', exact: true })).toBeDisabled();
});

test('a post can be taken back without leaving the community', async ({ page }) => {
  await page.goto('/');
  await navigate(page, "feed");

  const body = `Сказал не подумав ${RUN}`;
  await page.getByPlaceholder('Ask something, or say where you are applying').fill(body);
  await page.getByRole('button', { name: 'Post', exact: true }).click();

  const mine = page.locator('.post').filter({ hasText: body });
  await mine.getByRole('button', { name: 'Delete' }).click();
  await mine.getByRole('button', { name: 'Yes, delete' }).click();

  await expect(page.getByText(body)).toBeHidden();
  // Still a member: the composer is still there.
  await expect(
    page.getByPlaceholder('Ask something, or say where you are applying'),
  ).toBeVisible();
});

test('leaving the community is reversible from the same screen', async ({ page }) => {
  await ensureJoined(page);

  await page.getByRole('button', { name: 'Leave the community' }).click();
  await page.getByRole('button', { name: 'Keep my profile' }).click();
  await expect(page.getByRole('button', { name: 'Edit profile' })).toBeVisible();

  await page.getByRole('button', { name: 'Leave the community' }).click();
  await page.getByRole('button', { name: 'Yes, delete it' }).click();

  // Back to the join form, with the account still signed in.
  await expect(page.getByRole('heading', { name: 'Join the community' })).toBeVisible();
  await navigate(page, "discover");
  await expect(page.getByText('Nobody has joined yet')).toBeVisible();
});

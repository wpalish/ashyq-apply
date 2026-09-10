import type { Page } from '@playwright/test';

/** Follow the same primary -> contextual navigation as a user. */
export async function navigate(page: Page, screen: string): Promise<void> {
  const section = ['profile', 'preferences', 'progress'].includes(screen) ? 'case'
    : ['shortlist', 'funding', 'sources'].includes(screen) ? 'shortlist'
    : ['approved', 'documents'].includes(screen) ? 'plan'
    : ['feed', 'discover', 'messages', 'person'].includes(screen) ? 'community' : 'more';
  const destination = page.getByTestId(`nav-${screen}`);
  if (!(await destination.isVisible())) {
    await page.getByTestId(`section-${section}`).click();
  }
  await destination.click();
  // Legacy integration scenarios exercise fields across sections in review mode.
  if (screen === 'profile') await page.getByTestId('profile-show-all').click();
}

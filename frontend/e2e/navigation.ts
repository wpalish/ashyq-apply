import type { Page } from '@playwright/test';

/** Follow the same primary -> contextual navigation as a user. */
export async function navigate(page: Page, screen: string): Promise<void> {
  const section = ['profile', 'preferences', 'progress'].includes(screen) ? 'case'
    : ['shortlist', 'funding', 'sources'].includes(screen) ? 'shortlist'
    : ['approved', 'documents'].includes(screen) ? 'plan'
    : ['feed', 'discover', 'messages', 'person'].includes(screen) ? 'community' : 'more';
  await page.getByTestId(`section-${section}`).click();
  await page.getByTestId(`nav-${screen}`).click();
}

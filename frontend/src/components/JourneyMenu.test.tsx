/**
 * The header's "Explore" menu is the one place every screen is named at once,
 * so a Russian or Kazakh reader opening it must not meet an English label.
 */

import { act, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { JourneyMenu } from './JourneyMenu';
import { SCREENS } from '@/lib/screens';
import { setLocale, t } from '@/lib/i18n';

afterEach(() => {
  act(() => setLocale('en'));
});

function english(): string[] {
  setLocale('en');
  return [t('topbar.explore'), ...SCREENS.map((s) => t(s.label))];
}

describe('the Explore menu', () => {
  it('names every screen, the moderation queue only for a moderator', () => {
    const { container, rerender } = render(<JourneyMenu moderator={false} gate={{}} onSelect={() => {}} />);
    const menu = container.querySelector('.journey-menu') as HTMLElement;
    expect(within(menu).getAllByRole('button', { hidden: true })).toHaveLength(SCREENS.length - 1);
    expect(within(menu).queryByText('Moderation queue')).toBeNull();
    rerender(<JourneyMenu moderator gate={{}} onSelect={() => {}} />);
    expect(within(menu).getAllByRole('button', { hidden: true })).toHaveLength(SCREENS.length);
    expect(within(menu).getByText('Explore')).toBeTruthy();
    expect(within(menu).getByText('Preferences & budget')).toBeTruthy();
  });

  for (const locale of ['ru', 'kk'] as const) {
    it(`leaves no English label in ${locale}`, () => {
      const en = english();
      act(() => setLocale(locale));
      const { container } = render(<JourneyMenu moderator gate={{}} onSelect={() => {}} />);
      const menu = container.querySelector('.journey-menu') as HTMLElement;
      const labels = [
        menu.querySelector('summary')?.textContent ?? '',
        ...within(menu).getAllByRole('button', { hidden: true }).map((b) => b.textContent ?? ''),
      ];
      expect(labels).toHaveLength(SCREENS.length + 1);
      for (const label of labels) {
        expect(label.trim(), `${locale}: empty label`).not.toBe('');
        expect(en, `${locale}: "${label}" is the English label`).not.toContain(label);
        expect(label, `${locale}: "${label}" has Latin letters`).not.toMatch(/[A-Za-z]/);
      }
      expect(screen.queryByText('Preferences & budget')).toBeNull();
    });
  }
});

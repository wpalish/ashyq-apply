import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from './App';
import { api } from '@/api/client';
import { StoreProvider } from '@/lib/store';
import type { StoredProfile } from '@/types';

beforeEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  window.sessionStorage.clear();
  window.history.replaceState(null, '', '/#/profile');
  // jsdom does not implement this browser-only navigation convenience.
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  vi.spyOn(api, 'capabilities').mockResolvedValue({ demo_mode: true } as never);
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'authStatus').mockResolvedValue({ principal: null } as never);
  vi.spyOn(api, 'socialMe').mockResolvedValue({ joined: false, profile: null } as never);
  vi.spyOn(api, 'unreadMessages').mockResolvedValue({ unread: 0 });
  vi.spyOn(api, 'validateProfile').mockResolvedValue({
    gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok',
  });
});

afterEach(() => {
  window.history.replaceState(null, '', '/');
});

it('keeps the current wizard step and confirms a first save through the real app and store', async () => {
  const create = vi.spyOn(api, 'createProfile').mockImplementation(async (payload) => ({
    ...(payload as Record<string, unknown>),
    id: 'first-saved-applicant',
    created_at: '2026-10-09T00:00:00Z',
    updated_at: '2026-10-09T00:00:00Z',
  }) as StoredProfile);
  render(<StoreProvider><App /></StoreProvider>);
  fireEvent.change(screen.getByLabelText('Citizenship'), { target: { value: 'Uzbekistan' } });
  const steps = within(screen.getByRole('navigation', { name: 'Profile steps' })).getAllByRole('button');
  fireEvent.click(steps[2]!);
  fireEvent.change(screen.getByTestId('ielts-overall'), { target: { value: '7' } });

  fireEvent.click(screen.getByTestId('save-profile'));
  expect(await screen.findByText('Saved', { exact: true })).toBeVisible();

  const currentSteps = within(screen.getByRole('navigation', { name: 'Profile steps' })).getAllByRole('button');
  expect(currentSteps[2]).toHaveAttribute('aria-current', 'step');
  expect(screen.getByTestId('ielts-overall')).toHaveValue(7);
  expect(screen.getByLabelText('Citizenship')).toHaveValue('Uzbekistan');
  expect(window.sessionStorage.getItem('ashyq.activeProfile')).toBe('first-saved-applicant');
  expect(create).toHaveBeenCalledTimes(1);
  expect(create).toHaveBeenCalledWith(expect.objectContaining({
    context: expect.objectContaining({ citizenship: 'Uzbekistan' }),
    academics: expect.objectContaining({ ielts: expect.objectContaining({ overall: 7 }) }),
  }));
});

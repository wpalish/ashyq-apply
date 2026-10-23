import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import App from './App';
import { api } from '@/api/client';
import { setLocale } from '@/lib/i18n';
const state = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock('@/lib/store', () => ({ useStore: () => state.value }));
vi.mock('@/screens/ProfileScreen', () => ({ ProfileScreen: () => <h1>Applicant profile editor</h1> }));
vi.mock('@/screens/ProgressScreen', () => ({ ProgressScreen: () => <h1>Research progress view</h1> }));
vi.mock('@/screens/PersonScreen', () => ({ PersonScreen: ({ userId }: { userId: string }) => <h1>Public member {userId}</h1> }));
const inactive = () => ({ scope: null, profile_id: null, case_epoch: 0 });
const run = { id: 'existing-run', profile_id: 'profile-a' };
const flush = async () => { await act(async () => { for (let i=0; i<8; i++) await Promise.resolve(); }); };
beforeEach(() => {
  setLocale('en');
  window.location.hash = '#/profile';
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  vi.spyOn(api, 'authStatus').mockResolvedValue({ enabled: false, authenticated: true, registration_enabled: false, principal: null });
  vi.spyOn(api, 'socialMe').mockResolvedValue({ joined: false, profile: null });
  vi.spyOn(api, 'unreadMessages').mockResolvedValue({ unread: 0 });
  state.value = { run: null, results: [], summary: null, error: null, clearError: vi.fn(), capabilities: null,
    cases: [], savedProfile: { id: 'profile-a' }, dirty: false, hydrated: true, currentAdmissionsCase: inactive, paywall: null };
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it('keeps a directly opened editor when an existing run is already hydrated', async () => {
  state.value.run = run; render(<App />); await flush();
  expect(screen.getByRole('heading', { name: 'Applicant profile editor' })).toBeInTheDocument();
  expect(location.hash).toBe('#/profile');
});
it('keeps the editor when a previous run arrives during hydration', async () => {
  state.value.hydrated = false; const view = render(<App />); await flush();
  state.value = { ...state.value, hydrated: true, run }; view.rerender(<App />); await flush();
  expect(screen.getByRole('heading', { name: 'Applicant profile editor' })).toBeInTheDocument();
  expect(location.hash).toBe('#/profile');
});
it('still follows an explicitly started new run after initial hydration', async () => {
  const view = render(<App />); await flush();
  state.value = { ...state.value, run }; view.rerender(<App />); await flush();
  expect(screen.getByRole('heading', { name: 'Research progress view' })).toBeInTheDocument();
  expect(location.hash).toBe('#/progress');
});

it('restores the exact public member from a deep link', async () => {
  window.location.hash = '#/person?user=synthetic-member'; render(<App />);
  expect(await screen.findByRole('heading', { name: 'Public member synthetic-member' })).toBeInTheDocument();
  expect(location.hash).toBe('#/person?user=synthetic-member');
});
it('does not substitute the private owner profile for an incomplete member link', async () => {
  window.location.hash = '#/person'; render(<App />); await flush();
  expect(screen.getByRole('heading', { name: 'Member link incomplete' })).toBeInTheDocument();
  expect(screen.queryByText(/Public member/)).not.toBeInTheDocument();
});
it('explains an invalid address without replacing the current editor', async () => {
  render(<App/>); await flush();
  await act(async () => { window.location.hash = '#main-content'; window.dispatchEvent(new HashChangeEvent('hashchange')); });
  expect(screen.queryByTestId('missing-route-notice')).toBeNull();
  await act(async () => { window.location.hash = '#/missing-section'; window.dispatchEvent(new HashChangeEvent('hashchange')); });
  expect(screen.getByTestId('missing-route-notice')).toHaveTextContent('This page does not exist');
  expect(screen.getByRole('heading', { name: 'Applicant profile editor' })).toBeInTheDocument();
  await act(async () => { window.location.hash = '#/profile'; window.dispatchEvent(new HashChangeEvent('hashchange')); });
  expect(screen.queryByTestId('missing-route-notice')).toBeNull();
});
it.each(['#/welcome', '#/sign-in', '#/sign-in?create=1', '#/forgot', '#/reset?token=synthetic-token'])(
  'opens the authenticated workspace after returning from %s without a false missing-page notice', async (hash) => {
    window.location.hash = hash; render(<App/>); await flush();
    expect(location.hash).toBe('#/home');
    expect(screen.queryByTestId('missing-route-notice')).toBeNull();
  },
);
it('still explains a genuinely unknown initial address', async () => {
  window.location.hash = '#/missing-section'; render(<App/>); await flush();
  expect(screen.getByTestId('missing-route-notice')).toHaveTextContent('This page does not exist');
  expect(location.hash).toBe('#/missing-section');
});
it('keeps the workspace open and explains a failed sign-out without automatically retrying', async () => {
  const logout = vi.spyOn(api, 'logout').mockRejectedValue(new Error('Synthetic connection failure'));
  render(<App/>); await flush();
  fireEvent.click(screen.getByLabelText('Applicant workspace'));
  fireEvent.click(screen.getByTestId('sign-out')); await flush();
  expect(screen.getByRole('alert')).toHaveTextContent('Sign-out was not confirmed');
  expect(screen.getByRole('heading', { name: 'Applicant profile editor' })).toBeInTheDocument();
  expect(screen.getByTestId('sign-out')).toBeEnabled();
  expect(logout).toHaveBeenCalledTimes(1);
});

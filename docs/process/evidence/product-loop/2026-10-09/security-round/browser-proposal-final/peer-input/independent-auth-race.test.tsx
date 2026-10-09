import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { AuthGate } from '@/AuthGate';
import type { AuthPrincipal, AuthStatus } from '@/types';

const OWNER = 'ashyq.applicantOwner';
const a: AuthPrincipal = { user_id: 'synthetic-a', organization_id: 'org-a',
  email: 'a@example.test', display_name: 'Synthetic A', organization_name: 'A',
  role: 'owner', local_development: false };
const b: AuthPrincipal = { ...a, user_id: 'synthetic-b', organization_id: 'org-b', email: 'b@example.test' };
const status = (principal: AuthPrincipal | null): AuthStatus => ({ enabled: true,
  authenticated: principal !== null, registration_enabled: true, principal,
  password_reset_enabled: false });
const response = (value: unknown) => new Response(JSON.stringify(value), {
  status: 200, headers: { 'Content-Type': 'application/json' },
});
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); window.location.hash = '#/sign-in'; });
afterEach(() => { vi.unstubAllGlobals(); });

it('does not let post-login status A erase or supersede the newer acknowledged owner B', async () => {
  let lateA!: (value: Response) => void;
  let statuses = 0;
  const calls: string[] = [];
  const transport = vi.fn((path: string) => {
    calls.push(path);
    if (path === '/api/auth/login') return Promise.resolve(response(a));
    if (path !== '/api/auth/status') throw new Error('Unexpected native dispatch: ' + path);
    statuses++;
    if (statuses === 1) return Promise.resolve(response(status(null)));
    if (statuses === 2) return new Promise<Response>((resolve) => { lateA = resolve; });
    return Promise.resolve(response(status(b)));
  });
  vi.stubGlobal('fetch', transport);
  render(<AuthGate><p data-testid="private">Private workspace</p></AuthGate>);
  fireEvent.change(await screen.findByTestId('auth-email'), { target: { value: a.email } });
  fireEvent.change(screen.getByTestId('auth-password'), { target: { value: 'synthetic password 123' } });
  fireEvent.submit(screen.getByTestId('auth-submit').closest('form')!);
  await waitFor(() => expect(lateA).toBeDefined());
  const ownerB = `auth:${JSON.stringify([b.user_id, b.organization_id])}`;
  const draftB = `ashyq.owner.${encodeURIComponent(ownerB)}.ashyq.draft.local:b`;
  localStorage.setItem(OWNER, ownerB);
  localStorage.setItem(draftB, 'new B draft must survive');
  await act(async () => {
    window.dispatchEvent(new StorageEvent('storage', { key: OWNER, newValue: ownerB }));
  });
  await screen.findByTestId('private');
  expect(localStorage.getItem(OWNER)).toBe(ownerB);
  expect(localStorage.getItem(draftB)).toBe('new B draft must survive');
  await act(async () => { lateA(response(status(a))); });
  // No search, profile, or provider calls: actual client + AuthGate auth flow only.
  expect(calls).toEqual(['/api/auth/status', '/api/auth/login', '/api/auth/status', '/api/auth/status']);
  expect({ owner: localStorage.getItem(OWNER), draft: localStorage.getItem(draftB) })
    .toEqual({ owner: ownerB, draft: 'new B draft must survive' });
});

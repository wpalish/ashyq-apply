import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthGate } from './AuthGate';
import { api } from '@/api/client';
import { StoreProvider, useStore } from '@/lib/store';
import { adoptPointer, readDraftEnvelope, writeDraftEnvelope, writePointer } from '@/lib/caseDrafts';
import type { AuthPrincipal, AuthStatus } from '@/types';

const principal: AuthPrincipal = {
  user_id: 'user-1', email: 'applicant@example.test', display_name: 'Applicant',
  organization_id: 'org-1', organization_name: 'My workspace', role: 'owner',
  local_development: false,
};
const signedOut: AuthStatus = {
  enabled: true, registration_enabled: true, authenticated: false, principal: null,
};

function renderGate() {
  render(<AuthGate><p>Search workspace</p></AuthGate>);
}

beforeEach(() => {
  vi.restoreAllMocks();
  window.location.hash = '#/sign-in';
  vi.spyOn(api, 'authStatus').mockResolvedValue({ ...signedOut, password_reset_enabled: false });
  vi.spyOn(api, 'login').mockResolvedValue(principal);
  vi.spyOn(api, 'register').mockResolvedValue(principal);
  vi.spyOn(api, 'requestPasswordReset').mockResolvedValue({ detail: 'Check your inbox for a link.' });
  vi.spyOn(api, 'confirmPasswordReset').mockResolvedValue(principal);
});

describe('password recovery capability', () => {
  it('explains unavailable recovery while preserving sign in', async () => {
    vi.mocked(api.authStatus)
      .mockResolvedValueOnce({ ...signedOut, password_reset_enabled: false })
      .mockResolvedValueOnce({ ...signedOut, authenticated: true, principal, password_reset_enabled: false });
    renderGate();
    expect(await screen.findByText('Password recovery is currently unavailable.')).toBeInTheDocument();
    fireEvent.change(screen.getByTestId('auth-email'), { target: { value: principal.email } });
    fireEvent.change(screen.getByTestId('auth-password'), { target: { value: 'saved password 123' } });
    expect(screen.queryByTestId('forgot-password')).not.toBeInTheDocument();
    fireEvent.submit(screen.getByTestId('auth-submit').closest('form')!);
    expect(await screen.findByText('Search workspace')).toBeInTheDocument();
    expect(api.login).toHaveBeenCalledWith(principal.email, 'saved password 123');
    expect(api.requestPasswordReset).not.toHaveBeenCalled();
  });

  it('asks new users to save their password and still creates their workspace', async () => {
    vi.mocked(api.authStatus)
      .mockResolvedValueOnce({ ...signedOut, password_reset_enabled: false })
      .mockResolvedValueOnce({ ...signedOut, authenticated: true, principal, password_reset_enabled: false });
    renderGate();
    fireEvent.click(await screen.findByTestId('auth-mode-toggle'));
    expect(screen.getByText('Password recovery is currently unavailable.')).toBeInTheDocument();
    expect(screen.getByText('Save your password somewhere safe. You will need it to sign in.')).toBeInTheDocument();
    fireEvent.change(screen.getByTestId('auth-name'), { target: { value: principal.display_name } });
    fireEvent.change(screen.getByTestId('auth-organization'), { target: { value: principal.organization_name } });
    fireEvent.change(screen.getByTestId('auth-email'), { target: { value: principal.email } });
    fireEvent.change(screen.getByTestId('auth-password'), { target: { value: 'saved password 123' } });
    fireEvent.submit(screen.getByTestId('auth-submit').closest('form')!);
    expect(await screen.findByText('Search workspace')).toBeInTheDocument();
    expect(api.register).toHaveBeenCalledWith({
      email: principal.email, password: 'saved password 123',
      display_name: principal.display_name, organization_name: principal.organization_name,
    });
  });

  it('replaces a disabled recovery deep link with an explanation and a way back', async () => {
    window.location.hash = '#/reset?token=emailed-token';
    renderGate();
    expect(await screen.findByText('Password recovery is currently unavailable.')).toBeInTheDocument();
    expect(screen.queryByTestId('reset-password')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Set password and sign in' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Back to sign in' }));
    expect(await screen.findByRole('heading', { name: 'Welcome back.' })).toBeInTheDocument();
    expect(window.location.hash).toBe('#/sign-in');
    expect(api.confirmPasswordReset).not.toHaveBeenCalled();
    expect(api.requestPasswordReset).not.toHaveBeenCalled();
  });

  it.each([true, undefined])('keeps recovery available when the capability is %s', async (enabled) => {
    vi.mocked(api.authStatus).mockResolvedValue({ ...signedOut, password_reset_enabled: enabled });
    renderGate();
    fireEvent.change(await screen.findByTestId('auth-email'), { target: { value: principal.email } });
    fireEvent.click(screen.getByTestId('forgot-password'));
    expect(await screen.findByTestId('reset-notice')).toHaveTextContent('Check your inbox for a link.');
    expect(api.requestPasswordReset).toHaveBeenCalledWith(principal.email);
    expect(screen.queryByText('Password recovery is currently unavailable.')).not.toBeInTheDocument();
  });

  it('preserves reset completion when recovery is enabled', async () => {
    window.location.hash = '#/reset?token=emailed-token';
    vi.mocked(api.authStatus)
      .mockResolvedValueOnce({ ...signedOut, password_reset_enabled: true })
      .mockResolvedValueOnce({ ...signedOut, authenticated: true, principal, password_reset_enabled: true });
    renderGate();
    fireEvent.change(await screen.findByTestId('reset-password'), { target: { value: 'new password 123' } });
    fireEvent.submit(screen.getByTestId('reset-password').closest('form')!);
    await waitFor(() => expect(api.confirmPasswordReset).toHaveBeenCalledWith('emailed-token', 'new password 123'));
    expect(await screen.findByText('Search workspace')).toBeInTheDocument();
    expect(window.location.hash).toBe('');
  });
});

describe('public routes', () => {
  it('shows a public landing before authentication', async () => {
    window.location.hash = '#/welcome';
    renderGate();
    expect(screen.getByRole('heading', { name: /Find a university/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '#/sign-in');
  });

  it('makes the legal draft available before authentication', async () => {
    window.location.hash = '#/legal';
    renderGate();
    expect(screen.getByTestId('legal-draft')).toHaveTextContent('not reviewed by a lawyer');
  });
});


// Native AuthGate -> StoreProvider hydration, with synthetic principal/case data only.
const OWNER_KEY = 'ashyq.applicantOwner';
function BrowserCaseProbe() {
  const { profileDraft, hydrated } = useStore();
  return <p data-testid="private-draft">{hydrated ? String(profileDraft.display_name) : 'loading'}</p>;
}
function privateGate() {
  return render(<AuthGate><StoreProvider><BrowserCaseProbe /></StoreProvider></AuthGate>);
}
function localDraft(name: string) {
  writePointer('profile', 'local:private-case');
  writeDraftEnvelope('local:private-case', { display_name: name, context: { citizenship: 'Synthetic citizenship' } });
}
function authenticated(owner = principal): AuthStatus {
  return { ...signedOut, authenticated: true, principal: owner };
}

describe('private browser state belongs to the authenticated principal and workspace', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
    vi.spyOn(api, 'cases').mockResolvedValue([]);
    vi.spyOn(api, 'createProfile').mockResolvedValue({} as never);
    vi.spyOn(api, 'validateProfile').mockResolvedValue({ gaps: [], can_proceed: true } as never);
    vi.mocked(api.authStatus).mockResolvedValue(authenticated());
  });

  it('does not auto-import an unowned local draft, old pointers or docsDone into an authenticated case', async () => {
    localDraft('Previous private applicant');
    window.localStorage.setItem('unimatch.unsavedDraft', JSON.stringify({ display_name: 'Legacy applicant' }));
    window.localStorage.setItem('ashyq.docsDone', '{"old-result::Passport":true}');
    window.localStorage.setItem('unimatch.theme', 'dark');
    privateGate();
    await waitFor(() => expect(screen.getByTestId('private-draft')).not.toHaveTextContent('loading'));
    expect(screen.getByTestId('private-draft')).not.toHaveTextContent('Previous private applicant');
    expect(adoptPointer('profile')).toBeNull();
    expect(window.localStorage.getItem('unimatch.unsavedDraft')).toBeNull();
    expect(window.localStorage.getItem('ashyq.docsDone')).toBeNull();
    expect(window.localStorage.getItem('unimatch.theme')).toBe('dark');
    expect(api.createProfile).not.toHaveBeenCalled();
  });

  it('preserves the same authenticated owner local draft and pointer on reload', async () => {
    const first = privateGate();
    await screen.findByTestId('private-draft');
    localDraft('Same-owner draft');
    first.unmount();
    privateGate();
    await waitFor(() => expect(screen.getByTestId('private-draft')).toHaveTextContent('Same-owner draft'));
    expect(adoptPointer('profile')).toBe('local:private-case');
  });

  it.each([
    { ...principal, user_id: 'user-2' },
    { ...principal, organization_id: 'org-2' },
  ])('does not restore another user or organization local draft: %j', async (next) => {
    const first = privateGate();
    await screen.findByTestId('private-draft');
    localDraft('A-only draft');
    first.unmount();
    vi.mocked(api.authStatus).mockResolvedValue(authenticated(next));
    privateGate();
    await waitFor(() => expect(screen.getByTestId('private-draft')).not.toHaveTextContent('loading'));
    expect(screen.getByTestId('private-draft')).not.toHaveTextContent('A-only draft');
    expect(readDraftEnvelope('local:private-case')).toBeNull();
    expect(adoptPointer('profile')).toBeNull();
  });

  it('locks old private memory while a cross-tab owner transition awaits server revalidation', async () => {
    let resolve!: (status: AuthStatus) => void;
    const first = privateGate();
    await waitFor(() => expect(screen.getByTestId('private-draft')).not.toHaveTextContent('loading'));
    localDraft('A-only draft');
    first.unmount();
    privateGate();
    await waitFor(() => expect(screen.getByTestId('private-draft')).toHaveTextContent('A-only draft'));
    vi.mocked(api.authStatus).mockImplementation(() => new Promise((done) => { resolve = done; }));
    window.localStorage.setItem(OWNER_KEY, 'auth:["user-2","org-2"]');
    window.dispatchEvent(new StorageEvent('storage', { key: OWNER_KEY, newValue: 'auth:["user-2","org-2"]' }));
    await waitFor(() => expect(screen.queryByTestId('private-draft')).not.toBeInTheDocument());
    await waitFor(() => expect(resolve).toBeDefined());
    await act(async () => { resolve(authenticated({ ...principal, user_id: 'user-2', organization_id: 'org-2' })); });
    await waitFor(() => expect(screen.getByTestId('private-draft')).not.toHaveTextContent('loading'));
    expect(screen.getByTestId('private-draft')).not.toHaveTextContent('A-only draft');
  });

  it('preserves explicit anonymous demo local draft controls', async () => {
    vi.mocked(api.authStatus).mockResolvedValue({ enabled: false, authenticated: true, registration_enabled: false, principal: null });
    const first = privateGate();
    await screen.findByTestId('private-draft');
    localDraft('Anonymous demo draft');
    first.unmount();
    privateGate();
    await waitFor(() => expect(screen.getByTestId('private-draft')).toHaveTextContent('Anonymous demo draft'));
  });

  it('keeps an unbound legacy draft only when the server explicitly disables authentication for demo', async () => {
    localDraft('Legacy anonymous demo');
    vi.mocked(api.authStatus).mockResolvedValue({ enabled: false, authenticated: true, registration_enabled: false, principal: null });
    privateGate();
    await waitFor(() => expect(screen.getByTestId('private-draft')).toHaveTextContent('Legacy anonymous demo'));
  });

  it('does not bind an older status response over a newer cross-tab owner even before its event arrives', async () => {
    let resolve!: (status: AuthStatus) => void;
    vi.mocked(api.authStatus)
      .mockImplementationOnce(() => new Promise((done) => { resolve = done; }))
      .mockResolvedValue(authenticated({ ...principal, user_id: 'user-2', organization_id: 'org-2' }));
    privateGate();
    window.localStorage.setItem(OWNER_KEY, 'auth:["user-2","org-2"]');
    await act(async () => { resolve(authenticated()); });
    await waitFor(() => expect(screen.getByTestId('private-draft')).not.toHaveTextContent('loading'));
    expect(window.localStorage.getItem(OWNER_KEY)).toBe('auth:["user-2","org-2"]');
    expect(api.authStatus).toHaveBeenCalledTimes(2);
  });
});

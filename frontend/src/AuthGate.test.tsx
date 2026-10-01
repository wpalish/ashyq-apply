import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthGate } from './AuthGate';
import { api } from '@/api/client';
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
  window.location.hash = '';
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
    expect(await screen.findByRole('heading', { name: 'Sign in to ASHYQ Apply' })).toBeInTheDocument();
    expect(window.location.hash).toBe('');
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

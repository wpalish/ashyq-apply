/**
 * The account screen: the brand and the product's promises beside the form,
 * and a password hint that counts towards the minimum.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthGate } from './AuthGate';

const { authStatus } = vi.hoisted(() => ({ authStatus: vi.fn() }));
vi.mock('@/api/client', () => ({
  api: { authStatus },
  ApiError: class ApiError extends Error {},
}));

beforeEach(() => {
  authStatus.mockResolvedValue({ enabled: true, registration_enabled: true, authenticated: false, principal: null });
});

describe('the account screen', () => {
  it('says what the product is before it asks for an email', async () => {
    render(<AuthGate><p>app</p></AuthGate>);
    expect(await screen.findByRole('heading', { name: 'Sign in to ASHYQ Apply' })).toBeInTheDocument();
    const about = screen.getByRole('region', { name: 'About ASHYQ Apply' });
    expect(about).toHaveTextContent("Every figure links to the university's own page");
    expect(about).toHaveTextContent('admission is decided by the university');
    expect(about.textContent).not.toMatch(/%|chance|probab/i);
    expect(screen.queryByText('app')).toBeNull();
  });

  it('counts a new password towards the minimum', async () => {
    render(<AuthGate><p>app</p></AuthGate>);
    fireEvent.click(await screen.findByTestId('auth-mode-toggle'));
    const hint = screen.getByTestId('password-count');
    expect(hint).toHaveTextContent('At least 12 characters.');
    fireEvent.change(screen.getByTestId('auth-password'), { target: { value: 'seven77' } });
    expect(hint).toHaveTextContent('At least 12 characters · 7 so far.');
    fireEvent.change(screen.getByTestId('auth-password'), { target: { value: 'twelve-chars' } });
    expect(hint).toHaveTextContent('long enough');
  });
});

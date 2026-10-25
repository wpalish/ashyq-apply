import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { api } from '@/api/client';
import type { AuthPrincipal } from '@/types';

vi.mock('@/lib/store', () => ({
  useStore: () => ({
    run: null, results: [], summary: null, error: null, clearError: () => {},
    capabilities: null, cases: [], savedProfile: null, switchCase: async () => {},
    newCase: () => {}, dirty: false, hydrated: true,
  }),
}));

const owner: AuthPrincipal = {
  user_id: 'user-1', email: 'owner@example.test', display_name: 'Owner',
  organization_id: 'org-1', organization_name: 'Workspace', role: 'owner',
  local_development: false, is_moderator: false,
};

function signedInAs(principal: AuthPrincipal | null) {
  vi.spyOn(api, 'authStatus').mockResolvedValue({
    enabled: true, registration_enabled: true, authenticated: principal !== null, principal,
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  // A screen with no data of its own, so the shell is what is under test.
  window.location.hash = '#/legal';
  // jsdom has no scrolling; the shell scrolls to the top on every screen.
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  vi.spyOn(api, 'socialMe').mockRejectedValue(new Error('community off'));
  vi.spyOn(api, 'unreadMessages').mockResolvedValue({ unread: 0 });
});

describe('the moderation queue entry', () => {
  it('is shown to an account the deployment names as a moderator', async () => {
    // A moderator's workspace role is still `owner`: the flag, not the role, decides.
    signedInAs({ ...owner, is_moderator: true });
    render(<App />);
    expect(await screen.findByRole('button', { name: 'Moderation queue' })).toBeInTheDocument();
  });

  it('is not shown to anyone else, owners included', async () => {
    signedInAs(owner);
    render(<App />);
    await waitFor(() => expect(api.authStatus).toHaveBeenCalled());
    // The rest of the menu is there; only the queue is missing.
    expect(await screen.findByRole('button', { name: 'Privacy & terms' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Moderation queue' })).not.toBeInTheDocument();
  });

  it('is not shown when nobody is signed in', async () => {
    signedInAs(null);
    render(<App />);
    await waitFor(() => expect(api.authStatus).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: 'Moderation queue' })).not.toBeInTheDocument();
  });
});

/**
 * The account flows exist on the server; these prove they exist in the UI too.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AccountMenu } from './AccountMenu';
import { ApiError, api } from '@/api/client';

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api, 'organizations').mockResolvedValue([
    { id: 'org-1', name: 'First Workspace', role: 'owner', current: true },
    { id: 'org-2', name: 'Second Workspace', role: 'owner', current: false },
  ]);
});

describe('changing the password', () => {
  it('says that other devices were signed out', async () => {
    const change = vi.spyOn(api, 'changePassword').mockResolvedValue({} as never);
    render(<AccountMenu onSignedOut={() => {}} />);

    fireEvent.click(screen.getByTestId('account-toggle'));
    fireEvent.click(await screen.findByTestId('change-password'));
    fireEvent.change(screen.getByTestId('current-password'), { target: { value: 'old password 12' } });
    fireEvent.change(screen.getByTestId('new-password'), { target: { value: 'new password 1234' } });
    fireEvent.submit(screen.getByTestId('new-password').closest('form')!);

    await waitFor(() =>
      expect(change).toHaveBeenCalledWith('old password 12', 'new password 1234'),
    );
    expect(await screen.findByTestId('account-notice')).toHaveTextContent('signed out');
  });

  it('shows the reason from the server when the current password is wrong', async () => {
    vi.spyOn(api, 'changePassword').mockRejectedValue(
      new ApiError(400, 'The current password is not correct.'),
    );
    render(<AccountMenu onSignedOut={() => {}} />);

    fireEvent.click(screen.getByTestId('account-toggle'));
    fireEvent.click(await screen.findByTestId('change-password'));
    fireEvent.change(screen.getByTestId('current-password'), { target: { value: 'wrong one 123' } });
    fireEvent.change(screen.getByTestId('new-password'), { target: { value: 'new password 1234' } });
    fireEvent.submit(screen.getByTestId('new-password').closest('form')!);

    expect(await screen.findByTestId('account-error')).toHaveTextContent('not correct');
  });
});

describe('workspaces', () => {
  it('offers a switcher only when there is more than one', async () => {
    render(<AccountMenu onSignedOut={() => {}} />);
    fireEvent.click(screen.getByTestId('account-toggle'));
    expect(await screen.findByTestId('workspace-select')).toBeInTheDocument();
  });

  it('hides the switcher for a single workspace', async () => {
    vi.spyOn(api, 'organizations').mockResolvedValue([
      { id: 'org-1', name: 'Only Workspace', role: 'owner', current: true },
    ]);
    render(<AccountMenu onSignedOut={() => {}} />);
    fireEvent.click(screen.getByTestId('account-toggle'));
    await screen.findByTestId('change-password');
    expect(screen.queryByTestId('workspace-select')).toBeNull();
  });
});

describe('deleting the account', () => {
  it('states what is destroyed and asks for the password', async () => {
    const remove = vi.spyOn(api, 'deleteAccount').mockResolvedValue(undefined as never);
    const signedOut = vi.fn();
    render(<AccountMenu onSignedOut={signedOut} />);

    fireEvent.click(screen.getByTestId('account-toggle'));
    fireEvent.click(await screen.findByTestId('delete-account'));
    expect(screen.getByText(/It cannot be undone/)).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('delete-password'), { target: { value: 'my password 12' } });
    fireEvent.click(screen.getByTestId('confirm-data'));
    fireEvent.submit(screen.getByTestId('delete-password').closest('form')!);

    await waitFor(() => expect(remove).toHaveBeenCalledWith('my password 12', true));
    expect(signedOut).toHaveBeenCalled();
  });
});

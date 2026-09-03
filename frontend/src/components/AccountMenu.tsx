/**
 * The account flows, reachable from the topbar.
 *
 * Change a password, switch workspace, or delete the account. Each was
 * implemented on the server and had no way in from the UI, which is the same
 * as not existing.
 */

import { useEffect, useState, type FormEvent } from 'react';
import { ApiError, api } from '@/api/client';

type Workspace = { id: string; name: string; role: string; current: boolean };

export function AccountMenu({ onSignedOut }: { onSignedOut: () => void }) {
  const [open, setOpen] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [panel, setPanel] = useState<'none' | 'password' | 'delete'>('none');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [deletePassword, setDeletePassword] = useState('');
  const [confirmData, setConfirmData] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    api.organizations().then(setWorkspaces).catch(() => setWorkspaces([]));
  }, [open]);

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const changePassword = (event: FormEvent) => {
    event.preventDefault();
    void run(async () => {
      await api.changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setPanel('none');
      setNotice('Password changed. Every other signed-in device was signed out.');
    });
  };

  const deleteAccount = (event: FormEvent) => {
    event.preventDefault();
    void run(async () => {
      await api.deleteAccount(deletePassword, confirmData);
      onSignedOut();
    });
  };

  return (
    <div className="stack stack--tight" data-testid="account-menu">
      <button className="btn btn--sm btn--ghost" onClick={() => setOpen(!open)} data-testid="account-toggle">
        Account
      </button>
      {open && (
        <div className="panel stack stack--tight" style={{ minWidth: '20rem' }}>
          {workspaces.length > 1 && (
            <label className="field">
              <span className="field__label">Workspace</span>
              <select
                data-testid="workspace-select"
                value={workspaces.find((w) => w.current)?.id ?? ''}
                onChange={(e) =>
                  void run(async () => {
                    await api.switchOrganization(e.target.value);
                    // The tenant scope lives on the session, so everything on
                    // screen belongs to the workspace we just left.
                    window.location.reload();
                  })
                }
              >
                {workspaces.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </label>
          )}

          <div className="row row--tight">
            <button
              className="btn btn--sm"
              onClick={() => setPanel(panel === 'password' ? 'none' : 'password')}
              data-testid="change-password"
            >
              Change password
            </button>
            <button
              className="btn btn--sm btn--danger"
              onClick={() => setPanel(panel === 'delete' ? 'none' : 'delete')}
              data-testid="delete-account"
            >
              Delete account
            </button>
          </div>

          {panel === 'password' && (
            <form className="stack stack--tight" onSubmit={changePassword}>
              <label className="field">
                <span className="field__label">Current password</span>
                <input
                  type="password" autoComplete="current-password" required
                  value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)}
                  data-testid="current-password"
                />
              </label>
              <label className="field">
                <span className="field__label">New password</span>
                <input
                  type="password" autoComplete="new-password" required minLength={12}
                  value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                  data-testid="new-password"
                />
                <span className="field__hint">
                  At least 12 characters. Changing it signs out every other device.
                </span>
              </label>
              <button className="btn btn--primary btn--sm" disabled={busy} type="submit">
                {busy ? 'Saving…' : 'Change password'}
              </button>
            </form>
          )}

          {panel === 'delete' && (
            <form className="stack stack--tight" onSubmit={deleteAccount}>
              <div className="notice notice--risk">
                <div className="small">
                  This erases the account, and any workspace where you are the only member —
                  with every applicant case, run and claim inside it. It cannot be undone.
                </div>
              </div>
              <label className="field">
                <span className="field__label">Confirm with your password</span>
                <input
                  type="password" autoComplete="current-password" required
                  value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)}
                  data-testid="delete-password"
                />
              </label>
              <label className="row row--tight small">
                <input
                  type="checkbox" checked={confirmData}
                  onChange={(e) => setConfirmData(e.target.checked)}
                  data-testid="confirm-data"
                />
                Yes, delete my applicant cases too
              </label>
              <button className="btn btn--danger btn--sm" disabled={busy} type="submit">
                {busy ? 'Deleting…' : 'Delete my account'}
              </button>
            </form>
          )}

          {notice && <div className="notice notice--ok small" data-testid="account-notice">{notice}</div>}
          {error && <div className="notice notice--risk small" role="alert" data-testid="account-error">{error}</div>}
        </div>
      )}
    </div>
  );
}

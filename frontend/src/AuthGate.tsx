import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { ApiError, api } from '@/api/client';
import type { AuthStatus } from '@/types';

export function AuthGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [organization, setOrganization] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.authStatus().then(setStatus).catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (!status) {
    return (
      <main className="auth-shell">
        <div className="panel auth-card" role="status">
          <h1>ASHYQ Apply</h1>
          <p className="muted">Connecting securely…</p>
          {error && <div className="notice notice--risk">{error}</div>}
        </div>
      </main>
    );
  }
  if (status.authenticated) return <>{children}</>;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (mode === 'login') await api.login(email, password);
      else await api.register({
        email, password, display_name: name, organization_name: organization,
      });
      setStatus(await api.authStatus());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-shell">
      <form className="panel auth-card stack" onSubmit={submit}>
        <div>
          <p className="screen__eyebrow">Private applicant workspace</p>
          <h1>{mode === 'login' ? 'Sign in to ASHYQ Apply' : 'Create your workspace'}</h1>
          <p className="muted small" style={{ marginTop: 'var(--space-3)' }}>
            Applicant records stay isolated inside your organization. University research never
            sends profile data to third-party websites.
          </p>
        </div>
        {mode === 'register' && (
          <>
            <label className="field">
              <span className="field__label">Your name</span>
              <input autoComplete="name" required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="field">
              <span className="field__label">Workspace name</span>
              <input required maxLength={120} value={organization} onChange={(e) => setOrganization(e.target.value)} />
            </label>
          </>
        )}
        <label className="field">
          <span className="field__label">Email</span>
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">Password</span>
          <input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                 minLength={mode === 'register' ? 12 : undefined} required value={password}
                 onChange={(e) => setPassword(e.target.value)} />
          {mode === 'register' && <span className="field__hint">At least 12 characters.</span>}
        </label>
        {error && <div className="notice notice--risk" role="alert">{error}</div>}
        <button className="btn btn--primary" disabled={busy} type="submit">
          {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create workspace'}
        </button>
        {status.registration_enabled && (
          <button className="btn btn--ghost" type="button" onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login'); setError('');
          }}>
            {mode === 'login' ? 'Create a new workspace' : 'I already have an account'}
          </button>
        )}
      </form>
    </main>
  );
}

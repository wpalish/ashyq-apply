import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { ApiError, api } from '@/api/client';
import { BrandSun } from '@/components/primitives';
import type { AuthStatus } from '@/types';

const MIN_PASSWORD = 12;

/**
 * Round 7's account screen: the brand and what the product promises beside
 * the form, so the first page a family sees says what this is before it asks
 * for an email. The night panel is the reveal's; on a phone it shrinks to the
 * brand and one line so the form stays on the first screen.
 */
function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <main className="auth-shell auth-shell--split">
      <section className="auth-hero" aria-label="About ASHYQ Apply">
        <span className="brand__mark auth-hero__brand">
          <BrandSun size={32} />
          <span>ASHYQ <span className="brand__apply">Apply</span></span>
        </span>
        <p className="auth-hero__title">Find where you can study{'\u00A0'}— and what it will cost</p>
        <ul className="auth-hero__facts">
          <li>Every figure links to the university's own page, with the date it was read.</li>
          <li>Requirements, your profile and money stay three separate answers.</li>
          <li>Nothing here predicts a decision: admission is decided by the university.</li>
        </ul>
      </section>
      {children}
    </main>
  );
}

export function AuthGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [organization, setOrganization] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  // A reset link lands on #/reset?token=… — the token comes from the email,
  // never from anything this page knows.
  const [resetToken, setResetToken] = useState(() =>
    new URLSearchParams(window.location.hash.split('?')[1] ?? '').get('token') ?? '',
  );

  useEffect(() => {
    api.authStatus().then(setStatus).catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (!status) {
    return (
      <AuthFrame>
        <div className="panel auth-card" role="status">
          <h1>ASHYQ Apply</h1>
          <p className="muted">Connecting securely…</p>
          {error && <div className="notice notice--risk">{error}</div>}
        </div>
      </AuthFrame>
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

  if (resetToken) {
    const finishReset = async (event: FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError('');
      try {
        await api.confirmPasswordReset(resetToken, password);
        window.location.hash = '';
        setStatus(await api.authStatus());
      } catch (e) {
        setError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    };
    return (
      <AuthFrame>
        <form className="panel auth-card stack" onSubmit={finishReset}>
          <h1>Choose a new password</h1>
          <label className="field">
            <span className="field__label">New password</span>
            <input
              type="password" autoComplete="new-password" required minLength={12}
              value={password} onChange={(e) => setPassword(e.target.value)}
              data-testid="reset-password"
            />
            <span className="field__hint">At least 12 characters.</span>
          </label>
          {error && <div className="notice notice--risk" role="alert">{error}</div>}
          <button className="btn btn--primary" disabled={busy} type="submit">
            {busy ? 'Please wait…' : 'Set password and sign in'}
          </button>
          <button className="btn btn--ghost" type="button" onClick={() => {
            window.location.hash = '';
            setResetToken('');
          }}>Back to sign in</button>
        </form>
      </AuthFrame>
    );
  }

  const requestReset = async () => {
    setBusy(true);
    setError('');
    try {
      const answer = await api.requestPasswordReset(email);
      // The wording is the server's, and says nothing about whether the
      // address has an account.
      setNotice(
        answer.reset_link
          ? `${answer.detail} (development build: ${answer.reset_link})`
          : answer.detail,
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFrame>
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
              <input data-testid="auth-name" autoComplete="name" required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="field">
              <span className="field__label">Workspace name</span>
              <input data-testid="auth-organization" required maxLength={120} value={organization} onChange={(e) => setOrganization(e.target.value)} />
            </label>
          </>
        )}
        <label className="field">
          <span className="field__label">Email</span>
          <input data-testid="auth-email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">Password</span>
          <input data-testid="auth-password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                 minLength={mode === 'register' ? MIN_PASSWORD : undefined} required value={password}
                 onChange={(e) => setPassword(e.target.value)} />
          {mode === 'register' && (
            <span className="field__hint" data-testid="password-count">
              At least {MIN_PASSWORD} characters
              {password.length > 0 && (password.length < MIN_PASSWORD
                ? ` · ${password.length} so far`
                : ' · long enough')}
              .
            </span>
          )}
        </label>
        {error && <div className="notice notice--risk" role="alert">{error}</div>}
        {notice && <div className="notice notice--ok small" data-testid="reset-notice">{notice}</div>}
        <button className="btn btn--primary" data-testid="auth-submit" disabled={busy} type="submit">
          {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create workspace'}
        </button>
        {mode === 'login' && (
          <button
            className="btn btn--ghost btn--sm" type="button" disabled={busy || !email}
            onClick={requestReset} data-testid="forgot-password"
          >
            I forgot my password
          </button>
        )}
        {status.registration_enabled && (
          <button className="btn btn--ghost" data-testid="auth-mode-toggle" type="button" onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login'); setError('');
          }}>
            {mode === 'login' ? 'Create a new workspace' : 'I already have an account'}
          </button>
        )}
      </form>
    </AuthFrame>
  );
}

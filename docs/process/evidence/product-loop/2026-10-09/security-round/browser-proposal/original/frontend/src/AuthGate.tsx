import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { ApiError, api } from '@/api/client';
import type { AuthStatus } from '@/types';
import { PublicLanding } from '@/components/PublicLanding';
import { LegalScreen } from '@/screens/LegalScreen';

export function AuthGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [mode, setMode] = useState<'login' | 'register'>(() => window.location.hash.includes('create=1') ? 'register' : 'login');
  const [route, setRoute] = useState(() => window.location.hash);
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
    if (!status?.authenticated) document.documentElement.setAttribute('data-theme', 'light');
  }, [status?.authenticated]);

  useEffect(() => {
    api.authStatus().then(setStatus).catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => {
    const onHashChange = () => setRoute(window.location.hash);
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    if (route.startsWith('#/sign-in?create=1')) setMode('register');
  }, [route]);

  if (route.startsWith('#/legal')) {
    return (
      <div className="public-legal">
        <header><a className="landing__brand" href={status?.authenticated ? '#/home' : '#/welcome'}><img src="/brand/unimatch-mark.png" alt="" /> Unimatch</a><a href={status?.authenticated ? '#/home' : '#/welcome'}>Back</a></header>
        <main><LegalScreen /></main>
      </div>
    );
  }
  if (!status?.authenticated && (!route || route === '#/welcome' || route.startsWith('#how-it-works') || route.startsWith('#why-unimatch'))) {
    return <PublicLanding />;
  }

  if (!status) {
    return (
      <main className="auth-shell">
        <div className="panel auth-card" role="status">
          <h1>Unimatch</h1>
          <p className="muted">Connecting securely…</p>
          {error && <div className="notice notice--risk">{error}</div>}
        </div>
      </main>
    );
  }
  if (status.authenticated) return <>{children}</>;
  // Older servers do not advertise this capability and support recovery.
  const passwordResetEnabled = status.password_reset_enabled !== false;
  const backToSignIn = () => {
    window.location.hash = '#/sign-in';
    setRoute('#/sign-in');
    setResetToken('');
  };

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
    if (!passwordResetEnabled) {
      return (
        <main className="auth-shell">
          <div className="panel auth-card stack">
            <h1>Password recovery</h1>
            <p className="muted">Password recovery is currently unavailable.</p>
            <button className="btn btn--ghost" type="button" onClick={backToSignIn}>
              Back to sign in
            </button>
          </div>
        </main>
      );
    }
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
      <main className="auth-shell">
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
          <button className="btn btn--ghost" type="button" onClick={backToSignIn}>Back to sign in</button>
        </form>
      </main>
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
    <main className="auth-shell auth-shell--unimatch">
      <div className="auth-experience">
        <div className="auth-experience__visual">
          <img src="/brand/unimatch-journey.png" alt="A small Unimatch robot overlooks a university and a mountain lake" />
          <div>
            <span className="home-eyebrow">SAME STUDENTS. BIGGER HORIZONS.</span>
            <h1>Global opportunities<br />start with <em>you.</em></h1>
            <p>Personalized research. Real information. A clearer path.</p>
          </div>
        </div>
      <form className="panel auth-card stack" onSubmit={submit}>
        <div>
          <a className="landing__brand" href="#/welcome"><img src="/brand/unimatch-mark.png" alt="" /> Unimatch</a>
          <div className="auth-tabs" role="tablist" aria-label="Account">
            <button type="button" role="tab" aria-selected={mode === 'login'} onClick={() => setMode('login')}>Sign in</button>
            {status.registration_enabled && <button type="button" role="tab" aria-selected={mode === 'register'} onClick={() => setMode('register')}>Create account</button>}
          </div>
          <h1>{mode === 'login' ? 'Welcome back.' : 'Start your journey.'}</h1>
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
                 minLength={mode === 'register' ? 12 : undefined} required value={password}
                 onChange={(e) => setPassword(e.target.value)} />
          {mode === 'register' && <span className="field__hint">At least 12 characters.</span>}
        </label>
        {!passwordResetEnabled && (
          <div className="notice small">
            <p>Password recovery is currently unavailable.</p>
            {mode === 'register' && <p>Save your password somewhere safe. You will need it to sign in.</p>}
          </div>
        )}
        {error && <div className="notice notice--risk" role="alert">{error}</div>}
        {notice && <div className="notice notice--ok small" data-testid="reset-notice">{notice}</div>}
        <button className="btn btn--primary" data-testid="auth-submit" disabled={busy} type="submit">
          {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create workspace'}
        </button>
        {mode === 'login' && passwordResetEnabled && (
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
        <a className="auth-legal-link" href="#/legal">Privacy &amp; terms · Drafts awaiting legal review</a>
      </form>
      </div>
    </main>
  );
}

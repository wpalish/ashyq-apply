import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { ApiError, api } from '@/api/client';
import type { AuthStatus } from '@/types';
import { BookAuthShell } from '@/components/BookAuthShell';
import { Eye, EyeSlash, ArrowRight } from '@phosphor-icons/react';
import { useTranslation } from '@/lib/useTranslation';
import { PublicLanding } from '@/components/PublicLanding';
import { LegalScreen } from '@/screens/LegalScreen';
import { APPLICANT_OWNER_KEY, bindApplicantOwner } from '@/lib/applicantStorage';
import { DraftIdentityContext, draftIdentity } from '@/lib/draftIdentity';

export function AuthGate({ children }: { children: ReactNode }) {
  const { locale, setLocale } = useTranslation(); const ru=locale!=='en';
  const copy=(en:string,other:string)=>ru?other:en;
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
  const [showPassword, setShowPassword] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState('');
  // A reset link lands on #/reset?token=… — the token comes from the email,
  // never from anything this page knows.
  const [resetToken, setResetToken] = useState(() =>
    new URLSearchParams(window.location.hash.split('?')[1] ?? '').get('token') ?? '',
  );

  useEffect(() => {
    if (!status?.authenticated) document.documentElement.setAttribute('data-theme', 'light');
  }, [status?.authenticated]);

  const refreshAfterAuthentication = async () => {
    const ownerAtRequest = window.localStorage.getItem(APPLICANT_OWNER_KEY);
    if (ownerAtRequest?.startsWith('transition:')) return;
    const next = await api.authStatus();
    // Another tab may have completed its own login while this reply was pending.
    // Preserve its revalidated private tree; an older reply cannot bind or clear its data.
    if (window.localStorage.getItem(APPLICANT_OWNER_KEY) !== ownerAtRequest) return;
    bindApplicantOwner(next);
    setStatus(next);
  };

  useEffect(() => {
    let generation = 0;
    const reloadPrincipal = () => {
      const request = ++generation;
      let ownerAtRequest: string | null;
      try { ownerAtRequest = window.localStorage.getItem(APPLICANT_OWNER_KEY); }
      catch {
        setError('Browser storage is unavailable. Private draft restoration is locked.');
        return;
      }
      api.authStatus().then((next) => {
        if (request !== generation) return;
        if (window.localStorage.getItem(APPLICANT_OWNER_KEY) !== ownerAtRequest) {
          setStatus(null);
          if (!window.localStorage.getItem(APPLICANT_OWNER_KEY)?.startsWith('transition:')) reloadPrincipal();
          return;
        }
        bindApplicantOwner(next);
        setStatus(next);
      }).catch((e) => {
        if (request === generation) setError(e instanceof Error ? e.message : String(e));
      });
    };
    const changed = (event: StorageEvent) => {
      if (event.key !== APPLICANT_OWNER_KEY) return;
      ++generation;
      setStatus(null); // Unmount private memory before asking which principal owns the cookie now.
      if (!event.newValue?.startsWith('transition:')) reloadPrincipal();
    };
    window.addEventListener('storage', changed);
    reloadPrincipal();
    return () => { ++generation; window.removeEventListener('storage', changed); };
  }, []);

  useEffect(() => {
    const onHashChange = () => {
      setRoute(window.location.hash);
      setResetToken(window.location.hash.startsWith('#/reset?') ? new URLSearchParams(window.location.hash.split('?')[1]).get('token') ?? '' : '');
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    if (route.startsWith('#/sign-in?create=1')) setMode('register');
  }, [route]);

  if (route.startsWith('#/legal') && !status?.authenticated) {
    return (
      <div className="public-legal">
        <header><a className="landing__brand" href={status?.authenticated ? '#/home' : '#/welcome'}><img src="/brand/unimatch-orbit.svg" alt="" /> Unimatch</a><a href={status?.authenticated ? '#/home' : '#/welcome'}>Back</a></header>
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
  if (status.authenticated) {
    // Only an explicit auth-disabled server may use anonymous/demo recovery.
    // Authenticated product state always receives its verified tree identity.
    const identity = status.enabled ? draftIdentity(status.principal) : undefined;
    const owner = status.enabled ? `auth:${identity ?? 'identity-unavailable'}` : 'demo';
    return <DraftIdentityContext.Provider key={owner} value={identity}>{children}</DraftIdentityContext.Provider>;
  }
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
      await refreshAfterAuthentication();
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
      if (ru && password !== confirmPassword) { setError('Пароли не совпадают. Проверь оба поля.'); return; }
      setBusy(true);
      setError('');
      try {
        await api.confirmPasswordReset(resetToken, password);
        window.location.hash = '';
        await refreshAfterAuthentication();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    };
    return (
      <BookAuthShell>
        <form className="panel auth-card stack" onSubmit={finishReset}>
          <h1>{copy('Choose a new password','Новый пароль')}</h1><p className="auth-description">{copy('Choose a new password for your Unimatch account.','Придумай новый пароль для входа в ваш аккаунт Unimatch.')}</p>
          <label className="field">
            <span className="field__label">{copy('New password','Новый пароль')}</span>
            <input
              type="password" autoComplete="new-password" required minLength={12}
              value={password} onChange={(e) => setPassword(e.target.value)}
              data-testid="reset-password"
            />
            <span className="field__hint">{copy('At least 12 characters.','Не короче 12 символов.')}</span>
          </label>
          {ru&&<label className="field"><span className="field__label">Подтвердите пароль</span><input type="password" autoComplete="new-password" required minLength={12} value={confirmPassword} onChange={event=>setConfirmPassword(event.target.value)}/><span className="field__hint">Не короче12символов.</span></label>}
          {error && <div className="notice notice--risk" role="alert">{error}</div>}
          <button className="btn btn--primary" disabled={busy} type="submit">
            {busy ? copy('Please wait…','Подожди…') : copy('Set password and sign in','Сохранить пароль')}<ArrowRight size={20}/>
          </button>
          <button className="btn btn--ghost auth-return" type="button" onClick={backToSignIn}>{copy('Back to sign in','← Вернуться на страницу входа')}</button>
        </form>
      </BookAuthShell>
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

  if (route.startsWith('#/forgot')) return <BookAuthShell><form className="panel auth-card stack" onSubmit={event => { event.preventDefault(); void requestReset(); }}>
    <h1>{copy('Recover your password','Восстановление доступа')}</h1><p className="auth-description">{copy('Enter your email. If recovery is available for the account, you will receive the next steps.','Введи адрес электронной почты, который использовал при регистрации.')}</p>
    <label className="field"><span className="field__label">{copy('Email','Почта')}</span><input type="email" autoComplete="email" placeholder={ru?'имя@почта.kz':'you@example.com'} required value={email} onChange={event => setEmail(event.target.value)} /><span className="field__hint">{copy('If the account exists and recovery is enabled, we will send the next steps.','Если аккаунт существует и восстановление доступно, мы отправим письмо.')}</span></label>
    {!passwordResetEnabled && <p role="status">{copy('Password recovery is currently unavailable.','Восстановление доступа сейчас недоступно.')}</p>}
    {error && <div className="notice notice--risk" role="alert">{error}</div>}{notice && <div className="notice" role="status">{notice}</div>}
    <button className="btn btn--primary" disabled={busy || !passwordResetEnabled}>{busy ? copy('Please wait…','Подожди…') : copy('Send recovery instructions','Отправить письмо')}<ArrowRight size={20}/></button><button className="btn btn--ghost auth-return" type="button" onClick={backToSignIn}>{copy('Back to sign in','← Вернуться на страницу входа')}</button>
  </form></BookAuthShell>;

  return (
    <BookAuthShell split>
      <form className="panel auth-card stack" onSubmit={submit}>
        <div>
          <div className={`auth-tabs ${ru?'auth-tabs--reference':''}`} role="tablist" aria-label="Account">
            <button type="button" role="tab" aria-selected={mode === 'login'} onClick={() => setMode('login')}>Sign in</button>
            {status.registration_enabled && <button type="button" role="tab" aria-selected={mode === 'register'} onClick={() => setMode('register')}>Create account</button>}
          </div>
          <h1>{mode === 'login' ? copy('Welcome back.','Вход') : copy('Start your journey.','Создай аккаунт')}</h1>{mode==='login'&&<h2 className="auth-welcome">{copy('Welcome back!','Добро пожаловать обратно!')}</h2>}<p className="auth-description">{mode==='login'?copy('Sign in to continue planning your applications.','Войди в свой аккаунт, чтобы продолжить работу над поступлением.'):copy('Start your international education journey with Unimatch.','Начни путь к международному образованию с Unimatch.')}</p>

        </div>
        {mode === 'register' && (
          <>
            <label className="field">
              <span className="field__label">{copy('Your name','Имя')}</span>
              <input data-testid="auth-name" autoComplete="name" required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="field">
              <span className="field__label">{copy('Workspace name','Название рабочего пространства')}</span>
              <input data-testid="auth-organization" required maxLength={120} value={organization} onChange={(e) => setOrganization(e.target.value)} />
            </label>
          </>
        )}
        <label className="field">
          <span className="field__label">{copy('Email','Почта')}</span>
          <input data-testid="auth-email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">{copy('Password','Пароль')}</span>
          <span className="auth-password"><input data-testid="auth-password" type={showPassword ? 'text' : 'password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                 minLength={mode === 'register' ? 12 : undefined} required value={password}
                 onChange={(e) => setPassword(e.target.value)} /><button type="button" aria-label={showPassword?copy('Hide password','Скрыть пароль'):copy('Show password','Показать пароль')} onClick={()=>setShowPassword(value=>!value)}>{showPassword?<EyeSlash size={21}/>:<Eye size={21}/>}</button></span>
          {mode === 'register' && <span className="field__hint">{copy('At least 12 characters.','Не короче 12 символов.')}</span>}
        </label>
        <label className="row small auth-show-password"><input type="checkbox" checked={showPassword} onChange={event => setShowPassword(event.target.checked)} />Show password</label>
        {mode === 'login' && passwordResetEnabled && <a className="small" href="#/forgot">{copy('Password recovery','Забыли пароль?')}</a>}
        {!passwordResetEnabled && (
          <div className="notice small">
            <p>Password recovery is currently unavailable.</p>
            {mode === 'register' && <p>Save your password somewhere safe. You will need it to sign in.</p>}
          </div>
        )}
        {error && <div className="notice notice--risk" role="alert">{error}</div>}
        {notice && <div className="notice notice--ok small" data-testid="reset-notice">{notice}</div>}
        <button className="btn btn--primary" data-testid="auth-submit" disabled={busy} type="submit">
          {busy ? copy('Please wait…','Подожди…') : mode === 'login' ? copy('Sign in','Войти') : copy('Create workspace','Создать аккаунт')}<ArrowRight size={20}/>
        </button>
        {mode === 'login' && passwordResetEnabled && !ru && (
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
            {mode === 'login' ? ru?<><span>Ещё нет аккаунта?</span><strong>Создать аккаунт</strong></>:'Create a new workspace' : copy('I already have an account','Уже есть аккаунт? Войти')}
          </button>
        )}
        {mode==='register'&&<div className="auth-languages" role="group" aria-label={copy('Interface language','Язык интерфейса')}>{(['ru','kk','en'] as const).map(value=><button key={value} type="button" aria-pressed={locale===value} onClick={()=>setLocale(value)}>{{ru:'Русский',kk:'Қазақша',en:'English'}[value]}</button>)}</div>}
        <details className="auth-privacy-note"><summary>{copy('How your data is used','Как используются данные')}</summary><p>{copy('University searches use degree, subject and intake. Names, contacts, grades and budget are excluded from those queries.','Поисковые запросы используют ступень, направление и период поступления. Имя, контакты, оценки и бюджет в эти запросы не передаются.')}</p></details>
        <a className="auth-legal-link" href="#/legal">{copy('Privacy & terms · Drafts awaiting legal review','Конфиденциальность и правила · Проект на юридической проверке')}</a>
      </form>
    </BookAuthShell>
  );
}

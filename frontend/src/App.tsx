/**
 * Application shell: sidebar navigation, a status bar, and one screen at a time.
 *
 * Navigation is a plain state machine rather than a router. The workflow is
 * linear and gated — you cannot read a shortlist that has not been produced —
 * and disabled nav items say *why* they are disabled instead of vanishing.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useStore } from '@/lib/store';
import { PaywallNotice } from '@/components/PaywallNotice';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { AccountMenu } from '@/components/AccountMenu';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { CaseScreen } from '@/screens/CaseScreen';
import { redesignCopy } from '@/lib/redesignCopy';
import { PreferencesScreen } from '@/screens/PreferencesScreen';
import { ProgressScreen } from '@/screens/ProgressScreen';
import { ShortlistScreen } from '@/screens/ShortlistScreen';
import { FundingScreen } from '@/screens/FundingScreen';
import { ApprovedScreen } from '@/screens/ApprovedScreen';
import { DocumentsScreen } from '@/screens/DocumentsScreen';
import { SourcesScreen } from '@/screens/SourcesScreen';
import { ExportScreen } from '@/screens/ExportScreen';
import { LegalScreen } from '@/screens/LegalScreen';
import { FeedScreen } from '@/screens/FeedScreen';
import { DiscoverScreen } from '@/screens/DiscoverScreen';
import { PersonScreen } from '@/screens/PersonScreen';
import { MessagesScreen } from '@/screens/MessagesScreen';
import { ModerationScreen } from '@/screens/ModerationScreen';
import { Chip } from '@/components/primitives';
import { api } from '@/api/client';
import { LOCALES, t as translate, type Locale, type MessageKey } from '@/lib/i18n';
import { useTranslation } from '@/lib/useTranslation';
import type { PersonCard } from '@/types';

export type ScreenId =
  | 'case' | 'profile' | 'preferences' | 'progress' | 'shortlist' | 'funding'
  | 'approved' | 'documents' | 'sources' | 'export'
  | 'feed' | 'discover' | 'messages' | 'me' | 'person' | 'moderation' | 'legal';

/**
 * The numbers are not decoration: the case screens are a sequence, and 04
 * genuinely cannot be read before 03 has produced anything. Community is not a
 * sequence, so those entries carry no number.
 */
const SCREENS: { id: ScreenId; num?: string; label: MessageKey; group: MessageKey }[] = [
  { id: 'profile', num: '01', label: 'nav.profile', group: 'nav.group.prepare' },
  { id: 'preferences', num: '02', label: 'nav.preferences', group: 'nav.group.prepare' },
  { id: 'progress', num: '03', label: 'nav.progress', group: 'nav.group.research' },
  { id: 'shortlist', num: '04', label: 'nav.shortlist', group: 'nav.group.research' },
  { id: 'funding', num: '05', label: 'nav.funding', group: 'nav.group.research' },
  { id: 'sources', num: '06', label: 'nav.sources', group: 'nav.group.research' },
  { id: 'approved', num: '07', label: 'nav.approved', group: 'nav.group.decide' },
  { id: 'documents', num: '08', label: 'nav.documents', group: 'nav.group.decide' },
  { id: 'export', num: '09', label: 'nav.export', group: 'nav.group.decide' },
  { id: 'feed', label: 'nav.feed', group: 'nav.group.community' },
  { id: 'discover', label: 'nav.discover', group: 'nav.group.community' },
  { id: 'messages', label: 'nav.messages', group: 'nav.group.community' },
  { id: 'me', label: 'nav.me', group: 'nav.group.community' },
  { id: 'moderation', label: 'nav.moderation', group: 'nav.group.community' },
  // Listed rather than tucked into the footer, so that it has an address a
  // person can be sent to: "read the privacy policy" is a link, not a hunt.
  { id: 'legal', label: 'nav.legal', group: 'nav.group.about' },
];

/** The screen named by `#/…`, if it names one at all. */
function screenFromHash(): ScreenId | null {
  const id = window.location.hash.replace(/^#\/?/, '').split('?')[0];
  if (id === 'case') return 'case';
  return SCREENS.some((s) => s.id === id) ? (id as ScreenId) : null;
}

/**
 * A screen's name for a sentence, in the reader's language.
 *
 * Module scope rather than a closure over the hook's `t`: it would otherwise
 * be a new function on every render and a dependency of the memoised gate
 * check. `translate` reads the current locale when it is called, so this is
 * just as live as the hook.
 */
function label(id: ScreenId): string {
  const entry = SCREENS.find((s) => s.id === id);
  return entry ? translate(entry.label) : id;
}

/** Five stable destinations; detailed tools stay in contextual navigation. */
type SectionId = 'case' | 'shortlist' | 'plan' | 'community' | 'more';
const SECTIONS: { id: SectionId; icon: string; screens: ScreenId[] }[] = [
  { id: 'case', icon: '⌂', screens: ['case', 'profile', 'preferences', 'progress'] },
  { id: 'shortlist', icon: '◇', screens: ['shortlist', 'funding', 'sources'] },
  { id: 'plan', icon: '☷', screens: ['approved', 'documents'] },
  { id: 'community', icon: '◎', screens: ['feed', 'discover', 'messages', 'person'] },
  { id: 'more', icon: '···', screens: ['export', 'me', 'moderation', 'legal'] },
];

const THEME_KEY = 'ashyq.theme';
type Theme = 'system' | 'light' | 'dark';

export default function App() {
  const {
    run, results, summary, error, clearError, capabilities,
    cases, savedProfile, switchCase, newCase, dirty, hydrated,
  } = useStore();
  const { t, locale, setLocale } = useTranslation();
  const [screen, setScreenState] = useState<ScreenId>(() => screenFromHash() ?? 'case');
  const [section, setSection] = useState<SectionId>(() => SECTIONS.find((s) => s.screens.includes(screenFromHash() ?? 'case'))?.id ?? 'case');
  const copy = redesignCopy[locale];
  const [redirected, setRedirected] = useState<string | null>(null);
  /** Ask before throwing away typing the applicant has not saved. */
  const confirmDiscard = () =>
    !dirty ||
    window.confirm(
      'You have unsaved changes to this profile. Leaving now discards them. '
      + 'Save first, or continue and lose them?',
    );
  // Who I am in the community, and whose profile is open. The community has no
  // gates, so this is the only navigation state it needs.
  const [me, setMe] = useState<PersonCard | null>(null);
  const [joined, setJoined] = useState(false);
  const [personId, setPersonId] = useState<string | null>(null);
  const [messagingWith, setMessagingWith] = useState<string | null>(null);
  const [unread, setUnread] = useState(0);
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return (window.localStorage.getItem(THEME_KEY) as Theme) ?? 'system';
    } catch {
      return 'system';
    }
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'system') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', theme);
    try {
      window.localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* a browser blocking storage should not break theming */
    }
  }, [theme]);

  useEffect(() => {
    api.socialMe()
      .then((state) => { setJoined(state.joined); setMe(state.profile); })
      .catch(() => { /* the community is optional; its absence must not block the case */ });
  }, []);

  /**
   * The unread badge.
   *
   * Read once on load and again whenever a conversation is closed, rather than
   * polled: nothing else in this app polls, and a timer that wakes a phone
   * every few seconds to ask a question whose answer is almost always "no" is
   * a battery cost the product has not earned. A message that arrives while
   * you are looking at another screen shows up on the next navigation.
   */
  const refreshUnread = useCallback(() => {
    api.unreadMessages()
      .then((state) => setUnread(state.unread))
      .catch(() => { /* a badge that cannot be fetched simply does not show */ });
  }, []);

  useEffect(() => { refreshUnread(); }, [refreshUnread, screen]);

  // Follow the workflow forward on its own, but never take the user backwards.
  useEffect(() => {
    if (!run) return;
    if (screen === 'profile' || screen === 'preferences') setScreen('progress');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.id]);

  const hasResults = results.length > 0;
  const approvedCount = results.filter((r) => r.user_decision === 'approved').length;
  const maybeCount = results.filter((r) => r.user_decision === 'maybe').length;
  const withChecklists = results.filter((r) => r.checklist).length;

  const collectingDocuments = Boolean(
    run
      && (run.stage === 'document_collection'
        || ((run.job_status === 'queued' || run.job_status === 'running')
          && approvedCount + maybeCount > 0)),
  );

  const gate: Record<ScreenId, string | null> = {
    case: null,
    profile: null,
    preferences: null,
    progress: run ? null : 'Start research first',
    shortlist: hasResults ? null : 'No results yet',
    funding: hasResults ? null : 'No results yet',
    sources: hasResults ? null : 'No results yet',
    approved: hasResults ? null : 'No results yet',
    // Also open while collection is in flight: the applicant pressed Collect
    // and the worker has not finished yet. Bouncing them off the screen they
    // just asked for would be the redirect fighting the workflow.
    documents:
      withChecklists > 0 || collectingDocuments
        ? null
        : 'Approve programmes, then collect documents',
    export: run ? null : 'Start research first',
    // The community does not depend on a research run, so nothing gates it.
    feed: null,
    discover: null,
    messages: null,
    me: null,
    moderation: null,
    person: null,
    // A privacy policy nobody can reach before signing up is not a policy.
    legal: null,
  };

  // The hash is the address of the screen: back and forward work, a reload
  // lands where it left off, and a link to a screen can be sent to someone.
  // The gates still decide what may be shown - a bookmark to #/shortlist made
  // before there were any results redirects to progress and says why.
  const setScreen = useCallback((next: ScreenId) => {
    setScreenState(next);
    setSection(SECTIONS.find((s) => s.screens.includes(next))?.id ?? 'case');
    const target = `#/${next}`;
    if (window.location.hash !== target) window.location.hash = target;
  }, []);

  // Only an address typed, bookmarked or arrived at through history is checked
  // against the gates. In-app navigation is already gated by the disabled nav
  // buttons, and re-checking on every state change made the redirect fight the
  // workflow: pressing "Collect documents" bounced the applicant back to
  // progress because the checklists did not exist *yet*.
  const gateRef = useRef(gate);
  gateRef.current = gate;
  const runRef = useRef(run);
  runRef.current = run;
  const hydratedRef = useRef(hydrated);
  hydratedRef.current = hydrated;

  const [pendingLink, setPendingLink] = useState<ScreenId | null>(null);

  const evaluateLink = useCallback((requested: ScreenId) => {
    const blocked = gateRef.current[requested];
    if (!blocked) {
      setScreenState(requested);
      setSection(SECTIONS.find((s) => s.screens.includes(requested))?.id ?? 'case');
      return;
    }
    const fallback: ScreenId = runRef.current ? 'progress' : 'profile';
    setRedirected(`${label(requested)}: ${blocked}.`);
    setScreen(fallback);
  }, [setScreen]);

  const openFromHash = useCallback(() => {
    const requested = screenFromHash();
    if (!requested) return;
    // Before the store has loaded, "no results yet" would be a statement about
    // an empty store rather than about the run. Show the screen and judge it
    // once there is something to judge.
    setScreenState(requested);
    if (!hydratedRef.current) {
      setPendingLink(requested);
      return;
    }
    evaluateLink(requested);
  }, [evaluateLink]);

  useEffect(() => {
    if (!hydrated || !pendingLink) return;
    evaluateLink(pendingLink);
    setPendingLink(null);
  }, [hydrated, pendingLink, evaluateLink]);

  useEffect(() => {
    window.addEventListener('hashchange', openFromHash);
    // Stamp the hash on first load so Back has somewhere to return to, and
    // check a deep link before rendering the screen it names.
    if (screenFromHash()) openFromHash();
    else window.location.replace(`#/${screen}`);
    return () => window.removeEventListener('hashchange', openFromHash);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openFromHash]);

  const badges: Partial<Record<ScreenId, number>> = {
    shortlist: results.length || undefined,
    approved: approvedCount + maybeCount || undefined,
    documents: withChecklists || undefined,
    sources: (summary ? summary.with_conflicts + summary.with_open_questions : 0) || undefined,
    messages: unread || undefined,
  };

  const activeSection = SECTIONS.find((s) => s.id === section)!;
  const primaryNav = <nav className="primary-nav" aria-label={copy.navigation}>
    {SECTIONS.map((item) => <button key={item.id} type="button" className="primary-nav__item"
      data-testid={`section-${item.id}`}
      aria-current={section === item.id ? 'page' : undefined}
      disabled={item.screens.every((id) => Boolean(gate[id]))}
      title={item.screens.every((id) => Boolean(gate[id])) ? gate[item.screens[0]!] ?? undefined : undefined}
      onClick={() => {
        const target = item.screens.find((id) => !gate[id]);
        if (target) setScreen(target);
        setSection(item.id);
      }}>
      <span className="primary-nav__icon" aria-hidden="true">{item.icon}</span><span>{copy[item.id]}</span>
    </button>)}
  </nav>;

  return (
    <div className="app app--redesign">
      <a className="skip-link" href="#main-content">{copy.skip}</a>
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark">ASHYQ Apply</span>
          <span className="brand__tag">
            {t('brand.tagline')}
          </span>
        </div>

        {primaryNav}
        <nav className={`nav context-nav${screen === 'case' ? ' context-nav--home' : ''}`} aria-label={copy.sections}>
          <div className="nav__group-label">{copy[section]}</div>
          {SCREENS.filter((s) => activeSection.screens.includes(s.id)).map((s) => {
            const blocked = gate[s.id];
            return (
              <div key={s.id}>
                <button
                  type="button"
                  className="nav__item"
                  aria-current={screen === s.id ? 'page' : undefined}
                  disabled={Boolean(blocked)}
                  title={blocked ?? undefined}
                  data-testid={`nav-${s.id}`}
                  onClick={() => {
                    // A deliberate move answers the explanation, so it goes.
                    setRedirected(null);
                    setScreen(s.id);
                  }}
                >
                  <span className="nav__num">{s.num ?? ''}</span>
                  <span>{t(s.label)}</span>
                  {badges[s.id] !== undefined && <span className="nav__badge">{badges[s.id]}</span>}
                </button>
              </div>
            );
          })}
        </nav>

        <div className={`stack stack--tight shell-settings${section === 'more' ? ' shell-settings--open' : ''}`}>
          <div className="field">
            <label className="field__label xs" htmlFor="theme">{t('appearance.label')}</label>
            <select
              id="theme"
              value={theme}
              onChange={(e) => setTheme(e.target.value as Theme)}
            >
              <option value="system">{t('appearance.system')}</option>
              <option value="light">{t('appearance.light')}</option>
              <option value="dark">{t('appearance.dark')}</option>
            </select>
          </div>
          <div className="field">
            <label className="field__label xs" htmlFor="locale">{t('language.label')}</label>
            {/* Russian and Kazakh are partial on purpose: a string whose terms
                are still under review stays in English rather than being
                machine-translated. See docs/i18n/GLOSSARY.md. */}
            <select
              id="locale"
              data-testid="locale"
              value={locale}
              onChange={(e) => setLocale(e.target.value as Locale)}
            >
              {LOCALES.map((option) => (
                <option key={option.id} value={option.id}>{option.label}</option>
              ))}
            </select>
          </div>
          <p className="xs faint" style={{ margin: 0 }}>
            {t('brand.disclaimer')}
          </p>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <span className="topbar__title">{copy[section]}</span>
          <Chip tone={(run?.demo_mode ?? capabilities?.demo_mode) ? 'demo' : 'accent'}>
            {capabilities ? ((run?.demo_mode ?? capabilities.demo_mode) ? copy.modeDemo : copy.modeLive) : copy.connecting}
          </Chip>
          <div className="topbar__spacer" />
          {cases.length > 1 && <label className="row row--tight xs muted" htmlFor="case-switcher">
            {copy.applicant}
            <select
              id="case-switcher"
              value={savedProfile?.id ?? ''}
              onChange={(event) => {
                // Switching case replaces the form. Unsaved edits are the
                // applicant's typing, so they are never discarded silently.
                if (!confirmDiscard()) {
                  event.target.value = savedProfile?.id ?? '';
                  return;
                }
                if (event.target.value) void switchCase(event.target.value);
                else newCase();
              }}
            >
              <option value="">{t('topbar.newApplicant')}</option>
              {cases.map((item) => (
                <option key={item.id} value={item.profile_id}>
                  {item.display_name} · {item.run_count} run{item.run_count === 1 ? '' : 's'}
                </option>
              ))}
            </select>
          </label>}
          <div className={`row row--tight shell-account${section === 'more' ? ' shell-account--open' : ''}`}>
          <button className="btn btn--sm" type="button" onClick={() => {
            if (!confirmDiscard()) return;
            newCase(); setScreen('profile');
          }}>{t('topbar.newCase')}</button>
          <AccountMenu onSignedOut={() => window.location.reload()} />
          <button className="btn btn--sm btn--ghost" data-testid="sign-out" type="button" onClick={async () => {
            await api.logout(); window.location.reload();
          }}>{t('topbar.signOut')}</button>
          </div>
        </header>
        {(run?.job_running || run?.job_status === 'queued' || run?.job_status === 'running') && screen !== 'progress' &&
          <div className="shell-run" role="status"><span>{copy.working}</span><button className="btn btn--sm" onClick={() => setScreen('progress')}>{copy.progress} →</button></div>}

        {redirected && (
          <div style={{ padding: 'var(--space-4) var(--space-6) 0' }}>
            <div className="notice notice--warn" role="status" data-testid="redirect-notice">
              <div style={{ flex: 1 }}>
                <strong>Not available yet.</strong> {redirected} You were taken to the screen that
                comes first.
              </div>
              <button className="btn btn--sm btn--ghost" onClick={() => setRedirected(null)}>
                Dismiss
              </button>
            </div>
          </div>
        )}

        {error && (
          <div style={{ padding: 'var(--space-4) var(--space-6) 0' }}>
            <div className="notice notice--risk" role="alert">
              <div style={{ flex: 1 }}>
                <strong>Something went wrong.</strong> {error}
              </div>
              <button className="btn btn--sm btn--ghost" onClick={clearError}>Dismiss</button>
            </div>
          </div>
        )}

        {/* Mounted once: the paywall is global state, raised by whichever
            screen asked for locked material. */}
        <PaywallNotice />

        <main className="screen" id="main-content" tabIndex={-1}>
          {/* Scoped to the screen, so one broken screen cannot take the
              sidebar and the case switcher down with it. */}
          <ErrorBoundary label={`the ${screen} screen`} key={screen}>
          {screen === 'case' && <CaseScreen onNavigate={setScreen} />}
          {screen === 'profile' && <ProfileScreen onNext={() => setScreen('preferences')} />}
          {screen === 'preferences' && <PreferencesScreen onStarted={() => setScreen('progress')} />}
          {screen === 'progress' && <ProgressScreen onDone={() => setScreen('shortlist')} />}
          {screen === 'shortlist' && <ShortlistScreen />}
          {screen === 'funding' && <FundingScreen />}
          {screen === 'sources' && <SourcesScreen />}
          {screen === 'approved' && <ApprovedScreen onCollect={() => setScreen('documents')} />}
          {screen === 'documents' && <DocumentsScreen />}
          {screen === 'export' && <ExportScreen />}
          {screen === 'legal' && <LegalScreen />}
          {screen === 'feed' && (
            <FeedScreen
              joined={joined}
              myUserId={me?.user_id ?? null}
              onOpenPerson={(id) => { setPersonId(id); setScreen('person'); }}
              onJoin={() => setScreen('me')}
            />
          )}
          {screen === 'discover' && (
            <DiscoverScreen onOpenPerson={(id) => { setPersonId(id); setScreen('person'); }} />
          )}
          {screen === 'moderation' && <ModerationScreen />}
          {screen === 'messages' && (
            <MessagesScreen
              openWith={messagingWith}
              onOpenChange={setMessagingWith}
              onReadSomething={refreshUnread}
            />
          )}
          {(screen === 'me' || screen === 'person') && (
            <PersonScreen
              key={screen === 'me' ? 'me' : personId}
              userId={screen === 'me' ? null : personId}
              myUserId={me?.user_id ?? null}
              onOpenPerson={(id) => { setPersonId(id); setScreen('person'); }}
              onOpenMessages={(id) => { setMessagingWith(id); setScreen('messages'); }}
              onProfileSaved={(saved) => { setMe(saved); setJoined(true); }}
              onLeft={() => { setMe(null); setJoined(false); }}
            />
          )}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

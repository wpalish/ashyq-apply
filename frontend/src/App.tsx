/**
 * Application shell: five tabs, the screens inside each, and one screen at a time.
 *
 * The tabs are the «Горизонт» navigation - Match, Plan, Documents, People, Me -
 * on top on a desktop and at the bottom of a phone. Each tab keeps its own
 * screens in a sub-navigation, so every screen still has a button, an address
 * and a `nav-*` id; what changed is that a student sees five places, not
 * fifteen.
 *
 * Navigation is a plain state machine rather than a router. The workflow is
 * linear and gated — you cannot read a shortlist that has not been produced —
 * and disabled items say *why* they are disabled instead of vanishing.
 */

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { useStore } from '@/lib/store';
import { PaywallNotice } from '@/components/PaywallNotice';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { AccountMenu } from '@/components/AccountMenu';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { StartScreen } from '@/screens/StartScreen';
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
import { BrandSun, Chip } from '@/components/primitives';
import { api } from '@/api/client';
import { LOCALES, t as translate, type Locale, type MessageKey } from '@/lib/i18n';
import { useTranslation } from '@/lib/useTranslation';
import type { PersonCard } from '@/types';

export type ScreenId =
  | 'start' | 'profile' | 'preferences' | 'progress' | 'shortlist' | 'funding'
  | 'approved' | 'documents' | 'sources' | 'export'
  | 'feed' | 'discover' | 'messages' | 'me' | 'person' | 'moderation' | 'legal';

/**
 * The numbers are not decoration: the case screens are a sequence, and 04
 * genuinely cannot be read before 03 has produced anything. Community is not a
 * sequence, so those entries carry no number.
 */
const SCREENS: { id: ScreenId; num?: string; label: MessageKey; group: MessageKey }[] = [
  { id: 'start', label: 'nav.start', group: 'nav.group.prepare' },
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

type TabId = 'match' | 'plan' | 'documents' | 'people' | 'me';

/**
 * Which screens live under which tab, in their sub-navigation order.
 *
 * Match is the search and everything it produced; Plan is what the applicant
 * decided; Documents is what to send; People is the community; Me is the
 * applicant's own data and the product's paperwork. The person screen is
 * someone else's community profile, reached from People, so it belongs there
 * without a button of its own.
 */
const TABS: { id: TabId; label: MessageKey; screens: ScreenId[] }[] = [
  { id: 'match', label: 'tab.match', screens: ['start', 'progress', 'shortlist', 'funding', 'sources'] },
  { id: 'plan', label: 'tab.plan', screens: ['approved'] },
  { id: 'documents', label: 'tab.documents', screens: ['documents'] },
  { id: 'people', label: 'tab.people', screens: ['feed', 'discover', 'messages', 'person'] },
  { id: 'me', label: 'tab.me', screens: ['profile', 'preferences', 'me', 'export', 'moderation', 'legal'] },
];

/** The short sub-navigation name, where the tab already gives the context. */
const SUBNAV_LABEL: Partial<Record<ScreenId, MessageKey>> = {
  progress: 'subnav.progress',
  shortlist: 'subnav.shortlist',
  funding: 'subnav.funding',
  sources: 'subnav.sources',
  profile: 'subnav.profile',
  preferences: 'subnav.preferences',
  me: 'subnav.me',
  export: 'subnav.export',
  moderation: 'subnav.moderation',
  legal: 'subnav.legal',
};

function tabOf(screen: ScreenId): TabId {
  return TABS.find((tab) => tab.screens.includes(screen))?.id ?? 'match';
}

/** Line icons for the tabs: decorative, the label always sits next to them. */
const TAB_ICON: Record<TabId, ReactNode> = {
  match: (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3.5 12h17M12 3.5c2.6 2.4 3.9 5.2 3.9 8.5s-1.3 6.1-3.9 8.5c-2.6-2.4-3.9-5.2-3.9-8.5s1.3-6.1 3.9-8.5Z" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  ),
  plan: (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
      <path d="M9 6h11M9 12h11M9 18h11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="4.5" cy="6" r="1.4" fill="currentColor" /><circle cx="4.5" cy="12" r="1.4" fill="currentColor" /><circle cx="4.5" cy="18" r="1.4" fill="currentColor" />
    </svg>
  ),
  documents: (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
      <path d="M6 3.5h8l4 4v13H6z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M14 3.5v4h4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  ),
  people: (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
      <circle cx="9" cy="8.5" r="3.2" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3 19.5c.6-3.3 3-5 6-5s5.4 1.7 6 5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M15.5 5.6a3 3 0 0 1 0 5.8M17.5 14.8c1.9.6 3.1 2.2 3.5 4.7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
  me: (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
      <circle cx="12" cy="8.5" r="3.6" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4.5 20c.8-3.8 3.7-5.8 7.5-5.8s6.7 2 7.5 5.8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  ),
};

/** The screen named by `#/…`, if it names one at all. */
function screenFromHash(): ScreenId | null {
  const id = window.location.hash.replace(/^#\/?/, '').split('?')[0];
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

/** "1 conflict", not "1 conflicts". */
function plural(n: number, noun: string): string {
  return `${n} ${noun}${n === 1 ? '' : 's'}`;
}

const THEME_KEY = 'ashyq.theme';
type Theme = 'system' | 'light' | 'dark';

export default function App() {
  const {
    run, results, summary, error, clearError, capabilities,
    cases, savedProfile, switchCase, newCase, dirty, hydrated,
  } = useStore();
  const { t, locale, setLocale } = useTranslation();
  const [screen, setScreenState] = useState<ScreenId>(() => screenFromHash() ?? 'start');
  // The last screen seen in each tab, so a tab returns to where you were in it.
  const [lastInTab, setLastInTab] = useState<Partial<Record<TabId, ScreenId>>>({});
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
    if (screen === 'start' || screen === 'profile' || screen === 'preferences') setScreen('progress');
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
    start: null,
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
    setLastInTab((seen) => ({ ...seen, [tabOf(next)]: next }));
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
      return;
    }
    const fallback: ScreenId = runRef.current ? 'progress' : 'start';
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

  /**
   * Where a tab lands: the screen last seen in it, else its first open one.
   * Match follows the workflow instead - results once there are any, the run
   * while it works, the search before either.
   */
  const tabHome = (tab: TabId): ScreenId | null => {
    const remembered = lastInTab[tab];
    if (remembered && remembered !== 'person' && !gate[remembered]) return remembered;
    if (tab === 'match') return hasResults ? 'shortlist' : run ? 'progress' : 'start';
    const entry = TABS.find((item) => item.id === tab);
    return entry?.screens.find((id) => id !== 'person' && !gate[id]) ?? null;
  };
  const tabBadge: Partial<Record<TabId, number>> = {
    plan: badges.approved,
    documents: badges.documents,
    people: badges.messages,
  };
  const activeTab = tabOf(screen);
  const subScreens = (TABS.find((tab) => tab.id === activeTab)?.screens ?? [])
    .filter((id) => id !== 'person');

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark"><BrandSun /><span>ASHYQ <span className="brand__apply">Apply</span></span></span>
        </div>

        <nav className="navtabs" aria-label="Sections">
          {TABS.map((tab) => {
            const home = tabHome(tab.id);
            const firstGate = gate[tab.screens[0] ?? 'start'];
            return (
              <button
                key={tab.id}
                type="button"
                className="navtabs__item"
                aria-current={activeTab === tab.id ? 'page' : undefined}
                disabled={!home}
                title={home ? undefined : firstGate ?? undefined}
                data-testid={`navtab-${tab.id}`}
                onClick={() => {
                  if (!home) return;
                  setRedirected(null);
                  setScreen(home);
                }}
              >
                <span className="navtabs__icon">{TAB_ICON[tab.id]}</span>
                <span className="navtabs__label">{t(tab.label)}</span>
                {tabBadge[tab.id] !== undefined && <span className="navtabs__badge">{tabBadge[tab.id]}</span>}
              </button>
            );
          })}
        </nav>

        <div className="topbar__spacer" />
        <Chip tone={capabilities?.demo_mode ? 'demo' : 'accent'}>
          {capabilities ? (capabilities.demo_mode ? 'Demo data' : 'Live sources') : 'connecting…'}
        </Chip>
        <AccountMenu onSignedOut={() => window.location.reload()} />
        <button className="btn btn--sm btn--ghost topbar__signout" data-testid="sign-out" type="button" onClick={async () => {
          await api.logout(); window.location.reload();
        }}>{t('topbar.signOut')}</button>
      </header>

      {(subScreens.length > 1 || activeTab === 'me') && (
        <div className="subnav">
          {subScreens.length > 1 && (
            <nav className="nav" aria-label={t(TABS.find((tab) => tab.id === activeTab)?.label ?? 'tab.match')}>
              {subScreens.map((id) => {
                const blocked = gate[id];
                return (
                  <button
                    key={id}
                    type="button"
                    className="nav__item"
                    aria-current={screen === id ? 'page' : undefined}
                    disabled={Boolean(blocked)}
                    title={blocked ?? undefined}
                    data-testid={`nav-${id}`}
                    onClick={() => {
                      // A deliberate move answers the explanation, so it goes.
                      setRedirected(null);
                      setScreen(id);
                    }}
                  >
                    <span>{t(SUBNAV_LABEL[id] ?? (SCREENS.find((item) => item.id === id)?.label ?? 'nav.start'))}</span>
                    {badges[id] !== undefined && <span className="nav__badge">{badges[id]}</span>}
                  </button>
                );
              })}
            </nav>
          )}
          {activeTab === 'me' && (
            // Whose case this is. It lives with the applicant's own data: the
            // search and the results are always about the case chosen here.
            <div className="subnav__case">
              <label className="row row--tight xs muted" htmlFor="case-switcher">
                <span className="topbar__caption">Applicant</span>
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
              </label>
              <button className="btn btn--sm" type="button" onClick={() => {
                if (!confirmDiscard()) return;
                newCase(); setScreen('start');
              }}>{t('topbar.newCase')}</button>
            </div>
          )}
        </div>
      )}

      <div className="main">
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

        <main className="screen">
          {/* Scoped to the screen, so one broken screen cannot take the
              tabs and the case switcher down with it. */}
          <ErrorBoundary label={`the ${screen} screen`} key={screen}>
          {screen === 'start' && (
            <StartScreen
              onStarted={() => setScreen('progress')}
              onOpenProfile={() => setScreen('profile')}
              onOpenPreferences={() => setScreen('preferences')}
              onOpenResults={() => setScreen(hasResults ? 'shortlist' : 'progress')}
            />
          )}
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

      <footer className="app-footer">
        <div className="app-footer__inner">
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
          <div className="app-footer__about">
            <p className="xs faint">{t('brand.tagline')}. {t('brand.disclaimer')}</p>
            {run && (
              // For support and bug reports, not for the applicant's decision:
              // it used to sit in the top bar, in front of everything.
              <p className="xs faint mono">
                run {run.id.slice(0, 8)} · {run.stage.replace(/_/g, ' ')}
                {summary && ` · ${plural(summary.total, 'programme')} · ${plural(summary.with_conflicts, 'conflict')} · ${plural(summary.with_open_questions, 'open question')}`}
              </p>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}

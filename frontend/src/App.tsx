/**
 * Application shell: sidebar navigation, a status bar, and one screen at a time.
 *
 * Navigation is a plain state machine rather than a router. The workflow is
 * linear and gated — you cannot read a shortlist that has not been produced —
 * and disabled nav items say *why* they are disabled instead of vanishing.
 */

import { lazy, Suspense, useCallback, useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { useStore } from '@/lib/store';
import { APPLICANT_OWNER_KEY } from '@/lib/applicantStorage';
import type { SharedRouteLeaveRisk } from '@/lib/sharedRouteRecovery';
import { ResearchReadNotice } from '@/components/ResearchReadNotice';
import { PaywallNotice } from '@/components/PaywallNotice';
import { ErrorBoundary } from '@/components/ErrorBoundary';
const ProfileScreen = lazy(() => import('@/screens/ProfileScreen').then(module => ({ default: module.ProfileScreen })));
const PreferencesScreen = lazy(() => import('@/screens/PreferencesScreen').then(module => ({ default: module.PreferencesScreen })));
const ProgressScreen = lazy(() => import('@/screens/ProgressScreen').then(module => ({ default: module.ProgressScreen })));
const ShortlistScreen = lazy(() => import('@/screens/ShortlistScreen').then(module => ({ default: module.ShortlistScreen })));
const FundingScreen = lazy(() => import('@/screens/FundingScreen').then(module => ({ default: module.FundingScreen })));
const ApprovedScreen = lazy(() => import('@/screens/ApprovedScreen').then(module => ({ default: module.ApprovedScreen })));
const DocumentsScreen = lazy(() => import('@/screens/DocumentsScreen').then(module => ({ default: module.DocumentsScreen })));
const SourcesScreen = lazy(() => import('@/screens/SourcesScreen').then(module => ({ default: module.SourcesScreen })));
const ExportScreen = lazy(() => import('@/screens/ExportScreen').then(module => ({ default: module.ExportScreen })));
const LegalScreen = lazy(() => import('@/screens/LegalScreen').then(module => ({ default: module.LegalScreen })));
const FeedScreen = lazy(() => import('@/screens/FeedScreen').then(module => ({ default: module.FeedScreen })));
const DiscoverScreen = lazy(() => import('@/screens/DiscoverScreen').then(module => ({ default: module.DiscoverScreen })));
const PersonScreen = lazy(() => import('@/screens/PersonScreen').then(module => ({ default: module.PersonScreen })));
const MessagesScreen = lazy(() => import('@/screens/MessagesScreen').then(module => ({ default: module.MessagesScreen })));
const BookModerationFixture=import.meta.env.DEV?lazy(()=>import('@/dev/BookModerationFixture').then(module=>({default:module.BookModerationFixture}))):null;
const ModerationScreen = lazy(() => import('@/screens/ModerationScreen').then(module => ({ default: module.ModerationScreen })));
import { HomeScreen } from '@/screens/HomeScreen';
const SettingsScreen = lazy(() => import('@/screens/SettingsScreen').then(module => ({ default: module.SettingsScreen })));
const BillingScreen = lazy(() => import('@/screens/BillingScreen').then(module => ({ default: module.BillingScreen })));
const PreparationScreen = lazy(() => import('@/screens/PreparationScreen').then(module => ({ default: module.PreparationScreen })));
const TodayScreen=lazy(()=>import('@/screens/JourneyPages').then(module=>({default:module.TodayScreen})));
const CalendarScreen=lazy(()=>import('@/screens/JourneyPages').then(module=>({default:module.CalendarScreen})));
const ApplicationsScreen=lazy(()=>import('@/screens/JourneyPages').then(module=>({default:module.ApplicationsScreen})));
const ShareScreen=lazy(()=>import('@/screens/JourneyPages').then(module=>({default:module.ShareScreen})));
import { Chip } from '@/components/primitives';
import { api } from '@/api/client';
import { LOCALES, getLocale, t as translate, type Locale, type MessageKey } from '@/lib/i18n';
import { useTranslation } from '@/lib/useTranslation';
import type { PersonCard } from '@/types';
import { BookFooter } from '@/components/BookUI';
import { Files, House, ListChecks, MagnifyingGlass, UsersThree } from '@phosphor-icons/react';

export type ScreenId =
  | 'home' | 'profile' | 'preferences' | 'progress' | 'shortlist' | 'funding'
  | 'approved' | 'documents' | 'sources' | 'export'
  | 'feed' | 'discover' | 'messages' | 'me' | 'person' | 'moderation' | 'legal'
  | 'settings' | 'billing' | 'preparation' | 'today' | 'calendar' | 'applications' | 'share';

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
  { id: 'preparation', label: 'nav.preparation', group: 'nav.group.optional' },
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
  const id = window.location.hash.replace(/^#\/?/, '').split('?')[0] ?? '';
  return ['home', 'settings', 'billing', 'today', 'calendar', 'applications', 'share', 'person'].includes(id) || SCREENS.some((s) => s.id === id) ? (id as ScreenId) : null;
}
function personFromHash(): string | null {
  const id = new URLSearchParams(window.location.hash.split('?')[1] ?? '').get('user');
  return id && /^[a-zA-Z0-9_-]{1,64}$/.test(id) ? id : null;
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
  const locale=getLocale();
  const bookLabels:Partial<Record<ScreenId,[string,string]>>={home:['Главная','Басты бет'],settings:['Настройки','Баптаулар'],billing:['Доступ и подписка','Қолжетімділік және жазылым'],today:['Сегодня','Бүгін'],calendar:['Календарь сроков','Мерзімдер күнтізбесі'],applications:['Заявки','Өтінімдер'],share:['Поделиться маршрутом','Бағытпен бөлісу'],person:['Профиль участника','Қатысушының профилі']};
  const localized=bookLabels[id];if(locale!=='en'&&localized)return localized[locale==='kk'?1:0];
  if (id === 'home') return 'Home';
  if (id === 'settings') return 'Settings';
  if (id === 'billing') return 'Billing';
  if (id === 'today') return 'Today';
  if (id === 'calendar') return 'Deadline calendar';
  if (id === 'applications') return 'Applications';
  if (id === 'share') return 'Share your route';
  if (id === 'person') return 'Member profile';
  const entry = SCREENS.find((s) => s.id === id);
  return entry ? translate(entry.label) : id;
}
function closeDisclosureOnEscape(event:KeyboardEvent<HTMLDetailsElement>) {
  if(event.key!=='Escape'||event.defaultPrevented)return;
  const details=event.currentTarget;if(!details.open)return;
  event.preventDefault();event.stopPropagation();details.open=false;
  details.querySelector('summary')?.focus();
}

const THEME_KEY = 'unimatch.theme';
type Theme = 'system' | 'light' | 'dark';
const PRIMARY_NAV = [
  { id: 'home', label: 'Home', mobileLabel: 'Home', icon: House },
  { id: 'shortlist', label: 'Find', mobileLabel: 'Find', icon: MagnifyingGlass },
  { id: 'approved', label: 'Plan', mobileLabel: 'Plan', icon: ListChecks },
  { id: 'documents', label: 'Documents', mobileLabel: 'Docs', icon: Files },
  { id: 'me', label: 'My profile', mobileLabel: 'Me', icon: UsersThree },
] as const;

export default function App() {
  const {
    run, results, summary, error, clearError, capabilities,
    cases, savedProfile, switchCase, newCase, dirty, hydrated, profileRecovery,
  } = useStore();
  const { t, locale, setLocale } = useTranslation();
  const [screen, setScreenState] = useState<ScreenId>(() => screenFromHash() ?? 'home');
  const mainRef = useRef<HTMLElement | null>(null);
  const previousScreen = useRef(screen);
  const followedRun = useRef<{ hydrated: boolean; id: string | null }>({ hydrated: false, id: null });
  const screenRef = useRef(screen);
  const acceptedHash = useRef(screenFromHash() ? window.location.hash : '#/home');
  const sharedLeaveRisks = useRef(new Map<symbol, boolean>());
  const logoutIntent = useRef(0);
  useEffect(() => () => { ++logoutIntent.current; }, []);
  const onSharedLeaveRisk = useCallback<SharedRouteLeaveRisk>((token, risk) => {
    if (risk) sharedLeaveRisks.current.set(token, true);
    else sharedLeaveRisks.current.delete(token); // An old cleanup cannot erase a newer registration.
  }, []);
  const confirmSharedLeave = useCallback(() => sharedLeaveRisks.current.size === 0
    || window.confirm(translate('shared.recoveryLeave')), []);
  useEffect(() => {
    const protectUnload = (event: BeforeUnloadEvent) => {
      if (!sharedLeaveRisks.current.size) return;
      event.preventDefault(); event.returnValue = '';
    };
    window.addEventListener('beforeunload', protectUnload);
    return () => window.removeEventListener('beforeunload', protectUnload);
  }, []);
  const [role, setRole] = useState<string | null>(null);
  const [redirected, setRedirected] = useState<string | null>(null);
  /** Ask before throwing away typing the applicant has not saved. */
  const confirmDiscard = () =>
    confirmSharedLeave() && (!dirty ||
    window.confirm(
      'You have unsaved changes to this profile. Leaving now discards them. '
      + 'Save first, or continue and lose them?',
    ));
  // Who I am in the community, and whose profile is open. The community has no
  // gates, so this is the only navigation state it needs.
  const [me, setMe] = useState<PersonCard | null>(null);
  const [joined, setJoined] = useState(false);
  const [personId, setPersonId] = useState<string | null>(personFromHash);
  const personRef = useRef(personId);
  const [messagingWith, setMessagingWith] = useState<string | null>(null);
  const [unread, setUnread] = useState(0);
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      return (window.localStorage.getItem(THEME_KEY) as Theme) ?? 'light';
    } catch {
      return 'light';
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
    api.authStatus().then((status) => setRole(status.principal?.role ?? null)).catch(() => {});
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
    if (!hydrated) return;
    const prior = followedRun.current;
    followedRun.current = { hydrated: true, id: run?.id ?? null };
    // Restoring an existing run is not a new research action. In particular,
    // reloading the profile/recovery screen must keep the editor reachable.
    if (!prior.hydrated || !run || prior.id === run.id) return;
    if (screen === 'profile' || screen === 'preferences') setScreen('progress');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.id, hydrated]);

  const hasResults = results.length > 0;
  const approvedCount = results.filter((r) => r.user_decision === 'approved').length;
  const maybeCount = results.filter((r) => r.user_decision === 'maybe').length;
  const withChecklists = results.filter((r) => r.checklist).length;

  const gate: Record<ScreenId, string | null> = {
    home: null,
    profile: null,
    preferences: null,
    progress: run ? null : 'Start research first',
    shortlist: null,
    funding: hasResults ? null : 'No results yet',
    sources: hasResults ? null : 'No results yet',
    approved: null,
    // Also open while collection is in flight: the applicant pressed Collect
    // and the worker has not finished yet. Bouncing them off the screen they
    // just asked for would be the redirect fighting the workflow.
    documents: null,
    export: run || savedProfile ? null : 'Save an applicant case first',
    // The community does not depend on a research run, so nothing gates it.
    feed: null,
    discover: null,
    messages: null,
    me: null,
    moderation: null,
    person: null,
    // A privacy policy nobody can reach before signing up is not a policy.
    legal: null,
    settings: null,
    billing: null,
    preparation: null,
    today: null,
    calendar: null,
    applications: null,
    share: null,
  };

  // The hash is the address of the screen: back and forward work, a reload
  // lands where it left off, and a link to a screen can be sent to someone.
  // The gates still decide what may be shown - a bookmark to #/shortlist made
  // before there were any results redirects to progress and says why.
  const commitScreen = useCallback((next: ScreenId) => {
    screenRef.current = next;
    setScreenState(next);
    const target = next === 'person' && personRef.current ? `#/person?user=${encodeURIComponent(personRef.current)}` : `#/${next}`;
    acceptedHash.current = target;
    if (window.location.hash !== target) window.location.hash = target;
  }, []);
  const setScreen = useCallback((next: ScreenId) => {
    if (next !== screenRef.current && !confirmSharedLeave()) return;
    commitScreen(next);
  }, [commitScreen, confirmSharedLeave]);

  useEffect(() => {
    window.scrollTo(0, 0);
    if (previousScreen.current !== screen) mainRef.current?.focus({ preventScroll: true });
    previousScreen.current = screen;
  }, [screen]);

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
      screenRef.current = requested;
      setScreenState(requested);
      return;
    }
    const fallback: ScreenId = runRef.current ? 'progress' : 'profile';
    setRedirected(`${label(requested)}: ${blocked}.`);
    commitScreen(fallback);
  }, [commitScreen]);

  const openFromHash = useCallback(() => {
    const requested = screenFromHash();
    if (!requested) return;
    if (requested !== screenRef.current && !confirmSharedLeave()) {
      window.history.replaceState(null, '', acceptedHash.current);
      return;
    }
    acceptedHash.current = window.location.hash; screenRef.current = requested;
    if (requested === 'person') {
      const id = personFromHash(); personRef.current = id; setPersonId(id);
    }
    // Before the store has loaded, "no results yet" would be a statement about
    // an empty store rather than about the run. Show the screen and judge it
    // once there is something to judge.
    setScreenState(requested);
    if (!hydratedRef.current) {
      setPendingLink(requested);
      return;
    }
    evaluateLink(requested);
  }, [evaluateLink, confirmSharedLeave]);

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
  const openPerson = (id: string) => {
    if (!confirmSharedLeave()) return;
    personRef.current = id; setPersonId(id); commitScreen('person');
  };

  return (
    <div className="app book-window">
      <a className="skip-link" href="#main-content" onClick={(event) => { event.preventDefault(); mainRef.current?.focus(); }}>{locale==='en'?'Skip to content':locale==='kk'?'Мазмұнға өту':'К содержимому'}</a>
      <aside className="sidebar" aria-label={locale==='en'?'Application navigation':locale==='kk'?'Қолданба навигациясы':'Навигация приложения'}>
        <div className="brand">
          <img className="brand__icon" src="/brand/unimatch-orbit.svg" alt="" />
          <span className="brand__mark">unimatch</span>
        </div>

        <nav className="nav" aria-label={locale==='en'?'Main navigation':locale==='kk'?'Негізгі навигация':'Основная навигация'}>
          {PRIMARY_NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              className="nav__item"
              aria-label={locale==='en'?item.label:locale==='kk'?({home:'Басты бет',shortlist:'Іріктеу',approved:'Жоспар',documents:'Құжаттар',me:'Мен'} as Record<string,string>)[item.id]:({home:'Главная',shortlist:'Подбор',approved:'План',documents:'Документы',me:'Я'} as Record<string,string>)[item.id]}
              aria-current={(screen === item.id || (item.id === 'approved' && ['today', 'calendar', 'applications', 'share', 'funding'].includes(screen))) ? 'page' : undefined}
              data-testid={`nav-${item.id}`}
              onClick={() => { setRedirected(null); setScreen(item.id); }}
            >
              <item.icon size={21} weight={screen === item.id ? 'fill' : 'regular'} aria-hidden="true" />
              <span className="nav__label--full">{locale==='en'?item.label:locale==='kk'?({home:'Басты бет',shortlist:'Іріктеу',approved:'Жоспар',documents:'Құжаттар',me:'Мен'} as Record<string,string>)[item.id]:({home:'Главная',shortlist:'Подбор',approved:'План',documents:'Документы',me:'Я'} as Record<string,string>)[item.id]}</span>
              <span className="nav__label--compact">{locale==='en'?item.mobileLabel:locale==='kk'?({home:'Басты бет',shortlist:'Іріктеу',approved:'Жоспар',documents:'Құжаттар',me:'Мен'} as Record<string,string>)[item.id]:({home:'Главная',shortlist:'Подбор',approved:'План',documents:'Документы',me:'Я'} as Record<string,string>)[item.id]}</span>
              {badges[item.id] !== undefined && <span className="nav__badge">{badges[item.id]}</span>}
            </button>
          ))}
        </nav>

        <nav className="sidebar__optional" aria-label={t('nav.group.optional')}>
          <p className="sidebar__optional-label">{t('nav.group.optional')}</p>
          <button type="button" className="nav__item" aria-label={t('nav.preparation')}
            aria-current={screen === 'preparation' ? 'page' : undefined} data-testid="nav-preparation"
            onClick={() => { setRedirected(null); setScreen('preparation'); }}>
            <ListChecks size={21} weight={screen === 'preparation' ? 'fill' : 'regular'} aria-hidden="true" />
            <span>{t('nav.preparation')}</span>
          </button>
        </nav>

        <div className="sidebar__footer">
          <p>Same students.<br /><strong>Bigger horizons.</strong></p>
          <details className="sidebar__settings">
            <summary>Preferences</summary>
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
          </details>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button type="button" className="topbar__brand" onClick={() => setScreen('home')} aria-label="Unimatch home"><img src="/brand/unimatch-orbit.svg" alt="" />unimatch</button>
          <Chip tone={capabilities?.demo_mode ? 'demo' : 'accent'}>
            {capabilities ? (capabilities.demo_mode ? 'Demo data' : 'Live sources') : 'connecting…'}
          </Chip>
          <details className="journey-menu" onKeyDown={closeDisclosureOnEscape}>
            <summary>{locale==='en'?'More':locale==='kk'?'Тағы':'Ещё'}</summary>
            <div className="journey-menu__list">
              {(['today', 'calendar', 'applications', 'share'] as const).map(id => <button key={id} type="button" onClick={(event) => { setScreen(id); event.currentTarget.closest('details')?.removeAttribute('open'); }}>{label(id)}</button>)}
              {SCREENS.filter((item) => item.id !== 'moderation' || role === 'moderator').map((item) => (
                <button key={item.id} type="button" onClick={(event) => { setScreen(item.id); event.currentTarget.closest('details')?.removeAttribute('open'); }} disabled={Boolean(gate[item.id])}>
                  {t(item.label)}
                </button>
              ))}
            </div>
          </details>
          <label className="book-language"><span className="visually-hidden">{t('language.label')}</span><select value={locale} onChange={event=>setLocale(event.target.value as Locale)}><option value="ru">Рус</option><option value="kk">Қаз</option><option value="en">Eng</option></select></label><div className="topbar__spacer" />
          <details className="case-menu" onKeyDown={closeDisclosureOnEscape}><summary aria-label={locale==='en'?'Applicant workspace':locale==='kk'?'Талапкердің жұмыс аймағы':'Рабочее пространство абитуриента'}><span>{savedProfile?.display_name?.slice(0, 1).toUpperCase() || 'A'}</span><b>{savedProfile?.display_name?.split(' ')[0] || (locale==='en'?'Applicant':locale==='kk'?'Талапкер':'Абитуриент')}</b></summary><div className="case-menu__panel">
          <nav className="case-menu__destinations" aria-label={locale==='en'?'All sections':locale==='kk'?'Барлық бөлімдер':'Все разделы'}>{(['today','calendar','applications','share'] as const).map(id=><button className="btn btn--ghost btn--sm" key={id} type="button" onClick={event=>{setScreen(id);event.currentTarget.closest('details')?.removeAttribute('open');}}>{label(id)}</button>)}{SCREENS.filter(item=>item.id!=='moderation'||role==='moderator').map(item=><button className="btn btn--ghost btn--sm" key={item.id} type="button" disabled={Boolean(gate[item.id])} onClick={event=>{setScreen(item.id);event.currentTarget.closest('details')?.removeAttribute('open');}}>{t(item.label)}</button>)}</nav>
          <label className="row row--tight xs muted topbar__case" htmlFor="case-switcher">
            {locale==='en'?'Applicant':locale==='kk'?'Талапкер':'Абитуриент'}
            <select
              id="case-switcher"
              value={savedProfile?.id ?? ''}
              onChange={(event) => {
                // Switching case replaces the form. Unsaved edits are the
                // applicant's typing, so they are never discarded silently.
                if (event.target.value === (savedProfile?.id ?? '')) return;
                if (!confirmDiscard()) {
                  event.target.value = savedProfile?.id ?? '';
                  return;
                }
                if (event.target.value) void switchCase(event.target.value);
                else newCase();
              }}
            >
              <option value="">{t('topbar.newApplicant')}</option>
              {savedProfile && !cases.some(item => item.id === savedProfile.id) && <option value={savedProfile.id}>{savedProfile.display_name} · {t('topbar.caseListUnavailable')}</option>}
              {cases.map((item) => (
                <option key={item.id} value={item.profile_id}>
                  {item.display_name} · {item.run_count} {locale==='en'?`run${item.run_count === 1 ? '' : 's'}`:locale==='kk'?'зерттеу':'исследований'}
                </option>
              ))}
            </select>
          </label>
          <button className="btn btn--sm topbar__new-case" type="button" onClick={() => {
            if (!confirmDiscard()) return;
            newCase(); commitScreen('profile');
          }}>{t('topbar.newCase')}</button>
          <button className="btn btn--sm btn--ghost topbar__settings" type="button" onClick={() => setScreen('settings')}>{label('settings')}</button>
          <button className="btn btn--sm btn--ghost topbar__signout" data-testid="sign-out" type="button" onClick={async () => {
            if (!confirmSharedLeave()) return;
            const intent = ++logoutIntent.current;
            await api.logout();
            if (intent !== logoutIntent.current
              || window.localStorage.getItem(APPLICANT_OWNER_KEY) !== 'signed-out'
              || window.sessionStorage.getItem(APPLICANT_OWNER_KEY) !== 'signed-out') return;
            sharedLeaveRisks.current.clear(); // Only a real logout ACK retires the private workspace before reload.
            window.location.reload();
          }}>{t('topbar.signOut')}</button>
          </div></details>
        </header>

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

        {error && !(screen === 'profile' && profileRecovery) && (
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

        <main id="main-content" className={`screen screen--${screen}`} key={screen} ref={mainRef} tabIndex={-1} aria-label={label(screen)}>
          {locale==='en' && ['approved', 'today', 'calendar', 'applications', 'share'].includes(screen) && <nav className="section-nav" aria-label="Admissions plan">
            {(['approved', 'today', 'calendar', 'applications', 'share'] as const).map(id => <button className="btn btn--ghost" type="button" key={id} aria-current={screen === id ? 'page' : undefined} onClick={() => setScreen(id)}>{id === 'approved' ? 'My plan' : label(id)}</button>)}
          </nav>}
          {locale==='en' && ['feed', 'discover', 'messages', 'me', 'person', 'moderation'].includes(screen) && <nav className="section-nav" aria-label="Community">
            {(['feed', 'discover', 'messages', 'me'] as const).map(id => <button className="btn btn--ghost" type="button" key={id} aria-current={screen === id ? 'page' : undefined} onClick={() => setScreen(id)}>{label(id)}{id === 'messages' && unread > 0 ? ` (${unread})` : ''}</button>)}
          </nav>}
          {/* Scoped to the screen, so one broken screen cannot take the
              sidebar and the case switcher down with it. */}
          <details className="book-research-context" open={Boolean(run && (run.stale || ['changed','mixed'].includes(run.profile_input_status?.state??'') || ['failed','retryable_failed','cancelled'].includes(run.stage) || results.some(result=>(result.read_freshness?.stale_claim_count??0)>0)))}><summary>{locale==='en'?'Research context & source limitations':'Состояние исследования и ограничения источников'}</summary><ErrorBoundary label="the research read context"><ResearchReadNotice /></ErrorBoundary></details>
          <ErrorBoundary label={`the ${screen} screen`} key={screen}>
          <Suspense fallback={<div className="panel" role="status">Opening page…</div>}>
          {screen === 'home' && <HomeScreen onNavigate={setScreen} />}
          {screen === 'profile' && <ProfileScreen onNext={() => setScreen('preferences')} />}
          {screen === 'preferences' && <PreferencesScreen onStarted={() => setScreen('progress')} />}
          {screen === 'progress' && <ProgressScreen onDone={() => setScreen('shortlist')} />}
          {screen === 'shortlist' && <ShortlistScreen onStart={() => setScreen(savedProfile ? 'preferences' : 'profile')} onProgress={() => setScreen('progress')} />}
          {screen === 'funding' && <FundingScreen onPreferences={() => setScreen('preferences')} />}
          {screen === 'sources' && <SourcesScreen onProgress={() => setScreen('progress')} />}
          {screen === 'approved' && <ApprovedScreen onCollect={() => setScreen('documents')} onFind={() => setScreen('shortlist')} onPrepare={() => setScreen('preparation')} />}
          {screen === 'documents' && <DocumentsScreen onNavigate={setScreen} />}
          {screen === 'export' && <ExportScreen />}
          {screen === 'legal' && <LegalScreen />}
          {screen === 'settings' && <SettingsScreen theme={theme} setTheme={setTheme} locale={locale} setLocale={setLocale} onNavigate={setScreen} onSignedOut={() => window.location.reload()} />}
          {screen === 'billing' && <BillingScreen onPrepare={() => setScreen('preparation')} />}
          {screen === 'preparation' && <PreparationScreen onProfile={() => setScreen('profile')} onBilling={() => setScreen('billing')} onLeaveRisk={onSharedLeaveRisk} />}
          {screen === 'today' && <TodayScreen onNavigate={setScreen} />}
          {screen === 'calendar' && <CalendarScreen />}
          {screen === 'applications' && <ApplicationsScreen onNavigate={setScreen} />}
          {screen === 'share' && <ShareScreen onNavigate={setScreen} />}
          {screen === 'feed' && (
            <FeedScreen
              joined={joined}
              myUserId={me?.user_id ?? null}
              onOpenPerson={openPerson}
              onJoin={() => setScreen('me')}
              onDiscover={() => setScreen('discover')}
            />
          )}
          {screen === 'discover' && (
            <DiscoverScreen onOpenPerson={openPerson} />
          )}
          {screen === 'moderation' && (BookModerationFixture&&['127.0.0.1','localhost'].includes(location.hostname)&&new URLSearchParams(location.search).get('ui-fixture')==='moderation'?<BookModerationFixture/>:<ModerationScreen />)}
          {screen === 'messages' && (
            <MessagesScreen
              openWith={messagingWith}
              onOpenChange={setMessagingWith}
              onReadSomething={refreshUnread}
            />
          )}
          {screen === 'person' && !personId && <section className="panel"><h1>Member link incomplete</h1><p>Choose a member from the community to open their public profile.</p><button className="btn btn--primary" onClick={() => setScreen('discover')}>Find people</button></section>}
          {(screen === 'me' || (screen === 'person' && personId)) && (
            <PersonScreen
              key={screen === 'me' ? 'me' : personId}
              userId={screen === 'me' ? null : personId}
              myUserId={me?.user_id ?? null}
              onOpenPerson={openPerson}
              onOpenMessages={(id) => { setMessagingWith(id); setScreen('messages'); }}
              onProfileSaved={(saved) => { setMe(saved); setJoined(true); }}
              onLeft={() => { setMe(null); setJoined(false); }}
            />
          )}
          </Suspense>
          </ErrorBoundary>
        </main>
        <BookFooter demo={capabilities?.demo_mode ?? false} />
      </div>
    </div>
  );
}

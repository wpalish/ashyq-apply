/**
 * Application shell: sidebar navigation, a status bar, and one screen at a time.
 *
 * Navigation is a plain state machine rather than a router. The workflow is
 * linear and gated — you cannot read a shortlist that has not been produced —
 * and disabled nav items say *why* they are disabled instead of vanishing.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useStore } from '@/lib/store';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { AccountMenu } from '@/components/AccountMenu';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { PreferencesScreen } from '@/screens/PreferencesScreen';
import { ProgressScreen } from '@/screens/ProgressScreen';
import { ShortlistScreen } from '@/screens/ShortlistScreen';
import { FundingScreen } from '@/screens/FundingScreen';
import { ApprovedScreen } from '@/screens/ApprovedScreen';
import { DocumentsScreen } from '@/screens/DocumentsScreen';
import { SourcesScreen } from '@/screens/SourcesScreen';
import { ExportScreen } from '@/screens/ExportScreen';
import { FeedScreen } from '@/screens/FeedScreen';
import { DiscoverScreen } from '@/screens/DiscoverScreen';
import { PersonScreen } from '@/screens/PersonScreen';
import { Chip } from '@/components/primitives';
import { api } from '@/api/client';
import type { PersonCard } from '@/types';

export type ScreenId =
  | 'profile' | 'preferences' | 'progress' | 'shortlist' | 'funding'
  | 'approved' | 'documents' | 'sources' | 'export'
  | 'feed' | 'discover' | 'me' | 'person';

/**
 * The numbers are not decoration: the case screens are a sequence, and 04
 * genuinely cannot be read before 03 has produced anything. Community is not a
 * sequence, so those entries carry no number.
 */
const SCREENS: { id: ScreenId; num?: string; label: string; group: string }[] = [
  { id: 'profile', num: '01', label: 'Applicant profile', group: 'Prepare' },
  { id: 'preferences', num: '02', label: 'Preferences & budget', group: 'Prepare' },
  { id: 'progress', num: '03', label: 'Research progress', group: 'Research' },
  { id: 'shortlist', num: '04', label: 'University shortlist', group: 'Research' },
  { id: 'funding', num: '05', label: 'Funding comparison', group: 'Research' },
  { id: 'sources', num: '06', label: 'Sources & conflicts', group: 'Research' },
  { id: 'approved', num: '07', label: 'Approved universities', group: 'Decide' },
  { id: 'documents', num: '08', label: 'Documents & deadlines', group: 'Decide' },
  { id: 'export', num: '09', label: 'Export & data deletion', group: 'Decide' },
  { id: 'feed', label: 'Feed', group: 'Community' },
  { id: 'discover', label: 'Find applicants', group: 'Community' },
  { id: 'me', label: 'My community profile', group: 'Community' },
];

/** The screen named by `#/…`, if it names one at all. */
function screenFromHash(): ScreenId | null {
  const id = window.location.hash.replace(/^#\/?/, '').split('?')[0];
  return SCREENS.some((s) => s.id === id) ? (id as ScreenId) : null;
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
  const [screen, setScreenState] = useState<ScreenId>(() => screenFromHash() ?? 'profile');
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
    me: null,
    person: null,
  };

  // The hash is the address of the screen: back and forward work, a reload
  // lands where it left off, and a link to a screen can be sent to someone.
  // The gates still decide what may be shown - a bookmark to #/shortlist made
  // before there were any results redirects to progress and says why.
  const setScreen = useCallback((next: ScreenId) => {
    setScreenState(next);
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
    const fallback: ScreenId = runRef.current ? 'progress' : 'profile';
    setRedirected(`${SCREENS.find((s) => s.id === requested)?.label ?? requested}: ${blocked}.`);
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
  };

  let groupSeen = '';

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark">ASHYQ Apply</span>
          <span className="brand__tag">
            Evidence-backed university &amp; scholarship shortlisting
          </span>
        </div>

        <nav className="nav" aria-label="Workflow">
          {SCREENS.map((s) => {
            const header = s.group !== groupSeen ? ((groupSeen = s.group), s.group) : null;
            const blocked = gate[s.id];
            return (
              <div key={s.id}>
                {header && <div className="nav__group-label">{header}</div>}
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
                  <span>{s.label}</span>
                  {badges[s.id] !== undefined && <span className="nav__badge">{badges[s.id]}</span>}
                </button>
              </div>
            );
          })}
        </nav>

        <div className="stack stack--tight" style={{ marginTop: 'auto' }}>
          <div className="field">
            <label className="field__label xs" htmlFor="theme">Appearance</label>
            <select
              id="theme"
              value={theme}
              onChange={(e) => setTheme(e.target.value as Theme)}
            >
              <option value="system">Match system</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>
          <p className="xs faint" style={{ margin: 0 }}>
            Published criteria only. ASHYQ Apply never predicts admission or funding outcomes.
          </p>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <Chip tone={capabilities?.demo_mode ? 'demo' : 'accent'}>
            {capabilities ? (capabilities.demo_mode ? 'Demo data' : 'Live sources') : 'connecting…'}
          </Chip>
          {run && (
            <>
              <Chip tone="neutral" mono>run {run.id.slice(0, 8)}</Chip>
              <Chip tone={run.stage === 'failed' ? 'risk' : 'neutral'}>
                {run.stage.replace(/_/g, ' ')}
              </Chip>
            </>
          )}
          <div className="topbar__spacer" />
          <label className="row row--tight xs muted" htmlFor="case-switcher">
            Applicant
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
              <option value="">New applicant</option>
              {cases.map((item) => (
                <option key={item.id} value={item.profile_id}>
                  {item.display_name} · {item.run_count} run{item.run_count === 1 ? '' : 's'}
                </option>
              ))}
            </select>
          </label>
          <button className="btn btn--sm" type="button" onClick={() => {
            if (!confirmDiscard()) return;
            newCase(); setScreen('profile');
          }}>New case</button>
          {summary && (
            <span className="xs muted">
              {plural(summary.total, 'programme')} · {plural(summary.with_conflicts, 'conflict')} ·{' '}
              {plural(summary.with_open_questions, 'open question')}
            </span>
          )}
          <AccountMenu onSignedOut={() => window.location.reload()} />
          <button className="btn btn--sm btn--ghost" data-testid="sign-out" type="button" onClick={async () => {
            await api.logout(); window.location.reload();
          }}>Sign out</button>
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

        <main className="screen">
          {/* Scoped to the screen, so one broken screen cannot take the
              sidebar and the case switcher down with it. */}
          <ErrorBoundary label={`the ${screen} screen`} key={screen}>
          {screen === 'profile' && <ProfileScreen onNext={() => setScreen('preferences')} />}
          {screen === 'preferences' && <PreferencesScreen onStarted={() => setScreen('progress')} />}
          {screen === 'progress' && <ProgressScreen onDone={() => setScreen('shortlist')} />}
          {screen === 'shortlist' && <ShortlistScreen />}
          {screen === 'funding' && <FundingScreen />}
          {screen === 'sources' && <SourcesScreen />}
          {screen === 'approved' && <ApprovedScreen onCollect={() => setScreen('documents')} />}
          {screen === 'documents' && <DocumentsScreen />}
          {screen === 'export' && <ExportScreen />}
          {screen === 'feed' && (
            <FeedScreen
              joined={joined}
              onOpenPerson={(id) => { setPersonId(id); setScreen('person'); }}
              onJoin={() => setScreen('me')}
            />
          )}
          {screen === 'discover' && (
            <DiscoverScreen onOpenPerson={(id) => { setPersonId(id); setScreen('person'); }} />
          )}
          {(screen === 'me' || screen === 'person') && (
            <PersonScreen
              key={screen === 'me' ? 'me' : personId}
              userId={screen === 'me' ? null : personId}
              myUserId={me?.user_id ?? null}
              onOpenPerson={(id) => { setPersonId(id); setScreen('person'); }}
              onProfileSaved={(saved) => { setMe(saved); setJoined(true); }}
            />
          )}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

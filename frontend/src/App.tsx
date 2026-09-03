/**
 * Application shell: sidebar navigation, a status bar, and one screen at a time.
 *
 * Navigation is a plain state machine rather than a router. The workflow is
 * linear and gated — you cannot read a shortlist that has not been produced —
 * and disabled nav items say *why* they are disabled instead of vanishing.
 */

import { useEffect, useState } from 'react';
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
import { Chip } from '@/components/primitives';
import { api } from '@/api/client';

export type ScreenId =
  | 'profile' | 'preferences' | 'progress' | 'shortlist' | 'funding'
  | 'approved' | 'documents' | 'sources' | 'export';

const SCREENS: { id: ScreenId; num: string; label: string; group: string }[] = [
  { id: 'profile', num: '01', label: 'Applicant profile', group: 'Prepare' },
  { id: 'preferences', num: '02', label: 'Preferences & budget', group: 'Prepare' },
  { id: 'progress', num: '03', label: 'Research progress', group: 'Research' },
  { id: 'shortlist', num: '04', label: 'University shortlist', group: 'Research' },
  { id: 'funding', num: '05', label: 'Funding comparison', group: 'Research' },
  { id: 'sources', num: '06', label: 'Sources & conflicts', group: 'Research' },
  { id: 'approved', num: '07', label: 'Approved universities', group: 'Decide' },
  { id: 'documents', num: '08', label: 'Documents & deadlines', group: 'Decide' },
  { id: 'export', num: '09', label: 'Export & data deletion', group: 'Decide' },
];

/** "1 conflict", not "1 conflicts". */
function plural(n: number, noun: string): string {
  return `${n} ${noun}${n === 1 ? '' : 's'}`;
}

const THEME_KEY = 'ashyq.theme';
type Theme = 'system' | 'light' | 'dark';

export default function App() {
  const {
    run, results, summary, error, clearError, capabilities,
    cases, savedProfile, switchCase, newCase,
  } = useStore();
  const [screen, setScreen] = useState<ScreenId>('profile');
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

  const gate: Record<ScreenId, string | null> = {
    profile: null,
    preferences: null,
    progress: run ? null : 'Start research first',
    shortlist: hasResults ? null : 'No results yet',
    funding: hasResults ? null : 'No results yet',
    sources: hasResults ? null : 'No results yet',
    approved: hasResults ? null : 'No results yet',
    documents: withChecklists > 0 ? null : 'Approve programmes, then collect documents',
    export: run ? null : 'Start research first',
  };

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
                  onClick={() => setScreen(s.id)}
                >
                  <span className="nav__num">{s.num}</span>
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
            newCase(); setScreen('profile');
          }}>New case</button>
          {summary && (
            <span className="xs muted">
              {plural(summary.total, 'programme')} · {plural(summary.with_conflicts, 'conflict')} ·{' '}
              {plural(summary.with_open_questions, 'open question')}
            </span>
          )}
          <AccountMenu onSignedOut={() => window.location.reload()} />
          <button className="btn btn--sm btn--ghost" type="button" onClick={async () => {
            await api.logout(); window.location.reload();
          }}>Sign out</button>
        </header>

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
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

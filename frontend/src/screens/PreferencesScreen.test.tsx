/**
 * Turning demo mode off must say how far live mode actually reaches.
 *
 * The audited defect: the toggle offered "live" against an implied open web.
 * What it really searches is a curated registry of ten institutions, with an
 * individual programme page reached at about one site in ten. An applicant
 * who switches demo off and waits through a slow run deserves to know the
 * size of the search before it starts, not to infer it from a thin result.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PreferencesScreen } from './PreferencesScreen';
import type { Capabilities } from '@/types';

const COVERAGE: Capabilities['live_coverage'] = {
  institutions: 10,
  countries: ['Austria', 'Canada', 'Finland'],
  recall_note:
    'Live mode searches 10 curated institutions in 3 countries, not the open web.',
};

const CAPABILITIES = {
  currency: { supported: ['KZT', 'EUR', 'USD'], rate_date: '2026-09-01', rate_source: 'ECB' },
  live_coverage: COVERAGE,
} as Capabilities;

let capabilities: Capabilities | null;

vi.mock('@/lib/store', () => ({
  useStore: () => ({
    profileDraft: { preferences: {}, funding: {} },
    setProfileDraft: vi.fn(),
    startRun: vi.fn(),
    loading: false,
    capabilities,
    validation: null,
  }),
}));

function renderLive() {
  render(<PreferencesScreen onStarted={() => {}} />);
  fireEvent.click(screen.getByTestId('demo-toggle'));
}

describe('the live-mode disclosure', () => {
  it('stays hidden while demo mode is on', () => {
    capabilities = CAPABILITIES;
    render(<PreferencesScreen onStarted={() => {}} />);
    expect(screen.queryByTestId('live-coverage')).not.toBeInTheDocument();
  });

  it('names the real size of the search when demo mode is turned off', () => {
    capabilities = CAPABILITIES;
    renderLive();

    const panel = screen.getByTestId('live-coverage');
    expect(panel).toHaveTextContent('10 curated institutions');
    expect(panel).toHaveTextContent('not the open web');
    for (const country of COVERAGE.countries) {
      expect(panel).toHaveTextContent(country);
    }
  });

  it('still warns about live mode when coverage is unknown', () => {
    // A capabilities call that has not landed yet must not take the warning
    // down with it — the weaker statement is still true.
    capabilities = null;
    renderLive();
    expect(screen.queryByTestId('live-coverage')).not.toBeInTheDocument();
    expect(screen.getByTestId('live-mode-notice')).toHaveTextContent(
      'fetches real university websites',
    );
  });
});

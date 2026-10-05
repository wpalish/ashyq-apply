/**
 * Turning demo mode off must say how far live mode actually reaches.
 *
 * The audited defect: the toggle offered "live" against an implied open web.
 * Coverage must come from the server's current registry, without turning a
 * historical benchmark into a claim about the run someone is about to start.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PreferencesScreen } from './PreferencesScreen';
import type { Capabilities } from '@/types';

const COVERAGE: Capabilities['live_coverage'] = {
  institutions: 10,
  countries: ['Austria', 'Canada', 'Finland'],
  recall_note:
    'Live mode searches 10 curated institutions in 3 countries, not the open web.',
};

const CAPABILITIES = {
  demo_mode: true,
  currency: { supported: ['KZT', 'EUR', 'USD'], rate_date: '2026-09-01', rate_source: 'ECB' },
  live_coverage: COVERAGE,
} as Capabilities;

let capabilities: Capabilities | null;
const startRun = vi.fn();

beforeEach(() => {
  capabilities = CAPABILITIES;
  startRun.mockReset();
  startRun.mockResolvedValue(undefined);
});

vi.mock('@/lib/store', () => ({
  useStore: () => ({
    profileDraft: { preferences: {}, funding: {} },
    setProfileDraft: vi.fn(),
    startRun,
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
    capabilities = { demo_mode: true, currency: CAPABILITIES.currency } as Capabilities;
    renderLive();
    expect(screen.queryByTestId('live-coverage')).not.toBeInTheDocument();
    expect(screen.getByTestId('live-mode-notice')).toHaveTextContent(
      'fetches real university websites',
    );
  });
});

describe('the deployment research mode', () => {
  it('starts live research by default on a live server', async () => {
    capabilities = { ...CAPABILITIES, demo_mode: false };
    const onStarted = vi.fn();
    render(<PreferencesScreen onStarted={onStarted} />);

    expect(screen.getByTestId('demo-toggle')).not.toBeChecked();
    expect(screen.getByTestId('live-mode-notice')).toBeVisible();
    fireEvent.click(screen.getByTestId('start-research'));

    expect(startRun).toHaveBeenCalledWith(false);
    await waitFor(() => expect(onStarted).toHaveBeenCalledOnce());
  });

  it('keeps demo research as the default on a demo server', () => {
    render(<PreferencesScreen onStarted={() => {}} />);
    expect(screen.getByTestId('demo-toggle')).toBeChecked();
    fireEvent.click(screen.getByTestId('start-research'));
    expect(startRun).toHaveBeenCalledWith(true);
  });

  it('waits for server settings before allowing a search, then uses live mode', () => {
    capabilities = null;
    const { rerender } = render(<PreferencesScreen onStarted={() => {}} />);

    expect(screen.getByTestId('demo-toggle')).toBeDisabled();
    expect(screen.getByTestId('start-research')).toBeDisabled();
    expect(screen.queryByTestId('live-mode-notice')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('start-research'));
    expect(startRun).not.toHaveBeenCalled();

    capabilities = { ...CAPABILITIES, demo_mode: false };
    rerender(<PreferencesScreen onStarted={() => {}} />);
    expect(screen.getByTestId('demo-toggle')).not.toBeChecked();
    expect(screen.getByTestId('start-research')).toBeEnabled();
    fireEvent.click(screen.getByTestId('start-research'));
    expect(startRun).toHaveBeenCalledWith(false);
  });

  it.each([true, false])('preserves an explicit override of server demo_mode=%s', (serverMode) => {
    capabilities = { ...CAPABILITIES, demo_mode: serverMode };
    const { rerender } = render(<PreferencesScreen onStarted={() => {}} />);
    fireEvent.click(screen.getByTestId('demo-toggle'));

    capabilities = { ...CAPABILITIES, demo_mode: serverMode };
    rerender(<PreferencesScreen onStarted={() => {}} />);
    expect((screen.getByTestId('demo-toggle') as HTMLInputElement).checked).toBe(!serverMode);
    fireEvent.click(screen.getByTestId('start-research'));
    expect(startRun).toHaveBeenCalledWith(!serverMode);
  });
});

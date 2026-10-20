/**
 * Turning demo mode off must say how far live mode actually reaches.
 *
 * The audited defect: the toggle offered "live" against an implied open web.
 * Coverage must come from the server's current registry, without turning a
 * historical benchmark into a claim about the run someone is about to start.
 */

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PreferencesScreen } from './PreferencesScreen';
import { setLocale } from '@/lib/i18n';
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

describe('the kb-mode disclosure (RM-1)', () => {
  const KB_NOTE =
    "The verified knowledge base answers for 95 of 501 catalogue universities (bachelor's in "
    + "Computer Science). A university outside it, or another programme, gets 'No verified data "
    + "yet'; no page is read during a run.";
  const KB_CAPABILITIES = {
    ...CAPABILITIES,
    demo_mode: false,
    live_coverage: {
      mode: 'kb',
      institutions: 95,
      countries: ['Canada', 'Germany'],
      catalogue_total: 501,
      recall_note: KB_NOTE,
      recall_message: { key: 'coverage.kb', params: { universities: '95', total: '501' } },
    },
  } as Capabilities;

  afterEach(() => act(() => setLocale('en')));

  it('says that no page is read and nothing is sent to a search provider', () => {
    capabilities = KB_CAPABILITIES;
    render(<PreferencesScreen onStarted={() => {}} />);

    expect(screen.queryByTestId('live-mode-notice')).not.toBeInTheDocument();
    expect(screen.queryByTestId('live-coverage')).not.toBeInTheDocument();
    const notice = screen.getByTestId('kb-mode-notice');
    expect(notice).toHaveTextContent('Research answers from the verified knowledge base.');
    expect(notice).toHaveTextContent(
      'No university page is read and nothing is sent to a search provider during a run.',
    );
    expect(notice).not.toHaveTextContent('fetches real university websites');
    expect(screen.getByTestId('kb-coverage')).toHaveTextContent(KB_NOTE);
    // The country list belongs to live mode only.
    expect(notice).not.toHaveTextContent('Germany');
  });

  it.each([
    ['ru', 'Проверенная база знаний отвечает по 95 из 501 университетов каталога', 'поисковым сервисам'],
    ['kk', 'каталогтағы 501 университеттің 95 университеті бойынша', 'іздеу қызметтеріне'],
  ] as const)('renders the note and the notice in %s', (locale, note, notice) => {
    capabilities = KB_CAPABILITIES;
    act(() => setLocale(locale));
    render(<PreferencesScreen onStarted={() => {}} />);

    expect(screen.getByTestId('kb-coverage')).toHaveTextContent(note);
    expect(screen.getByTestId('kb-mode-notice')).toHaveTextContent(notice);
    expect(screen.getByTestId('kb-coverage')).not.toHaveTextContent('knowledge base answers');
  });

  it('keeps the live notice and its English note unchanged in live mode', () => {
    const note = 'Live mode searches 19 curated institutions in 15 countries. Results depend on '
      + 'the selected fields and which official pages can be accessed. Missing or unverified '
      + 'evidence stays visible in the results.';
    capabilities = {
      ...CAPABILITIES,
      demo_mode: false,
      live_coverage: {
        ...COVERAGE,
        mode: 'live',
        recall_note: note,
        recall_message: { key: 'coverage.live', params: { institutions: '19', countries: '15' } },
      },
    } as Capabilities;
    render(<PreferencesScreen onStarted={() => {}} />);

    expect(screen.queryByTestId('kb-mode-notice')).not.toBeInTheDocument();
    expect(screen.getByTestId('live-mode-notice')).toHaveTextContent(
      'Live mode fetches real university websites.',
    );
    const panel = screen.getByTestId('live-coverage');
    expect(panel).toHaveTextContent(note);
    for (const country of COVERAGE.countries) {
      expect(panel).toHaveTextContent(country);
    }
  });
});

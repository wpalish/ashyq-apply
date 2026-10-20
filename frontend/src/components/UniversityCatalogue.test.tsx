import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { UniversityCatalogue } from './UniversityCatalogue';
import { api, type UniversityCatalogue as Catalogue } from '@/api/client';
import { setLocale } from '@/lib/i18n';

vi.mock('@/api/client', () => ({ api: { universities: vi.fn() } }));
const startRun = vi.fn().mockResolvedValue(undefined);
let savedProfile: { id: string } | null;
let run: { id: string } | null;
vi.mock('@/lib/store', () => ({ useStore: () => ({ savedProfile, run, startRun, loading: false }) }));
const response: Catalogue = {
  total: 1, catalogue_total: 501, seed_count: 500, countries: ['United States'],
  items: [{ id: 'mit', name: 'Massachusetts Institute of Technology', country: 'United States', city: 'Cambridge',
    aliases: ['MIT'], domain: 'mit.edu', domain_status: 'seed', identity_status: 'seed', programme_status: 'needs_research',
    admissions_status: 'unknown', tuition_status: 'needs_verification', funding_status: 'needs_research',
    seed_tuition_usd: null, seed_ranking: { year: 2027, rank: '1', status: 'seed' },
    seed_version: '2026-10-02/1.0', observed_at: null, sources: {} }],
};
beforeEach(() => {
  vi.clearAllMocks();
  savedProfile = { id: 'profile-1' };
  run = null;
  vi.mocked(api.universities).mockResolvedValue(response);
});

it('shows local candidates with unknown admission fit and no fabricated programme', async () => {
  render(<UniversityCatalogue />);
  expect(await screen.findByText('Massachusetts Institute of Technology')).toBeInTheDocument();
  expect(screen.getByText('Not assessed')).toBeInTheDocument();
  expect(screen.getByText('Research required')).toBeInTheDocument();
  expect(screen.queryByText(/Match \d/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'MIT' } });
  await waitFor(() => expect(api.universities).toHaveBeenLastCalledWith({ q: 'MIT', country: '', offset: 0, profile_id: 'profile-1' }));
});

it('starts live research only for selected identities and navigates to the new run', async () => {
  const onProgress = vi.fn();
  const { rerender } = render(<UniversityCatalogue onProgress={onProgress} />);
  fireEvent.click(await screen.findByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Research selected (1)' }));
  await waitFor(() => expect(startRun).toHaveBeenCalledWith(false, ['mit']));
  run = { id: 'new-run' };
  rerender(<UniversityCatalogue onProgress={onProgress} />);
  expect(onProgress).toHaveBeenCalledOnce();
});

it('keeps candidates visible and allows retry after a catalogue request failure', async () => {
  render(<UniversityCatalogue />);
  await screen.findByText('Massachusetts Institute of Technology');
  vi.mocked(api.universities).mockRejectedValueOnce(new Error('Temporarily unavailable'));
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'MIT' } });
  expect(await screen.findByRole('alert')).toHaveTextContent('Temporarily unavailable');
  expect(screen.getByText('Massachusetts Institute of Technology')).toBeInTheDocument();
  fireEvent.click(screen.getByText('Try again'));
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
});

it('lets a new applicant browse and open profile creation before selecting', async () => {
  savedProfile = null;
  const onStart = vi.fn();
  render(<UniversityCatalogue onStart={onStart} />);
  expect(await screen.findByRole('checkbox')).toBeDisabled();
  fireEvent.click(screen.getByText('Complete profile to research'));
  expect(onStart).toHaveBeenCalledOnce();
  expect(startRun).not.toHaveBeenCalled();
});


it('clears the university selection when switching applicant cases', async () => {
  const { rerender } = render(<UniversityCatalogue />);
  fireEvent.click(await screen.findByRole('checkbox'));
  expect(screen.getByRole('button', { name: 'Research selected (1)' })).toBeEnabled();
  savedProfile = { id: 'another-profile' };
  rerender(<UniversityCatalogue />);
  expect(screen.getByRole('button', { name: 'Research selected (0)' })).toBeDisabled();
  expect(screen.getByRole('checkbox')).not.toBeChecked();
});

// --- kb mode: verified-data coverage on the cards (CAT-1) --------------------

const [mit] = response.items;
const kbResponse: Catalogue = {
  ...response,
  total: 2,
  kb_total: 95,
  items: [
    {
      ...mit!,
      id: 'eth', name: 'ETH Zurich', country: 'Switzerland', city: 'Zurich',
      seed_tuition_usd: { min: 1500, max: 1800, quality: 'seed' },
      knowledge: {
        in_kb: true, programme_page: 'known', core_answered: 5, documents: 8,
        verified_on: '2026-10-19', stale_count: 0, review_label: 'expert-checked, quote verified',
        tuition: {
          amount: 2190, currency: 'CHF', range_low: null, range_high: null, period: 'semester',
          academic_year: null, stale: false, stale_reasons: [], stale_messages: [],
          caveat: 'fee policy page; no academic year printed',
          caveat_message: { key: 'caveat.feePolicy', params: {} },
          source_url: 'https://ethz.ch/fees',
        },
      },
    },
    {
      ...mit!,
      knowledge: {
        in_kb: true, programme_page: 'related_only', core_answered: 4, documents: 1,
        verified_on: '2026-10-19', stale_count: 1, review_label: 'expert-checked, quote verified',
        tuition: {
          amount: 66720, currency: 'USD', range_low: null, range_high: null, period: 'year',
          academic_year: '2026/2027', stale: true,
          stale_reasons: ["academic year 2026/2027 is before the fall 2027 intake's 2027/28"],
          stale_messages: [{ key: 'stale.yearBeforeIntake', params: { year: '2026/2027', intake: 'fall 2027', wanted: '2027/28' } }],
          caveat: null, caveat_message: null, source_url: 'https://mit.edu/fees',
        },
      },
    },
    {
      ...mit!, id: 'other', name: 'Another University',
      knowledge: {
        in_kb: false, programme_page: 'unknown', core_answered: 0, documents: 0, verified_on: null,
        stale_count: 0, review_label: null, tuition: null,
      },
    },
  ],
};

describe('in kb mode', () => {
  beforeEach(() => vi.mocked(api.universities).mockResolvedValue(kbResponse));
  afterEach(() => act(() => setLocale('en')));

  it('shows each card\'s verified coverage, the KB fee with its caveat, and the historical estimate', async () => {
    render(<UniversityCatalogue />);
    const eth = within((await screen.findByText('ETH Zurich')).closest('article')!);
    expect(screen.getByText('95 of 501 universities have verified data')).toBeInTheDocument();
    expect(eth.getByText('Verified knowledge base')).toBeInTheDocument();
    expect(eth.getByText('5/6 answers')).toBeInTheDocument();
    expect(eth.getByText('8 documents')).toBeInTheDocument();
    expect(eth.getByText('Programme page')).toBeInTheDocument();
    expect(eth.getByText(/2,190 CHF per semester/)).toBeInTheDocument();
    expect(eth.getByText(/Caveat: fee policy page; no academic year printed\./)).toBeInTheDocument();
    // The historical estimate stays, below the KB fee and labelled as such.
    expect(eth.getByText('Historical estimate')).toBeInTheDocument();
    expect(eth.getByText(/USD 1,500–1,800; period and scope unverified/)).toBeInTheDocument();
    expect(eth.queryByText('Research required')).not.toBeInTheDocument();
    expect(eth.queryByText('Programme verification needed')).not.toBeInTheDocument();

    const mitCard = within(screen.getByText('Massachusetts Institute of Technology').closest('article')!);
    expect(mitCard.getByText('Related programme only')).toBeInTheDocument();
    expect(mitCard.getByText('1 fact not current')).toBeInTheDocument();
    expect(mitCard.getByText(/66,720 USD a year · academic year 2026\/2027/)).toBeInTheDocument();
    expect(mitCard.getByText('not current')).toBeInTheDocument();
    expect(mitCard.getByText(/Not current: academic year 2026\/2027 is before the fall 2027 intake's 2027\/28\./)).toBeInTheDocument();

    const other = within(screen.getByText('Another University').closest('article')!);
    expect(other.getByText('No verified data yet')).toBeInTheDocument();
    expect(other.getByText('No verified fee yet')).toBeInTheDocument();
  });

  it('keeps only universities with verified data when the filter is on', async () => {
    render(<UniversityCatalogue />);
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Verified data only' }));
    await waitFor(() => expect(api.universities).toHaveBeenLastCalledWith({
      q: '', country: '', offset: 0, profile_id: 'profile-1', verified: true,
    }));
  });

  it('says the coverage in Russian and Kazakh', async () => {
    render(<UniversityCatalogue />);
    await screen.findByText('ETH Zurich');
    act(() => setLocale('ru'));
    expect(screen.getByText('Проверенные данные есть у 95 из 501 университетов')).toBeInTheDocument();
    expect(screen.getAllByText('Проверенная база знаний')).toHaveLength(2);
    expect(screen.getByText('8 документов')).toBeInTheDocument();
    expect(screen.getByText(/2,190 CHF за семестр/)).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Только с проверенными данными' })).toBeInTheDocument();
    act(() => setLocale('kk'));
    expect(screen.getByText('501 университеттің 95-інде тексерілген деректер бар')).toBeInTheDocument();
    expect(screen.getAllByText('Тексерілген білім базасы')).toHaveLength(2);
    expect(screen.getByText('Тексерілген деректер әзірге жоқ')).toBeInTheDocument();
  });
});

it('renders live and demo mode cards exactly as before, with no verified-data filter', async () => {
  render(<UniversityCatalogue />);
  const card = within((await screen.findByText('Massachusetts Institute of Technology')).closest('article')!);
  expect(card.getByText('Programme verification needed')).toBeInTheDocument();
  expect(card.getByText('Research required')).toBeInTheDocument();
  expect(screen.getByText('500 imported universities')).toBeInTheDocument();
  expect(screen.queryByRole('checkbox', { name: 'Verified data only' })).not.toBeInTheDocument();
  expect(screen.queryByText('Verified knowledge base')).not.toBeInTheDocument();
});

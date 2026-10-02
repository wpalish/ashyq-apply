import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { UniversityCatalogue } from './UniversityCatalogue';
import { api, type UniversityCatalogue as Catalogue } from '@/api/client';

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

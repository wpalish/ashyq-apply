import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { ShortlistScreen } from './ShortlistScreen';
import { DocumentsScreen } from './DocumentsScreen';
import type { ProgramResult } from '@/types';

const { universities } = vi.hoisted(() => ({ universities: vi.fn().mockResolvedValue({ items: [], countries: [], total: 0, catalogue_total: 0, seed_count: 0 }) }));
vi.mock('@/api/client', () => ({ api: { universities, deadlinesUrl: (id: string) => `/api/runs/${id}/deadlines.ics` } }));
const decide = vi.fn();
const saveNotes = vi.fn();
let results: ProgramResult[];
vi.mock('@/lib/store', () => ({ useStore: () => ({ results, run: { id: 'run-1', stage: 'awaiting_user_decision', job_status: 'succeeded', job_running: false, stale: false, cancelled: false }, summary: { by_eligibility: { MET: 2 }, by_funding: { UNKNOWN: 2 } }, shortlist: null, decide, saveNotes }) }));

function result(id: string, university: string, country: string): ProgramResult {
  return { id, run_id: 'run-1', university, program: 'Synthetic BSc', country, city: 'Synthetic', degree: 'bachelor', intake: 'fall 2027', eligibility: 'MET', admissions_fit: 'PLAUSIBLE_FIT', funding_fit: 'LIMITED_OPPORTUNITY', best_funding_classification: 'UNKNOWN', rankings: [], requirement_checks: [], claims: [], conflicts: [], unresolved: [], scholarships: [], source_urls: [], user_decision: 'undecided', user_decision_reason: '', user_notes: '', checklist: null, admission_deadline: '2027-01-15' } as unknown as ProgramResult;
}
beforeEach(() => { results = [result('one', 'Alpha Example', 'Netherlands'), result('two', 'Beta Example', 'Canada')]; decide.mockClear(); saveNotes.mockClear(); window.localStorage.clear(); });

it('keeps an unsaved note draft and comparison while removing one filter and then all filters', () => {
  results[0]!.user_notes = 'Original saved note';
  const original = JSON.stringify(results);
  render(<ShortlistScreen />);
  fireEvent.click(within(screen.getByTestId('card-one')).getByRole('button', { name: 'Compare' }));
  fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'university' } });
  fireEvent.click(screen.getByRole('button', { name: 'Edit note' }));
  fireEvent.change(screen.getByTestId('note-input-one'), { target: { value: 'Unsaved draft remains mine' } });
  fireEvent.change(screen.getByLabelText('Country'), { target: { value: 'Netherlands' } });
  fireEvent.click(screen.getByRole('button', { name: 'Remove filter: Country: Netherlands' }));
  expect(screen.getByTestId('note-input-one')).toHaveValue('Unsaved draft remains mine');
  fireEvent.change(screen.getByPlaceholderText('Search universities, programmes or countries…'), { target: { value: 'No match' } });
  expect(screen.queryByTestId('note-input-one')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Clear all filters' }));
  expect(screen.getByTestId('note-input-one')).toHaveValue('Unsaved draft remains mine');
  expect(screen.getByLabelText('Sort by')).toHaveValue('university');
  expect(screen.getByRole('button', { name: 'Compare (1)' })).toBeEnabled();
  expect(screen.getByRole('region', { name: 'Compare selected programmes' })).toHaveTextContent('Alpha Example');
  expect(JSON.stringify(results)).toBe(original);
  expect(decide).not.toHaveBeenCalled(); expect(saveNotes).not.toHaveBeenCalled();
});

it('places the existing empty-checklist action before a 24-date timeline in the DOM', () => {
  results = Array.from({ length: 24 }, (_, i) => result(`synthetic-${i}`, `Synthetic University ${i}`, 'Example'));
  results[0]!.user_decision = 'maybe';
  const navigate = vi.fn();
  render(<DocumentsScreen onNavigate={navigate} />);
  const action = screen.getByRole('button', { name: 'Open plan' });
  const calendar = screen.getByText('Calendar and deadlines across your shortlist (24)').closest('details')!;
  expect(action.compareDocumentPosition(calendar) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getAllByText('Admission application')).toHaveLength(24);
  expect(screen.getByTestId('download-ics')).toHaveAttribute('href', '/api/runs/run-1/deadlines.ics');
  fireEvent.click(action);
  expect(navigate).toHaveBeenCalledExactlyOnceWith('approved');
});

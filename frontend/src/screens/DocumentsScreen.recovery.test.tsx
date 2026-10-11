import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { DocumentsScreen } from '@/screens/DocumentsScreen';
import type { ProgramResult, RunView } from '@/types';

const state = vi.hoisted(() => ({ run: null as RunView | null, results: [] as ProgramResult[] }));
vi.mock('@/lib/store', () => ({ useStore: () => state }));
const navigate = vi.fn();
function research(overrides: Partial<RunView> = {}): RunView {
  return { id: 'synthetic-run', stage: 'awaiting_user_decision', job_status: 'succeeded',
    job_running: false, stale: false, cancelled: false, ...overrides } as RunView;
}
const retained: ProgramResult = {
  id: 'synthetic-result', run_id: 'synthetic-run', university_id: 'synthetic-university',
  university: 'Synthetic University', program: 'BSc Synthetic',
  program_url: null, country: 'Example', city: 'Example', degree: 'bachelor', intake: 'September 2027',
  rankings: [], eligibility: 'PENDING', admissions_fit: 'INSUFFICIENT_DATA',
  funding_fit: 'UNKNOWN', best_funding_classification: 'UNKNOWN',
  requirement_checks: [], missing_prerequisites: [], hard_filter_failures: [], scholarships: [],
  costs: { items: {}, total: null, academic_year: null, source_urls: [], is_range: false },
  funding_gap: null, preference_score: null, ranking: null,
  catalog_attributes: {}, catalog_attributes_source: '',
  admission_deadline: null, admission_deadline_timezone: null, admission_deadline_raw: null,
  deadline_passed: false, climate_fit: '', city_fit: '', workload_fit: '', size_fit: '', campus_fit: '',
  career_notes: '', post_study_work: '', work_during_study: '', conflicts: [], unresolved: [],
  claims: [], source_urls: [], last_verified: null, verification_completeness: 0,
  user_decision: 'maybe', user_decision_reason: '', user_notes: '', decided_at: null,
  checklist: {
    result_id: 'synthetic-result', university: 'Synthetic University', program: 'BSc Synthetic',
    admission_documents: [], scholarship_documents: [], ordered_steps: [],
    applicant_actions: [], school_actions: [], recommender_actions: [], certification_actions: [],
    unresolved: [{ topic: 'documents', university: 'Synthetic University', program: 'BSc Synthetic',
      suggested_contact: null, question: 'Confirm the retained translation requirement',
      why_it_matters: 'The official list was incomplete.', blocking: true }],
    completeness: 'partial', generated_at: null,
  },
};

beforeEach(() => { state.results = [retained]; state.run = null; navigate.mockClear(); localStorage.clear(); });
afterEach(() => { cleanup(); });

it.each([
  { stage: 'failed', job_status: 'queued', job_running: false },
  { stage: 'cancelled', job_status: 'queued', job_running: false },
  { stage: 'failed', job_status: 'running', job_running: true },
  { stage: 'cancelled', job_status: 'running', job_running: true },
] as Partial<RunView>[])('shows accepted active restart while the previous stage remains terminal: %j', (status) => {
  // B4 returns the new active job before its worker transitions the run stage.
  state.run = research(status);
  render(<DocumentsScreen onNavigate={navigate} />);
  expect(screen.getByRole('status')).toHaveTextContent('Research is in progress.');
  expect(screen.queryByText('Research needs attention.')).toBeNull();
  expect(screen.queryByText(/Review the stopped stage/)).toBeNull();
  expect(screen.getByText('Confirm the retained translation requirement')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'View research progress' }));
  expect(navigate).toHaveBeenCalledWith('progress');
});

it.each([
  { stage: 'failed', job_status: 'failed' },
  { stage: 'cancelled', job_status: 'cancelled', cancelled: true },
  { job_status: 'dead' },
  { stage: 'cancelled', job_status: 'succeeded' },
  { stage: 'document_collection', job_status: 'queued', cancelled: true },
  { stage: 'document_collection', job_status: 'running', job_running: true, stale: true },
] as Partial<RunView>[])('keeps an actual terminal, cancelled or stale run in recovery: %j', (status) => {
  state.run = research(status);
  render(<DocumentsScreen onNavigate={navigate} />);
  expect(screen.getByRole('status')).toHaveTextContent('Research needs attention.');
  expect(screen.queryByText('Research is in progress.')).toBeNull();
  expect(screen.queryByText('Document collection is in progress.')).toBeNull();
  expect(screen.getByText('Confirm the retained translation requirement')).toBeVisible();
});

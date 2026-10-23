import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HomeScreen } from './HomeScreen';
import { ApprovedScreen } from './ApprovedScreen';
import { DocumentsScreen } from './DocumentsScreen';
import type { ProgramResult, RunView } from '@/types';

const navigate = vi.fn();
const collectDocuments = vi.fn();
let results: ProgramResult[];
let run: RunView | null;
vi.mock('@/lib/store', () => ({
  useStore: () => ({ savedProfile: { id: 'profile-1' }, results, run,
    summary: null, hydrated: true, capabilities: { demo_mode: true },
    collectDocuments, decide: vi.fn() }),
}));

function programme(overrides: Partial<ProgramResult> = {}): ProgramResult {
  return {
    id: 'result-1', university: 'Example University', program: 'BSc Example',
    user_decision: 'undecided', user_notes: '', country: 'Example', city: 'Example',
    eligibility: 'PENDING', best_funding_classification: 'UNKNOWN',
    admission_deadline: '2027-01-15', scholarships: [], checklist: null,
    ...overrides,
  } as ProgramResult;
}

function research(overrides: Partial<RunView> = {}): RunView {
  return { id: 'run-1', stage: 'awaiting_user_decision', job_status: 'succeeded',
    job_running: false, stale: false, cancelled: false, ...overrides } as RunView;
}

const partialChecklist = {
  result_id: 'result-1', university: 'Example University', program: 'BSc Example',
  admission_documents: [], scholarship_documents: [], ordered_steps: [],
  applicant_actions: [], school_actions: [], recommender_actions: [], certification_actions: [],
  unresolved: [{ topic: 'documents', university: 'Example University', program: 'BSc Example', suggested_contact: null,
    question: 'Confirm the required translation', why_it_matters: 'The source list was incomplete.', blocking: true }],
  completeness: 'partial', generated_at: null,
} as NonNullable<ProgramResult['checklist']>;

beforeEach(() => {
  results = [];
  run = null;
  navigate.mockClear();
  collectDocuments.mockReset().mockResolvedValue(true);
  window.localStorage.clear();
});

describe('Home chooses the next step from the current run', () => {
  it.each([
    { stage: 'failed' }, { stage: 'retryable_failed' }, { stage: 'cancelled', cancelled: true },
    { stale: true, job_status: 'running' }, { job_status: 'dead' },
  ] as Partial<RunView>[])('opens recovery for stopped research: %j', (status) => {
    run = research(status);
    render(<HomeScreen onNavigate={navigate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Review research' }));
    expect(navigate).toHaveBeenCalledWith('progress');
    expect(screen.queryByRole('button', { name: 'Set preferences' })).not.toBeInTheDocument();
  });

  it('reviews the completed empty research instead of silently proposing a new run', () => {
    run = research();
    render(<HomeScreen onNavigate={navigate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Review research' }));
    expect(navigate).toHaveBeenCalledWith('progress');
  });

  it('opens existing partial checklists while keeping unresolved requirements visible', () => {
    results = [programme({ user_decision: 'approved', checklist: partialChecklist })];
    render(<HomeScreen onNavigate={navigate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Open documents' }));
    expect(navigate).toHaveBeenCalledWith('documents');
    expect(screen.getByText(/does not mean an application is ready/)).toBeInTheDocument();
  });

  it('opens Plan when one of the chosen programmes still lacks a checklist', () => {
    results = [programme({ user_decision: 'approved', checklist: partialChecklist }),
      programme({ id: 'result-2', user_decision: 'maybe' })];
    render(<HomeScreen onNavigate={navigate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Open plan' }));
    expect(navigate).toHaveBeenCalledWith('approved');
  });

  it('shows queued collection before offering existing checklists', () => {
    results = [programme({ user_decision: 'approved', checklist: partialChecklist })];
    run = research({ stage: 'document_collection', job_status: 'queued' });
    render(<HomeScreen onNavigate={navigate} />);
    fireEvent.click(screen.getByRole('button', { name: 'View progress' }));
    expect(navigate).toHaveBeenCalledWith('progress');
  });
});

describe('Plan actions', () => {
  it.each([{ name: 'empty research', rows: [] }, { name: 'undecided results', rows: [programme()] }])('offers a direct Find route without selected programmes: $name', ({ rows }) => {
    results = rows;
    render(<ApprovedScreen onCollect={navigate} onFind={() => navigate('shortlist')} />);
    fireEvent.click(screen.getByRole('button', { name: /Explore programmes|Choose programmes/ }));
    expect(navigate).toHaveBeenCalledWith('shortlist');
    expect(collectDocuments).not.toHaveBeenCalled();
  });

  it.each([true, false])('opens Documents only when collection was accepted: %s', async (accepted) => {
    results = [programme({ user_decision: 'approved' })];
    collectDocuments.mockResolvedValue(accepted);
    render(<ApprovedScreen onCollect={navigate} />);
    fireEvent.click(screen.getByTestId('collect-documents'));
    await waitFor(() => expect(collectDocuments).toHaveBeenCalledOnce());
    if (accepted) await waitFor(() => expect(navigate).toHaveBeenCalledOnce());
    else expect(navigate).not.toHaveBeenCalled();
  });
});

describe('Documents preserves findings before checklists arrive', () => {
  it('shows confirmed dates and calendar export even when no checklist has been collected', () => {
    results = [programme()];
    run = research();
    render(<DocumentsScreen onNavigate={navigate} />);
    expect(screen.getByText('Admission application')).toBeVisible();
    expect(screen.getByTestId('download-ics')).toHaveAttribute('href', expect.stringContaining('run-1'));
    fireEvent.click(screen.getByRole('button', { name: 'Choose programmes' }));
    expect(navigate).toHaveBeenCalledWith('shortlist');
  });

  it('sends a saved programme without requirements to Plan', () => {
    results = [programme({ user_decision: 'maybe' })];
    render(<DocumentsScreen onNavigate={navigate} />);
    fireEvent.click(screen.getByRole('button', { name: 'Open plan' }));
    expect(navigate).toHaveBeenCalledWith('approved');
  });

  it('keeps existing partial requirements visible during queued collection', () => {
    results = [programme({ checklist: partialChecklist })];
    run = research({ stage: 'document_collection', job_status: 'queued' });
    render(<DocumentsScreen onNavigate={navigate} />);
    expect(screen.getByText('Document collection is in progress.')).toBeInTheDocument();
    expect(screen.getByText('Confirm the required translation')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'View research progress' }));
    expect(navigate).toHaveBeenCalledWith('progress');
  });

  it('does not pretend a stale worker is still collecting', () => {
    run = research({ stale: true, job_status: 'running' });
    render(<DocumentsScreen onNavigate={navigate} />);
    expect(screen.getByText('Research needs attention.')).toBeInTheDocument();
    expect(screen.queryByText('Document collection is in progress.')).not.toBeInTheDocument();
  });
});

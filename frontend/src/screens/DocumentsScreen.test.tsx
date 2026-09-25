/**
 * The documents screen: how much of each programme's list is ready and how
 * much is missing, and when to start each document - its due date minus the
 * time it takes, never a date the data cannot support.
 */

import { fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DocumentsScreen } from './DocumentsScreen';
import type { DocumentItem, ProgramResult } from '@/types';

let results: ProgramResult[] = [];
let run: unknown = null;

vi.mock('@/lib/store', () => ({
  useStore: () => ({ results, run }),
}));
vi.mock('@/api/client', () => ({ api: { deadlinesUrl: () => '/deadlines.ics' } }));

function item(name: string, overrides: Partial<DocumentItem> = {}): DocumentItem {
  return {
    name, purpose: 'admission', owner: 'applicant', required: true, format_notes: '',
    max_pages: null, max_file_size_mb: null, naming_convention: null, needs_translation: false,
    needs_notarization: false, needs_apostille: false, needs_credential_evaluation: false,
    word_limit: null, character_limit: null, prompt_text: null, deadline: null, deadline_timezone: null,
    depends_on: [], lead_time_days: null, source_url: null, claim_ids: [],
    ...overrides,
  };
}

function programme(id: string, university: string, deadline: string | null, docs: {
  recommender?: DocumentItem[]; applicant?: DocumentItem[];
}): ProgramResult {
  return {
    id, university, program: 'BSc Computing Science', admission_deadline: deadline, scholarships: [],
    checklist: {
      result_id: id, university, program: 'BSc', admission_documents: [], scholarship_documents: [],
      applicant_actions: docs.applicant ?? [], school_actions: [], recommender_actions: docs.recommender ?? [],
      certification_actions: [], ordered_steps: [], unresolved: [], generated_at: '2026-09-25T10:00:00Z',
      completeness: 'official',
    },
  } as unknown as ProgramResult;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date(2026, 8, 25, 12));
  window.localStorage.removeItem('ashyq.docsDone');
  run = null;
  results = [
    programme('groningen', 'University of Groningen', '2027-05-01', {
      recommender: [item('Academic reference', { owner: 'recommender', lead_time_days: 30 })],
      applicant: [
        item('Statement of motivation', { purpose: 'scholarship', lead_time_days: 14, deadline: '2027-02-01' }),
        item('Passport copy', { lead_time_days: 1 }),
      ],
    }),
    programme('leuven', 'KU Leuven', '2027-03-01', { applicant: [item('Curriculum vitae', { lead_time_days: 5 })] }),
  ];
});

afterEach(() => {
  vi.useRealTimers();
});

describe('the documents screen', () => {
  it('says for each programme how much is ready and how much is still missing', () => {
    render(<DocumentsScreen />);
    expect(screen.getByTestId('doc-tab-groningen')).toHaveTextContent('0 of 3 ready · 3 still missing');
    expect(screen.getByTestId('doc-tab-leuven')).toHaveTextContent('0 of 1 ready · 1 still missing');
    fireEvent.click(screen.getByLabelText(/Passport copy/));
    expect(screen.getByTestId('doc-tab-groningen')).toHaveTextContent('1 of 3 ready · 2 still missing');
  });

  it('dates each document from its own deadline, or the admission one, minus the time it takes', () => {
    render(<DocumentsScreen />);
    const reference = screen.getByText('Academic reference').closest('label')!;
    // 1 May 2027 minus 30 days.
    expect(within(reference).getByText(/^start by/)).toHaveTextContent('start by');
    expect(reference.textContent).toMatch(/start by .*(1|01).*Apr.*2027|start by .*Apr.*(1|01).*2027/);
    const essay = screen.getByText('Statement of motivation').closest('label')!;
    // Its own deadline, 1 February 2027, minus 14 days.
    expect(essay.textContent).toMatch(/start by .*18.*Jan.*2027|start by .*Jan.*18.*2027/);
  });

  it('names what to start first: the earliest start date among what is not ready', () => {
    render(<DocumentsScreen />);
    expect(screen.getByTestId('doc-first')).toHaveTextContent('Start first: Statement of motivation.');
    fireEvent.click(screen.getByLabelText(/Statement of motivation/));
    expect(screen.getByTestId('doc-first')).toHaveTextContent('Start first: Academic reference.');
  });

  it('says "start now" when the start date has already gone by', () => {
    results = [programme('soon', 'Soon University', '2026-10-05', {
      recommender: [item('Academic reference', { owner: 'recommender', lead_time_days: 30 })],
    })];
    render(<DocumentsScreen />);
    expect(screen.getByText('start now')).toBeInTheDocument();
    expect(screen.getByTestId('doc-first')).toHaveTextContent('needs starting now');
  });

  it('dates nothing when the deadline has passed or is unknown', () => {
    results = [
      programme('past', 'Past University', '2026-01-15', { applicant: [item('Transcript', { lead_time_days: 21 })] }),
    ];
    render(<DocumentsScreen />);
    expect(screen.queryByText(/start by|start now/)).toBeNull();
    expect(screen.queryByTestId('doc-first')).toBeNull();
  });

  it('never states a chance', () => {
    const { container } = render(<DocumentsScreen />);
    expect(container.textContent).not.toMatch(/%|chance|probab/i);
  });

  it('says the collection is running instead of asking for it again', () => {
    results = [];
    run = { job_status: 'running', stage: 'document_collection', job_running: true };
    render(<DocumentsScreen />);
    expect(screen.getByText('Collecting documents…')).toBeInTheDocument();
    expect(screen.queryByText(/No checklists yet/)).toBeNull();
  });
});

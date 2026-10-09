import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DocumentsScreen } from './DocumentsScreen';
import type { ProgramResult } from '@/types';

const OWNER = 'ashyq.applicantOwner';
const results = [{ id: 'synthetic-result', university: 'Synthetic University', program: 'Synthetic BSc',
  user_decision: 'maybe', admission_deadline: null, scholarships: [], checklist: {
    result_id: 'synthetic-result', university: 'Synthetic University', program: 'Synthetic BSc',
    admission_documents: [], scholarship_documents: [], ordered_steps: [],
    applicant_actions: [{ name: 'Passport', purpose: 'admission', owner: 'applicant',
      lead_time_days: 0, note: null, official_url: null }],
    school_actions: [], recommender_actions: [], certification_actions: [], unresolved: [],
    completeness: 'partial', generated_at: null,
  },
}] as unknown as ProgramResult[];
vi.mock('@/lib/store', () => ({ useStore: () => ({ results, run: null }) }));
function owner(value: string) { localStorage.setItem(OWNER, value); sessionStorage.setItem(OWNER, value); }
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); owner('auth:["user-a","org-a"]'); });

describe('native checklist mark owner scope', () => {
  it('does not restore the previous person mark for even the same result/document id', () => {
    const first = render(<DocumentsScreen />);
    fireEvent.click(screen.getByRole('checkbox'));
    expect(screen.getByRole('checkbox')).toBeChecked();
    first.unmount();
    owner('auth:["user-b","org-b"]');
    render(<DocumentsScreen />);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });
  it('keeps a same-owner mark on ordinary remount without any collection or research', () => {
    const first = render(<DocumentsScreen />);
    fireEvent.click(screen.getByRole('checkbox'));
    first.unmount();
    render(<DocumentsScreen />);
    expect(screen.getByRole('checkbox')).toBeChecked();
  });
});

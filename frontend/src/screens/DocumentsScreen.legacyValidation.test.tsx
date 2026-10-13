import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { DocumentsScreen } from './DocumentsScreen';
import { setLocale } from '@/lib/i18n';
import type { ProgramResult } from '@/types';
const state = vi.hoisted(() => ({ results: [] as ProgramResult[], run: null, savedProfile: null }));
vi.mock('@/lib/store', () => ({ useStore: () => state }));
// This case is deliberately historical browser data, not a server/G3 task.
function result(): ProgramResult {
  return { id: 'synthetic-result', university: 'Synthetic University', program: 'Synthetic BSc',
    user_decision: 'approved', scholarships: [], admission_deadline: null, checklist: {
      result_id: 'synthetic-result', university: 'Synthetic University', program: 'Synthetic BSc', completeness: 'unavailable', generated_at: null,
      admission_documents: [], scholarship_documents: [], ordered_steps: [],
      applicant_actions: [{ name: 'Synthetic transcript', owner: 'applicant', purpose: 'admission', lead_time_days: null, note: null, official_url: null }], school_actions: [], recommender_actions: [], certification_actions: [], unresolved: [] } } as unknown as ProgramResult;
}
beforeEach(() => { setLocale('en'); localStorage.clear(); sessionStorage.clear();
  localStorage.setItem('ashyq.applicantOwner', 'demo'); sessionStorage.setItem('ashyq.applicantOwner', 'demo'); state.results = [result()]; });
it.each(['null', '[]', '{"synthetic-result::Synthetic transcript":"yes"}'])('preserves malformed %s data and blocks checkbox writes', raw => {
  localStorage.setItem('ashyq.docsDone', raw); render(<DocumentsScreen />);
  expect(screen.getByTestId('legacy-document-storage-invalid')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('checkbox')); expect(localStorage.getItem('ashyq.docsDone')).toBe(raw);
});
it('labels earlier browser marks and unavailable lists without claiming official readiness or absence', () => {
  render(<DocumentsScreen />);
  expect(screen.getByText(/earlier checklist marks below are browser-only notes/)).toBeInTheDocument();
  expect(screen.getByText('official list not confirmed')).toBeInTheDocument();
  expect(screen.queryByText('no official list found')).toBeNull();
});

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import type { ProgramResult } from '@/types';
import { DocumentsScreen } from './DocumentsScreen';
let rows: ProgramResult[];
const save = vi.fn();
vi.mock('@/lib/store', () => ({ useStore: () => ({ results: rows, run: { id: 'run' }, setDocumentProgress: save }) }));
beforeEach(() => {
  window.localStorage.clear(); save.mockReset();
  rows = [{ id: 'result', university: 'University', program: 'Computer science', admission_deadline: null, scholarships: [], document_progress: {}, checklist: { generated_at: null, completeness: 'partial', applicant_actions: [{ name: 'Reference', owner: 'applicant', purpose: 'admission', progress_id: 'admission', depends_on: [], claim_ids: [] }], school_actions: [], recommender_actions: [{ name: 'Reference', owner: 'recommender', purpose: 'scholarship', progress_id: 'scholarship', depends_on: [], claim_ids: [] }], certification_actions: [], unresolved: [] } }] as unknown as ProgramResult[];
});
it('shows a tick only after server acknowledgement and restores it from the saved result', async () => {
  let accept!: (value: boolean) => void; save.mockReturnValue(new Promise<boolean>((r) => { accept = r; }));
  const view = render(<DocumentsScreen />); const boxes = screen.getAllByRole('checkbox');
  fireEvent.click(boxes[0]!); expect(boxes[0]).not.toBeChecked(); expect(boxes[0]).toBeDisabled();
  expect(save).toHaveBeenCalledWith('result', 'scholarship', true);
  rows = [{ ...rows[0]!, document_progress: { scholarship: true } }];
  await act(async () => { accept(true); }); view.rerender(<DocumentsScreen />);
  expect(screen.getAllByRole('checkbox')[0]).toBeChecked(); expect(screen.getAllByRole('checkbox')[1]).not.toBeChecked();
  view.unmount(); render(<DocumentsScreen />); expect(screen.getAllByRole('checkbox')[0]).toBeChecked();
});
it('does not lose or invent marks on failure, or import another user browser marks', async () => {
  window.localStorage.setItem('ashyq.docsDone', JSON.stringify({ 'result::Reference': true }));
  save.mockResolvedValue(false); render(<DocumentsScreen />);
  expect(screen.getAllByRole('checkbox').every((box) => !(box as HTMLInputElement).checked)).toBe(true);
  fireEvent.click(screen.getAllByRole('checkbox')[0]!);
  await screen.findByText('Could not save your progress. Your previous marks are kept; try again.');
  await waitFor(() => expect(screen.getAllByRole('checkbox')[0]).toBeEnabled());
  expect(screen.getAllByRole('checkbox')[0]).not.toBeChecked();
});

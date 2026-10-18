import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { PrintableReport } from './PrintableReport';
import type { ProgramResult } from '@/types';
const result = { id:'r1', university:'Synthetic University', program:'Example programme', country:'Example', city:'Example', user_decision:'maybe', eligibility:'MET', conflicts:[],unresolved:[],source_urls:['fixture://example'],admission_deadline:null,funding_gap:null } as unknown as ProgramResult;
it('keeps a name private by default and prints only after an explicit action', () => {
  const print = vi.spyOn(window,'print').mockImplementation(() => {});
  render(<PrintableReport results={[result]} name="Private applicant name" demo />);
  fireEvent.click(screen.getByRole('button',{name:'Preview printable report'}));
  const preview = screen.getByRole('article',{name:'Printable report preview'});
  expect(within(preview).queryByText('Private applicant name')).not.toBeInTheDocument();
  expect(within(preview).getByText(/Synthetic demonstration findings/)).toBeInTheDocument();
  expect(within(preview).getByText('Not enough comparable data')).toBeInTheDocument();
  expect(print).not.toHaveBeenCalled();
  fireEvent.click(within(preview).getByRole('button',{name:'Print / Save as PDF'}));
  expect(print).toHaveBeenCalledTimes(1);
});
it('requires a fresh preview after the applicant explicitly includes their name', () => {
  render(<PrintableReport results={[result]} name="Private applicant name" demo={false} />);
  fireEvent.click(screen.getByRole('checkbox',{name:'Include applicant display name'}));
  fireEvent.click(screen.getByRole('button',{name:'Preview printable report'}));
  expect(within(screen.getByRole('article',{name:'Printable report preview'})).getByText('Private applicant name')).toBeInTheDocument();
});

import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { ProgrammePlan } from '@/lib/applicationPlan';
import { ApplicationNextAction } from './ApplicationNextAction';
const plan = {
  resultId: 'second', university: 'Second university', program: 'Engineering', total: 2, prepared: 1,
  status: 'preparing', reviewReasons: [], nextItem: { item: { name: 'Reference', owner: 'recommender', purpose: 'admission', lead_time_days: 30, source_url: 'https://university.example/requirements' } },
} as unknown as ProgrammePlan;
it('opens the right programme and separates planning estimates from official requirements', () => {
  const open = vi.fn(); render(<ApplicationNextAction plan={plan} onOpenDocuments={open} />);
  expect(screen.getByText('Your referee · Admission requirements')).toBeInTheDocument();
  expect(screen.getByText('Allow approximately 30 days. This is a planning estimate.')).toBeInTheDocument();
  expect(screen.getByRole('link')).toHaveAttribute('href', 'https://university.example/requirements');
  fireEvent.click(screen.getByRole('button', { name: 'Open documents' })); expect(open).toHaveBeenCalledWith('second');
});
it('prepared items lead to portal review without claiming verification or submission', () => {
  render(<ApplicationNextAction plan={{ ...plan, prepared: 2, status: 'review_submission', nextItem: null }} onOpenDocuments={vi.fn()} />);
  expect(screen.getByText(/Review the official application portal/)).toBeInTheDocument();
  expect(screen.getByText(/they do not verify documents or submit an application/)).toBeInTheDocument();
  expect(screen.queryByText(/Prepare Reference/)).not.toBeInTheDocument();
});

import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { SourcesScreen } from './SourcesScreen';
import type { ProgramResult } from '@/types';

const result = {
  id: 'result-1', university: 'Example University', program: 'Computer Science',
  claims: [], unresolved: [], source_urls: [], last_verified: null,
  conflicts: [{
    claim_type: 'TUITION_FEE', subject: 'Tuition',
    claim_ids: ['claim-a', 'claim-b'], values: ['10000', '12000'],
    source_urls: ['https://example.edu/overview', 'https://example.edu/program'],
    preferred_claim_id: 'claim-b', resolution_rule: 'Programme page is more specific.',
    question_for_admissions: 'Which tuition applies?', unresolved: true,
  }],
} as unknown as ProgramResult;

let run: { errors: string[]; unknowns: string[] } | undefined;
vi.mock('@/lib/store', () => ({ useStore: () => ({ results: [result], run }) }));

it('marks the preferred claim by claim ID even when the source URL differs', () => {
  render(<SourcesScreen />);
  const preferred = screen.getByText('more specific source');
  expect(preferred.parentElement).toHaveTextContent('12000');
  expect(preferred.parentElement).not.toHaveTextContent('10000');
});

it('preserves run-level access failures and unknowns even when returned programmes have no questions', () => {
  run = { errors: ['Example page was blocked by robots'], unknowns: ['Deadline not confirmed for the requested intake'] };
  const onProgress = vi.fn();
  render(<SourcesScreen onProgress={onProgress} />);
  expect(screen.getByText('Example page was blocked by robots')).toBeInTheDocument();
  expect(screen.getByText('Deadline not confirmed for the requested intake')).toBeInTheDocument();
  expect(screen.queryByText('Nothing outstanding.')).not.toBeInTheDocument();
  expect(screen.getByText(/Review the research limitations above/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Review research progress' }));
  expect(onProgress).toHaveBeenCalledOnce();
  run = undefined;
});

import { render, screen } from '@testing-library/react';
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

vi.mock('@/lib/store', () => ({ useStore: () => ({ results: [result] }) }));

it('marks the preferred claim by claim ID even when the source URL differs', () => {
  render(<SourcesScreen />);
  const preferred = screen.getByText('more specific source');
  expect(preferred.parentElement).toHaveTextContent('12000');
  expect(preferred.parentElement).not.toHaveTextContent('10000');
});

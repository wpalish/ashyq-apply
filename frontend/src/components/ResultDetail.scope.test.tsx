/**
 * A requirement says who it is published for.
 *
 * The backend reads that from the page and refuses to invent it; the UI's job
 * is to show it when it exists and to stay quiet when it does not — silence
 * about who a rule covers must never read as "everyone".
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ResultDetail } from './ResultDetail';
import type { ProgramResult, RequirementCheck } from '@/types';

function check(overrides: Partial<RequirementCheck> = {}): RequirementCheck {
  return {
    requirement: 'IELTS overall',
    published_value: 6.5,
    applicant_value: 7,
    status: 'MET',
    is_hard_filter: false,
    explanation: 'Published minimum 6.5; applicant 7.',
    claim_ids: [],
    published_scope: '',
    ...overrides,
  } as RequirementCheck;
}

function result(checks: RequirementCheck[]): ProgramResult {
  return {
    id: 'result-1',
    university: 'Delft University of Technology',
    program: 'BSc Computer Science',
    requirement_checks: checks,
    hard_filter_failures: [],
    claims: [],
    conflicts: [],
    unresolved: [],
    scholarships: [],
    source_urls: [],
    rankings: [],
  } as unknown as ProgramResult;
}

describe('a requirement check', () => {
  it('shows the scope the page published it under', () => {
    render(
      <ResultDetail
        result={result([
          check({ published_scope: 'published for intake Fall 2027, population international' }),
        ])}
      />,
    );

    expect(
      screen.getByText('published for intake Fall 2027, population international'),
    ).toBeInTheDocument();
  });

  it('says nothing when the page did not say', () => {
    render(<ResultDetail result={result([check()])} />);

    expect(screen.queryByText(/^published for/)).not.toBeInTheDocument();
    // The requirement itself is still shown: an unscoped rule is evidence,
    // not an error.
    expect(screen.getByText('IELTS overall')).toBeInTheDocument();
  });
});

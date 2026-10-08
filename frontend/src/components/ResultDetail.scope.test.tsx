/**
 * A requirement says who it is published for.
 *
 * The backend reads that from the page and refuses to invent it; the UI's job
 * is to show it when it exists and to stay quiet when it does not — silence
 * about who a rule covers must never read as "everyone".
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ResultDetail } from './ResultDetail';
import type { ProgramResult, RequirementCheck, Scholarship } from '@/types';

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
    country: 'Netherlands',
    city: 'Delft',
    degree: 'bachelor',
    program_url: null,
    eligibility: 'PENDING',
    admissions_fit: 'INSUFFICIENT_DATA',
    best_funding_classification: 'UNKNOWN',
    funding_gap: null,
    admission_deadline: null,
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

function award(overrides: Record<string, unknown> = {}): Scholarship {
  return {
    id: 'sch-1',
    name: 'Example Award',
    scholarship_type: 'MERIT',
    classification: 'PARTIAL_TUITION',
    classification_reason: '',
    amount: null,
    coverage: [],
    meets_applicant_shape: true,
    international_eligible: 'yes',
    citizenship_restrictions: [],
    residency_restrictions: [],
    program_restrictions: [],
    degree_applicability: 'yes',
    applies_to_degrees: [],
    application_mode: 'separate_application',
    requires_extra_essays: false,
    deadline: null,
    renewable: null,
    duration_years: null,
    renewal_requirements: [],
    min_test_scores: {},
    stackable: 'unknown',
    offer_required: 'unknown',
    financial_need_required: 'unknown',
    published_count: null,
    opportunity_exists: true,
    eligibility_checks: [],
    source_urls: [],
    claim_ids: [],
    ...overrides,
  } as unknown as Scholarship;
}

/** The award lives behind the Funding tab; a test that never opens it would
 *  pass for the wrong reason. */
function openFunding() {
  fireEvent.click(screen.getByTestId('tab-funding'));
}

describe('an award', () => {
  it('says when an admission offer must come first', () => {
    render(
      <ResultDetail
        result={
          { ...result([]), scholarships: [award({ offer_required: 'yes' })] } as ProgramResult
        }
      />,
    );

    openFunding();

    expect(
      screen.getByText('An admission offer must be held before applying for this award.'),
    ).toBeInTheDocument();
  });

  it('says when it is decided on financial need', () => {
    render(
      <ResultDetail
        result={
          {
            ...result([]),
            scholarships: [award({ financial_need_required: 'yes' })],
          } as ProgramResult
        }
      />,
    );

    openFunding();

    expect(screen.getByText('Decided on demonstrated financial need.')).toBeInTheDocument();
  });

  it('stays quiet when the award page did not say', () => {
    render(
      <ResultDetail
        result={{ ...result([]), scholarships: [award()] } as ProgramResult}
      />,
    );

    openFunding();

    expect(screen.queryByText(/admission offer/)).not.toBeInTheDocument();
    expect(screen.queryByText(/financial need/)).not.toBeInTheDocument();
  });
});


describe('Documents for saved programmes', () => {
  it.each(['approved', 'maybe'] as const)('explains collection in Plan for %s without asking for another approval', (user_decision) => {
    const saved = { ...result([]), user_decision, checklist: null } as ProgramResult;
    const original = JSON.stringify(saved);
    render(<ResultDetail result={saved} />);
    fireEvent.click(screen.getByTestId('tab-documents'));
    expect(screen.getByText(/Documents are collected for programmes marked “Chosen by you” or “Considering” in Plan/)).toBeInTheDocument();
    expect(screen.getByText(/Use “Collect documents” in Plan/)).toBeInTheDocument();
    expect(screen.getByText(/does not mean an application is ready/)).toBeInTheDocument();
    expect(screen.queryByText(/Approve this row/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Collect documents/ })).not.toBeInTheDocument();
    expect(JSON.stringify(saved)).toBe(original);
  });

  it('continues to show the returned checklist rather than the no-checklist hint', () => {
    const saved: ProgramResult = { ...result([]), user_decision: 'maybe', checklist: {
      result_id: 'result-1', university: 'Delft University of Technology', program: 'BSc Computer Science',
      admission_documents: [], scholarship_documents: [], applicant_actions: [], school_actions: [],
      recommender_actions: [], certification_actions: [], unresolved: [],
      completeness: 'partial', generated_at: '2026-10-09T00:00:00Z',
      ordered_steps: ['1. Confirm the official transcript format'],
    } };
    render(<ResultDetail result={saved} />);
    fireEvent.click(screen.getByTestId('tab-documents'));
    expect(screen.getByText('partially read')).toBeInTheDocument();
    expect(screen.getByText('Confirm the official transcript format')).toBeInTheDocument();
    expect(screen.queryByText(/Use “Collect documents” in Plan/)).not.toBeInTheDocument();
  });
});

/**
 * Knowledge-base mode copy (KB smoke 2026-10-19, B2-B4).
 *
 * In kb mode no page is read during a run, so the detail tabs must not say a
 * page "could not be read", and a verified fact the comparison cannot use is
 * shown, not hidden behind "not found".
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ResultDetail } from './ResultDetail';
import type { ClaimOut, ProgramResult, UnresolvedQuestion } from '@/types';

const STALE_NOTES =
  'Verified knowledge base (expert-checked); quote found on the official page on 2026-10-19. '
  + "Stale, not current: academic year 2026/2027 is before the fall 2027 intake's 2027/28.";

function claim(overrides: Partial<ClaimOut>): ClaimOut {
  return {
    claim_type: 'tuition',
    normalized_value: { amount: 66720, currency: 'USD' },
    original_text_excerpt: 'Tuition 2026-2027: $66,720',
    source_url: 'https://example.edu/tuition',
    academic_year: '2026/2027',
    status: 'POSSIBLY_STALE',
    notes: STALE_NOTES,
    id: 'c1',
    is_stale: true,
    age_days: 0,
    ...overrides,
  } as ClaimOut;
}

function question(overrides: Partial<UnresolvedQuestion>): UnresolvedQuestion {
  return {
    topic: 'funding',
    question: 'Which scholarships does Example University offer?',
    why_it_matters: 'The verified knowledge base names no award for this programme.',
    university: 'Example University',
    program: 'BSc Computer Science',
    suggested_contact: null,
    blocking: false,
    ...overrides,
  };
}

function result(overrides: Record<string, unknown> = {}): ProgramResult {
  return {
    id: 'result-1',
    university: 'Example University',
    program: 'BSc Computer Science',
    country: 'Germany',
    city: 'Berlin',
    degree: 'bachelor',
    program_url: null,
    eligibility: 'NEEDS_OFFICIAL_CLARIFICATION',
    admissions_fit: 'INSUFFICIENT_DATA',
    best_funding_classification: 'UNKNOWN',
    funding_gap: null,
    admission_deadline: null,
    requirement_checks: [],
    hard_filter_failures: [],
    claims: [],
    costs: { items: {}, total: null, academic_year: '2027/28', source_urls: [] },
    conflicts: [],
    unresolved: [],
    scholarships: [],
    source_urls: [],
    rankings: [],
    ...overrides,
  } as unknown as ProgramResult;
}

describe('the Costs tab', () => {
  it('names a verified fee for another academic year instead of saying none was found', () => {
    render(<ResultDetail result={result({ claims: [claim({})] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));

    expect(screen.getByTestId('unused-tuition')).toHaveTextContent(
      "66,720 USD a year, academic year 2026/2027 (not current: academic year 2026/2027 is before the fall 2027 intake's 2027/28)",
    );
    expect(screen.queryByText(/No official cost of attendance was found/)).not.toBeInTheDocument();
  });

  it('keeps the plain notice when no fee was found at all', () => {
    render(<ResultDetail result={result()} />);
    fireEvent.click(screen.getByTestId('tab-costs'));

    expect(
      screen.getByText('No official cost of attendance was found for this programme and intake.'),
    ).toBeInTheDocument();
  });
});

describe('the Funding tab with no award', () => {
  it('says in kb mode that no page was read, and shows the open question', () => {
    render(<ResultDetail result={result({ unresolved: [question({})] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-funding'));

    expect(screen.getByText(/names no scholarship for this programme/)).toBeInTheDocument();
    expect(screen.queryByText(/could be read/)).not.toBeInTheDocument();
    expect(screen.getByText('Which scholarships does Example University offer?')).toBeInTheDocument();
  });

  it('states a verified "none offered" as the outcome', () => {
    const none = 'No institutional scholarship: Example University states that it offers none.';
    render(
      <ResultDetail
        result={result({ funding_gap: { computable: false, reason: '', warnings: [none] } })}
        knowledgeMode="kb"
      />,
    );
    fireEvent.click(screen.getByTestId('tab-funding'));

    expect(screen.getByText(none)).toBeInTheDocument();
  });

  it('keeps the live copy outside kb mode', () => {
    render(<ResultDetail result={result()} knowledgeMode="live" />);
    fireEvent.click(screen.getByTestId('tab-funding'));

    expect(screen.getByText(/No official scholarship page could be read/)).toBeInTheDocument();
  });
});

describe('the Requirements tab of a row that needs clarification', () => {
  it('shows the verified statement behind it', () => {
    const language = question({
      topic: 'language requirement',
      question: 'Not an English requirement: the language requirement is German (DSH 2). Which language certificate does Example University require instead, and do you hold it?',
      why_it_matters: 'Verified on the official page https://example.edu/de: "DSH 2".',
    });
    render(<ResultDetail result={result({ unresolved: [language] })} knowledgeMode="kb" />);

    expect(screen.getByTestId('requirement-questions')).toHaveTextContent(
      'the language requirement is German (DSH 2)',
    );
    expect(screen.getByText(/holds no requirement for this programme/)).toBeInTheDocument();
  });
});

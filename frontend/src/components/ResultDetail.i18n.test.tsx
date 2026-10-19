/**
 * Gap B6: the detail drawer follows the locale switcher, labels and backend
 * questions alike, and English readers see exactly what they saw before.
 */

import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { ResultDetail } from './ResultDetail';
import { setLocale } from '@/lib/i18n';
import type { ProgramResult } from '@/types';

const QUESTION = 'Which official page publishes the Data Science programme?';

function result(): ProgramResult {
  return {
    id: 'result-1',
    university: 'Example University',
    program: 'Data Science',
    country: 'Netherlands',
    city: 'Delft',
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
    conflicts: [],
    unresolved: [
      {
        topic: 'official source',
        question: QUESTION,
        why_it_matters: 'An English sentence no template knows.',
        university: 'Example University',
        program: 'Data Science',
        suggested_contact: null,
        blocking: true,
        question_message: { key: 'question.programmePage', params: { programme: 'Data Science' } },
        why_message: null,
      },
    ],
    scholarships: [],
    source_urls: [],
    rankings: [],
    verification_completeness: 0,
    last_verified: null,
  } as unknown as ProgramResult;
}

afterEach(() => act(() => setLocale('en')));

describe('the result detail in Kazakh and Russian', () => {
  it('is unchanged in English', () => {
    render(<ResultDetail result={result()} />);
    expect(screen.getByTestId('tab-costs').textContent).toBe('Costs');
    expect(screen.getByText('Unverified')).toBeTruthy();
    fireEvent.click(screen.getByTestId('tab-sources'));
    expect(screen.getByText(QUESTION)).toBeTruthy();
    expect(screen.getByText('blocking')).toBeTruthy();
  });

  it('re-renders in Kazakh, keyed questions included, unkeyed ones left in English', () => {
    render(<ResultDetail result={result()} />);
    act(() => setLocale('kk'));
    expect(screen.getByTestId('tab-costs').textContent).toBe('Шығындар');
    expect(screen.getAllByText('Расталмаған').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByTestId('tab-sources'));
    expect(screen.getByText('Data Science бағдарламасы қай ресми бетте жарияланған?')).toBeTruthy();
    expect(screen.getByText('An English sentence no template knows.')).toBeTruthy();
    expect(screen.getByText('маңызды')).toBeTruthy();
  });

  it('speaks Russian in the requirements notice', () => {
    act(() => setLocale('ru'));
    render(<ResultDetail result={result()} />);
    expect(screen.getByText(/Не удалось прочитать ни одного опубликованного требования/)).toBeTruthy();
  });
});

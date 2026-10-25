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

/** I18N-2: a row whose checks, award, ranking and conflict all carry keys. */
function keyedResult(): ProgramResult {
  return {
    ...result(),
    requirement_checks: [
      {
        requirement: 'Minimum GPA',
        published_value: 3.5,
        applicant_value: 3,
        status: 'GAP',
        is_hard_filter: true,
        explanation: 'Published minimum 3.5; applicant 3. The published minimum is not met.',
        claim_ids: [],
        published_scope: '',
        requirement_message: { key: 'req.minGpa', params: {} },
        explanation_message: { key: 'explain.minimumNotMet', params: { published: '3.5', applicant: '3' } },
      },
    ],
    hard_filter_failures: ['Minimum GPA'],
    scholarships: [
      {
        id: 's1',
        name: 'Example Award',
        scholarship_type: 'merit',
        classification: 'UNKNOWN',
        classification_reason: 'No official per-category coverage information was found.',
        classification_messages: [{ key: 'class.noCoverage', params: {} }],
        amount: null,
        coverage: [],
        citizenship_restrictions: [],
        international_eligible: 'yes',
        application_mode: 'separate_application',
        requires_extra_essays: false,
        deadline: null,
        renewable: null,
        duration_years: null,
        stackable: 'unknown',
        offer_required: 'unknown',
        financial_need_required: 'unknown',
        published_count: null,
        renewal_requirements: [],
        eligibility_checks: [
          {
            requirement: 'Scholarship international eligibility',
            published_value: true,
            applicant_value: 'kazakhstan',
            status: 'MET',
            is_hard_filter: false,
            explanation: 'The award is officially open to international students of any nationality.',
            claim_ids: [],
            published_scope: '',
            explanation_message: { key: 'explain.internationalOpen', params: {} },
          },
        ],
        source_urls: [],
        claim_ids: [],
      },
    ],
    ranking: {
      fit: null,
      coverage: 0,
      sort_key: 0,
      gamma: 1,
      axes: [
        {
          axis: 'climate',
          value: null,
          state: 'not_applicable',
          weight: 0.1,
          reason: 'No climate preference was stated.',
          evidence_claim_ids: [],
          reason_message: { key: 'rank.noPreference', params: { axis: 'climate' } },
        },
      ],
      unknown_axes: [],
      not_applicable_axes: ['climate'],
      knocked_out_by: ['Canada is on the applicant\'s excluded list.'],
      knocked_out_messages: [{ key: 'rank.excludedCountry', params: { country: 'Canada' } }],
      bucket: 'EXCLUDED',
      bucket_reason: 'Canada is on the applicant\'s excluded list.',
      bucket_reason_message: { key: 'rank.excludedCountry', params: { country: 'Canada' } },
      weights_source: 'priorities_roc',
      version: '2',
      disclaimer: 'How well this matches your stated priorities, on confirmed data. Not a probability of admission.',
      disclaimer_message: { key: 'rank.disclaimer', params: {} },
    },
    conflicts: [
      {
        claim_type: 'tuition',
        subject: 'the tuition fee',
        claim_ids: ['a', 'b'],
        values: [2530, 2600],
        source_urls: ['https://u.example/a', 'https://u.example/b'],
        preferred_claim_id: 'a',
        resolution_rule: 'Preferring the more specific source (program); the disagreement is shown rather than resolved.',
        question_for_admissions: 'Dear Admissions Office,',
        unresolved: true,
        subject_message: {
          key: 'conflict.subject',
          params: { what: 'the tuition fee' },
          parts: { what: [{ key: 'conflict.label.tuition', params: {} }] },
        },
        resolution_message: { key: 'conflict.preferSpecific', params: { specificity: 'program' } },
      },
    ],
  } as unknown as ProgramResult;
}

describe('the backend\'s explanations on the results tabs (I18N-2)', () => {
  it('are the served English in English', () => {
    render(<ResultDetail result={keyedResult()} />);
    expect(screen.getAllByText('Minimum GPA').length).toBeGreaterThan(0);
    expect(screen.getByText('Published minimum 3.5; applicant 3. The published minimum is not met.')).toBeTruthy();
    fireEvent.click(screen.getByTestId('tab-funding'));
    expect(screen.getByText('No official per-category coverage information was found.')).toBeTruthy();
  });

  it('re-render in Russian: requirements, award, ranking and conflicts', () => {
    render(<ResultDetail result={keyedResult()} />);
    act(() => setLocale('ru'));
    expect(screen.getByText('Минимальный GPA')).toBeTruthy();
    expect(screen.getByText('Опубликованный минимум 3.5; у вас 3. Опубликованный минимум не достигнут.')).toBeTruthy();
    expect(screen.getByText(/Минимальный GPA\./)).toBeTruthy();
    fireEvent.click(screen.getByTestId('tab-funding'));
    expect(screen.getByText('Официальные данные о покрытии по статьям расходов не найдены.')).toBeTruthy();
    expect(screen.getByText('Стипендия официально открыта для иностранных студентов любого гражданства.')).toBeTruthy();
    fireEvent.click(screen.getByTestId('tab-score'));
    expect(screen.getByText('Предпочтение по параметру «Климат» не указано.')).toBeTruthy();
    expect(screen.getAllByText('Canada — в списке исключённых вами стран.').length).toBe(2);
    fireEvent.click(screen.getByTestId('tab-sources'));
    expect(screen.getByText('плата за обучение')).toBeTruthy();
    expect(screen.getByText(/Предпочтение отдаётся более конкретному источнику \(program\)/)).toBeTruthy();
    expect(screen.getByText('Dear Admissions Office,')).toBeTruthy();
  });

  it('re-render in Kazakh', () => {
    act(() => setLocale('kk'));
    render(<ResultDetail result={keyedResult()} />);
    expect(screen.getByText('Ең төменгі GPA')).toBeTruthy();
    fireEvent.click(screen.getByTestId('tab-score'));
    expect(screen.getByText(/Түсу ықтималдығы емес/)).toBeTruthy();
    expect(screen.getByText('«Климат» бойынша қалау көрсетілмеген.')).toBeTruthy();
  });
});

const DIPLOMA = 'Secondary school diploma (certified copy)';
const PASSPORT = 'Passport identity page (copy)';

/** I18N-3: a Fudan-shaped checklist — a stale conditional diploma, a passport after it, and an unkeyed name. */
function documentsResult(): ProgramResult {
  const item = (name: string, owner: string, extra: Record<string, unknown> = {}) => ({
    name, purpose: 'admission', owner, required: false, format_notes: '', lead_time_days: null,
    word_limit: null, max_pages: null, max_file_size_mb: null, needs_translation: false,
    needs_notarization: false, needs_apostille: false, needs_credential_evaluation: false,
    prompt_text: null, deadline: null, depends_on: [], claim_ids: [], source_url: null, ...extra,
  });
  const diploma = item(DIPLOMA, 'school', {
    lead_time_days: 21,
    name_message: { key: 'document.secondary_diploma', params: {} },
    notes_messages: [{ key: 'document.note.conditionWhen', params: { condition: 'the original is not in English' } }],
    format_notes: 'Required only when: the original is not in English.',
  });
  const passport = item(PASSPORT, 'applicant', {
    lead_time_days: 1, depends_on: [DIPLOMA], name_message: { key: 'document.passport', params: {} },
  });
  const offer = item('Offer letter', 'applicant');
  return {
    ...result(),
    unresolved: [],
    claims: [{
      id: 'c1', claim_type: 'required_document', source_url: 'https://example.edu/docs', status: 'POSSIBLY_STALE',
      normalized_value: { document: DIPLOMA, requirement: 'conditional', condition: 'the original is not in English' },
      notes: 'Stale, not current: no verification date.', is_stale: true, age_days: 0,
      stale_messages: [{ key: 'stale.noDate', params: {} }],
    }],
    checklist: {
      result_id: 'result-1', university: 'Example University', program: 'Data Science',
      admission_documents: [diploma, passport, offer], scholarship_documents: [],
      applicant_actions: [passport, offer], school_actions: [diploma], recommender_actions: [], certification_actions: [],
      ordered_steps: [
        `1. Your school: ${DIPLOMA} (allow ~21 days)`,
        `2. You: ${PASSPORT} (allow ~1 day) — after ${DIPLOMA}, Offer letter`,
        '3. You: Offer letter',
      ],
      unresolved: [], generated_at: null, completeness: 'partial',
    },
  } as unknown as ProgramResult;
}

describe('the documents tab names the documents in the reader\'s words (I18N-3)', () => {
  it('is the served English in English', () => {
    render(<ResultDetail result={documentsResult()} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-documents'));
    expect(screen.getByText(DIPLOMA)).toBeTruthy();
    expect(screen.getByText(`Your school: ${DIPLOMA} (allow ~21 days)`)).toBeTruthy();
    expect(screen.getByText(`You: ${PASSPORT} (allow ~1 day) — after ${DIPLOMA}, Offer letter`)).toBeTruthy();
  });

  it('re-renders in Russian: names, steps and what a step waits for', () => {
    render(<ResultDetail result={documentsResult()} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-documents'));
    act(() => setLocale('ru'));
    expect(screen.getByText('Аттестат о среднем образовании (заверенная копия)')).toBeTruthy();
    expect(screen.getByText('Страница паспорта с личными данными (копия)')).toBeTruthy();
    expect(screen.getByText('Условие, как опубликовано: the original is not in English.')).toBeTruthy();
    expect(screen.getByText('Ваша школа: Аттестат о среднем образовании (заверенная копия) (заложите ~21 день)')).toBeTruthy();
    expect(screen.getByText(
      'Вы: Страница паспорта с личными данными (копия) (заложите ~1 день) — после: ' +
        'Аттестат о среднем образовании (заверенная копия), Offer letter',
    )).toBeTruthy();
    // A name outside the 18-kind vocabulary keeps its English.
    expect(screen.getAllByText('Offer letter').length).toBeGreaterThan(0);
    expect(document.body.textContent).not.toContain(DIPLOMA);
  });

  it('re-renders in Kazakh', () => {
    act(() => setLocale('kk'));
    render(<ResultDetail result={documentsResult()} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-documents'));
    expect(screen.getByText('Орта білім туралы аттестат (куәландырылған көшірме)')).toBeTruthy();
    expect(screen.getByText('Мектебіңіз: Орта білім туралы аттестат (куәландырылған көшірме) (~21 күн уақыт бөліңіз)')).toBeTruthy();
    expect(document.body.textContent).not.toContain(PASSPORT);
  });
});

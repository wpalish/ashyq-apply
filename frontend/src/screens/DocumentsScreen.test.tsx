/**
 * I18N-2: the Documents screen's fixed labels follow the locale switcher; the
 * university's own words (document names, prompts) stay as published, and an
 * English reader sees exactly what the screen said before.
 */

import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { DocumentsScreen } from './DocumentsScreen';
import { setLocale } from '@/lib/i18n';
import type { ProgramResult } from '@/types';

const letter = {
  name: 'Reference letter', purpose: 'admission', owner: 'recommender', required: true,
  format_notes: '', lead_time_days: 30, word_limit: null, max_pages: 2, max_file_size_mb: null,
  needs_translation: true, needs_notarization: false, needs_apostille: false,
  needs_credential_evaluation: false, prompt_text: null, deadline: null, depends_on: [], claim_ids: [],
};
const passport = { ...letter, name: 'Passport copy', owner: 'applicant', lead_time_days: 1, max_pages: null, needs_translation: false };

const result = {
  id: 'r1', university: 'Example University', program: 'Computer Science', scholarships: [],
  admission_deadline: '2020-01-15', admission_deadline_timezone: null,
  checklist: {
    result_id: 'r1', university: 'Example University', program: 'Computer Science',
    admission_documents: [letter, passport], scholarship_documents: [],
    applicant_actions: [passport], school_actions: [], recommender_actions: [letter], certification_actions: [],
    ordered_steps: [], generated_at: null, completeness: 'partial',
    unresolved: [{
      topic: 'documents', question: 'What documents does Example University require for Computer Science?',
      why_it_matters: 'No official document list could be read, so nothing can be prepared in advance.',
      university: 'Example University', program: 'Computer Science', suggested_contact: 'admissions office',
      blocking: false,
      question_message: { key: 'question.documents', params: { university: 'Example University', programme: 'Computer Science' } },
      why_message: { key: 'why.noDocumentList', params: {} },
    }],
  },
} as unknown as ProgramResult;

vi.mock('@/lib/store', () => ({ useStore: () => ({ results: [result], run: null, capabilities: null }) }));

afterEach(() => act(() => setLocale('en')));

describe('the Documents screen', () => {
  it('says what it said before in English', () => {
    render(<DocumentsScreen />);
    expect(screen.getByRole('heading', { name: /Prepare with confidence\./ })).toBeTruthy();
    expect(screen.getByText('Your referee')).toBeTruthy();
    expect(screen.getByText('You')).toBeTruthy();
    expect(screen.getByText('for admission · allow ~30 days · max 2 pages · certified translation required')).toBeTruthy();
    expect(screen.getByText('for admission · allow ~1 day')).toBeTruthy();
    expect(screen.getByText('partially read')).toBeTruthy();
    expect(screen.getByText('Still to confirm')).toBeTruthy();
    expect(screen.getByText('Ask: admissions office')).toBeTruthy();
    expect(screen.getByText('Calendar and deadlines across your shortlist (1)')).toBeTruthy();
    expect(screen.getByText('Admission application')).toBeTruthy();
    expect(screen.getByText('passed')).toBeTruthy();
  });

  it('re-renders in Russian, the document names kept as published', () => {
    render(<DocumentsScreen />);
    act(() => setLocale('ru'));
    expect(screen.getByText('Документы и сроки')).toBeTruthy();
    expect(screen.getByText('Reference letter')).toBeTruthy();
    expect(screen.getByText('для поступления · заложите ~30 дней · не более 2 стр. · нужен заверенный перевод')).toBeTruthy();
    expect(screen.getByText('для поступления · заложите ~1 день')).toBeTruthy();
    expect(screen.getByText('Ещё нужно уточнить')).toBeTruthy();
    expect(screen.getByText('Заявление на поступление')).toBeTruthy();
    expect(screen.getByText(/Example University/, { selector: 'strong' })).toBeTruthy();
  });

  it('re-renders in Kazakh, the open question included', () => {
    act(() => setLocale('kk'));
    render(<DocumentsScreen />);
    expect(screen.getByText('Құжаттар мен мерзімдер')).toBeTruthy();
    expect(screen.getByText('Әлі нақтылау керек')).toBeTruthy();
    expect(screen.getByText('Кімнен сұрау керек: admissions office')).toBeTruthy();
    expect(screen.queryByText('Still to confirm')).toBeNull();
    expect(screen.queryByText('No official document list could be read, so nothing can be prepared in advance.')).toBeNull();
  });
});

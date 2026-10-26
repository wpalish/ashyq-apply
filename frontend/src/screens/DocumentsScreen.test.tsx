/**
 * I18N-2: the Documents screen's fixed labels follow the locale switcher; I18N-3:
 * the 18 document names and the backend's note sentences follow it too. The
 * university's own words (a name a live page used, prompts, a condition) stay
 * as published, and an English reader sees exactly what the screen said before.
 */

import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { DocumentsScreen } from './DocumentsScreen';
import { setLocale } from '@/lib/i18n';
import type { DocumentItem, MessageRef, ProgramResult } from '@/types';

const letter = {
  name: 'Reference letter', purpose: 'admission', owner: 'recommender', required: true,
  format_notes: '', lead_time_days: 30, word_limit: null, max_pages: 2, max_file_size_mb: null,
  needs_translation: true, needs_notarization: false, needs_apostille: false,
  needs_credential_evaluation: false, prompt_text: null, deadline: null, depends_on: [], claim_ids: [],
};
const passport = { ...letter, name: 'Passport copy', owner: 'applicant', lead_time_days: 1, max_pages: null, needs_translation: false };
/** I18N-3: a Fudan-shaped item — a conditional diploma from another cycle's list, two stale reasons. */
const KEYED_NOTES: (MessageRef | null)[] = [
  { key: 'document.note.conditionWhen', params: { condition: 'the original is not in English' } },
  {
    key: 'document.note.possiblyOutdated',
    params: { reasons: 'document list published for "Guide 2026", not the fall 2027 intake; no verification date' },
    parts: {
      reasons: [
        { key: 'stale.documentsForCycle', params: { cycle: 'Guide 2026', intake: 'fall 2027' } },
        { key: 'stale.noDate', params: {} },
      ],
    },
  },
];
const diploma: DocumentItem = {
  ...letter, name: 'Secondary school diploma (certified copy)', owner: 'school', required: false,
  lead_time_days: 21, max_pages: null, needs_notarization: false,
  format_notes:
    'Required only when: the original is not in English. Possibly outdated: document list published for ' +
    '"Guide 2026", not the fall 2027 intake; no verification date.',
  name_message: { key: 'document.secondary_diploma', params: {} },
  notes_messages: KEYED_NOTES,
} as unknown as DocumentItem;

const result = {
  id: 'r1', university: 'Example University', program: 'Computer Science', scholarships: [],
  admission_deadline: '2020-01-15', admission_deadline_timezone: null,
  checklist: {
    result_id: 'r1', university: 'Example University', program: 'Computer Science',
    admission_documents: [letter, passport, diploma], scholarship_documents: [],
    applicant_actions: [passport], school_actions: [diploma], recommender_actions: [letter], certification_actions: [],
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

describe('the backend\'s document names and notes (I18N-3)', () => {
  const NOTES =
    'Required only when: the original is not in English. Possibly outdated: document list published for ' +
    '"Guide 2026", not the fall 2027 intake; no verification date.';

  it('are the served English in English', () => {
    render(<DocumentsScreen />);
    expect(screen.getByText('Secondary school diploma (certified copy)')).toBeTruthy();
    expect(document.body.textContent).toContain(`allow ~21 days · ${NOTES} · certified translation required`);
  });

  it('are said in Russian: the name, the condition sentence and the stale caveat with its reasons', () => {
    render(<DocumentsScreen />);
    act(() => setLocale('ru'));
    expect(screen.getByText('Аттестат о среднем образовании (заверенная копия)')).toBeTruthy();
    const text = document.body.textContent ?? '';
    expect(text).toContain(
      'Требуется, только если: the original is not in English. Возможно, устарело: список документов ' +
        'опубликован для «Guide 2026», а не для набора fall 2027; нет даты проверки. · нужен заверенный перевод',
    );
    expect(text).not.toContain('Possibly outdated');
    expect(text).not.toContain('Secondary school diploma');
    // A name outside the 18-kind vocabulary has no key and stays as served.
    expect(screen.getByText('Reference letter')).toBeTruthy();
  });

  it('are said in Kazakh', () => {
    act(() => setLocale('kk'));
    render(<DocumentsScreen />);
    expect(screen.getByText('Орта білім туралы аттестат (куәландырылған көшірме)')).toBeTruthy();
    const text = document.body.textContent ?? '';
    expect(text).toContain('Тек мына жағдайда талап етіледі: the original is not in English.');
    expect(text).toContain(
      'Ескірген болуы мүмкін: құжаттар тізімі fall 2027 қабылдауына емес, «Guide 2026» үшін жарияланған; ' +
        'тексерілген күні жоқ.',
    );
    expect(text).not.toContain('Possibly outdated');
  });

  it('keep a sentence no template knows in English, beside the keyed one', () => {
    diploma.notes_messages = [null, diploma.notes_messages![1]!];
    try {
      act(() => setLocale('ru'));
      render(<DocumentsScreen />);
      expect(document.body.textContent).toContain(
        'Required only when: the original is not in English. Возможно, устарело:',
      );
    } finally {
      diploma.notes_messages = KEYED_NOTES;
    }
  });
});

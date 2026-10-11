/** Typed synthetic preparation DTOs for native unit controls; no official question content. */
import type {
  PreparationAccess, PreparationAttemptInput, PreparationCatalogue, PreparationCheck,
  PreparationLesson, PreparationPlan, PreparationProgress, StudyAttempt,
} from '@/types';
export const version = 'starter-2026-10-11-v1';
export const access = (allowed = true, development_only = false): PreparationAccess => ({
  allowed, development_only, reason: development_only ? 'development_mode' : allowed ? 'subscription_term' : 'no_eligible_subscription',
  subscription_id: allowed && !development_only ? 'synthetic-subscription' : null,
  starts_at: allowed ? '2026-10-01T00:00:00Z' : null, ends_at: allowed ? '2026-11-01T00:00:00Z' : null,
});
export const catalogue = (): PreparationCatalogue => ({
  version, notice: 'Original synthetic starters; no official scaled score.',
  exams: [
    { id: 'ielts_academic', title: 'IELTS Academic', role: 'language', course_status: 'starter', track_ids: ['ielts_reading'], official_info_urls: ['https://example.test/ielts/info'], official_practice_urls: [], notice: 'Confirm the accepted edition and recipient policy.', checked_date: '2026-10-11' },
    { id: 'digital_sat', title: 'Digital SAT', role: 'academic', course_status: 'starter', track_ids: ['sat_math', 'sat_reading_writing'], official_info_urls: ['https://example.test/sat/info'], official_practice_urls: [], notice: 'Original practice is not an official mock.', checked_date: '2026-10-11' },
    ...(['toefl_ibt', 'det', 'hsk_hskk', 'csca'] as const).map(id => ({
      id, title: { toefl_ibt: 'TOEFL iBT', det: 'DET', hsk_hskk: 'HSK / HSKK', csca: 'CSCA' }[id],
      role: id === 'csca' ? 'academic' as const : 'language' as const, course_status: 'planned' as const,
      track_ids: [], official_info_urls: [`https://example.test/${id}/info`], official_practice_urls: [],
      notice: 'Course planned; acceptance and current edition must be confirmed.', checked_date: '2026-10-11',
    })),
  ],
  tracks: [
    { id: 'ielts_reading', title: 'IELTS Reading', lesson_ids: ['ielts-reading-1'] },
    { id: 'sat_math', title: 'SAT Math', lesson_ids: ['sat-math-1'] },
    { id: 'sat_reading_writing', title: 'SAT Reading & Writing', lesson_ids: ['sat-rw-1'] },
  ],
  lessons: [
    { id: 'ielts-reading-1', track_id: 'ielts_reading', title: 'Synthetic Reading', question_count: 1 },
    { id: 'sat-math-1', track_id: 'sat_math', title: 'Synthetic Math', question_count: 1 },
    { id: 'sat-rw-1', track_id: 'sat_reading_writing', title: 'Synthetic R&W', question_count: 1 },
  ],
});
export function lesson(id = 'ielts-reading-1', marker = ''): PreparationLesson {
  const summary = catalogue().lessons.find(item => item.id === id)!;
  return { ...summary, version, unofficial: true, introduction: `Original synthetic introduction ${marker}`,
    questions: [{ id: `${id}-q1`, prompt: `Choose the supported answer ${marker}`,
      choices: [{ id: 'a', text: `Supported ${marker}` }, { id: 'b', text: `Unsupported ${marker}` }] }],
  };
}
export function attempt(input: PreparationAttemptInput, profile_id = 'case-a'): StudyAttempt {
  return { ...structuredClone(input), id: `saved-${input.attempt_id}`, profile_id,
    correct: 1, total: 1, created_at: '2026-10-11T10:00:00Z',
    feedback: input.answers.map(answer => ({ question_id: answer.question_id, selected_choice_id: answer.choice_id,
      correct_choice_id: 'a', correct: answer.choice_id === 'a', explanation: 'Synthetic explanation; this is practice only.' })),
  };
}
export const progress = (profile_id = 'case-a', attempts: StudyAttempt[] = []): PreparationProgress => ({
  profile_id, attempts, attempt_count: attempts.length,
  correct: attempts.reduce((n, item) => n + item.correct, 0), answered: attempts.reduce((n, item) => n + item.total, 0),
  completed_lesson_ids: [...new Set(attempts.map(item => item.lesson_id))],
});
export function check(): PreparationCheck {
  return {
    requirement_check: { requirement: 'IELTS overall', published_value: 7, applicant_value: 7,
      status: 'NEEDS_OFFICIAL_CLARIFICATION', is_hard_filter: false,
      explanation: 'A waiver may apply; confirm the programme and intake policy.',
      claim_ids: ['claim-a', 'https://example.test/policy'], published_scope: 'BSc Synthetic · September 2027 · stated population only' },
    evidence_state: 'current', policy: 'waiver_check', lesson_ids: ['ielts-reading-1'],
    claim_ids: ['claim-a', 'https://example.test/policy'], source_urls: ['https://example.test/policy'],
    claims: [{ id: 'claim-a', claim_type: 'language_requirement', normalized_value: 7,
      original_text_excerpt: 'Synthetic policy excerpt preserving scope.', source_url: 'https://example.test/policy',
      page_title: 'Synthetic policy', relevant_section: 'Language', official_domain: true,
      program: 'BSc Synthetic', subject_key: null, intake: 'September 2027', academic_year: '2027/28',
      accessed_at: '2026-10-11T00:00:00Z', source_specificity: 'program_intake', confidence: 1,
      status: 'VERIFIED_CURRENT', extraction_method: 'fixture', notes: '', is_stale: false, age_days: 0,
      scope: { university: 'Synthetic University', faculty: null, programme: 'BSc Synthetic', degree: 'bachelor',
        intake: 'September 2027', academic_year: '2027/28', population: 'stated population only',
        nationality: null, residency: null, qualification: null },
    }],
  };
}
export const plan = (profile_id = 'case-a', result_id: string | null = null): PreparationPlan => ({
  profile_id, result_id, research_access: false, evidence_state: 'unknown', checks: [],
  notice: 'No confirmed programme requirement. Personal practice does not invent one.',
});
export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}

import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import type { ApplicantCase, DocumentItem, ProgramResult, RunView, StoredProfile } from '@/types';

export function profile(id: string): StoredProfile {
  return { ...structuredClone(DEFAULT_PROFILE), id, display_name: `Saved ${id}`,
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' };
}
export function caseRow(id: string): ApplicantCase {
  return { id, profile_id: id, display_name: `Saved ${id}`, status: 'draft', run_count: 1,
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' };
}
export function research(id: string, profileId: string): RunView {
  return { id, profile_id: profileId, stage: 'awaiting_user_decision', demo_mode: true,
    cancelled: false, progress: 1, candidates_found: 1, programs_verified: 1,
    pages_checked: 1, pages_failed: 0, claims_recorded: 0, results_count: 1, decided_count: 0,
    stages: [], errors: [], retry_urls: [], settings: {}, created_at: '2026-01-01T00:00:00Z',
    started_at: '2026-01-01T00:00:00Z', finished_at: '2026-01-01T00:00:00Z',
    job_running: false, job_error: '', job_id: null, job_status: 'succeeded', job_attempts: 1,
    candidate_limit: 1, verify_limit: 1, fetch_tiers: {}, stale: false,
    worker_id: null, heartbeat_at: null, recovery_count: 0 };
}
export function result(id: string, runId: string): ProgramResult {
  const value: ProgramResult = {
  id: 'synthetic-result', run_id: 'synthetic-run', university_id: 'synthetic-university',
  university: 'Synthetic University', program: 'BSc Synthetic',
  program_url: null, country: 'Example', city: 'Example', degree: 'bachelor', intake: 'September 2027',
  rankings: [], eligibility: 'PENDING', admissions_fit: 'INSUFFICIENT_DATA',
  funding_fit: 'UNKNOWN', best_funding_classification: 'UNKNOWN',
  requirement_checks: [], missing_prerequisites: [], hard_filter_failures: [], scholarships: [],
  costs: { items: {}, total: null, academic_year: null, source_urls: [], is_range: false },
  funding_gap: null, preference_score: null, ranking: null,
  catalog_attributes: {}, catalog_attributes_source: '',
  admission_deadline: null, admission_deadline_timezone: null, admission_deadline_raw: null,
  deadline_passed: false, climate_fit: '', city_fit: '', workload_fit: '', size_fit: '', campus_fit: '',
  career_notes: '', post_study_work: '', work_during_study: '', conflicts: [], unresolved: [],
  claims: [], source_urls: [], last_verified: null, verification_completeness: 0,
  user_decision: 'maybe', user_decision_reason: '', user_notes: '', decided_at: null,
  checklist: {
    result_id: 'synthetic-result', university: 'Synthetic University', program: 'BSc Synthetic',
    admission_documents: [], scholarship_documents: [], ordered_steps: [],
    applicant_actions: [], school_actions: [], recommender_actions: [], certification_actions: [],
    unresolved: [{ topic: 'documents', university: 'Synthetic University', program: 'BSc Synthetic',
      suggested_contact: null, question: 'Confirm the retained translation requirement',
      why_it_matters: 'The official list was incomplete.', blocking: true }],
    completeness: 'partial', generated_at: null,
  },
};
  const passport: DocumentItem = {
    name: 'Passport', purpose: 'admission', owner: 'applicant', required: true,
    format_notes: '', max_pages: null, max_file_size_mb: null, naming_convention: null,
    needs_translation: false, needs_notarization: false, needs_apostille: false,
    needs_credential_evaluation: false, word_limit: null, character_limit: null,
    prompt_text: null, deadline: null, deadline_timezone: null, depends_on: [],
    lead_time_days: 0, source_url: null, claim_ids: [],
  };
  return { ...value, id, run_id: runId, checklist: value.checklist
    ? { ...value.checklist, result_id: id, unresolved: [], applicant_actions: [passport] }
    : null };
}

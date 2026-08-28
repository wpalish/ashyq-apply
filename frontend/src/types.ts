/**
 * Contracts mirroring the backend Pydantic schemas.
 *
 * The unions below are the same controlled vocabularies the API exposes at
 * /api/vocabulary. A backend test parses this file and fails if the two drift
 * apart, so a renamed status cannot silently reach the UI as an unstyled chip.
 */

export type EligibilityStatus =
  | 'MET' | 'PENDING' | 'GAP' | 'NOT_APPLICABLE' | 'NEEDS_OFFICIAL_CLARIFICATION';

export type AdmissionsFit =
  | 'STRONGER_FIT' | 'PLAUSIBLE_FIT' | 'AMBITIOUS' | 'INSUFFICIENT_DATA';

export type FundingFit =
  | 'CONFIRMED_OPPORTUNITY' | 'COMPETITIVE_OPPORTUNITY' | 'LIMITED_OPPORTUNITY'
  | 'NOT_ELIGIBLE' | 'UNKNOWN';

export type FundingClassification =
  | 'FULL_RIDE_CONFIRMED' | 'FULL_TUITION' | 'LARGE_GRANT' | 'PARTIAL'
  | 'NEED_BASED_POSSIBLE' | 'NOT_ELIGIBLE' | 'UNKNOWN';

export type ClaimStatus =
  | 'VERIFIED_CURRENT' | 'POSSIBLY_STALE' | 'CONFLICTING' | 'UNVERIFIED'
  | 'NOT_FOUND' | 'NEEDS_OFFICIAL_CLARIFICATION';

export type SourceSpecificity =
  | 'program_intake' | 'program' | 'university_admissions' | 'application_portal'
  | 'scholarship_administrator' | 'government' | 'admissions_office_reply'
  | 'aggregator' | 'unknown';

export type UserDecision = 'undecided' | 'approved' | 'maybe' | 'rejected';

export type PipelineStage =
  | 'queued' | 'profile_validation' | 'candidate_discovery' | 'program_verification'
  | 'funding_discovery' | 'assessment' | 'awaiting_user_decision'
  | 'document_collection' | 'completed' | 'failed'
  /** The worker holding the run stopped without finishing; the work itself did not fail. */
  | 'retryable_failed'
  | 'cancelled';

export type CostCategory =
  | 'tuition' | 'mandatory_fees' | 'housing' | 'meals' | 'health_insurance'
  | 'books' | 'travel' | 'visa' | 'personal';

export type ScholarshipType =
  | 'merit' | 'need_based' | 'automatic' | 'competitive' | 'departmental'
  | 'honors' | 'government' | 'external' | 'unknown';

export type ApplicationMode = 'automatic' | 'separate' | 'nomination' | 'unknown';

export type DocumentOwner = 'applicant' | 'school' | 'recommender' | 'third_party';

export type DegreeLevel = 'foundation' | 'bachelor' | 'master' | 'phd';

export type Coverage = 'yes' | 'no' | 'partial' | 'unknown';

export interface Money {
  amount: number;
  currency: string;
  academic_year: string | null;
  as_of?: string | null;
  is_estimate: boolean;
  range_low: number | null;
  range_high: number | null;
  source_url?: string | null;
}

export interface RankingEntry {
  source: string;
  year: number;
  position: string;
  url: string | null;
}

export interface RequirementCheck {
  requirement: string;
  published_value: unknown;
  applicant_value: unknown;
  status: EligibilityStatus;
  is_hard_filter: boolean;
  explanation: string;
  claim_ids: string[];
}

export interface CoverageBreakdown {
  category: CostCategory;
  covered: Coverage;
  amount: Money | null;
  claim_ids: string[];
}

export interface Scholarship {
  id: string;
  name: string;
  scholarship_type: ScholarshipType;
  classification: FundingClassification;
  classification_reason: string;
  amount: Money | null;
  amount_is_percentage_of_tuition: number | null;
  coverage: CoverageBreakdown[];
  international_eligible: 'yes' | 'no' | 'unknown';
  citizenship_restrictions: string[];
  program_restrictions: string[];
  application_mode: ApplicationMode;
  requires_extra_essays: boolean | null;
  deadline: string | null;
  deadline_timezone: string | null;
  deadline_raw: string | null;
  renewable: boolean | null;
  duration_years: number | null;
  renewal_requirements: string[];
  min_test_scores: Record<string, number>;
  stackable: 'yes' | 'no' | 'unknown';
  published_count: number | null;
  available_this_intake: 'yes' | 'no' | 'unknown';
  eligibility_checks: RequirementCheck[];
  source_urls: string[];
  claim_ids: string[];
  last_verified: string | null;
}

export interface CostBreakdown {
  items: Partial<Record<CostCategory, Money>>;
  total: Money | null;
  academic_year: string | null;
  source_urls: string[];
  is_range: boolean;
}

export interface FundingGap {
  computable: boolean;
  gap: Money | null;
  gap_low: number | null;
  gap_high: number | null;
  total_cost: Money | null;
  confirmed_aid: Money | null;
  stackable_aid: Money | null;
  reason: string;
  year_mismatch: boolean;
  currency_mismatch: boolean;
  category_mismatch: boolean;
  warnings: string[];
}

export interface ScoreComponent {
  name: string;
  raw: number;
  weight: number;
  weighted: number;
  explanation: string;
  data_present: boolean;
}

export interface ExplainableScore {
  total: number;
  max_possible: number;
  components: ScoreComponent[];
  missing_data_penalty: number;
  missing_fields: string[];
  disclaimer: string;
}

export interface ClaimOut {
  claim_type: string;
  normalized_value: unknown;
  original_text_excerpt: string;
  source_url: string;
  page_title: string;
  relevant_section: string;
  official_domain: boolean;
  program: string | null;
  subject_key: string | null;
  intake: string | null;
  academic_year: string | null;
  accessed_at: string;
  source_specificity: SourceSpecificity;
  confidence: number;
  status: ClaimStatus;
  extraction_method: string;
  notes: string;
  id: string;
  is_stale: boolean;
  age_days: number;
}

export interface Conflict {
  claim_type: string;
  subject: string;
  claim_ids: string[];
  values: unknown[];
  source_urls: string[];
  preferred_claim_id: string | null;
  resolution_rule: string;
  question_for_admissions: string;
  unresolved: boolean;
}

export interface UnresolvedQuestion {
  topic: string;
  question: string;
  why_it_matters: string;
  university: string | null;
  program: string | null;
  suggested_contact: string | null;
  blocking: boolean;
}

export interface DocumentItem {
  name: string;
  purpose: 'admission' | 'scholarship' | 'both';
  owner: DocumentOwner;
  required: boolean;
  format_notes: string;
  max_pages: number | null;
  max_file_size_mb: number | null;
  naming_convention: string | null;
  needs_translation: boolean;
  needs_notarization: boolean;
  needs_apostille: boolean;
  needs_credential_evaluation: boolean;
  word_limit: number | null;
  character_limit: number | null;
  prompt_text: string | null;
  deadline: string | null;
  deadline_timezone: string | null;
  depends_on: string[];
  lead_time_days: number | null;
  source_url: string | null;
  claim_ids: string[];
}

export interface DocumentChecklist {
  result_id: string;
  university: string;
  program: string;
  admission_documents: DocumentItem[];
  scholarship_documents: DocumentItem[];
  applicant_actions: DocumentItem[];
  school_actions: DocumentItem[];
  recommender_actions: DocumentItem[];
  certification_actions: DocumentItem[];
  ordered_steps: string[];
  unresolved: UnresolvedQuestion[];
  generated_at: string | null;
  completeness: 'official' | 'partial' | 'unavailable';
}

export interface ProgramResult {
  id: string;
  run_id: string;
  university: string;
  university_id: string;
  country: string;
  city: string;
  program: string;
  program_url: string | null;
  degree: DegreeLevel;
  intake: string;
  rankings: RankingEntry[];
  eligibility: EligibilityStatus;
  admissions_fit: AdmissionsFit;
  funding_fit: FundingFit;
  best_funding_classification: FundingClassification;
  requirement_checks: RequirementCheck[];
  missing_prerequisites: string[];
  hard_filter_failures: string[];
  scholarships: Scholarship[];
  costs: CostBreakdown;
  funding_gap: FundingGap | null;
  preference_score: ExplainableScore | null;
  admission_deadline: string | null;
  admission_deadline_timezone: string | null;
  admission_deadline_raw: string | null;
  deadline_passed: boolean;
  climate_fit: string;
  city_fit: string;
  workload_fit: string;
  career_notes: string;
  post_study_work: string;
  work_during_study: string;
  conflicts: Conflict[];
  unresolved: UnresolvedQuestion[];
  claims: ClaimOut[];
  source_urls: string[];
  last_verified: string | null;
  verification_completeness: number;
  user_decision: UserDecision;
  user_decision_reason: string;
  user_notes: string;
  decided_at: string | null;
  checklist: DocumentChecklist | null;
}

export interface StageView {
  stage: string;
  status: 'pending' | 'running' | 'done' | 'failed' | 'skipped';
  detail: string;
  error: string;
  items_done: number;
  items_total: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface RunView {
  id: string;
  profile_id: string;
  stage: PipelineStage;
  demo_mode: boolean;
  cancelled: boolean;
  progress: number;
  candidates_found: number;
  programs_verified: number;
  pages_checked: number;
  pages_failed: number;
  claims_recorded: number;
  results_count: number;
  decided_count: number;
  stages: StageView[];
  errors: string[];
  retry_urls: string[];
  settings: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  job_running: boolean;
  job_error: string;
  candidate_limit: number;
  verify_limit: number;
  fetch_tiers: Record<string, number>;
  /** The run claims to be working but its worker has gone silent. */
  stale: boolean;
  worker_id: string | null;
  heartbeat_at: string | null;
  recovery_count: number;
}

export interface ProfileGap {
  field_path: string;
  status: string;
  severity: 'blocking' | 'high' | 'medium' | 'low';
  impact: string;
  suggested_action: string | null;
}

export interface ProfileValidationReport {
  gaps: ProfileGap[];
  can_proceed: boolean;
  blocking_count: number;
  summary: string;
}

export interface ShortlistSummary {
  total: number;
  by_eligibility: Record<string, number>;
  by_funding: Record<string, number>;
  by_decision: Record<string, number>;
  with_conflicts: number;
  with_open_questions: number;
  demo_data: boolean;
}

export interface Capabilities {
  demo_mode: boolean;
  data_origin: string;
  adapters: { name: string; role: string; live: boolean }[];
  fetch_tiers: string[];
  currency: { supported: string[]; rate_date: string; rate_source: string };
  guarantees: string[];
  limits: string[];
}

export interface StoredProfile {
  id: string;
  created_at: string;
  updated_at: string;
  display_name: string;
  [key: string]: unknown;
}

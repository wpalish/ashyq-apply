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
  | 'NOT_FOUND' | 'NEEDS_OFFICIAL_CLARIFICATION'
  /** Historical record, kept forever: the page no longer says this (see backend enum). */
  | 'SUPERSEDED';

export type SourceSpecificity =
  | 'program_intake' | 'program' | 'university_admissions' | 'application_portal'
  | 'scholarship_administrator' | 'government' | 'admissions_office_reply'
  | 'aggregator' | 'unknown';

export type UserDecision = 'undecided' | 'approved' | 'maybe' | 'rejected';

/**
 * Where a row sits in a balanced list.
 *
 * Deliberately not "safety / match / reach": *safety* reads as a promise, and
 * nothing here predicts an admission.
 */
export type Bucket =
  | 'WELL_PLACED' | 'PLAUSIBLE' | 'AMBITIOUS' | 'OUT_OF_BUDGET'
  | 'NEEDS_CLARIFICATION' | 'EXCLUDED';

/** The six groups the applicant ranks; their order becomes the axis weights. */
export type PriorityGroup =
  | 'funding' | 'academic' | 'country' | 'city_climate' | 'career' | 'campus_life';

export type JobStatus =
  | 'queued' | 'running' | 'succeeded'
  /** Failed but retryable: it will be picked up again after its backoff. */
  | 'failed'
  /** Attempts exhausted. Needs a human decision; never retried automatically. */
  | 'dead'
  | 'cancelled';

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

/** A three-valued answer. Nothing in this product defaults to "yes". */
export type Tristate = 'yes' | 'no' | 'unknown';

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
  /** Who the publishing page said the rule is for, in its own terms. Empty
   *  when the page did not say — which is not the same as "everyone", and is
   *  why this is shown as a quiet line rather than a badge. */
  published_scope: string;
  /** Keys for `requirement` and `explanation` (I18N-2); served, never stored. */
  requirement_message?: MessageRef | null;
  explanation_message?: MessageRef | null;
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
  /** `classification_reason` sentence by sentence, keyed; only when every sentence is (I18N-2). */
  classification_messages?: MessageRef[] | null;
  amount: Money | null;
  amount_is_percentage_of_tuition: number | null;
  coverage: CoverageBreakdown[];
  // Eligibility, one question per field. These were previously collapsed,
  // which let "an award exists" stand in for "this applicant can apply".
  international_eligible: Tristate;
  citizenship_restrictions: string[];
  residency_restrictions: string[];
  program_restrictions: string[];
  degree_applicability: Tristate;
  degree_applicability_reason: string;
  applies_to_degrees: string[];
  application_mode: ApplicationMode;
  requires_extra_essays: boolean | null;
  deadline: string | null;
  deadline_timezone: string | null;
  deadline_raw: string | null;
  renewable: boolean | null;
  duration_years: number | null;
  renewal_requirements: string[];
  min_test_scores: Record<string, number>;
  stackable: Tristate;
  /** Whether an admission offer must be held before applying. "unknown" is
   *  the common answer: most award pages never say. */
  offer_required: Tristate;
  /** Whether the award is decided on demonstrated financial need. */
  financial_need_required: Tristate;
  published_count: number | null;

  // Availability, decomposed. A missing deadline is not availability.
  opportunity_exists: boolean;
  currently_available: Tristate;
  applicant_eligible: Tristate;
  application_window_open: Tristate;
  deadline_known: boolean;
  deadline_passed: boolean;
  award_current_for_intake: Tristate;
  /** Derived from the fields above; never set directly. */
  available_this_intake: Tristate;
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

/** What the cost figure rests on; null when no cost basis was established. */
export type CostBasis = 'published_total' | 'itemised_complete' | 'itemised_partial';

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
  cost_basis: CostBasis | null;
  /** Core categories the cost table omits; non-empty only for itemised_partial. */
  missing_categories: CostCategory[];
  warnings: string[];
  /** Keys for `reason` and each warning (gap B6); absent from older servers. */
  reason_message?: MessageRef | null;
  warning_messages?: (MessageRef | null)[] | null;
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

export interface RerankIn {
  priorities?: PriorityGroup[];
  weights?: Record<string, number>;
  gamma?: number;
  /** Off by default: trying an ordering out must not rewrite the profile. */
  persist?: boolean;
}

export interface BalancedShortlist {
  chosen: ProgramResult[];
  /** What the quotas could not fill, said out loud rather than hidden. */
  notes: string[];
  quotas: Record<string, number>;
}

export interface AxisScore {
  axis: string;
  /** null whenever `state` is not 'known'. */
  value: number | null;
  /** 'unknown' lowers coverage; 'not_applicable' is ignored by both numbers. */
  state: 'known' | 'unknown' | 'not_applicable';
  weight: number;
  reason: string;
  evidence_claim_ids: string[];
  reason_message?: MessageRef | null;
}

export interface RankingV2 {
  /** Match against the stated priorities, 0-1. Never a probability. */
  fit: number | null;
  /** Share of the weight that rests on verified data. */
  coverage: number;
  sort_key: number;
  gamma: number;
  axes: AxisScore[];
  unknown_axes: string[];
  not_applicable_axes: string[];
  knocked_out_by: string[];
  bucket: Bucket;
  bucket_reason: string;
  weights_source: 'priorities_roc' | 'weights_override';
  version: '2';
  disclaimer: string;
  /** Keys for `bucket_reason`, `knocked_out_by` (index for index) and `disclaimer` (I18N-2). */
  bucket_reason_message?: MessageRef | null;
  knocked_out_messages?: (MessageRef | null)[] | null;
  disclaimer_message?: MessageRef | null;
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
  /** One key per reason in the notes' "Stale, not current:" sentence (gap B6). */
  stale_messages?: (MessageRef | null)[] | null;
  /** The key of the notes' "Caveat: …" sentence: current, but not fully verified. */
  caveat_message?: MessageRef | null;
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
  /** Keys for `subject` and `resolution_rule` (I18N-2). The drafted email stays English on purpose. */
  subject_message?: MessageRef | null;
  resolution_message?: MessageRef | null;
}

/**
 * A stable key for one English sentence the backend wrote, with its
 * parameters (gap B6). The English is still served beside it; see
 * `lib/messages.ts`.
 */
export interface MessageRef {
  key: string;
  params: Record<string, string>;
  parts?: Record<string, (MessageRef | null)[]>;
}

export interface UnresolvedQuestion {
  topic: string;
  question: string;
  why_it_matters: string;
  university: string | null;
  program: string | null;
  suggested_contact: string | null;
  blocking: boolean;
  question_message?: MessageRef | null;
  why_message?: MessageRef | null;
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
  /** Served only (I18N-3): the key of `name` when it is one of the 18 document kinds. */
  name_message?: MessageRef | null;
  /** Served only (I18N-3): one key per sentence of `format_notes`, null where none matched. */
  notes_messages?: (MessageRef | null)[] | null;
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

/** Why a KB value is unknown (WHY-1); mirrors `app.schemas.result.KbUnknownKind`. */
export type KbUnknownKind =
  | 'not_published'
  | 'access'
  | 'unverified_quote'
  | 'undated'
  | 'other_year'
  | 'not_researched'
  | 'unspecified';

/** One unanswered KB question and why (kb mode only). */
export interface KbUnknown {
  question: string;
  kind: KbUnknownKind;
  checked_on: string | null;
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
  ranking: RankingV2 | null;
  catalog_attributes: Record<string, string>;
  catalog_attributes_source: string;
  admission_deadline: string | null;
  admission_deadline_timezone: string | null;
  admission_deadline_raw: string | null;
  deadline_passed: boolean;
  previous_cycle_deadline?: string | null;
  climate_fit: string;
  city_fit: string;
  workload_fit: string;
  size_fit: string;
  campus_fit: string;
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
  /** WHY-1: absent outside kb mode and when every question is answered. */
  kb_unknown?: KbUnknown[];
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
  //: Diagnostics that mean 'the page was read and does not say'. Absent on
  //: runs made before the two were separated.
  unknowns?: string[];
  retry_urls: string[];
  settings: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  job_running: boolean;
  job_error: string;
  /** The durable job backing this run, if one exists. */
  job_id: string | null;
  /** queued | running | succeeded | failed | dead | cancelled */
  job_status: JobStatus | null;
  job_attempts: number;
  candidate_limit: number;
  verify_limit: number;
  fetch_tiers: Record<string, number>;
  /** The run claims to be working but its worker has gone silent. */
  stale: boolean;
  worker_id: string | null;
  heartbeat_at: string | null;
  recovery_count: number;
  //: When the evidence is next re-read automatically (ISO 8601), if ever.
  next_recheck_at?: string | null;
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

/** What the knowledge base says about the CS programme page (`routes_universities.PROGRAMME_PAGES`). */
export type KbProgrammePage = 'known' | 'related_only' | 'not_offered' | 'unknown';

/** A KB fee as published, judged by the run's stale and caveat rules. */
export interface CatalogueKbTuition {
  amount: number;
  currency: string;
  range_low: number | null;
  range_high: number | null;
  /** As published ("semester", "year"); null when the page gave none. */
  period: string | null;
  academic_year: string | null;
  stale: boolean;
  stale_reasons: string[];
  /** `stale_reasons` keyed, one per reason (null for an unknown shape), for ru and kk. */
  stale_messages: (MessageRef | null)[];
  caveat: string | null;
  caveat_message: MessageRef | null;
  source_url: string;
}

/**
 * A catalogue card's verified-data coverage (kb mode only; null in live and
 * demo mode). Checked against the backend by `test_frontend_contract.py`.
 */
export interface CatalogueKnowledge {
  in_kb: boolean;
  programme_page: KbProgrammePage;
  /** The six core questions answered: known, or verified as not applicable. */
  core_answered: number;
  documents: number;
  verified_on: string | null;
  stale_count: number;
  review_label: string | null;
  tuition: CatalogueKbTuition | null;
}

export interface Capabilities {
  demo_mode: boolean;
  /** Where answers come from; optional so an older API still type-checks. */
  knowledge_mode?: 'demo' | 'kb' | 'live';
  data_origin: string;
  /** `active` appears in kb mode only: false for the web adapters a kb-mode run never uses. */
  adapters: { name: string; role: string; live: boolean; active?: boolean }[];
  fetch_tiers: string[];
  currency: {
    supported: string[];
    rate_date: string;
    rate_source: string;
    rate_age_days?: number;
    //: Empty while the snapshot is fresh; a sentence to show verbatim once it is not.
    stale_warning?: string;
    //: Its key (I18N-2); absent while the snapshot is fresh.
    stale_warning_message?: MessageRef;
  };
  guarantees: string[];
  limits: string[];
  //: What live mode can actually reach. Someone switching demo mode off
  //: pictures the open web; the truth is a curated registry, and the
  //: difference has to be on screen before they choose, not after.
  //: RM-1: in kb mode the block names the knowledge base's reach instead
  //: (`mode: 'kb'`, `institutions` = KB entries with verified data); demo
  //: mode serves no `mode`, which reads as live. `recall_message` localises
  //: `recall_note` (`msg.coverage.kb` / `msg.coverage.live`).
  live_coverage: {
    institutions: number;
    countries: string[];
    recall_note: string;
    mode?: 'kb' | 'live';
    catalogue_total?: number;
    recall_message?: MessageRef;
    //: MODE-1: a demo server whose knowledge mode is kb adds the kb block,
    //: because unticking demo there starts a kb run, not a live one.
    kb_coverage?: KbCoverage;
  };
}

//: The kb-mode coverage block (RM-1), as `live_coverage` serves it on a kb
//: server and as `live_coverage.kb_coverage` on a kb-configured demo server.
export interface KbCoverage {
  mode: 'kb';
  institutions: number;
  countries: string[];
  catalogue_total: number;
  recall_note: string;
  recall_message: MessageRef;
}

export interface StoredProfile {
  id: string;
  created_at: string;
  updated_at: string;
  display_name: string;
  [key: string]: unknown;
}

export interface AuthPrincipal {
  user_id: string;
  email: string;
  display_name: string;
  organization_id: string;
  organization_name: string;
  role: string;
  local_development: boolean;
}

export interface AuthStatus {
  enabled: boolean;
  registration_enabled: boolean;
  password_reset_enabled?: boolean;
  authenticated: boolean;
  principal: AuthPrincipal | null;
}

export interface ApplicantCase {
  id: string;
  profile_id: string;
  display_name: string;
  status: string;
  run_count: number;
  created_at: string;
  updated_at: string;
}

export type PaymentMethod = 'phone' | 'qr';

export interface Pricing {
  case_unlock_price_kzt: number;
  currency: string;
  payments_enabled: boolean;
  includes: string[];
}

export interface EntitlementView {
  profile_id: string;
  full_access: boolean;
  /** Cases left on the current subscription; null when there is none. */
  subscription_cases_left: number | null;
  /** Bought-but-not-started subscriptions waiting behind it. */
  subscription_queued: number;
}

export interface OrderView {
  id: string;
  profile_id: string;
  status: 'created' | 'pending' | 'paid' | 'cancelled' | 'expired' | 'failed';
  method: PaymentMethod;
  amount_kzt: number;
  phone_masked: string;
  qr_payload: string;
  qr_expires_at: string | null;
  created_at: string;
}

/* --- Community ---------------------------------------------------------
 *
 * `status` is nullable everywhere it appears. Null means the person has not
 * said, which the interface shows as "not stated" — never as waitlist.
 */

export type ApplicantStatus = 'accepted' | 'waitlist';

/** Who may open a conversation with you. */
export type DirectMessagePolicy = 'anyone' | 'threads' | 'nobody';

export interface PersonCard {
  user_id: string;
  display_name: string;
  status: ApplicantStatus | null;
  target_city: string;
  target_major: string;
  universities: string[];
  /** How this person can be reached — never anything about them. */
  dm_policy: DirectMessagePolicy;
  bio: string;
  can_message?: boolean | null;
}

export interface MyProfile {
  joined: boolean;
  profile: PersonCard | null;
}

export interface ProfileInput {
  status: ApplicantStatus | null;
  target_city: string;
  target_major: string;
  bio: string;
  universities: string[];
  dm_policy: DirectMessagePolicy;
}

export interface MessageView {
  id: string;
  body: string;
  created_at: string;
  /** Whose side of the conversation this is: the screen places the line by it. */
  mine: boolean;
}

export interface ConversationView {
  person: PersonCard;
  last_message: string;
  last_message_at: string;
  unread: number;
}

export interface MessagePage {
  person: PersonCard;
  items: MessageView[];
  next_cursor: string | null;
}

export interface AuthorRef {
  user_id: string;
  display_name: string;
  status: ApplicantStatus | null;
}

export interface PostView {
  id: string;
  author: AuthorRef;
  body: string;
  tags: string[];
  reply_count: number;
  created_at: string;
}

export interface ReplyView {
  id: string;
  post_id: string;
  author: AuthorRef;
  body: string;
  created_at: string;
}

/** A keyset page. `next_cursor` is null on the last one. */
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}

export interface PeopleFilters {
  city?: string;
  university?: string;
  major?: string;
  status?: string;
}

export interface FeedFilters {
  tag?: string;
  author?: string;
  city?: string;
  university?: string;
  status?: string;
}

/**
 * One value read off an applicant's transcript, with the words it came from.
 *
 * `field` is the dotted path into the profile form, so a suggestion can be
 * applied without a second mapping table drifting out of step with the API.
 * Nothing here is applied until the applicant says so.
 */
export interface TranscriptSuggestion {
  field: string;
  label: string;
  value: unknown;
  excerpt: string;
}

export interface TranscriptReading {
  suggestions: TranscriptSuggestion[];
  /** Why the list is empty, when it is. A scan of paper carries no text. */
  note: string;
}

/* --- Moderation -------------------------------------------------------- */

export type ReportReason =
  | 'harassment'
  | 'personal_information'
  | 'impersonation'
  | 'spam'
  | 'misleading_advice'
  | 'other';

export type ReportTarget = 'post' | 'reply' | 'message' | 'profile';

export type ReportStatus = 'open' | 'actioned' | 'dismissed';

export interface ReporterRef {
  user_id: string;
  display_name: string;
}

export interface ReportView {
  id: string;
  reporter: ReporterRef;
  subject_type: ReportTarget;
  subject_id: string;
  subject_author: ReporterRef | null;
  reason: ReportReason;
  note: string;
  /** What the content said when it was reported, kept for after it is gone. */
  excerpt: string;
  status: ReportStatus;
  created_at: string;
  resolved_by: string | null;
  resolution_note: string;
}

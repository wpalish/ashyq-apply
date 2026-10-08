import { describe, expect, it } from 'vitest';
import type { ClaimOut, DocumentChecklist, DocumentItem, ProgramResult } from '@/types';
import { deriveApplicationPlan } from './applicationPlan';

const TODAY = '2027-01-01';
const doc = (progressId: string | undefined, name: string, extra: Partial<DocumentItem> = {}): DocumentItem => ({
  progress_id: progressId, name, purpose: 'admission', owner: 'applicant', required: true,
  format_notes: '', max_pages: null, max_file_size_mb: null, naming_convention: null,
  needs_translation: false, needs_notarization: false, needs_apostille: false, needs_credential_evaluation: false,
  word_limit: null, character_limit: null, prompt_text: null, deadline: null, deadline_timezone: null,
  depends_on: [], lead_time_days: null, source_url: 'https://university.example/apply', claim_ids: [], ...extra,
});
const list = (docs: DocumentItem[], extra: Partial<DocumentChecklist> = {}): DocumentChecklist => ({
  result_id: 'A', university: 'University', program: 'Computer science', admission_documents: docs,
  scholarship_documents: [], applicant_actions: docs.filter((item) => item.owner === 'applicant'),
  school_actions: docs.filter((item) => item.owner === 'school'),
  recommender_actions: docs.filter((item) => item.owner === 'recommender'),
  certification_actions: docs.filter((item) => item.owner === 'third_party'),
  ordered_steps: [], unresolved: [], generated_at: null, completeness: 'official', ...extra,
});
const result = (extra: Partial<ProgramResult> = {}): ProgramResult => ({
  id: 'A', run_id: 'run', university: 'University', university_id: 'uni', program: 'Computer science',
  degree: 'bachelor', intake: 'fall 2027', user_decision: 'approved', checklist: null,
  document_progress: {}, unresolved: [], conflicts: [], claims: [], admission_deadline: null,
  deadline_passed: false, eligibility: 'NEEDS_OFFICIAL_CLARIFICATION', ...extra,
} as ProgramResult);
const scope = { degree: 'bachelor', intake: 'fall 2027', programme: 'Computer science' };
const claim = (extra: Partial<ClaimOut> & { scope?: Record<string, string | null> | null } = {}): ClaimOut => ({
  id: 'deadline', claim_type: 'admission_deadline', normalized_value: '2027-03-01',
  source_url: 'https://university.example/deadlines', official_domain: true,
  status: 'VERIFIED_CURRENT', is_stale: false, program: 'Computer science', intake: 'fall 2027',
  source_specificity: 'program_intake', scope, ...extra,
} as ClaimOut);
const plan = (row: ProgramResult) => deriveApplicationPlan([row], TODAY)[0]!;

describe('saved application tasks', () => {
  it('keeps programmes and marks separate, and excludes rejected or undecided rows', () => {
    const requirement = doc('passport', 'Passport');
    const rows = [
      result({ id: 'B', program: 'Physics', user_decision: 'maybe', checklist: list([requirement]) }),
      result({ checklist: list([requirement]), document_progress: { passport: true, orphan: true } }),
      result({ id: 'reject', user_decision: 'rejected' }), result({ id: 'undecided', user_decision: 'undecided' }),
    ];
    const plans = deriveApplicationPlan(rows, TODAY);
    expect(plans.map((item) => [item.resultId, item.total, item.prepared])).toEqual([['A', 1, 1], ['B', 1, 0]]);
    expect(plans[1]!.pendingRequiredIds).toEqual(['passport']);
    expect(plan(result({ run_id: 'new-run', checklist: list([requirement]) })).prepared).toBe(0);
  });

  it('counts duplicate projections once but retains distinct requirement identities', () => {
    const a = doc('applicant-ref', 'Reference');
    const b = doc('school-ref', 'Reference', { owner: 'school' });
    const c = doc('scholarship-ref', 'Reference', { purpose: 'scholarship' });
    const d = doc('another-scope', 'Reference');
    const checklist = list([a, b, d], { scholarship_documents: [c], applicant_actions: [a, c, d] });
    const derived = plan(result({ checklist, document_progress: { 'applicant-ref': true } }));
    expect(derived.total).toBe(4); expect(derived.prepared).toBe(1);
    expect(new Set(derived.items.map((item) => item.progressId))).toEqual(new Set([a.progress_id, b.progress_id, c.progress_id, d.progress_id]));
  });

  it('never uses a name or orphan mark as the identity of an untracked document', () => {
    const derived = plan(result({ checklist: list([doc(undefined, 'Reference')]), document_progress: { Reference: true } }));
    expect(derived.items).toEqual([]); expect(derived.total).toBe(0); expect(derived.prepared).toBe(0);
    expect(derived.untracked).toBeGreaterThan(0); expect(derived.status).toBe('needs_review');
  });

  it('orders required tasks before optional, longest estimates first, with stable ties', () => {
    const docs = [
      doc('optional', 'Portfolio', { required: false, lead_time_days: 90 }),
      doc('passport', 'Passport', { lead_time_days: 1 }),
      doc('ref-z', 'Ref Z', { owner: 'recommender', lead_time_days: 30 }),
      doc('ref-a', 'Ref A', { owner: 'recommender', lead_time_days: 30 }),
      doc('transcript', 'Transcript', { owner: 'school', lead_time_days: 30 }),
    ];
    const derived = plan(result({ checklist: list(docs) }));
    expect(derived.items.map((item) => item.progressId)).toEqual(['ref-a', 'ref-z', 'transcript', 'passport', 'optional']);
    expect(derived.nextItem?.progressId).toBe('ref-a');
    expect(plan(result({ checklist: list([...docs].reverse()) })).items.map((item) => item.progressId))
      .toEqual(derived.items.map((item) => item.progressId));
    expect(plan(result({ checklist: list(docs), document_progress: { 'ref-a': true, 'ref-z': true, transcript: true, passport: true } })).nextItem?.progressId).toBe('optional');
  });

  it('only unlocks a named prerequisite after the corresponding saved task is prepared', () => {
    const docs = [doc('transcript', 'Transcript'), doc('translate', 'Translation', { depends_on: ['  TRANSCRIPT  '], lead_time_days: 21 })];
    const first = plan(result({ checklist: list(docs) }));
    expect(first.nextItem?.progressId).toBe('transcript');
    expect(first.items.find((item) => item.progressId === 'translate')?.blockedDependencies).toEqual(['  TRANSCRIPT  ']);
    const after = plan(result({ checklist: list(docs), document_progress: { transcript: true } }));
    expect(after.nextItem?.progressId).toBe('translate'); expect(after.nextItem?.blocked).toBe(false);
  });

  it('keeps unknown milestones, ambiguous names, self dependencies and cycles blocked', () => {
    const docs = [
      doc('award', 'Award form', { depends_on: ['admission offer letter'] }),
      doc('ref-1', 'Reference'), doc('ref-2', 'Reference', { owner: 'school' }),
      doc('depends-ref', 'Submit references', { depends_on: ['Reference'] }),
      doc('self', 'Self', { depends_on: ['Self'] }),
      doc('cycle-a', 'A', { depends_on: ['B'] }), doc('cycle-b', 'B', { depends_on: ['A'] }),
    ];
    const derived = plan(result({ checklist: list(docs), document_progress: { 'ref-1': true, 'ref-2': true } }));
    expect(derived.items.filter((item) => !item.completed).every((item) => item.blocked)).toBe(true);
    expect(derived.nextItem).toBeNull(); expect(derived.status).toBe('needs_review');
  });

  it('still offers an unblocked optional task when required tasks await an unknown prerequisite', () => {
    const derived = plan(result({ checklist: list([
      doc('award', 'Award form', { depends_on: ['admission offer letter'] }),
      doc('optional', 'Optional CV', { required: false }),
    ]) }));
    expect(derived.nextItem?.progressId).toBe('optional'); expect(derived.status).toBe('needs_review');
  });

  it('does not unlock a chain by ticking an intermediate task whose own milestone is unconfirmed', () => {
    const derived = plan(result({ checklist: list([
      doc('award', 'Award form', { depends_on: ['admission offer letter'] }),
      doc('submit', 'Submit award', { depends_on: ['Award form'] }),
    ]), document_progress: { award: true } }));
    expect(derived.items.find((item) => item.progressId === 'submit')?.blocked).toBe(true);
    expect(derived.nextItem).toBeNull(); expect(derived.status).toBe('needs_review');
  });

  it('distinguishes no collection, an empty official list and partial/unavailable lists', () => {
    expect(plan(result()).status).toBe('not_collected');
    expect(plan(result({ checklist: list([]) })).status).toBe('needs_review');
    for (const completeness of ['partial', 'unavailable'] as const) {
      const derived = plan(result({ checklist: list([doc('passport', 'Passport')], { completeness }), document_progress: { passport: true } }));
      expect(derived.prepared).toBe(1); expect(derived.status).toBe('needs_review');
    }
  });

  it('advances from preparation to submission review without mutating evidence or eligibility', () => {
    const before = result({ checklist: list([doc('passport', 'Passport')]) });
    expect(plan(before).status).toBe('preparing');
    const after = { ...before, document_progress: { passport: true } };
    const snapshot = JSON.stringify(after);
    const derived = plan(after);
    expect(derived.status).toBe('review_submission'); expect(derived.nextItem).toBeNull(); expect(derived.prepared).toBe(1);
    expect(after.eligibility).toBe('NEEDS_OFFICIAL_CLARIFICATION'); expect(JSON.stringify(after)).toBe(snapshot);
  });

  it('does not clear source questions or unknown prerequisites by checking every item', () => {
    const unresolved = [{ topic: 'documents', question: 'Which copy?', why_it_matters: '', university: null, program: null, suggested_contact: null, blocking: false }];
    expect(plan(result({ checklist: list([doc('passport', 'Passport')], { unresolved }), document_progress: { passport: true } })).status).toBe('needs_review');
    expect(plan(result({ checklist: list([doc('award', 'Award', { depends_on: ['admission offer letter'] })]), document_progress: { award: true } })).status).toBe('needs_review');
  });
});

describe('confirmed admission date', () => {
  const dated = (claims: ClaimOut[], extra: Partial<ProgramResult> = {}) => result({ admission_deadline: '2027-03-01', claims, ...extra });

  it('uses a current official programme/intake claim and preserves its source', () => {
    const derived = plan(dated([claim()]));
    expect(derived.confirmedAdmissionDeadline).toBe('2027-03-01');
    expect(derived.deadlineSourceUrl).toBe('https://university.example/deadlines');
    expect(plan(dated([claim({ scope: { degree: 'bachelor', intake: 'fall 2027' } })])).confirmedAdmissionDeadline).toBe('2027-03-01');
  });

  it.each([
    { status: 'POSSIBLY_STALE' }, { status: 'SUPERSEDED' }, { status: 'CONFLICTING' },
    { status: 'UNVERIFIED' }, { is_stale: true }, { official_domain: false },
    { source_url: 'javascript:alert(1)' }, { source_url: 'fixture://deadlines' },
    { claim_type: 'required_document' }, { program: 'Physics' }, { intake: 'fall 2026' },
    { scope: null }, { scope: {} }, { scope: { ...scope, degree: 'master' } },
    { scope: { ...scope, intake: 'fall 2026' } }, { scope: { ...scope, population: 'international' } },
    { scope: { ...scope, residency: 'EU' } }, { scope: { ...scope, qualification: 'IB' } },
    { scope: { ...scope, academic_year: '2026/27' } }, { scope: { ...scope, programme: 'Physics' } },
    { normalized_value: { date: '2027-03-01' } }, { normalized_value: '2027-02-29' },
  ] as const)('rejects unsafe or mismatched date evidence: %j', (extra) => {
    expect(plan(dated([claim(extra)])).confirmedAdmissionDeadline).toBeNull();
  });

  it('does not promote a university-wide unspecific claim or the earliest unknown population', () => {
    const wide = claim({ scope: { degree: 'bachelor', intake: 'fall 2027' }, source_specificity: 'university_admissions' });
    expect(plan(dated([wide])).confirmedAdmissionDeadline).toBeNull();
    expect(plan(dated([claim({ scope: { ...scope, population: 'non-EU/EEA' } }), claim({ normalized_value: '2027-05-01', scope: { ...scope, population: 'EU/EEA' } })])).confirmedAdmissionDeadline).toBeNull();
  });

  it('keeps ambiguous dates, previous-cycle-only evidence and stored unresolved conflicts out', () => {
    expect(plan(dated([claim(), claim({ id: 'later', normalized_value: '2027-05-01' })])).confirmedAdmissionDeadline).toBeNull();
    expect(plan(result({ previous_cycle_deadline: '2026-03-01', claims: [claim({ normalized_value: '2026-03-01' })] })).confirmedAdmissionDeadline).toBeNull();
    const conflict = { claim_type: 'admission_deadline', subject: 'deadline', claim_ids: ['deadline'], values: [], source_urls: [], preferred_claim_id: null, resolution_rule: '', question_for_admissions: '', unresolved: true };
    expect(plan(dated([claim()], { conflicts: [conflict] })).confirmedAdmissionDeadline).toBeNull();
  });

  it('validates the supplied date-only clock and never turns a past date into an upcoming one', () => {
    expect(deriveApplicationPlan([dated([claim()])], '2027-02-29')[0]?.confirmedAdmissionDeadline).toBeNull();
    expect(deriveApplicationPlan([dated([claim()])], '2027-03-02')[0]?.confirmedAdmissionDeadline).toBeNull();
    expect(deriveApplicationPlan([dated([claim()])], '2027-03-01')[0]?.confirmedAdmissionDeadline).toBe('2027-03-01');
  });
});

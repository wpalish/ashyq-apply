import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ComparePanel } from './ComparePanel';
import type { ClaimOut, DocumentChecklist, DocumentItem, ProgramResult, UnresolvedQuestion } from '@/types';

function doc(overrides: Partial<DocumentItem> = {}): DocumentItem {
  return {
    name: 'Transcript', purpose: 'admission', owner: 'school', required: true,
    format_notes: '', max_pages: null, max_file_size_mb: null, naming_convention: null,
    needs_translation: false, needs_notarization: false, needs_apostille: false,
    needs_credential_evaluation: false, word_limit: null, character_limit: null,
    prompt_text: null, deadline: null, deadline_timezone: null, depends_on: [],
    lead_time_days: null, source_url: 'https://alpha.example/admission/documents', claim_ids: [],
    ...overrides,
  };
}

function checklist(id: string, overrides: Partial<DocumentChecklist> = {}): DocumentChecklist {
  return {
    result_id: id, university: 'Alpha University', program: 'Computer Science',
    admission_documents: [], scholarship_documents: [], applicant_actions: [], school_actions: [],
    recommender_actions: [], certification_actions: [], ordered_steps: [], unresolved: [],
    generated_at: null, completeness: 'partial', ...overrides,
  };
}

function result(id: string, overrides: Partial<ProgramResult> = {}): ProgramResult {
  return {
    id, run_id: 'run-1', university_id: id, university: `${id} University`, country: 'Example',
    city: 'Example City', program: 'Computer Science', program_url: `https://${id}.example/program`,
    degree: 'bachelor', intake: 'September 2027', rankings: [], eligibility: 'PENDING',
    admissions_fit: 'INSUFFICIENT_DATA', funding_fit: 'UNKNOWN', best_funding_classification: 'UNKNOWN',
    requirement_checks: [], missing_prerequisites: [], hard_filter_failures: [], scholarships: [],
    costs: { items: {}, total: null, academic_year: null, source_urls: [], is_range: false },
    funding_gap: null, preference_score: null, ranking: null, catalog_attributes: {},
    catalog_attributes_source: '', admission_deadline: null, admission_deadline_timezone: null,
    admission_deadline_raw: null, deadline_passed: false, climate_fit: '', city_fit: '', workload_fit: '',
    size_fit: '', campus_fit: '', career_notes: '', post_study_work: '', work_during_study: '',
    conflicts: [], unresolved: [], claims: [], source_urls: [], last_verified: null,
    verification_completeness: 0, user_decision: 'undecided', user_decision_reason: '', user_notes: '',
    decided_at: null, checklist: null, ...overrides,
  };
}

function question(): UnresolvedQuestion {
  return {
    topic: 'document scope', question: 'Does this list cover international applicants?',
    why_it_matters: 'Applicant coverage is not confirmed.', university: null, program: null,
    suggested_contact: null, blocking: true,
  };
}

function claim(id: string): ClaimOut {
  return {
    id, claim_type: 'document_requirement', normalized_value: 'Transcript',
    original_text_excerpt: 'Saved evidence for this programme.', source_url: `https://${id}.example/evidence`,
    page_title: 'Document requirements', relevant_section: 'Documents', official_domain: true,
    program: 'Computer Science', subject_key: null, intake: null, academic_year: null,
    accessed_at: '2026-10-01T00:00:00Z', source_specificity: 'program', confidence: 0.9,
    status: 'VERIFIED_CURRENT', extraction_method: 'fixture', notes: '', is_stale: false, age_days: 0,
  };
}

function column(university: string) {
  const article = screen.getByRole('heading', { name: university, level: 3 }).closest('article');
  if (!article) throw new Error('Compare column missing');
  return within(article);
}

function show(results: ProgramResult[]) {
  return render(<ComparePanel results={results} onRemove={vi.fn()} onClear={vi.fn()} />);
}

describe('Independent Compare peer controls', () => {
  it('routes by exact ID when both compared programmes have the same university and programme label', () => {
    const a = result('alpha', { university: 'Same University', program: 'Computer Science', intake: 'September 2027', claims: [claim('alpha')] });
    const b = result('beta', { university: 'Same University', program: 'Computer Science', intake: 'February 2028', claims: [claim('beta')] });
    show([a, b]);
    const columns = screen.getAllByRole('heading', { name: 'Same University', level: 3 }).map(heading => within(heading.closest('article')!));
    expect(columns[0]!.getByText('September 2027')).toBeInTheDocument();
    expect(columns[1]!.getByText('February 2028')).toBeInTheDocument();
    fireEvent.click(columns[1]!.getByRole('button', { name: 'View details' }));
    const detail = within(screen.getByTestId('detail-beta'));
    expect(screen.queryByTestId('detail-alpha')).not.toBeInTheDocument();
    fireEvent.click(detail.getByRole('tab', { name: 'Sources & evidence' }));
    expect(detail.getByRole('link', { name: /beta.example\/evidence/ })).toHaveAttribute('href', 'https://beta.example/evidence');
    expect(detail.queryByRole('link', { name: /alpha.example\/evidence/ })).not.toBeInTheDocument();
  });

  it('keeps a both-purpose record in its two named lists without summing repeated owner projections or claiming readiness', () => {
    const shared = doc({ name: 'Shared transcript', purpose: 'both', owner: 'school' });
    const a = result('alpha', { checklist: checklist('alpha', { completeness: 'official', admission_documents: [shared], scholarship_documents: [shared], school_actions: [shared], unresolved: [question()] }) });
    const original = JSON.stringify(a);
    show([a]);
    const c = column('alpha University');
    expect(c.getByText('Admission: 1 · Scholarship: 1')).toBeInTheDocument();
    expect(c.getAllByText('Shared transcript')).toHaveLength(2);
    expect(c.getAllByText('Your school')).toHaveLength(2);
    expect(c.getByText('Read from official pages')).toBeInTheDocument();
    expect(c.getByText('1 checklist question to clarify')).toBeInTheDocument();
    expect(c.getByText(question().question)).toBeInTheDocument();
    expect(screen.queryByText(/2 documents|ready to apply|no documents required/i)).not.toBeInTheDocument();
    expect(JSON.stringify(a)).toBe(original);
  });
});

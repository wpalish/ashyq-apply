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

describe('Compare preparation evidence', () => {
  it('keeps requested intakes attached to each selected programme and distinguishes a missing list', () => {
    show([result('alpha'), result('beta', { intake: 'February 2028' })]);
    expect(column('alpha University').getByText('September 2027')).toBeInTheDocument();
    expect(column('beta University').getByText('February 2028')).toBeInTheDocument();
    expect(column('alpha University').getByText('Not collected')).toBeInTheDocument();
    expect(screen.queryByText(/ready to apply|admission ready|fully prepared/i)).not.toBeInTheDocument();
  });

  it('distinguishes successful source reading, partial reading and an unavailable collection attempt', () => {
    show([
      result('alpha', { checklist: checklist('alpha', { completeness: 'official' }) }),
      result('beta', { checklist: checklist('beta', { completeness: 'partial' }) }),
      result('gamma', { checklist: checklist('gamma', { completeness: 'unavailable' }) }),
    ]);
    expect(column('alpha University').getByText('Read from official pages')).toBeInTheDocument();
    expect(column('beta University').getByText('Partially read from sources')).toBeInTheDocument();
    expect(column('gamma University').getByText('Collection attempted — unavailable')).toBeInTheDocument();
    expect(column('alpha University').getByText('No required items recorded')).toBeInTheDocument();
    expect(screen.getAllByText(/Reading sources does not confirm/)).toHaveLength(3);
    expect(screen.getAllByText(/requested intake does not confirm which intake/)).toHaveLength(3);
  });

  it('counts only saved required items in the two lists, without counting owner views again', () => {
    const transcript = doc();
    const reference = doc({ name: 'Reference', purpose: 'scholarship', owner: 'recommender' });
    show([result('alpha', { checklist: checklist('alpha', {
      admission_documents: [transcript, doc({ name: 'Optional CV', required: false })],
      scholarship_documents: [reference], school_actions: [transcript], recommender_actions: [reference],
    }) })]);
    const c = column('alpha University');
    expect(c.getByText('Admission: 1 · Scholarship: 1')).toBeInTheDocument();
    expect(c.getByText('Transcript')).toBeInTheDocument();
    expect(c.getByText('Your school')).toBeInTheDocument();
    expect(c.getByText('Your referee')).toBeInTheDocument();
    expect(c.queryByText('Optional CV')).not.toBeInTheDocument();
  });

  it('uses the stored document source and marks a missing source instead of borrowing a programme URL', () => {
    show([result('alpha', { checklist: checklist('alpha', {
      admission_documents: [doc(), doc({ name: 'Essay', owner: 'applicant', source_url: null })],
    }) })]);
    const c = column('alpha University');
    expect(c.getByRole('link', { name: /alpha.example\/admission\/documents/ })).toHaveAttribute('href', 'https://alpha.example/admission/documents');
    expect(c.getByText('Source not recorded')).toBeInTheDocument();
    expect(c.getByText('You')).toBeInTheDocument();
  });

  it('keeps unsafe sources non-clickable and does not invent an owner when a stored role is missing', () => {
    const missingOwner = { ...doc({ name: 'External report', source_url: 'javascript:alert(1)' }), owner: undefined } as unknown as DocumentItem;
    show([result('alpha', { checklist: checklist('alpha', { admission_documents: [missingOwner] }) })]);
    const c = column('alpha University');
    expect(c.getByText('Owner not recorded')).toBeInTheDocument();
    expect(c.queryByText('You')).not.toBeInTheDocument();
    expect(c.getAllByRole('link').every(link => !link.getAttribute('href')?.startsWith('javascript:'))).toBe(true);
  });

  it('shows saved checklist unknowns and treats blank intake as unknown', () => {
    show([result('alpha', { intake: ' ', checklist: checklist('alpha', { unresolved: [question()] }) })]);
    const c = column('alpha University');
    expect(c.getByText('Not recorded')).toBeInTheDocument();
    expect(c.getByText('1 checklist question to clarify')).toBeInTheDocument();
    expect(c.getByText('1 checklist question to clarify').closest('details')).toBeNull();
    expect(c.getByText(question().question)).toBeInTheDocument();
    expect(c.getByText(question().why_it_matters)).toBeInTheDocument();
  });

  it('does not show another result’s checklist in Compare or the existing Documents detail', () => {
    show([result('alpha', { checklist: checklist('beta', {
      admission_documents: [doc({ name: 'Foreign document' })],
      ordered_steps: ['Foreign document'], unresolved: [question()],
    }) })]);
    const c = column('alpha University');
    expect(c.getByText('Checklist link needs clarification')).toBeInTheDocument();
    expect(c.queryByText('Foreign document')).not.toBeInTheDocument();
    expect(c.queryByText(question().question)).not.toBeInTheDocument();
    fireEvent.click(c.getByRole('button', { name: 'View details' }));
    fireEvent.click(within(screen.getByTestId('detail-alpha')).getByRole('tab', { name: 'Documents' }));
    expect(screen.queryByText('Foreign document')).not.toBeInTheDocument();
  });

  it('opens the chosen result and its saved evidence, switches results and closes a removed result', () => {
    const alpha = result('alpha', { claims: [claim('alpha')] });
    const beta = result('beta', { claims: [claim('beta')] });
    const remove = vi.fn();
    const clear = vi.fn();
    const view = render(<ComparePanel results={[alpha, beta]} onRemove={remove} onClear={clear} />);
    fireEvent.click(column('beta University').getByRole('button', { name: 'View details' }));
    const details = screen.getByTestId('detail-beta');
    expect(screen.queryByTestId('detail-alpha')).not.toBeInTheDocument();
    fireEvent.click(within(details).getByRole('tab', { name: 'Sources & evidence' }));
    expect(within(details).getByRole('link', { name: /beta.example\/evidence/ })).toHaveAttribute('href', 'https://beta.example/evidence');
    expect(within(details).queryByRole('link', { name: /alpha.example\/evidence/ })).not.toBeInTheDocument();
    fireEvent.click(column('alpha University').getByRole('button', { name: 'View details' }));
    expect(screen.getByTestId('detail-alpha')).toBeInTheDocument();
    expect(screen.queryByTestId('detail-beta')).not.toBeInTheDocument();
    fireEvent.click(column('alpha University').getByRole('button', { name: 'Remove' }));
    expect(remove).toHaveBeenCalledWith('alpha');
    view.rerender(<ComparePanel results={[beta]} onRemove={remove} onClear={clear} />);
    expect(screen.queryByTestId('detail-alpha')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Clear' }));
    expect(clear).toHaveBeenCalledOnce();
  });

  it('can toggle details closed without persisting any preparation state', () => {
    const write = vi.spyOn(Storage.prototype, 'setItem');
    show([result('alpha')]);
    const button = column('alpha University').getByRole('button', { name: 'View details' });
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByTestId('detail-alpha')).not.toBeInTheDocument();
    expect(write).not.toHaveBeenCalled();
    write.mockRestore();
  });
});

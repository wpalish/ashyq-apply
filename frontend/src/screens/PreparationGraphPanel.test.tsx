import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { setLocale } from '@/lib/i18n';
import type {
  ClaimOut, ClaimScope, GraphDocumentAction, GraphDocumentItem, GraphRequirementAtom,
  GraphProgrammeProjection, PreparationGraph, ProgramResult,
} from '@/types';
import { PreparationGraphPanel } from './PreparationGraphPanel';

const candidate = (id: string, decision: 'approved' | 'maybe' | 'rejected' | 'undecided' = 'approved') => ({
  id, user_decision: decision, university: `LOCAL ${id}`, program: `Local programme ${id}`, intake: 'Fall 2027',
} as ProgramResult);
const projection = (id: string, locked = false): GraphProgrammeProjection => ({
  result_id: id, run_id: locked ? null : `run-${id}`, user_decision: id === 'b' ? 'maybe' : 'approved',
  university: locked ? null : `SERVER ${id}`, programme: locked ? null : `Server programme ${id}`,
  requested_scope: null, research_access: !locked,
  evidence_state: locked ? 'locked' : 'unknown', projection_state: locked ? 'locked' : 'partial',
  requirement_ids: [], document_action_ids: [], unprojected_checks: [], unresolved_questions: [],
  unresolved_reasons: locked ? ['research_locked'] : ['checks_missing'],
  notice: locked ? 'Research evidence is locked. This view retains only the selected result ID and decision.' : '',
});
function graph(ids: string[], options: { locked?: string; profileId?: string; label?: string } = {}): PreparationGraph {
  return {
    schema_version: 'preparation-graph-v1', profile_id: options.profileId ?? 'case-a',
    requested_result_ids: ids, selected_result_ids: ids, selection_source: 'server_verified_owned_explicit',
    programmes: ids.map(id => ({ ...projection(id, options.locked === id),
      university: options.label && options.locked !== id ? `${options.label} ${id}` : projection(id, options.locked === id).university })),
    requirements: [], policy_groups: [], exam_workstreams: [], document_actions: [],
    source_manifest: ids.map(id => ({ result_id: id, run_id: options.locked === id ? null : `run-${id}`,
      result_snapshot_digest: null, authoritative_evidence_digest: null, resolved_claim_ids: [] })),
    source_fingerprint: '0'.repeat(64), evidence_state: 'unknown', projection_state: 'partial', notice: '',
  };
}
function deferred<T>() {
  let resolve!: (value: T) => void; let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const props = (programmes = [candidate('a'), candidate('b', 'maybe')]) => ({
  profileId: 'case-a', programmes, isCurrent: () => true,
});
const pick = (id: string) => fireEvent.click(screen.getByLabelText(new RegExp(`LOCAL ${id} —`)));
const view = () => fireEvent.click(screen.getByRole('button', { name: 'View combined evidence' }));

beforeEach(() => {
  setLocale('en');
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in synthetic G1 control'); }));
  vi.spyOn(api, 'preparationGraph').mockImplementation(async (_profileId, ids) => graph([...ids]));
  vi.spyOn(api, 'saveStudySchedule');
  vi.spyOn(api, 'saveLearningSchedule');
});
afterEach(() => {
  expect(fetch).not.toHaveBeenCalled();
  expect(api.saveStudySchedule).not.toHaveBeenCalled();
  expect(api.saveLearningSchedule).not.toHaveBeenCalled();
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals();
});

describe('read-only explicit G1 graph', () => {
  it('sends exactly the applicant-selected order and never reads before the explicit button', async () => {
    render(<PreparationGraphPanel {...props()} />);
    expect(api.preparationGraph).not.toHaveBeenCalled();
    pick('b'); pick('a');
    expect(api.preparationGraph).not.toHaveBeenCalled();
    view();
    await waitFor(() => expect(api.preparationGraph).toHaveBeenCalledWith('case-a', ['b', 'a']));
    expect(await screen.findByText('SERVER b — Server programme b')).toBeVisible();
    const cards = screen.getAllByRole('region', { name: /Programme evidence/ });
    expect(cards.map(card => card.getAttribute('aria-label'))).toEqual(['Programme evidence b', 'Programme evidence a']);
    expect(screen.getByText(/has not created or saved a shared study plan/)).toBeVisible();
  });

  it('rejects the first A and B completions after selection cycles A→B→A', async () => {
    const first = deferred<PreparationGraph>(), middle = deferred<PreparationGraph>(), last = deferred<PreparationGraph>();
    vi.mocked(api.preparationGraph).mockReturnValueOnce(first.promise).mockReturnValueOnce(middle.promise).mockReturnValueOnce(last.promise);
    render(<PreparationGraphPanel {...props([candidate('a'), candidate('b', 'maybe'), candidate('c')])} />);
    pick('a'); pick('b'); view();
    pick('b'); pick('c'); view();
    pick('c'); pick('b'); view();
    await act(async () => { first.resolve(graph(['a', 'b'], { label: 'OLD' })); middle.reject(new Error('old failure')); });
    expect(screen.queryByText('OLD a — Server programme a')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await act(async () => last.resolve(graph(['a', 'b'], { label: 'LATEST' })));
    expect(screen.getByText('LATEST a — Server programme a')).toBeVisible();
    expect(api.preparationGraph).toHaveBeenCalledTimes(3);
  });

  it('hides a prior selection immediately and prunes a result that is no longer eligible', async () => {
    const pending = deferred<PreparationGraph>();
    vi.mocked(api.preparationGraph).mockReturnValueOnce(pending.promise);
    const rendered = render(<PreparationGraphPanel {...props()} />);
    pick('a'); pick('b'); view();
    rendered.rerender(<PreparationGraphPanel {...props([candidate('a'), candidate('b', 'rejected')])} />);
    await act(async () => pending.resolve(graph(['a', 'b'])));
    expect(screen.queryByTestId('preparation-graph')).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/LOCAL b —/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View combined evidence' })).toBeDisabled();
  });

  it('does not accept an old owner or case response', async () => {
    const pending = deferred<PreparationGraph>();
    vi.mocked(api.preparationGraph).mockReturnValueOnce(pending.promise);
    let ownerCurrent = true;
    const rendered = render(<PreparationGraphPanel profileId="case-a" programmes={props().programmes} isCurrent={() => ownerCurrent} />);
    pick('a'); pick('b'); view();
    ownerCurrent = false;
    await act(async () => pending.resolve(graph(['a', 'b'])));
    expect(screen.queryByTestId('preparation-graph')).not.toBeInTheDocument();
    ownerCurrent = true;
    rendered.rerender(<PreparationGraphPanel profileId="case-b" programmes={props().programmes} isCurrent={() => ownerCurrent} />);
    expect(screen.queryByTestId('preparation-graph')).not.toBeInTheDocument();
  });

  it.each([
    ['profile', (item: PreparationGraph) => ({ ...item, profile_id: 'foreign-case' })],
    ['schema', (item: PreparationGraph) => ({ ...item, schema_version: 'future' as PreparationGraph['schema_version'] })],
    ['source', (item: PreparationGraph) => ({ ...item, selection_source: 'client' as PreparationGraph['selection_source'] })],
    ['requested echo', (item: PreparationGraph) => ({ ...item, requested_result_ids: ['b', 'a'] })],
    ['selected echo', (item: PreparationGraph) => ({ ...item, selected_result_ids: ['b', 'a'] })],
    ['programme order', (item: PreparationGraph) => ({ ...item, programmes: [...item.programmes].reverse() })],
    ['manifest order', (item: PreparationGraph) => ({ ...item, source_manifest: [...item.source_manifest].reverse() })],
  ])('rejects a mismatched %s before rendering any evidence', async (_kind, corrupt) => {
    vi.mocked(api.preparationGraph).mockResolvedValue(corrupt(graph(['a', 'b'])));
    render(<PreparationGraphPanel {...props()} />); pick('a'); pick('b'); view();
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded');
    expect(screen.queryByTestId('preparation-graph')).not.toBeInTheDocument();
  });

  it('shows only the server-permitted receipt for a locked selection', async () => {
    vi.mocked(api.preparationGraph).mockResolvedValue(graph(['a', 'b'], { locked: 'b' }));
    render(<PreparationGraphPanel {...props()} />); pick('a'); pick('b'); view();
    const lockedCard = await screen.findByRole('region', { name: 'Programme evidence b' });
    expect(lockedCard).toHaveTextContent('b');
    expect(lockedCard).toHaveTextContent('Research evidence is locked');
    expect(lockedCard).not.toHaveTextContent('LOCAL b');
    expect(lockedCard).not.toHaveTextContent('SERVER b');
    expect(lockedCard.querySelector('a')).toBeNull();
  });

  it('keeps original values, exact scope, unresolved policy and document work distinct', async () => {
    const scope = { university: null, faculty: null, programme: 'Programme A', degree: null,
      intake: 'Fall 2027', academic_year: null, population: null, nationality: null,
      residency: null, qualification: null } satisfies ClaimScope;
    const proof = { claim: { id: 'claim-1', original_text_excerpt: 'Published IELTS overall 7.5 for a different intake.',
      page_title: 'Admissions', relevant_section: 'Language', accessed_at: '2026-10-11T00:00:00Z',
      status: 'VERIFIED_CURRENT', is_stale: true, age_days: 400,
      source_url: 'https://example.test/source', scope: null } as ClaimOut,
      scope: { requested: scope, published: null, verdict: 'unknown' as const,
        gaps: ['programme', 'intake'], contradictions: [] } };
    const atom = { id: 'atom-a', result_id: 'a', source_check_index: 0, purpose: 'admission',
      scholarship_id: null, scholarship_subject: null,
      original_check: { requirement: 'IELTS overall', published_value: 7.5, applicant_value: null,
        status: 'PENDING', is_hard_filter: false, explanation: 'Saved check remains pending.',
        claim_ids: ['legacy-url'], published_scope: 'Different intake' },
      evidence_state: 'unknown', policy: 'unknown', family: 'ielts', metric: 'overall',
      original_reference_ids: ['legacy-url'], resolved_claim_ids: ['claim-1'], proofs: [proof],
      source_urls: ['https://example.test/source'], lesson_id_hints: [],
      unresolved_reasons: ['scope_unknown', 'alternatives_unresolved'] } as GraphRequirementAtom;
    const original: GraphDocumentItem = { name: 'Transcript', owner: 'school', purpose: 'admission',
      required: true, format_notes: 'Synthetic certified PDF', max_pages: 5, max_file_size_mb: 2,
      naming_convention: null, needs_translation: true, needs_notarization: false,
      needs_apostille: false, needs_credential_evaluation: false, word_limit: null,
      character_limit: null, prompt_text: 'List your completed subjects.',
      deadline: '2027-01-15', deadline_timezone: 'Asia/Almaty', depends_on: ['School seal'],
      lead_time_days: 14, source_url: 'https://example.test/transcript', claim_ids: [], scope: null };
    const document: GraphDocumentAction = { id: 'document-a', result_id: 'a', original_item: original,
      original_items: [original],
      source_locations: ['school_actions'], scope: proof.scope, proofs: [],
      evidence_state: 'conflicted', fulfillment_state: 'untracked', action_state: 'requires_review',
      dependencies: [{ original_name: 'School seal', target_document_id: null,
        resolution: 'missing', fulfillment_state: 'untracked' }],
      unresolved_reasons: ['dependency_missing'] };
    const result = graph(['a', 'b']);
    result.programmes[0] = { ...result.programmes[0]!, requested_scope: scope,
      requirement_ids: ['atom-a'], document_action_ids: ['document-a'] };
    result.requirements = [atom]; result.document_actions = [document];
    result.policy_groups = [{ id: 'group-a', result_id: 'a', purpose: 'admission', scholarship_id: null,
      kind: 'alternatives_unresolved', requirement_ids: ['atom-a'], context_proofs: [],
      unresolved_reasons: ['alternatives_unresolved'] }];
    result.exam_workstreams = [{ id: 'ielts-family', family: 'ielts', grouping: 'family_only',
      identity_state: 'unknown', edition: null, requirement_ids: ['atom-a'],
      contributing_result_ids: ['a'], missing_identity_dimensions: ['edition', 'accepted_variant', 'retake_policy', 'route'] }];
    result.source_manifest[0]!.resolved_claim_ids = ['claim-1'];
    vi.mocked(api.preparationGraph).mockResolvedValue(result);
    render(<PreparationGraphPanel {...props()} />); pick('a'); pick('b'); view();
    expect(await screen.findByText('IELTS overall')).toBeVisible();
    expect(screen.getByText('Published value: 7.5')).toBeVisible();
    expect(screen.getByText('Saved check status: Pending in saved check · Evidence: Unknown evidence')).toBeVisible();
    expect(screen.getAllByText(/Alternatives are mentioned; their relationship is unresolved/)).toHaveLength(2);
    expect(screen.getByText('Requires review; fulfillment is untracked.')).toBeVisible();
    const programme = screen.getByRole('region', { name: 'Programme evidence a' });
    expect(within(programme).getByText(/^Applicant request scope:/)).toHaveTextContent('Programme A');
    const documentCard = screen.getByRole('region', { name: 'Transcript' });
    expect(within(documentCard).getByText('Evidence: Conflicting evidence')).toBeVisible();
    fireEvent.click(within(documentCard).getByText('Recorded document details'));
    expect(within(documentCard).getByText('Programme prompt: List your completed subjects.')).toBeVisible();
    expect(within(documentCard).getByText('Format notes: Synthetic certified PDF')).toBeVisible();
    expect(screen.getByText(/Family observation only/)).toBeVisible();
    const source = screen.getAllByText('Source evidence').find(node => node.tagName === 'SUMMARY');
    if (!source) throw new Error('Source disclosure missing');
    fireEvent.click(source);
    expect(screen.getByText('Published IELTS overall 7.5 for a different intake.')).toBeVisible();
    expect(screen.getByText('Stored verification status: Verified current claim')).toBeVisible();
    expect(screen.getByText('Freshness at this read: Marked stale; review the source · Age in days: 400')).toBeVisible();
    expect(screen.getByText(/Original stored references: legacy-url/)).toBeVisible();
    expect(screen.getByText(/Exact resolved claim IDs: claim-1/)).toBeVisible();
    expect(screen.getAllByText('Applicability is unknown').length).toBeGreaterThan(0);
    expect(screen.queryByText(/shared score target/i)).not.toBeInTheDocument();
  });

  it('keeps identical exam labels for distinct awards separate in policy groups', async () => {
    const result = graph(['a', 'b']);
    const atom = (id: string, award: string): GraphRequirementAtom => ({
      id, result_id: 'a', source_check_index: 0, purpose: 'scholarship',
      scholarship_id: award, scholarship_subject: `Named ${award}`,
      original_check: { requirement: 'IELTS overall', published_value: 7,
        applicant_value: null, status: 'PENDING', is_hard_filter: false,
        explanation: 'Award policy unresolved', claim_ids: [], published_scope: '' },
      evidence_state: 'unknown', policy: 'unknown', family: 'ielts', metric: 'overall',
      original_reference_ids: [], resolved_claim_ids: [], proofs: [], source_urls: [],
      lesson_id_hints: [], unresolved_reasons: ['scholarship_subject_unestablished'],
    });
    result.requirements = [atom('one', 'award-one'), atom('two', 'award-two')];
    result.programmes[0]!.requirement_ids = ['one', 'two'];
    result.policy_groups = result.requirements.map(item => ({ id: `group-${item.id}`,
      result_id: 'a', purpose: 'scholarship', scholarship_id: item.scholarship_id,
      kind: 'unresolved', requirement_ids: [item.id], context_proofs: [], unresolved_reasons: ['policy_unknown'] }));
    vi.mocked(api.preparationGraph).mockResolvedValue(result);
    render(<PreparationGraphPanel {...props()} />); pick('a'); pick('b'); view();
    expect(await screen.findByText('IELTS overall · Scholarship: Named award-one')).toBeVisible();
    expect(screen.getByText('IELTS overall · Scholarship: Named award-two')).toBeVisible();
    expect(screen.getByText('Scholarship: award-one')).toBeVisible();
    expect(screen.getByText('Scholarship: award-two')).toBeVisible();
  });
});

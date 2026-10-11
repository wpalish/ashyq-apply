import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { DraftIdentityContext } from '@/lib/draftIdentity';
import { profile, result } from '@/lib/securityMergeFixtures';
import type { PreparationGraph, PreparationLesson, PreparationPlan, PreparationProgress, StudyAttempt } from '@/types';
import { PreparationScreen } from './PreparationScreen';
import { access, attempt, catalogue, check, deferred, learningCatalogue, learningVersion, lesson, plan, progress } from './preparationFixtures';

const state = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock('@/lib/store', () => ({ useStore: () => state.value }));
const ownerA = 'auth:["synthetic-a","workspace-a"]';
const ownerB = 'auth:["synthetic-b","workspace-b"]';
function bind(owner = ownerA) {
  localStorage.setItem('ashyq.applicantOwner', owner); sessionStorage.setItem('ashyq.applicantOwner', owner);
}
async function flush() { await act(async () => { for (let i = 0; i < 8; ++i) await Promise.resolve(); }); }
async function openLesson(id = 'ielts-reading-1') {
  fireEvent.click(await screen.findByRole('button', { name: 'Practice' }));
  fireEvent.click(screen.getByRole('button', { name: `Start ${catalogue().lessons.find(item => item.id === id)!.title}` }));
  await screen.findByRole('radio', { name: 'Supported' });
}
function chooseAnswer() { fireEvent.click(screen.getByRole('radio', { name: 'Supported' })); }
beforeEach(() => {
  localStorage.clear(); sessionStorage.clear(); bind();
  state.value = { savedProfile: profile('case-a'), caseEpoch: 0, results: [], hydrated: true, loading: false };
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in synthetic preparation control'); }));
  vi.spyOn(api, 'preparationAccess').mockResolvedValue(access());
  vi.spyOn(api, 'preparationCatalogue').mockResolvedValue(learningCatalogue());
  vi.spyOn(api, 'preparationProgress').mockImplementation(async id => progress(id));
  vi.spyOn(api, 'preparationPlan').mockImplementation(async (id, resultId) => plan(id, resultId ?? null));
  vi.spyOn(api, 'preparationLesson').mockImplementation(async (_id, lessonId) => lesson(lessonId));
  vi.spyOn(api, 'submitPreparation').mockImplementation(async (id, input) => attempt(input, id));
  vi.spyOn(api, 'updateProfile'); vi.spyOn(api, 'createProfile'); vi.spyOn(api, 'startRun');
});
afterEach(() => { expect(fetch).not.toHaveBeenCalled(); cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('owned starter preparation', () => {

  it.each(['catalogue', 'progress'] as const)('keeps explicit comparison available after the %s learning read fails', async failedRead => {
    const programmes = [{ ...result('chosen-a', 'run-a'), user_decision: 'approved' as const },
      { ...result('chosen-b', 'run-b'), user_decision: 'maybe' as const }];
    state.value.results = programmes;
    const refusal = new Error('Synthetic learning read unavailable');
    if (failedRead === 'catalogue') vi.mocked(api.preparationCatalogue).mockRejectedValue(refusal);
    else vi.mocked(api.preparationProgress).mockRejectedValue(refusal);
    const comparison = vi.spyOn(api, 'preparationGraph').mockImplementation(async (profileId, ids): Promise<PreparationGraph> => ({
      schema_version: 'preparation-graph-v1', profile_id: profileId,
      requested_result_ids: [...ids], selected_result_ids: [...ids],
      selection_source: 'server_verified_owned_explicit', source_fingerprint: '0'.repeat(64),
      evidence_state: 'unknown', projection_state: 'partial', notice: '',
      requirements: [], document_actions: [], policy_groups: [], exam_workstreams: [],
      programmes: ids.map(id => ({ result_id: id, run_id: `run-${id}`,
        user_decision: id === 'chosen-a' ? 'approved' : 'maybe', university: `Comparison ${id}`,
        programme: 'Synthetic programme', requested_scope: null, research_access: true,
        evidence_state: 'unknown', projection_state: 'partial', requirement_ids: [],
        document_action_ids: [], unprojected_checks: [], unresolved_questions: [],
        unresolved_reasons: ['checks_missing'], notice: '' })),
      source_manifest: ids.map(id => ({ result_id: id, run_id: `run-${id}`,
        result_snapshot_digest: null, authoritative_evidence_digest: null, resolved_claim_ids: [] })),
    }));
    const saveSchedule = vi.spyOn(api, 'saveStudySchedule');
    const saveLearning = vi.spyOn(api, 'saveLearningSchedule');
    render(<PreparationScreen />);
    expect(await screen.findByRole('alert')).toHaveTextContent(refusal.message);
    expect(screen.getByRole('heading', { name: 'Compare programme requirements' })).toBeVisible();
    expect(comparison).not.toHaveBeenCalled();
    const choices = within(screen.getByRole('group', { name: 'Programmes to compare' })).getAllByRole('checkbox');
    fireEvent.click(choices[0]); fireEvent.click(choices[1]);
    expect(comparison).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'View combined evidence' }));
    expect(await screen.findByText('Comparison chosen-a — Synthetic programme')).toBeVisible();
    expect(screen.getByText('Comparison chosen-b — Synthetic programme')).toBeVisible();
    expect(comparison).toHaveBeenCalledWith('case-a', ['chosen-a', 'chosen-b']);
    expect(screen.getByRole('alert')).toHaveTextContent(refusal.message);
    expect(screen.queryByRole('button', { name: 'Practice', exact: true })).not.toBeInTheDocument();
    expect(api.startRun).not.toHaveBeenCalled(); expect(api.submitPreparation).not.toHaveBeenCalled();
    expect(saveSchedule).not.toHaveBeenCalled(); expect(saveLearning).not.toHaveBeenCalled();
  });

  it('keeps source details closed while retaining every excerpt, scope and extra link', async () => {
    const evidence = check();
    evidence.source_urls.push('https://example.test/additional-policy');
    vi.mocked(api.preparationPlan).mockResolvedValue({ ...plan(), research_access: true,
      evidence_state: 'current', checks: [evidence] });
    render(<PreparationScreen />);
    expect(await screen.findByText('Policy: waiver check')).toBeVisible();
    const summary = screen.getByText('Source evidence (2)', { exact: true });
    const details = summary.closest('details');
    if (!details) throw new Error('Source evidence must have a native details disclosure');
    expect(details).not.toHaveAttribute('open');
    const quote = screen.getByText('Synthetic policy excerpt preserving scope.');
    expect(quote).toBeInTheDocument();
    expect(quote).not.toBeVisible();
    expect(screen.getByText(/Published scope:/)).toBeVisible();
    fireEvent.click(summary);
    expect(details).toHaveAttribute('open');
    expect(quote).toBeVisible();
    expect(within(details).getByText(/Recorded source scope:/)).toHaveTextContent('stated population only');
    expect(within(details).getAllByRole('link').map(link => link.getAttribute('href'))).toEqual([
      'https://example.test/policy', 'https://example.test/additional-policy',
    ]);
    fireEvent.click(summary);
    expect(details).not.toHaveAttribute('open');
    expect(quote).toBeInTheDocument();
    expect(screen.getByText('Policy: waiver check')).toBeVisible();
  });

  it('retains loaded evidence when the selected programme is selected again', async () => {
    state.value.results = [{ ...result('chosen-a', 'run-a'), user_decision: 'approved' }];
    vi.mocked(api.preparationPlan).mockResolvedValue({ ...plan('case-a', 'chosen-a'),
      research_access: true, evidence_state: 'current', checks: [check()] });
    render(<PreparationScreen />);
    await screen.findByText('IELTS overall');
    fireEvent.change(screen.getByLabelText('Programme evidence'), { target: { value: 'chosen-a' } });
    await flush();
    expect(screen.getByText('IELTS overall')).toBeInTheDocument();
    expect(screen.queryByText('Loading stored exam evidence…')).not.toBeInTheDocument();
    expect(api.preparationPlan).toHaveBeenCalledTimes(1);
  });

  it('lets the current request finish when the selected programme is selected again', async () => {
    state.value.results = [{ ...result('chosen-a', 'run-a'), user_decision: 'approved' }];
    const pending = deferred<PreparationPlan>();
    vi.mocked(api.preparationPlan).mockReturnValue(pending.promise);
    render(<PreparationScreen />);
    await screen.findByRole('button', { name: 'Practice' });
    fireEvent.change(screen.getByLabelText('Programme evidence'), { target: { value: 'chosen-a' } });
    await act(async () => pending.resolve({ ...plan('case-a', 'chosen-a'),
      research_access: true, evidence_state: 'current', checks: [check()] }));
    await screen.findByText('IELTS overall');
    expect(screen.queryByText('Loading stored exam evidence…')).not.toBeInTheDocument();
    expect(api.preparationPlan).toHaveBeenCalledTimes(1);
  });

  it('shows component thresholds and unstated scope in readable terms instead of raw JSON', async () => {
    const evidence = check();
    evidence.requirement_check.published_value = { overall: 7, sections: { reading: 6.5 } };
    evidence.requirement_check.applicant_value = null;
    vi.mocked(api.preparationPlan).mockResolvedValue({ ...plan(), research_access: true, evidence_state: 'current', checks: [evidence] });
    render(<PreparationScreen />);
    expect(await screen.findByText('Published: Overall: 7; Sections: Reading: 6.5')).toBeInTheDocument();
    expect(screen.getByText('Your entered value: Not entered')).toBeInTheDocument();
    expect(screen.getByText(/Recorded source scope:/)).toHaveTextContent('Citizenship: Not stated');
    expect(screen.queryByText(/"overall"|"nationality"/)).not.toBeInTheDocument();
  });

  it('refreshes saved history on entering Progress and ignores an older same-case refresh', async () => {
    const older = deferred<PreparationProgress>();
    vi.mocked(api.preparationProgress).mockResolvedValueOnce(progress()).mockImplementationOnce(() => older.promise)
      .mockResolvedValueOnce(progress('case-a', [attempt({ attempt_id: 'new-saved-attempt', lesson_id: 'sat-math-1',
        version: catalogue().version, answers: [{ question_id: 'sat-math-1-q1', choice_id: 'a' }] })]));
    render(<PreparationScreen />);
    fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    // A successful later submission triggers a newer history read while this one is still pending.
    fireEvent.click(screen.getByRole('button', { name: 'Practice' }));
    fireEvent.click(screen.getByRole('button', { name: 'Start Synthetic Math' }));
    await screen.findByRole('radio', { name: 'Supported' }); chooseAnswer();
    fireEvent.click(screen.getByRole('button', { name: 'Submit practice' }));
    await screen.findByTestId('practice-result'); await flush();
    await act(async () => older.resolve(progress())); await flush();
    // Prevent a fourth network read from hiding the assertion behind a newer fixture.
    vi.mocked(api.preparationProgress).mockReturnValue(new Promise<PreparationProgress>(() => {}));
    fireEvent.click(screen.getByRole('button', { name: 'Progress' }));
    expect(screen.getByTestId('progress-summary')).toHaveTextContent('1 saved attempts');
  });

  it('does not call preparation for an unsaved case or an unavailable principal', () => {
    state.value.savedProfile = null;
    const view = render(<PreparationScreen />);
    expect(screen.getByText('Save or select an applicant case first')).toBeInTheDocument();
    state.value.savedProfile = profile('case-a');
    view.rerender(<DraftIdentityContext.Provider value={null}><PreparationScreen /></DraftIdentityContext.Provider>);
    expect(screen.getByText('Sign in to your workspace')).toBeInTheDocument();
    expect(api.preparationAccess).not.toHaveBeenCalled(); expect(api.preparationCatalogue).not.toHaveBeenCalled();
    expect(api.preparationProgress).not.toHaveBeenCalled(); expect(api.preparationPlan).not.toHaveBeenCalled();
  });

  it('uses explicit education access while personal goals stay unknown', async () => {
    state.value.full_access = false; state.value.subscription_cases_left = 0;
    render(<PreparationScreen />);
    expect(await screen.findByText('Evidence: unknown')).toBeInTheDocument();
    expect(screen.getByText(/No confirmed exam goal is shown/)).toBeInTheDocument();
    await openLesson();
    expect(screen.getByRole('button', { name: 'Submit practice' })).toBeDisabled();
    expect(screen.getByText(/No official IELTS band or SAT scaled score/)).toBeInTheDocument();
    expect(api.preparationLesson).toHaveBeenCalledWith('case-a', 'ielts-reading-1', catalogue().version);
  });

  it('blocks new practice for an expired term while retaining readable own history', async () => {
    vi.mocked(api.preparationAccess).mockResolvedValue(access(false));
    const saved = attempt({ attempt_id: 'synthetic-old-attempt', lesson_id: 'ielts-reading-1', version: catalogue().version,
      answers: [{ question_id: 'ielts-reading-1-q1', choice_id: 'a' }] });
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [saved]));
    render(<PreparationScreen />);
    fireEvent.click(await screen.findByRole('button', { name: 'Practice' }));
    expect(screen.getByRole('button', { name: 'Start Synthetic Reading' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Progress' }));
    expect(screen.getByTestId('progress-summary')).toHaveTextContent('1 saved attempts');
    expect(screen.getByText(/Completed means submitted, not mastered/)).toBeInTheDocument();
    expect(api.preparationLesson).not.toHaveBeenCalled();
  });

  it('distinguishes locked evidence and never renders checks from a locked response', async () => {
    vi.mocked(api.preparationPlan).mockResolvedValue({ ...plan(), evidence_state: 'locked', checks: [check()] });
    render(<PreparationScreen />);
    expect(await screen.findByText('Exam evidence is locked')).toBeInTheDocument();
    expect(screen.getByText(/A hidden requirement is not an absent requirement/)).toBeInTheDocument();
    expect(screen.queryByText('IELTS overall')).not.toBeInTheDocument();
    expect(screen.queryByText('Synthetic policy excerpt preserving scope.')).not.toBeInTheDocument();
  });

  it('retains waiver, excerpt and recorded scope without promoting them to an unconditional goal', async () => {
    state.value.results = [{ ...result('chosen-a', 'run-a'), user_decision: 'approved' },
      { ...result('maybe-b', 'run-a'), university: 'Maybe University' },
      { ...result('rejected-c', 'run-a'), university: 'Rejected University', user_decision: 'rejected' }];
    vi.mocked(api.preparationPlan).mockImplementation(async (id, resultId) => ({ ...plan(id, resultId ?? null),
      research_access: true, evidence_state: 'current', checks: [check()] }));
    render(<PreparationScreen />);
    expect(await screen.findByText('Policy: waiver check')).toBeInTheDocument();
    expect(screen.getByText('Synthetic policy excerpt preserving scope.')).toBeInTheDocument();
    expect(screen.getByText(/Recorded source scope:/)).toHaveTextContent('stated population only');
    expect(screen.getByText(/Published scope:/)).toHaveTextContent('September 2027');
    expect(screen.getByLabelText('Programme evidence')).toHaveValue('chosen-a');
    expect(screen.queryByRole('option', { name: /Rejected University/ })).not.toBeInTheDocument();
    expect(api.preparationPlan).toHaveBeenCalledWith('case-a', 'chosen-a');
  });

  it('clears previous programme evidence immediately and ignores its late response', async () => {
    state.value.results = [result('result-a', 'run-a'), { ...result('result-b', 'run-a'), university: 'University B' }];
    const first = deferred<PreparationPlan>();
    vi.mocked(api.preparationPlan).mockImplementationOnce(() => first.promise);
    render(<PreparationScreen />);
    await screen.findByRole('button', { name: 'Practice' });
    fireEvent.change(screen.getByLabelText('Programme evidence'), { target: { value: 'result-b' } });
    await flush();
    await act(async () => first.resolve({ ...plan('case-a', 'result-a'), research_access: true,
      evidence_state: 'current', checks: [check()] }));
    await flush();
    expect(screen.getByLabelText('Programme evidence')).toHaveValue('result-b');
    expect(screen.queryByText('IELTS overall')).not.toBeInTheDocument();
    expect(api.preparationPlan).toHaveBeenLastCalledWith('case-a', 'result-b');
  });

  it('shows planned courses as external metadata, with no fabricated local practice', async () => {
    render(<PreparationScreen />);
    fireEvent.click(await screen.findByRole('button', { name: 'Practice' }));
    const toefl = screen.getByRole('heading', { name: 'TOEFL iBT' }).closest('section')!;
    expect(within(toefl).getByText('Course planned — not available here')).toBeInTheDocument();
    expect(within(toefl).getByRole('link')).toHaveAttribute('href', 'https://example.test/toefl_ibt/info');
    expect(within(toefl).queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /^Start Synthetic/ })).toHaveLength(3);
  });

  it('keeps one immutable UUID across double submit and network retry, then resets for a new attempt', async () => {
    const pending = deferred<StudyAttempt>();
    vi.mocked(api.submitPreparation).mockImplementationOnce(() => pending.promise);
    const originalProfile = structuredClone(state.value.savedProfile);
    render(<PreparationScreen />); await openLesson(); chooseAnswer();
    const form = screen.getByRole('button', { name: 'Submit practice' }).closest('form')!;
    fireEvent.submit(form); fireEvent.submit(form);
    expect(api.submitPreparation).toHaveBeenCalledTimes(1);
    const payload = structuredClone(vi.mocked(api.submitPreparation).mock.calls[0]![1]);
    expect(payload.attempt_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(screen.getByRole('radio', { name: 'Supported' })).toBeChecked();
    expect(screen.getByRole('radio', { name: 'Unsupported' })).toBeDisabled();
    await act(async () => pending.reject(new Error('Synthetic network failure')));
    expect(await screen.findByRole('button', { name: 'Retry same submission' })).toBeEnabled();
    expect(screen.queryByText('Practice saved.')).not.toBeInTheDocument();
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [attempt(payload)]));
    fireEvent.click(screen.getByRole('button', { name: 'Retry same submission' }));
    expect(await screen.findByTestId('practice-result')).toHaveAttribute('data-attempt-id', payload.attempt_id);
    expect(api.submitPreparation).toHaveBeenNthCalledWith(2, 'case-a', payload);
    expect(screen.getByLabelText('Practice feedback')).toHaveTextContent('Synthetic explanation');
    fireEvent.click(screen.getByRole('button', { name: 'Start a new attempt' }));
    await screen.findByRole('radio', { name: 'Supported' }); chooseAnswer();
    fireEvent.click(screen.getByRole('button', { name: 'Submit practice' }));
    await waitFor(() => expect(api.submitPreparation).toHaveBeenCalledTimes(3));
    expect(vi.mocked(api.submitPreparation).mock.calls[2]![1].attempt_id).not.toBe(payload.attempt_id);
    await waitFor(() => expect(screen.getByTestId('practice-result')).not.toHaveAttribute('data-attempt-id', payload.attempt_id));
    expect(state.value.savedProfile).toEqual(originalProfile);
    expect(api.updateProfile).not.toHaveBeenCalled(); expect(api.createProfile).not.toHaveBeenCalled(); expect(api.startRun).not.toHaveBeenCalled();
  });

  it('hides A questions during switch-start and ignores late A lesson before B commits', async () => {
    const pending = deferred<PreparationLesson>();
    vi.mocked(api.preparationLesson).mockImplementationOnce(() => pending.promise);
    const view = render(<PreparationScreen />);
    fireEvent.click(await screen.findByRole('button', { name: 'Practice' }));
    fireEvent.click(screen.getByRole('button', { name: 'Start Synthetic Reading' }));
    state.value = { ...state.value, loading: true, caseEpoch: 1 }; view.rerender(<PreparationScreen />);
    expect(screen.queryByLabelText('Preparation views')).not.toBeInTheDocument();
    await act(async () => pending.resolve(lesson('ielts-reading-1', 'A-only')));
    state.value = { ...state.value, savedProfile: profile('case-b'), loading: false }; view.rerender(<PreparationScreen />);
    await screen.findByRole('button', { name: 'Progress' });
    expect(screen.queryByText(/A-only/)).not.toBeInTheDocument();
    expect(api.preparationProgress).toHaveBeenLastCalledWith('case-b', learningVersion);
  });

  it('does not show late A feedback or refresh its progress after B replaces the case', async () => {
    const pending = deferred<StudyAttempt>();
    vi.mocked(api.submitPreparation).mockImplementationOnce(() => pending.promise);
    const view = render(<PreparationScreen />); await openLesson(); chooseAnswer();
    fireEvent.click(screen.getByRole('button', { name: 'Submit practice' }));
    const payload = vi.mocked(api.submitPreparation).mock.calls[0]![1];
    state.value = { ...state.value, savedProfile: profile('case-b'), caseEpoch: 1 }; view.rerender(<PreparationScreen />);
    await flush(); const calls = vi.mocked(api.preparationProgress).mock.calls.length;
    await act(async () => pending.resolve(attempt(payload, 'case-a'))); await flush();
    expect(screen.queryByLabelText('Practice feedback')).not.toBeInTheDocument();
    expect(api.preparationProgress).toHaveBeenCalledTimes(calls);
    fireEvent.click(screen.getByRole('button', { name: 'Progress' }));
    expect(screen.getByTestId('progress-summary')).toHaveTextContent('0 saved attempts');
  });

  it('fences a submit response when the shared owner changes before React remounts', async () => {
    const pending = deferred<StudyAttempt>();
    vi.mocked(api.submitPreparation).mockImplementationOnce(() => pending.promise);
    render(<PreparationScreen />); await openLesson(); chooseAnswer();
    fireEvent.click(screen.getByRole('button', { name: 'Submit practice' }));
    const payload = vi.mocked(api.submitPreparation).mock.calls[0]![1];
    const calls = vi.mocked(api.preparationProgress).mock.calls.length;
    localStorage.setItem('ashyq.applicantOwner', ownerB); // Storage event/React update deliberately has not arrived.
    await act(async () => pending.resolve(attempt(payload))); await flush();
    expect(screen.queryByLabelText('Practice feedback')).not.toBeInTheDocument();
    expect(screen.queryByText('Practice saved.')).not.toBeInTheDocument();
    expect(api.preparationProgress).toHaveBeenCalledTimes(calls);
  });

  it('ignores a failed old-owner access read without showing its error in stale memory', async () => {
    const pending = deferred<ReturnType<typeof access>>();
    vi.mocked(api.preparationAccess).mockImplementationOnce(() => pending.promise);
    render(<PreparationScreen />);
    localStorage.setItem('ashyq.applicantOwner', ownerB);
    await act(async () => pending.reject(new Error('Old owner access failure'))); await flush();
    expect(screen.queryByText(/Old owner access failure/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Preparation views')).not.toBeInTheDocument();
  });

  it('ignores a lesson that resolves after a newer lesson intent', async () => {
    const pending = deferred<PreparationLesson>();
    vi.mocked(api.preparationLesson).mockImplementationOnce(() => pending.promise);
    render(<PreparationScreen />);
    fireEvent.click(await screen.findByRole('button', { name: 'Practice' }));
    fireEvent.click(screen.getByRole('button', { name: 'Start Synthetic Reading' }));
    fireEvent.click(screen.getByRole('button', { name: 'Progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'Practice' }));
    fireEvent.click(screen.getByRole('button', { name: 'Start Synthetic Math' }));
    await screen.findByRole('radio', { name: 'Supported' });
    await act(async () => pending.resolve(lesson('ielts-reading-1', 'old intent'))); await flush();
    expect(screen.queryByText(/old intent/)).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Synthetic Math' })).toBeInTheDocument();
  });

  it('rejects mixed-case progress rather than rendering another case attempt', async () => {
    const other = attempt({ attempt_id: 'foreign-attempt', lesson_id: 'ielts-reading-1', version: catalogue().version,
      answers: [{ question_id: 'ielts-reading-1-q1', choice_id: 'a' }] }, 'case-b');
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [other]));
    render(<PreparationScreen />);
    expect(await screen.findByRole('alert')).toHaveTextContent('The practice history did not match this case.');
    expect(screen.queryByTestId('progress-summary')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Preparation views')).not.toBeInTheDocument();
  });
});

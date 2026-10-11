import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { profile } from '@/lib/securityMergeFixtures';
import type { PreparationAttemptInput, PreparationCatalogue, PreparationLesson, StudyAttempt, StudyScheduleOut } from '@/types';
import { PreparationScreen } from './PreparationScreen';
import { access, attempt, deferred, learningCatalogue, learningVersion, lesson, plan, progress, version } from './preparationFixtures';

const state = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock('@/lib/store', () => ({ useStore: () => state.value }));
const ownerA = 'auth:["synthetic-a","workspace-a"]';
const ownerB = 'auth:["synthetic-b","workspace-b"]';
const headings = 'ielts-reading-headings-1';
const completion = 'ielts-reading-completion-1';
const features = 'ielts-reading-features-1';
function pack(): PreparationCatalogue {
  const base = learningCatalogue();
  const extra = [
    { id: headings, track_id: 'ielts_reading', title: 'Synthetic headings', question_count: 1, version: learningVersion },
    { id: completion, track_id: 'ielts_reading', title: 'Synthetic completion', question_count: 2, version: learningVersion },
    { id: features, track_id: 'ielts_reading', title: 'Synthetic features', question_count: 1, version: learningVersion },
    { id: 'sat-quadratic-structure-1', track_id: 'sat_math', title: 'Synthetic quadratic', question_count: 1, version: learningVersion },
    { id: 'sat-data-interpretation-1', track_id: 'sat_math', title: 'Synthetic data', question_count: 1, version: learningVersion },
    { id: 'sat-grammar-transitions-1', track_id: 'sat_reading_writing', title: 'Synthetic grammar', question_count: 1, version: learningVersion },
  ];
  return { ...base, lessons: [...base.lessons, ...extra].reverse(), tracks: [
    { ...base.tracks[0]!, lesson_ids: ['ielts-reading-1', headings, completion, features] },
    { ...base.tracks[1]!, lesson_ids: ['sat-math-1', 'sat-quadratic-structure-1', 'sat-data-interpretation-1'] },
    { ...base.tracks[2]!, lesson_ids: ['sat-rw-1', 'sat-grammar-transitions-1'] },
  ] };
}
function packLesson(id: string): PreparationLesson {
  if (['ielts-reading-1', 'sat-math-1', 'sat-rw-1'].includes(id)) return lesson(id);
  const summary = pack().lessons.find(item => item.id === id)!;
  return { ...summary, version: summary.version!, introduction: 'Synthetic original teaching and passage. No private answer keys.', unofficial: true,
    questions: id === completion
      ? [1, 2].map(n => ({ id: `short-${n}`, prompt: `Find the recorded noun ${n}`, answer_format: 'short_answer' as const, max_words: 2 }))
      : [{ id: `${id}-q1`, prompt: 'Choose the supported evidence', choices: [{ id: 'a', text: 'Supported' }, { id: 'b', text: 'Unsupported' }] }],
  };
}
function receipt(input: PreparationAttemptInput, id = 'case-a'): StudyAttempt {
  if (input.lesson_id !== completion) return attempt(input, id);
  const feedback = input.answers.map(answer => {
    if (!('text' in answer)) throw new Error('Synthetic receipt requires text answers');
    const accepted = answer.question_id === 'short-1' ? ['dividers'] : ['condition sheet', 'sheet'];
    return { question_id: answer.question_id, selected_text: answer.text, accepted_answers: accepted,
      correct: accepted.includes(answer.text), explanation: `Saved explanation for ${answer.question_id}` };
  });
  return { ...structuredClone(input), id: `saved-${input.attempt_id}`, profile_id: id,
    correct: feedback.filter(item => item.correct).length, total: feedback.length, feedback, created_at: '2026-10-11T10:00:00Z' };
}
function schedule(): StudyScheduleOut {
  return { profile_id: 'case-a', revision: 4, updated_at: '2026-10-11T00:00:00Z', settings: {
    exam: 'ielts_academic', starts_on: '2026-10-01', certificate_deadline: '2026-11-10', first_exam_on: '2026-10-25', retake_on: null,
    result_wait_days: 3, delivery_days: 2, safety_days: 3, timezone: 'Asia/Almaty', weekly_minutes: 120, study_days: [0, 2],
    target_scores: { overall: 7, listening: 6.5, reading: 6.5, writing: 6.5, speaking: 6.5 }, baseline_scores: {}, baseline_on: null,
    confirmed_planning_dates: true, completed_task_ids: [],
  }, schedule: { as_of: '2026-10-11', latest_safe_exam_on: '2026-11-02', latest_exam_on: '2026-10-25',
    result_expected_on: '2026-10-28', delivery_expected_on: '2026-10-30', study_minutes_remaining: 180, remaining_study_days: 5,
    diagnostic_required: true, readiness: 'not_assessed', timing: 'within_entered_buffers', warnings: [],
    tasks: [{ id: 'unchanged-reading-task', due_on: '2026-10-12', title: 'Dated reading', kind: 'skill', skill: 'reading', minutes: 30,
      lesson_id: 'ielts-reading-1', completed: false, overdue: false }] } };
}
async function open(id: string) {
  fireEvent.click(await screen.findByRole('button', { name: 'Practice' }));
  fireEvent.click(screen.getByRole('button', { name: `Start ${pack().lessons.find(item => item.id === id)!.title}` }));
  await screen.findByRole('heading', { name: pack().lessons.find(item => item.id === id)!.title });
}
function answerShort(first = 'dividers', second = 'wrong') {
  fireEvent.change(screen.getByLabelText('Answer 1'), { target: { value: first } });
  fireEvent.change(screen.getByLabelText('Answer 2'), { target: { value: second } });
}
async function flush() { await act(async () => { for (let i = 0; i < 8; ++i) await Promise.resolve(); }); }
beforeEach(() => {
  localStorage.clear(); sessionStorage.clear();
  localStorage.setItem('ashyq.applicantOwner', ownerA); sessionStorage.setItem('ashyq.applicantOwner', ownerA);
  state.value = { savedProfile: profile('case-a'), caseEpoch: 0, results: [], hydrated: true, loading: false };
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in isolated learning path control'); }));
  vi.spyOn(api, 'preparationAccess').mockResolvedValue(access());
  vi.spyOn(api, 'preparationCatalogue').mockResolvedValue(pack());
  vi.spyOn(api, 'preparationProgress').mockImplementation(async id => progress(id));
  vi.spyOn(api, 'preparationPlan').mockImplementation(async id => plan(id));
  vi.spyOn(api, 'preparationLesson').mockImplementation(async (_id, lessonId) => packLesson(lessonId));
  vi.spyOn(api, 'submitPreparation').mockImplementation(async (id, input) => receipt(input, id));
  vi.spyOn(api, 'preparationAttemptReview').mockImplementation(async (id, uuid) => {
    const saved = progress(id).attempts.find(item => item.attempt_id === uuid);
    if (!saved) throw new Error('Synthetic review not configured');
    return { attempt: saved, lesson: null, notice: 'Saved feedback is practice only.' };
  });
  vi.spyOn(api, 'studySchedule').mockResolvedValue(schedule());
  vi.spyOn(api, 'saveStudySchedule'); vi.spyOn(api, 'updateProfile'); vi.spyOn(api, 'startRun');
});
afterEach(() => {
  expect(fetch).not.toHaveBeenCalled(); expect(api.saveStudySchedule).not.toHaveBeenCalled();
  expect(api.updateProfile).not.toHaveBeenCalled(); expect(api.startRun).not.toHaveBeenCalled();
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals();
});

describe('versioned original learning units and saved mistake review', () => {
  it('opts into the pack and uses track order, not unordered summaries or unqualified completion IDs', async () => {
    const old = attempt({ attempt_id: 'old-version', lesson_id: headings, version: 'older-content', answers: [{ question_id: 'old-q', choice_id: 'b' }] });
    const saved = attempt({ attempt_id: 'saved-starter', lesson_id: 'ielts-reading-1', version, answers: [{ question_id: 'ielts-reading-1-q1', choice_id: 'a' }] });
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [old, saved]));
    render(<PreparationScreen />);
    fireEvent.click(await screen.findByRole('button', { name: 'Practice' }));
    expect(api.preparationCatalogue).toHaveBeenCalledWith(learningVersion);
    expect(api.preparationProgress).toHaveBeenCalledWith('case-a', learningVersion);
    const path = screen.getByRole('region', { name: 'IELTS Reading learning path' });
    expect(within(path).getAllByRole('button').map(item => item.getAttribute('data-lesson-id'))).toEqual(['ielts-reading-1', headings, completion, features]);
    expect(within(path).getAllByText(/Saved submission/)).toHaveLength(1);
    expect(within(path).getByText(/Saved submission/).closest('li')).toHaveTextContent('Synthetic Reading');
    expect(screen.queryByText(/mastered skills/)).not.toBeInTheDocument();
  });

  it('requires the requested pack version rather than silently adopting the legacy catalogue', async () => {
    vi.mocked(api.preparationCatalogue).mockResolvedValue({ ...pack(), version });
    render(<PreparationScreen />);
    expect(await screen.findByRole('alert')).toHaveTextContent('requested version');
    expect(screen.queryByRole('button', { name: 'Practice' })).not.toBeInTheDocument();
    expect(api.preparationLesson).not.toHaveBeenCalled();
  });

  it('opens a dated legacy starter with its own version and offers the ordered next lesson only after acceptance', async () => {
    const pending = deferred<StudyAttempt>(); vi.mocked(api.submitPreparation).mockReturnValueOnce(pending.promise);
    const original = structuredClone(schedule());
    render(<PreparationScreen />);
    fireEvent.click(await screen.findByRole('button', { name: 'Study plan' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Open starter lesson: Dated reading' }));
    await screen.findByRole('radio', { name: 'Supported' });
    expect(api.preparationLesson).toHaveBeenCalledWith('case-a', 'ielts-reading-1', version);
    expect(screen.queryByTestId('next-lesson')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('radio', { name: 'Supported' })); fireEvent.click(screen.getByRole('button', { name: 'Submit practice' }));
    expect(screen.queryByTestId('next-lesson')).not.toBeInTheDocument();
    const input = vi.mocked(api.submitPreparation).mock.calls[0]![1];
    await act(async () => pending.resolve(receipt(input)));
    const next = await screen.findByRole('button', { name: 'Next lesson: Synthetic headings' });
    expect(next).toHaveAttribute('data-version', learningVersion); fireEvent.click(next);
    await screen.findByRole('heading', { name: 'Synthetic headings' });
    expect(api.preparationLesson).toHaveBeenLastCalledWith('case-a', headings, learningVersion);
    expect(screen.queryByLabelText('Practice feedback')).not.toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Supported' })).not.toBeChecked();
    expect(schedule()).toEqual(original); expect(api.studySchedule).toHaveBeenCalledTimes(1);
  });

  it('renders bounded short input without keys and keeps exact text/UUID through double send, failure and retry', async () => {
    const pending = deferred<StudyAttempt>(); vi.mocked(api.submitPreparation).mockReturnValueOnce(pending.promise);
    render(<PreparationScreen />); await open(completion);
    expect(api.preparationLesson).toHaveBeenCalledWith('case-a', completion, learningVersion);
    expect(screen.getByLabelText('Answer 1')).toHaveAttribute('maxlength', '100');
    expect(screen.getAllByText(/Use no more than 2 words/)).toHaveLength(2);
    expect(screen.queryByText(/condition sheet/)).not.toBeInTheDocument();
    answerShort('dividers', 'wrong');
    const form = screen.getByRole('button', { name: 'Submit practice' }).closest('form')!;
    fireEvent.submit(form); fireEvent.submit(form);
    expect(api.submitPreparation).toHaveBeenCalledTimes(1);
    const input = structuredClone(vi.mocked(api.submitPreparation).mock.calls[0]![1]);
    expect(input.answers).toEqual([{ question_id: 'short-1', text: 'dividers' }, { question_id: 'short-2', text: 'wrong' }]);
    expect(input.attempt_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(screen.getByLabelText('Answer 1')).toBeDisabled();
    await act(async () => pending.reject(new Error('Synthetic lost response')));
    expect(screen.queryByText('Practice saved.')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Answer 2')).toHaveValue('wrong');
    fireEvent.click(screen.getByRole('button', { name: 'Retry same submission' }));
    await screen.findByTestId('practice-result');
    expect(api.submitPreparation).toHaveBeenNthCalledWith(2, 'case-a', input);
    const rows = within(screen.getByLabelText('Practice feedback')).getAllByTestId('feedback-item');
    expect(rows.map(row => row.getAttribute('data-correct'))).toEqual(['false', 'true']);
    expect(rows[0]).toHaveTextContent('Your answer: wrong');
    expect(rows[0]).toHaveTextContent('Correct answer: condition sheet / sheet');
    expect(rows[0]).toHaveTextContent('Saved explanation for short-2');
  });

  it('creates a new UUID and clears text feedback when explicitly starting another attempt', async () => {
    render(<PreparationScreen />); await open(completion); answerShort();
    fireEvent.click(screen.getByRole('button', { name: 'Submit practice' })); await screen.findByTestId('practice-result');
    const first = vi.mocked(api.submitPreparation).mock.calls[0]![1];
    fireEvent.click(screen.getByRole('button', { name: 'Start a new attempt' }));
    await screen.findByLabelText('Answer 1'); expect(screen.getByLabelText('Answer 1')).toHaveValue('');
    expect(screen.queryByLabelText('Practice feedback')).not.toBeInTheDocument(); answerShort('dividers', 'sheet');
    fireEvent.click(screen.getByRole('button', { name: 'Submit practice' })); await screen.findByTestId('practice-result');
    expect(vi.mocked(api.submitPreparation).mock.calls[1]![1].attempt_id).not.toBe(first.attempt_id);
    expect(screen.getByTestId('practice-result')).toHaveTextContent('2 / 2');
  });

  it('does not accept a different lesson version or present it as the requested material', async () => {
    vi.mocked(api.preparationLesson).mockResolvedValueOnce({ ...packLesson(completion), version: 'unrequested' });
    render(<PreparationScreen />); await openFailedLesson(completion);
    expect(await screen.findByRole('alert')).toHaveTextContent('requested version');
    expect(screen.queryByLabelText('Answer 1')).not.toBeInTheDocument(); expect(api.submitPreparation).not.toHaveBeenCalled();
  });

  it('rejects a matching UUID receipt with a different submitted answer payload', async () => {
    vi.mocked(api.submitPreparation).mockImplementation(async (_id, input) => ({ ...receipt(input), answers: [{ question_id: 'short-1', text: 'different' }] }));
    render(<PreparationScreen />); await open(completion); answerShort(); fireEvent.click(screen.getByRole('button', { name: 'Submit practice' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('saved attempt did not match');
    expect(screen.queryByTestId('practice-result')).not.toBeInTheDocument(); expect(screen.queryByTestId('next-lesson')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Answer 1')).toHaveValue('dividers');
  });

  it('reviews persisted short feedback after expiry and remount without fetching or reconstructing current questions', async () => {
    const saved = receipt({ attempt_id: 'saved-short', lesson_id: completion, version: 'historical-version',
      answers: [{ question_id: 'short-1', text: 'dividers' }, { question_id: 'short-2', text: 'wrong' }] });
    vi.mocked(api.preparationAccess).mockResolvedValue(access(false));
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [saved]));
    vi.mocked(api.preparationAttemptReview).mockResolvedValue({ attempt: saved, lesson: null, notice: 'Stored historical feedback.' });
    const view = render(<PreparationScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review saved attempt 1' }));
    await screen.findByTestId('saved-attempt-review');
    const review = screen.getByLabelText('Saved attempt review');
    expect(review).toHaveTextContent('historical-version'); expect(review).toHaveTextContent('Correct answer: condition sheet / sheet');
    expect(review).toHaveTextContent('Stored question: short-2'); expect(review).toHaveTextContent('Your answer: wrong');
    expect(within(review).getAllByTestId('feedback-item')[0]).toHaveAttribute('data-correct', 'false');
    expect(api.preparationLesson).not.toHaveBeenCalled();
    view.unmount(); render(<PreparationScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review saved attempt 1' }));
    await screen.findByTestId('saved-attempt-review');
    expect(screen.getByLabelText('Saved attempt review')).toHaveTextContent('Saved explanation for short-2');
    expect(api.preparationLesson).not.toHaveBeenCalled();
  });

  it('uses stored choice IDs for an old saved version, not new lesson choice labels', async () => {
    const saved = attempt({ attempt_id: 'old-choice', lesson_id: 'ielts-reading-1', version: 'retired-version',
      answers: [{ question_id: 'ielts-reading-1-q1', choice_id: 'b' }] });
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [saved]));
    vi.mocked(api.preparationAttemptReview).mockResolvedValue({ attempt: saved, lesson: null, notice: 'Original version unavailable.' }); render(<PreparationScreen />);
    fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review saved attempt 1' }));
    await screen.findByTestId('saved-attempt-review');
    expect(screen.getByLabelText('Saved attempt review')).toHaveTextContent('Your answer: Choice ID: b');
    expect(screen.getByLabelText('Saved attempt review')).toHaveTextContent('Correct answer: Choice ID: a');
    expect(screen.getByLabelText('Saved attempt review')).not.toHaveTextContent('Supported'); expect(api.preparationLesson).not.toHaveBeenCalled();
  });

  it('reads exact immutable question and choice text through owned review rather than a current lesson fetch', async () => {
    const saved = attempt({ attempt_id: 'immutable-choice', lesson_id: 'ielts-reading-1', version,
      answers: [{ question_id: 'ielts-reading-1-q1', choice_id: 'b' }] });
    const original = { ...lesson(), introduction: 'Immutable original teaching', questions: [{ id: 'ielts-reading-1-q1',
      prompt: 'Immutable original stem', choices: [{ id: 'a', text: 'Original correct text' }, { id: 'b', text: 'Original selected text' }] }] };
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [saved]));
    vi.mocked(api.preparationAttemptReview).mockResolvedValue({ attempt: saved, lesson: original, notice: 'Stored exact version.' });
    render(<PreparationScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review saved attempt 1' })); await screen.findByTestId('saved-attempt-review');
    expect(api.preparationAttemptReview).toHaveBeenCalledWith('case-a', saved.attempt_id);
    expect(screen.getByLabelText('Saved attempt review')).toHaveTextContent('Immutable original stem');
    expect(screen.getByLabelText('Saved attempt review')).toHaveTextContent('Your answer: Original selected text');
    expect(screen.getByLabelText('Saved attempt review')).toHaveTextContent('Correct answer: Original correct text');
    expect(api.preparationLesson).not.toHaveBeenCalled();
  });

  it('keeps the same review request in flight and explicitly retries a failed read without writes', async () => {
    const saved = receipt({ attempt_id: 'retry-review', lesson_id: completion, version: learningVersion,
      answers: [{ question_id: 'short-1', text: 'dividers' }, { question_id: 'short-2', text: 'sheet' }] });
    const pending = deferred<{ attempt: StudyAttempt; lesson: PreparationLesson | null; notice: string }>();
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [saved]));
    vi.mocked(api.preparationAttemptReview).mockReturnValueOnce(pending.promise).mockResolvedValue({ attempt: saved, lesson: packLesson(completion), notice: 'Accepted saved review.' });
    render(<PreparationScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    const button = screen.getByRole('button', { name: 'Review saved attempt 1' });
    act(() => { fireEvent.click(button); fireEvent.click(button); });
    expect(api.preparationAttemptReview).toHaveBeenCalledTimes(1); expect(screen.queryByTestId('saved-attempt-review')).not.toBeInTheDocument();
    await act(async () => pending.reject(new Error('Synthetic read failure')));
    expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic read failure');
    fireEvent.click(screen.getByRole('button', { name: 'Retry saved review' })); await screen.findByTestId('saved-attempt-review');
    expect(api.preparationAttemptReview).toHaveBeenNthCalledWith(2, 'case-a', saved.attempt_id);
    fireEvent.click(button); expect(api.preparationAttemptReview).toHaveBeenCalledTimes(2);
    expect(api.submitPreparation).not.toHaveBeenCalled();
  });

  it('ignores an older review after a newer saved attempt is selected', async () => {
    const first = attempt({ attempt_id: 'first-review', lesson_id: 'ielts-reading-1', version, answers: [{ question_id: 'old-q', choice_id: 'b' }] });
    const second = receipt({ attempt_id: 'second-review', lesson_id: completion, version: learningVersion,
      answers: [{ question_id: 'short-1', text: 'dividers' }, { question_id: 'short-2', text: 'sheet' }] });
    const pending = deferred<{ attempt: StudyAttempt; lesson: PreparationLesson | null; notice: string }>();
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [first, second]));
    vi.mocked(api.preparationAttemptReview).mockReturnValueOnce(pending.promise).mockResolvedValue({ attempt: second, lesson: packLesson(completion), notice: 'Second owned review.' });
    render(<PreparationScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review saved attempt 1' })); fireEvent.click(screen.getByRole('button', { name: 'Review saved attempt 2' }));
    expect(await screen.findByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', second.attempt_id);
    await act(async () => pending.resolve({ attempt: first, lesson: null, notice: 'Late first private review.' })); await flush();
    expect(screen.getByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', second.attempt_id);
    expect(screen.queryByText('Late first private review.')).not.toBeInTheDocument();
  });

  it.each(['profile', 'uuid', 'lesson-version'] as const)('rejects mismatched review %s before rendering feedback', async mismatch => {
    const saved = receipt({ attempt_id: 'matched-review', lesson_id: completion, version: learningVersion,
      answers: [{ question_id: 'short-1', text: 'dividers' }, { question_id: 'short-2', text: 'sheet' }] });
    const returned = { ...saved, ...(mismatch === 'profile' ? { profile_id: 'case-b' } : mismatch === 'uuid' ? { attempt_id: 'foreign-review' } : {}) };
    const returnedLesson = { ...packLesson(completion), version: mismatch === 'lesson-version' ? 'unrequested' : learningVersion };
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [saved]));
    vi.mocked(api.preparationAttemptReview).mockResolvedValue({ attempt: returned, lesson: returnedLesson, notice: 'Do not reveal mismatched data.' });
    render(<PreparationScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review saved attempt 1' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('saved review did not match');
    expect(screen.queryByTestId('saved-attempt-review')).not.toBeInTheDocument();
    expect(screen.queryByText('Do not reveal mismatched data.')).not.toBeInTheDocument();
  });

  it('fences a review read after owner changes before a storage event reaches React', async () => {
    const saved = receipt({ attempt_id: 'owner-review', lesson_id: completion, version: learningVersion,
      answers: [{ question_id: 'short-1', text: 'dividers' }, { question_id: 'short-2', text: 'sheet' }] });
    const pending = deferred<{ attempt: StudyAttempt; lesson: PreparationLesson | null; notice: string }>();
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', [saved])); vi.mocked(api.preparationAttemptReview).mockReturnValue(pending.promise);
    render(<PreparationScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review saved attempt 1' })); localStorage.setItem('ashyq.applicantOwner', ownerB);
    await act(async () => pending.resolve({ attempt: saved, lesson: packLesson(completion), notice: 'Late previous owner review.' })); await flush();
    expect(screen.queryByTestId('saved-attempt-review')).not.toBeInTheDocument(); expect(screen.queryByText('Late previous owner review.')).not.toBeInTheDocument();
  });

  it('hides and discards a pending review at case switch-start before the new case commits', async () => {
    const saved = receipt({ attempt_id: 'case-review', lesson_id: completion, version: learningVersion,
      answers: [{ question_id: 'short-1', text: 'dividers' }, { question_id: 'short-2', text: 'sheet' }] });
    const pending = deferred<{ attempt: StudyAttempt; lesson: PreparationLesson | null; notice: string }>();
    vi.mocked(api.preparationProgress).mockResolvedValueOnce(progress('case-a', [saved])).mockResolvedValueOnce(progress('case-a', [saved])).mockImplementation(async id => progress(id));
    vi.mocked(api.preparationAttemptReview).mockReturnValue(pending.promise);
    const view = render(<PreparationScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
    fireEvent.click(screen.getByRole('button', { name: 'Review saved attempt 1' }));
    state.value = { ...state.value, caseEpoch: 1, loading: true }; view.rerender(<PreparationScreen />);
    expect(screen.queryByLabelText('Saved attempt review')).not.toBeInTheDocument();
    await act(async () => pending.resolve({ attempt: saved, lesson: packLesson(completion), notice: 'Late case A review.' }));
    state.value = { ...state.value, savedProfile: profile('case-b'), loading: false }; view.rerender(<PreparationScreen />);
    await screen.findByRole('button', { name: 'Progress' }); await flush(); expect(screen.queryByLabelText('Saved attempt review')).not.toBeInTheDocument();
    expect(screen.queryByText('Late case A review.')).not.toBeInTheDocument();
  });

  it('fences delayed short feedback after a shared owner change before React replacement', async () => {
    const pending = deferred<StudyAttempt>(); vi.mocked(api.submitPreparation).mockReturnValueOnce(pending.promise);
    render(<PreparationScreen />); await open(completion); answerShort(); fireEvent.click(screen.getByRole('button', { name: 'Submit practice' }));
    const input = vi.mocked(api.submitPreparation).mock.calls[0]![1]; const reads = vi.mocked(api.preparationProgress).mock.calls.length;
    localStorage.setItem('ashyq.applicantOwner', ownerB);
    await act(async () => pending.resolve(receipt(input))); await flush();
    expect(screen.queryByTestId('practice-result')).not.toBeInTheDocument(); expect(screen.queryByTestId('next-lesson')).not.toBeInTheDocument();
    expect(api.preparationProgress).toHaveBeenCalledTimes(reads);
  });

  it('drops text, accepted history review and late submission across a case switch', async () => {
    const pending = deferred<StudyAttempt>(); vi.mocked(api.submitPreparation).mockReturnValueOnce(pending.promise);
    const view = render(<PreparationScreen />); await open(completion); answerShort(); fireEvent.click(screen.getByRole('button', { name: 'Submit practice' }));
    const input = vi.mocked(api.submitPreparation).mock.calls[0]![1];
    state.value = { ...state.value, caseEpoch: 1, loading: true }; view.rerender(<PreparationScreen />);
    expect(screen.queryByLabelText('Answer 1')).not.toBeInTheDocument();
    state.value = { ...state.value, savedProfile: profile('case-b'), loading: false }; view.rerender(<PreparationScreen />);
    await screen.findByRole('button', { name: 'Progress' }); const reads = vi.mocked(api.preparationProgress).mock.calls.length;
    await act(async () => pending.resolve(receipt(input))); await flush();
    expect(screen.queryByLabelText('Practice feedback')).not.toBeInTheDocument(); expect(api.preparationProgress).toHaveBeenCalledTimes(reads);
    fireEvent.click(screen.getByRole('button', { name: 'Progress' })); await flush();
    expect(screen.queryByRole('button', { name: 'Review saved attempt 1' })).not.toBeInTheDocument();
    expect(screen.getByTestId('progress-summary')).toHaveTextContent('0 saved attempts');
  });

  it('keeps accepted saved-version markers even when the immediate history refresh fails', async () => {
    vi.mocked(api.preparationProgress).mockResolvedValueOnce(progress()).mockRejectedValue(new Error('Synthetic history unavailable'));
    render(<PreparationScreen />); await open(completion); answerShort(); fireEvent.click(screen.getByRole('button', { name: 'Submit practice' }));
    await screen.findByTestId('practice-result'); await screen.findByRole('alert');
    fireEvent.click(screen.getByRole('button', { name: 'Practice' }));
    const marker = screen.getByText(/Saved submission/); expect(marker.closest('li')).toHaveTextContent('Synthetic completion');
    expect(marker.closest('li')).toHaveAttribute('data-version', learningVersion);
  });
});
async function openFailedLesson(id: string) {
  fireEvent.click(await screen.findByRole('button', { name: 'Practice' }));
  fireEvent.click(screen.getByRole('button', { name: `Start ${pack().lessons.find(item => item.id === id)!.title}` }));
  await flush();
}

function calendar(ref: import('@/types').LearningTaskRef): import('@/types').LearningPathOut {
  const old = schedule();
  return { profile_id: 'case-a', revision: old.revision, legacy_fingerprint: 'legacy', needs_review: false, updated_at: old.updated_at,
    learning_path: { legacy_settings: old.settings!, legacy_fingerprint: 'legacy',
      draft: { planned_on: old.schedule!.as_of, fingerprint: 'draft', plan: { planner_version: 'schedule-v2', catalogue_version: learningVersion,
        schedule_settings: old.settings!, lessons: [], reviews: ref.kind === 'attempt_review' ? [ref] : [] } },
      schedule: { ...old.schedule!, unallocated_lesson_ids: [], unallocated_review_ids: [], tasks: [{ ...old.schedule!.tasks[0]!,
        learning_ref: ref, lesson_id: null, availability: 'available', unavailable_reason: null, submitted_attempt_id: null }] },
    } };
}
async function openDatedCalendar() {
  fireEvent.click(await screen.findByRole('button', { name: 'Study plan' }));
  fireEvent.click(await screen.findByRole('button', { name: 'View learning calendar' }));
}

describe('exact calendar actions outside latest catalogue and recent progress', () => {
  it('requests a pinned older lesson version rather than the current catalogue summary', async () => {
    const exact = 'retained-original-version';
    vi.spyOn(api, 'learningStudySchedule').mockResolvedValue(calendar({ kind: 'lesson', id: `lesson:ielts-reading-1:${exact}`, lesson_id: 'ielts-reading-1', content_version: exact }));
    vi.mocked(api.preparationLesson).mockResolvedValue({ ...lesson(), version: exact });
    render(<PreparationScreen />); await openDatedCalendar();
    fireEvent.click(await screen.findByRole('button', { name: 'Open lesson', exact: true }));
    await screen.findByRole('radio', { name: 'Supported' });
    expect(api.preparationLesson).toHaveBeenCalledWith('case-a', 'ielts-reading-1', exact);
  });
  it('opens an owned pinned review by UUID even when it is outside the recent twenty attempts', async () => {
    const uuid = '123e4567-e89b-42d3-a456-426614174000';
    const saved = attempt({ attempt_id: uuid, lesson_id: 'ielts-reading-1', version, answers: [{ question_id: 'ielts-reading-1-q1', choice_id: 'b' }] });
    vi.spyOn(api, 'learningStudySchedule').mockResolvedValue(calendar({ kind: 'attempt_review', id: `attempt:${uuid}`, attempt_id: uuid, lesson_id: 'ielts-reading-1', content_version: version }));
    vi.mocked(api.preparationProgress).mockResolvedValue(progress('case-a', []));
    vi.mocked(api.preparationAttemptReview).mockResolvedValue({ attempt: saved, lesson: lesson(), notice: 'Owned retained practice feedback.' });
    render(<PreparationScreen />); await openDatedCalendar();
    fireEvent.click(await screen.findByRole('button', { name: 'Review my saved attempt', exact: true }));
    expect(await screen.findByTestId('saved-attempt-review')).toHaveAttribute('data-attempt-id', uuid);
    expect(api.preparationAttemptReview).toHaveBeenCalledWith('case-a', uuid);
    expect(api.preparationLesson).not.toHaveBeenCalled();
  });
  it('refuses a mismatched version returned for the exact dated lesson', async () => {
    const exact = 'retained-original-version';
    vi.spyOn(api, 'learningStudySchedule').mockResolvedValue(calendar({ kind: 'lesson', id: `lesson:ielts-reading-1:${exact}`, lesson_id: 'ielts-reading-1', content_version: exact }));
    vi.mocked(api.preparationLesson).mockResolvedValue(lesson());
    render(<PreparationScreen />); await openDatedCalendar();
    fireEvent.click(await screen.findByRole('button', { name: 'Open lesson', exact: true }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The lesson did not match the requested version.');
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    expect(api.submitPreparation).not.toHaveBeenCalled();
  });
});

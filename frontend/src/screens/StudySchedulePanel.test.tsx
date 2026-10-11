import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from '@/api/client';
import type { ScheduleSettings, ScheduleWrite, StudyScheduleOut } from '@/types';
import { StudySchedulePanel } from './StudySchedulePanel';

function settings(overrides: Partial<ScheduleSettings> = {}): ScheduleSettings {
  return { exam: 'ielts_academic', starts_on: '2026-10-01', certificate_deadline: '2026-11-10',
    first_exam_on: '2026-10-25', retake_on: null, result_wait_days: 3, delivery_days: 2, safety_days: 3,
    timezone: 'Asia/Almaty', weekly_minutes: 120, study_days: [0, 2],
    target_scores: { overall: 7, listening: 6.5, reading: 6.5, writing: 6.5, speaking: 6.5 },
    baseline_scores: {}, baseline_on: null, confirmed_planning_dates: true, completed_task_ids: [], ...overrides };
}
function stored(profileId = 'case-a', value: ScheduleSettings | null = settings(), revision = 4): StudyScheduleOut {
  return { profile_id: profileId, revision, settings: value, updated_at: value ? '2026-10-11T00:00:00Z' : null,
    schedule: value ? { as_of: '2026-10-11', latest_safe_exam_on: '2026-11-02', latest_exam_on: value.retake_on ?? value.first_exam_on,
      result_expected_on: '2026-10-28', delivery_expected_on: '2026-10-30', study_minutes_remaining: 180,
      remaining_study_days: 5, diagnostic_required: !value.baseline_scores.reading, readiness: 'not_assessed', timing: 'within_entered_buffers',
      warnings: ['Listening, writing and speaking need appropriate external practice and feedback.'],
      tasks: [{ id: 'task-reading', due_on: '2026-10-12', title: 'Reading introduction', kind: 'skill', skill: 'reading', minutes: 30,
        lesson_id: 'ielts-reading-1', completed: value.completed_task_ids.includes('task-reading'), overdue: false }] } : null };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (problem: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
let live = true;
const onLesson = vi.fn();
const current = () => live;
const props = (profileId = 'case-a', allowed = true) => ({ profileId, allowed, isCurrent: current, onLesson });
async function ready() { await screen.findByText('Saved dated tasks'); }
function change(label: string, value: string) { fireEvent.change(screen.getByLabelText(label), { target: { value } }); }
function submit() { fireEvent.submit(screen.getByRole('button', { name: 'Save study plan' }).closest('form')!); }
function fillNewPlan() {
  for (const [label, value] of Object.entries({ 'Preparation starts': '2026-10-01', 'Certificate deadline': '2026-11-10',
    'First exam': '2026-10-25', 'Result wait (days)': '3', 'Delivery (days)': '2', 'Safety buffer (days)': '3',
    'Time zone': 'Asia/Almaty', 'Weekly study minutes': '120', 'Overall target': '7', 'Listening target': '6.5',
    'Reading target': '6.5', 'Writing target': '6.5', 'Speaking target': '6.5' })) change(label, value);
  fireEvent.click(screen.getByLabelText('Monday')); fireEvent.click(screen.getByLabelText('Wednesday'));
  fireEvent.click(screen.getByLabelText('I confirm these are my planning dates and buffers, not verified bookings or official deadlines'));
}
beforeEach(() => {
  live = true; onLesson.mockReset();
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network in synthetic schedule control'); }));
  vi.spyOn(api, 'studySchedule').mockImplementation(async id => stored(id));
  vi.spyOn(api, 'saveStudySchedule').mockImplementation(async (id, input) => stored(id, input.settings, input.expected_revision + 1));
  vi.spyOn(api, 'updateProfile'); vi.spyOn(api, 'createProfile'); vi.spyOn(api, 'startRun');
});
afterEach(() => {
  expect(fetch).not.toHaveBeenCalled(); expect(api.updateProfile).not.toHaveBeenCalled();
  expect(api.createProfile).not.toHaveBeenCalled(); expect(api.startRun).not.toHaveBeenCalled();
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals();
});

describe('owned deadline study schedule', () => {
  it('loads on mount and requires explicit dates, all targets, budget, study days and buffers for a new plan', async () => {
    expect(api.studySchedule).not.toHaveBeenCalled();
    vi.mocked(api.studySchedule).mockResolvedValue(stored('case-a', null, 0));
    render(<StudySchedulePanel {...props()} />);
    await screen.findByRole('button', { name: 'Save study plan' });
    expect(screen.getByLabelText('Result wait (days)')).toHaveValue(null);
    expect(screen.getByLabelText('Delivery (days)')).toHaveValue(null);
    expect(screen.getByLabelText('Safety buffer (days)')).toHaveValue(null);
    expect(screen.getByLabelText('Certificate deadline')).toHaveValue('');
    submit(); expect(api.saveStudySchedule).not.toHaveBeenCalled();
    fillNewPlan(); submit();
    await screen.findByText('Study plan saved.');
    expect(api.saveStudySchedule).toHaveBeenCalledWith('case-a', { expected_revision: 0, settings: settings() });
    expect(screen.getByText(/Latest exam under your entered buffers: 2026-11-02/)).toBeInTheDocument();
    expect(screen.getByText(/Readiness: not assessed/)).toBeInTheDocument();
  });

  it('retains the complete form and denies double writes until a failed save can be explicitly retried', async () => {
    const pending = deferred<StudyScheduleOut>();
    vi.mocked(api.saveStudySchedule).mockImplementationOnce(() => pending.promise);
    render(<StudySchedulePanel {...props()} />); await ready();
    change('Weekly study minutes', '150'); submit(); submit();
    expect(api.saveStudySchedule).toHaveBeenCalledTimes(1);
    const input = structuredClone(vi.mocked(api.saveStudySchedule).mock.calls[0]![1]);
    await act(async () => pending.reject(new Error('Synthetic transport failure')));
    expect(screen.getByRole('alert')).toHaveTextContent('Not saved. Your inputs remain in this form.');
    expect(screen.queryByText('Study plan saved.')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Weekly study minutes')).toHaveValue(150);
    submit(); await screen.findByText('Study plan saved.');
    expect(api.saveStudySchedule).toHaveBeenNthCalledWith(2, 'case-a', input);
  });

  it('refreshes a revision conflict without repeating PUT and requires review before explicitly applying the retained inputs', async () => {
    vi.mocked(api.saveStudySchedule).mockRejectedValueOnce(new ApiError(409, 'Changed revision'));
    vi.mocked(api.studySchedule).mockResolvedValueOnce(stored()).mockResolvedValueOnce(stored('case-a', settings({ weekly_minutes: 180 }), 6));
    render(<StudySchedulePanel {...props()} />); await ready();
    change('Weekly study minutes', '150'); submit();
    await waitFor(() => expect(api.studySchedule).toHaveBeenCalledTimes(2));
    const review = await screen.findByLabelText('I reviewed the latest saved version before replacing it');
    await waitFor(() => expect(review).toBeEnabled());
    expect(screen.getByLabelText('Weekly study minutes')).toHaveValue(150);
    expect(screen.getByRole('button', { name: 'Save study plan' })).toBeDisabled();
    expect(api.saveStudySchedule).toHaveBeenCalledTimes(1);
    fireEvent.click(review); submit(); await screen.findByText('Study plan saved.');
    expect(api.saveStudySchedule).toHaveBeenNthCalledWith(2, 'case-a', { expected_revision: 6, settings: settings({ weekly_minutes: 150 }) });
  });

  it('keeps conflict review blocked when the latest GET fails even if an edit clears the alert', async () => {
    vi.mocked(api.saveStudySchedule).mockRejectedValueOnce(new ApiError(409, 'Changed revision'));
    vi.mocked(api.studySchedule).mockResolvedValueOnce(stored()).mockRejectedValueOnce(new Error('Refresh unavailable'));
    render(<StudySchedulePanel {...props()} />); await ready();
    change('Weekly study minutes', '150'); submit(); await screen.findByText('Refresh unavailable');
    change('Weekly study minutes', '160');
    expect(screen.getByLabelText('I reviewed the latest saved version before replacing it')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Save study plan' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Refresh latest saved plan' })).toBeEnabled();
    submit(); expect(api.saveStudySchedule).toHaveBeenCalledTimes(1);
  });

  it('saves one checkbox intent with unchanged settings/revision and never marks completion before acceptance', async () => {
    const pending = deferred<StudyScheduleOut>();
    vi.mocked(api.saveStudySchedule).mockImplementationOnce(() => pending.promise);
    render(<StudySchedulePanel {...props()} />); await ready();
    const checkbox = screen.getByLabelText('Completed: Reading introduction (2026-10-12)');
    fireEvent.click(checkbox); fireEvent.click(checkbox);
    const input: ScheduleWrite = { expected_revision: 4, settings: settings({ completed_task_ids: ['task-reading'] }) };
    expect(api.saveStudySchedule).toHaveBeenCalledTimes(1);
    expect(api.saveStudySchedule).toHaveBeenCalledWith('case-a', input);
    expect(checkbox).not.toBeChecked();
    await act(async () => pending.reject(new Error('Synthetic save failure')));
    expect(checkbox).not.toBeChecked(); fireEvent.click(checkbox);
    await waitFor(() => expect(checkbox).toBeChecked());
    expect(api.saveStudySchedule).toHaveBeenNthCalledWith(2, 'case-a', input);
    expect(screen.getByText(/This is your reported completion, not an assessed score/)).toBeInTheDocument();
  });

  it('requires explicit calendar-reset confirmation when structural inputs change, then clears only task checkmarks', async () => {
    vi.mocked(api.studySchedule).mockResolvedValue(stored('case-a', settings({ completed_task_ids: ['task-reading'] })));
    render(<StudySchedulePanel {...props()} />); await ready();
    change('Weekly study minutes', '180'); submit();
    expect(api.saveStudySchedule).not.toHaveBeenCalled();
    fireEvent.click(screen.getByLabelText('Rebuild the calendar and clear previous task checkmarks')); submit();
    await screen.findByText('Study plan saved.');
    expect(api.saveStudySchedule).toHaveBeenCalledWith('case-a', { expected_revision: 4, settings: settings({ weekly_minutes: 180, completed_task_ids: [] }) });
  });

  it('allows a newer partial current-score entry after preparation started without treating missing components as zero', async () => {
    render(<StudySchedulePanel {...props()} />); await ready();
    change('Reading current score (optional)', '6'); change('Current-score date (optional)', '2026-10-10'); submit();
    await screen.findByText('Study plan saved.');
    expect(api.saveStudySchedule).toHaveBeenCalledWith('case-a', { expected_revision: 4,
      settings: settings({ baseline_scores: { reading: 6 }, baseline_on: '2026-10-10' }) });
    expect(screen.getByText(/Readiness: not assessed/)).toBeInTheDocument();
  });

  it('clears current scores when selecting another active exam and keeps all SAT target components explicit', async () => {
    vi.mocked(api.studySchedule).mockResolvedValue(stored('case-a', settings({ baseline_scores: { reading: 6 }, baseline_on: '2026-09-30' })));
    render(<StudySchedulePanel {...props()} />); await ready();
    change('Exam', 'digital_sat');
    expect(screen.getByLabelText('Current-score date (optional)')).toHaveValue('');
    expect(screen.getByLabelText('Math current score (optional)')).toHaveValue(null);
    expect(screen.getByLabelText('Total target')).toHaveValue(null);
    change('Total target', '1400'); change('Math target', '700'); change('Reading & Writing target', '700'); submit();
    await screen.findByText('Study plan saved.');
    expect(api.saveStudySchedule).toHaveBeenCalledWith('case-a', { expected_revision: 4, settings: settings({
      exam: 'digital_sat', target_scores: { total: 1400, math: 700, reading_writing: 700 }, baseline_scores: {}, baseline_on: null }) });
  });

  it('keeps saved own schedules readable without access while blocking writes and starter openings', async () => {
    render(<StudySchedulePanel {...props('case-a', false)} />); await ready();
    expect(api.studySchedule).toHaveBeenCalledWith('case-a');
    expect(screen.getByRole('button', { name: 'Save study plan' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Open starter lesson: Reading introduction' })).toBeDisabled();
    submit(); expect(api.saveStudySchedule).not.toHaveBeenCalled(); expect(onLesson).not.toHaveBeenCalled();
  });

  it('remounts a changed case and ignores a late old-case read', async () => {
    const pending = deferred<StudyScheduleOut>();
    vi.mocked(api.studySchedule).mockImplementationOnce(() => pending.promise);
    const view = render(<StudySchedulePanel {...props()} />);
    view.rerender(<StudySchedulePanel {...props('case-b')} />); await ready();
    await act(async () => pending.resolve(stored('case-a', settings({ weekly_minutes: 900 }))));
    expect(screen.getByLabelText('Weekly study minutes')).toHaveValue(120);
    expect(api.studySchedule).toHaveBeenLastCalledWith('case-b');
  });

  it('rejects a mismatched saved-case response and suppresses a late write after the owner changes', async () => {
    vi.mocked(api.studySchedule).mockResolvedValueOnce(stored('case-other'));
    const view = render(<StudySchedulePanel {...props()} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('did not match this applicant case');
    expect(screen.queryByText('Saved dated tasks')).not.toBeInTheDocument();
    view.unmount();
    const pending = deferred<StudyScheduleOut>(); vi.mocked(api.saveStudySchedule).mockImplementationOnce(() => pending.promise);
    const next = render(<StudySchedulePanel {...props()} />); await ready(); submit();
    live = false; next.rerender(<StudySchedulePanel {...props()} />);
    await act(async () => pending.resolve(stored('case-a', settings(), 5)));
    expect(screen.queryByText('Study plan saved.')).not.toBeInTheDocument();
    expect(screen.queryByText('Saved dated tasks')).not.toBeInTheDocument();
  });

  it('shows fourteen upcoming tasks and preserves the rest and past warnings in a native disclosure', async () => {
    const value = stored();
    value.schedule!.tasks = Array.from({ length: 17 }, (_, index) => ({ id: `task-${index}`, due_on: `2026-10-${String(index + 12).padStart(2, '0')}`,
      title: `Review skill ${index}`, kind: 'review', skill: 'reading', minutes: 10, lesson_id: null, completed: false, overdue: false }));
    value.schedule!.tasks.unshift({ id: 'past', due_on: '2026-10-02', title: 'Past diagnostic', kind: 'diagnostic', skill: null,
      minutes: 10, lesson_id: null, completed: false, overdue: true });
    vi.mocked(api.studySchedule).mockResolvedValue(value);
    render(<StudySchedulePanel {...props()} />); await ready();
    const summary = screen.getByText('Other saved tasks (4), including past tasks');
    const details = summary.closest('details')!;
    const checkmarks = screen.getAllByRole('checkbox', { name: /^Completed:/ });
    // JSDOM role queries include closed details descendants; verify both DOM groups and the native toggle.
    expect(checkmarks.filter(item => !details.contains(item))).toHaveLength(14);
    expect(checkmarks.filter(item => details.contains(item))).toHaveLength(4);
    expect(details).not.toHaveAttribute('open');
    expect(screen.getByText(/1 past-due unchecked tasks/)).toBeVisible();
    fireEvent.click(summary);
    expect(details).toHaveAttribute('open');
    expect(screen.getAllByRole('checkbox', { name: /^Completed:/ })).toHaveLength(18);
    expect(screen.getByText(/2026-10-02 · Past diagnostic/)).toBeVisible();
    expect(onLesson).not.toHaveBeenCalled();
  });
});

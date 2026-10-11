import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from '@/api/client';
import type { LearningPathOut, LearningPathSnapshot, LearningTaskRef, ScheduleSettings } from '@/types';
import { setLocale } from '@/lib/i18n';
import { LearningSchedulePanel } from './LearningSchedulePanel';

const lessonRef = { kind: 'lesson', id: 'lesson:ielts-reading-1:exact-v1',
  lesson_id: 'ielts-reading-1', content_version: 'exact-v1' } as const;
const reviewRef = { kind: 'attempt_review', id: 'attempt:123e4567-e89b-42d3-a456-426614174000',
  attempt_id: '123e4567-e89b-42d3-a456-426614174000', lesson_id: 'ielts-reading-1', content_version: 'exact-v1' } as const;
const settings: ScheduleSettings = {
  exam: 'ielts_academic', starts_on: '2026-10-01', certificate_deadline: '2026-11-10',
  first_exam_on: '2026-10-25', retake_on: null, result_wait_days: 3, delivery_days: 2, safety_days: 3,
  timezone: 'Asia/Almaty', weekly_minutes: 120, study_days: [0, 2], target_scores: { overall: 7 },
  baseline_scores: {}, baseline_on: null, confirmed_planning_dates: true, completed_task_ids: ['legacy-tick'],
};
function snapshot(ref: typeof lessonRef | typeof reviewRef = lessonRef): LearningPathSnapshot {
  return {
    draft: { planned_on: '2026-10-11', fingerprint: 'draft-fingerprint', plan: {
      planner_version: 'schedule-v2', catalogue_version: 'exact-v1', schedule_settings: { ...settings, completed_task_ids: [] },
      lessons: [{ ref: lessonRef, skill: 'reading', title: 'Exact reading lesson', planned_minutes: 20 }],
      reviews: ref.kind === 'attempt_review' ? [reviewRef] : [],
    } },
    legacy_settings: settings, legacy_fingerprint: 'legacy-fingerprint',
    schedule: {
      as_of: '2026-10-11', latest_exam_on: '2026-10-25', latest_safe_exam_on: '2026-11-02',
      result_expected_on: '2026-10-28', delivery_expected_on: '2026-10-30',
      study_minutes_remaining: 20, remaining_study_days: 1, diagnostic_required: true,
      readiness: 'not_assessed', timing: 'within_entered_buffers', warnings: [], unallocated_lesson_ids: [], unallocated_review_ids: [],
      tasks: [{ id: 'dated-task', due_on: '2026-10-12', title: 'Exact dated task',
        kind: ref.kind === 'lesson' ? 'skill' : 'review', skill: 'reading', minutes: 20,
        lesson_id: null, completed: false, overdue: false, learning_ref: ref,
        availability: 'available', unavailable_reason: null, submitted_attempt_id: null }],
    },
  };
}
function record(revision = 4, path: LearningPathSnapshot | null = snapshot(), needs_review = false): LearningPathOut {
  return { profile_id: 'case-a', revision, legacy_fingerprint: 'legacy-fingerprint',
    learning_path: path, needs_review, updated_at: '2026-10-11T00:00:00Z' };
}
const onTarget = vi.fn<(ref: LearningTaskRef) => void>();
const onSaved = vi.fn();
const props = (revision = 4, allowed = true) => ({ profileId: 'case-a', revision, allowed,
  dirty: false, isCurrent: () => true, onTarget, onSaved });
async function openCalendar(canPreview = true) {
  fireEvent.click(screen.getByRole('button', { name: 'View learning calendar' }));
  const preview = await screen.findByRole('button', { name: 'Preview updated learning path' });
  await waitFor(() => canPreview ? expect(preview).toBeEnabled() : expect(preview).toBeDisabled());
}
beforeEach(() => {
  setLocale('en');
  onTarget.mockReset(); onSaved.mockReset();
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in synthetic learning calendar control'); }));
  vi.spyOn(api, 'learningStudySchedule').mockResolvedValue(record());
  vi.spyOn(api, 'previewLearningSchedule').mockResolvedValue(record());
  vi.spyOn(api, 'saveLearningSchedule').mockResolvedValue(record(5));
  vi.spyOn(api, 'saveStudySchedule');
});
afterEach(() => {
  expect(fetch).not.toHaveBeenCalled();
  expect(api.saveStudySchedule).not.toHaveBeenCalled();
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals();
});

describe('opt-in exact learning calendar', () => {
  it('keeps a nullable sidecar separate from legacy ticks until explicit preview and PUT', async () => {
    vi.mocked(api.learningStudySchedule).mockResolvedValue(record(4, null));
    render(<LearningSchedulePanel {...props()} />);
    expect(api.learningStudySchedule).not.toHaveBeenCalled();
    await openCalendar();
    expect(screen.queryByRole('button', { name: 'Use this updated path' })).not.toBeInTheDocument();
    expect(api.previewLearningSchedule).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Preview updated learning path' }));
    await screen.findByRole('button', { name: 'Use this updated path' });
    expect(api.previewLearningSchedule).toHaveBeenCalledWith('case-a', 4);
    expect(api.saveLearningSchedule).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Use this updated path' }));
    await waitFor(() => expect(api.saveLearningSchedule).toHaveBeenCalledWith('case-a', {
      expected_revision: 4, legacy_fingerprint: 'legacy-fingerprint', draft: snapshot().draft,
    }));
    fireEvent.click(await screen.findByRole('button', { name: 'Open lesson' }));
    expect(onTarget).toHaveBeenCalledWith(lessonRef);
    expect(screen.getByText('legacy-tick')).toBeInTheDocument();
    expect(api.saveStudySchedule).not.toHaveBeenCalled();
  });

  it('invalidates the preview after a 409 even when conflict refresh fails', async () => {
    vi.mocked(api.learningStudySchedule).mockResolvedValueOnce(record()).mockRejectedValueOnce(new Error('Offline'));
    vi.mocked(api.saveLearningSchedule).mockRejectedValueOnce(new ApiError(409, 'Changed revision'));
    render(<LearningSchedulePanel {...props()} />); await openCalendar();
    fireEvent.click(screen.getByRole('button', { name: 'Preview updated learning path' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Use this updated path' }));
    await screen.findByRole('alert');
    expect(screen.queryByRole('button', { name: 'Use this updated path' })).not.toBeInTheDocument();
    expect(api.saveLearningSchedule).toHaveBeenCalledTimes(1);
  });

  it('keeps a server-confirmed own attempt review open when the legacy plan needs a fresh preview', async () => {
    vi.mocked(api.learningStudySchedule).mockResolvedValue(record(4, snapshot(reviewRef), true));
    render(<LearningSchedulePanel {...props(4, false)} />); await openCalendar(false);
    const review = await screen.findByRole('button', { name: 'Review my saved attempt' });
    expect(review).toBeEnabled();
    fireEvent.click(review);
    expect(onTarget).toHaveBeenCalledWith(reviewRef);
    expect(api.previewLearningSchedule).not.toHaveBeenCalled();
    expect(api.saveLearningSchedule).not.toHaveBeenCalled();
  });
});

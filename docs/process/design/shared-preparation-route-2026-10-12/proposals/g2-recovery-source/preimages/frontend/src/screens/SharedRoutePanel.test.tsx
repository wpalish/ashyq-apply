import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '@/api/client';
import { setLocale } from '@/lib/i18n';
import type {
  PreparationProgress, ProgramResult, SharedRouteCurrentOutV1, SharedRouteInputV1,
  SharedRoutePreviewOutV1, SharedRouteViewV1, SharedRouteWriteReceiptV1, SharedRouteWriteV1,
} from '@/types';
import { matchesSharedPreview, matchesSharedReceipt, matchesSharedView, SharedRoutePanel } from './SharedRoutePanel';

const hash = (letter: string) => letter.repeat(64);
const candidate = (id: string, decision: 'approved' | 'maybe' = 'approved') => ({ id, user_decision: decision,
  university: `LOCAL ${id}`, program: `Local ${id}` } as ProgramResult);
const progress = (profileId = 'case-a') => ({ profile_id: profileId, attempts: [], attempt_count: 0,
  correct: 0, answered: 0, completed_lesson_ids: [], completed_lessons: [], catalogue_version: 'learning-pack-2026-10-11-v1' } as PreparationProgress);
const empty = (profileId = 'case-a'): SharedRouteCurrentOutV1 => ({ profile_id: profileId, revision: 0, view: null });
const allocation = (input: SharedRouteInputV1): SharedRoutePreviewOutV1['allocation'] => ({
  planner_version: 'shared-route-allocator-v1', planned_on: '2026-10-12', timezone: input.timezone,
  ordered_exam_choices: input.exam_choices, lessons: [], slots: [], capacity: [{ iso_week_monday: '2026-10-12',
    weekly_budget_minutes: input.shared_weekly_minutes, allocated_minutes: 0, remaining_minutes: input.shared_weekly_minutes }],
  unallocated: [], exam_timing: input.exam_choices.map(choice => ({ exam: choice.exam,
    first_exam_on: choice.first_exam_on, retake_on: choice.retake_on,
    certificate_deadline: choice.certificate_deadline, result_wait_days: choice.result_wait_days,
    delivery_days: choice.delivery_days, safety_days: choice.safety_days,
    latest_safe_exam_on: new Date(Date.parse(`${choice.certificate_deadline}T00:00:00Z`)
      - (choice.result_wait_days + choice.delivery_days + choice.safety_days) * 86400000).toISOString().slice(0, 10),
    timing: 'within_buffers' })),
  readiness: 'not_assessed', programme_applicability: 'unknown', digest: hash('a'),
});
const preview = (input: SharedRouteInputV1, profileId = 'case-a', revision = 0): SharedRoutePreviewOutV1 => ({
  profile_id: profileId, expected_shared_revision: revision, legacy_anchor: { technical_revision: 0,
    structural_fingerprint: null, imported_learning_refs_fingerprint: null },
  planned_on: '2026-10-12', expires_on_local_date: '2026-10-12',
  requested_result_ids: input.selected_result_ids, selected_result_ids: input.selected_result_ids,
  selection_source: 'server_verified_owned_explicit', source_fingerprint: hash('b'),
  allocation: allocation(input), preview_fingerprint: hash('c'), review_reasons: [], saved: false,
});
const receipt = (write: SharedRouteWriteV1, profileId = 'case-a'): SharedRouteWriteReceiptV1 => ({
  schema_version: 'shared-route-v1', profile_id: profileId, revision: write.expected_revision + 1,
  expected_revision: write.expected_revision, client_write_uuid: write.client_write_uuid,
  canonical_request_digest: hash('d'), accepted_at: '2026-10-12T08:00:00Z',
  selected_result_ids: write.applicant_input.selected_result_ids, applicant_input: write.applicant_input,
  accepted_planned_on: write.planned_on, catalogue_version: 'learning-pack-2026-10-11-v1',
  planner_version: 'shared-route-allocator-v1', catalogue_snapshot: { version: 'learning-pack-2026-10-11-v1', lessons: [] },
  owned_review_snapshot: [], allocation: allocation(write.applicant_input), allocation_digest: hash('a'),
  source_fingerprint: write.source_fingerprint, source_reference_digests: write.applicant_input.selected_result_ids.map(result_id => ({ result_id, reference_digest: null })),
  preview_fingerprint: write.preview_fingerprint, legacy_anchor: write.legacy_anchor, snapshot_digest: hash('e'),
});
const view = (saved: SharedRouteWriteReceiptV1, access: 'active' | 'expired' = 'active'): SharedRouteViewV1 => ({
  receipt: saved, current_status: { as_of: '2026-10-12T08:01:00Z',
    goal_statuses: saved.selected_result_ids.map(result_id => ({ result_id, state: 'research_locked', safe_reason_code: 'research_locked' })),
    legacy_structure: 'unchanged', imported_refs: 'not_used', content_statuses: [],
    preparation_access: access, needs_review: true,
    review_reasons: saved.selected_result_ids.map(result_id => ({ code: 'goal_research_locked', result_id })) },
  visible_evidence: [],
});
const current = (saved: SharedRouteWriteReceiptV1, access: 'active' | 'expired' = 'active'): SharedRouteCurrentOutV1 => ({
  profile_id: saved.profile_id, revision: saved.revision, view: view(saved, access),
});
function deferred<T>() {
  let resolve!: (value: T) => void; let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const onTarget = vi.fn(); const onActive = vi.fn();
const props = (profileId = 'case-a', allowed = true) => ({ profileId, allowed,
  programmes: [candidate('a'), candidate('b', 'maybe')], progress: progress(profileId),
  isCurrent: () => true, onTarget, onActive });
const change = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const fill = async () => {
  await screen.findByRole('button', { name: 'Preview route' });
  fireEvent.click(screen.getByRole('button', { name: 'Add Saved programme 1' }));
  fireEvent.click(screen.getByRole('button', { name: 'Add Saved programme 2' }));
  change('Planning starts on', '2026-10-12'); change('Minutes available each week across all exams', '120');
  fireEvent.click(screen.getAllByLabelText('Include this personal exam')[0]!);
  change('First exam date', '2026-10-25'); change('Date by which you want the certificate', '2026-11-10');
  change('Days for results', '3'); change('Delivery days', '2'); change('Safety buffer days', '3');
  fireEvent.click(screen.getByLabelText('I entered these personal dates and buffers myself'));
  fireEvent.click(screen.getByLabelText('I chose these programmes, study capacity and personal exam plans explicitly'));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Preview route' })).not.toBeDisabled());
};

beforeEach(() => {
  setLocale('en'); onTarget.mockReset(); onActive.mockReset();
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in G2 synthetic control'); }));
  vi.spyOn(api, 'sharedRouteCurrent').mockResolvedValue(empty());
  vi.spyOn(api, 'previewSharedRoute').mockImplementation(async (_profile, body) => preview(body.applicant_input));
  vi.spyOn(api, 'saveSharedRoute');
  vi.spyOn(api, 'sharedRouteHistory');
  vi.spyOn(api, 'studySchedule'); vi.spyOn(api, 'saveStudySchedule');
  vi.spyOn(api, 'learningStudySchedule'); vi.spyOn(api, 'saveLearningSchedule');
});
afterEach(() => {
  expect(fetch).not.toHaveBeenCalled();
  expect(api.studySchedule).not.toHaveBeenCalled(); expect(api.saveStudySchedule).not.toHaveBeenCalled();
  expect(api.learningStudySchedule).not.toHaveBeenCalled(); expect(api.saveLearningSchedule).not.toHaveBeenCalled();
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals();
});

describe('explicit shared route and own revision fences', () => {
  it('updates accessible route controls in Russian and Kazakh without changing the draft', async () => {
    render(<SharedRoutePanel {...props()} />); await fill();
    await act(async () => setLocale('ru'));
    expect(screen.getByRole('heading', { name: 'Общий маршрут подготовки' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Предпросмотр маршрута' })).toBeVisible();
    await act(async () => setLocale('kk'));
    expect(screen.getByRole('heading', { name: 'Ортақ дайындық бағыты' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Бағытты алдын ала қарау' })).toBeVisible();
    expect(screen.getByLabelText('Барлық емтиханға арналған апталық минут')).toHaveValue(120);
  });

  it('keeps exact result IDs and lets the applicant place SAT first without creating a second budget', async () => {
    render(<SharedRoutePanel {...props()} />); await fill();
    change('Older saved result ID', ' older');
    fireEvent.click(screen.getByRole('button', { name: 'Add saved ID' }));
    expect(screen.getByRole('alert')).toHaveTextContent('without extra spaces');
    fireEvent.click(screen.getAllByLabelText('Include this personal exam')[1]!);
    fireEvent.change(document.getElementById('digital_sat-first')!, { target: { value: '2026-10-27' } });
    fireEvent.change(document.getElementById('digital_sat-deadline')!, { target: { value: '2026-11-15' } });
    fireEvent.change(document.getElementById('digital_sat-result_wait_days')!, { target: { value: '3' } });
    fireEvent.change(document.getElementById('digital_sat-delivery_days')!, { target: { value: '2' } });
    fireEvent.change(document.getElementById('digital_sat-safety_days')!, { target: { value: '3' } });
    fireEvent.click(screen.getAllByLabelText('I entered these personal dates and buffers myself')[1]!);
    fireEvent.click(screen.getByRole('button', { name: 'Make this exam first in the allocation order' }));
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    await waitFor(() => expect(api.previewSharedRoute).toHaveBeenCalledTimes(1));
    const input = vi.mocked(api.previewSharedRoute).mock.calls[0]![1].applicant_input;
    expect(input.selected_result_ids).toEqual(['a', 'b']);
    expect(input.exam_choices.map(choice => [choice.exam, choice.priority])).toEqual([
      ['digital_sat', 0], ['ielts_academic', 1],
    ]);
    expect(input.shared_weekly_minutes).toBe(120);
  });

  it('keeps an A→B→A preview response hidden until a new explicit request returns', async () => {
    const first = deferred<SharedRoutePreviewOutV1>();
    vi.mocked(api.previewSharedRoute).mockImplementationOnce(async (_profile, _body) => first.promise)
      .mockImplementationOnce(async (_profile, body) => preview(body.applicant_input));
    render(<SharedRoutePanel {...props()} />); await fill();
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    change('Minutes available each week across all exams', '130');
    change('Minutes available each week across all exams', '120');
    const originalInput = vi.mocked(api.previewSharedRoute).mock.calls[0]![1].applicant_input;
    await act(async () => first.resolve(preview(originalInput)));
    expect(screen.queryByText('Preview only — nothing has been saved.')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    expect(await screen.findByText('Preview only — nothing has been saved.')).toBeVisible();
    expect(api.previewSharedRoute).toHaveBeenCalledTimes(2);
    expect(api.saveSharedRoute).not.toHaveBeenCalled();
  });

  it('rejects a preview with a foreign case, reordered result IDs or changed weekly capacity', async () => {
    vi.mocked(api.previewSharedRoute).mockImplementation(async (_profile, body) => ({
      ...preview(body.applicant_input), profile_id: 'case-foreign',
    }));
    render(<SharedRoutePanel {...props()} />); await fill();
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('did not match this case');
    expect(screen.queryByText('Preview only — nothing has been saved.')).not.toBeInTheDocument();
    const input = vi.mocked(api.previewSharedRoute).mock.calls[0]![1].applicant_input;
    expect(matchesSharedPreview({ ...preview(input), selected_result_ids: ['b', 'a'] }, 'case-a', input, 0)).toBe(false);
    const altered = preview(input);
    altered.allocation.capacity[0]!.weekly_budget_minutes = 240;
    expect(matchesSharedPreview(altered, 'case-a', input, 0)).toBe(false);
  });

  it('requires explicit exam and minutes for an exact own review and retains its attempt UUID', async () => {
    const attemptId = '9c64ec34-350d-4dfa-a70c-6d44f0c486eb';
    const ownProgress = { ...progress(), attempts: [{ attempt_id: attemptId, lesson_id: 'ielts-reading-1',
      version: 'starter-2026-10-11-v1', profile_id: 'case-a' }] } as PreparationProgress;
    render(<SharedRoutePanel {...props()} progress={ownProgress} />); await fill();
    fireEvent.click(screen.getByText('My saved attempt reviews'));
    fireEvent.click(screen.getAllByRole('button', { name: 'Add own review' })[0]!);
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    expect(api.previewSharedRoute).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('Exam stream'), { target: { value: 'ielts_academic' } });
    change('Minutes for this review', '35');
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    await waitFor(() => expect(api.previewSharedRoute).toHaveBeenCalledTimes(1));
    const review = vi.mocked(api.previewSharedRoute).mock.calls[0]![1].applicant_input.own_reviews[0]!;
    expect(review.ref).toEqual({ kind: 'attempt_review', id: `attempt:${attemptId}`,
      attempt_id: attemptId, lesson_id: 'ielts-reading-1', content_version: 'starter-2026-10-11-v1' });
    expect(review.planned_minutes).toBe(35);
  });

  it('retries an uncertain PUT with the identical UUID and body, then trusts only a matching ACK', async () => {
    let accepted: SharedRouteWriteReceiptV1 | null = null;
    vi.mocked(api.sharedRouteCurrent).mockImplementation(async () => accepted ? current(accepted) : empty());
    vi.mocked(api.saveSharedRoute).mockRejectedValueOnce(new ApiError(0, 'network outcome unknown'))
      .mockImplementationOnce(async (_profile, body) => { accepted = receipt(body); return accepted; });
    render(<SharedRoutePanel {...props()} />); await fill();
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    await screen.findByText('Preview only — nothing has been saved.');
    fireEvent.click(screen.getByRole('button', { name: 'Save this exact preview' }));
    expect((await screen.findAllByText(/The outcome is uncertain/))[0]!).toBeVisible();
    expect(screen.queryByText('Accepted revision 1')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry original request' }));
    await waitFor(() => expect(screen.getByText('Accepted revision 1')).toBeVisible());
    const [first, second] = vi.mocked(api.saveSharedRoute).mock.calls;
    expect(second).toEqual(first); expect(first![1].client_write_uuid).toMatch(/^[0-9a-f-]{36}$/);
    expect(onActive).toHaveBeenCalledWith(true);
  });

  it('reconciles an unknown outcome only when a fresh own GET carries the exact original receipt', async () => {
    let accepted: SharedRouteWriteReceiptV1 | null = null;
    vi.mocked(api.sharedRouteCurrent).mockImplementation(async () => accepted ? current(accepted) : empty());
    vi.mocked(api.saveSharedRoute).mockImplementation(async (_profile, body) => {
      accepted = receipt(body); throw new ApiError(503, 'write unconfirmed');
    });
    render(<SharedRoutePanel {...props()} />); await fill();
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    await screen.findByText('Preview only — nothing has been saved.');
    fireEvent.click(screen.getByRole('button', { name: 'Save this exact preview' }));
    expect((await screen.findAllByText(/The outcome is uncertain/))[0]!).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Refresh saved route' }));
    await waitFor(() => expect(screen.getByText('Accepted revision 1')).toBeVisible());
    expect(api.saveSharedRoute).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('button', { name: 'Retry original request' })).not.toBeInTheDocument();
  });

  it('retains the original 409 intent and requires a fresh preview before any new save', async () => {
    vi.mocked(api.saveSharedRoute).mockRejectedValueOnce(new ApiError(409, 'revision changed'));
    render(<SharedRoutePanel {...props()} />); await fill();
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    await screen.findByText('Preview only — nothing has been saved.');
    fireEvent.click(screen.getByRole('button', { name: 'Save this exact preview' }));
    expect((await screen.findAllByText(/planning inputs changed elsewhere/i))[0]!).toBeVisible();
    expect(screen.queryByText('Preview only — nothing has been saved.')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry original request' })).toBeVisible();
    expect(api.saveSharedRoute).toHaveBeenCalledTimes(1);
  });

  it('does not show a saved plan when PUT returns a mismatched receipt', async () => {
    vi.mocked(api.saveSharedRoute).mockImplementation(async (_profile, body) => ({
      ...receipt(body), selected_result_ids: ['b', 'a'],
    }));
    render(<SharedRoutePanel {...props()} />); await fill();
    fireEvent.click(screen.getByRole('button', { name: 'Preview route' }));
    await screen.findByText('Preview only — nothing has been saved.');
    fireEvent.click(screen.getByRole('button', { name: 'Save this exact preview' }));
    expect((await screen.findAllByText(/The outcome is uncertain/))[0]!).toBeVisible();
    expect(screen.queryByText('Accepted revision 1')).not.toBeInTheDocument();
    expect(onActive).not.toHaveBeenCalledWith(true);
  });

  it('keeps expired own reviews open while exact lessons stay gated and missing reviews stay disabled', async () => {
    const attemptId = 'aab34500-718e-4efa-a835-c50a5eb0dceb';
    const input: SharedRouteInputV1 = { schema_version: 'shared-route-v1', selected_result_ids: ['a', 'b'],
      starts_on: '2026-10-12', timezone: 'Asia/Almaty', study_days: [0], shared_weekly_minutes: 120,
      exam_choices: [{ exam: 'ielts_academic', priority: 0, first_exam_on: '2026-10-25', retake_on: null,
        certificate_deadline: '2026-11-10', result_wait_days: 3, delivery_days: 2, safety_days: 3,
        personal_targets: null, confirmed_exam_dates_and_buffers: true }], own_reviews: [], confirmed_shared_planning_inputs: true };
    const write: SharedRouteWriteV1 = { applicant_input: input, expected_revision: 0,
      client_write_uuid: '9c64ec34-350d-4dfa-a70c-6d44f0c486eb', preview_fingerprint: hash('c'),
      source_fingerprint: hash('b'), legacy_anchor: { technical_revision: 0, structural_fingerprint: null,
        imported_learning_refs_fingerprint: null }, planned_on: '2026-10-12' };
    const saved = receipt(write);
    saved.allocation.slots = [{ occurrence_id: hash('f'), action_id: hash('1'),
      ref: { kind: 'lesson', id: 'lesson:ielts-reading-1:starter-2026-10-11-v1',
        lesson_id: 'ielts-reading-1', content_version: 'starter-2026-10-11-v1' },
      exam: 'ielts_academic', kind: 'lesson', local_date: '2026-10-13', planned_minutes: 20,
      origin: 'personal_practice', completion: 'not_projected' }];
    const reviewRef = { kind: 'attempt_review' as const, id: `attempt:${attemptId}`,
      attempt_id: attemptId, lesson_id: 'ielts-reading-1', content_version: 'starter-2026-10-11-v1' };
    saved.allocation.slots.push({ occurrence_id: hash('2'), action_id: hash('3'), ref: reviewRef,
      exam: 'ielts_academic', kind: 'attempt_review', local_date: '2026-10-13', planned_minutes: 30,
      origin: 'personal_practice', completion: 'not_projected' });
    const lockedView = view(saved, 'expired');
    lockedView.current_status.content_statuses = [{ action_id: hash('1'), state: 'available' },
      { action_id: hash('3'), state: 'available' }];
    vi.mocked(api.sharedRouteCurrent).mockResolvedValue({ profile_id: 'case-a', revision: 1, view: lockedView });
    vi.mocked(api.sharedRouteHistory).mockResolvedValue(lockedView);
    render(<SharedRoutePanel {...props('case-a', false)} />);
    expect(await screen.findByText('Current saved route · Revision 1')).toBeVisible();
    expect(screen.getByText('One shared weekly budget: 120 minutes per week')).toBeVisible();
    expect(screen.queryByText(/LOCAL a/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Preview route' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Open exact lesson' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Open my exact review' }));
    expect(onTarget).toHaveBeenCalledTimes(1);
    expect(onTarget).toHaveBeenLastCalledWith(reviewRef);
    fireEvent.click(screen.getByText('Earlier saved revisions'));
    change('Revision', '1'); fireEvent.click(screen.getByRole('button', { name: 'Open revision' }));
    expect(await screen.findByText('Earlier saved route · Revision 1')).toBeVisible();
    expect(screen.getAllByRole('button', { name: 'Open exact lesson' }).every(button => button.hasAttribute('disabled'))).toBe(true);
    fireEvent.click(screen.getAllByRole('button', { name: 'Open my exact review' })[1]!);
    expect(onTarget).toHaveBeenCalledTimes(2);
    expect(onTarget).toHaveBeenLastCalledWith(reviewRef);
    expect(api.saveSharedRoute).not.toHaveBeenCalled();
    cleanup();
    lockedView.current_status.content_statuses[1]!.state = 'review_unavailable';
    render(<SharedRoutePanel {...props('case-a', false)} />);
    expect(await screen.findByRole('button', { name: 'Open my exact review' })).toBeDisabled();
  });

  it('rejects foreign current body and an ACK with another case or input', async () => {
    vi.mocked(api.sharedRouteCurrent).mockResolvedValue(empty('case-foreign'));
    render(<SharedRoutePanel {...props()} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('did not match this case');
    expect(onActive).not.toHaveBeenCalledWith(true);
    const input = { schema_version: 'shared-route-v1', selected_result_ids: ['a', 'b'],
      starts_on: '2026-10-12', timezone: 'Asia/Almaty', study_days: [0], shared_weekly_minutes: 120,
      exam_choices: [], own_reviews: [], confirmed_shared_planning_inputs: true } as SharedRouteInputV1;
    const write = { applicant_input: input, expected_revision: 0, client_write_uuid: '9c64ec34-350d-4dfa-a70c-6d44f0c486eb',
      preview_fingerprint: hash('c'), source_fingerprint: hash('b'),
      legacy_anchor: { technical_revision: 0, structural_fingerprint: null, imported_learning_refs_fingerprint: null },
      planned_on: '2026-10-12' } as SharedRouteWriteV1;
    expect(matchesSharedReceipt(receipt(write, 'case-foreign'), 'case-a', write)).toBe(false);
    expect(matchesSharedReceipt({ ...receipt(write), applicant_input: { ...input, selected_result_ids: ['b', 'a'] } }, 'case-a', write)).toBe(false);
    expect(matchesSharedView(view(receipt(write, 'case-foreign')), 'case-a', 1)).toBe(false);
  });

  it('discards a former case read after a keyed case replacement', async () => {
    const old = deferred<SharedRouteCurrentOutV1>();
    vi.mocked(api.sharedRouteCurrent).mockReturnValueOnce(old.promise).mockResolvedValueOnce(empty('case-b'));
    const rendered = render(<SharedRoutePanel key="case-a" {...props('case-a')} />);
    rendered.rerender(<SharedRoutePanel key="case-b" {...props('case-b')} />);
    await act(async () => old.resolve(empty('case-a')));
    await waitFor(() => expect(api.sharedRouteCurrent).toHaveBeenCalledWith('case-b'));
    expect(screen.queryByText('Current saved route · Revision 1')).not.toBeInTheDocument();
    expect(onActive).not.toHaveBeenCalledWith(true);
  });
});

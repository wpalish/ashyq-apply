import { useCallback, useContext, useEffect, useRef, useState, useSyncExternalStore, type CSSProperties } from 'react';
import { api, ApiError } from '@/api/client';
import { Notice, Panel } from '@/components/primitives';
import { subscribe, t, type MessageKey } from '@/lib/i18n';
import { DraftIdentityContext } from '@/lib/draftIdentity';
import {
  acknowledgeSharedRouteRecovery, newSharedRouteRecovery, readSharedRouteRecovery,
  recoveryCanonical, resetSharedRouteRecovery, sharedRouteRecoveryBinding, writeSharedRouteRecovery,
  type RecoveryBinding, type SharedExamDraft as ExamDraft, type SharedManualReview,
  type SharedPendingWrite as PendingWrite, type SharedRouteDraft as Draft, type SharedRouteLeaveRisk,
  type SharedRouteRecovery,
} from '@/lib/sharedRouteRecovery';
import type {
  PreparationProgress, ProgramResult, SharedExam, SharedExamChoice,
  SharedLearningRef, SharedOwnReview, SharedRouteCurrentOutV1, SharedRouteInputV1,
  SharedRoutePreviewOutV1, SharedRouteViewV1, SharedRouteWriteReceiptV1, SharedRouteWriteV1,
} from '@/types';

interface Props {
  profileId: string;
  programmes: ProgramResult[]; // Latest run suggestions only, never an exhaustive own-result inventory.
  progress: PreparationProgress;
  allowed: boolean;
  isCurrent: () => boolean;
  onTarget: (ref: SharedLearningRef) => void;
  onActive: (active: boolean) => void;
  onLeaveRisk?: SharedRouteLeaveRisk;
}

type PreparedPreview = { body: SharedRoutePreviewOutV1; input: SharedRouteInputV1; generation: number };

const weekdays = [0, 1, 2, 3, 4, 5, 6];
const examLabel = (exam: SharedExam) => exam === 'ielts_academic' ? t('shared.ielts') : t('shared.sat');
const same = (a: unknown, b: readonly string[]) => Array.isArray(a) && a.length === b.length
  && a.every((value, index) => value === b[index]);
const canonical = (value: unknown): string => JSON.stringify(value, (_key, item) => item && typeof item === 'object' && !Array.isArray(item)
  ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b))) : item) ?? '';
const integer = (value: string, min: number, max: number): number | null => {
  if (!/^(0|[1-9][0-9]*)$/.test(value)) return null;
  const result = Number(value);
  return Number.isSafeInteger(result) && result >= min && result <= max ? result : null;
};
const isoDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value)
  && !Number.isNaN(Date.parse(`${value}T00:00:00Z`))
  && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
const weekday = (value: string) => (new Date(`${value}T00:00:00Z`).getUTCDay() + 6) % 7;
const subtractDays = (value: string, days: number) => new Date(Date.parse(`${value}T00:00:00Z`) - days * 86400000).toISOString().slice(0, 10);
const initialExam = (exam: SharedExam): ExamDraft => ({
  exam, enabled: false, first_exam_on: '', retake_on: '', certificate_deadline: '',
  result_wait_days: '', delivery_days: '', safety_days: '', confirmed: false, targets: {},
});
const initialDraft = (): Draft => ({
  ids: [], starts_on: '', timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
  days: [0, 1, 2, 3, 4], weekly: '',
  exams: [initialExam('ielts_academic'), initialExam('digital_sat')], reviews: [], confirmed: false,
});
const canName = (item: ProgramResult) => item.user_decision === 'approved' || item.user_decision === 'maybe';
const targetKeys: Record<SharedExam, readonly string[]> = {
  ielts_academic: ['overall', 'listening', 'reading', 'writing', 'speaking'],
  digital_sat: ['total', 'math', 'reading_writing'],
};
const targetLabel: Record<string, MessageKey> = {
  overall: 'shared.targetOverall', listening: 'shared.targetListening', reading: 'shared.targetReading',
  writing: 'shared.targetWriting', speaking: 'shared.targetSpeaking', total: 'shared.targetTotal',
  math: 'shared.targetMath', reading_writing: 'shared.targetReadingWriting',
};
const stateLabel = (state: string): string => {
  const keys: Record<string, MessageKey> = {
    eligible: 'shared.stateEligible', decision_changed: 'shared.stateDecision',
    result_unavailable: 'shared.stateMissing', research_locked: 'shared.stateLocked',
    source_changed: 'shared.stateSource', evidence_unknown: 'shared.stateUnknown',
    unchanged: 'shared.stateUnchanged', changed: 'shared.stateChanged', unknown: 'shared.stateUnknown',
    not_used: 'shared.stateNotUsed', available: 'shared.stateAvailable',
    version_unavailable: 'shared.stateVersion', review_unavailable: 'shared.stateReview',
    within_buffers: 'shared.timingWithin', at_risk: 'shared.timingRisk', deadline_passed: 'shared.timingPassed',
    insufficient_capacity: 'shared.reasonCapacity', window_elapsed: 'shared.reasonWindow',
    too_long_for_day: 'shared.reasonDay', too_long_for_week: 'shared.reasonWeek',
    slot_limit: 'shared.reasonLimit',
  };
  return t(keys[state] ?? 'shared.stateUnknown');
};
const reasonLabel = (code: string): string => {
  if (code.startsWith('goal_')) return stateLabel(code.slice(5));
  if (code.startsWith('legacy_structure_')) return `${t('shared.legacyStatus')} ${stateLabel(code.slice(17))}`;
  if (code.startsWith('imported_refs_')) return `${t('shared.contentStatus')} ${stateLabel(code.slice(14))}`;
  if (code === 'content_version_unavailable') return stateLabel('version_unavailable');
  if (code === 'own_review_unavailable') return stateLabel('review_unavailable');
  return stateLabel('unknown');
};
const meaningfulError = (error: unknown) => error instanceof Error ? error.message : t('shared.error');
const safeReference = (ref: SharedLearningRef): boolean => ref?.kind === 'lesson'
  ? !!ref.id && !!ref.lesson_id && !!ref.content_version
  : ref?.kind === 'attempt_review' && !!ref.id && !!ref.attempt_id && !!ref.lesson_id && !!ref.content_version;

/** The server validates ownership. The browser still fences the exact case, order, intent and response body. */
export function matchesSharedPreview(
  out: SharedRoutePreviewOutV1, profileId: string, input: SharedRouteInputV1, expectedRevision: number,
): boolean {
  return out.profile_id === profileId && out.saved === false
    && out.selection_source === 'server_verified_owned_explicit'
    && out.expected_shared_revision === expectedRevision
    && same(out.requested_result_ids, input.selected_result_ids)
    && same(out.selected_result_ids, input.selected_result_ids)
    && out.allocation?.digest?.length === 64 && out.preview_fingerprint?.length === 64
    && out.source_fingerprint?.length === 64
    && out.planned_on === out.allocation.planned_on
    && out.expires_on_local_date === out.planned_on
    && out.allocation.readiness === 'not_assessed' && out.allocation.programme_applicability === 'unknown'
    && Array.isArray(out.allocation.slots)
    && out.allocation.slots.every(slot => {
      const exam = input.exam_choices.find(choice => choice.exam === slot.exam);
      if (!exam || !isoDate(slot.local_date) || !safeReference(slot.ref)
        || slot.kind !== slot.ref.kind || slot.local_date < input.starts_on || slot.local_date < out.planned_on
        || !input.study_days.includes(weekday(slot.local_date))) return false;
      const windowEnd = slot.kind === 'lesson' ? exam.first_exam_on : exam.retake_on ?? exam.first_exam_on;
      return slot.local_date < windowEnd && slot.planned_minutes > 0;
    })
    && out.allocation.ordered_exam_choices?.length === input.exam_choices.length
    && canonical(out.allocation.ordered_exam_choices) === canonical(input.exam_choices)
    && out.allocation.exam_timing?.length === input.exam_choices.length
    && out.allocation.exam_timing.every((timing, index) => {
      const choice = input.exam_choices[index];
      return !!choice && timing.exam === choice.exam && timing.first_exam_on === choice.first_exam_on
        && timing.retake_on === choice.retake_on && timing.certificate_deadline === choice.certificate_deadline
        && timing.result_wait_days === choice.result_wait_days && timing.delivery_days === choice.delivery_days
        && timing.safety_days === choice.safety_days
        && timing.latest_safe_exam_on === subtractDays(choice.certificate_deadline,
          choice.result_wait_days + choice.delivery_days + choice.safety_days);
    })
    && out.allocation.capacity?.every(week => week.weekly_budget_minutes === input.shared_weekly_minutes) === true
    && out.allocation.timezone === input.timezone;
}

export function matchesSharedReceipt(receipt: SharedRouteWriteReceiptV1, profileId: string, write: SharedRouteWriteV1): boolean {
  return receipt.schema_version === 'shared-route-v1' && receipt.profile_id === profileId
    && receipt.expected_revision === write.expected_revision
    && receipt.revision === write.expected_revision + 1
    && receipt.client_write_uuid === write.client_write_uuid
    && same(receipt.selected_result_ids, write.applicant_input.selected_result_ids)
    && canonical(receipt.applicant_input) === canonical(write.applicant_input)
    && receipt.source_fingerprint === write.source_fingerprint
    && receipt.preview_fingerprint === write.preview_fingerprint
    && canonical(receipt.legacy_anchor) === canonical(write.legacy_anchor)
    && receipt.accepted_planned_on === write.planned_on
    && receipt.allocation?.planned_on === write.planned_on
    && receipt.allocation?.timezone === write.applicant_input.timezone
    && canonical(receipt.allocation?.ordered_exam_choices) === canonical(write.applicant_input.exam_choices)
    && receipt.allocation?.capacity?.every(week => week.weekly_budget_minutes === write.applicant_input.shared_weekly_minutes) === true
    && receipt.allocation_digest === receipt.allocation?.digest
    && receipt.canonical_request_digest?.length === 64
    && same(receipt.source_reference_digests?.map(item => item.result_id), write.applicant_input.selected_result_ids)
    && receipt.snapshot_digest?.length === 64
    && receipt.allocation?.slots?.every(slot => safeReference(slot.ref)) === true;
}

export function matchesSharedView(view: SharedRouteViewV1, profileId: string, revision: number): boolean {
  const receipt = view.receipt;
  const actions = [...(receipt.allocation?.slots ?? []), ...(receipt.allocation?.unallocated ?? [])];
  return receipt.profile_id === profileId && receipt.revision === revision
    && receipt.schema_version === 'shared-route-v1'
    && receipt.expected_revision + 1 === receipt.revision
    && same(receipt.selected_result_ids, receipt.applicant_input?.selected_result_ids ?? [])
    && receipt.allocation?.planned_on === receipt.accepted_planned_on
    && receipt.allocation?.timezone === receipt.applicant_input?.timezone
    && canonical(receipt.allocation?.ordered_exam_choices) === canonical(receipt.applicant_input?.exam_choices)
    && receipt.allocation?.capacity?.every(week => week.weekly_budget_minutes === receipt.applicant_input.shared_weekly_minutes) === true
    && same(receipt.source_reference_digests?.map(item => item.result_id), receipt.selected_result_ids)
    && receipt.allocation_digest === receipt.allocation?.digest
    && receipt.snapshot_digest?.length === 64
    && actions.every(action => safeReference(action.ref))
    && same(view.current_status?.goal_statuses?.map(item => item.result_id), receipt.selected_result_ids)
    && same(view.current_status?.content_statuses?.map(item => item.action_id), actions.map(item => item.action_id))
    && Array.isArray(view.visible_evidence)
    && (!view.current_status.goal_statuses.some(item => item.state === 'research_locked') || view.visible_evidence.length === 0)
    && view.visible_evidence.every(graph => graph.profile_id === profileId
      && graph.selected_result_ids.length === 1 && receipt.selected_result_ids.includes(graph.selected_result_ids[0]!));
}

function buildInput(draft: Draft): SharedRouteInputV1 | null {
  const ids = draft.ids;
  if (ids.length < 2 || ids.length > 20 || new Set(ids).size !== ids.length
    || ids.some(id => !id || id.length > 32 || id !== id.trim())
    || !isoDate(draft.starts_on) || !draft.timezone || draft.timezone !== draft.timezone.trim() || draft.timezone.length > 80
    || draft.days.length < 1 || new Set(draft.days).size !== draft.days.length
    || draft.days.some(day => !weekdays.includes(day)) || !draft.confirmed) return null;
  const weekly = integer(draft.weekly, 30, 1260);
  if (weekly === null) return null;
  const choices: SharedExamChoice[] = [];
  for (const exam of draft.exams.filter(item => item.enabled)) {
    const wait = integer(exam.result_wait_days, 1, 60);
    const delivery = integer(exam.delivery_days, 0, 30);
    const safety = integer(exam.safety_days, 0, 30);
    if (wait === null || delivery === null || safety === null || !exam.confirmed
      || !isoDate(exam.first_exam_on) || !isoDate(exam.certificate_deadline)
      || (exam.retake_on && !isoDate(exam.retake_on))
      || draft.starts_on > exam.first_exam_on || exam.first_exam_on >= exam.certificate_deadline
      || (exam.retake_on && (exam.first_exam_on >= exam.retake_on || exam.retake_on >= exam.certificate_deadline))) return null;
    const targets: Record<string, number> = {};
    for (const key of targetKeys[exam.exam]) {
      const raw = exam.targets[key]?.trim();
      if (!raw) continue;
      const number = Number(raw);
      const valid = exam.exam === 'ielts_academic'
        ? Number.isFinite(number) && number >= (key === 'overall' ? 0.5 : 0)
          && number <= 9 && number * 2 === Math.trunc(number * 2)
        : Number.isSafeInteger(number) && number >= (key === 'total' ? 400 : 200)
          && number <= (key === 'total' ? 1600 : 800);
      if (!valid) return null;
      targets[key] = number;
    }
    if (exam.exam === 'digital_sat' && targets.total !== undefined && targets.math !== undefined
      && targets.reading_writing !== undefined && targets.math + targets.reading_writing < targets.total) return null;
    choices.push({ exam: exam.exam, priority: choices.length, first_exam_on: exam.first_exam_on,
      retake_on: exam.retake_on || null, certificate_deadline: exam.certificate_deadline,
      result_wait_days: wait, delivery_days: delivery, safety_days: safety,
      personal_targets: Object.keys(targets).length ? targets : null,
      confirmed_exam_dates_and_buffers: true });
  }
  if (choices.length < 1 || choices.length > 2) return null;
  const maxDate = choices.map(item => item.certificate_deadline).sort().at(-1)!;
  if ((Date.parse(`${maxDate}T00:00:00Z`) - Date.parse(`${draft.starts_on}T00:00:00Z`)) / 86400000 > 365) return null;
  const reviews: SharedOwnReview[] = [];
  for (const review of draft.reviews) {
    const minutes = integer(review.minutes, 1, 1260);
    if (minutes === null || (review.exam !== 'ielts_academic' && review.exam !== 'digital_sat')
      || !choices.some(choice => choice.exam === review.exam)
      || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(review.attempt_id)
      || !review.lesson_id || !review.content_version) return null;
    reviews.push({ ref: { kind: 'attempt_review', id: `attempt:${review.attempt_id}`,
      attempt_id: review.attempt_id, lesson_id: review.lesson_id, content_version: review.content_version },
      exam: review.exam, planned_minutes: minutes });
  }
  if (reviews.length > 400 || new Set(reviews.map(item => item.ref.attempt_id)).size !== reviews.length) return null;
  return { schema_version: 'shared-route-v1', selected_result_ids: ids,
    starts_on: draft.starts_on, timezone: draft.timezone, study_days: [...draft.days].sort(),
    shared_weekly_minutes: weekly, exam_choices: choices, own_reviews: reviews,
    confirmed_shared_planning_inputs: true };
}

const actionLabel = (ref: SharedLearningRef) => ref.kind === 'lesson' ? t('shared.lesson') : t('shared.review');
const ExactReference = ({ learningRef: item }: { learningRef: SharedLearningRef }) => <details>
  <summary>{t('shared.reference')}</summary>
  <p className="xs" style={{ overflowWrap: 'anywhere' }}>{t('shared.lessonId')}: {item.lesson_id}</p>
  <p className="xs" style={{ overflowWrap: 'anywhere' }}>{t('shared.contentVersion')}: {item.content_version}</p>
  {item.kind === 'attempt_review' && <p className="xs" style={{ overflowWrap: 'anywhere' }}>{t('shared.attemptId')}: {item.attempt_id}</p>}
</details>;

export function SharedRoutePanel({ profileId, programmes, progress, allowed, isCurrent, onTarget, onActive, onLeaveRisk }: Props) {
  useSyncExternalStore(subscribe, () => t('shared.title'));
  const identity = useContext(DraftIdentityContext);
  const [draft, setDraft] = useState<Draft>(initialDraft);
  const [manualId, setManualId] = useState('');
  const [manualReview, setManualReview] = useState<SharedManualReview>({ attempt_id: '', lesson_id: '', content_version: '' });
  const [current, setCurrent] = useState<SharedRouteCurrentOutV1 | null>(null);
  const [historyRevision, setHistoryRevision] = useState('');
  const [history, setHistory] = useState<SharedRouteViewV1 | null>(null);
  const [preview, setPreview] = useState<PreparedPreview | null>(null);
  const [pending, setPending] = useState<PendingWrite | null>(null);
  const pendingRef = useRef<PendingWrite | null>(null);
  const [ack, setAck] = useState<SharedRouteWriteReceiptV1 | null>(null);
  const [busy, setBusy] = useState<'read' | 'preview' | 'save' | 'history' | null>('read');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const mounted = useRef(true);
  const generation = useRef(0);
  const readIntent = useRef(0);
  const previewIntent = useRef(0);
  const writeIntent = useRef(0);
  const historyIntent = useRef(0);
  const acceptedRevision = useRef(0);

  const draftRef = useRef(draft);
  const manualIdRef = useRef(manualId);
  const manualReviewRef = useRef(manualReview);
  const bindingRef = useRef<RecoveryBinding | null>(null);
  const journal = useRef<SharedRouteRecovery | null>(null);
  const journalRaw = useRef<string | null>(null);
  const blockedJournal = useRef(false);
  const [recoveryWarning, setRecoveryWarning] = useState('');
  const [restored, setRestored] = useState(false);
  const [localDirty, setLocalDirty] = useState(false);
  const dirtyRef = useRef(false);
  const leaveToken = useRef(Symbol('shared-route-recovery'));
  const publishRisk = useCallback(() => {
    onLeaveRisk?.(leaveToken.current, dirtyRef.current || !!pendingRef.current);
  }, [onLeaveRisk]);
  const persist = useCallback((record: SharedRouteRecovery): boolean => {
    journal.current = record;
    if (!mounted.current || !isCurrent() || blockedJournal.current) {
      setRecoveryWarning(t('shared.recoveryUnavailable')); publishRisk(); return false;
    }
    const out = writeSharedRouteRecovery(bindingRef.current, record, journalRaw.current);
    if (out.ok) { journal.current = out.record; journalRaw.current = out.raw; setRecoveryWarning(''); }
    else setRecoveryWarning(out.reason === 'changed' || out.reason === 'invalid'
      ? t('shared.recoveryInvalid') : t('shared.recoveryUnavailable'));
    dirtyRef.current = record.dirty; setLocalDirty(record.dirty); publishRisk(); return out.ok;
  }, [isCurrent, publishRisk]);
  const acknowledge = useCallback((receipt: SharedRouteWriteReceiptV1, body: SharedRouteWriteV1) => {
    const active = pendingRef.current;
    const latest = journal.current;
    if (!active || !latest || recoveryCanonical(active.body) !== recoveryCanonical(body)) return false;
    const retired = acknowledgeSharedRouteRecovery(bindingRef.current, latest, body, journalRaw.current);
    if (!retired.ok) {
      // The receipt is real, but a different/failed browser journal must not be reported retired.
      const unresolved = { ...active, state: 'uncertain' as const, dispatched: true };
      pendingRef.current = unresolved; setPending(unresolved);
      journal.current = { ...latest, pending: unresolved };
      setRecoveryWarning(t('shared.recoveryCleanup')); publishRisk(); return false;
    }
    journal.current = retired.record; journalRaw.current = retired.raw;
    pendingRef.current = null; setPending(null); setAck(receipt); setPreview(null);
    dirtyRef.current = retired.record.dirty; setLocalDirty(retired.record.dirty); setRecoveryWarning('');
    setNotice(retired.record.dirty ? t('shared.recoveryNewer') : t('shared.saved'));
    publishRisk(); return true;
  }, [publishRisk]);
  const readCurrent = useCallback(async () => {
    const intent = ++readIntent.current;
    setBusy('read'); setError('');
    try {
      const out = await api.sharedRouteCurrent(profileId);
      if (!mounted.current || !isCurrent() || intent !== readIntent.current) return;
      if (out.profile_id !== profileId || out.view === undefined
        || !Number.isSafeInteger(out.revision) || out.revision < acceptedRevision.current
        || (out.view === null && out.revision !== 0)
        || (out.view && !matchesSharedView(out.view, profileId, out.revision))) {
        throw new Error(t('shared.mismatch'));
      }
      setPreview(old => old && old.body.expected_shared_revision === out.revision ? old : null);
      setCurrent(out); onActive(!!out.view);
      const unresolved = pendingRef.current;
      if (unresolved && out.view) {
        let accepted = out.view.receipt;
        const expected = unresolved.body.expected_revision + 1;
        // One exact free own history read; no scan, reallocation, preview or automatic PUT.
        if (!matchesSharedReceipt(accepted, profileId, unresolved.body) && out.revision > expected) {
          const historical = await api.sharedRouteHistory(profileId, expected);
          if (!mounted.current || !isCurrent() || intent !== readIntent.current) return;
          if (!matchesSharedView(historical, profileId, expected)) throw new Error(t('shared.mismatch'));
          accepted = historical.receipt;
        }
        if (matchesSharedReceipt(accepted, profileId, unresolved.body)) {
          acceptedRevision.current = Math.max(acceptedRevision.current, accepted.revision);
          acknowledge(accepted, unresolved.body);
        }
      }
    } catch (cause) { if (mounted.current && isCurrent() && intent === readIntent.current) setError(meaningfulError(cause)); }
    finally { if (mounted.current && isCurrent() && intent === readIntent.current) setBusy(null); }
  }, [profileId, isCurrent, onActive, acknowledge]);
  useEffect(() => {
    mounted.current = true;
    bindingRef.current = sharedRouteRecoveryBinding(identity, profileId);
    const stored = readSharedRouteRecovery(bindingRef.current);
    if (stored.state === 'valid') {
      const recovered = stored.record.pending?.state === 'sending'
        ? { ...stored.record, pending: { ...stored.record.pending, state: 'uncertain' as const } } : stored.record;
      journal.current = recovered; journalRaw.current = stored.raw; blockedJournal.current = false;
      draftRef.current = recovered.draft; manualIdRef.current = recovered.manual_id; manualReviewRef.current = recovered.manual_review;
      generation.current = recovered.draft_generation; pendingRef.current = recovered.pending;
      setDraft(recovered.draft); setManualId(recovered.manual_id); setManualReview(recovered.manual_review);
      setPending(recovered.pending); dirtyRef.current = recovered.dirty; setLocalDirty(recovered.dirty); setRestored(recovered.dirty || !!recovered.pending);
    } else {
      journalRaw.current = stored.raw; blockedJournal.current = stored.state === 'invalid';
      journal.current = bindingRef.current ? newSharedRouteRecovery(bindingRef.current, draftRef.current) : null;
      if (stored.state !== 'empty') setRecoveryWarning(stored.state === 'invalid' ? t('shared.recoveryInvalid') : t('shared.recoveryUnavailable'));
    }
    publishRisk(); void readCurrent();
    const token = leaveToken.current;
    return () => {
      mounted.current = false; ++readIntent.current; ++previewIntent.current; ++writeIntent.current; ++historyIntent.current;
      onLeaveRisk?.(token, false);
    };
  }, [readCurrent, identity, profileId, publishRisk, onLeaveRisk]);

  const edit = (next: (old: Draft) => Draft, manual?: { id?: string; review?: SharedManualReview }) => {
    if (!mounted.current || !isCurrent()) return;
    const value = next(draftRef.current); // Compute outside React updater; journal side effects happen once.
    const id = manual?.id ?? manualIdRef.current; const review = manual?.review ?? manualReviewRef.current;
    ++generation.current; ++previewIntent.current;
    draftRef.current = value; manualIdRef.current = id; manualReviewRef.current = review;
    setDraft(value); setManualId(id); setManualReview(review); setPreview(null); setNotice(''); setError('');
    dirtyRef.current = true; setLocalDirty(true); setBusy(old => old === 'preview' ? null : old);
    if (journal.current) persist({ ...journal.current, draft: value, manual_id: id, manual_review: review,
      draft_generation: generation.current, dirty: true, pending: pendingRef.current });
    else { setRecoveryWarning(t('shared.recoveryUnavailable')); onLeaveRisk?.(leaveToken.current, true); }
  };
  const resetLocal = () => {
    if (!isCurrent()) return;
    const stored = readSharedRouteRecovery(bindingRef.current);
    if (!window.confirm(t('shared.recoveryResetConfirm'))) return;
    if (stored.state === 'unavailable' || !resetSharedRouteRecovery(bindingRef.current, stored.raw)) {
      setRecoveryWarning(t('shared.recoveryUnavailable')); return;
    }
    const value = initialDraft(); const review = { attempt_id: '', lesson_id: '', content_version: '' };
    draftRef.current = value; manualIdRef.current = ''; manualReviewRef.current = review;
    journal.current = bindingRef.current ? newSharedRouteRecovery(bindingRef.current, value) : null;
    journalRaw.current = null; blockedJournal.current = false; generation.current = 0; ++previewIntent.current; ++writeIntent.current;
    pendingRef.current = null; setDraft(value); setManualId(''); setManualReview(review); setPending(null); setPreview(null);
    dirtyRef.current = false; setLocalDirty(false); setRecoveryWarning(''); setNotice(''); setError(''); setRestored(false); publishRisk();
  };
  const changeExam = (exam: SharedExam, change: Partial<ExamDraft>) => edit(old => ({ ...old,
    exams: old.exams.map(item => item.exam === exam ? { ...item, ...change } : item),
  }));
  const addId = (raw: string) => {
    const id = raw;
    if (!id || id !== id.trim() || id.length > 32 || draft.ids.includes(id) || draft.ids.length >= 20) {
      setError(t('shared.invalidId')); return;
    }
    edit(old => ({ ...old, ids: [...old.ids, id] }), { id: '' });
  };
  const previewRoute = async () => {
    if (!allowed || !current || busy || !isCurrent()) return;
    const input = buildInput(draft);
    if (!input) { setError(t('shared.invalid')); return; }
    const generationAtRequest = generation.current;
    const intent = ++previewIntent.current;
    setBusy('preview'); setError(''); setPreview(null);
    try {
      const out = await api.previewSharedRoute(profileId, { applicant_input: input, expected_revision: current.revision });
      if (!mounted.current || !isCurrent() || intent !== previewIntent.current || generation.current !== generationAtRequest) return;
      if (!matchesSharedPreview(out, profileId, input, current.revision)) throw new Error(t('shared.mismatch'));
      setPreview({ body: out, input, generation: generationAtRequest });
    } catch (cause) { if (mounted.current && isCurrent() && intent === previewIntent.current) {
      if (cause instanceof ApiError && cause.status === 409) { setNotice(t('shared.conflict')); await readCurrent(); }
      else setError(meaningfulError(cause));
    } }
    finally { if (mounted.current && isCurrent() && intent === previewIntent.current) setBusy(null); }
  };

  const sendWrite = async (body: SharedRouteWriteV1) => {
    if (!mounted.current || !isCurrent()) return;
    const prior = pendingRef.current;
    const submitted = prior?.submitted_generation ?? generation.current;
    const next: PendingWrite = { body, state: 'sending', submitted_generation: submitted, dispatched: true };
    // An explicit retry may repair an earlier verified setItem whose readback failed; never adopt another intent.
    const stored = readSharedRouteRecovery(bindingRef.current);
    if (stored.state === 'valid' && journal.current && stored.record.draft_id === journal.current.draft_id
      && stored.record.pending && recoveryCanonical(stored.record.pending.body) === recoveryCanonical(body)
      && stored.record.draft_generation === journal.current.draft_generation
      && recoveryCanonical(stored.record.draft) === recoveryCanonical(journal.current.draft)
      && stored.record.manual_id === journal.current.manual_id
      && recoveryCanonical(stored.record.manual_review) === recoveryCanonical(journal.current.manual_review)) {
      journal.current = { ...journal.current, journal_revision: stored.record.journal_revision }; journalRaw.current = stored.raw;
    }
    pendingRef.current = next; setPending(next);
    const persisted = journal.current && persist({ ...journal.current, pending: next });
    if (!persisted) {
      // A failed retry journal cannot turn an already dispatched unknown outcome into "never sent".
      const blocked: PendingWrite = { body, submitted_generation: submitted,
        dispatched: prior?.dispatched ?? false, state: prior?.dispatched ? prior.state === 'sending' ? 'uncertain' : prior.state : 'not_sent' };
      pendingRef.current = blocked; setPending(blocked);
      if (journal.current) journal.current = { ...journal.current, pending: blocked };
      setRecoveryWarning(t('shared.recoveryUnavailable')); setNotice(blocked.dispatched ? t('shared.uncertain') : t('shared.recoveryNotSent'));
      publishRisk(); return;
    }
    const intent = ++writeIntent.current;
    setBusy('save'); setError(''); setNotice(''); publishRisk();
    try {
      const receipt = await api.saveSharedRoute(profileId, body);
      if (!mounted.current || !isCurrent() || intent !== writeIntent.current) return;
      if (!matchesSharedReceipt(receipt, profileId, body)) throw new Error(t('shared.mismatch'));
      acceptedRevision.current = Math.max(acceptedRevision.current, receipt.revision); onActive(true);
      acknowledge(receipt, body); await readCurrent();
    } catch (cause) { if (mounted.current && isCurrent() && intent === writeIntent.current) {
      const conflict = cause instanceof ApiError && cause.status === 409;
      const expired = cause instanceof ApiError && cause.status === 402;
      const unresolved: PendingWrite = { ...next, state: conflict ? 'conflict' : expired ? 'expired' : 'uncertain' };
      pendingRef.current = unresolved; setPending(unresolved);
      if (journal.current) persist({ ...journal.current, pending: unresolved });
      setNotice(conflict ? t('shared.conflict') : expired ? t('shared.readonly') : t('shared.uncertain'));
      if (conflict) { setPreview(null); await readCurrent(); }
    } }
    finally { if (mounted.current && isCurrent() && intent === writeIntent.current) setBusy(null); }
  };
  const savePreview = () => {
    if (!allowed || !preview || !current || pending || busy || !isCurrent()
      || preview.generation !== generation.current
      || preview.body.expected_shared_revision !== current.revision) return;
    const body: SharedRouteWriteV1 = { applicant_input: preview.input,
      expected_revision: preview.body.expected_shared_revision,
      client_write_uuid: crypto.randomUUID(), preview_fingerprint: preview.body.preview_fingerprint,
      source_fingerprint: preview.body.source_fingerprint, legacy_anchor: preview.body.legacy_anchor,
      planned_on: preview.body.planned_on };
    void sendWrite(body);
  };
  const retryOriginal = () => { if (pending && pending.state !== 'sending' && pending.state !== 'expired' && allowed && !busy && isCurrent()) void sendWrite(pending.body); };
  const loadHistory = async () => {
    if (!current || busy || !isCurrent()) return;
    const revision = integer(historyRevision, 1, current.revision);
    if (revision === null) { setError(t('shared.historyInvalid')); return; }
    const intent = ++historyIntent.current;
    setBusy('history'); setError(''); setHistory(null);
    try {
      const view = await api.sharedRouteHistory(profileId, revision);
      if (!mounted.current || !isCurrent() || intent !== historyIntent.current) return;
      if (!matchesSharedView(view, profileId, revision)) throw new Error(t('shared.mismatch'));
      setHistory(view);
    } catch (cause) { if (mounted.current && isCurrent() && intent === historyIntent.current) setError(meaningfulError(cause)); }
    finally { if (mounted.current && isCurrent() && intent === historyIntent.current) setBusy(null); }
  };

  const visiblePreview = preview?.generation === generation.current ? preview : null;
  const recentAttempts = progress.profile_id === profileId ? progress.attempts : [];
  const grid: CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))', gap: '0.75rem' };
  return <Panel title={t('shared.title')} hint={t('shared.intro')}>
    <div className="stack study-schedule" role="region" aria-label={t('shared.title')}>
      <p className="small">{t('shared.oneBudget')}</p>
      {!allowed && <Notice kind="warn"><div>{t('shared.readonly')}</div></Notice>}
      {busy === 'read' && <p role="status">{t('shared.loading')}</p>}
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      {(restored || localDirty) && <p role="status">{t('shared.recoveryDraft')}</p>}
      {recoveryWarning && <p role="alert">{recoveryWarning}</p>}
      {(recoveryWarning || localDirty || pending) && <button type="button" className="btn btn--sm" disabled={busy === 'save'} onClick={resetLocal}>{t('shared.recoveryReset')}</button>}
      <button type="button" className="btn btn--sm" disabled={busy !== null} onClick={() => void readCurrent()}>{t('shared.refresh')}</button>
      {ack && <p role="status">{t('shared.acceptedRevision')} {ack.revision}</p>}
      {current?.view && <RouteView title={t('shared.current')} view={current.view} allowed={allowed} onTarget={onTarget} />}
      <details><summary>{t('shared.history')}</summary>
        <p className="small">{t('shared.historyHint')}</p>
        <div className="row"><label htmlFor="shared-history-revision">{t('shared.revision')}</label>
          <input id="shared-history-revision" type="number" min="1" max={current?.revision ?? 1} value={historyRevision}
            onChange={event => setHistoryRevision(event.target.value)} />
          <button type="button" className="btn btn--sm" disabled={!current || busy !== null} onClick={() => void loadHistory()}>{t('shared.openHistory')}</button></div>
        {history && <RouteView title={t('shared.historical')} view={history} allowed={allowed} onTarget={onTarget} />}
      </details>
      <section className="panel panel--sunken stack" aria-label={t('shared.newPlan')}>
        <h3>{t('shared.newPlan')}</h3>
        <p className="small">{t('shared.selectionHint')}</p>
        <ol>{draft.ids.map((id, index) => <li key={id} style={{ overflowWrap: 'anywhere' }}>
          {t('shared.programmeNumber')} {index + 1} <details><summary>{t('shared.reference')}</summary>{id}</details>
          <button type="button" className="btn btn--sm" onClick={() => edit(old => ({ ...old, ids: old.ids.filter(value => value !== id) }))}>{t('shared.remove')}</button>
          <button type="button" className="btn btn--sm" disabled={index === 0} onClick={() => edit(old => {
            const ids = [...old.ids]; const earlier = ids[index - 1]!;
            ids[index - 1] = ids[index]!; ids[index] = earlier; return { ...old, ids };
          })}>{t('shared.up')}</button>
        </li>)}</ol>
        <div className="row">{programmes.filter(canName).map((item, index) => draft.ids.includes(item.id) ? null
          : <div key={item.id}><button type="button" className="btn btn--sm" disabled={draft.ids.length >= 20}
            onClick={() => addId(item.id)}>{t('shared.add')} {t('shared.programmeNumber')} {index + 1}</button>
            <details><summary>{t('shared.reference')}</summary><span style={{ overflowWrap: 'anywhere' }}>{item.id}</span></details></div>)}</div>
        <div className="field"><label htmlFor="shared-manual-id">{t('shared.savedId')}</label>
          <input id="shared-manual-id" value={manualId} maxLength={32} onChange={event => edit(old => old, { id: event.target.value })} />
          <p className="xs muted">{t('shared.savedIdHint')}</p>
          <button type="button" className="btn btn--sm" disabled={!manualId.trim() || draft.ids.length >= 20} onClick={() => addId(manualId)}>{t('shared.addId')}</button></div>
        <div style={grid}>
          <div className="field"><label htmlFor="shared-start">{t('shared.startsOn')}</label><input id="shared-start" type="date" value={draft.starts_on}
            onChange={event => edit(old => ({ ...old, starts_on: event.target.value }))} /></div>
          <div className="field"><label htmlFor="shared-timezone">{t('shared.timezone')}</label><input id="shared-timezone" value={draft.timezone} maxLength={80}
            onChange={event => edit(old => ({ ...old, timezone: event.target.value }))} /></div>
          <div className="field"><label htmlFor="shared-budget">{t('shared.weeklyMinutes')}</label><input id="shared-budget" type="number" min="30" max="1260" value={draft.weekly}
            onChange={event => edit(old => ({ ...old, weekly: event.target.value }))} /></div>
        </div>
        <fieldset><legend>{t('shared.days')}</legend><div className="row">{weekdays.map(day => <label key={day}>
          <input type="checkbox" checked={draft.days.includes(day)} onChange={() => edit(old => ({ ...old,
            days: old.days.includes(day) ? old.days.filter(value => value !== day) : [...old.days, day] }))} /> {t((`shared.day${day}`) as Parameters<typeof t>[0])}
        </label>)}</div></fieldset>
        {draft.exams.map((exam, index) => <fieldset key={exam.exam} className="panel panel--sunken stack"><legend>{examLabel(exam.exam)}</legend>
          <label><input type="checkbox" checked={exam.enabled} onChange={event => changeExam(exam.exam, { enabled: event.target.checked })} /> {t('shared.includeExam')}</label>
          {index > 0 && exam.enabled && <button type="button" className="btn btn--sm" onClick={() => edit(old => ({ ...old, exams: [...old.exams].reverse() }))}>{t('shared.priorityFirst')}</button>}
          {exam.enabled && <>
            <div style={grid}>
              <div className="field"><label htmlFor={`${exam.exam}-first`}>{t('shared.firstExam')}</label><input id={`${exam.exam}-first`} type="date" value={exam.first_exam_on} onChange={event => changeExam(exam.exam, { first_exam_on: event.target.value })} /></div>
              <div className="field"><label htmlFor={`${exam.exam}-retake`}>{t('shared.retake')}</label><input id={`${exam.exam}-retake`} type="date" value={exam.retake_on} onChange={event => changeExam(exam.exam, { retake_on: event.target.value })} /></div>
              <div className="field"><label htmlFor={`${exam.exam}-deadline`}>{t('shared.certificateDeadline')}</label><input id={`${exam.exam}-deadline`} type="date" value={exam.certificate_deadline} onChange={event => changeExam(exam.exam, { certificate_deadline: event.target.value })} /></div>
              {([['result_wait_days', 'shared.wait'], ['delivery_days', 'shared.delivery'], ['safety_days', 'shared.safety']] as const).map(([field, key]) =>
                <div className="field" key={field}><label htmlFor={`${exam.exam}-${field}`}>{t(key)}</label><input id={`${exam.exam}-${field}`} type="number" min={field === 'result_wait_days' ? 1 : 0} max={field === 'result_wait_days' ? 60 : 30}
                  value={exam[field]} onChange={event => changeExam(exam.exam, { [field]: event.target.value })} /></div>)}
            </div>
            <details><summary>{t('shared.optionalTargets')}</summary><div style={grid}>{targetKeys[exam.exam].map(key =>
              <div className="field" key={key}><label htmlFor={`${exam.exam}-${key}`}>{t(targetLabel[key] ?? 'shared.stateUnknown')}</label>
                <input id={`${exam.exam}-${key}`} type="number" step={exam.exam === 'ielts_academic' ? '0.5' : '1'} value={exam.targets[key] ?? ''}
                  onChange={event => changeExam(exam.exam, { targets: { ...exam.targets, [key]: event.target.value } })} /></div>)}</div></details>
            <label><input type="checkbox" checked={exam.confirmed} onChange={event => changeExam(exam.exam, { confirmed: event.target.checked })} /> {t('shared.confirmExam')}</label>
          </>}
        </fieldset>)}
        <details><summary>{t('shared.ownReviews')}</summary><p className="small">{t('shared.reviewHint')}</p>
          {recentAttempts.map((attempt, index) => <div key={attempt.attempt_id} className="row" style={{ overflowWrap: 'anywhere' }}>
            <span>{t('shared.review')} {index + 1}</span>
            <details><summary>{t('shared.reference')}</summary>{attempt.lesson_id} · {attempt.version} · {attempt.attempt_id}</details>
            <button type="button" className="btn btn--sm" disabled={draft.reviews.length >= 400 || draft.reviews.some(item => item.attempt_id === attempt.attempt_id)}
              onClick={() => edit(old => ({ ...old, reviews: [...old.reviews, { attempt_id: attempt.attempt_id,
                lesson_id: attempt.lesson_id, content_version: attempt.version, exam: '', minutes: '' }] }))}>{t('shared.addReview')}</button>
          </div>)}
          <fieldset><legend>{t('shared.olderReview')}</legend><div style={grid}>
            <div className="field"><label htmlFor="shared-own-attempt">{t('shared.attemptId')}</label><input id="shared-own-attempt" value={manualReview.attempt_id}
              maxLength={36} onChange={event => edit(old => old, { review: { ...manualReviewRef.current, attempt_id: event.target.value } })} /></div>
            <div className="field"><label htmlFor="shared-own-lesson">{t('shared.lessonId')}</label><input id="shared-own-lesson" value={manualReview.lesson_id}
              maxLength={80} onChange={event => edit(old => old, { review: { ...manualReviewRef.current, lesson_id: event.target.value } })} /></div>
            <div className="field"><label htmlFor="shared-own-version">{t('shared.contentVersion')}</label><input id="shared-own-version" value={manualReview.content_version}
              maxLength={40} onChange={event => edit(old => old, { review: { ...manualReviewRef.current, content_version: event.target.value } })} /></div>
          </div><button type="button" className="btn btn--sm" disabled={draft.reviews.length >= 400} onClick={() => {
            const candidate = manualReview;
            if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(candidate.attempt_id)
              || !candidate.lesson_id || candidate.lesson_id !== candidate.lesson_id.trim()
              || !candidate.content_version || candidate.content_version !== candidate.content_version.trim()
              || draft.reviews.some(item => item.attempt_id === candidate.attempt_id)) {
              setError(t('shared.invalidReview')); return;
            }
            edit(old => ({ ...old, reviews: [...old.reviews, { ...candidate, exam: '', minutes: '' }] }),
              { review: { attempt_id: '', lesson_id: '', content_version: '' } });
          }}>{t('shared.addReview')}</button></fieldset>
          {draft.reviews.map((review, index) => <div className="panel panel--sunken" key={review.attempt_id}>
            <p>{t('shared.review')} {index + 1}</p>
            <details><summary>{t('shared.reference')}</summary><span style={{ overflowWrap: 'anywhere' }}>{review.lesson_id} · {review.content_version} · {review.attempt_id}</span></details>
            <div style={grid}><div className="field"><label htmlFor={`review-exam-${index}`}>{t('shared.exam')}</label><select id={`review-exam-${index}`} value={review.exam}
              onChange={event => edit(old => ({ ...old, reviews: old.reviews.map((item, i) => i === index ? { ...item, exam: event.target.value as SharedExam } : item) }))}>
              <option value="">{t('shared.chooseExam')}</option>
              <option value="ielts_academic">{t('shared.ielts')}</option><option value="digital_sat">{t('shared.sat')}</option></select></div>
              <div className="field"><label htmlFor={`review-minutes-${index}`}>{t('shared.reviewMinutes')}</label><input id={`review-minutes-${index}`} type="number" min="1" max="1260" value={review.minutes}
                onChange={event => edit(old => ({ ...old, reviews: old.reviews.map((item, i) => i === index ? { ...item, minutes: event.target.value } : item) }))} /></div></div>
            <button type="button" className="btn btn--sm" onClick={() => edit(old => ({ ...old, reviews: old.reviews.filter((_, i) => i !== index) }))}>{t('shared.remove')}</button>
          </div>)}
        </details>
        <label><input type="checkbox" checked={draft.confirmed} onChange={event => edit(old => ({ ...old, confirmed: event.target.checked }))} /> {t('shared.confirmInputs')}</label>
        <p className="small">{t('shared.previewOnly')}</p>
        <button type="button" className="btn btn--primary" disabled={!allowed || !current || busy !== null} onClick={() => void previewRoute()}>{t('shared.preview')}</button>
        {visiblePreview && <section aria-label={t('shared.previewResult')} className="stack">
          <h4>{t('shared.previewResult')}</h4><p>{t('shared.unsaved')}</p>
          <Allocation allocation={visiblePreview.body.allocation} budget={visiblePreview.input.shared_weekly_minutes}
            allowed={allowed} onTarget={onTarget} statuses={null} />
          {!!visiblePreview.body.review_reasons.length && <p className="small">{t('shared.needsReview')}</p>}
          <button type="button" className="btn btn--primary" disabled={busy !== null || !!pending || !allowed} onClick={savePreview}>{t('shared.save')}</button>
        </section>}
        {pending && <div className="stack" role="status">
          <p>{pending.state === 'not_sent' ? t('shared.recoveryNotSent') : pending.state === 'conflict' ? t('shared.conflict') : pending.state === 'expired' ? t('shared.readonly') : pending.state === 'uncertain' ? t('shared.uncertain') : t('shared.saving')}</p>
          <details><summary>{t('shared.originalIntent')}</summary><p className="xs muted" style={{ overflowWrap: 'anywhere' }}>{pending.body.client_write_uuid}</p></details>
          {pending.state !== 'sending' && <button type="button" className="btn" disabled={busy !== null || !allowed || pending.state === 'expired'} onClick={retryOriginal}>{t('shared.retryOriginal')}</button>}
          {pending.state === 'conflict' && <button type="button" className="btn" disabled={!visiblePreview || busy !== null}
            onClick={() => {
              const original = journal.current;
              if (original && persist({ ...original, pending: null, dirty: true })) {
                pendingRef.current = null; setPending(null); publishRisk();
              }
            }}>{t('shared.newIntent')}</button>}
        </div>}
      </section>
    </div>
  </Panel>;
}

function RouteView({ title, view, allowed, onTarget }: {
  title: string; view: SharedRouteViewV1; allowed: boolean; onTarget: (ref: SharedLearningRef) => void;
}) {
  const status = view.current_status;
  return <section className="panel panel--sunken stack" aria-label={title}>
    <h3>{title} · {t('shared.revision')} {view.receipt.revision}</h3>
    <p className="small">{t('shared.acceptedOn')} {view.receipt.accepted_at}</p>
    <p className="small">{t('shared.status')} {status.needs_review ? t('shared.needsReview') : t('shared.noCurrentChange')}</p>
    <p className="small">{t('shared.evidenceHint')}</p>
    {status.goal_statuses.map((goal, index) => <div className="small" key={goal.result_id}>
      {t('shared.programmeNumber')} {index + 1}: {stateLabel(goal.state)}
      <details><summary>{t('shared.reference')}</summary><span style={{ overflowWrap: 'anywhere' }}>{goal.result_id}</span></details>
    </div>)}
    <p className="small">{t('shared.legacyStatus')} {stateLabel(status.legacy_structure)} · {t('shared.contentStatus')} {stateLabel(status.imported_refs)}</p>
    {!!status.review_reasons.length && <details><summary>{t('shared.reviewReasons')}</summary><ul>{status.review_reasons.map((reason, index) =>
      <li key={`${reason.code}-${index}`}>{reasonLabel(reason.code)}
        {(reason.result_id || reason.action_id) && <details><summary>{t('shared.reference')}</summary>
          <span style={{ overflowWrap: 'anywhere' }}>{reason.result_id ?? reason.action_id}</span></details>}
      </li>)}</ul></details>}
    <Allocation allocation={view.receipt.allocation} budget={view.receipt.applicant_input.shared_weekly_minutes}
      allowed={allowed && status.preparation_access === 'active'}
      onTarget={onTarget} statuses={new Map(status.content_statuses.map(item => [item.action_id, item.state]))} />
    <p className="small">{t('shared.savedTruth')}</p>
  </section>;
}

function Allocation({ allocation, budget, allowed, onTarget, statuses }: {
  allocation: SharedRoutePreviewOutV1['allocation']; budget: number; allowed: boolean;
  onTarget: (ref: SharedLearningRef) => void;
  statuses: Map<string, string> | null;
}) {
  return <div className="stack">
    <p>{t('shared.oneBudget')}: {budget} {t('shared.minutesWeek')}</p>
    <p className="small">{t('shared.notReadiness')}</p>
    {allocation.exam_timing.map(item => <section key={item.exam} className="panel panel--sunken stack stack--tight">
      <h5>{examLabel(item.exam)} · {stateLabel(item.timing)}</h5>
      <p className="small">{t('shared.firstExam')} {item.first_exam_on}</p>
      {item.retake_on && <p className="small">{t('shared.retake')} {item.retake_on}</p>}
      <p className="small">{t('shared.certificateDeadline')} {item.certificate_deadline}</p>
      <p className="small">{t('shared.wait')} {item.result_wait_days} · {t('shared.delivery')} {item.delivery_days} · {t('shared.safety')} {item.safety_days}</p>
      <p className="small">{t('shared.latestSafe')} {item.latest_safe_exam_on}</p>
      {(() => {
        const targets = allocation.ordered_exam_choices.find(choice => choice.exam === item.exam)?.personal_targets;
        return targets && Object.keys(targets).length ? <details><summary>{t('shared.personalTargetHint')}</summary><ul>
          {Object.entries(targets).map(([key, value]) => <li key={key}>{t(targetLabel[key] ?? 'shared.stateUnknown')}: {value}</li>)}
        </ul></details> : null;
      })()}
    </section>)}
    {allocation.slots.length ? <ol>{allocation.slots.map(slot => <li key={slot.occurrence_id} style={{ overflowWrap: 'anywhere' }}>
      {slot.local_date} · {examLabel(slot.exam)} · {actionLabel(slot.ref)} · {slot.planned_minutes} {t('shared.minutes')}
      <ExactReference learningRef={slot.ref} />
      <button type="button" className="btn btn--sm" disabled={(slot.ref.kind === 'lesson' && !allowed) || (statuses !== null && statuses.get(slot.action_id) !== 'available')}
        onClick={() => onTarget(slot.ref)}>{slot.ref.kind === 'lesson' ? t('shared.openLesson') : t('shared.openReview')}</button>
      {statuses !== null && statuses.get(slot.action_id) !== 'available' && <span className="small">{t('shared.exactUnavailable')}</span>}
    </li>)}</ol> : <p>{t('shared.noSlots')}</p>}
    {!!allocation.unallocated.length && <details><summary>{t('shared.unallocated')}</summary><ul>{allocation.unallocated.map(item =>
      <li key={item.action_id}>{examLabel(item.exam)} · {actionLabel(item.ref)} · {item.requested_minutes} {t('shared.minutes')} · {stateLabel(item.reason)}
        <ExactReference learningRef={item.ref} /></li>)}</ul></details>}
  </div>;
}

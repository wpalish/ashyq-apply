import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { ApiError, api } from '@/api/client';
import { Loading, Notice, Panel } from '@/components/primitives';
import { getLocale, subscribe, t } from '@/lib/i18n';
import type { LearningPathOut, LearningTaskRef, LearningTask } from '@/types';

interface Props {
  profileId: string; revision: number; allowed: boolean; dirty: boolean;
  isCurrent: () => boolean; onTarget: (ref: LearningTaskRef) => void; onSaved: () => void;
}

export function validLearningRef(ref: LearningTaskRef | null): boolean {
  if (!ref || typeof ref.id !== 'string' || !ref.id) return false;
  if (ref.kind === 'lesson' || ref.kind === 'attempt_review') {
    if (typeof ref.lesson_id !== 'string' || !ref.lesson_id || typeof ref.content_version !== 'string' || !ref.content_version) return false;
    return ref.kind === 'lesson'
      ? ref.id === `lesson:${ref.lesson_id}:${ref.content_version}`
      : typeof ref.attempt_id === 'string' && /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i.test(ref.attempt_id) && ref.id === `attempt:${ref.attempt_id}`;
  }
  return false;
}

export function LearningSchedulePanel({ profileId, revision, allowed, dirty, isCurrent, onTarget, onSaved }: Props) {
  useSyncExternalStore(subscribe, getLocale);
  const [opened, setOpened] = useState(false);
  const [record, setRecord] = useState<LearningPathOut | null>(null);
  const [readReady, setReadReady] = useState(false);
  const [preview, setPreview] = useState<LearningPathOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const mounted = useRef(false);
  const intent = useRef(0);
  const writing = useRef(false);
  const liveCurrent = useRef(isCurrent);
  const liveRevision = useRef(revision);
  const liveSaved = useRef(onSaved);
  liveCurrent.current = isCurrent;
  liveRevision.current = revision;
  liveSaved.current = onSaved;
  const current = useCallback(() => {
    try { return mounted.current && liveCurrent.current(); } catch { return false; }
  }, []);
  const matches = (next: LearningPathOut) => next.profile_id === profileId && Number.isInteger(next.revision) && next.revision >= 0;
  const load = useCallback(async () => {
    const token = ++intent.current;
    setBusy(true); setReadReady(false); setError(''); setPreview(null);
    try {
      const next = await api.learningStudySchedule(profileId);
      if (!current() || token !== intent.current) return;
      if (next.profile_id !== profileId || !Number.isInteger(next.revision)) throw new Error(t('learning.error'));
      setRecord(next); setReadReady(true); setPreview(null);
      if (next.revision !== liveRevision.current) {
        setStatus(t('learning.conflict')); liveSaved.current();
      }
    } catch { if (current() && token === intent.current) setError(t('learning.error')); }
    finally { if (current() && token === intent.current) setBusy(false); }
  }, [current, profileId]);
  useEffect(() => {
    mounted.current = true;
    if (opened) void load();
    return () => { mounted.current = false; ++intent.current; };
  }, [opened, revision, load]);
  const previewPath = async () => {
    if (!current() || busy || dirty || !allowed || !readReady || !record?.revision || record.revision !== revision) return;
    const token = ++intent.current;
    setBusy(true); setError(''); setStatus(''); setPreview(null);
    try {
      const next = await api.previewLearningSchedule(profileId, record.revision);
      if (!current() || token !== intent.current) return;
      if (!matches(next) || next.revision !== record.revision || !next.learning_path) throw new Error(t('learning.error'));
      setPreview(next);
    } catch (problem) {
      if (!current() || token !== intent.current) return;
      if (problem instanceof ApiError && problem.status === 409) { setStatus(t('learning.conflict')); await load(); onSaved(); }
      else setError(t('learning.error'));
    } finally { if (current() && token === intent.current) setBusy(false); }
  };
  const save = async () => {
    if (!current() || busy || writing.current || dirty || !allowed || !preview?.learning_path || !preview.legacy_fingerprint) return;
    writing.current = true;
    const token = ++intent.current;
    setBusy(true); setError(''); setStatus('');
    const input = { expected_revision: preview.revision, legacy_fingerprint: preview.legacy_fingerprint, draft: preview.learning_path.draft };
    try {
      const next = await api.saveLearningSchedule(profileId, input);
      if (!current() || token !== intent.current) return;
      if (!matches(next) || next.revision !== input.expected_revision + 1 || !next.learning_path
        || next.learning_path.draft.fingerprint !== input.draft.fingerprint) throw new Error(t('learning.error'));
      setRecord(next); setPreview(null); setStatus(t('learning.loaded')); onSaved();
    } catch (problem) {
      if (!current() || token !== intent.current) return;
      if (problem instanceof ApiError && problem.status === 409) { setStatus(t('learning.conflict')); await load(); onSaved(); }
      else setError(t('learning.error'));
    } finally { writing.current = false; if (current()) setBusy(false); }
  };
  if (!isCurrent()) return null;
  if (!opened) return <button type="button" className="btn" onClick={() => setOpened(true)}>{t('learning.open')}</button>;
  const view = preview ?? record;
  const path = view?.learning_path;
  const tasks = path?.schedule.tasks ?? [];
  const nextTasks = tasks.filter(task => task.due_on >= (path?.schedule.as_of ?? '')).slice(0, 14);
  const nextIds = new Set(nextTasks.map(task => task.id));
  const others = tasks.filter(task => !nextIds.has(task.id));
  const renderTask = (task: LearningTask) => {
    const ref = task.learning_ref;
    const active = task.availability === 'available' && validLearningRef(ref) && (ref?.kind === 'attempt_review' || allowed);
    const receipt = ref?.kind === 'lesson' && task.submitted_attempt_id
      ? { kind: 'attempt_review' as const, id: `attempt:${task.submitted_attempt_id}`, attempt_id: task.submitted_attempt_id, lesson_id: ref.lesson_id, content_version: ref.content_version }
      : null;
    return <li key={task.id} data-learning-task={task.id} className="stack stack--tight">
      <p><strong>{task.due_on} · {task.title}</strong>{task.minutes ? ` · ${task.minutes} min` : ''}</p>
      {ref && <details><summary>{t('learning.details')}</summary><p className="xs">{ref.id}</p></details>}
      {active && ref && <button type="button" className="btn btn--sm" disabled={busy || !readReady || record?.revision !== revision || Boolean(preview) || (ref.kind === 'lesson' && Boolean(record?.needs_review))}
        data-learning-ref={ref.id} onClick={() => { if (current()) onTarget(ref); }}>{t(ref.kind === 'attempt_review' ? 'learning.review' : 'learning.lesson')}</button>}
      {task.unavailable_reason && <p className="small">{t(`learning.${task.unavailable_reason}`)}</p>}
      {receipt && validLearningRef(receipt) && <><p className="small">{t('learning.submitted')}</p><button type="button" className="btn btn--sm" disabled={busy || !readReady || record?.revision !== revision || Boolean(preview)} onClick={() => { if (current()) onTarget(receipt); }}>{t('learning.review')}</button></>}
    </li>;
  };
  return <Panel title={t('learning.title')}>
    {busy && <Loading label={t('learning.loading')} />}
    {error && <div role="alert">{error}<button type="button" className="btn" onClick={() => void load()}>{t('learning.open')}</button></div>}
    <p role="status">{status}</p>
    {!allowed && <Notice kind="warn">{t('learning.readonly')}</Notice>}
    {dirty && <p>{t('learning.dirty')}</p>}
    {record?.needs_review && <Notice kind="warn">{t('learning.stale')}</Notice>}
    {record?.revision === 0 && <p>{t('learning.empty')}</p>}
    <p className="small">{t('learning.note')}</p>
    <button type="button" className="btn" disabled={busy || dirty || !allowed || !readReady || !record?.revision || record.revision !== revision} onClick={() => void previewPath()}>{t('learning.preview')}</button>
    {preview && <Notice kind="info"><div><p>{t('learning.previewNotice')}</p>
      <button type="button" className="btn btn--primary" disabled={busy || dirty || !allowed} onClick={() => void save()}>{t('learning.save')}</button>
      <button type="button" className="btn" disabled={busy} onClick={() => setPreview(null)}>{t('learning.cancel')}</button>
    </div></Notice>}
    {path && <>
      <p>{path.draft.plan.schedule_settings.timezone} · {path.schedule.latest_exam_on} · {path.schedule.study_minutes_remaining} min</p>
      {path.schedule.unallocated_lesson_ids.length > 0 && <Notice kind="warn"><p>{t('learning.unallocated')}: {path.schedule.unallocated_lesson_ids.join(', ')}</p></Notice>}
      {path.schedule.unallocated_review_ids.length > 0 && <Notice kind="warn"><p>{t('learning.unallocated')}: {path.schedule.unallocated_review_ids.length} · {t('learning.review')}</p></Notice>}
      <ol className="stack">{nextTasks.map(renderTask)}</ol>
      {others.length > 0 && <details><summary>{t('learning.other')} ({others.length})</summary><ol className="stack">{others.map(renderTask)}</ol></details>}
      <details><summary>{t('learning.history')} ({path.legacy_settings.completed_task_ids.length})</summary><ul>{path.legacy_settings.completed_task_ids.map(id => <li key={id} className="xs">{id}</li>)}</ul></details>
    </>}
  </Panel>;
}

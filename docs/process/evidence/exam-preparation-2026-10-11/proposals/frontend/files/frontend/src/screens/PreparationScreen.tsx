import { useCallback, useContext, useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { Chip, Empty, Loading, Notice, Panel, SourceLink, StatusChip } from '@/components/primitives';
import { currentApplicantOwner } from '@/lib/applicantStorage';
import { DraftIdentityContext } from '@/lib/draftIdentity';
import { dateTime, eligibilityTone } from '@/lib/format';
import { useStore } from '@/lib/store';
import type {
  PreparationAccess, PreparationAttemptInput, PreparationCatalogue, PreparationLesson,
  ClaimScope, PreparationPlan, PreparationProgress, ProgramResult, StudyAttempt,
} from '@/types';

type Mode = 'goals' | 'practice' | 'progress';
const MODES: { id: Mode; title: string }[] = [
  { id: 'goals', title: 'Goals & evidence' }, { id: 'practice', title: 'Practice' }, { id: 'progress', title: 'Progress' },
];
const message = (error: unknown) => error instanceof Error ? error.message : 'Preparation could not be loaded. Try again.';
const FIELD_LABELS: Record<string, string> = {
  university: 'University', faculty: 'Faculty', programme: 'Programme', degree: 'Degree', intake: 'Intake',
  academic_year: 'Academic year', population: 'Applicant group', nationality: 'Citizenship', residency: 'Residency',
  qualification: 'Educational qualification', overall: 'Overall', reading: 'Reading', writing: 'Writing',
  listening: 'Listening', speaking: 'Speaking', math: 'Math', reading_writing: 'Reading & Writing',
};
const fieldLabel = (field: string) => FIELD_LABELS[field] ?? field.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/_/g, ' ').replace(/^./, letter => letter.toUpperCase());
function readableValue(value: unknown): string {
  if (value == null || value === '') return 'Not established';
  if (Array.isArray(value)) return value.map(readableValue).join('; ') || 'Not established';
  if (typeof value === 'object') return Object.entries(value).map(([field, item]) => `${fieldLabel(field)}: ${readableValue(item)}`).join('; ') || 'Not established';
  return String(value);
}
const recordedScope = (scope: ClaimScope) => Object.entries(scope).map(([field, value]) => `${fieldLabel(field)}: ${value || 'Not stated'}`).join(' · ');

/** Account/case replacement remounts local questions, answers and feedback before paint. */
export function PreparationScreen({ onProfile, onBilling }: { onProfile?: () => void; onBilling?: () => void }) {
  const { savedProfile, caseEpoch, results, hydrated, loading: caseLoading } = useStore();
  const identity = useContext(DraftIdentityContext);
  if (identity === null) return <Empty title="Sign in to your workspace">Preparation requires a verified workspace.</Empty>;
  if (!hydrated || caseLoading) return <Loading label="Loading your applicant case…" />;
  if (!savedProfile) return <Panel title="Exam preparation">
    <Empty title="Save or select an applicant case first">Your practice history belongs to your own saved case.</Empty>
    {onProfile && <button className="btn btn--primary" type="button" onClick={onProfile}>Open profile</button>}
  </Panel>;
  return <PreparationCase key={JSON.stringify([identity ?? 'demo', savedProfile.id, caseEpoch])}
    profileId={savedProfile.id} programmes={results.filter(r => r.user_decision === 'approved' || r.user_decision === 'maybe')}
    onBilling={onBilling} />;
}

function AccessNotice({ access, onBilling }: { access: PreparationAccess; onBilling?: () => void }) {
  return <Notice kind={access.development_only ? 'demo' : access.allowed ? 'info' : 'warn'}>
    <div>
      <strong>{access.development_only ? 'Development starter access' : access.allowed ? 'Starter preparation included' : 'Preparation subscription required'}</strong>
      <p className="small">{access.allowed
        ? 'Original IELTS Reading, SAT Math and SAT Reading & Writing starters. This is not a full exam course or an official mock test.'
        : 'An eligible started subscription term is required for new practice. A research case unlock does not grant preparation. Your saved history remains available.'}</p>
      <p className="xs muted">Access reason: {access.reason.replace(/_/g, ' ')}{access.ends_at ? ` · term ends ${dateTime(access.ends_at)}` : ''}</p>
      {onBilling && !access.allowed && <button type="button" className="btn btn--sm" onClick={onBilling}>View access details</button>}
    </div>
  </Notice>;
}

function PreparationCase({ profileId, programmes, onBilling }: {
  profileId: string; programmes: ProgramResult[]; onBilling?: () => void;
}) {
  const [mode, setMode] = useState<Mode>('goals');
  const [data, setData] = useState<{ access: PreparationAccess; catalogue: PreparationCatalogue; progress: PreparationProgress } | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [reload, setReload] = useState(0);
  const [progressRefreshing, setProgressRefreshing] = useState(false);
  const [resultId, setResultId] = useState(programmes[0]?.id ?? '');
  const [plan, setPlan] = useState<PreparationPlan | null>(null);
  const [planError, setPlanError] = useState('');
  const [planLoading, setPlanLoading] = useState(true);
  const [planReload, setPlanReload] = useState(0);
  const [lesson, setLesson] = useState<PreparationLesson | null>(null);
  const [lessonLoading, setLessonLoading] = useState(false);
  const [lessonError, setLessonError] = useState('');
  const [lastLessonId, setLastLessonId] = useState('');
  const [lessonKey, setLessonKey] = useState(0);
  const mounted = useRef(false);
  const lessonIntent = useRef(0);
  const progressIntent = useRef(0);
  const owner = useRef<string | null | undefined>(undefined);
  const isCurrent = useCallback(() => {
    try { return mounted.current && owner.current === currentApplicantOwner(); }
    catch { return false; }
  }, []);
  useEffect(() => {
    mounted.current = true;
    try { owner.current = currentApplicantOwner(); }
    catch { setLoadError('The workspace changed. Sign in again.'); }
    return () => { mounted.current = false; ++lessonIntent.current; ++progressIntent.current; };
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true); setLoadError('');
    const intent = ++progressIntent.current;
    Promise.all([api.preparationAccess(profileId), api.preparationCatalogue(), api.preparationProgress(profileId)])
      .then(([access, catalogue, progress]) => {
        if (!active || !isCurrent() || intent !== progressIntent.current) return;
        if (progress.profile_id !== profileId || progress.attempts.some(item => item.profile_id !== profileId)) throw new Error('The practice history did not match this case.');
        setData({ access, catalogue, progress });
      }).catch(error => { if (active && isCurrent()) setLoadError(message(error)); })
      .finally(() => { if (active && isCurrent()) setLoading(false); });
    return () => { active = false; };
  }, [profileId, reload, isCurrent]);

  const programmeIds = programmes.map(r => r.id).join('\n');
  const currentResultId = programmes.some(r => r.id === resultId) ? resultId : '';
  useEffect(() => {
    let active = true;
    setPlan(null); setPlanLoading(true); setPlanError('');
    api.preparationPlan(profileId, currentResultId || null).then(next => {
      if (!active || !isCurrent()) return;
      if (next.profile_id !== profileId || next.result_id !== (currentResultId || null)) throw new Error('The exam evidence did not match this case and programme.');
      setPlan(next);
    }).catch(error => { if (active && isCurrent()) setPlanError(message(error)); })
      .finally(() => { if (active && isCurrent()) setPlanLoading(false); });
    return () => { active = false; };
  }, [profileId, currentResultId, programmeIds, planReload, isCurrent]);

  const chooseMode = (next: Mode) => {
    ++lessonIntent.current;
    setLesson(null); setLessonError(''); setLessonLoading(false);
    setMode(next);
    if (next === 'progress') void refreshProgress();
  };
  const startLesson = async (id: string) => {
    if (loading || !data?.access.allowed || !isCurrent()) return;
    const intent = ++lessonIntent.current;
    setMode('practice'); setLesson(null); setLessonError(''); setLessonLoading(true); setLastLessonId(id);
    try {
      const next = await api.preparationLesson(profileId, id, data.catalogue.version);
      if (!isCurrent() || intent !== lessonIntent.current) return;
      if (next.id !== id || next.version !== data.catalogue.version) throw new Error('The lesson did not match the requested version.');
      setLesson(next); setLessonKey(intent);
    } catch (error) {
      if (isCurrent() && intent === lessonIntent.current) setLessonError(message(error));
    } finally {
      if (isCurrent() && intent === lessonIntent.current) setLessonLoading(false);
    }
  };
  const refreshProgress = async () => {
    if (!isCurrent()) return;
    const intent = ++progressIntent.current;
    setProgressRefreshing(true);
    try {
      const progress = await api.preparationProgress(profileId);
      if (!isCurrent() || intent !== progressIntent.current) return;
      if (progress.profile_id !== profileId || progress.attempts.some(item => item.profile_id !== profileId)) throw new Error('The practice history did not match this case.');
      setData(previous => previous ? { ...previous, progress } : previous);
      setLoadError('');
    } catch (error) { if (isCurrent() && intent === progressIntent.current) setLoadError(`Saved history could not refresh: ${message(error)}`); }
    finally { if (isCurrent() && intent === progressIntent.current) setProgressRefreshing(false); }
  };

  const visiblePlan = plan?.profile_id === profileId && plan.result_id === (currentResultId || null) ? plan : null;
  const checks = visiblePlan?.research_access && visiblePlan.evidence_state !== 'locked' ? visiblePlan.checks : [];
  return <div className="stack stack--loose">
    <div className="screen__head">
      <p className="screen__eyebrow">ORIGINAL PRACTICE · YOUR CASE</p>
      <h1 className="screen__title">Prepare for your next step.</h1>
      <p className="screen__lede">Programme requirements, original practice and saved attempts. Practice does not change your official scores or establish admission readiness.</p>
    </div>
    {loading && <Loading label="Loading preparation access and history…" />}
    {loadError && <div role="alert"><Notice kind="risk"><div>{loadError}<button className="btn btn--sm" type="button" onClick={() => setReload(n => n + 1)}>Retry preparation loading</button></div></Notice></div>}
    {data && <>
      <AccessNotice access={data.access} onBilling={onBilling} />
      <nav className="row" aria-label="Preparation views">
        {MODES.map(item => <button type="button" className="btn" key={item.id}
          aria-pressed={mode === item.id} disabled={loading || (item.id === 'progress' && progressRefreshing)} onClick={() => chooseMode(item.id)}>{item.title}</button>)}
      </nav>
      <p className="xs muted">Unsubmitted answers stay only in this form. Leaving a lesson clears them.</p>
      {mode === 'goals' && <Panel title="Exam goals from your chosen programmes">
        <div className="field"><label htmlFor="preparation-programme">Programme evidence</label>
          <select id="preparation-programme" value={currentResultId} onChange={event => { setPlan(null); setPlanError(''); setPlanLoading(true); setResultId(event.target.value); }}>
            <option value="">Personal practice — no programme requirement selected</option>
            {programmes.map(r => <option key={r.id} value={r.id}>{r.university} — {r.program} · {r.intake || 'intake unknown'}</option>)}
          </select>
        </div>
        {planLoading && <Loading label="Loading stored exam evidence…" />}
        {planError && <div role="alert">{planError}<button type="button" className="btn btn--sm" onClick={() => setPlanReload(n => n + 1)}>Retry exam evidence</button></div>}
        {!planLoading && visiblePlan && <>
          <Notice kind={visiblePlan.evidence_state === 'current' ? 'info' : 'warn'}><div>
            <strong>{visiblePlan.evidence_state === 'locked' ? 'Exam evidence is locked' : `Evidence: ${visiblePlan.evidence_state}`}</strong>
            <p className="small">{visiblePlan.notice}</p>
            {visiblePlan.evidence_state === 'locked' && <p className="small">A hidden requirement is not an absent requirement. Research access is separate from preparation.</p>}
          </div></Notice>
          {checks.length === 0 && <p>No confirmed exam goal is shown. You can practise without inventing a university requirement.</p>}
          {checks.map((check, index) => <section className="panel panel--sunken" key={`${check.requirement_check.requirement}-${index}`}>
            <h3>{check.requirement_check.requirement}</h3>
            <div className="row"><StatusChip status={check.requirement_check.status} tone={eligibilityTone[check.requirement_check.status]} />
              <Chip>Policy: {check.policy.replace(/_/g, ' ')}</Chip><Chip>Evidence: {check.evidence_state}</Chip></div>
            <p>{check.requirement_check.explanation}</p>
            <p className="small">Published: {readableValue(check.requirement_check.published_value)}</p>
            <p className="small">Your entered value: {check.requirement_check.applicant_value == null ? 'Not entered' : readableValue(check.requirement_check.applicant_value)}</p>
            <p className="xs muted">Published scope: {check.requirement_check.published_scope || 'Not established — do not assume it covers your programme or intake.'}</p>
            {check.claims.map(claim => <div key={claim.id} className="stack stack--tight">
              <StatusChip status={claim.status} tone={claim.status === 'VERIFIED_CURRENT' ? 'ok' : 'warn'} />
              <p className="xs">{claim.original_text_excerpt}</p><SourceLink url={claim.source_url} />
              <p className="xs muted">Recorded source scope: {claim.scope ? recordedScope(claim.scope) : 'Not recorded — do not assume a match.'}</p>
              <p className="xs muted">{claim.program || 'Programme not established'} · {claim.intake || 'Intake not established'} · read {dateTime(claim.accessed_at)}</p>
            </div>)}
            {check.claims.length === 0 && <p className="xs muted">No linked source proves this requirement.</p>}
            {check.source_urls.filter(url => !check.claims.some(claim => claim.source_url === url)).map(url => <SourceLink key={url} url={url} />)}
            {check.lesson_ids.map(id => <button key={id} type="button" className="btn btn--sm" disabled={loading || !data.access.allowed || !data.catalogue.lessons.some(item => item.id === id)}
              onClick={() => void startLesson(id)}>Practise: {data.catalogue.lessons.find(item => item.id === id)?.title ?? id}</button>)}
          </section>)}
          <button type="button" className="btn btn--primary" onClick={() => chooseMode('practice')}>Browse original practice</button>
        </>}
      </Panel>}
      {mode === 'practice' && <>
        {lessonLoading && <Loading label="Opening the original lesson…" />}
        {lessonError && <div role="alert">{lessonError}<button type="button" className="btn btn--sm" onClick={() => void startLesson(lastLessonId)}>Retry lesson</button></div>}
        {lesson ? <PracticeSession key={lessonKey} profileId={profileId} lesson={lesson} onSaved={() => void refreshProgress()}
          onRestart={() => void startLesson(lesson.id)} canRestart={!loading && data.access.allowed} /> : <Panel title="Original starter lessons" hint={data.catalogue.notice}>
          <div className="stack">{data.catalogue.tracks.map(track => <section key={track.id}>
            <h3>{track.title}</h3>
            {data.catalogue.lessons.filter(item => item.track_id === track.id).map(item => <div key={item.id} className="row">
              <span>{item.title} · {item.question_count} questions</span>
              <button type="button" className="btn btn--sm" disabled={loading || !data.access.allowed || lessonLoading}
                onClick={() => void startLesson(item.id)}>Start {item.title}</button>
            </div>)}
          </section>)}</div>
          <h3>Official exam information &amp; planned courses</h3>
          <p className="small">Exam information below is not a requirement for every programme. Use your programme’s confirmed policy and current official edition.</p>
          <div className="stack">{data.catalogue.exams.map(exam => <section className="panel panel--sunken" key={exam.id}>
            <h3>{exam.title}</h3><Chip>{exam.course_status === 'starter' ? 'Original starters available' : 'Course planned — not available here'}</Chip>
            <p className="small">{exam.notice}</p>
            <p className="xs muted">Metadata checked {exam.checked_date}. External links do not unlock a local course.</p>
            {exam.official_info_urls.length > 0 && <div><span className="xs">Official information (external): </span>{exam.official_info_urls.map(url => <SourceLink key={url} url={url} />)}</div>}
            {exam.official_practice_urls.length > 0 && <div><span className="xs">Official practice (external): </span>{exam.official_practice_urls.map(url => <SourceLink key={url} url={url} />)}</div>}
          </section>)}</div>
        </Panel>}
      </>}
      {mode === 'progress' && <Panel title="Your saved practice" hint="Completed means submitted, not mastered. These results are not official exam scores.">
        <button type="button" className="btn btn--sm" disabled={progressRefreshing} onClick={() => void refreshProgress()}>Refresh saved history</button>
        {progressRefreshing && <Loading label="Refreshing saved practice…" />}
        <p data-testid="progress-summary">{data.progress.attempt_count} saved attempts · {data.progress.completed_lesson_ids.length} starter lessons submitted.</p>
        <p>{data.progress.correct} correct answers out of {data.progress.answered} answered across saved attempts.</p>
        {data.progress.attempts.length === 0 ? <Empty title="No submitted practice yet">Start an original lesson to build your history.</Empty>
          : <ol>{data.progress.attempts.map(attempt => <li key={attempt.id}>
            {data.catalogue.lessons.find(item => item.id === attempt.lesson_id)?.title ?? attempt.lesson_id}: {attempt.correct} / {attempt.total} correct · {dateTime(attempt.created_at)} · version {attempt.version}
          </li>)}</ol>}
      </Panel>}
    </>}
  </div>;
}

function PracticeSession({ profileId, lesson, onSaved, onRestart, canRestart }: {
  profileId: string; lesson: PreparationLesson; onSaved: () => void; onRestart: () => void; canRestart: boolean;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState<StudyAttempt | null>(null);
  const pending = useRef<PreparationAttemptInput | null>(null);
  const inFlight = useRef(false);
  const mounted = useRef(false);
  const owner = useRef<string | null | undefined>(undefined);
  const isCurrent = () => {
    try { return mounted.current && owner.current === currentApplicantOwner(); }
    catch { return false; }
  };
  useEffect(() => {
    mounted.current = true;
    try { owner.current = currentApplicantOwner(); }
    catch { mounted.current = false; }
    return () => { mounted.current = false; };
  }, []);
  const submit = async () => {
    if (!isCurrent() || inFlight.current || attempt || lesson.questions.some(q => !answers[q.id])) return;
    const payload = pending.current ?? {
      attempt_id: crypto.randomUUID(), lesson_id: lesson.id, version: lesson.version,
      answers: lesson.questions.map(q => ({ question_id: q.id, choice_id: answers[q.id]! })),
    };
    pending.current = payload;
    inFlight.current = true; setSending(true); setError('');
    try {
      const next = await api.submitPreparation(profileId, payload);
      if (!isCurrent()) return;
      if (next.profile_id !== profileId || next.lesson_id !== lesson.id || next.version !== lesson.version || next.attempt_id !== payload.attempt_id) {
        throw new Error('The saved attempt did not match this case and lesson.');
      }
      setAttempt(next); onSaved();
    } catch (problem) { if (isCurrent()) setError(message(problem)); }
    finally { inFlight.current = false; if (isCurrent()) setSending(false); }
  };
  const frozen = sending || Boolean(error && pending.current) || Boolean(attempt);
  return <Panel title={lesson.title} hint="Original practice. No official IELTS band or SAT scaled score is produced.">
    <p style={{ whiteSpace: 'pre-wrap' }}>{lesson.introduction}</p>
    <form onSubmit={event => { event.preventDefault(); void submit(); }}>
      <div className="stack">{lesson.questions.map((question, index) => <fieldset key={question.id} disabled={frozen}>
        <legend>{index + 1}. {question.prompt}</legend>
        {question.choices.map(choice => <label key={choice.id} className="row">
          <input type="radio" name={`answer-${question.id}`} value={choice.id} checked={answers[question.id] === choice.id}
            onChange={() => setAnswers(previous => ({ ...previous, [question.id]: choice.id }))} />
          {choice.text}
        </label>)}
      </fieldset>)}</div>
      <div role="status" aria-live="polite">{sending ? 'Submitting practice…' : attempt ? 'Practice saved.' : 'Answers are not saved until submission succeeds.'}</div>
      {error && <div role="alert"><p>{error} Your selected answers remain in this form. Retry sends the same attempt.</p></div>}
      {!attempt && <button type="submit" className="btn btn--primary" disabled={sending || lesson.questions.some(q => !answers[q.id])}>{error ? 'Retry same submission' : sending ? 'Submitting…' : 'Submit practice'}</button>}
    </form>
    {attempt && <section aria-label="Practice feedback">
      <h3 data-testid="practice-result" data-attempt-id={attempt.attempt_id}>{attempt.correct} / {attempt.total} correct — practice only</h3>
      {attempt.feedback.map(item => <div className="panel panel--sunken" key={item.question_id}>
        <p>{lesson.questions.find(q => q.id === item.question_id)?.prompt ?? item.question_id}</p>
        <Chip tone={item.correct ? 'ok' : 'warn'}>{item.correct ? 'Correct' : 'Review this answer'}</Chip>
        <p>Correct choice: {lesson.questions.find(q => q.id === item.question_id)?.choices.find(c => c.id === item.correct_choice_id)?.text ?? item.correct_choice_id}</p>
        <p>{item.explanation}</p>
      </div>)}
    </section>}
    <button type="button" className="btn" disabled={sending || !canRestart} onClick={onRestart}>{attempt ? 'Start a new attempt' : 'Restart lesson with a new attempt'}</button>
  </Panel>;
}

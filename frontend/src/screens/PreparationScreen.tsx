import { useCallback, useContext, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { BookPreparationOverview } from '@/components/BookPreparationOverview';
import { BookPracticeView } from '@/components/BookPracticeView';
import { BookSavedReview } from '@/components/BookSavedReview';
import { BookHelp } from '@/components/BookUI';
import { useTranslation } from '@/lib/useTranslation';
import { useAdmissionsTarget } from '@/lib/admissionsNavigation';
import { api } from '@/api/client';
import { TeachingText } from '@/components/TeachingText';
import { StudySchedulePanel } from './StudySchedulePanel';
import { PreparationGraphPanel } from './PreparationGraphPanel';
import { SharedRoutePanel } from './SharedRoutePanel';
import { Chip, Empty, Loading, Notice, Panel, SourceLink, StatusChip } from '@/components/primitives';
import { currentApplicantOwner } from '@/lib/applicantStorage';
import { DraftIdentityContext } from '@/lib/draftIdentity';
import type { SharedRouteLeaveRisk } from '@/lib/sharedRouteRecovery';
import { dateTime, eligibilityTone } from '@/lib/format';
import { subscribe, t } from '@/lib/i18n';
import { useStore } from '@/lib/store';
import type {
  PreparationAccess, PreparationAttemptInput, PreparationAttemptReview, PreparationCatalogue, PreparationLesson,
  LearningTaskRef, ClaimScope, PreparationPlan, PreparationProgress, ProgramResult, StudyAttempt,
} from '@/types';

const LEARNING_CATALOGUE_VERSION = 'learning-pack-2026-10-11-v1';
const lessonVersionKey = (id: string, version: string) => JSON.stringify([id, version]);
const ACCESS_REASONS: Record<PreparationAccess['reason'], string> = {
  development_mode: 'Local preview access', subscription_term: 'Included in your current subscription',
  no_eligible_subscription: 'No active preparation subscription',
};
type Mode = 'goals' | 'schedule' | 'shared' | 'practice' | 'progress';
const MODES: { id: Mode; title: string }[] = [
  { id: 'goals', title: 'Goals & evidence' }, { id: 'schedule', title: 'Study plan' },
  { id: 'shared', title: 'Shared route' }, { id: 'practice', title: 'Practice' }, { id: 'progress', title: 'Progress' },
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
export function PreparationScreen({ onProfile, onBilling, onLeaveRisk }: { onProfile?: () => void; onBilling?: () => void; onLeaveRisk?: SharedRouteLeaveRisk }) {
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
    onBilling={onBilling} onLeaveRisk={onLeaveRisk} />;
}

function AccessNotice({ access, onBilling }: { access: PreparationAccess; onBilling?: () => void }) {
  const {locale}=useTranslation();const ru=locale!=='en';
  const reason=ru?({development_mode:'Локальный тестовый доступ',subscription_term:'Доступ в текущем периоде подписки',no_eligible_subscription:'Нет действующего доступа к подготовке'} as Record<string,string>)[access.reason]:ACCESS_REASONS[access.reason];
  if(ru&&access.allowed)return <div className="book-preparation__access" role="note"><Chip tone={access.development_only?'demo':'accent'}>{access.development_only?'Локальный тестовый доступ':'Учебный доступ подтверждён'}</Chip><span>Авторские учебные блоки — не полный экзаменационный курс.</span><details><summary>Об этом доступе</summary><p>IELTS Reading, SAT Math и SAT Reading & Writing. Это не официальный пробный экзамен. {reason??'Источник доступа не подтверждён'}{access.ends_at?` · до ${dateTime(access.ends_at)}`:''}</p></details></div>;
  return <Notice kind={access.development_only?'demo':access.allowed?'info':'warn'}><div>
    <strong>{ru?access.development_only?'Локальные стартовые материалы':access.allowed?'Стартовая подготовка доступна':'Для новых занятий нужен доступ к подготовке':access.development_only?'Development starter access':access.allowed?'Starter preparation included':'Preparation subscription required'}</strong>
    <p className="small">{ru?access.allowed?'Авторские блоки IELTS Reading, SAT Math и SAT Reading & Writing. Это не полный курс и не официальный пробный экзамен.':'Для новой практики нужен действующий доступ к подготовке. Доступ к исследованию не открывает учебные блоки. Сохранённая история остаётся доступной.':access.allowed?'Original IELTS Reading, SAT Math and SAT Reading & Writing practice units. This is not a full exam course or an official mock test.':'An eligible started subscription term is required for new practice. A research case unlock does not grant preparation. Your saved history remains available.'}</p>
    <p className="xs muted">{reason??(ru?'Источник доступа не подтверждён':'Access source not confirmed')}{access.ends_at?` · ${ru?'до':'term ends'} ${dateTime(access.ends_at)}`:''}</p>
    {onBilling&&!access.allowed&&<button type="button" className="btn btn--sm" onClick={onBilling}>{ru?'Посмотреть условия доступа':'View access details'}</button>}
  </div></Notice>;
}

function PreparationCase({ profileId, programmes, onBilling, onLeaveRisk }: {
  profileId: string; programmes: ProgramResult[]; onBilling?: () => void; onLeaveRisk?: SharedRouteLeaveRisk;
}) {
  useSyncExternalStore(subscribe, () => t('shared.nav'));
  const {locale}=useTranslation(); const ru=locale!=='en';
  const [goalsExpanded,setGoalsExpanded]=useState(false);
  const exactTarget = useAdmissionsTarget(); const openedExact = useRef<string | null>(null);
  const [mode, setMode] = useState<Mode>('goals');
  const [sharedActive, setSharedActive] = useState<boolean | null>(null);
  const [sharedReadError, setSharedReadError] = useState(false);
  const [sharedReadRetry, setSharedReadRetry] = useState(0);
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
  const [lastLessonVersion, setLastLessonVersion] = useState<string | undefined>();
  const [reviewSelection, setReviewSelection] = useState<(Pick<StudyAttempt, 'attempt_id' | 'lesson_id' | 'version'> & { id?: string }) | null>(null);
  const [lessonKey, setLessonKey] = useState(0);
  const [submitted, setSubmitted] = useState<string[]>([]);
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [review, setReview] = useState<PreparationAttemptReview | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [reviewError, setReviewError] = useState('');
  const mounted = useRef(false);
  const lessonIntent = useRef(0);
  const progressIntent = useRef(0);
  const reviewIntent = useRef(0);
  const reviewTarget = useRef<string | null>(null);
  const owner = useRef<string | null | undefined>(undefined);
  const isCurrent = useCallback(() => {
    try { return mounted.current && owner.current === currentApplicantOwner(); }
    catch { return false; }
  }, []);
  useEffect(() => {
    mounted.current = true;
    try { owner.current = currentApplicantOwner(); }
    catch { setLoadError('The workspace changed. Sign in again.'); }
    // Capture the stable ref objects, not generation values: cleanup invalidates the latest intent.
    const lessons = lessonIntent; const history = progressIntent; const reviews = reviewIntent;
    return () => { mounted.current = false; ++lessons.current; ++history.current; ++reviews.current; };
  }, []);

  useEffect(() => {
    let active = true;
    setSharedReadError(false);
    api.sharedRouteCurrent(profileId).then(out => {
      if (!active || !isCurrent()) return;
      if (out.profile_id !== profileId || out.view === undefined || !Number.isSafeInteger(out.revision)
        || (out.view === null && out.revision !== 0)
        || (out.view && (out.view.receipt.profile_id !== profileId || out.view.receipt.revision !== out.revision))) {
        setSharedReadError(true); return;
      }
      setSharedActive(old => old === true ? true : !!out.view);
    }).catch(() => { if (active && isCurrent()) setSharedReadError(true); });
    return () => { active = false; };
  }, [profileId, isCurrent, sharedReadRetry]);
  const noteSharedActive = useCallback((active: boolean) => setSharedActive(old => old === true ? true : active), []);

  useEffect(() => {
    let active = true;
    setLoading(true); setLoadError('');
    const intent = ++progressIntent.current;
    Promise.all([api.preparationAccess(profileId), api.preparationCatalogue(LEARNING_CATALOGUE_VERSION), api.preparationProgress(profileId, LEARNING_CATALOGUE_VERSION)])
      .then(([access, catalogue, progress]) => {
        if (!active || !isCurrent() || intent !== progressIntent.current) return;
        if (progress.profile_id !== profileId || progress.attempts.some(item => item.profile_id !== profileId)) throw new Error('The practice history did not match this case.');
        if (catalogue.version !== LEARNING_CATALOGUE_VERSION || catalogue.lessons.some(item => !item.version)
          || progress.catalogue_version !== LEARNING_CATALOGUE_VERSION || !Array.isArray(progress.completed_lessons)) {
          throw new Error('The learning catalogue or history did not match the requested version.');
        }
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
    setMode(next); ++reviewIntent.current; reviewTarget.current = null; setReviewId(null); setReview(null); setReviewLoading(false); setReviewError('');
    if (next === 'progress') void refreshProgress();
  };
  const startLesson = async (id: string, exactVersion?: string) => {
    if (loading || !data?.access.allowed || !isCurrent()) return;
    const summary = data.catalogue.lessons.find(item => item.id === id);
    if (!exactVersion && !summary?.version) { setLessonError('This lesson has no confirmed catalogue version. Reload preparation.'); return; }
    const requestedVersion = exactVersion ?? summary!.version!;
    setLastLessonVersion(requestedVersion);
    const intent = ++lessonIntent.current;
    setMode('practice'); setLesson(null); setLessonError(''); setLessonLoading(true); setLastLessonId(id); ++reviewIntent.current; reviewTarget.current = null; setReviewId(null); setReview(null); setReviewLoading(false); setReviewError('');
    try {
      const next = await api.preparationLesson(profileId, id, requestedVersion);
      if (!isCurrent() || intent !== lessonIntent.current) return;
      if (next.id !== id || next.version !== requestedVersion) throw new Error('The lesson did not match the requested version.');
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
      const progress = await api.preparationProgress(profileId, LEARNING_CATALOGUE_VERSION);
      if (!isCurrent() || intent !== progressIntent.current) return;
      if (progress.profile_id !== profileId || progress.attempts.some(item => item.profile_id !== profileId)) throw new Error('The practice history did not match this case.');
      if (progress.catalogue_version !== LEARNING_CATALOGUE_VERSION || !Array.isArray(progress.completed_lessons)) {
        throw new Error('The saved history did not match the requested learning catalogue.');
      }
      setData(previous => previous ? { ...previous, progress } : previous);
      setLoadError('');
    } catch (error) { if (isCurrent() && intent === progressIntent.current) setLoadError(`Saved history could not refresh: ${message(error)}`); }
    finally { if (isCurrent() && intent === progressIntent.current) setProgressRefreshing(false); }
  };

  const openReview = async (saved: Pick<StudyAttempt, 'attempt_id' | 'lesson_id' | 'version'> & { id?: string }) => {
    const selectionId = saved.id ?? saved.attempt_id;
    if (!isCurrent() || reviewTarget.current === selectionId) return;
    const intent = ++reviewIntent.current;
    reviewTarget.current = selectionId;
    setReviewSelection(saved);
    setReviewId(selectionId); setReview(null); setReviewError(''); setReviewLoading(true);
    try {
      const next = await api.preparationAttemptReview(profileId, saved.attempt_id);
      if (!isCurrent() || intent !== reviewIntent.current) return;
      const accepted = next.attempt;
      if (accepted.profile_id !== profileId || accepted.attempt_id !== saved.attempt_id || (saved.id !== undefined && accepted.id !== saved.id)
        || accepted.lesson_id !== saved.lesson_id || accepted.version !== saved.version
        || (next.lesson && (next.lesson.id !== accepted.lesson_id || next.lesson.version !== accepted.version))) {
        throw new Error('The saved review did not match this case, attempt and lesson version.');
      }
      setReview(next);
    } catch (error) { if (isCurrent() && intent === reviewIntent.current) { reviewTarget.current = null; setReviewError(message(error)); } }
    finally { if (isCurrent() && intent === reviewIntent.current) setReviewLoading(false); }
  };

  const visiblePlan = plan?.profile_id === profileId && plan.result_id === (currentResultId || null) ? plan : null;
  const checks = visiblePlan?.research_access && visiblePlan.evidence_state !== 'locked' ? visiblePlan.checks : [];
  const submittedVersions = new Set([
    ...(data?.progress.completed_lessons ?? []).map(item => lessonVersionKey(item.lesson_id, item.version)), ...submitted,
  ]);
  const activeTrack = data?.catalogue.tracks.find(track => lesson && track.lesson_ids.includes(lesson.id));
  const activeIndex = lesson && activeTrack ? activeTrack.lesson_ids.indexOf(lesson.id) : -1;
  const nextId = activeTrack?.lesson_ids[activeIndex + 1];
  const nextLesson = activeIndex >= 0 && nextId ? data?.catalogue.lessons.find(item => item.id === nextId && item.track_id === activeTrack?.id) : undefined;
  const reviewed = reviewId ? reviewSelection : null;
  const openLearningTarget = (ref: LearningTaskRef) => {
    if (ref.kind === 'lesson') void startLesson(ref.lesson_id, ref.content_version);
    else if (ref.kind === 'attempt_review') {
      chooseMode('progress');
      void openReview({ attempt_id: ref.attempt_id, lesson_id: ref.lesson_id, version: ref.content_version });
    }
  };
  const exactOpeners = useRef({ startLesson, chooseMode, openReview }); exactOpeners.current = { startLesson, chooseMode, openReview };
  const exactKey = exactTarget?.screen === 'preparation' ? JSON.stringify(exactTarget) : null;
  const exactWrongCase = exactKey !== null && exactTarget?.profileId !== profileId;
  useEffect(() => {
    if (!exactKey || openedExact.current === exactKey || exactWrongCase || loading || !data || !isCurrent() || !exactTarget) return;
    const ref = exactTarget.target;
    if (ref.kind !== 'lesson' && ref.kind !== 'attempt_review') return;
    openedExact.current = exactKey;
    if (ref.kind === 'lesson') { if (!data.access.allowed) return; void exactOpeners.current.startLesson(ref.lesson_id, ref.content_version); }
    else { exactOpeners.current.chooseMode('progress'); void exactOpeners.current.openReview({ attempt_id: ref.attempt_id, lesson_id: ref.lesson_id, version: ref.content_version }); }
  }, [exactKey, exactWrongCase, loading, data, isCurrent, exactTarget]);
  const goalEvidence=data&&(<Panel title="Exam goals from your chosen programmes">
        <div className="field"><label htmlFor="preparation-programme">Programme evidence</label>
          <select id="preparation-programme" value={currentResultId} onChange={event => {
            const nextResultId = event.target.value;
            if (nextResultId === currentResultId) return;
            setPlan(null); setPlanError(''); setPlanLoading(true); setResultId(nextResultId);
          }}>
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
            {check.claims.length === 0 && <p className="xs muted">No linked source proves this requirement.</p>}
            {(check.claims.length > 0 || check.source_urls.length > 0) && <details className="preparation-evidence">
              <summary>Source evidence ({check.claims.length + check.source_urls.filter(url => !check.claims.some(claim => claim.source_url === url)).length})</summary>
              <div className="preparation-evidence__content stack">
                {check.claims.map(claim => <div key={claim.id} className="preparation-evidence__claim stack stack--tight">
                  <StatusChip status={claim.status} tone={claim.status === 'VERIFIED_CURRENT' ? 'ok' : 'warn'} />
                  <p className="xs">{claim.original_text_excerpt}</p><SourceLink url={claim.source_url} />
                  <p className="xs muted">Recorded source scope: {claim.scope ? recordedScope(claim.scope) : 'Not recorded — do not assume a match.'}</p>
                  <p className="xs muted">{claim.program || 'Programme not established'} · {claim.intake || 'Intake not established'} · read {dateTime(claim.accessed_at)}</p>
                </div>)}
                {check.source_urls.filter(url => !check.claims.some(claim => claim.source_url === url)).map(url => <SourceLink key={url} url={url} />)}
              </div>
            </details>}
            {check.lesson_ids.map(id => <button key={id} type="button" className="btn btn--sm" disabled={loading || !data.access.allowed || !data.catalogue.lessons.some(item => item.id === id)}
              onClick={() => void startLesson(id)}>Practise: {data.catalogue.lessons.find(item => item.id === id)?.title ?? id}</button>)}
          </section>)}
          <button type="button" className="btn btn--primary" onClick={() => chooseMode('practice')}>Browse original practice</button>
        </>}
      </Panel>);
  return <div className={`preparation-page stack stack--loose${ru?' book-preparation-page':''}${ru&&((mode==='practice'&&lesson)||(mode==='progress'&&review?.lesson))?' book-preparation-page--lesson':''}`}>
    {exactWrongCase && <Notice kind="warn">{t('today.targetMissing')}</Notice>}
    {!(ru&&((mode==='practice'&&lesson)||(mode==='progress'&&review?.lesson)))&&<div className={`screen__head${ru&&mode==='goals'?' book-preparation__header':''}`}><div>
      <p className="screen__eyebrow">{ru?'Дополнительная подготовка':'ORIGINAL PRACTICE · YOUR CASE'}</p>
      <h1 className="screen__title">{ru?'Подготовка под твою цель':'Prepare for your next step.'}</h1>
      <p className="screen__lede">{ru?'Практикуй ключевые навыки и изучай требования выбранных программ. Подготовка необязательна и не подтверждает готовность к экзамену или поступлению.':'Programme requirements, original practice and saved attempts. Practice does not change your official scores or establish admission readiness.'}</p>
    </div>{ru&&mode==='goals'&&<BookHelp><strong>Связь с твоими программами</strong><br/>Применимость экзаменов проверяется по требованиям выбранных программ. Учебный курс остаётся дополнительным.</BookHelp>}</div>}
    {loading && <Loading label="Loading preparation access and history…" />}
    {loadError && <div role="alert"><Notice kind="risk"><div>{loadError}<button className="btn btn--sm" type="button" onClick={() => setReload(n => n + 1)}>Retry preparation loading</button></div></Notice></div>}
    {data && <>
      <AccessNotice access={data.access} onBilling={onBilling} />
      {ru?<details className="book-preparation__navigation" hidden={Boolean(lesson||review?.lesson)} open={mode!=='goals'}><summary>Другие разделы подготовки</summary>
      <nav className="row book-preparation__views" aria-label="Preparation views" hidden={ru&&Boolean(lesson||review?.lesson)}>
        {MODES.map(item => <button type="button" className="btn" key={item.id}
          aria-pressed={mode === item.id} disabled={loading || (item.id === 'progress' && progressRefreshing)} onClick={() => chooseMode(item.id)}>{item.id === 'shared' ? t('shared.nav') : item.id === 'goals' ? t('shared.goalsNav') : ru?({schedule:'Учебный план',practice:'Материалы и практика',progress:'Сохранённые попытки'} as Record<string,string>)[item.id]:item.title}</button>)}
      </nav>
      </details>:<>
      <nav className="row book-preparation__views" aria-label="Preparation views" hidden={ru&&Boolean(lesson||review?.lesson)}>
        {MODES.map(item => <button type="button" className="btn" key={item.id}
          aria-pressed={mode === item.id} disabled={loading || (item.id === 'progress' && progressRefreshing)} onClick={() => chooseMode(item.id)}>{item.id === 'shared' ? t('shared.nav') : item.id === 'goals' ? t('shared.goalsNav') : ru?({schedule:'Учебный план',practice:'Материалы и практика',progress:'Сохранённые попытки'} as Record<string,string>)[item.id]:item.title}</button>)}
      </nav>
      </>}
      <p className="xs muted book-preparation__draft-note">{ru?'Неотправленные ответы остаются только в форме. При выходе из материала они очистятся.':'Unsubmitted answers stay only in this form. Leaving a lesson clears them.'}</p>
      {mode==='goals'&&ru&&<BookPreparationOverview programmes={programmes} catalogue={data.catalogue} access={data.access} checks={checks} submitted={submittedVersions} evidenceState={visiblePlan?.evidence_state??null} loadingEvidence={planLoading} onProgramme={id=>{if(id!==currentResultId){setPlan(null);setPlanLoading(true);setPlanError('');setResultId(id);}setGoalsExpanded(true);}} onEvidence={()=>setGoalsExpanded(true)} onLesson={id=>void startLesson(id)}/>}
      {mode==='goals'&&(ru?<details className="book-preparation__evidence" open={goalsExpanded} onToggle={event=>setGoalsExpanded(event.currentTarget.open)}><summary>Требования, источники и применимость экзамена</summary>{goalEvidence}</details>:goalEvidence)}
      {mode === 'schedule' && (sharedActive === null ? <Panel title={t('shared.legacyHistory')}>
          {sharedReadError ? <div role="alert"><p>{t('shared.legacyUnknown')}</p><button type="button" className="btn btn--sm" onClick={() => setSharedReadRetry(n => n + 1)}>{t('shared.refresh')}</button></div> : <p>{t('shared.loading')}</p>}
          <details><summary>{t('shared.legacyHistory')}</summary><fieldset disabled style={{ border: 0, padding: 0, minWidth: 0 }}>
            <StudySchedulePanel profileId={profileId} allowed={!loading && data.access.allowed}
              isCurrent={isCurrent} onLesson={id => void startLesson(id)} onLearningTarget={openLearningTarget} />
          </fieldset></details>
        </Panel>
        : sharedActive ? <details><summary>{t('shared.legacyHistory')}</summary>
          <p className="small">{t('shared.legacyInactive')}</p>
          <fieldset disabled style={{ border: 0, padding: 0, minWidth: 0 }}><StudySchedulePanel profileId={profileId}
            allowed={!loading && data.access.allowed} isCurrent={isCurrent}
            onLesson={id => void startLesson(id)} onLearningTarget={openLearningTarget} /></fieldset>
        </details> : <StudySchedulePanel profileId={profileId} allowed={!loading && data.access.allowed}
          isCurrent={isCurrent} onLesson={id => void startLesson(id)} onLearningTarget={openLearningTarget} />)}
      <div hidden={mode !== 'shared'}><SharedRoutePanel profileId={profileId} programmes={programmes} progress={data.progress}
        allowed={!loading && data.access.allowed} isCurrent={isCurrent} onTarget={openLearningTarget} onActive={noteSharedActive}  onLeaveRisk={onLeaveRisk} /></div>
      {mode === 'practice' && <>
        {lessonLoading && <Loading label="Opening the original lesson…" />}
        {lessonError && <div role="alert">{lessonError}<button type="button" className="btn btn--sm" onClick={() => void startLesson(lastLessonId, lastLessonVersion)}>Retry lesson</button></div>}
        {lesson ? <PracticeSession key={lessonKey} profileId={profileId} lesson={lesson} onSaved={saved => {
          setSubmitted(previous => [...new Set([...previous, lessonVersionKey(saved.lesson_id, saved.version)])]);
          void refreshProgress();
        }} unitLabel={activeTrack ? `${activeTrack.title} · Original practice unit · Lesson ${activeIndex + 1} of ${activeTrack.lesson_ids.length}` : 'Original practice unit'}
          nextLesson={nextLesson} onNext={() => { if (nextLesson) void startLesson(nextLesson.id); }}
          onRestart={() => void startLesson(lesson.id, lesson.version)} canRestart={!loading && data.access.allowed} bookLessons={data.catalogue.lessons.filter(item=>item.track_id===lesson.track_id)} submittedVersions={submittedVersions} onBack={()=>chooseMode('goals')} onLesson={id=>void startLesson(id)} /> : <Panel title={ru?"Стартовые учебные материалы":"Original starter lessons"} hint={data.catalogue.notice}>
          <p className="small">{ru?"Авторские учебные блоки. Сохранённая работа не подтверждает освоение навыка и не является официальным баллом. Это не полные курсы IELTS или SAT.":"Ordered original practice units. A saved submission is not mastery or an exam diagnosis. These units are not full IELTS or SAT courses."}</p>
          <div className="stack">{data.catalogue.tracks.map(track => <section key={track.id} aria-label={`${track.title} learning path`}>
            <h3>{track.title}</h3>
            <ol className="preparation-learning-path">{track.lesson_ids.map(id => data.catalogue.lessons.find(item => item.id === id && item.track_id === track.id)).map(item => item ? <li key={item.id} data-version={item.version}>
              <div className="row">
                <span>{item.title} · {item.question_count} questions</span>
                {item.version && submittedVersions.has(lessonVersionKey(item.id, item.version)) && <Chip>{ru?"Практика сохранена":"Saved submission"}</Chip>}
                <button type="button" className="btn btn--sm" disabled={loading || !data.access.allowed || lessonLoading || !item.version}
                  data-lesson-id={item.id} data-version={item.version} onClick={() => void startLesson(item.id)}>{ru?"Открыть":"Start"} {item.title}</button>
              </div>
            </li> : null)}</ol>
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
      {mode === 'progress' && (ru&&review?.lesson?<BookSavedReview key={review.attempt.attempt_id} lesson={review.lesson} attempt={review.attempt} notice={review.notice} canRestart={data.access.allowed&&!loading} onRestart={()=>void startLesson(review.lesson!.id,review.lesson!.version)} onBack={()=>{++reviewIntent.current;reviewTarget.current=null;setReviewId(null);setReview(null);setReviewError('');setReviewLoading(false);}}/>:<Panel title={ru?"Сохранённая практика":"Your saved practice"} hint={ru?"Сохранение подтверждает отправку работы, а не освоение навыка. Это не официальные баллы экзамена.":"Completed means submitted, not mastered. These results are not official exam scores."}>
        <button type="button" className="btn btn--sm" disabled={progressRefreshing} onClick={() => void refreshProgress()}>{ru?"Обновить историю":"Refresh saved history"}</button>
        {progressRefreshing && <Loading label="Refreshing saved practice…" />}
        <p data-testid="progress-summary">{data.progress.attempt_count} saved attempts · {data.progress.completed_lessons?.filter(item => data.catalogue.lessons.some(summary => summary.id === item.lesson_id && summary.version === item.version)).length ?? 0} practice lessons submitted.</p>
        <p>{data.progress.correct} correct answers out of {data.progress.answered} answered across saved attempts.</p>
        {data.progress.attempts.length === 0 ? <Empty title="No submitted practice yet">Start an original lesson to build your history.</Empty>
          : <ol>{data.progress.attempts.map((attempt, index) => <li key={attempt.id} data-version={attempt.version}>
            {data.catalogue.lessons.find(item => item.id === attempt.lesson_id && item.version === attempt.version)?.title ?? 'Archived lesson'}: {attempt.correct} / {attempt.total} correct · {dateTime(attempt.created_at)}
            <button type="button" className="btn btn--sm" data-testid="review-attempt" data-attempt-id={attempt.attempt_id}
              aria-pressed={reviewId === attempt.id} onClick={() => void openReview(attempt)}>{ru?"Открыть сохранённый разбор":"Review saved attempt"} {index + 1}</button>
          </li>)}</ol>}
        {reviewed && <section aria-label="Saved attempt review" className="stack" aria-busy={reviewLoading}>
          {reviewLoading && <Loading label="Loading saved attempt review…" />}
          {reviewError && <div role="alert">{reviewError}<button type="button" className="btn btn--sm" onClick={() => void openReview(reviewed)}>Retry saved review</button></div>}
          {review && <>
            <h3 data-testid="saved-attempt-review" data-attempt-id={review.attempt.attempt_id}>{review.attempt.correct} / {review.attempt.total} correct — practice only</h3>
            <p className="small">{review.lesson?.title ?? 'Archived lesson'} · your saved answers and feedback.</p>
            <details className="preparation-evidence"><summary>Material details</summary>
              <p className="xs muted">Recorded lesson: {review.attempt.lesson_id} · content version: {review.attempt.version}</p>
            </details>
            <p className="small">{review.notice}</p>
            {!review.lesson && <p className="small">Original question text is unavailable for this saved version. Stored IDs and feedback remain below.</p>}
            {review.lesson && <details className="preparation-evidence"><summary>Original teaching material</summary>
              <TeachingText text={review.lesson.introduction} />
            </details>}
            <AttemptFeedback attempt={review.attempt} lesson={review.lesson ?? undefined} />
          </>}
          <button type="button" className="btn" onClick={() => { ++reviewIntent.current; reviewTarget.current = null; setReviewId(null); setReview(null); setReviewError(''); setReviewLoading(false); }}>Close saved review</button>
        </section>}
      </Panel>)}
    </>}
    {mode==='goals'&&(ru?<details className="book-preparation__evidence"><summary>Подробный маршрут подготовки и обязательные действия</summary><PreparationGraphPanel profileId={profileId} programmes={programmes} isCurrent={isCurrent}/></details>:<PreparationGraphPanel profileId={profileId} programmes={programmes} isCurrent={isCurrent}/>)}
  </div>;
}

function PracticeSession({ profileId, lesson, onSaved, onRestart, canRestart, unitLabel, nextLesson, onNext, bookLessons, submittedVersions, onBack, onLesson }: {
  profileId: string; lesson: PreparationLesson; onSaved: (attempt: StudyAttempt) => void; onRestart: () => void; canRestart: boolean;
  unitLabel: string; nextLesson?: PreparationCatalogue['lessons'][number]; onNext: () => void;
  bookLessons:PreparationCatalogue['lessons']; submittedVersions:Set<string>; onBack:()=>void; onLesson:(id:string)=>void;
}) {
  const {locale}=useTranslation(); const ru=locale!=='en';
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [materialOnly, setMaterialOnly] = useState(ru);
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
    if (!isCurrent() || inFlight.current || attempt || lesson.questions.some(q => !answers[q.id]?.trim() || answers[q.id]!.length > 100)) return;
    const payload = pending.current ?? {
      attempt_id: crypto.randomUUID(), lesson_id: lesson.id, version: lesson.version,
      answers: lesson.questions.map(q => 'answer_format' in q
        ? { question_id: q.id, text: answers[q.id]! } : { question_id: q.id, choice_id: answers[q.id]! }),
    };
    pending.current = payload;
    inFlight.current = true; setSending(true); setError('');
    try {
      const next = await api.submitPreparation(profileId, payload);
      if (!isCurrent()) return;
      const sameAnswers = next.answers.length === payload.answers.length && next.answers.every((answer, index) => {
        const sent = payload.answers[index];
        if (!sent || sent.question_id !== answer.question_id) return false;
        return 'text' in sent ? 'text' in answer && sent.text === answer.text
          : 'choice_id' in answer && sent.choice_id === answer.choice_id;
      });
      if (next.profile_id !== profileId || next.lesson_id !== lesson.id || next.version !== lesson.version || next.attempt_id !== payload.attempt_id
        || !sameAnswers) {
        throw new Error('The saved attempt did not match this case and lesson.');
      }
      setAttempt(next); onSaved(next);
    } catch (problem) { if (isCurrent()) setError(message(problem)); }
    finally { inFlight.current = false; if (isCurrent()) setSending(false); }
  };
  const frozen = sending || Boolean(error && pending.current) || Boolean(attempt);
  if(ru)return <BookPracticeView lesson={lesson} lessons={bookLessons} submitted={submittedVersions} answers={answers} materialOnly={materialOnly} frozen={frozen} sending={sending} error={error} attempt={attempt} nextLesson={nextLesson} canRestart={canRestart} onMaterial={setMaterialOnly} onAnswer={(id,value)=>setAnswers(previous=>({...previous,[id]:value}))} onSubmit={()=>void submit()} onRestart={onRestart} onNext={onNext} onBack={onBack} onLesson={onLesson}/>;
  return <Panel title={lesson.title} hint="Original practice. No official IELTS band or SAT scaled score is produced.">
    <p className="small" data-version={lesson.version}>{unitLabel}</p>
    <nav className="section-nav" aria-label="Lesson view"><button type="button" className="btn btn--ghost" aria-pressed={materialOnly} onClick={() => setMaterialOnly(true)}>Learning material</button><button type="button" className="btn btn--ghost" aria-pressed={!materialOnly} onClick={() => setMaterialOnly(false)}>Practice & feedback</button></nav>
    <TeachingText text={lesson.introduction} />
    {materialOnly && <div className="lesson-material-action"><p className="small muted">Read at your own pace. Opening the material does not mark a lesson as completed.</p><button type="button" className="btn btn--primary" onClick={() => setMaterialOnly(false)}>Continue to practice</button></div>}
    <div hidden={materialOnly}>
    <form onSubmit={event => { event.preventDefault(); void submit(); }}>
      <div className="stack">{lesson.questions.map((question, index) => <fieldset key={question.id} className="preparation-question" disabled={frozen}>
        <legend>{index + 1}. {question.prompt}</legend>
        {'answer_format' in question ? <div className="field">
          <label htmlFor={`answer-${question.id}`}>Answer {index + 1}</label>
          <input id={`answer-${question.id}`} type="text" autoComplete="off" maxLength={100}
            aria-describedby={`instruction-${question.id}`} value={answers[question.id] ?? ''}
            onChange={event => setAnswers(previous => ({ ...previous, [question.id]: event.target.value }))} />
          <p className="xs muted" id={`instruction-${question.id}`}>Use no more than {question.max_words} words or numbers, following this lesson’s instructions.</p>
        </div> : question.choices.map(choice => <label key={choice.id} className="preparation-choice">
          <input type="radio" name={`answer-${question.id}`} value={choice.id} checked={answers[question.id] === choice.id}
            onChange={() => setAnswers(previous => ({ ...previous, [question.id]: choice.id }))} />
          {choice.text}
        </label>)}
      </fieldset>)}</div>
      <div role="status" aria-live="polite">{sending ? 'Submitting practice…' : attempt ? 'Practice saved.' : 'Answers are not saved until submission succeeds.'}</div>
      {error && <div role="alert"><p>{error} Your selected answers remain in this form. Retry sends the same attempt.</p></div>}
      {!attempt && <button type="submit" className="btn btn--primary" disabled={sending || lesson.questions.some(q => !answers[q.id]?.trim() || answers[q.id]!.length > 100)}>{error ? 'Retry same submission' : sending ? 'Submitting…' : 'Submit practice'}</button>}
    </form>
    {attempt && <section aria-label="Practice feedback">
      <h3 data-testid="practice-result" data-attempt-id={attempt.attempt_id}>{attempt.correct} / {attempt.total} correct — practice only</h3>
      <p className="small">Review incorrect answers first. Repeating known items is review, not an unseen diagnostic.</p>
      <AttemptFeedback attempt={attempt} lesson={lesson} />
    </section>}
    {attempt && nextLesson?.version && <button type="button" className="btn btn--primary" data-testid="next-lesson"
      data-lesson-id={nextLesson.id} data-version={nextLesson.version} disabled={sending || !canRestart} onClick={onNext}>Next lesson: {nextLesson.title}</button>}
    {attempt && !nextLesson && <p className="small">End of this original practice unit. This does not establish mastery or exam readiness.</p>}
    <button type="button" className="btn" disabled={sending || !canRestart} onClick={onRestart}>{attempt ? 'Start a new attempt' : 'Restart lesson with a new attempt'}</button>
    </div>
  </Panel>;
}

/** Review uses accepted feedback and the server's exact immutable lesson, never current-version reconstruction. */
function AttemptFeedback({ attempt, lesson }: { attempt: StudyAttempt; lesson?: PreparationLesson }) {
  const matchingLesson = lesson?.id === attempt.lesson_id && lesson.version === attempt.version ? lesson : undefined;
  return <div className="stack">{[...attempt.feedback].sort((a, b) => Number(a.correct) - Number(b.correct)).map(item => {
    const question = matchingLesson?.questions.find(q => q.id === item.question_id);
    const choices = question && 'choices' in question ? question.choices : undefined;
    const selected = 'selected_text' in item ? item.selected_text : choices?.find(c => c.id === item.selected_choice_id)?.text ?? `Choice ID: ${item.selected_choice_id}`;
    const correct = 'accepted_answers' in item ? item.accepted_answers.join(' / ') : choices?.find(c => c.id === item.correct_choice_id)?.text ?? `Choice ID: ${item.correct_choice_id}`;
    return <div className="panel panel--sunken" data-testid="feedback-item" data-correct={String(item.correct)} key={item.question_id}>
      <p>{question?.prompt ?? `Stored question: ${item.question_id}`}</p>
      <Chip tone={item.correct ? 'ok' : 'warn'}>{item.correct ? 'Correct' : 'Review this answer'}</Chip>
      <p>Your answer: {selected}</p><p>Correct answer: {correct}</p><p>{item.explanation}</p>
    </div>;
  })}</div>;
}

import { AdmissionsTodayPanel } from '@/components/AdmissionsTodayPanel';
import { useStore } from '@/lib/store';
import { useTranslation } from '@/lib/useTranslation';
import type { ScreenId } from '@/App';

type HomeScreenProps = { onNavigate: (screen: ScreenId) => void };

/** A single next step, selected only from real case/run state. */
export function HomeScreen({ onNavigate }: HomeScreenProps) {
  const { t } = useTranslation();
  const { savedProfile, run, results, summary, hydrated, capabilities } = useStore();
  const selected = results.filter((result) => result.user_decision === 'approved' || result.user_decision === 'maybe');
  const needsAttention = run && (run.stale || run.cancelled
    || ['failed', 'retryable_failed', 'cancelled'].includes(run.stage)
    || ['failed', 'dead', 'cancelled'].includes(run.job_status ?? ''));
  const active = run?.job_status === 'running' || run?.job_status === 'queued' || run?.job_running;
  const emptyResearch = run && ['awaiting_user_decision', 'completed'].includes(run.stage) && !results.length;
  const documentsReady = selected.length > 0 && selected.every((result) => result.checklist);
  const next: { title: string; detail: string; action: string; screen: ScreenId } = !savedProfile
    ? {
      title: 'Build your profile',
      detail: 'Tell us what you want to study so your research starts with your own goals.',
      action: 'Create profile', screen: 'profile',
    }
    : needsAttention || emptyResearch
      ? {
        title: needsAttention ? 'Your research needs attention' : 'Review your research findings',
        detail: 'Review where the research stopped and what remains unknown before choosing your next step.',
        action: 'Review research', screen: 'progress',
      }
      : active
      ? {
        title: 'Your research is in progress',
        detail: 'Follow what has been checked and see any source limitations as they appear.',
        action: 'View progress', screen: 'progress',
      }
      : documentsReady
        ? {
          title: 'Work through your document checklists',
          detail: 'Review the requirements and unresolved questions for your selected programmes. A collected checklist does not mean an application is ready.',
          action: 'Open documents', screen: 'documents',
        }
      : results.length > 0 && selected.length > 0
        ? {
          title: 'Plan your next steps',
          detail: 'Collect the document requirements for the programmes you selected.',
          action: 'Open plan', screen: 'approved',
        }
        : results.length > 0
          ? {
            title: 'Review your matches',
            detail: 'Compare confirmed information and choose which programmes to keep.',
            action: 'Explore matches', screen: 'shortlist',
          }
          : {
            title: 'Set your preferences',
            detail: 'Choose your priorities and budget before starting university research.',
            action: 'Set preferences', screen: 'preferences',
          };

  if (!hydrated) return <div className="home-loading" role="status">Loading your journey…</div>;

  return (
    <div className="home-page">
      <div className="home-hero">
        <div className="home-hero__copy">
          <span className="home-eyebrow">YOUR UNIMATCH JOURNEY</span>
          <h1>Good to see you<span className="accent-dot">.</span></h1>
          <p>Your global journey is taking shape. We keep the research clear so you can focus on your next move.</p>
          {capabilities?.demo_mode && <span className="home-demo">Demo data · sample findings</span>}
        </div>
      </div>

      {savedProfile && <AdmissionsTodayPanel />}

      <section className="home-next" aria-labelledby="home-next-title">
        <div>
          <span className="home-eyebrow">YOUR NEXT STEP</span>
          <h2 id="home-next-title">{next.title}</h2>
          <p>{next.detail}</p>
        </div>
        <button className="btn btn--primary" type="button" onClick={() => onNavigate(next.screen)}>
          {next.action} <span aria-hidden="true">→</span>
        </button>
      </section>

      <div className="home-overview" aria-label="Your current research">
        <div><strong>{results.length}</strong><span>Programmes found</span></div>
        <div><strong>{selected.length}</strong><span>Saved for a closer look</span></div>
        <div><strong>{summary?.with_open_questions ?? 0}</strong><span>Open questions</span></div>
      </div>

      <section className="home-path" aria-labelledby="home-path-title">
        <div>
          <span className="home-eyebrow">EXPLORE YOUR PATH</span>
          <h2 id="home-path-title">A clearer way forward.</h2>
        </div>
        <div className="home-path__actions">
          <button type="button" onClick={() => onNavigate('profile')}>Profile <span aria-hidden="true">↗</span></button>
          <button type="button" onClick={() => onNavigate('sources')} disabled={!results.length}>Evidence <span aria-hidden="true">↗</span></button>
          <button type="button" onClick={() => onNavigate('discover')}>Meet students <span aria-hidden="true">↗</span></button>
          <button type="button" onClick={() => onNavigate('preparation')}>{t('preparation.optionalLink')} <span aria-hidden="true">↗</span></button>
        </div>
        <p className="small muted">{t('preparation.optionalHint')}</p>
      </section>
    </div>
  );
}

import { useStore } from '@/lib/store';
import { useTranslation } from '@/lib/useTranslation';
import { redesignCopy } from '@/lib/redesignCopy';
import { Loading } from '@/components/primitives';
import type { ScreenId } from '@/App';

export function CaseScreen({ onNavigate }: { onNavigate: (screen: ScreenId) => void }) {
  const { savedProfile, run, results, summary, dirty, hydrated } = useStore();
  const { locale } = useTranslation();
  const c = redesignCopy[locale];
  if (!hydrated) return <Loading label={c.connecting} />;
  const running = Boolean(run?.job_running || run?.job_status === 'queued' || run?.job_status === 'running');
  const failed = Boolean(run?.cancelled || run?.stage === 'failed' || run?.job_status === 'failed' || run?.job_status === 'dead');
  const next: { title: string; body: string; action: string; target: ScreenId } =
    failed ? { title: c.failed, body: c.failedBody, action: c.progress, target: 'progress' } :
    running ? { title: c.working, body: c.workingBody, action: c.progress, target: 'progress' } :
    results.length ? { title: c.ready, body: c.readyBody, action: c.review, target: 'shortlist' } :
    savedProfile ? { title: c.preferences, body: c.preferencesBody, action: c.preferences, target: 'preferences' } :
    { title: c.prepare, body: c.prepareBody, action: c.edit, target: 'profile' };
  const selected = results.filter((r) => r.user_decision === 'approved' || r.user_decision === 'maybe').length;
  const steps: { title: string; hint: string; status: string; target: ScreenId }[] = [
    { title: c.profile, hint: c.profileHint, status: savedProfile && !dirty ? c.saved : c.draft, target: 'profile' },
    { title: c.research, hint: c.researchHint, status: failed ? c.failed : running ? c.working : results.length ? c.available : c.notStarted, target: run ? 'progress' : savedProfile ? 'preferences' : 'profile' },
    { title: c.documents, hint: c.documentsHint, status: selected ? `${selected} · ${c.selected}` : c.notStarted, target: results.length ? 'approved' : 'profile' },
  ];
  return <div className="case-home">
    <header className="case-intro">
      <p className="screen__eyebrow">ASHYQ APPLY / {c.chapter}</p>
      <h1>{c.title}</h1>
      <p className="screen__lede">{c.intro}</p>
    </header>
    <section className="case-next" aria-labelledby="next-step-title">
      <div className="case-next__mark" aria-hidden="true">↗</div>
      <div>
        <p className="screen__eyebrow">{c.next}</p>
        <h2 id="next-step-title">{next.title}</h2>
        <p className="case-next__body">{next.body}</p>
        <button className="btn btn--primary" onClick={() => onNavigate(next.target)}>{next.action} <span aria-hidden="true">→</span></button>
      </div>
    </section>
    <section aria-labelledby="case-route">
      <h2 id="case-route" className="case-section-title">{c.route}</h2>
      <ol className="case-route">
        {steps.map((step, i) => <li key={step.title}>
          <button className="case-step" onClick={() => onNavigate(step.target)}>
            <span className="case-step__number" aria-hidden="true">0{i + 1}</span>
            <span className="case-step__content"><strong>{step.title}</strong><span>{step.hint}</span><small>{step.status}</small></span>
            <span aria-hidden="true">↗</span>
          </button>
        </li>)}
      </ol>
    </section>
    {results.length > 0 && <section aria-labelledby="case-overview">
      <h2 id="case-overview" className="case-section-title">{c.overview}</h2>
      <dl className="case-metrics">
        {[[c.programmes, results.length], [c.selected, selected], [c.questions, summary?.with_open_questions ?? null]].map(([label, value]) =>
          <div key={label}><dt>{label}</dt><dd>{value ?? c.unavailable}</dd></div>)}
      </dl>
    </section>}
    <aside className="case-evidence"><span aria-hidden="true">↳</span><div><h2>{c.evidence}</h2><p>{c.evidenceBody}</p></div></aside>
    {(dirty || savedProfile) && <p className="small muted">{dirty ? c.draftNote : c.savedNote}</p>}
  </div>;
}

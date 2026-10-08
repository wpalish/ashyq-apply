import type { ProgrammePlan } from '@/lib/applicationPlan';
import { date } from '@/lib/format';

const OWNER: Record<string, string> = {
  applicant: 'You', school: 'Your school', recommender: 'Your referee', third_party: 'A third party',
};

/** Applicant preparation, kept separate from eligibility and submission. */
export function ApplicationNextAction({ plan, onOpenDocuments }: {
  plan: ProgrammePlan;
  onOpenDocuments: (resultId: string) => void;
}) {
  const next = plan.nextItem;
  return (
    <section className="stack stack--tight" aria-label={`Preparation for ${plan.university}`}>
      <div className="row" style={{ justifyContent: 'space-between', marginTop: 'var(--space-3)' }}>
        <strong className="small">{plan.prepared} of {plan.total} items marked prepared</strong>
        {plan.status !== 'not_collected' && (
          <button className="btn btn--sm" type="button" onClick={() => onOpenDocuments(plan.resultId)}>
            Open documents
          </button>
        )}
      </div>
      {plan.status === 'not_collected' ? <p className="small muted">Collect this programme’s requirements to build your preparation plan.</p>
        : next ? (
          <div className="panel panel--sunken">
            <span className="home-eyebrow">NEXT ACTION</span>
            <h3 className="small">Prepare {next.item.name}</h3>
            <p className="xs muted">{OWNER[next.item.owner] ?? next.item.owner} · {next.item.purpose === 'both' ? 'Admission and scholarship requirements' : next.item.purpose === 'scholarship' ? 'Scholarship requirements' : 'Admission requirements'}</p>
            {(next.item.lead_time_days ?? 0) > 0 && <p className="xs muted">Allow approximately {next.item.lead_time_days} days. This is a planning estimate.</p>}
            {next.item.deadline && <p className="xs">Listed document deadline: {date(next.item.deadline)}</p>}
            {next.item.source_url && /^https?:\/\//i.test(next.item.source_url) && <a className="xs" href={next.item.source_url} target="_blank" rel="noreferrer">View requirement source ↗</a>}
          </div>
        ) : plan.status === 'review_submission' ? (
          <p className="small muted">Your listed items are marked prepared. Review the official application portal and confirm its requirements before submitting.</p>
        ) : <p className="small muted">Check the unresolved requirements and dependencies before choosing your next task.</p>}
      {plan.status === 'needs_review' && <p className="xs muted">Requirements still need review: {plan.reviewReasons.join(' · ')}.</p>}
      {plan.status !== 'not_collected' && <p className="xs faint">Marks record your preparation; they do not verify documents or submit an application.</p>}
    </section>
  );
}

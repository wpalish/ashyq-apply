/**
 * Screen 07 — Approved universities.
 *
 * The decision ledger. Rejected rows stay visible with their reason, because
 * "why did I rule this out in March" is a real question in October.
 */

import { Chip, Empty, Notice, Panel, StatusChip } from '@/components/primitives';
import { date, eligibilityTone, fundingClassTone, money } from '@/lib/format';
import { useStore } from '@/lib/store';
import type { ProgramResult, UserDecision } from '@/types';

export function ApprovedScreen({ onCollect }: { onCollect: () => void }) {
  const { results, run, collectDocuments, decide } = useStore();

  const group = (d: UserDecision) => results.filter((r) => r.user_decision === d);
  const approved = group('approved');
  const maybe = group('maybe');
  const rejected = group('rejected');
  const shortlisted = approved.length + maybe.length;
  // A queued job counts as collecting: the worker has not claimed it yet, but
  // the request has been made and the button must not invite a second one.
  const collecting =
    run?.job_status === 'queued' || run?.job_status === 'running' ||
    (run?.stage === 'document_collection' && run.job_running);

  if (results.length === 0) return <Empty title="No results yet">Run the research first.</Empty>;

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">Step 07</p>
        <h1 className="screen__title">Your decisions</h1>
        <p className="screen__lede">
          Documents are collected only for what you shortlist. It is the slowest step, so it runs
          on the handful you actually intend to apply to.
        </p>
      </div>

      <div className="stack stack--loose">
        <Panel>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <div className="row">
              <Chip tone="ok">{approved.length} approved</Chip>
              <Chip tone="warn">{maybe.length} maybe</Chip>
              <Chip tone="risk">{rejected.length} rejected</Chip>
              <Chip>{results.length - shortlisted - rejected.length} undecided</Chip>
            </div>
            <button
              className="btn btn--primary"
              disabled={shortlisted === 0 || collecting}
              onClick={async () => {
                await collectDocuments();
                onCollect();
              }}
              data-testid="collect-documents"
            >
              {collecting ? 'Collecting…' : `Collect documents for ${shortlisted} programmes`}
            </button>
          </div>
          {shortlisted === 0 && (
            <Notice kind="info">
              <div>Approve or mark “maybe” on at least one programme in the shortlist first.</div>
            </Notice>
          )}
        </Panel>

        {[
          { label: 'Approved', rows: approved, tone: 'ok' as const },
          { label: 'Maybe', rows: maybe, tone: 'warn' as const },
        ].map(({ label, rows, tone }) =>
          rows.length > 0 ? (
            <Panel key={label} title={`${label} (${rows.length})`}>
              <div className="stack stack--tight">
                {rows.map((r) => <DecidedRow key={r.id} result={r} tone={tone} onChange={decide} />)}
              </div>
            </Panel>
          ) : null,
        )}

        {rejected.length > 0 && (
          <Panel
            title={`Rejected (${rejected.length})`}
            hint="Kept on purpose. These are not proposed again unless something material changes."
          >
            <div className="stack stack--tight">
              {rejected.map((r) => (
                <div key={r.id} className="row" style={{ justifyContent: 'space-between', opacity: 0.75 }}>
                  <div>
                    <span className="small"><strong>{r.university}</strong> — {r.program}</span>
                    {r.user_decision_reason && <div className="xs muted">{r.user_decision_reason}</div>}
                    {r.user_notes && <div className="xs faint">{r.user_notes}</div>}
                  </div>
                  <button
                    className="btn btn--sm"
                    onClick={() => decide(r.id, 'undecided', '', r.user_notes)}
                  >
                    Undo
                  </button>
                </div>
              ))}
            </div>
          </Panel>
        )}
      </div>
    </>
  );
}

function DecidedRow({
  result, tone, onChange,
}: {
  result: ProgramResult;
  tone: 'ok' | 'warn';
  onChange: (id: string, d: UserDecision, reason: string, notes: string) => Promise<void>;
}) {
  const g = result.funding_gap;
  return (
    <div className="panel panel--sunken" data-testid={`approved-${result.id}`}>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600 }}>{result.university}</div>
          <div className="small muted">{result.program} · {result.city}, {result.country}</div>
        </div>
        <div className="row row--tight">
          <Chip tone={tone}>{result.user_decision}</Chip>
          <button
            className="btn btn--sm"
            onClick={() => onChange(result.id, 'undecided', '', result.user_notes)}
          >
            Undo
          </button>
        </div>
      </div>
      <div className="row row--tight" style={{ marginTop: 'var(--space-3)' }}>
        <StatusChip status={result.eligibility} tone={eligibilityTone[result.eligibility]} />
        <StatusChip
          status={result.best_funding_classification}
          tone={fundingClassTone[result.best_funding_classification]}
        />
        <span className="num xs">
          remaining {g?.computable && g.gap ? money(g.gap) : 'not computable'}
        </span>
        <span className="num xs muted">
          deadline {result.admission_deadline ? date(result.admission_deadline) : 'not found'}
        </span>
        {result.checklist && <Chip tone="accent">checklist ready</Chip>}
      </div>
      {result.user_notes && <p className="xs faint" style={{ marginTop: 8 }}>{result.user_notes}</p>}
    </div>
  );
}

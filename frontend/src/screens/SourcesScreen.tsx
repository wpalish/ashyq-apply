/**
 * Screen 09 — Sources and conflicts.
 *
 * Everything the pipeline could not settle, in one place, with a drafted
 * question for each. Contradictions are shown, never resolved silently.
 */

import { useMemo, useState } from 'react';
import { Chip, Empty, Notice, Panel, SourceLink, StatusChip } from '@/components/primitives';
import { claimStatusTone, dateTime } from '@/lib/format';
import { useStore } from '@/lib/store';

export function SourcesScreen() {
  const { results } = useStore();
  const [copied, setCopied] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'conflicts' | 'questions' | 'stale'>('all');

  const conflicts = useMemo(
    () => results.flatMap((r) => r.conflicts.map((c) => ({ result: r, conflict: c }))),
    [results],
  );
  const questions = useMemo(
    () => results.flatMap((r) => r.unresolved.map((q) => ({ result: r, question: q }))),
    [results],
  );
  const stale = useMemo(
    () => results.flatMap((r) => r.claims.filter((c) => c.is_stale).map((c) => ({ result: r, claim: c }))),
    [results],
  );
  const allSources = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of results) for (const u of r.source_urls) map.set(u, (map.get(u) ?? 0) + 1);
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }, [results]);

  if (results.length === 0) return <Empty title="No results yet">Run the research first.</Empty>;

  const copy = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      window.setTimeout(() => setCopied(null), 2000);
    } catch {
      setCopied(null);
    }
  };

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">Step 06</p>
        <h1 className="screen__title">What we could not settle</h1>
        <p className="screen__lede">
          When two official pages disagree, UniMatch shows both and marks the more specific one as
          preferred — it does not pick a winner. Each contradiction comes with a ready-to-send
          question for the admissions office.
        </p>
      </div>

      <div className="stack stack--loose">
        <div className="row">
          {([
            ['all', `All (${conflicts.length + questions.length})`],
            ['conflicts', `Conflicts (${conflicts.length})`],
            ['questions', `Open questions (${questions.length})`],
            ['stale', `Ageing claims (${stale.length})`],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              className="btn btn--sm"
              style={filter === id ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : undefined}
              onClick={() => setFilter(id)}
              data-testid={`filter-${id}`}
            >
              {label}
            </button>
          ))}
        </div>

        {(filter === 'all' || filter === 'conflicts') && (
          <Panel title={`Sources that disagree (${conflicts.length})`}>
            {conflicts.length === 0 ? (
              <p className="muted small">No contradictions were found between official sources.</p>
            ) : (
              <div className="stack" data-testid="conflict-list">
                {conflicts.map(({ result, conflict }, i) => (
                  <div key={i} className="panel panel--sunken">
                    <div className="row" style={{ justifyContent: 'space-between' }}>
                      <div>
                        <strong className="small">{result.university}</strong>
                        <div className="xs muted">{conflict.subject}</div>
                      </div>
                      <Chip tone="risk">unresolved</Chip>
                    </div>
                    <div className="stack stack--tight" style={{ marginTop: 'var(--space-3)' }}>
                      {conflict.values.map((v, j) => (
                        <div key={j} className="row row--tight">
                          <Chip mono tone={conflict.source_urls[j] === conflict.preferred_claim_id ? 'accent' : 'neutral'}>
                            {String(v)}
                          </Chip>
                          <SourceLink url={conflict.source_urls[j] ?? ''} />
                          {conflict.source_urls[j] === conflict.preferred_claim_id && (
                            <Chip tone="accent">more specific source</Chip>
                          )}
                        </div>
                      ))}
                    </div>
                    <p className="xs muted" style={{ marginTop: 'var(--space-3)' }}>{conflict.resolution_rule}</p>
                    <details style={{ marginTop: 'var(--space-3)' }}>
                      <summary className="small" style={{ cursor: 'pointer' }}>
                        Draft question for the admissions office
                      </summary>
                      <pre className="xs mono" style={{ whiteSpace: 'pre-wrap', background: 'var(--surface)', padding: 'var(--space-3)', borderRadius: 'var(--radius)', marginTop: 8 }}>
                        {conflict.question_for_admissions}
                      </pre>
                      <button
                        className="btn btn--sm"
                        onClick={() => copy(conflict.question_for_admissions, `c${i}`)}
                      >
                        {copied === `c${i}` ? 'Copied' : 'Copy'}
                      </button>
                    </details>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        )}

        {(filter === 'all' || filter === 'questions') && (
          <Panel
            title={`Open questions (${questions.length})`}
            hint="Things no official source answered. They are reported rather than filled in with a guess."
          >
            {questions.length === 0 ? (
              <p className="muted small">Nothing outstanding.</p>
            ) : (
              <div className="stack stack--tight">
                {questions.map(({ result, question }, i) => (
                  <div key={i} className={`gap-item ${question.blocking ? 'gap-item--blocking' : 'gap-item--medium'}`}>
                    <Chip tone={question.blocking ? 'risk' : 'warn'}>
                      {question.blocking ? 'blocking' : 'open'}
                    </Chip>
                    <div>
                      <div className="small"><strong>{question.question}</strong></div>
                      <div className="xs muted">{question.why_it_matters}</div>
                      <div className="xs faint" style={{ marginTop: 2 }}>
                        {result.university} — {result.program}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        )}

        {filter === 'stale' && (
          <Panel
            title={`Claims past their freshness window (${stale.length})`}
            hint="Deadlines and prices are re-checked more often than policies. These need a re-read before you rely on them."
          >
            {stale.length === 0 ? (
              <p className="muted small">Every claim is inside its freshness window.</p>
            ) : (
              <div className="stack stack--tight">
                {stale.map(({ result, claim }, i) => (
                  <div key={i} className="claim claim--stale">
                    <div className="claim__head">
                      <span className="claim__type">{claim.claim_type}</span>
                      <span className="claim__value">{String(claim.normalized_value)}</span>
                      <StatusChip status={claim.status} tone={claimStatusTone[claim.status]} />
                      <Chip tone="warn">{claim.age_days} days old</Chip>
                    </div>
                    <div className="claim__src">
                      {result.university} · <SourceLink url={claim.source_url} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        )}

        <Panel title={`Every source consulted (${allSources.length})`} sunken>
          <div className="stack stack--tight" style={{ maxHeight: '22rem', overflowY: 'auto' }}>
            {allSources.map(([url, count]) => (
              <div key={url} className="row row--tight">
                <Chip mono>{count}×</Chip>
                <SourceLink url={url} />
              </div>
            ))}
          </div>
        </Panel>

        <Notice kind="info">
          <div>
            Claims are re-checked on a schedule that depends on what they are: deadlines and prices
            after 30 days, costs and award amounts after 120, policies after 180. Anything older is
            marked, not silently trusted. Last verification times are on each result.
            {results[0]?.last_verified && ` Most recent: ${dateTime(results[0].last_verified)}.`}
          </div>
        </Notice>
      </div>
    </>
  );
}

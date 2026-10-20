/**
 * Screen 09 — Sources and conflicts.
 *
 * Everything the pipeline could not settle, in one place, with a drafted
 * question for each. Contradictions are shown, never resolved silently.
 */

import { useMemo, useState } from 'react';
import { Chip, Empty, Notice, Panel, SourceLink, StatusChip } from '@/components/primitives';
import { claimStatusTone, claimValue, dateTime } from '@/lib/format';
import { localStaleChip, localStaleReason, localize } from '@/lib/messages';
import { useStore } from '@/lib/store';
import { rich, useTranslation } from '@/lib/useTranslation';

export function SourcesScreen() {
  const { results, summary } = useStore();
  const [copied, setCopied] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'conflicts' | 'questions' | 'stale'>('all');
  const { t, tf } = useTranslation();

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
  const verified = results.reduce((count, result) => count + result.claims.filter((claim) => claim.status === 'VERIFIED_CURRENT').length, 0);
  const allSources = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of results) for (const u of r.source_urls) map.set(u, (map.get(u) ?? 0) + 1);
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }, [results]);

  if (results.length === 0) return <Empty title={t('results.empty.title')}>{t('results.empty.runFirst')}</Empty>;

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
        <p className="screen__eyebrow">{t('sources.eyebrow')}</p>
        <h1 className="screen__title">{rich(t('sources.title'), { highlight: <span className="find-yellow">{t('sources.titleHighlight')}</span> })}</h1>
        <p className="screen__lede">{t('sources.lede')}</p>
      </div>

      <div className="stack stack--loose">
        {summary?.demo_data && (
          <Notice kind="demo"><strong>{t('results.demoData')}</strong> {t('sources.demoBody')}</Notice>
        )}
        <div className="evidence-overview" aria-label={t('sources.overviewAria')}>
          <div><strong>{verified}</strong><span>{t('sources.verifiedClaims')}</span></div>
          <div><strong>{conflicts.length}</strong><span>{t('sources.conflictsToReview')}</span></div>
          <div><strong>{questions.length}</strong><span>{t('sources.openQuestions')}</span></div>
        </div>
        <div className="row">
          {([
            ['all', tf('sources.filter.all', { n: conflicts.length + questions.length })],
            ['conflicts', tf('sources.filter.conflicts', { n: conflicts.length })],
            ['questions', tf('sources.filter.questions', { n: questions.length })],
            ['stale', tf('sources.filter.stale', { n: stale.length })],
          ] as const).map(([id, label]) => (
            <button
              key={id}
              className="btn btn--sm"
              style={filter === id ? { borderColor: 'var(--accent)', color: 'var(--accent-text)' } : undefined}
              onClick={() => setFilter(id)}
              data-testid={`filter-${id}`}
            >
              {label}
            </button>
          ))}
        </div>

        {(filter === 'all' || filter === 'conflicts') && (
          <Panel title={tf('sources.disagreeTitle', { n: conflicts.length })}>
            {conflicts.length === 0 ? (
              <p className="muted small">{t('sources.noConflicts')}</p>
            ) : (
              <div className="stack" data-testid="conflict-list">
                {conflicts.map(({ result, conflict }, i) => (
                  <div key={i} className="panel panel--sunken">
                    <div className="row" style={{ justifyContent: 'space-between' }}>
                      <div>
                        <strong className="small">{result.university}</strong>
                        <div className="xs muted">{conflict.subject}</div>
                      </div>
                      <Chip tone="risk">{t('sources.unresolved')}</Chip>
                    </div>
                    <div className="stack stack--tight" style={{ marginTop: 'var(--space-3)' }}>
                      {conflict.values.map((v, j) => (
                        <div key={j} className="row row--tight">
                          <Chip mono tone={conflict.claim_ids[j] === conflict.preferred_claim_id ? 'accent' : 'neutral'}>
                            {String(v)}
                          </Chip>
                          <SourceLink url={conflict.source_urls[j] ?? ''} />
                          {conflict.claim_ids[j] === conflict.preferred_claim_id && (
                            <Chip tone="accent">{t('sources.moreSpecific')}</Chip>
                          )}
                        </div>
                      ))}
                    </div>
                    <p className="xs muted" style={{ marginTop: 'var(--space-3)' }}>{conflict.resolution_rule}</p>
                    <details style={{ marginTop: 'var(--space-3)' }}>
                      <summary className="small" style={{ cursor: 'pointer' }}>
                        {t('sources.draftQuestion')}
                      </summary>
                      <pre className="xs mono" style={{ whiteSpace: 'pre-wrap', background: 'var(--surface)', padding: 'var(--space-3)', borderRadius: 'var(--radius)', marginTop: 8 }}>
                        {conflict.question_for_admissions}
                      </pre>
                      <button
                        className="btn btn--sm"
                        onClick={() => copy(conflict.question_for_admissions, `c${i}`)}
                      >
                        {copied === `c${i}` ? t('sources.copied') : t('sources.copy')}
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
            title={tf('sources.questionsTitle', { n: questions.length })}
            hint={t('sources.questionsHint')}
          >
            {questions.length === 0 ? (
              <p className="muted small">{t('sources.nothingOutstanding')}</p>
            ) : (
              <div className="stack stack--tight">
                {questions.map(({ result, question }, i) => (
                  <div key={i} className={`gap-item ${question.blocking ? 'gap-item--blocking' : 'gap-item--medium'}`}>
                    <Chip tone={question.blocking ? 'risk' : 'warn'}>
                      {question.blocking ? t('results.blocking') : t('results.open')}
                    </Chip>
                    <div>
                      <div className="small"><strong>{localize(question.question_message, question.question)}</strong></div>
                      <div className="xs muted">{localize(question.why_message, question.why_it_matters)}</div>
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
            title={tf('sources.staleTitle', { n: stale.length })}
            hint={t('sources.staleHint')}
          >
            {stale.length === 0 ? (
              <p className="muted small">{t('sources.noStale')}</p>
            ) : (
              <div className="stack stack--tight">
                {stale.map(({ result, claim }, i) => (
                  <div key={i} className="claim claim--stale">
                    <div className="claim__head">
                      <span className="claim__type">{claim.claim_type}</span>
                      <span className="claim__value">{claimValue(claim.normalized_value)}</span>
                      <StatusChip status={claim.status} tone={claimStatusTone[claim.status]} />
                      <Chip tone="warn">{localStaleChip(claim.age_days, localStaleReason(claim) !== null)}</Chip>
                    </div>
                    {localStaleReason(claim) && (
                      <div className="xs claim__stale-reason">{tf('results.notCurrent', { reason: localStaleReason(claim) ?? '' })}</div>
                    )}
                    <div className="claim__src">
                      {result.university} · <SourceLink url={claim.source_url} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        )}

        <Panel title={tf('sources.everySource', { n: allSources.length })} sunken>
          <div
            className="stack stack--tight"
            style={{ maxHeight: '22rem', overflowY: 'auto' }}
            tabIndex={0}
            role="region"
            aria-label={t('sources.everySourceAria')}
          >
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
            {t('sources.schedule')}
            {results[0]?.last_verified && tf('sources.mostRecent', { when: dateTime(results[0].last_verified) })}
          </div>
        </Notice>
      </div>
    </>
  );
}

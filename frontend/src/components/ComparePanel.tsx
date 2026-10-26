import { Deadline } from '@/components/Deadline';
import { Chip, SourceLink, StatusChip, statusLabel } from '@/components/primitives';
import { FIT_DISCLAIMER, admissionsFitTone, eligibilityTone, fundingClassTone, money, percent } from '@/lib/format';
import { useTranslation } from '@/lib/useTranslation';
import { localize } from '@/lib/messages';
import type { ProgramResult } from '@/types';

export function ComparePanel({ results, onRemove, onClear }: {
  results: ProgramResult[];
  onRemove: (id: string) => void;
  onClear: () => void;
}) {
  const { t, tf, tOr } = useTranslation();
  return (
    <section className="find-compare" id="find-compare" aria-label={t('compare.aria')}>
      <div className="find-compare__head">
        <div><span className="home-eyebrow">{t('compare.eyebrow')}</span><h2>{t('compare.title')}</h2></div>
        <button type="button" className="btn btn--ghost" onClick={onClear}>{t('compare.clear')}</button>
      </div>
      <p className="small muted">{t('compare.lede')}</p>
      <div className="find-compare__grid" style={{ gridTemplateColumns: `repeat(${results.length}, minmax(0, 1fr))` }}>
        {results.map((result) => (
          <article className="find-compare__column" key={result.id}>
            <span className="home-eyebrow">{result.country}</span>
            <h3>{result.university}</h3>
            <p>{result.program}</p>
            <dl>
              <dt>{t('col.eligibility')}</dt><dd><StatusChip status={result.eligibility} tone={eligibilityTone[result.eligibility]} /></dd>
              <dt>{t('col.admissionsFit')}</dt><dd><StatusChip status={result.admissions_fit} tone={admissionsFitTone[result.admissions_fit]} /></dd>
              <dt>{t('col.funding')}</dt><dd><StatusChip status={result.best_funding_classification} tone={fundingClassTone[result.best_funding_classification]} /></dd>
              <dt>{t('col.remainingPerYear')}</dt><dd>{result.funding_gap?.computable && result.funding_gap.gap ? money(result.funding_gap.gap) : t('results.notEnoughData')}</dd>
              <dt>{t('col.deadline')}</dt><dd><Deadline result={result} fallback={t('results.notConfirmed')} /></dd>
              <dt title={tOr('results.fitDisclaimer', FIT_DISCLAIMER)}>{t('compare.preferenceFit')}</dt><dd>{result.ranking ? statusLabel(result.ranking.bucket, tOr) : t('compare.notAssessed')}</dd>
              <dt title={t('compare.coverageHint')}>{t('compare.coverage')}</dt><dd>{percent(result.ranking?.coverage ?? null)}</dd>
            </dl>
            <div className="find-compare__foot">
              {(result.conflicts.length > 0 || result.unresolved.length > 0) && <Chip tone="warn">{tf('compare.toClarify', { n: result.conflicts.length + result.unresolved.length })}</Chip>}
              {result.program_url && <SourceLink url={result.program_url} />}
              <button type="button" className="btn btn--sm" onClick={() => onRemove(result.id)}>{t('results.remove')}</button>
            </div>
            <details><summary className="small">{t('compare.whyFit')}</summary><p className="small muted">{result.ranking ? localize(result.ranking.bucket_reason_message, result.ranking.bucket_reason) : statusLabel(result.eligibility, tOr)}</p></details>
          </article>
        ))}
      </div>
    </section>
  );
}

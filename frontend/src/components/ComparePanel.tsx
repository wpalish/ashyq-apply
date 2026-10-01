import { Chip, SourceLink, StatusChip } from '@/components/primitives';
import { FIT_DISCLAIMER, STATUS_LABEL, admissionsFitTone, date, eligibilityTone, fundingClassTone, humanize, money, percent, ratio } from '@/lib/format';
import type { ProgramResult } from '@/types';

export function ComparePanel({ results, onRemove, onClear }: {
  results: ProgramResult[];
  onRemove: (id: string) => void;
  onClear: () => void;
}) {
  return (
    <section className="find-compare" id="find-compare" aria-label="Compare selected programmes">
      <div className="find-compare__head">
        <div><span className="home-eyebrow">COMPARE WITH CLARITY</span><h2>Different strengths. A clearer choice.</h2></div>
        <button type="button" className="btn btn--ghost" onClick={onClear}>Clear</button>
      </div>
      <p className="small muted">Compare what the sources actually support. A match score describes your stated preferences, not your chance of admission.</p>
      <div className="find-compare__grid" style={{ gridTemplateColumns: `repeat(${results.length}, minmax(0, 1fr))` }}>
        {results.map((result) => (
          <article className="find-compare__column" key={result.id}>
            <span className="home-eyebrow">{result.country}</span>
            <h3>{result.university}</h3>
            <p>{result.program}</p>
            <dl>
              <dt>Eligibility</dt><dd><StatusChip status={result.eligibility} tone={eligibilityTone[result.eligibility]} /></dd>
              <dt>Admissions fit</dt><dd><StatusChip status={result.admissions_fit} tone={admissionsFitTone[result.admissions_fit]} /></dd>
              <dt>Funding</dt><dd><StatusChip status={result.best_funding_classification} tone={fundingClassTone[result.best_funding_classification]} /></dd>
              <dt>Remaining per year</dt><dd>{result.funding_gap?.computable && result.funding_gap.gap ? money(result.funding_gap.gap) : 'Not enough comparable data'}</dd>
              <dt>Deadline</dt><dd>{result.admission_deadline ? date(result.admission_deadline) : 'Not confirmed'}</dd>
              <dt title={FIT_DISCLAIMER}>Preference fit</dt><dd>{ratio(result.ranking?.fit ?? null)}</dd>
              <dt>Confirmed data</dt><dd>{percent(result.ranking?.coverage ?? null)}</dd>
            </dl>
            <div className="find-compare__foot">
              {(result.conflicts.length > 0 || result.unresolved.length > 0) && <Chip tone="warn">{result.conflicts.length + result.unresolved.length} to clarify</Chip>}
              {result.program_url && <SourceLink url={result.program_url} />}
              <button type="button" className="btn btn--sm" onClick={() => onRemove(result.id)}>Remove</button>
            </div>
            <details><summary className="small">Why this fit?</summary><p className="small muted">{result.ranking?.bucket_reason ?? STATUS_LABEL[result.eligibility] ?? humanize(result.eligibility)}</p></details>
          </article>
        ))}
      </div>
    </section>
  );
}

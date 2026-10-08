import { useState } from 'react';
import { ResultDetail } from '@/components/ResultDetail';
import { Chip, SourceLink, StatusChip } from '@/components/primitives';
import { FIT_DISCLAIMER, STATUS_LABEL, admissionsFitTone, date, eligibilityTone, fundingClassTone, humanize, money, percent } from '@/lib/format';
import type { DocumentOwner, ProgramResult } from '@/types';

const DOCUMENT_OWNER: Record<DocumentOwner, string> = {
  applicant: 'You', school: 'Your school', recommender: 'Your referee', third_party: 'A third party',
};

const LIST_STATE = {
  official: 'Read from official pages',
  partial: 'Partially read from sources',
  unavailable: 'Collection attempted — unavailable',
};

function linkedChecklist(result: ProgramResult) {
  return result.checklist?.result_id === result.id ? result.checklist : null;
}

function PreparationEvidence({ result }: { result: ProgramResult }) {
  const checklist = linkedChecklist(result);
  // Owner action arrays repeat items from these lists; they are not extra documents.
  const admission = checklist?.admission_documents.filter(d => d.required === true) ?? [];
  const scholarship = checklist?.scholarship_documents.filter(d => d.required === true) ?? [];
  const groups = [
    { label: 'Admission', items: admission },
    { label: 'Scholarship', items: scholarship },
  ];
  const hasRequired = groups.some(group => group.items.length > 0);
  const listState = result.checklist && !checklist ? 'Checklist link needs clarification'
    : checklist ? LIST_STATE[checklist.completeness] : 'Not collected';

  return (
    <section aria-label={`${result.university} preparation evidence`}>
      <h4>Preparation evidence</h4>
      <dl>
        <dt>Requested intake</dt><dd>{result.intake.trim() || 'Not recorded'}</dd>
        <dt>Document list</dt><dd>{listState}</dd>
        <dt>Required items recorded</dt>
        <dd>{hasRequired ? `Admission: ${admission.length} · Scholarship: ${scholarship.length}` : 'No required items recorded'}</dd>
      </dl>
      <p className="xs muted">Reading sources does not confirm that your documents are prepared. The requested intake does not confirm which intake the document sources cover.</p>
      {(checklist?.unresolved.length ?? 0) > 0 && <p className="small">{checklist?.unresolved.length} checklist question{checklist?.unresolved.length === 1 ? '' : 's'} to clarify</p>}
      {(hasRequired || (checklist?.unresolved.length ?? 0) > 0) && (
        <details>
          <summary className="small">Required items, owners &amp; sources</summary>
          {groups.filter(group => group.items.length > 0).map(group => (
            <div key={group.label}>
              <h5>{group.label}</h5>
              <ul className="stack stack--tight">
                {group.items.map((document, index) => (
                  <li key={`${document.name}-${index}`} className="small">
                    <strong>{document.name}</strong>
                    <p className="xs muted">{DOCUMENT_OWNER[document.owner] ?? 'Owner not recorded'}</p>
                    {document.source_url ? <SourceLink url={document.source_url} /> : <span className="xs muted">Source not recorded</span>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {(checklist?.unresolved.length ?? 0) > 0 && (
            <div>
              {checklist?.unresolved.map((question, index) => (
                <div key={`${question.topic}-${index}`}>
                  <p className="small">{question.question}</p>
                  <p className="xs muted">{question.why_it_matters}</p>
                </div>
              ))}
            </div>
          )}
        </details>
      )}
    </section>
  );
}

export function ComparePanel({ results, onRemove, onClear }: {
  results: ProgramResult[];
  onRemove: (id: string) => void;
  onClear: () => void;
}) {
  const [detailsFor, setDetailsFor] = useState<string | null>(null);
  const detailResult = results.find(result => result.id === detailsFor);

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
              <dt title={FIT_DISCLAIMER}>Preference fit</dt><dd>{result.ranking ? (STATUS_LABEL[result.ranking.bucket] ?? humanize(result.ranking.bucket)) : 'Not assessed'}</dd>
              <dt title="How much of the evidence needed for this assessment was confirmed">Evidence coverage</dt><dd>{percent(result.ranking?.coverage ?? null)}</dd>
            </dl>
            <PreparationEvidence result={result} />
            <div className="find-compare__foot">
              {(result.conflicts.length > 0 || result.unresolved.length > 0) && <Chip tone="warn">{result.conflicts.length + result.unresolved.length} to clarify</Chip>}
              {result.program_url && <SourceLink url={result.program_url} />}
              <button type="button" className="btn btn--sm" aria-expanded={detailResult?.id === result.id} aria-controls={detailResult?.id === result.id ? `compare-details-${result.id}` : undefined} onClick={() => setDetailsFor(current => current === result.id ? null : result.id)}>View details</button>
              <button type="button" className="btn btn--sm" onClick={() => onRemove(result.id)}>Remove</button>
            </div>
            <details><summary className="small">Why this fit?</summary><p className="small muted">{result.ranking?.bucket_reason ?? STATUS_LABEL[result.eligibility] ?? humanize(result.eligibility)}</p></details>
          </article>
        ))}
      </div>
      {detailResult && (
        <div id={`compare-details-${detailResult.id}`}>
          <ResultDetail key={detailResult.id} result={detailResult.checklist && !linkedChecklist(detailResult) ? { ...detailResult, checklist: null } : detailResult} />
        </div>
      )}
    </section>
  );
}

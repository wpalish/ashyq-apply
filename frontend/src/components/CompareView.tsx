/**
 * Two or three programmes, row by row.
 *
 * Round 7's comparison screen: the same questions asked of each programme on
 * one line - what is left to pay, the price, the grant, what it covers and
 * leaves out, the three judgements, the deadline and where it was read - so
 * a difference is visible without opening two pages and remembering one of
 * them. Every cell comes from the row the table shows; an unknown stays
 * unknown in its cell, and nothing is ranked or scored between the columns.
 */

import { useEffect, useRef, type ReactNode } from 'react';
import { StatusChip } from '@/components/primitives';
import { coverageOf } from '@/components/MoneyArithmetic';
import { FIT_NOTE, requirementNote, sourceNote } from '@/components/ResultCard';
import {
  admissionsFitTone, date, eligibilityTone, fundingClassTone, humanize, money,
} from '@/lib/format';
import type { ProgramResult } from '@/types';

function list(items: string[]): string {
  return items.length ? items.map(humanize).join(', ').toLowerCase() : '—';
}

export function CompareView({
  programmes, onClose, onRemove,
}: {
  programmes: ProgramResult[];
  onClose: () => void;
  onRemove: (id: string) => void;
}) {
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    title.current?.focus();
  }, []);

  const rows: { label: string; cell: (r: ProgramResult) => ReactNode }[] = [
    {
      label: 'Left to pay a year',
      cell: (r) => {
        const gap = r.funding_gap;
        if (gap?.computable && gap.gap) {
          const aid = gap.confirmed_aid?.amount ?? 0;
          return (
            <>
              <strong className="compare__money">{money({ ...gap.gap, academic_year: null })}</strong>
              {aid > 0 && <span className="compare__sub">if awarded</span>}
            </>
          );
        }
        return <span className="compare__unknown">not computed</span>;
      },
    },
    {
      label: 'Price a year',
      cell: (r) => (r.funding_gap?.total_cost
        ? money({ ...r.funding_gap.total_cost, academic_year: null })
        : <span className="compare__unknown">not published</span>),
    },
    {
      label: 'Grant',
      cell: (r) => {
        const { award } = coverageOf(r);
        return (
          <>
            <StatusChip status={r.best_funding_classification} tone={fundingClassTone[r.best_funding_classification]} />
            <span className="compare__sub">{award ? award.name : 'no award found'}</span>
          </>
        );
      },
    },
    { label: 'The grant covers', cell: (r) => list(coverageOf(r).covered) },
    { label: 'Not covered', cell: (r) => (coverageOf(r).award ? list(coverageOf(r).leftOut) : '—') },
    {
      label: 'Requirements',
      cell: (r) => (
        <>
          <StatusChip status={r.eligibility} tone={eligibilityTone[r.eligibility]} />
          <span className="compare__sub">{requirementNote(r)}</span>
        </>
      ),
    },
    {
      label: 'Your profile',
      cell: (r) => (
        <>
          <StatusChip status={r.admissions_fit} tone={admissionsFitTone[r.admissions_fit]} />
          <span className="compare__sub">{FIT_NOTE[r.admissions_fit] ?? ''}</span>
        </>
      ),
    },
    {
      label: 'Deadline',
      cell: (r) => (
        <>
          {r.admission_deadline ? date(r.admission_deadline) : <span className="compare__unknown">not found</span>}
          {r.deadline_passed && <strong className="rcard__passed"> · passed</strong>}
        </>
      ),
    },
    { label: 'Source', cell: (r) => <span className="compare__sub">{sourceNote(r)}</span> },
  ];

  return (
    <section className="compare" aria-labelledby="compare-title" data-testid="compare-view">
      <div className="compare__top">
        <h2 className="compare__title" id="compare-title" tabIndex={-1} ref={title}>
          Row by row
        </h2>
        <button type="button" className="btn btn--sm" onClick={onClose} data-testid="compare-close">
          Back to the list
        </button>
      </div>
      <p className="compare__lede">
        The same questions for each programme, from the pages the research read. Nothing here is
        ranked or scored between them, and none of it predicts a decision.
      </p>
      <div className="compare__wrap" style={{ ['--compare-n' as string]: programmes.length }}>
        <table className="compare__table">
          <caption className="visually-hidden">Programmes compared row by row</caption>
          <thead>
            <tr>
              <td className="compare__corner" />
              {programmes.map((r) => (
                <th scope="col" key={r.id}>
                  <span className="compare__uni">{r.university}</span>
                  <span className="compare__prog">{r.program}</span>
                  <button
                    type="button"
                    className="compare__remove"
                    onClick={() => {
                      onRemove(r.id);
                      // The button goes with its column; keep focus on the view.
                      title.current?.focus();
                    }}
                    aria-label={`Remove ${r.university} from the comparison`}
                  >Remove</button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                {programmes.map((r) => <td key={r.id}>{row.cell(r)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

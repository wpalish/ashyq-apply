/**
 * Screen 04 — University shortlist.
 *
 * A compact table with an expandable detail row, deliberately not one card per
 * university: the whole point is comparing thirty rows on the same axes.
 * Eligibility, admissions fit and funding are three separate columns because
 * they are three separate judgements and collapsing them would hide which one
 * is the problem.
 */

import { Fragment, useMemo, useState } from 'react';
import { ResultDetail } from '@/components/ResultDetail';
import { Chip, Empty, Field, Notice, Panel, StatusChip } from '@/components/primitives';
import {
  STATUS_LABEL, admissionsFitTone, date, eligibilityTone, fundingClassTone, humanize, money,
  scorePercent,
} from '@/lib/format';
import { useStore } from '@/lib/store';
import type { ProgramResult, UserDecision } from '@/types';

type SortKey = 'score' | 'gap' | 'university' | 'deadline';

//: The four reasons applicants actually give, as one-click chips. Free text
//: stays available because these will never cover every case.
const REJECTION_REASONS = ['cost', 'deadline passed', 'no funding', 'not a fit'];

export function ShortlistScreen() {
  const { results, summary, decide, saveNotes } = useStore();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>('score');
  const [country, setCountry] = useState('');
  const [eligibility, setEligibility] = useState('');
  const [funding, setFunding] = useState('');
  const [hideRejected, setHideRejected] = useState(false);
  const [noteFor, setNoteFor] = useState<string | null>(null);
  const [noteText, setNoteText] = useState('');
  const [rejectFor, setRejectFor] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const countries = useMemo(
    () => Array.from(new Set(results.map((r) => r.country))).sort(),
    [results],
  );

  const rows = useMemo(() => {
    const filtered = results.filter(
      (r) =>
        (!country || r.country === country) &&
        (!eligibility || r.eligibility === eligibility) &&
        (!funding || r.best_funding_classification === funding) &&
        (!hideRejected || r.user_decision !== 'rejected'),
    );
    const gapOf = (r: ProgramResult) =>
      r.funding_gap?.computable && r.funding_gap.gap ? r.funding_gap.gap.amount : Number.MAX_SAFE_INTEGER;
    return [...filtered].sort((a, b) => {
      if (sort === 'university') return a.university.localeCompare(b.university);
      if (sort === 'gap') return gapOf(a) - gapOf(b);
      if (sort === 'deadline') {
        return (a.admission_deadline ?? '9999').localeCompare(b.admission_deadline ?? '9999');
      }
      return (b.preference_score?.total ?? 0) - (a.preference_score?.total ?? 0);
    });
  }, [results, country, eligibility, funding, hideRejected, sort]);

  if (results.length === 0) {
    return <Empty title="No results yet">Run the research first.</Empty>;
  }

  const decideRow = (r: ProgramResult, d: UserDecision) => {
    const next = r.user_decision === d ? 'undecided' : d;
    if (next === 'rejected') {
      // The product promises rejections keep their reason, and the API has
      // always accepted one; the UI simply never asked. Ask now, and let the
      // reason stay optional so saying No is still one click away.
      setRejectFor(r.id);
      setRejectReason(r.user_decision_reason);
      return Promise.resolve();
    }
    setRejectFor(null);
    return decide(r.id, next, '', r.user_notes);
  };

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">Step 04</p>
        <h1 className="screen__title">The shortlist</h1>
        <p className="screen__lede">
          Three independent judgements per row. <strong>Eligibility</strong> is about published
          requirements, <strong>fit</strong> is how your profile sits against them, and{' '}
          <strong>funding</strong> is what an official page says an award covers. None of them
          predicts a decision.
        </p>
      </div>

      <div className="stack stack--loose">
        {summary?.demo_data && (
          <Notice kind="demo">
            <div>
              <strong>Demo data.</strong> These figures come from a bundled synthetic corpus, not
              from real university pages. Every source below is a <code>fixture://</code> address.
            </div>
          </Notice>
        )}

        <Panel sunken>
          <div className="filters">
            <Field label="Country" htmlFor="f-country">
              <select id="f-country" value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="">All ({results.length})</option>
                {countries.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label="Eligibility" htmlFor="f-elig">
              <select id="f-elig" value={eligibility} onChange={(e) => setEligibility(e.target.value)}>
                <option value="">Any</option>
                {Object.entries(summary?.by_eligibility ?? {}).map(([k, v]) => (
                  // The value stays the enum; only the label is for humans.
                  <option key={k} value={k}>{STATUS_LABEL[k] ?? humanize(k)} ({v})</option>
                ))}
              </select>
            </Field>
            <Field label="Funding" htmlFor="f-fund">
              <select id="f-fund" value={funding} onChange={(e) => setFunding(e.target.value)}>
                <option value="">Any</option>
                {Object.entries(summary?.by_funding ?? {}).map(([k, v]) => (
                  <option key={k} value={k}>{STATUS_LABEL[k] ?? humanize(k)} ({v})</option>
                ))}
              </select>
            </Field>
            <Field label="Sort by" htmlFor="f-sort">
              <select id="f-sort" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
                <option value="score">Preference score</option>
                <option value="gap">Smallest remaining cost</option>
                <option value="deadline">Earliest deadline</option>
                <option value="university">University name</option>
              </select>
            </Field>
            <label className="row row--tight small" style={{ paddingBottom: 6 }}>
              <input type="checkbox" checked={hideRejected} onChange={(e) => setHideRejected(e.target.checked)} />
              Hide rejected
            </label>
          </div>
        </Panel>

        <div className="table-wrap">
          <table className="dtable" data-testid="shortlist-table">
            <caption className="visually-hidden">
              Shortlisted university programmes with eligibility, fit, funding and remaining cost
            </caption>
            <thead>
              <tr>
                <th scope="col">University &amp; programme</th>
                <th scope="col">Eligibility</th>
                <th scope="col">Admissions fit</th>
                <th scope="col">Funding</th>
                <th scope="col">Remaining&nbsp;/&nbsp;year</th>
                <th scope="col">Deadline</th>
                <th scope="col">Preference match</th>
                <th scope="col">Decision</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const open = expanded === r.id;
                const gap = r.funding_gap;
                return (
                  // The Fragment carries the key: a row and its detail drawer are
                  // two siblings produced by one iteration.
                  <Fragment key={r.id}>
                    <tr
                      className={`${open ? 'is-expanded' : ''} ${r.user_decision === 'rejected' ? 'is-rejected' : ''}`}
                      data-testid={`row-${r.id}`}
                    >
                      <td data-label="University & programme">
                        <div className="uni-cell">
                          <button
                            className="uni-cell__name"
                            onClick={() => setExpanded(open ? null : r.id)}
                            aria-expanded={open}
                            data-testid={`expand-${r.id}`}
                          >
                            {r.university}
                          </button>
                          <span className="uni-cell__prog">{r.program}</span>
                          <span className="uni-cell__meta">
                            {r.city}, {r.country}
                            {r.rankings[0] && ` · ${r.rankings[0].source} ${r.rankings[0].year}: ${r.rankings[0].position}`}
                          </span>
                        </div>
                      </td>
                      <td data-label="Eligibility"><StatusChip status={r.eligibility} tone={eligibilityTone[r.eligibility]} /></td>
                      <td data-label="Admissions fit"><StatusChip status={r.admissions_fit} tone={admissionsFitTone[r.admissions_fit]} /></td>
                      <td data-label="Funding">
                        <StatusChip
                          status={r.best_funding_classification}
                          tone={fundingClassTone[r.best_funding_classification]}
                        />
                      </td>
                      <td className="num" data-label="Remaining / year">
                        {gap?.computable && gap.gap ? (
                          money(gap.gap)
                        ) : (
                          <span className="xs muted" title={gap?.reason}>not computable</span>
                        )}
                      </td>
                      <td className="num" data-label="Deadline">
                        {r.admission_deadline ? date(r.admission_deadline) : <span className="xs muted">not found</span>}
                        {r.deadline_passed && <div><Chip tone="risk">passed</Chip></div>}
                      </td>
                      <td className="num" data-label="Preference match">
                        {r.preference_score
                          ? `${(scorePercent(r.preference_score.total, r.preference_score.max_possible) / 10).toFixed(1)} / 10`
                          : '—'}
                      </td>
                      <td data-label="Decision">
                        <div className="decision-group" role="group" aria-label={`Decision for ${r.university}`}>
                          <button
                            className="decision-btn decision-btn--approve"
                            aria-pressed={r.user_decision === 'approved'}
                            onClick={() => decideRow(r, 'approved')}
                            data-testid={`approve-${r.id}`}
                          >Yes</button>
                          <button
                            className="decision-btn decision-btn--maybe"
                            aria-pressed={r.user_decision === 'maybe'}
                            onClick={() => decideRow(r, 'maybe')}
                            data-testid={`maybe-${r.id}`}
                          >Maybe</button>
                          <button
                            className="decision-btn decision-btn--reject"
                            aria-pressed={r.user_decision === 'rejected'}
                            onClick={() => decideRow(r, 'rejected')}
                            data-testid={`reject-${r.id}`}
                          >No</button>
                        </div>
                        {rejectFor === r.id && (
                          <div
                            className="stack stack--tight"
                            style={{ marginTop: 6, minWidth: '13rem' }}
                            data-testid={`reject-reason-${r.id}`}
                          >
                            <label className="xs muted" htmlFor={`reject-input-${r.id}`}>
                              Why not this one? (optional — it is kept with the row)
                            </label>
                            <div className="row row--tight" style={{ flexWrap: 'wrap' }}>
                              {REJECTION_REASONS.map((preset) => (
                                <button
                                  key={preset}
                                  type="button"
                                  className="btn btn--sm btn--ghost xs"
                                  onClick={() => setRejectReason(preset)}
                                  data-testid={`reject-chip-${preset.replace(/\s+/g, '-')}-${r.id}`}
                                >{preset}</button>
                              ))}
                            </div>
                            <input
                              id={`reject-input-${r.id}`}
                              value={rejectReason}
                              onChange={(e) => setRejectReason(e.target.value)}
                              placeholder="cost, deadline, fit…"
                              data-testid={`reject-input-${r.id}`}
                            />
                            <div className="row row--tight">
                              <button
                                className="btn btn--sm"
                                onClick={async () => {
                                  await decide(r.id, 'rejected', rejectReason, r.user_notes);
                                  setRejectFor(null);
                                }}
                                data-testid={`reject-save-${r.id}`}
                              >Save rejection</button>
                              <button
                                className="btn btn--sm btn--ghost"
                                onClick={() => setRejectFor(null)}
                                data-testid={`reject-cancel-${r.id}`}
                              >Cancel</button>
                            </div>
                          </div>
                        )}
                        {r.user_decision === 'rejected' && r.user_decision_reason && rejectFor !== r.id && (
                          <p className="xs faint" style={{ margin: '4px 0 0', maxWidth: '12rem' }}>
                            Rejected: {r.user_decision_reason}
                          </p>
                        )}
                        <div>
                          <button
                            className="btn btn--sm btn--ghost xs"
                            onClick={() => {
                              setNoteFor(noteFor === r.id ? null : r.id);
                              setNoteText(r.user_notes);
                            }}
                          >
                            {r.user_notes ? 'Edit note' : 'Add note'}
                          </button>
                        </div>
                        {noteFor === r.id && (
                          <div className="stack stack--tight" style={{ marginTop: 6, minWidth: '13rem' }}>
                            <textarea
                              rows={2}
                              value={noteText}
                              onChange={(e) => setNoteText(e.target.value)}
                              placeholder="Why this one?"
                              data-testid={`note-input-${r.id}`}
                            />
                            <button
                              className="btn btn--sm"
                              onClick={async () => {
                                await saveNotes(r.id, noteText);
                                setNoteFor(null);
                              }}
                              data-testid={`note-save-${r.id}`}
                            >Save note</button>
                          </div>
                        )}
                        {r.user_notes && noteFor !== r.id && (
                          <p className="xs faint" style={{ margin: '4px 0 0', maxWidth: '12rem' }}>
                            {r.user_notes}
                          </p>
                        )}
                      </td>
                    </tr>
                    {open && (
                      <tr className="detail-row">
                        <td colSpan={8}><ResultDetail result={r} /></td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        <p className="xs faint">
          Showing {rows.length} of {results.length}. Rejected rows are kept with their reason so the
          same programme is not proposed again without new information.
        </p>
      </div>
    </>
  );
}

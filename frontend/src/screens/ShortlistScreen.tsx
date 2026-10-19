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
import { ComparePanel } from '@/components/ComparePanel';
import { UniversityCatalogue } from '@/components/UniversityCatalogue';
import { Chip, Empty, Field, Notice, Panel, StatusChip, statusLabel } from '@/components/primitives';
import {
  FIT_DISCLAIMER, admissionsFitTone, bucketTone, date, eligibilityTone,
  fundingClassTone, money, openQuestionCount, percent, ratio,
} from '@/lib/format';
import type { MessageKey } from '@/lib/i18n';
import { useStore } from '@/lib/store';
import { rich, useTranslation } from '@/lib/useTranslation';
import type { Bucket, ProgramResult, UserDecision } from '@/types';

type SortKey = 'key' | 'fit' | 'coverage' | 'gap' | 'university' | 'deadline';

//: Buckets that are ranked against each other. The rest are real answers too,
//: but they answer a different question, so they sit in their own sections
//: below rather than competing for a place in the top ten.
const RANKED: Bucket[] = ['WELL_PLACED', 'PLAUSIBLE', 'AMBITIOUS'];
const SET_ASIDE: Bucket[] = ['OUT_OF_BUDGET', 'NEEDS_CLARIFICATION', 'EXCLUDED'];

const SET_ASIDE_HINT: Record<string, MessageKey> = {
  OUT_OF_BUDGET: 'shortlist.hint.OUT_OF_BUDGET',
  NEEDS_CLARIFICATION: 'shortlist.hint.NEEDS_CLARIFICATION',
  EXCLUDED: 'shortlist.hint.EXCLUDED',
};

//: The four reasons applicants actually give, as one-click chips. Free text
//: stays available because these will never cover every case.
const REJECTION_REASONS = ['cost', 'deadline passed', 'no funding', 'not a fit'];

export function ShortlistScreen({ onStart, onProgress }: { onStart?: () => void; onProgress?: () => void }) {
  const { results, summary, shortlist, decide, saveNotes, capabilities } = useStore();
  const { t, tf, tn, tOr } = useTranslation();
  const bucketLabel = (bucket: string) => statusLabel(bucket, tOr);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [cardExpanded, setCardExpanded] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>('key');
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState<'all' | 'priority' | 'saved' | 'exploring'>('all');
  const [compareIds, setCompareIds] = useState<string[]>([]);
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
        (!query.trim() || `${r.university} ${r.program} ${r.country} ${r.city}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())) &&
        (tab === 'all' ||
          (tab === 'priority' && r.ranking?.bucket === 'WELL_PLACED') ||
          (tab === 'saved' && (r.user_decision === 'approved' || r.user_decision === 'maybe')) ||
          (tab === 'exploring' && r.user_decision === 'undecided')) &&
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
      if (sort === 'fit') return (b.ranking?.fit ?? 0) - (a.ranking?.fit ?? 0);
      if (sort === 'coverage') return (b.ranking?.coverage ?? 0) - (a.ranking?.coverage ?? 0);
      if (sort === 'deadline') {
        return (a.admission_deadline ?? '9999').localeCompare(b.admission_deadline ?? '9999');
      }
      // Ties break on the identifier so the same data is always the same order.
      const key = (r: ProgramResult) => r.ranking?.sort_key ?? r.preference_score?.total ?? 0;
      return key(b) - key(a) || a.id.localeCompare(b.id);
    });
  }, [results, query, tab, country, eligibility, funding, hideRejected, sort]);

  // A row with no ranking is one assessed under v1; it still belongs in the
  // list rather than in a set-aside section it was never scored for.
  const ranked = rows.filter((r) => !r.ranking || RANKED.includes(r.ranking.bucket));

  if (results.length === 0) {
    return (
      <div className="find-page">
        <div className="screen__head"><p className="screen__eyebrow">{t('shortlist.emptyEyebrow')}</p><h1 className="screen__title">{rich(t('shortlist.title'), { highlight: <span className="find-yellow">{t('shortlist.titleHighlight')}</span> })}</h1><p className="screen__lede">{t('shortlist.emptyLede')}</p></div>
        <div className="find-empty"><Empty title={t('results.empty.title')}>{t('shortlist.emptyBody')}</Empty>{onStart && <button className="btn btn--primary" type="button" onClick={onStart}>{t('shortlist.start')}</button>}</div>
        <UniversityCatalogue onStart={onStart} onProgress={onProgress} />
      </div>
    );
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

  const renderTable = (
    tableRows: ProgramResult[],
    testId: string,
    caption: string,
    // The set-aside sections name their bucket in the heading above the
    // table, so repeating it on every row only costs the width that made it
    // unreadable in the first place.
    showBucket = true,
  ) => (
          <div className="table-wrap">
            <table
              className={`dtable shortlist-table${showBucket ? ' shortlist-table--with-bucket' : ''}`}
              data-testid={testId}
            >
              {/* Each table says which list it is: four identically captioned
                  tables read as one repeated table to a screen reader. */}
              <caption className="visually-hidden">{caption}</caption>
              <colgroup>
                <col className="shortlist-col--university" />
                <col className="shortlist-col--eligibility" />
                <col className="shortlist-col--fit" />
                <col className="shortlist-col--funding" />
                <col className="shortlist-col--remaining" />
                <col className="shortlist-col--deadline" />
                <col className="shortlist-col--match" />
                <col className="shortlist-col--confirmed" />
                {showBucket && <col className="shortlist-col--bucket" />}
                <col className="shortlist-col--decision" />
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">{t('col.university')}</th>
                  <th scope="col">{t('col.eligibility')}</th>
                  <th scope="col">{t('col.admissionsFit')}</th>
                  <th scope="col">{t('col.funding')}</th>
                  <th scope="col">{t('col.remaining')}</th>
                  <th scope="col">{t('col.deadline')}</th>
                  <th scope="col" title={tOr('results.fitDisclaimer', FIT_DISCLAIMER)}>{t('col.match')}</th>
                  <th scope="col" title={t('col.confirmedHint')}>{t('col.confirmed')}</th>
                  {showBucket && <th scope="col">{t('col.bucket')}</th>}
                  <th scope="col">{t('col.decision')}</th>
                </tr>
              </thead>
              <tbody>
                {tableRows.map((r) => {
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
                        <td data-label={t('col.university')}>
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
                        <td data-label={t('col.eligibility')}><StatusChip status={r.eligibility} tone={eligibilityTone[r.eligibility]} /></td>
                        <td data-label={t('col.admissionsFit')}><StatusChip status={r.admissions_fit} tone={admissionsFitTone[r.admissions_fit]} /></td>
                        <td data-label={t('col.funding')}>
                          <StatusChip
                            status={r.best_funding_classification}
                            tone={fundingClassTone[r.best_funding_classification]}
                          />
                        </td>
                        <td className="num" data-label={t('col.remaining')}>
                          {gap?.computable && gap.gap ? (
                            <>
                              {money({ ...gap.gap, academic_year: null })}
                              {/* The year on its own line: on one line this was
                                  the widest column in the table, and the width
                                  it took came out of the bucket beside it. */}
                              {gap.gap.academic_year && (
                                <div className="xs muted">{gap.gap.academic_year}</div>
                              )}
                            </>
                          ) : (
                            <span className="xs muted" title={gap?.reason}>{t('results.notComputable')}</span>
                          )}
                        </td>
                        <td className="num" data-label={t('col.deadline')}>
                          {r.admission_deadline ? date(r.admission_deadline) : <span className="xs muted">{t('results.notFound')}</span>}
                          {r.deadline_passed && <div><Chip tone="risk">{t('shortlist.passed')}</Chip></div>}
                          {r.previous_cycle_deadline && <div className="xs muted">{tf('shortlist.previousCycle', { date: date(r.previous_cycle_deadline) })}</div>}
                        </td>
                        <td className="num" data-label={t('col.match')} title={tOr('results.fitDisclaimer', FIT_DISCLAIMER)}>
                          {ratio(r.ranking?.fit ?? null)}
                        </td>
                        <td className="num" data-label={t('col.confirmed')} data-testid={`coverage-${r.id}`}>
                          {percent(r.ranking?.coverage ?? null)}
                        </td>
                        {showBucket && (
                          <td data-label={t('col.bucket')}>
                            {r.ranking ? (
                              <StatusChip
                                status={r.ranking.bucket}
                                tone={bucketTone[r.ranking.bucket]}
                              />
                            ) : (
                              <span className="xs muted">{t('shortlist.notRanked')}</span>
                            )}
                          </td>
                        )}
                        <td data-label={t('col.decision')}>
                          <div className="decision-group" role="group" aria-label={tf('shortlist.decisionFor', { university: r.university })}>
                            <button
                              className="decision-btn decision-btn--approve"
                              aria-pressed={r.user_decision === 'approved'}
                              onClick={() => decideRow(r, 'approved')}
                              data-testid={`approve-${r.id}`}
                            >{t('results.yes')}</button>
                            <button
                              className="decision-btn decision-btn--maybe"
                              aria-pressed={r.user_decision === 'maybe'}
                              onClick={() => decideRow(r, 'maybe')}
                              data-testid={`maybe-${r.id}`}
                            >{t('shortlist.maybe')}</button>
                            <button
                              className="decision-btn decision-btn--reject"
                              aria-pressed={r.user_decision === 'rejected'}
                              onClick={() => decideRow(r, 'rejected')}
                              data-testid={`reject-${r.id}`}
                            >{t('results.no')}</button>
                          </div>
                          {rejectFor === r.id && (
                            <div
                              className="stack stack--tight"
                              style={{ marginTop: 6, minWidth: '13rem' }}
                              data-testid={`reject-reason-${r.id}`}
                            >
                              <label className="xs muted" htmlFor={`reject-input-${r.id}`}>
                                {t('shortlist.whyNot')}
                              </label>
                              <div className="row row--tight" style={{ flexWrap: 'wrap' }}>
                                {REJECTION_REASONS.map((preset) => (
                                  <button
                                    key={preset}
                                    type="button"
                                    className="btn btn--sm btn--ghost xs"
                                    onClick={() => setRejectReason(t(`shortlist.reason.${preset}` as MessageKey))}
                                    data-testid={`reject-chip-${preset.replace(/\s+/g, '-')}-${r.id}`}
                                  >{t(`shortlist.reason.${preset}` as MessageKey)}</button>
                                ))}
                              </div>
                              <input
                                id={`reject-input-${r.id}`}
                                value={rejectReason}
                                onChange={(e) => setRejectReason(e.target.value)}
                                placeholder={t('shortlist.whyNotPlaceholder')}
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
                                >{t('shortlist.saveRejection')}</button>
                                <button
                                  className="btn btn--sm btn--ghost"
                                  onClick={() => setRejectFor(null)}
                                  data-testid={`reject-cancel-${r.id}`}
                                >{t('results.cancel')}</button>
                              </div>
                            </div>
                          )}
                          {r.user_decision === 'rejected' && r.user_decision_reason && rejectFor !== r.id && (
                            <p className="xs faint" style={{ margin: '4px 0 0', maxWidth: '12rem' }}>
                              {tf('shortlist.rejected', { reason: r.user_decision_reason })}
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
                              {r.user_notes ? t('shortlist.editNote') : t('shortlist.addNote')}
                            </button>
                          </div>
                          {noteFor === r.id && (
                            <div className="stack stack--tight" style={{ marginTop: 6, minWidth: '13rem' }}>
                              <textarea
                                rows={2}
                                value={noteText}
                                onChange={(e) => setNoteText(e.target.value)}
                                placeholder={t('shortlist.notePlaceholder')}
                                data-testid={`note-input-${r.id}`}
                              />
                              <button
                                className="btn btn--sm"
                                onClick={async () => {
                                  await saveNotes(r.id, noteText);
                                  setNoteFor(null);
                                }}
                                data-testid={`note-save-${r.id}`}
                              >{t('shortlist.saveNote')}</button>
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
                          <td colSpan={showBucket ? 10 : 9}><ResultDetail result={r} knowledgeMode={capabilities?.knowledge_mode} /></td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
  );

  return (
    <div className="find-page">
      <details className="catalogue-expand"><summary>{t('shortlist.exploreCatalogue')}</summary><UniversityCatalogue onStart={onStart} onProgress={onProgress} /></details>
      <div className="find-hero">
        <div className="screen__head">
          <p className="screen__eyebrow">{t('shortlist.eyebrow')}</p>
          <h1 className="screen__title">{rich(t('shortlist.title'), { highlight: <span className="find-yellow">{t('shortlist.titleHighlight')}</span> })}</h1>
          <p className="screen__lede">{t('shortlist.lede')}</p>
        </div>
        <img src="/brand/unimatch-journey.png" alt={t('shortlist.mascotAlt')} />
      </div>

      <div className="stack stack--loose">
        {summary?.demo_data && (
          <Notice kind="demo">
            <div>
              <strong>{t('results.demoData')}</strong>{' '}
              {rich(t('shortlist.demoBody'), { code: <code>fixture://</code> })}
            </div>
          </Notice>
        )}

        <div className="find-toolbar">
          <label className="find-search"><span className="visually-hidden">{t('shortlist.search')}</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('shortlist.searchPlaceholder')} /></label>
          <button type="button" className="btn" onClick={() => document.getElementById('find-filters')?.toggleAttribute('open')}>{t('shortlist.filters')}</button>
          <button type="button" className="btn btn--dark" disabled={compareIds.length === 0} onClick={() => document.getElementById('find-compare')?.scrollIntoView({ behavior: 'smooth' })}>{tf('shortlist.compareCount', { n: compareIds.length })}</button>
        </div>
        <div className="find-tabs" role="tablist" aria-label={t('shortlist.matchList')}>
          {(['all', 'priority', 'saved', 'exploring'] as const).map((value) => <button key={value} type="button" role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>{t(`shortlist.tab.${value}`)}</button>)}
        </div>

        <details id="find-filters" className="find-filters">
          <summary>{t('shortlist.filterSort')}</summary>
        <Panel sunken>
          <div className="filters">
            <Field label={t('shortlist.country')} htmlFor="f-country">
              <select id="f-country" value={country} onChange={(e) => setCountry(e.target.value)}>
                <option value="">{tf('shortlist.allCount', { n: results.length })}</option>
                {countries.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </Field>
            <Field label={t('col.eligibility')} htmlFor="f-elig">
              <select id="f-elig" value={eligibility} onChange={(e) => setEligibility(e.target.value)}>
                <option value="">{t('shortlist.any')}</option>
                {Object.entries(summary?.by_eligibility ?? {}).map(([k, v]) => (
                  // The value stays the enum; only the label is for humans.
                  <option key={k} value={k}>{bucketLabel(k)} ({v})</option>
                ))}
              </select>
            </Field>
            <Field label={t('col.funding')} htmlFor="f-fund">
              <select id="f-fund" value={funding} onChange={(e) => setFunding(e.target.value)}>
                <option value="">{t('shortlist.any')}</option>
                {Object.entries(summary?.by_funding ?? {}).map(([k, v]) => (
                  <option key={k} value={k}>{bucketLabel(k)} ({v})</option>
                ))}
              </select>
            </Field>
            <Field label={t('shortlist.sortBy')} htmlFor="f-sort">
              <select id="f-sort" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
                {(['key', 'fit', 'coverage', 'gap', 'deadline', 'university'] as const).map((value) => (
                  <option key={value} value={value}>{t(`shortlist.sort.${value}`)}</option>
                ))}
              </select>
            </Field>
            <label className="row row--tight small" style={{ paddingBottom: 6 }}>
              <input type="checkbox" checked={hideRejected} onChange={(e) => setHideRejected(e.target.checked)} />
              {t('shortlist.hideRejected')}
            </label>
          </div>
        </Panel>
        </details>

        <div className="find-results" aria-live="polite">
          <p className="find-results__count">{tn('shortlist.resultCount', rows.length)}</p>
          {rows.length === 0 && <div className="find-empty"><Empty title={t('shortlist.noMatchTitle')}>{t('shortlist.noMatchBody')}</Empty><button type="button" className="btn" onClick={() => { setQuery(''); setTab('all'); setCountry(''); setEligibility(''); setFunding(''); setHideRejected(false); }}>{t('shortlist.clearFilters')}</button></div>}
          {rows.map((result) => {
            const open = cardExpanded === result.id;
            const selected = compareIds.includes(result.id);
            const gap = result.funding_gap;
            return (
              <article className="find-card" key={result.id} data-testid={`card-${result.id}`}>
                <div className="find-card__body">
                  <span className="find-card__eyebrow">{result.country} · {result.city}</span>
                  <h2>{result.university}</h2>
                  <p>{result.program}</p>
                  <div className="find-card__signals">
                    {result.ranking && <Chip tone={bucketTone[result.ranking.bucket]}>{bucketLabel(result.ranking.bucket)}</Chip>}
                    <StatusChip status={result.eligibility} tone={eligibilityTone[result.eligibility]} />
                    <StatusChip status={result.best_funding_classification} tone={fundingClassTone[result.best_funding_classification]} />
                  </div>
                  <div className="find-card__facts">
                    <span><small>{t('col.remaining')}</small><strong>{gap?.computable && gap.gap ? money({ ...gap.gap, academic_year: null }) : t('results.notEnoughData')}</strong></span>
                    <span><small>{t('col.deadline')}</small><strong>{result.admission_deadline ? date(result.admission_deadline) : t('results.notConfirmed')}</strong></span>
                  </div>
                  {(result.conflicts.length > 0 || openQuestionCount(result) > 0) && <p className="find-card__caution">{tn('results.conflictCount', result.conflicts.length)} · {tn('results.questionCount', openQuestionCount(result))}</p>}
                </div>
                <div className="find-card__actions">
                  <button type="button" className="btn btn--dark" onClick={() => setCardExpanded(open ? null : result.id)} aria-expanded={open} data-testid={`card-expand-${result.id}`}>{open ? t('shortlist.hideDetails') : t('shortlist.viewDetails')}</button>
                  <button type="button" className="btn" onClick={() => decideRow(result, 'maybe')} aria-pressed={result.user_decision === 'maybe' || result.user_decision === 'approved'}>{result.user_decision === 'maybe' || result.user_decision === 'approved' ? t('shortlist.saved') : t('shortlist.save')}</button>
                  <button type="button" className="btn" onClick={() => setCompareIds((current) => selected ? current.filter((id) => id !== result.id) : current.length < 3 ? [...current, result.id] : current)} aria-pressed={selected} disabled={!selected && compareIds.length >= 3}>{selected ? t('results.remove') : t('results.compare')}</button>
                </div>
                {open && <div className="find-card__detail"><ResultDetail result={result} knowledgeMode={capabilities?.knowledge_mode} /></div>}
              </article>
            );
          })}
        </div>

        {compareIds.length > 0 && (
          <ComparePanel
            results={compareIds.map((id) => results.find((item) => item.id === id)).filter((item): item is ProgramResult => Boolean(item))}
            onRemove={(id) => setCompareIds((current) => current.filter((item) => item !== id))}
            onClear={() => setCompareIds([])}
          />
        )}

        <details className="find-advanced">
          <summary>{t('shortlist.evidenceTable')}</summary>
        {shortlist && shortlist.chosen.length > 0 && (
          <Panel
            title={t('shortlist.balancedTitle')}
            hint={t('shortlist.balancedHint')}
          >
            <ol className="stack stack--tight" data-testid="balanced-shortlist">
              {shortlist.chosen.map((r) => (
                <li key={r.id} className="small">
                  <strong>{r.university}</strong> — {r.program}{' '}
                  {r.ranking && (
                    <Chip tone={bucketTone[r.ranking.bucket]}>
                      {bucketLabel(r.ranking.bucket)}
                    </Chip>
                  )}
                </li>
              ))}
            </ol>
            {shortlist.notes.map((note) => (
              <p key={note} className="xs muted" data-testid="shortlist-note">{note}</p>
            ))}
          </Panel>
        )}

        {ranked.length > 0 ? (
          renderTable(
            ranked,
            'shortlist-table',
            t('shortlist.caption'),
          )
        ) : (
          // An empty table with headers reads as "nothing found". Something
          // was found; it is all in the sections below, with its reason.
          <Notice kind="info">
            <div>
              {t('shortlist.nothingRanked')}
            </div>
          </Notice>
        )}

        <p className="xs faint">
          {rich(tf('shortlist.rankedFootnote', { shown: ranked.length, total: results.length }), {
            match: <strong>{t('col.match')}</strong>,
            confirmed: <strong>{t('col.confirmed')}</strong>,
          })}
        </p>

        {SET_ASIDE.map((bucket) => {
          const setAside = rows.filter((r) => r.ranking?.bucket === bucket);
          if (setAside.length === 0) return null;
          return (
            <details key={bucket} className="stack" data-testid={`section-${bucket}`}>
              <summary className="small">
                {bucketLabel(bucket)} ({setAside.length})
              </summary>
              <p className="xs muted">{SET_ASIDE_HINT[bucket] && t(SET_ASIDE_HINT[bucket])}</p>
              {renderTable(
                setAside,
                `table-${bucket}`,
                tf('shortlist.captionSetAside', { bucket: bucketLabel(bucket).toLowerCase() }),
                false,
              )}
            </details>
          );
        })}
        </details>


        <p className="xs faint">
          {tf('shortlist.footnote', { shown: rows.length, total: results.length })}
        </p>
      </div>
    </div>
  );
}

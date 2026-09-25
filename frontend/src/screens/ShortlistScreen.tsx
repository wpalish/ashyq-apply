/**
 * Screen 04 — University shortlist.
 *
 * Two views of the same rows. Cards are the default («Горизонт»): the price a
 * year after grants as the headline, and requirements, profile and money as
 * three separate lines with their reasons - a student reads one programme at a
 * time. The table is one tap away for comparing thirty rows on the same axes,
 * with the match, what is confirmed and the bucket (brief §267). Eligibility,
 * admissions fit and funding stay three separate judgements in both, because
 * collapsing them would hide which one is the problem.
 */

import { Fragment, useMemo, useState } from 'react';
import { BudgetLadder, ceilingFrom } from '@/components/BudgetLadder';
import { CompareView } from '@/components/CompareView';
import { REGION_LABEL, REGION_ORDER, regionCounts, regionOf, type Region } from '@/lib/regions';
import { Globe } from '@/components/Globe';
import { REGION_VIEW, centroidOf, defaultView, homeOf, markersFor } from '@/lib/globe';
import { ResultCard } from '@/components/ResultCard';
import { ResultDetail } from '@/components/ResultDetail';
import { LazyShareSheet } from '@/components/LazyShareSheet';
import { Triage } from '@/components/Triage';
import { Chip, Empty, Field, Notice, Panel, StatusChip } from '@/components/primitives';
import {
  FIT_DISCLAIMER, STATUS_LABEL, admissionsFitTone, bucketTone, date, eligibilityTone,
  fundingClassTone, humanize, money, percent, ratio,
} from '@/lib/format';
import { useStore } from '@/lib/store';
import type { Bucket, ProgramResult, UserDecision } from '@/types';

type SortKey = 'key' | 'fit' | 'coverage' | 'gap' | 'university' | 'deadline';

//: Buckets that are ranked against each other. The rest are real answers too,
//: but they answer a different question, so they sit in their own sections
//: below rather than competing for a place in the top ten.
const RANKED: Bucket[] = ['WELL_PLACED', 'PLAUSIBLE', 'AMBITIOUS'];
const SET_ASIDE: Bucket[] = ['OUT_OF_BUDGET', 'NEEDS_CLARIFICATION', 'EXCLUDED'];

const SET_ASIDE_HINT: Record<string, string> = {
  OUT_OF_BUDGET: 'Kept with the number, not hidden: you may know something about the money that we do not.',
  NEEDS_CLARIFICATION: 'Too little could be verified to place these. Ask the admissions office the open questions on the row.',
  EXCLUDED: 'A published requirement that is not met, or a country you excluded.',
};

//: The four reasons applicants actually give, as one-click chips. Free text
//: stays available because these will never cover every case.
const REJECTION_REASONS = ['cost', 'deadline passed', 'no funding', 'not a fit'];

const SORT_LABEL: Record<SortKey, string> = {
  key: 'Match, discounted by what is unverified',
  fit: 'Match with your priorities',
  coverage: 'Most confirmed',
  gap: 'Smallest remaining cost',
  deadline: 'Earliest deadline',
  university: 'University name',
};

type View = 'cards' | 'table';
const VIEW_KEY = 'ashyq.shortlistView';
const COMPARE_KEY = 'ashyq.compare';
/** Three columns is what a phone can hold side by side and still be read. */
const COMPARE_MAX = 3;

function storedCompare(): string[] {
  try {
    const raw = JSON.parse(window.localStorage.getItem(COMPARE_KEY) ?? '[]');
    return Array.isArray(raw) ? raw.filter((id): id is string => typeof id === 'string').slice(0, COMPARE_MAX) : [];
  } catch {
    return [];
  }
}

function storedView(): View {
  try {
    return window.localStorage.getItem(VIEW_KEY) === 'table' ? 'table' : 'cards';
  } catch {
    return 'cards';
  }
}

/** "computer science · Netherlands, Germany +3 · up to 6,000 USD a year" */
function searchSummary(profile: unknown): string | null {
  const p = profile as {
    context?: { intended_fields?: string[] };
    preferences?: { preferred_countries?: string[] };
    funding?: { max_annual_budget?: number | null; budget_currency?: string };
  } | null | undefined;
  if (!p) return null;
  const fields = p.context?.intended_fields ?? [];
  const countries = p.preferences?.preferred_countries ?? [];
  const where = countries.length === 0
    ? 'anywhere'
    : countries.length <= 2 ? countries.join(', ') : `${countries.slice(0, 2).join(', ')} +${countries.length - 2}`;
  const budget = typeof p.funding?.max_annual_budget === 'number'
    ? `up to ${p.funding.max_annual_budget.toLocaleString('en-US')} ${p.funding.budget_currency ?? 'USD'} a year`
    : 'no budget set';
  return [fields.join(', ') || 'any subject', where, budget].join(' · ');
}

export function ShortlistScreen({ onEditSearch }: { onEditSearch?: () => void } = {}) {
  const { results, summary, shortlist, decide, saveNotes, savedProfile, capabilities } = useStore();
  const rate = capabilities?.currency
    ? { date: capabilities.currency.rate_date, source: capabilities.currency.rate_source }
    : null;
  const [view, setViewState] = useState<View>(storedView);
  const setView = (next: View) => {
    setViewState(next);
    try {
      window.localStorage.setItem(VIEW_KEY, next);
    } catch {
      /* the choice still holds on this screen */
    }
  };
  const [expanded, setExpanded] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>('key');
  const [country, setCountry] = useState('');
  const [region, setRegionState] = useState<Region | ''>('');
  // A cluster tapped on the globe: where to look, and how close. A region
  // chip starts from that region's own view again.
  const [globeCloser, setGlobeCloser] = useState<{ lat: number; lon: number; zoom: number } | null>(null);
  const setRegion = (next: Region | '') => {
    setRegionState(next);
    setGlobeCloser(null);
  };
  const [eligibility, setEligibility] = useState('');
  const [funding, setFunding] = useState('');
  const [hideRejected, setHideRejected] = useState(false);
  const [noteFor, setNoteFor] = useState<string | null>(null);
  const [noteText, setNoteText] = useState('');
  const [rejectFor, setRejectFor] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [triageTotal, setTriageTotal] = useState<number | null>(null);
  // The programme a story card is being made for (concept Q).
  const [shareFor, setShareFor] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>(storedCompare);
  const [comparing, setComparing] = useState(false);
  const saveCompare = (next: string[]) => {
    setCompareIds(next);
    try {
      window.localStorage.setItem(COMPARE_KEY, JSON.stringify(next));
    } catch {
      /* the picks still hold on this screen */
    }
  };

  const countries = useMemo(
    () => Array.from(new Set(results.map((r) => r.country))).sort(),
    [results],
  );

  const rows = useMemo(() => {
    const filtered = results.filter(
      (r) =>
        (!region || regionOf(r.country) === region) &&
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
  }, [results, region, country, eligibility, funding, hideRejected, sort]);

  // A row with no ranking is one assessed under v1; it still belongs in the
  // list rather than in a set-aside section it was never scored for.
  const ranked = rows.filter((r) => !r.ranking || RANKED.includes(r.ranking.bucket));
  const home = homeOf(savedProfile);
  const globe = useMemo(() => markersFor(rows), [rows]);
  const globeZoom = globeCloser?.zoom ?? (region && REGION_VIEW[region] ? REGION_VIEW[region].zoom : 1);

  if (results.length === 0) {
    return <Empty title="No results yet">Run the research first.</Empty>;
  }

  const ceiling = ceilingFrom(savedProfile);
  const undecided = rows.filter((r) => r.user_decision === 'undecided');

  /** Open a row's detail from the ladder, wherever the row sits. */
  const openRow = (id: string) => {
    setExpanded(id);
    window.setTimeout(() => {
      const el = document.querySelector(`[data-testid="row-${id}"], [data-testid="card-${id}"]`);
      // A set-aside row lives in a collapsed section; open it first.
      const section = el?.closest('details');
      if (section && !section.open) section.open = true;
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 0);
  };

  // Picks from an older run whose rows are gone simply drop out.
  const picked = compareIds
    .map((id) => results.find((r) => r.id === id))
    .filter((r): r is ProgramResult => Boolean(r));
  const toggleCompare = (id: string) => {
    const ids = picked.map((r) => r.id);
    if (ids.includes(id)) saveCompare(ids.filter((other) => other !== id));
    else if (ids.length < COMPARE_MAX) saveCompare([...ids, id]);
  };

  const closeCompare = () => {
    setComparing(false);
    setTimeout(() => document.querySelector<HTMLElement>('[data-testid="compare-go"]')?.focus(), 0);
  };

  if (comparing && picked.length >= 2) {
    return (
      <>
        <h1 className="visually-hidden">The shortlist, compared row by row</h1>
        <CompareView
          programmes={picked}
          onRemove={(id) => {
            toggleCompare(id);
            // One programme is not a comparison: back to the list, and a
            // later pick does not reopen this view without being asked.
            if (picked.length - 1 < 2) closeCompare();
          }}
          onClose={closeCompare}
        />
      </>
    );
  }

  if (triageTotal !== null) {
    return (
      <>
        {/* The card is the screen here, as in the concept: the heading stays
            for assistive technology, and the answers stay above the fold. */}
        <h1 className="visually-hidden">The shortlist, one programme at a time</h1>
        <Triage
          queue={undecided}
          total={triageTotal}
          decide={decide}
          home={home}
          onClose={() => {
            setTriageTotal(null);
            // Back where the person started; the title when nothing is left to decide.
            setTimeout(() => {
              const start = document.querySelector<HTMLElement>('[data-testid="triage-start"]');
              (start ?? document.getElementById('shortlist-title'))?.focus();
            }, 0);
          }}
        />
      </>
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

  /** Yes / Maybe / No, the reason and the note: one set of controls for the
   *  table row and the card, so both views decide the same way. */
  const renderDecision = (r: ProgramResult) => (
    <>
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
    </>
  );

  const renderCard = (r: ProgramResult) => (
    <ResultCard
      key={r.id}
      result={r}
      open={expanded === r.id}
      onToggle={() => setExpanded(expanded === r.id ? null : r.id)}
      decision={renderDecision(r)}
      detail={<ResultDetail result={r} rate={rate} home={home} onShare={() => setShareFor(r.id)} />}
      compare={(() => {
        const on = picked.some((p) => p.id === r.id);
        const full = !on && picked.length >= COMPARE_MAX;
        return (
          <button
            type="button"
            className="btn btn--sm rcard__compare"
            aria-pressed={on}
            disabled={full}
            title={full ? `Compare at most ${COMPARE_MAX} at a time` : undefined}
            onClick={() => toggleCompare(r.id)}
            data-testid={`compare-${r.id}`}
          >
            {on ? 'In comparison' : 'Compare'}
          </button>
        );
      })()}
    />
  );

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
                  <th scope="col">University &amp; programme</th>
                  <th scope="col">Eligibility</th>
                  <th scope="col">Admissions fit</th>
                  <th scope="col">Funding</th>
                  <th scope="col">Remaining / year</th>
                  <th scope="col">Deadline</th>
                  <th scope="col" title={FIT_DISCLAIMER}>Match</th>
                  <th scope="col" title="How much of the weight rests on data we confirmed.">Confirmed</th>
                  {showBucket && <th scope="col">Bucket</th>}
                  <th scope="col">Decision</th>
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
                            <span className="xs muted" title={gap?.reason}>not computable</span>
                          )}
                        </td>
                        <td className="num" data-label="Deadline">
                          {r.admission_deadline ? date(r.admission_deadline) : <span className="xs muted">not found</span>}
                          {r.deadline_passed && <div><Chip tone="risk">passed</Chip></div>}
                        </td>
                        <td className="num" data-label="Match" title={FIT_DISCLAIMER}>
                          {ratio(r.ranking?.fit ?? null)}
                        </td>
                        <td className="num" data-label="Confirmed" data-testid={`coverage-${r.id}`}>
                          {percent(r.ranking?.coverage ?? null)}
                        </td>
                        {showBucket && (
                          <td data-label="Bucket">
                            {r.ranking ? (
                              <StatusChip
                                status={r.ranking.bucket}
                                tone={bucketTone[r.ranking.bucket]}
                              />
                            ) : (
                              <span className="xs muted">not ranked</span>
                            )}
                          </td>
                        )}
                        <td data-label="Decision">{renderDecision(r)}</td>
                      </tr>
                      {open && (
                        <tr className="detail-row">
                          <td colSpan={showBucket ? 10 : 9}><ResultDetail result={r} rate={rate} home={home} onShare={() => setShareFor(r.id)} /></td>
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
    <>
      <div className="screen__head">
        {searchSummary(savedProfile) && (
          <button
            type="button"
            className="search-pill"
            onClick={onEditSearch}
            disabled={!onEditSearch}
            data-testid="search-pill"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">
              <circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" strokeWidth="2.2" />
              <path d="m15.5 15.5 5 5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
            </svg>
            <span className="search-pill__text">{searchSummary(savedProfile)}</span>
          </button>
        )}
        <p className="screen__eyebrow">
          {results.length} programme{results.length === 1 ? '' : 's'} · {countries.length} countr{countries.length === 1 ? 'y' : 'ies'}
        </p>
        <h1 className="screen__title" id="shortlist-title" tabIndex={-1}>The shortlist</h1>
        <p className="screen__lede">
          <strong>Requirements</strong>, your <strong>profile</strong> and <strong>money</strong>:
          three separate answers per programme. None of them predicts a decision.
        </p>
        <div className="shortlist-actions">
          {undecided.length > 0 && (
            <>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => setTriageTotal(undecided.length)}
                data-testid="triage-start"
              >
                Decide one at a time
              </button>
              <span className="small muted">{undecided.length} without an answer yet</span>
            </>
          )}
          <div className="segmented" role="group" aria-label="View">
            <button
              type="button"
              aria-pressed={view === 'cards'}
              onClick={() => setView('cards')}
              data-testid="view-cards"
            >Cards</button>
            <button
              type="button"
              aria-pressed={view === 'table'}
              onClick={() => setView('table')}
              data-testid="view-table"
            >Table</button>
          </div>
        </div>
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

        {/* Concept 07's region chips: counted from every result, so a chip
            never promises programmes the list will not show. */}
        <div className="region-chips" role="group" aria-label="Region" data-testid="region-chips">
          <button type="button" aria-pressed={region === ''} onClick={() => setRegion('')} data-testid="region-all">
            All <span className="region-chips__n">{results.length}</span>
          </button>
          {regionCounts(results).map(({ region: r, count }) => (
            <button
              key={r}
              type="button"
              aria-pressed={region === r}
              disabled={count === 0}
              onClick={() => setRegion(region === r ? '' : r)}
              data-testid={`region-${r}`}
            >
              {REGION_LABEL[r]} <span className="region-chips__n">{count}</span>
            </button>
          ))}
        </div>

        {/* Concept N's list over a small globe: the programmes the filters
            show, at their cities; a region chip turns it to that region, and
            a marker opens its card. The list stays the way through - the
            globe is for looking. */}
        {view === 'cards' && (
          <div className="shortlist-globe">
            {globeCloser && (
              <button type="button" className="btn btn--sm shortlist-globe__out" onClick={() => setGlobeCloser(null)} data-testid="globe-out">
                {/* With a region chosen, going back out stops at the region. */}
                {region && REGION_VIEW[region] ? `All of ${REGION_LABEL[region]}` : 'Whole globe'}
              </button>
            )}
            <Globe
              layout="band"
              tone="day"
              height={230}
              markers={globe.markers}
              home={home}
              focus={globeCloser ?? (region && REGION_VIEW[region] ? REGION_VIEW[region] : defaultView(home))}
              zoom={globeZoom}
              onCluster={(members) => {
                const lat = members.reduce((n, m) => n + m.lat, 0) / members.length;
                const lon = members.reduce((n, m) => n + m.lon, 0) / members.length;
                setGlobeCloser({ lat, lon, zoom: Math.min(12, globeZoom * 2.4) });
              }}
              onEdge={(members) => {
                // One city: bring it round at this zoom. A region's worth:
                // that region's own view, as its chip above would give.
                const only = members.length === 1 ? members[0] : undefined;
                const groups = new Set(members.map((m) => m.group));
                const key = groups.size === 1
                  ? REGION_ORDER.find((r) => REGION_LABEL[r] === members[0]?.group)
                  : undefined;
                const whole = key ? REGION_VIEW[key] : undefined;
                if (only) setGlobeCloser({ lat: only.lat, lon: only.lon, zoom: globeZoom });
                else if (whole) setGlobeCloser({ ...whole });
                else setGlobeCloser({ ...centroidOf(members), zoom: 1 });
              }}
              routes={false}
              selected={expanded}
              onSelect={openRow}
              caption={`A globe with ${globe.markers.length} of the ${rows.length} programmes shown at their cities.`}
              testId="shortlist-globe"
            />
            {globe.unplaced > 0 && (
              <p className="shortlist-globe__note" data-testid="globe-unplaced">
                {globe.unplaced} programme{globe.unplaced === 1 ? ' is' : 's are'} not on the globe: the city is not in its table yet.
              </p>
            )}
          </div>
        )}

        {ceiling && (
          <BudgetLadder results={rows} ceiling={ceiling} onOpen={openRow} folded={view === 'cards'} />
        )}

        {view === 'table' ? (
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
                {(Object.keys(SORT_LABEL) as SortKey[]).map((key) => (
                  <option key={key} value={key}>{SORT_LABEL[key]}</option>
                ))}
              </select>
            </Field>
            <label className="row row--tight small" style={{ paddingBottom: 6 }}>
              <input type="checkbox" checked={hideRejected} onChange={(e) => setHideRejected(e.target.checked)} />
              Hide rejected
            </label>
          </div>
          </Panel>
        ) : (
          // One line in the cards view, as the concept's "best for you" sort:
          // the same controls, folded until they are wanted.
          <details className="panel panel--fold filters-fold" data-testid="filters-fold">
            <summary className="panel__summary">
              <span className="panel__summary-text">
                <h2 className="panel__title">Sort and filter</h2>
                <span className="panel__hint">
                  {SORT_LABEL[sort]} · showing {rows.length} of {results.length}
                </span>
              </span>
              <span className="panel__state">
                {[region, country, eligibility, funding].filter(Boolean).length + (hideRejected ? 1 : 0) || 'none'} on
              </span>
            </summary>
            <div className="panel__body">
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
                {(Object.keys(SORT_LABEL) as SortKey[]).map((key) => (
                  <option key={key} value={key}>{SORT_LABEL[key]}</option>
                ))}
              </select>
            </Field>
            <label className="row row--tight small" style={{ paddingBottom: 6 }}>
              <input type="checkbox" checked={hideRejected} onChange={(e) => setHideRejected(e.target.checked)} />
              Hide rejected
            </label>
          </div>
            </div>
          </details>
        )}

        {view === 'table' && shortlist && shortlist.chosen.length > 0 && (
          <Panel
            title="A balanced shortlist"
            hint="Filled to quota before the ranking speaks: a top ten of ten ambitious options is a list nobody can act on."
          >
            <ol className="stack stack--tight" data-testid="balanced-shortlist">
              {shortlist.chosen.map((r) => (
                <li key={r.id} className="small">
                  <strong>{r.university}</strong> — {r.program}{' '}
                  {r.ranking && (
                    <Chip tone={bucketTone[r.ranking.bucket]}>
                      {STATUS_LABEL[r.ranking.bucket] ?? humanize(r.ranking.bucket)}
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

        {view === 'cards' ? (
          <>
            {ranked.length > 0 ? (
              <div className="rcards" data-testid="shortlist-cards">{ranked.map(renderCard)}</div>
            ) : (
              <Notice kind="info">
                <div>
                  Nothing here is both affordable and verified enough to rank. Every option is in a
                  section below, with the reason it is there.
                </div>
              </Notice>
            )}
            {SET_ASIDE.map((bucket) => {
              const setAside = rows.filter((r) => r.ranking?.bucket === bucket);
              if (setAside.length === 0) return null;
              return (
                <details key={bucket} className="stack" data-testid={`cards-${bucket}`}>
                  <summary className="small">
                    {STATUS_LABEL[bucket] ?? humanize(bucket)} ({setAside.length})
                  </summary>
                  <p className="xs muted">{SET_ASIDE_HINT[bucket]}</p>
                  <div className="rcards">{setAside.map(renderCard)}</div>
                </details>
              );
            })}
            <p className="xs faint">
              Showing {rows.length} of {results.length}. The table view adds the match with your
              priorities, how much of it is confirmed, and the bucket.
            </p>
          </>
        ) : null}

        {view === 'table' && (ranked.length > 0 ? (
          renderTable(
            ranked,
            'shortlist-table',
            'Shortlisted university programmes with eligibility, fit, funding and remaining cost',
          )
        ) : (
          // An empty table with headers reads as "nothing found". Something
          // was found; it is all in the sections below, with its reason.
          <Notice kind="info">
            <div>
              Nothing here is both affordable and verified enough to rank. Every option is in a
              section below, with the reason it is there.
            </div>
          </Notice>
        ))}

        {view === 'table' && <p className="xs faint">
          Showing {ranked.length} of {results.length} ranked rows. <strong>Match</strong> is how well
          a place fits the priorities you stated, on confirmed data — not a probability of admission.
          The <strong>Confirmed</strong> percentage is how much of that judgement rests on data we could verify.
        </p>}

        {view === 'table' && SET_ASIDE.map((bucket) => {
          const setAside = rows.filter((r) => r.ranking?.bucket === bucket);
          if (setAside.length === 0) return null;
          return (
            <details key={bucket} className="stack" data-testid={`section-${bucket}`}>
              <summary className="small">
                {STATUS_LABEL[bucket] ?? humanize(bucket)} ({setAside.length})
              </summary>
              <p className="xs muted">{SET_ASIDE_HINT[bucket]}</p>
              {renderTable(
                setAside,
                `table-${bucket}`,
                `Shortlisted university programmes set aside as ${(STATUS_LABEL[bucket] ?? humanize(bucket)).toLowerCase()}, `
                + 'with eligibility, fit, funding and remaining cost',
                false,
              )}
            </details>
          );
        })}


        {view === 'table' && (
          <p className="xs faint">
            Showing {rows.length} of {results.length}. Rejected rows are kept with their reason so the
            same programme is not proposed again without new information.
          </p>
        )}

        {picked.length > 0 && (
          <div className="compare-tray" data-testid="compare-tray" role="region" aria-label="Comparison">
            <span className="compare-tray__label">Compare</span>
            <span className="compare-tray__count">{picked.length} picked</span>
            <ul className="compare-tray__picks">
              {picked.map((r) => (
                <li key={r.id}>
                  <span className="compare-tray__name">{r.university}</span>
                  <span className="compare-tray__price">
                    {r.funding_gap?.computable && r.funding_gap.gap
                      ? money({ ...r.funding_gap.gap, academic_year: null })
                      : 'not computed'}
                  </span>
                  <button
                    type="button"
                    className="compare-tray__remove"
                    onClick={() => toggleCompare(r.id)}
                    aria-label={`Remove ${r.university} from the comparison`}
                  >×</button>
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="btn btn--dark compare-tray__go"
              disabled={picked.length < 2}
              title={picked.length < 2 ? 'Pick one more programme' : undefined}
              onClick={() => setComparing(true)}
              data-testid="compare-go"
            >
              {picked.length < 2 ? 'Pick one more' : `Compare ${picked.length} row by row`}
            </button>
          </div>
        )}
      </div>
      {shareFor && (
        <LazyShareSheet
          results={results}
          result={results.find((r) => r.id === shareFor) ?? null}
          profile={savedProfile}
          demo={Boolean(summary?.demo_data)}
          onClose={() => setShareFor(null)}
        />
      )}
    </>
  );
}

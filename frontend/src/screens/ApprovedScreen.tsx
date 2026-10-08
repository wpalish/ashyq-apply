/**
 * Screen 07 — the plan: deadlines and decisions.
 *
 * The departures board first - the nearest deadline among the kept and
 * "maybe" programmes, then every one after it - and the decision ledger
 * under it. Rejected rows stay visible with their reason, because "why did I
 * rule this out in March" is a real question in October.
 */

import { useMemo, useState } from 'react';
import { DeadlineBoard } from '@/components/DeadlineBoard';
import { passColours, preferredCountries } from '@/lib/passColour';
import { Chip, Empty, Notice, Panel, StatusChip } from '@/components/primitives';
import { planDeadlines } from '@/lib/deadlines';
import { doneKey, nextToStart, useDocsDone } from '@/lib/docs';
import { date, eligibilityTone, fundingClassTone, money } from '@/lib/format';
import { useStore } from '@/lib/store';
import type { ProgramResult, UserDecision } from '@/types';

export function ApprovedScreen({ onCollect }: { onCollect: () => void }) {
  const { results, run, collectDocuments, decide, savedProfile } = useStore();
  const passes = useMemo(
    () => passColours(results.map((r) => r.country), preferredCountries(savedProfile)),
    [results, savedProfile],
  );
  const [done, toggle] = useDocsDone();

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
  const planned = planDeadlines(results);
  const datedCount = planned.filter((p) => p.day !== null).length;

  return (
    <>
      <header className="plan-head">
        <h1 className="plan-title">Plan</h1>
        <p className="plan-sub">
          {approved.length} kept programme{approved.length === 1 ? '' : 's'}
          {maybe.length > 0 && <> · {maybe.length} maybe</>}
          {' · '}{datedCount} date{datedCount === 1 ? '' : 's'}
        </p>
      </header>

      <div className="stack stack--loose">
        <ThisWeek
          results={results}
          done={done}
          shortlisted={shortlisted}
          collecting={Boolean(collecting)}
          onCollect={async () => { await collectDocuments(); onCollect(); }}
          onOpen={onCollect}
        />

        <DeadlineBoard planned={planned} done={done} colourOf={(c) => passes.get(c)} />

        <NextToStart results={results} done={done} toggle={toggle} />

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
              {collecting ? 'Collecting…' : `Collect documents for ${shortlisted} programme${shortlisted === 1 ? '' : 's'}`}
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

/**
 * Concept L's "this week", made useful on any day: the documents with the
 * earliest start dates across the kept list, ticked here or on the documents
 * screen alike. The ones due to start within seven days say so.
 */
function NextToStart({
  results, done, toggle,
}: {
  results: ProgramResult[];
  done: Record<string, boolean>;
  toggle: (key: string) => void;
}) {
  // A document ticked here stays in place, struck through, until the next
  // visit: vanishing on the tick left no way to undo a slip from this list.
  const [tickedHere, setTickedHere] = useState<Set<string>>(() => new Set());
  const kept = results.filter((r) => r.user_decision === 'approved' || r.user_decision === 'maybe');
  if (kept.length === 0) return null;
  const collected = kept.some((r) => r.checklist);
  const settled = Object.fromEntries(Object.entries(done).filter(([key]) => !tickedHere.has(key)));
  const tasks = nextToStart(results, settled);
  const shown = tasks.slice(0, 3);
  return (
    <Panel title="Next to start" hint="From your document lists: each one's due date minus the time it takes.">
      <div data-testid="next-to-start">
        {!collected ? (
          <p className="small muted">Collect documents for what you keep, and the first ones to start appear here.</p>
        ) : shown.length === 0 ? (
          <p className="small muted">Nothing left to start on the dates that are known.</p>
        ) : (
          <>
            <ul className="next-docs">
              {shown.map(({ result, item, timing }) => {
                const key = doneKey(result, item);
                const soon = timing.late || timing.daysToStart <= 7;
                return (
                  <li key={key} className={`next-docs__item${done[key] ? ' is-done' : ''}`}>
                    <input
                      type="checkbox"
                      checked={Boolean(done[key])}
                      onChange={() => {
                        toggle(key);
                        setTickedHere((prev) => new Set(prev).add(key));
                      }}
                      aria-label={`${item.name}, ${result.university}: ready`}
                    />
                    <span>
                      <span className="next-docs__name">{item.name}</span>
                      <span className="next-docs__where"> · {result.university} · due {date(timing.due)}</span>
                    </span>
                    <span className={`next-docs__when${soon ? ' next-docs__when--soon' : ''}`}>
                      {timing.late ? 'start now' : timing.daysToStart <= 7 ? `this week · by ${date(timing.start)}` : `by ${date(timing.start)}`}
                    </span>
                  </li>
                );
              })}
            </ul>
            {tasks.length > shown.length && (
              <p className="xs muted" style={{ marginTop: 'var(--space-2)' }}>
                and {tasks.length - shown.length} more on the documents screen
              </p>
            )}
          </>
        )}
      </div>
    </Panel>
  );
}

/**
 * The plan's black card (concept «Пропуск»): what to do this week. Before
 * the document lists exist it asks for them; after, it names the documents
 * whose start date falls within seven days - each one's due date minus the
 * time it takes, from the lists - and opens the documents screen.
 */
function ThisWeek({
  results, done, shortlisted, collecting, onCollect, onOpen,
}: {
  results: ProgramResult[];
  done: Record<string, boolean>;
  shortlisted: number;
  collecting: boolean;
  onCollect: () => void;
  onOpen: () => void;
}) {
  const kept = results.filter((r) => r.user_decision === 'approved' || r.user_decision === 'maybe');
  const collected = kept.some((r) => r.checklist);
  const tasks = collected ? nextToStart(results, done) : [];
  const week = tasks.filter(({ timing }) => timing.late || timing.daysToStart <= 7);
  const names = [...new Set(week.map(({ item }) => item.name))];

  let title: string;
  let detail: string;
  let action: { label: string; run: () => void; disabled?: boolean } | null;
  if (shortlisted === 0) {
    title = 'Keep a programme to start a plan';
    detail = 'Its deadlines and the documents it asks for appear here.';
    action = null;
  } else if (!collected) {
    title = `Collect the document lists for ${shortlisted} programme${shortlisted === 1 ? '' : 's'}`;
    detail = 'The slowest step, so it runs only on what you keep.';
    action = { label: collecting ? 'Collecting…' : 'Collect', run: onCollect, disabled: collecting };
  } else if (names.length > 0) {
    title = `${names.length} document${names.length === 1 ? '' : 's'} to start`;
    detail = names.slice(0, 3).join(' · ') + (names.length > 3 ? ` · and ${names.length - 3} more` : '');
    action = { label: 'Open', run: onOpen };
  } else {
    const next = tasks[0];
    title = 'Nothing to start this week';
    detail = next ? `Next: ${next.item.name}, by ${date(next.timing.start)}` : 'Every document with a known date is ready.';
    action = { label: 'Open', run: onOpen };
  }
  return (
    <section className="week" aria-labelledby="week-title" data-testid="this-week">
      <div>
        <p className="week__kicker">This week</p>
        <h2 className="week__title" id="week-title">{title}</h2>
        <p className="week__detail">{detail}</p>
      </div>
      {action && (
        <button type="button" className="week__action" onClick={action.run} disabled={action.disabled} data-testid="this-week-action">
          {action.label}
        </button>
      )}
    </section>
  );
}

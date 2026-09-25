/**
 * Screen 03 — Research progress.
 *
 * There is never an unexplained spinner here: each stage names what it is
 * doing, how far it has got, and every page it failed to read.
 *
 * While the research runs, the top of the screen is round 7's night moment:
 * the stage in words, how far it has got, four counters, and what has been
 * found so far that is worth knowing - a requirement that rules a programme
 * out, a cost and an award from different years, a site that did not answer.
 * When it finishes, the same list stays under "How the research went".
 */

import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import { ceilingFrom, groupByBudget } from '@/components/BudgetLadder';
import { Chip, Loading, Notice, Panel, Stat } from '@/components/primitives';
import { findingTotals, findingsSoFar, type Finding } from '@/lib/findings';
import { dateTime } from '@/lib/format';
import { useStore } from '@/lib/store';

const STAGE_LABELS: Record<string, string> = {
  queued: 'Starting the research',
  profile_validation: 'Checking your profile',
  candidate_discovery: 'Finding candidate universities',
  program_verification: 'Reading official programme pages',
  funding_discovery: 'Reading official scholarship pages',
  assessment: 'Comparing your profile against what was published',
  awaiting_user_decision: 'Waiting for your decisions',
  document_collection: 'Collecting documents for approved programmes',
  completed: 'Finished',
};

function errorCategory(message: string): string {
  const value = message.toLowerCase();
  if (/timeout|429|rate limit|temporar|network|server error/.test(value)) return 'Temporary fetch issue';
  if (/no known|no .*url|not found|missing page/.test(value)) return 'Official page not located';
  if (/not applicable|degree|intake|citizenship/.test(value)) return 'Page not applicable to this applicant';
  if (/robots|blocked|refused/.test(value)) return 'Site policy prevented reading';
  return 'Page could not be interpreted';
}

function FoundList({ findings, more }: { findings: Finding[]; more: number }) {
  return (
    <>
      <ul className="found__list" data-testid="found-list">
        {findings.map((f) => (
          <li key={`${f.kind}-${f.where}-${f.text}`} className={`found__item found__item--${f.kind}`}>
            <span className="found__label">{f.label}</span>
            <span className="found__where">{f.where}</span>
            <span className="found__text">{f.text}</span>
          </li>
        ))}
      </ul>
      {more > 0 && <p className="found__more">and {more} more like these in the results</p>}
    </>
  );
}

export function ProgressScreen({ onDone }: { onDone: () => void }) {
  const { run, cancelRun, retryRun, recheckNow, results, savedProfile } = useStore();
  // Work the queue gave up on after exhausting its attempts. It is asked for
  // here, before the early return, because a hook cannot live behind one.
  const [deadJobs, setDeadJobs] = useState(0);
  const runStage = run?.stage;

  useEffect(() => {
    api
      .deadJobCount()
      .then(setDeadJobs)
      .catch(() => {
        // Only a workspace owner may read the queue. For anyone else this
        // line simply does not exist, and its absence must not break progress.
      });
  }, [runStage]);

  if (!run) {
    return (
      <Panel title="No research is running">
        <p className="muted small">Start a run from the preferences screen.</p>
      </Panel>
    );
  }

  const finished = ['awaiting_user_decision', 'completed'].includes(run.stage);
  const failed = run.stage === 'failed';
  const cancelled = run.stage === 'cancelled';
  // Where the pipeline actually stopped. Retrying from here keeps the stages
  // that already succeeded, which is what the old single button claimed to do
  // while in fact restarting everything.
  const stoppedStage = run.stages.find((s) => s.status === 'failed' || s.status === 'running')?.stage;
  // The API says stale when a run claims to be working but its worker has gone
  // silent. Without this the screen showed a frozen spinner, no error and no
  // way out — the user could only reload and hope.
  const abandoned = run.stale && !run.job_running && !finished && !failed && !cancelled;
  const groupedErrors = run.errors.reduce<Record<string, string[]>>((groups, message) => {
    const category = errorCategory(message);
    (groups[category] ??= []).push(message);
    return groups;
  }, {});
  // Older runs, made before the two were separated, carry everything in
  // `errors`; they keep rendering under the failures panel rather than being
  // silently reclassified.
  const unknowns = run.unknowns ?? [];

  // The reveal: what the run found, counted from the results themselves. A
  // count is only shown when the data can say it - the budget tile needs a
  // budget, and none of them is a chance of anything.
  const revealed = finished && results.length > 0;
  const running = !finished && !failed && !cancelled;
  const findings = findingsSoFar(run.errors, results, 2, run.pages_failed);
  const moreFindings = findingTotals(run.errors, results, run.pages_failed) - findings.length;
  const runningStage = run.stages.find((s) => s.status === 'running');
  const percent = Math.round(run.progress * 100);
  const countries = new Set(results.map((r) => r.country)).size;
  const met = results.filter((r) => r.eligibility === 'MET').length;
  const livingGrant = results.filter((r) => r.best_funding_classification === 'FULL_RIDE_CONFIRMED').length;
  const ceiling = ceilingFrom(savedProfile);
  const withinBudget = ceiling ? groupByBudget(results, ceiling).within.length : null;

  return (
    <>
      {revealed ? (
        <section className="reveal" aria-labelledby="reveal-title" data-testid="results-reveal">
          <p className="reveal__kicker">Research complete</p>
          <h1 className="reveal__title" id="reveal-title">
            {results.length} programme{results.length === 1 ? '' : 's'} in {countries} countr{countries === 1 ? 'y' : 'ies'}
          </h1>
          <dl className="reveal__tiles">
            <div className="reveal__tile">
              <dt>meet every published requirement checked so far</dt>
              <dd>{met}</dd>
            </div>
            <div className="reveal__tile">
              <dt>have a published grant for tuition and living</dt>
              <dd>{livingGrant}</dd>
            </div>
            <div className="reveal__tile">
              <dt>facts, each with a link to its page</dt>
              <dd>{run.claims_recorded}</dd>
            </div>
            {withinBudget !== null && ceiling ? (
              <div className="reveal__tile">
                <dt>left to pay within {ceiling.amount.toLocaleString('en-US')} {ceiling.currency} a year, if awarded</dt>
                <dd>{withinBudget}</dd>
              </div>
            ) : (
              <div className="reveal__tile">
                <dt>official pages read</dt>
                <dd>{run.pages_checked}</dd>
              </div>
            )}
          </dl>
          <p className="reveal__note">
            Prices after grants, sources with dates, deadlines and documents are in the results.
            Grants are mostly competitive, and admission is decided by the university.
          </p>
          <button className="btn btn--primary reveal__cta" onClick={onDone} data-testid="to-shortlist">
            See {results.length} programme{results.length === 1 ? '' : 's'}
          </button>
        </section>
      ) : running ? (
        <section className="reveal reveal--running" aria-labelledby="running-title" data-testid="research-running">
          <p className="reveal__kicker">Research running</p>
          <h1 className="reveal__title reveal__title--stage" id="running-title">
            {STAGE_LABELS[run.stage] ?? run.stage.replace(/_/g, ' ')}
          </h1>
          <div className="reveal__progress">
            <div className="meter meter--night" role="progressbar" aria-valuenow={percent}
                 aria-valuemin={0} aria-valuemax={100} aria-label="Research progress">
              <div className="meter__fill" style={{ width: `${Math.max(3, percent)}%` }} />
            </div>
            <span>
              {runningStage && runningStage.items_total > 0
                ? `${runningStage.items_done} of ${runningStage.items_total} in this stage · `
                : ''}
              {percent}% of stages complete
            </span>
          </div>
          <dl className="reveal__tiles reveal__tiles--four">
            <div className="reveal__tile"><dt>programmes checked</dt><dd>{run.programs_verified}</dd></div>
            <div className="reveal__tile"><dt>official pages read</dt><dd>{run.pages_checked}</dd></div>
            <div className="reveal__tile"><dt>facts recorded, each with its page</dt><dd>{run.claims_recorded}</dd></div>
            <div className="reveal__tile"><dt>pages that could not be read</dt><dd>{run.pages_failed}</dd></div>
          </dl>
          <div className="found">
            <h2 className="found__title">Found so far</h2>
            {findings.length > 0
              ? <FoundList findings={findings} more={moreFindings} />
              : <p className="found__none">Nothing to flag yet. Requirements and money are compared once the pages are read.</p>}
          </div>
        </section>
      ) : (
        <div className="screen__head">
          <p className="screen__eyebrow">Match · Research</p>
          <h1 className="screen__title">
            {failed ? 'Research failed' : cancelled ? 'Research cancelled' : finished ? 'Research complete' : 'Researching'}
          </h1>
          <p className="screen__lede">{STAGE_LABELS[run.stage] ?? run.stage.replace(/_/g, ' ')}</p>
        </div>
      )}

      {revealed && <h2 className="reveal__how">How the research went</h2>}

      <div className="stack stack--loose">
        {!running && <div className="stack stack--tight">
          <div className="meter" role="progressbar" aria-valuenow={Math.round(run.progress * 100)}
               aria-valuemin={0} aria-valuemax={100} aria-label="Research progress">
            <div className="meter__fill" style={{ width: `${Math.max(3, run.progress * 100)}%` }} />
          </div>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <span className="xs muted">{Math.round(run.progress * 100)}% of stages complete</span>
            <span className="xs faint">
              started {dateTime(run.started_at)}
              {run.finished_at && ` · finished ${dateTime(run.finished_at)}`}
            </span>
          </div>
        </div>}

        {abandoned && (
          <Notice kind="risk">
            <div className="stack stack--tight" data-testid="stale-run">
              <div>
                <strong>The worker stopped responding.</strong> This run last reported progress
                {run.heartbeat_at ? ` at ${dateTime(run.heartbeat_at)}` : ' some time ago'} and
                nothing has happened since. Your results so far are saved.
              </div>
              {run.job_error && <div className="xs mono muted">{run.job_error}</div>}
              {run.recovery_count > 0 && (
                <div className="xs muted">
                  Recovered and restarted {run.recovery_count} time
                  {run.recovery_count === 1 ? '' : 's'} already.
                </div>
              )}
              <div className="row">
                <button
                  className="btn btn--primary"
                  onClick={() => retryRun(stoppedStage)}
                  data-testid="retry-stale"
                >
                  Resume from {STAGE_LABELS[stoppedStage ?? ''] ?? 'where it stopped'}
                </button>
                <button className="btn btn--ghost" onClick={cancelRun} data-testid="cancel-stale">
                  Cancel this run
                </button>
              </div>
            </div>
          </Notice>
        )}

        {deadJobs > 0 && (
          <Notice kind="warn">
            <div data-testid="dead-jobs">
              <strong>
                {deadJobs} job{deadJobs === 1 ? '' : 's'} need
                {deadJobs === 1 ? 's' : ''} attention.
              </strong>{' '}
              The queue tried each of them until its attempts ran out and then stopped. Nothing is
              retrying them on its own — re-run the affected research, or ask an operator to look
              at the queue.
            </div>
          </Notice>
        )}

        {/* While the research runs, the night panel above carries the counters;
            once it has finished they settle back onto the page. */}
        {!running && (
          <div className="statband">
            <Stat value={run.candidates_found} label="Candidates found" />
            <Stat value={run.programs_verified} label="Programmes checked" />
            <Stat value={run.pages_checked} label="Official pages read" />
            <Stat value={run.pages_failed} label="Pages unreadable" />
            <Stat value={run.claims_recorded} label="Claims recorded" />
            <Stat value={results.length} label="Results ready" />
          </div>
        )}

        {!running && findings.length > 0 && (
          <Panel title="Found along the way" hint="Read off the results and the pages, so none of it is a guess.">
            <div className="found found--day">
              <FoundList findings={findings} more={moreFindings} />
            </div>
          </Panel>
        )}

        {finished && (
          <p className="small muted">
            Pages that could not be read: <strong>{run.pages_failed}</strong>. Any facts depending
            on them remain unknown and are never guessed.
          </p>
        )}

        {finished && (
          <div className="row" style={{ justifyContent: 'space-between' }} data-testid="recheck">
            <span className="small muted">
              {run.next_recheck_at
                ? <>Next automatic re-check of this evidence: <strong>{dateTime(run.next_recheck_at)}</strong>.</>
                : 'This run holds no dated evidence to re-check.'}
            </span>
            <button className="btn btn--sm btn--ghost" onClick={recheckNow} data-testid="recheck-now">
              Re-verify now
            </button>
          </div>
        )}

        <Panel title="Stages">
          <div className="stage-list" data-testid="stage-list">
            {run.stages.map((s) => (
              <div key={s.stage} className={`stage stage--${s.status}`}>
                <span className="stage__dot" aria-hidden="true" />
                <div>
                  <div className="stage__name">{STAGE_LABELS[s.stage] ?? s.stage.replace(/_/g, ' ')}</div>
                  {s.detail && <div className="stage__detail">{s.detail}</div>}
                  {s.error && <div className="stage__detail" style={{ color: 'var(--risk)' }}>{s.error}</div>}
                </div>
                <div className="row row--tight">
                  {s.items_total > 0 && (
                    <span className="num xs faint">{s.items_done}/{s.items_total}</span>
                  )}
                  <Chip tone={s.status === 'done' ? 'ok' : s.status === 'failed' ? 'risk' : s.status === 'running' ? 'accent' : 'neutral'}>
                    {s.status}
                  </Chip>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        {unknowns.length > 0 && (
          <Panel
            title="What could not be confirmed"
            hint={
              `${unknowns.length} facts were not published on the pages that were read. `
              + 'This is normal, and none of them was guessed — each stays unknown in the results.'
            }
          >
            <details data-testid="unknowns-panel">
              <summary className="small">
                <strong>Unconfirmed facts</strong> · {unknowns.length}
              </summary>
              <div
                className="stack stack--tight"
                style={{ maxHeight: '12rem', overflowY: 'auto', marginTop: 'var(--space-2)' }}
                tabIndex={0}
                role="region"
                aria-label="Facts that could not be confirmed"
              >
                {unknowns.slice(0, 60).map((message, index) => (
                  <div key={index} className="xs mono muted" style={{ overflowWrap: 'anywhere' }}>{message}</div>
                ))}
              </div>
            </details>
          </Panel>
        )}

        {run.errors.length > 0 && (
          <Panel title="Fetch failures" data-testid="failures-panel"
            hint={`${run.errors.length} pages could not be read at all. Anything that depended on them is unknown, never guessed.`}>
            <div className="stack stack--tight">
              {Object.entries(groupedErrors).map(([category, messages]) => (
                <details key={category}>
                  <summary className="small"><strong>{category}</strong> · {messages.length}</summary>
                  <div
                    className="stack stack--tight"
                    style={{ maxHeight: '12rem', overflowY: 'auto', marginTop: 'var(--space-2)' }}
                    tabIndex={0}
                    role="region"
                    aria-label={`${category} diagnostics`}
                  >
                    {messages.slice(0, 30).map((message, index) => (
                      <div key={index} className="xs mono muted" style={{ overflowWrap: 'anywhere' }}>{message}</div>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </Panel>
        )}

        {run.retry_urls.length > 0 && (
          <Notice kind="warn">
            <div>
              <strong>{run.retry_urls.length} pages are queued for a re-check.</strong> They failed
              transiently (timeout, rate limit, or a server error) rather than being missing.
            </div>
          </Notice>
        )}

        <div className="row">
          {run.job_running && (
            <>
              <Loading label="Working…" />
              <button className="btn btn--danger" onClick={cancelRun} data-testid="cancel-run">
                Cancel run
              </button>
            </>
          )}
          {(failed || cancelled) && stoppedStage && (
            <button
              className="btn btn--primary"
              onClick={() => retryRun(stoppedStage)}
              data-testid="retry-stage"
            >
              Retry from {STAGE_LABELS[stoppedStage] ?? stoppedStage.replace(/_/g, ' ')}
            </button>
          )}
          {(failed || cancelled || finished) && (
            <button
              className="btn btn--ghost"
              onClick={() => {
                if (
                  window.confirm(
                    'Re-run every stage? Programmes are read again from their official pages, '
                    + 'so values may change. Your approvals, rejections and notes are kept.',
                  )
                ) void retryRun();
              }}
              data-testid="retry-run"
            >
              Re-run everything
            </button>
          )}

        </div>
      </div>
    </>
  );
}

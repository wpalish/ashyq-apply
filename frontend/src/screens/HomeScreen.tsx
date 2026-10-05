/**
 * Home (concept «Пропуск» × «Горизонт», palette E).
 *
 * One question at the top - how many programmes still wait for the
 * applicant's answer - and the one way to answer it. Under it, the passes the
 * applicant has kept and the next deadline on them. On a desk the question
 * sits on the night band with the routes from home, and the counts the run
 * can stand behind sit under it. Every number is counted from the results;
 * none of them is a chance of anything.
 */

import { useMemo } from 'react';
import { ArrowRight } from '@phosphor-icons/react';
import { useStore } from '@/lib/store';
import type { ScreenId } from '@/App';
import { Globe } from '@/components/Globe';
import { Pass, PassAnswers } from '@/components/Pass';
import { Ticket } from '@/components/Ticket';
import { ceilingFrom, groupByBudget } from '@/components/BudgetLadder';
import { nextDeadline, planDeadlines } from '@/lib/deadlines';
import { defaultView, homeOf, markersFor } from '@/lib/globe';
import { passColours, preferredCountries } from '@/lib/passColour';
import { useMedia, WIDE } from '@/lib/useMedia';
import type { ProgramResult } from '@/types';

type HomeScreenProps = {
  onNavigate: (screen: ScreenId) => void;
  /** Open Find straight into deciding one programme at a time. */
  onDecide?: () => void;
};

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** "Fall 2027", when the profile says both. */
function intake(profile: unknown): string {
  const c = (profile as { context?: { intake_term?: unknown; intake_year?: unknown } } | null)?.context;
  const term = typeof c?.intake_term === 'string' ? c.intake_term : '';
  const year = typeof c?.intake_year === 'number' ? c.intake_year : null;
  return term && year ? `${term.charAt(0).toUpperCase()}${term.slice(1)} ${year}` : '';
}

export function HomeScreen({ onNavigate, onDecide }: HomeScreenProps) {
  const { savedProfile, run, results, hydrated, capabilities } = useStore();
  const wide = useMedia(WIDE);

  const undecided = results.filter((r) => r.user_decision === 'undecided');
  const kept = results.filter((r) => r.user_decision === 'approved');
  const maybe = results.filter((r) => r.user_decision === 'maybe');
  const active = run?.job_status === 'running' || run?.job_status === 'queued';
  const passes = useMemo(
    () => passColours(results.map((r) => r.country), preferredCountries(savedProfile)),
    [results, savedProfile],
  );
  // The phone shows the next one, as in the concept; the desk the next three.
  const deadlines = useMemo(() => {
    const planned = planDeadlines(results);
    const first = nextDeadline(planned);
    return first ? planned.slice(planned.indexOf(first)).filter((p) => p.day && !p.passed).slice(0, wide ? 3 : 1) : [];
  }, [results, wide]);

  if (!hydrated) return <div className="home-loading" role="status">Loading your journey…</div>;

  // The one question this screen asks, and the one way to answer it.
  const ask: { lead: string; rest: string; action: string; go: () => void } = !savedProfile
    ? { lead: 'Where can you study,', rest: 'and what will it cost?', action: 'Start with your profile', go: () => onNavigate('profile') }
    : active
      ? { lead: 'Your research', rest: 'is reading official pages', action: 'Follow the research', go: () => onNavigate('progress') }
      : results.length === 0
        ? { lead: 'Your profile is saved.', rest: 'Say where to look next.', action: 'Set preferences', go: () => onNavigate('preferences') }
        : undecided.length > 0
          ? {
            lead: plural(undecided.length, 'programme'),
            rest: `wait${undecided.length === 1 ? 's' : ''} for your answer`,
            action: 'Decide one at a time',
            go: () => (onDecide ? onDecide() : onNavigate('shortlist')),
          }
          : { lead: 'Every programme', rest: 'has your answer', action: 'Open your plan', go: () => onNavigate('approved') };

  const mine: ProgramResult[] = [...kept, ...maybe];
  const answered = [kept.length ? `${kept.length} kept` : '', maybe.length ? `${maybe.length} maybe` : ''].filter(Boolean).join(' · ');
  const when = intake(savedProfile);
  const demo = Boolean(capabilities?.demo_mode);

  return (
    <div className={`home${results.length ? ' home--results' : ''}`}>
      <section className="home__ask" aria-labelledby="home-title">
        {wide && results.length > 0 && <HomeBand results={results} passes={passes} profile={savedProfile} />}
        <div className="home__ask-copy">
          <p className="home__kicker">Home{when ? ` · ${when}` : ''}</p>
          <h1 id="home-title" className="home__title">
            {ask.lead}<br /><span>{ask.rest}</span>
          </h1>
          <div className="home__actions">
            <button className="btn btn--primary home__cta" type="button" onClick={ask.go} data-testid="home-cta">
              {ask.action} <ArrowRight size={18} weight="bold" aria-hidden="true" />
            </button>
            {results.length > 0 && (
              <button className="btn home__all" type="button" onClick={() => onNavigate('shortlist')}>
                See all {results.length}
              </button>
            )}
          </div>
          {wide && results.length > 0 && <Legend results={results} passes={passes} />}
        </div>
      </section>

      {results.length > 0 && (
        <HomeStats results={results} profile={savedProfile} claims={run?.claims_recorded ?? null} kept={kept.length} maybe={maybe.length} />
      )}

      {results.length > 0 && (
        <div className="home__grid">
          <section className="home__passes" aria-labelledby="home-passes">
            <header className="home__head">
              <h2 id="home-passes">Your passes</h2>
              {answered && <span>{answered}</span>}
            </header>
            {mine.length ? (
              <div className="pass-stack">
                {mine.slice(0, 3).map((r) => (
                  <Pass
                    key={r.id}
                    result={r}
                    colour={passes.get(r.country)}
                    title={<button type="button" onClick={() => onNavigate('shortlist')}>{r.city || r.university}</button>}
                    testId={`home-pass-${r.id}`}
                  >
                    <PassAnswers result={r} />
                  </Pass>
                ))}
              </div>
            ) : (
              <p className="home__empty">Keep a programme, or mark it maybe, and its pass appears here.</p>
            )}
            {mine.length > 3 && (
              <button className="home__more" type="button" onClick={() => onNavigate('approved')}>
                {plural(mine.length - 3, 'more pass', 'more passes')} on your plan
              </button>
            )}
          </section>

          <section className="home__deadlines" aria-labelledby="home-deadlines">
            <header className="home__head">
              <h2 id="home-deadlines">{deadlines.length > 1 ? 'Next deadlines' : 'Next deadline'}</h2>
              {deadlines.length > 0 && <button type="button" onClick={() => onNavigate('approved')}>Plan</button>}
            </header>
            {deadlines.length ? (
              <ul className="tickets">
                {deadlines.map((p) => <Ticket key={p.key} planned={p} colour={passes.get(p.result.country)} />)}
              </ul>
            ) : (
              <p className="home__empty">
                {mine.length
                  ? 'No published deadline ahead on the programmes you kept.'
                  : 'Deadlines appear once you keep a programme.'}
              </p>
            )}
          </section>
        </div>
      )}

      {demo && <p className="home__demo">Demo data: synthetic programmes and pages, not real offers.</p>}
    </div>
  );
}

/** The counts under the question, each one the run can stand behind. */
function HomeStats({ results, profile, claims, kept, maybe }: {
  results: ProgramResult[];
  profile: unknown;
  claims: number | null;
  kept: number;
  maybe: number;
}) {
  const met = results.filter((r) => r.eligibility === 'MET').length;
  const ceiling = ceilingFrom(profile);
  const within = ceiling ? groupByBudget(results, ceiling).within.length : null;
  return (
    <dl className="home__stats">
      <div><dt>meet every requirement checked so far</dt><dd>{met}</dd></div>
      {within !== null && ceiling && (
        <div><dt>within {ceiling.amount.toLocaleString('en-US')} {ceiling.currency} a year, if awarded</dt><dd>{within}</dd></div>
      )}
      <div><dt>kept{maybe ? ` · ${maybe} maybe` : ' so far'}</dt><dd>{kept}</dd></div>
      {claims !== null && <div><dt>facts, each with a link to its page</dt><dd>{claims}</dd></div>}
    </dl>
  );
}

/** The countries in the results, in their route colours. */
function Legend({ results, passes }: { results: ProgramResult[]; passes: Map<string, { slot: number }> }) {
  const counts = new Map<string, number>();
  for (const r of results) counts.set(r.country, (counts.get(r.country) ?? 0) + 1);
  const order = [...passes.keys()].filter((c) => counts.has(c));
  const shown = order.slice(0, 5);
  return (
    <ul className="home__legend" aria-label="Countries in the results">
      {shown.map((c) => (
        <li key={c} style={{ ['--tint' as string]: `var(--pass-tint-${passes.get(c)?.slot ?? 1})` }}>
          {c} {counts.get(c)}
        </li>
      ))}
      {order.length > shown.length && <li className="home__legend-more">+{order.length - shown.length} more countries</li>}
    </ul>
  );
}

/** The night band's globe: a route from home to every programme, in its country's tint. */
function HomeBand({ results, passes, profile }: {
  results: ProgramResult[];
  passes: Map<string, { slot: number }>;
  profile: unknown;
}) {
  const home = homeOf(profile);
  const markers = useMemo(() => {
    const country = new Map(results.map((r) => [r.id, r.country]));
    return markersFor(results).markers.map((m) => ({ ...m, slot: passes.get(country.get(m.id) ?? '')?.slot }));
  }, [results, passes]);
  return (
    <div className="home__globe" aria-hidden="true">
      <Globe
        layout="band"
        tone="night"
        height={330}
        markers={markers}
        home={home}
        focus={defaultView(home)}
        routes
        nameHome
        plain
        caption=""
        testId="home-globe"
      />
    </div>
  );
}

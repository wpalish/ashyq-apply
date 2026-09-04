/**
 * Screen 02 — Preferences, budget and scoring weights.
 *
 * The weights are exposed rather than hidden, because the score is only
 * defensible if the user can see and change what produced it.
 */

import { useState } from 'react';
import { Chip, Field, Notice, Panel } from '@/components/primitives';
import { castInput, get, setIn, type Path } from '@/lib/immutable';
import { useStore } from '@/lib/store';

const WEIGHT_LABELS: Record<string, string> = {
  academic_fit: 'Academic fit',
  funding_fit: 'Funding fit',
  extracurricular_alignment: 'Activities',
  program_quality: 'Programme standing',
  country_preference: 'Country preference',
  city_fit: 'City fit',
  climate_fit: 'Climate fit',
  workload_fit: 'Workload fit',
  career_outcomes: 'Careers & internships',
  post_study_work: 'Post-study work',
};

export function PreferencesScreen({ onStarted }: { onStarted: () => void }) {
  const { profileDraft, setProfileDraft, startRun, loading, capabilities, validation } = useStore();
  const [demoMode, setDemoMode] = useState(true);
  const [showAdvancedWeights, setShowAdvancedWeights] = useState(false);

  const bind = (path: Path, cast: 'string' | 'number' | 'float' = 'string') => ({
    value: String(get(profileDraft, path) ?? ''),
    onChange: (e: { target: { value: string } }) => {
      setProfileDraft((d) => setIn(d, path, castInput(e.target.value, cast)));
    },
  });

  const bindList = (path: Path) => ({
    value: ((get(profileDraft, path) as string[]) ?? []).join(', '),
    onChange: (e: { target: { value: string } }) =>
      setProfileDraft((d) =>
        setIn(d, path, e.target.value.split(',').map((s) => s.trim()).filter(Boolean)),
      ),
  });

  const bindBool = (path: Path) => ({
    checked: Boolean(get(profileDraft, path)),
    onChange: (e: { target: { checked: boolean } }) =>
      setProfileDraft((d) => setIn(d, path, e.target.checked)),
  });

  const weights = (get(profileDraft, ['weights']) ?? {}) as Record<string, number>;

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">Step 02</p>
        <h1 className="screen__title">What matters to you</h1>
        <p className="screen__lede">
          These shape the ordering, not the facts. Eligibility and funding are read from official
          pages either way — preferences only decide which of the qualifying options rise first.
        </p>
      </div>

      <div className="stack stack--loose">
        <Panel title="Where" hint="Countries you would actually move to, and any you would not.">
          <div className="grid-2">
            <Field label="Preferred countries" htmlFor="pref-countries" hint="Comma-separated.">
              <input id="pref-countries" data-testid="preferred-countries" {...bindList(['preferences', 'preferred_countries'])} />
            </Field>
            <Field label="Excluded countries" htmlFor="excl-countries" hint="These are never proposed.">
              <input id="excl-countries" {...bindList(['preferences', 'excluded_countries'])} />
            </Field>
            <Field label="City size" htmlFor="citysize">
              <select id="citysize" {...bind(['preferences', 'city_size'])}>
                {['any', 'small', 'medium', 'large', 'metropolis'].map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
            </Field>
            <Field label="Climate" htmlFor="climate">
              <select id="climate" {...bind(['preferences', 'climate'])}>
                {['any', 'cold', 'temperate', 'warm', 'mediterranean'].map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
            </Field>
            <Field label="Workload you can carry" htmlFor="workload">
              <select id="workload" {...bind(['preferences', 'acceptable_workload'])}>
                {['any', 'moderate', 'demanding', 'very_demanding'].map((v) => <option key={v} value={v}>{v.replace('_', ' ')}</option>)}
              </select>
            </Field>
            <Field label="Ranking band" htmlFor="rank-band">
              <select id="rank-band" {...bind(['preferences', 'target_ranking_band'])}>
                {['any', 'top_50', 'top_100', 'top_300', 'top_500'].map((v) => <option key={v} value={v}>{v.replace('_', ' ')}</option>)}
              </select>
            </Field>
            <Field label="University size" htmlFor="university-size">
              <select id="university-size" {...bind(['preferences', 'university_size'])}>
                {['any', 'small', 'medium', 'large'].map((v) => <option key={v}>{v}</option>)}
              </select>
            </Field>
            <Field label="Campus type" htmlFor="campus-type">
              <select id="campus-type" {...bind(['preferences', 'campus_type'])}>
                {['any', 'campus', 'urban', 'suburban'].map((v) => <option key={v}>{v}</option>)}
              </select>
            </Field>
            <Field label="Research interests" htmlFor="research-interests" hint="Comma-separated.">
              <input id="research-interests" {...bindList(['preferences', 'research_interests'])} />
            </Field>
            {/*
              Safety, diversity and housing-guarantee priorities used to be
              asked here. No official page this product reads publishes a
              comparable figure for any of them, so the answers changed
              nothing - and a question that changes nothing still implies the
              result was tailored to it. They are gone from the form; the
              fields remain in the schema only so profiles saved earlier still
              load. See docs/PROFILE_FIELDS.md.
            */}
          </div>
          <div className="row" style={{ marginTop: 'var(--space-4)' }}>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['preferences', 'values_internships'])} /> Internships matter
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['preferences', 'values_coop'])} /> Co-op programmes matter
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['preferences', 'needs_post_study_work'])} /> Need post-study work rights
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['preferences', 'needs_work_during_study'])} /> Need to work while studying
            </label>
          </div>
        </Panel>

        <Panel
          title="Budget"
          hint="Used to compute what is left after funding — never to hide options that cost more."
        >
          <div className="grid-2">
            <Field label="Maximum you can pay per year" htmlFor="budget">
              <input id="budget" data-testid="max-budget" type="number" {...bind(['funding', 'max_annual_budget'], 'float')} />
            </Field>
            <Field label="Currency" htmlFor="cur">
              <select id="cur" {...bind(['funding', 'budget_currency'])}>
                {(capabilities?.currency.supported ?? ['USD', 'EUR', 'GBP']).map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </Field>
            <Field label="Largest annual shortfall you could absorb" htmlFor="gap">
              <input id="gap" type="number" {...bind(['funding', 'max_acceptable_gap'], 'float')} />
            </Field>
            <Field label="Maximum family contribution" htmlFor="family-contribution">
              <input id="family-contribution" type="number" {...bind(['funding', 'max_family_contribution'], 'float')} />
            </Field>
            <Field label="How decisive is funding?" htmlFor="crit">
              <select id="crit" {...bind(['funding', 'funding_criticality'])}>
                <option value="nice_to_have">Nice to have</option>
                <option value="important">Important</option>
                <option value="decisive">Decisive</option>
              </select>
            </Field>
          </div>
          <div className="row" style={{ marginTop: 'var(--space-4)' }}>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['funding', 'requires_full_ride'])} /> Only a full ride works
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['funding', 'accepts_full_tuition'])} /> Full tuition is acceptable
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['funding', 'accepts_partial'])} /> Partial funding is acceptable
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['funding', 'must_cover_housing'])} /> Housing must be covered
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['funding', 'must_cover_meals'])} /> Meals must be covered
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['funding', 'must_cover_health_insurance'])} /> Health insurance must be covered
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['funding', 'must_cover_books'])} /> Books must be covered
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['funding', 'must_cover_travel'])} /> Travel must be covered
            </label>
            <label className="row row--tight small">
              <input type="checkbox" {...bindBool(['funding', 'willing_to_submit_need_documents'])} /> Willing to file financial-need documents
            </label>
          </div>
        </Panel>

        <Panel
          title="How should options be ordered?"
          hint="Choose a starting point. Advanced weights are available when you need fine control; this remains a preference match, never an admission probability."
        >
          <p className="small muted">
            The score only compares your stated preferences. It is not a probability of admission.
          </p>
          <div className="row">
            {([
              ['Funding first', { funding_fit: 2.5, academic_fit: 1.2, program_quality: 0.6 }],
              ['Balanced', { funding_fit: 1.5, academic_fit: 1.0, program_quality: 0.8 }],
              ['Academic fit first', { funding_fit: 1.0, academic_fit: 2.3, program_quality: 1.4 }],
            ] as const).map(([label, preset]) => (
              <button key={label} className="btn btn--sm" type="button" onClick={() =>
                setProfileDraft((draft) => setIn(draft, ['weights'], { ...weights, ...preset }))
              }>{label}</button>
            ))}
            <button className="btn btn--sm btn--ghost" type="button" onClick={() => setShowAdvancedWeights((value) => !value)}>
              {showAdvancedWeights ? 'Hide advanced weights' : 'Advanced weights'}
            </button>
          </div>
          {showAdvancedWeights && (
            <div className="grid-2" style={{ marginTop: 'var(--space-4)' }}>
              {Object.entries(WEIGHT_LABELS).map(([key, label]) => (
                <Field key={key} label={`${label} — ${(weights[key] ?? 0).toFixed(1)}`} htmlFor={`w-${key}`}>
                  <input
                    id={`w-${key}`} type="range" min={0} max={3} step={0.1}
                    value={weights[key] ?? 0}
                    onChange={(e) =>
                      setProfileDraft((d) => setIn(d, ['weights', key], Number.parseFloat(e.target.value)))
                    }
                  />
                </Field>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Run the research">
          <div className="stack">
            <label className="row row--tight">
              <input
                type="checkbox"
                data-testid="demo-toggle"
                checked={demoMode}
                onChange={(e) => setDemoMode(e.target.checked)}
              />
              <span className="small">
                <strong>Demo mode</strong> — use the bundled synthetic corpus. No network access,
                deterministic, and every value is badged as demo data.
              </span>
            </label>

            {!demoMode && (
              <Notice kind="warn">
                <div data-testid="live-mode-notice">
                  <strong>Live mode fetches real university websites.</strong> It honours robots.txt,
                  rate-limits per host, and never sends any part of your profile off this machine.
                  It is slower, and pages that cannot be read are reported as not found rather than
                  guessed.
                  {capabilities?.live_coverage && (
                    // Without this, "live" reads as "the open web". It is ten
                    // curated institutions, and the applicant deserves to know
                    // the size of the search before they wait for it.
                    <div className="stack stack--tight" data-testid="live-coverage">
                      <div><strong>{capabilities.live_coverage.recall_note}</strong></div>
                      {capabilities.live_coverage.countries.length > 0 && (
                        <div className="row row--tight">
                          {capabilities.live_coverage.countries.map((c) => (
                            <Chip key={c}>{c}</Chip>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </Notice>
            )}

            {validation && !validation.can_proceed && (
              <Notice kind="risk">
                <div><strong>Cannot start yet.</strong> {validation.summary}</div>
              </Notice>
            )}

            <div className="row">
              <button
                className="btn btn--primary"
                data-testid="start-research"
                disabled={loading || (validation ? !validation.can_proceed : false)}
                onClick={async () => {
                  await startRun(demoMode);
                  onStarted();
                }}
              >
                {loading ? 'Starting…' : 'Start research'}
              </button>
              {validation?.can_proceed && (
                <Chip tone="ok">{validation.gaps.length} gaps noted, none blocking</Chip>
              )}
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}

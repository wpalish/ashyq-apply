/**
 * The first screen: what to study, where, and what a year may cost.
 *
 * The concept opened on one question and three fields, and the app opened on
 * a form four thousand pixels long. Both ask for the same data - these three
 * fields are the ones the research cannot run without (a field of study) or
 * that decide the answer a family reads first (the budget) - and the rest of
 * the profile still makes the match more precise, one tap away and optional.
 *
 * Nothing here is new behaviour. The fields write the same draft the profile
 * and preferences screens write, and the button is the same `startRun` as
 * "Start research": it saves the profile first, and a blocking gap stops it
 * with the same reason.
 */

import { useEffect, useState, type InputHTMLAttributes } from 'react';
import { useStore } from '@/lib/store';
import { castInput, get, setIn, type Path } from '@/lib/immutable';

const parseList = (text: string) => text.split(',').map((item) => item.trim()).filter(Boolean);

/**
 * A comma-separated list the person can actually type into.
 *
 * Rendering the parsed list back into the box ate the comma the moment it was
 * typed ("a, " became "a"), so a second item could not be started. The box
 * keeps the typed text; the draft gets the parsed list; a list replaced from
 * outside (another applicant, the demo) replaces the text.
 */
function ListInput({
  value, onChange, ...rest
}: {
  value: string[];
  onChange: (next: string[]) => void;
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'>) {
  const [text, setText] = useState(value.join(', '));
  useEffect(() => {
    if (parseList(text).join('\u0000') !== value.join('\u0000')) setText(value.join(', '));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value.join('\u0000')]);
  return (
    <input
      {...rest}
      value={text}
      onChange={(e) => {
        setText(e.target.value);
        onChange(parseList(e.target.value));
      }}
    />
  );
}

export function StartScreen({
  onStarted, onOpenProfile, onOpenPreferences, onOpenResults,
}: {
  onStarted: () => void;
  onOpenProfile: () => void;
  onOpenPreferences: () => void;
  onOpenResults: () => void;
}) {
  const {
    profileDraft, setProfileDraft, startRun, loading, capabilities, validation, run, results,
  } = useStore();

  const list = (path: Path) => ({
    value: (get(profileDraft, path) as string[] | undefined) ?? [],
    onChange: (next: string[]) => setProfileDraft((d) => setIn(d, path, next)),
  });
  const bind = (path: Path, cast: 'string' | 'float' = 'string') => ({
    value: String(get(profileDraft, path) ?? ''),
    onChange: (e: { target: { value: string } }) =>
      setProfileDraft((d) => setIn(d, path, castInput(e.target.value, cast))),
  });

  const synthetic = String(profileDraft.display_name ?? '').includes('synthetic');
  const blocked = validation ? !validation.can_proceed : false;
  const currencies = capabilities?.currency.supported ?? ['USD', 'EUR', 'GBP'];

  return (
    <div className="start">
      <div className="start__intro">
        <h1 className="start__title">Find where you can study{'\u00A0'}— and what it will cost</h1>
        <p className="start__lede">
          Programmes whose published requirements you meet, and the price a year after grants.
          Every figure links to the university&rsquo;s own page, with the date it was read.
        </p>
      </div>

      <form
        className="start__card"
        aria-label="Search"
        onSubmit={async (event) => {
          event.preventDefault();
          if (blocked || loading) return;
          // Demo mode, as on Preferences: live mode reads real websites and
          // is chosen there, with its warning, never by default from here.
          await startRun(true);
          onStarted();
        }}
      >
        <label className="start__field start__field--wide" htmlFor="start-fields">
          <span className="start__label">What to study</span>
          <ListInput
            id="start-fields"
            data-testid="start-fields"
            placeholder="e.g. computer science"
            {...list(['context', 'intended_fields'])}
          />
        </label>
        <label className="start__field" htmlFor="start-countries">
          <span className="start__label">Where</span>
          <ListInput
            id="start-countries"
            data-testid="start-countries"
            placeholder="Anywhere"
            {...list(['preferences', 'preferred_countries'])}
          />
        </label>
        <div className="start__field">
          <label className="start__label" htmlFor="start-budget">Budget a year</label>
          <div className="start__budget">
            <input
              id="start-budget"
              data-testid="start-budget"
              type="number"
              min={0}
              inputMode="numeric"
              placeholder="No limit"
              {...bind(['funding', 'max_annual_budget'], 'float')}
            />
            <select aria-label="Currency" {...bind(['funding', 'budget_currency'])}>
              {currencies.map((code) => <option key={code} value={code}>{code}</option>)}
            </select>
          </div>
        </div>

        <button
          type="submit"
          className="btn btn--primary start__go"
          data-testid="start-search"
          disabled={loading || blocked}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
            <circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" strokeWidth="2.2" />
            <path d="m15.5 15.5 5 5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
          </svg>
          {loading ? 'Starting…' : 'Show programmes'}
        </button>

        {blocked && validation && (
          <p className="start__blocked" role="status" data-testid="start-blocked">{validation.summary}</p>
        )}
        <p className="start__small">
          {capabilities?.demo_mode !== false && (
            <>
              <strong>Demo data:</strong> a bundled synthetic corpus, not live university pages.{' '}
            </>
          )}
          {synthetic && <>The fields hold the synthetic demo applicant. </>}
          Nothing is predicted: the list compares your profile with what universities publish.
        </p>
      </form>

      <div className="start__more">
        <button type="button" className="start__link" onClick={onOpenProfile} data-testid="start-open-profile">
          <span>Add grades and test scores</span>
          <span className="start__hint">A precise match needs them; the search runs without.</span>
        </button>
        <button type="button" className="start__link" onClick={onOpenPreferences}>
          <span>More preferences</span>
          <span className="start__hint">Climate, city size, what matters most, live mode.</span>
        </button>
        {run && (
          <button type="button" className="start__link start__link--result" onClick={onOpenResults} data-testid="start-open-results">
            <span>{results.length > 0 ? `Your last search: ${results.length} programmes` : 'Your search is running'}</span>
            <span className="start__hint">Open it</span>
          </button>
        )}
      </div>

      <svg className="start__horizon" viewBox="0 0 400 120" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <path d="M-10 120 Q200 -20 410 120" fill="none" stroke="var(--route)" strokeWidth="2" strokeDasharray="2 7" strokeLinecap="round" />
        <circle cx="200" cy="50" r="7" fill="var(--sun)" />
      </svg>
    </div>
  );
}

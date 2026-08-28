/**
 * Screen 01 — Applicant profile.
 *
 * The form's job is to make the *cost of each gap* visible. Every missing
 * field is listed with what it will do to the result, so the applicant can
 * decide which blanks are worth filling.
 */

import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import { Chip, Field, Notice, Panel } from '@/components/primitives';
import { castInput, get, setIn, type Path } from '@/lib/immutable';
import { useStore } from '@/lib/store';

const SEVERITY_LABEL: Record<string, string> = {
  blocking: 'Blocks research',
  high: 'Strong effect on results',
  medium: 'Noticeable effect',
  low: 'Minor effect',
};

export function ProfileScreen({ onNext }: { onNext: () => void }) {
  const {
    profileDraft, setProfileDraft, validation, saveProfile, loading,
    savedProfile, restored, loadDemoProfile, clearProfile,
  } = useStore();
  const [saved, setSaved] = useState(false);
  const [confirmingReplace, setConfirmingReplace] = useState<'demo' | 'clear' | null>(null);
  const [methods, setMethods] = useState<
    { key: string; description: string; source: string; caveat: string; to_scale: string }[]
  >([]);

  const scaleLabel = String(get(profileDraft, ['academics', 'gpa', 'raw_scale_label']) ?? '');

  useEffect(() => {
    if (!scaleLabel) return;
    api.conversionMethods(scaleLabel).then((r) => setMethods(r.methods)).catch(() => setMethods([]));
  }, [scaleLabel]);

  const bind = (path: Path, cast: 'string' | 'number' | 'float' = 'string') => ({
    value: String(get(profileDraft, path) ?? ''),
    onChange: (e: { target: { value: string } }) => {
      setProfileDraft((d) => setIn(d, path, castInput(e.target.value, cast)));
      setSaved(false);
    },
  });

  const applyConversion = async (key: string) => {
    const gpa = get(profileDraft, ['academics', 'gpa']) as Record<string, unknown>;
    const converted = await api
      .validateProfile(profileDraft)
      .then(() =>
        fetch(`/api/profiles/conversions/preview?method_key=${key}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(gpa),
        }).then((r) => r.json()),
      );
    setProfileDraft((d) => setIn(d, ['academics', 'gpa'], converted));
  };

  const converted = get(profileDraft, ['academics', 'gpa', 'converted_value']);

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">Step 01</p>
        <h1 className="screen__title">Who is applying</h1>
        <p className="screen__lede">
          Nothing here is converted or inferred behind your back. Grades keep their original scale,
          and every blank below is listed with exactly what it costs you in the results.
        </p>
      </div>

      <div className="stack stack--loose">
        {restored && savedProfile && (
          <Notice kind="info">
            <div>
              Loaded <strong>{String(profileDraft.display_name)}</strong> from your saved profile.
              Edits here update that profile.
            </div>
          </Notice>
        )}

        <Panel
          title="Start from"
          hint="Demo data is never loaded on your behalf. Choose it explicitly, and it is clearly labelled everywhere it appears."
        >
          <div className="row">
            <button
              className="btn btn--sm"
              data-testid="clear-profile"
              onClick={() => (savedProfile ? setConfirmingReplace('clear') : clearProfile())}
            >
              Blank profile
            </button>
            <button
              className="btn btn--sm"
              data-testid="load-demo-profile"
              onClick={() => (savedProfile ? setConfirmingReplace('demo') : loadDemoProfile())}
            >
              Load synthetic demo
            </button>
            {String(profileDraft.display_name).includes('synthetic') && (
              <Chip tone="demo">synthetic demo data</Chip>
            )}
          </div>
          {confirmingReplace && (
            <Notice kind="warn">
              <div style={{ flex: 1 }}>
                <strong>Replace the profile you have saved?</strong> The saved copy is not deleted,
                but your unsaved edits are lost.
                <div className="row" style={{ marginTop: 'var(--space-3)' }}>
                  <button
                    className="btn btn--sm btn--danger"
                    data-testid="confirm-replace"
                    onClick={() => {
                      if (confirmingReplace === 'demo') loadDemoProfile();
                      else clearProfile();
                      setConfirmingReplace(null);
                    }}
                  >
                    Replace
                  </button>
                  <button className="btn btn--sm" onClick={() => setConfirmingReplace(null)}>
                    Keep editing
                  </button>
                </div>
              </div>
            </Notice>
          )}
        </Panel>

        <Panel title="Application context" hint="What you are applying for, and from where.">
          <div className="grid-2">
            <Field label="Level" htmlFor="level">
              <select id="level" {...bind(['context', 'level'])}>
                <option value="foundation">Foundation</option>
                <option value="bachelor">Bachelor</option>
                <option value="master">Master</option>
                <option value="phd">PhD</option>
              </select>
            </Field>
            <Field label="Field of study" htmlFor="field" hint="Drives which programmes are searched.">
              <input
                id="field"
                value={((get(profileDraft, ['context', 'intended_fields']) as string[]) ?? []).join(', ')}
                onChange={(e) =>
                  setProfileDraft((d) =>
                    setIn(d, ['context', 'intended_fields'],
                      e.target.value.split(',').map((s) => s.trim()).filter(Boolean)),
                  )
                }
              />
            </Field>
            <Field label="Intake term" htmlFor="term">
              <select id="term" {...bind(['context', 'intake_term'])}>
                <option value="fall">Fall</option>
                <option value="spring">Spring</option>
                <option value="summer">Summer</option>
                <option value="winter">Winter</option>
              </select>
            </Field>
            <Field label="Intake year" htmlFor="year">
              <input id="year" type="number" min={2024} max={2035} {...bind(['context', 'intake_year'], 'number')} />
            </Field>
            <Field label="Citizenship" htmlFor="citizenship"
                   hint="Decides which scholarships you are eligible for at all.">
              <input id="citizenship" {...bind(['context', 'citizenship'])} />
            </Field>
            <Field label="Country of residence" htmlFor="residence">
              <input id="residence" {...bind(['context', 'country_of_residence'])} />
            </Field>
            <Field label="Education system" htmlFor="edsys">
              <input id="edsys" {...bind(['context', 'education_system'])} />
            </Field>
            <Field label="Finishing school on" htmlFor="grad">
              <input id="grad" type="date" {...bind(['context', 'graduation_date'])} />
            </Field>
          </div>
        </Panel>

        <Panel
          title="Grades"
          hint="Enter the grade exactly as it appears on your transcript. UniMatch does not convert it silently."
        >
          <div className="grid-2">
            <Field label="GPA / average" htmlFor="gpa">
              <input id="gpa" type="number" step="0.01" {...bind(['academics', 'gpa', 'raw_value'], 'float')} />
            </Field>
            <Field label="Maximum on your scale" htmlFor="gpamax">
              <input id="gpamax" type="number" step="0.1" {...bind(['academics', 'gpa', 'raw_scale_max'], 'float')} />
            </Field>
            <Field label="Scale name" htmlFor="gpascale" hint="e.g. 'KZ 5-point', 'US 4.0 unweighted'">
              <input id="gpascale" {...bind(['academics', 'gpa', 'raw_scale_label'])} />
            </Field>
            <Field label="Class rank" htmlFor="rank">
              <input id="rank" type="number" {...bind(['academics', 'class_rank'], 'number')} />
            </Field>
          </div>

          {methods.length > 0 && (
            <div className="stack stack--tight" style={{ marginTop: 'var(--space-4)' }}>
              <p className="small muted" style={{ marginBottom: 0 }}>
                Programmes that publish a different scale cannot be decided without a conversion.
                You can accept one — the method and its caveat are stored with the number.
              </p>
              {converted != null ? (
                <Notice kind="info">
                  <div>
                    <strong>Converted to {String(get(profileDraft, ['academics', 'gpa', 'converted_scale_label']))}: {String(converted)}</strong>
                    <div className="xs" style={{ marginTop: 4 }}>
                      {String(get(profileDraft, ['academics', 'gpa', 'method_source']))}
                    </div>
                  </div>
                </Notice>
              ) : (
                <div className="row">
                  {methods.map((m) => (
                    <button
                      key={m.key}
                      type="button"
                      className="btn btn--sm"
                      title={m.caveat}
                      onClick={() => applyConversion(m.key)}
                      data-testid={`convert-${m.key}`}
                    >
                      Convert to {m.to_scale}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </Panel>

        <Panel
          title="English language"
          hint="Subscores matter: many programmes publish a per-section minimum on top of the overall band."
        >
          <div className="grid-3">
            {(['overall', 'listening', 'reading', 'writing', 'speaking'] as const).map((band) => (
              <Field key={band} label={`IELTS ${band}`} htmlFor={`ielts-${band}`}>
                <input
                  id={`ielts-${band}`}
                  data-testid={`ielts-${band}`}
                  type="number" step="0.5" min={0} max={9}
                  {...bind(['academics', 'ielts', band], 'float')}
                />
              </Field>
            ))}
            <Field label="Test type" htmlFor="ielts-type">
              <select id="ielts-type" {...bind(['academics', 'ielts', 'test_type'])}>
                <option value="academic">Academic</option>
                <option value="general_training">General Training</option>
                <option value="ukvi_academic">UKVI Academic</option>
                <option value="one_skill_retake">One Skill Retake</option>
              </select>
            </Field>
          </div>
        </Panel>

        <Panel title="Standardised tests" hint="Leave blank if not taken — test-optional programmes are unaffected.">
          <div className="grid-3">
            <Field label="SAT total" htmlFor="sat"><input id="sat" type="number" {...bind(['academics', 'sat', 'total'], 'number')} /></Field>
            <Field label="SAT Math" htmlFor="satm"><input id="satm" type="number" {...bind(['academics', 'sat', 'math'], 'number')} /></Field>
            <Field label="SAT Reading &amp; Writing" htmlFor="satr"><input id="satr" type="number" {...bind(['academics', 'sat', 'reading_writing'], 'number')} /></Field>
            <Field label="TOEFL total" htmlFor="toefl"><input id="toefl" type="number" {...bind(['academics', 'toefl', 'total'], 'number')} /></Field>
            <Field label="ACT composite" htmlFor="act"><input id="act" type="number" {...bind(['academics', 'act', 'composite'], 'number')} /></Field>
          </div>
        </Panel>

        {validation && (
          <Panel
            title="What is missing, and what it costs you"
            hint={validation.summary}
          >
            {validation.gaps.length === 0 ? (
              <p className="muted small">No gaps found. Every field that affects the result is present.</p>
            ) : (
              <div className="stack stack--tight" data-testid="gap-list">
                {validation.gaps.map((g) => (
                  <div key={g.field_path} className={`gap-item gap-item--${g.severity}`}>
                    <Chip tone={g.severity === 'blocking' ? 'risk' : g.severity === 'high' ? 'warn' : 'neutral'}>
                      {SEVERITY_LABEL[g.severity]}
                    </Chip>
                    <div>
                      <div className="gap-item__path">{g.field_path}</div>
                      <p className="small" style={{ margin: '2px 0 0' }}>{g.impact}</p>
                      {g.suggested_action && (
                        <p className="xs muted" style={{ margin: '4px 0 0' }}>→ {g.suggested_action}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        )}

        <div className="row">
          <button
            className="btn"
            disabled={loading}
            data-testid="save-profile"
            onClick={async () => {
              await saveProfile();
              setSaved(true);
            }}
          >
            {loading ? 'Saving…' : 'Save profile'}
          </button>
          {saved && <Chip tone="ok">Saved</Chip>}
          <button className="btn btn--primary" onClick={onNext} data-testid="to-preferences">
            Next: preferences &amp; budget →
          </button>
        </div>
      </div>
    </>
  );
}

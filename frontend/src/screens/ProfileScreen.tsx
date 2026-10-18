import { readPublicSearchIntent, clearPublicSearchIntent } from '@/lib/publicSearchIntent';
import { ProfileRecoveryPanel } from '@/components/ProfileRecoveryPanel';
/**
 * Screen 01 — Applicant profile.
 *
 * The form's job is to make the *cost of each gap* visible. Every missing
 * field is listed with what it will do to the result, so the applicant can
 * decide which blanks are worth filling.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, api } from '@/api/client';
import { CommaSeparatedInput } from '@/components/CommaSeparatedInput';
import { Chip, Field, Notice, Panel, SaveFeedback } from '@/components/primitives';
import { castInput, get, setIn, type Path } from '@/lib/immutable';
import { useStore } from '@/lib/store';
import type { TranscriptSuggestion } from '@/types';
import type { G3LiveCaseIdentity } from '@/lib/admissionsActionsRecovery';

type GradeInput = { identity: G3LiveCaseIdentity; fingerprint: string; generation: number };
type SuggestionInput = { input: GradeInput; serial: number; fields: Record<string, string> };
function sameCase(a: G3LiveCaseIdentity, b: G3LiveCaseIdentity): boolean {
  return a.scope === b.scope && a.profile_id === b.profile_id && a.case_epoch === b.case_epoch;
}

/** "4.82 out of 5", not "[object Object]". */
function describe(value: unknown): string {
  if (value && typeof value === 'object') {
    const gpa = value as { raw_value?: unknown; raw_scale_max?: unknown };
    if (gpa.raw_value != null && gpa.raw_scale_max != null) {
      return `${gpa.raw_value} out of ${gpa.raw_scale_max}`;
    }
    return Object.values(value as Record<string, unknown>).filter(Boolean).join(', ');
  }
  return String(value ?? '');
}

const SEVERITY_LABEL: Record<string, string> = {
  blocking: 'Blocks research',
  high: 'Strong effect on results',
  medium: 'Noticeable effect',
  low: 'Minor effect',
};
const PROFILE_STEPS = ['Personal details', 'Academic background', 'Tests & scores', 'Activities & achievements', 'Review'] as const;

export function ProfileScreen({ onNext }: { onNext: () => void }) {
  const {
    profileDraft, setProfileDraft, currentProfileDraft, currentAdmissionsCase, validation, saveProfile, loading,
    savedProfile, restored, loadDemoProfile, clearProfile, draftRestored, discardDraft, dirty, caseEpoch, profileRecovery, hydrated,
  } = useStore();
  const toolCaseKey = JSON.stringify(currentAdmissionsCase());
  let gradeGeneration = -1;
  try { gradeGeneration = currentProfileDraft().gpa_generation; } catch { /* An obsolete workspace exposes no input. */ }
  const mounted = useRef(true);
  const conversionSerial = useRef(0);
  const transcriptSerial = useRef(0);
  const methodsSerial = useRef(0);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const captureGrade = (): GradeInput => {
    const current = currentProfileDraft();
    return { identity: currentAdmissionsCase(), fingerprint: JSON.stringify(get(current.draft, ['academics', 'gpa']) ?? null), generation: current.gpa_generation };
  };
  const gradeIsCurrent = (input: GradeInput, serial: number, currentSerial: number): boolean => {
    if (!mounted.current || serial !== currentSerial) return false;
    try {
      const latest = captureGrade();
      return sameCase(input.identity, latest.identity) && input.generation === latest.generation && input.fingerprint === latest.fingerprint;
    } catch { return false; }
  };
  const [publicIntent, setPublicIntent] = useState(readPublicSearchIntent);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveFailed, setSaveFailed] = useState(false);
  const failedDraft = useRef<string | null>(null);
  const saveOwner = useRef({ epoch: caseEpoch, attempt: 0 });
  saveOwner.current.epoch = caseEpoch;
  useEffect(() => {
    const owner = saveOwner.current;
    ++owner.attempt;
    failedDraft.current = null;
    setSaving(false); setSaved(false); setSaveFailed(false);
    return () => { ++owner.attempt; };
  }, [caseEpoch]);
  useEffect(() => {
    // A failed unchanged draft waits for Save. A new semantic edit may autosave,
    // including list/transcript/conversion changes made outside input binding.
    if (saveFailed && failedDraft.current !== JSON.stringify(profileDraft)) {
      failedDraft.current = null;
      setSaveFailed(false);
    }
  }, [profileDraft, saveFailed]);
  const commitProfile = useCallback(async () => {
    const attemptedDraft = JSON.stringify(profileDraft);
    const attempt = ++saveOwner.current.attempt;
    const current = () => saveOwner.current.epoch === caseEpoch && saveOwner.current.attempt === attempt;
    failedDraft.current = null;
    setSaving(true); setSaveFailed(false);
    try {
      await saveProfile();
      if (current()) setSaved(true);
    } catch {
      if (current()) {
        failedDraft.current = attemptedDraft;
        setSaved(false); setSaveFailed(true);
      }
    } finally {
      if (current()) setSaving(false);
    }
  }, [saveProfile, caseEpoch, profileDraft]);
  const receiptConfirmsCurrentDraft = !dirty && !profileRecovery && Boolean(savedProfile?.write_receipt);
  const [step, setStep] = useState(1);
  const [confirmingReplace, setConfirmingReplace] = useState<'demo' | 'clear' | null>(null);
  const [methods, setMethods] = useState<
    { key: string; description: string; source: string; caveat: string; to_scale: string }[]
  >([]);

  const [conversionError, setConversionError] = useState<string | null>(null);

  const scaleLabel = String(get(profileDraft, ['academics', 'gpa', 'raw_scale_label']) ?? '');

  useEffect(() => {
    const clock = methodsSerial;
    const serial = ++methodsSerial.current;
    const identity = currentAdmissionsCase();
    const current = () => {
      if (!mounted.current || serial !== methodsSerial.current) return false;
      try {
        return sameCase(identity, currentAdmissionsCase())
          && scaleLabel === String(get(currentProfileDraft().draft, ['academics', 'gpa', 'raw_scale_label']) ?? '');
      } catch { return false; }
    };
    setMethods([]);
    if (scaleLabel) api.conversionMethods(scaleLabel).then(r => { if (current()) setMethods(r.methods); }).catch(() => { if (current()) setMethods([]); });
    return () => { ++clock.current; };
  }, [scaleLabel, caseEpoch, toolCaseKey, currentAdmissionsCase, currentProfileDraft]);

  useEffect(() => {
    // Recovered edits stay local until Save, as the recovery notice promises.
    if (!savedProfile || !dirty || loading || saving || saveFailed || draftRestored || profileRecovery) return;
    const timer = window.setTimeout(() => {
      void commitProfile();
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [savedProfile, dirty, loading, saving, saveFailed, draftRestored, profileDraft, commitProfile, profileRecovery]);

  const bind = (path: Path, cast: 'string' | 'number' | 'float' = 'string') => ({
    value: String(get(profileDraft, path) ?? ''),
    onChange: (e: { target: { value: string } }) => {
      setProfileDraft((d) => setIn(d, path, castInput(e.target.value, cast)));
      setSaved(false);
    },
  });

  const bindList = (path: Path) => ({
    items: get(profileDraft, path) as string[] | undefined,
    onItemsChange: (items: string[]) => {
      setProfileDraft((d) => setIn(d, path, items));
      setSaved(false);
    },
  });

  const [suggestions, setSuggestions] = useState<TranscriptSuggestion[]>([]);
  const [transcriptNote, setTranscriptNote] = useState('');
  const [transcriptBusy, setTranscriptBusy] = useState(false);
  const [suggestionInput, setSuggestionInput] = useState<SuggestionInput | null>(null);
  const gradeFingerprint = JSON.stringify(get(profileDraft, ['academics', 'gpa']) ?? null);
  // Clearing the rendered tools complements the synchronous completion guard.
  useEffect(() => {
    ++conversionSerial.current; ++transcriptSerial.current;
    setConversionError(null); setSuggestions([]); setSuggestionInput(null); setTranscriptNote(''); setTranscriptBusy(false);
  }, [caseEpoch, gradeFingerprint, gradeGeneration, toolCaseKey]);

  const readTranscript = async (file: File | undefined) => {
    if (!file) return;
    const serial = ++transcriptSerial.current;
    const input = captureGrade();
    const capturedDraft = currentProfileDraft().draft;
    setTranscriptBusy(true);
    setSuggestions([]);
    setSuggestionInput(null); setTranscriptNote('');
    try {
      const reading = await api.readTranscript(file);
      if (!gradeIsCurrent(input, serial, transcriptSerial.current)) return;
      setSuggestions(reading.suggestions);
      setSuggestionInput({ input, serial, fields: Object.fromEntries(reading.suggestions.map(s => [s.field, JSON.stringify(get(capturedDraft, s.field.split('.') as Path) ?? null)])) });
      setTranscriptNote(reading.note);
    } catch (e) {
      // The draft is not touched on failure, for the same reason the grade
      // conversion leaves it alone: a refused read must not cost the applicant
      // what they have already typed.
      if (gradeIsCurrent(input, serial, transcriptSerial.current)) setTranscriptNote(e instanceof ApiError ? e.message : 'That file could not be read.');
    } finally {
      if (gradeIsCurrent(input, serial, transcriptSerial.current)) setTranscriptBusy(false);
    }
  };

  /**
   * Apply one suggestion, field by field rather than wholesale.
   *
   * A transcript states a number and a scale; it does not know what the
   * applicant calls their grading system. Writing the whole object in would
   * blank the scale name they had already typed.
   */
  const applySuggestion = (suggestion: TranscriptSuggestion, binding: SuggestionInput | null) => {
    if (!binding || !gradeIsCurrent(binding.input, binding.serial, transcriptSerial.current)) return;
    const path = suggestion.field.split('.') as Path;
    if (binding.fields[suggestion.field] !== JSON.stringify(get(currentProfileDraft().draft, path) ?? null)) return;
    setProfileDraft((d) => {
      if (!gradeIsCurrent(binding.input, binding.serial, transcriptSerial.current)
        || binding.fields[suggestion.field] !== JSON.stringify(get(d, path) ?? null)) return d;
      if (suggestion.value && typeof suggestion.value === 'object') {
        return Object.entries(suggestion.value as Record<string, unknown>)
          .filter(([, v]) => v !== '' && v !== null && v !== undefined)
          .reduce((draft, [key, v]) => setIn(draft, [...path, key] as Path, v), d);
      }
      return setIn(d, path, suggestion.value);
    });
    setSuggestions((rest) => rest.filter((s) => s.field !== suggestion.field));
    setSaved(false);
  };

  const applyConversion = async (key: string) => {
    // The draft is only touched on success. The old code parsed the response
    // without checking it, so a 400 replaced the applicant's GPA object with
    // {detail: "..."} — their grades, gone, with no error shown.
    const input = captureGrade();
    const serial = ++conversionSerial.current;
    const gpa = get(currentProfileDraft().draft, ['academics', 'gpa']) as Record<string, unknown>;
    setConversionError(null);
    try {
      const converted = await api.previewConversion(gpa, key);
      if (!gradeIsCurrent(input, serial, conversionSerial.current)) return;
      setProfileDraft(d => gradeIsCurrent(input, serial, conversionSerial.current) ? setIn(d, ['academics', 'gpa'], converted) : d);
      setSaved(false);
    } catch (e) {
      if (gradeIsCurrent(input, serial, conversionSerial.current)) setConversionError(e instanceof ApiError ? e.message : 'The conversion could not be applied.');
    }
  };

  const converted = get(profileDraft, ['academics', 'gpa', 'converted_value']);
  const subjectGrades = (get(profileDraft, ['academics', 'subject_grades']) as Record<string, unknown>[]) ?? [];
  const curriculumResults = (get(profileDraft, ['academics', 'curriculum_results']) as Record<string, unknown>[]) ?? [];
  const otherTests = (get(profileDraft, ['academics', 'other_tests']) as Record<string, unknown>[]) ?? [];
  const activities = (get(profileDraft, ['activities']) as Record<string, unknown>[]) ?? [];
  const achievements = (get(profileDraft, ['achievements']) as Record<string, unknown>[]) ?? [];

  const append = (path: Path, item: Record<string, unknown>) => {
    const current = (get(profileDraft, path) as Record<string, unknown>[]) ?? [];
    setProfileDraft((draft) => setIn(draft, path, [...current, item]));
  };
  const remove = (path: Path, index: number) => {
    const current = (get(profileDraft, path) as Record<string, unknown>[]) ?? [];
    setProfileDraft((draft) => setIn(draft, path, current.filter((_, itemIndex) => itemIndex !== index)));
  };

  if (hydrated === false) return <div className="panel" role="status">Loading your saved applicant profile…</div>;
  return (
    <>
      <ProfileRecoveryPanel />
      {publicIntent && !savedProfile && <Notice><div className="stack stack--tight"><strong>Your search starts here: {publicIntent.subject}</strong><p className="small">{publicIntent.country || 'Worldwide'} · {publicIntent.budget === null ? 'Budget not decided' : `Up to USD ${publicIntent.budget.toLocaleString()} per year`}. Add these preferences to this draft, then complete your profile.</p><div className="row"><button className="btn btn--primary" onClick={() => { setProfileDraft(draft => { let next = setIn(draft, ['context', 'intended_fields'], [publicIntent.subject]); next = setIn(next, ['preferences', 'preferred_countries'], publicIntent.country ? [publicIntent.country] : []); if (publicIntent.budget !== null) { next = setIn(next, ['funding', 'max_annual_budget'], publicIntent.budget); next = setIn(next, ['funding', 'budget_currency'], 'USD'); } return next; }); clearPublicSearchIntent(); setPublicIntent(null); }}>Use these preferences</button><button className="btn btn--ghost" onClick={() => { clearPublicSearchIntent(); setPublicIntent(null); }}>Start blank</button></div></div></Notice>}
      <div className="screen__head">
        <p className="screen__eyebrow">CREATE YOUR PROFILE · {String(step).padStart(2, '0')} / 05</p>
        <h1 className="screen__title">{step === 1 ? <>Tell us about <span className="find-yellow">yourself.</span></> : ['','','Education & grades','Tests & scores','Activities & achievements','Review your profile'][step]}</h1>
        <p className="screen__lede">
          A few simple details help us find the right matches for you. Your information stays editable.
        </p>
      </div>

      <div className="profile-layout">
      <nav className="profile-steps" aria-label="Profile steps">
        {PROFILE_STEPS.map((name, index) => <button key={name} type="button" aria-current={step === index + 1 ? 'step' : undefined} onClick={() => setStep(index + 1)}><span>{index + 1}</span>{name}</button>)}
      </nav>

      <div className="stack stack--loose">
        {draftRestored && (
          <Notice kind="warn">
            <div className="stack stack--tight" data-testid="draft-restored">
              <div>
                <strong>Unsaved changes restored.</strong> This browser still had edits you had
                not saved. Your saved profile on the server is untouched until you press Save.
              </div>
              <div className="row">
                <button className="btn btn--sm" onClick={discardDraft} data-testid="discard-draft">
                  Discard these edits
                </button>
              </div>
            </div>
          </Notice>
        )}

        {restored && savedProfile && (
          <Notice kind="info">
            <div>
              Loaded <strong>{String(profileDraft.display_name)}</strong> from your saved profile.
              Edits here update that profile.
            </div>
          </Notice>
        )}

        <div className="profile-step-content" hidden={step !== 1}>
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
            <Field label="Applicant display name" htmlFor="applicant-name" hint="A label for your private applicant case. It is excluded from university search queries.">
              <input id="applicant-name" autoComplete="name" maxLength={120} {...bind(['display_name'])} />
            </Field>
            <Field label="Level" htmlFor="level">
              <select id="level" {...bind(['context', 'level'])}>
                <option value="foundation">Foundation</option>
                <option value="bachelor">Bachelor</option>
                <option value="master">Master</option>
                <option value="phd">PhD</option>
              </select>
            </Field>
            <Field label="Field of study" htmlFor="field" hint="Drives which programmes are searched.">
              <CommaSeparatedInput id="field" {...bindList(['context', 'intended_fields'])} />
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
            <Field label="Country of education" htmlFor="education-country">
              <input id="education-country" {...bind(['context', 'education_country'])} />
            </Field>
            <Field label="Additional nationality (if any)" htmlFor="second-citizenship" hint="Leave blank if none.">
              <input id="second-citizenship" {...bind(['context', 'second_citizenship'])} />
            </Field>
            <Field label="Education system" htmlFor="edsys">
              <input id="edsys" {...bind(['context', 'education_system'])} />
            </Field>
            <Field label="Curriculum type" htmlFor="curriculum-type">
              <select id="curriculum-type" {...bind(['context', 'curriculum_type'])}>
                {['national', 'ib', 'a_level', 'ap', 'us_high_school', 'other'].map((value) => (
                  <option key={value} value={value}>{value.replace('_', ' ')}</option>
                ))}
              </select>
            </Field>
            <Field label="Finishing school on" htmlFor="grad">
              <input id="grad" type="date" {...bind(['context', 'graduation_date'])} />
            </Field>
          </div>
        </Panel>
        </div>

        <div className="profile-step-content" hidden={step !== 2}>
        <Panel
          title="Read it off your transcript"
          hint="Optional. The file is read and discarded — it is never saved, and nothing is filled in until you say so."
        >
          <div className="stack stack--tight">
            <Field label="Transcript (PDF)" htmlFor="transcript-file">
              <input
                id="transcript-file"
                type="file"
                accept="application/pdf"
                data-testid="transcript-file"
                onChange={(e) => readTranscript(e.target.files?.[0])}
              />
            </Field>
            {transcriptBusy && <p className="xs muted">Reading…</p>}
            {transcriptNote && (
              <p className="xs muted" data-testid="transcript-note">{transcriptNote}</p>
            )}
            {suggestions.map((suggestion) => (
              <div key={suggestion.field} className="notice" data-testid={`suggestion-${suggestion.field}`}>
                <div style={{ flex: 1 }}>
                  <div className="small"><strong>{suggestion.label}:</strong> {describe(suggestion.value)}</div>
                  {/* The quote is the point: the applicant checks the number
                      against their own document instead of trusting ours. */}
                  <div className="xs faint">“{suggestion.excerpt}”</div>
                </div>
                <button
                  type="button"
                  className="btn btn--sm"
                  data-testid={`apply-${suggestion.field}`}
                  onClick={() => applySuggestion(suggestion, suggestionInput)}
                >
                  Use this
                </button>
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          title="Grades"
          hint="Enter the grade exactly as it appears on your transcript. Unimatch does not convert it silently."
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
            <Field label="Class size" htmlFor="class-size">
              <input id="class-size" type="number" {...bind(['academics', 'class_size'], 'number')} />
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
              {conversionError && (
                <Notice kind="risk">
                  <div data-testid="conversion-error">
                    <strong>The conversion was not applied.</strong> {conversionError} Your grade
                    is unchanged.
                  </div>
                </Notice>
              )}
            </div>
          )}
        </Panel>
        </div>

        <div className="profile-step-content" hidden={step !== 3}>
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
            <Field label="ACT English" htmlFor="act-en"><input id="act-en" type="number" {...bind(['academics', 'act', 'english'], 'number')} /></Field>
            <Field label="ACT Math" htmlFor="act-math"><input id="act-math" type="number" {...bind(['academics', 'act', 'math'], 'number')} /></Field>
            <Field label="ACT Reading" htmlFor="act-read"><input id="act-read" type="number" {...bind(['academics', 'act', 'reading'], 'number')} /></Field>
            <Field label="ACT Science" htmlFor="act-sci"><input id="act-sci" type="number" {...bind(['academics', 'act', 'science'], 'number')} /></Field>
            <Field label="TOEFL Reading" htmlFor="toefl-r"><input id="toefl-r" type="number" {...bind(['academics', 'toefl', 'reading'], 'number')} /></Field>
            <Field label="TOEFL Listening" htmlFor="toefl-l"><input id="toefl-l" type="number" {...bind(['academics', 'toefl', 'listening'], 'number')} /></Field>
            <Field label="TOEFL Speaking" htmlFor="toefl-s"><input id="toefl-s" type="number" {...bind(['academics', 'toefl', 'speaking'], 'number')} /></Field>
            <Field label="TOEFL Writing" htmlFor="toefl-w"><input id="toefl-w" type="number" {...bind(['academics', 'toefl', 'writing'], 'number')} /></Field>
            {(['sat', 'act', 'ielts', 'toefl'] as const).flatMap((test) => [
              <Field key={`${test}-taken`} label={`${test.toUpperCase()} test date`} htmlFor={`${test}-taken`}>
                <input id={`${test}-taken`} type="date" {...bind(['academics', test, 'dates', 'taken_on'])} />
              </Field>,
              <Field key={`${test}-retake`} label={`${test.toUpperCase()} planned retake`} htmlFor={`${test}-retake`}>
                <input id={`${test}-retake`} type="date" {...bind(['academics', test, 'dates', 'planned_retake_on'])} />
              </Field>,
            ])}
            <Field label="Duolingo English Test" htmlFor="duolingo-score">
              <input id="duolingo-score" type="number"
                value={String(get(profileDraft, ['academics', 'duolingo', 'score']) ?? '')}
                onChange={(event) => setProfileDraft((draft) => setIn(draft, ['academics', 'duolingo'], event.target.value === '' ? null : {
                  name: 'Duolingo English Test', score: Number.parseFloat(event.target.value),
                  max_score: get(profileDraft, ['academics', 'duolingo', 'max_score']) ?? 160,
                  dates: get(profileDraft, ['academics', 'duolingo', 'dates']) ?? { taken_on: null, planned_retake_on: null },
                }))} />
            </Field>
            <Field label="Duolingo maximum" htmlFor="duolingo-max">
              <input id="duolingo-max" type="number" {...bind(['academics', 'duolingo', 'max_score'], 'float')} />
            </Field>
            <Field label="Planned retakes" htmlFor="planned-retakes" hint="Comma-separated.">
              <CommaSeparatedInput id="planned-retakes" {...bindList(['academics', 'planned_retakes'])} />
            </Field>
          </div>
          <div className="stack stack--tight" style={{ marginTop: 'var(--space-4)' }}>
            {otherTests.map((_, index) => (
              <div className="grid-3 panel panel--sunken" key={`other-test-${index}`}>
                <Field label="Test name" htmlFor={`other-test-name-${index}`}><input id={`other-test-name-${index}`} {...bind(['academics', 'other_tests', index, 'name'])} /></Field>
                <Field label="Score" htmlFor={`other-test-score-${index}`}><input id={`other-test-score-${index}`} type="number" step="0.01" {...bind(['academics', 'other_tests', index, 'score'], 'float')} /></Field>
                <Field label="Maximum" htmlFor={`other-test-max-${index}`}><input id={`other-test-max-${index}`} type="number" step="0.01" {...bind(['academics', 'other_tests', index, 'max_score'], 'float')} /></Field>
                <Field label="Taken on" htmlFor={`other-test-date-${index}`}><input id={`other-test-date-${index}`} type="date" {...bind(['academics', 'other_tests', index, 'dates', 'taken_on'])} /></Field>
                <Field label="Planned retake" htmlFor={`other-test-retake-${index}`}><input id={`other-test-retake-${index}`} type="date" {...bind(['academics', 'other_tests', index, 'dates', 'planned_retake_on'])} /></Field>
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['academics', 'other_tests'], index)}>Remove</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['academics', 'other_tests'], {
              name: '', score: null, max_score: null, dates: { taken_on: null, planned_retake_on: null },
            })}>+ Add another test</button>
          </div>
        </Panel>
        </div>

        <div className="profile-step-content" hidden={step !== 2}>
        <Panel title="Subject grades" hint="Keep the original transcript scale for every subject.">
          <div className="stack stack--tight">
            {subjectGrades.map((_, index) => (
              <div className="panel panel--sunken" key={`subject-${index}`}>
                <div className="grid-3">
                  <Field label="Subject" htmlFor={`subject-${index}`}><input id={`subject-${index}`} {...bind(['academics', 'subject_grades', index, 'subject'])} /></Field>
                  <Field label="Grade" htmlFor={`subject-grade-${index}`}><input id={`subject-grade-${index}`} type="number" step="0.01" {...bind(['academics', 'subject_grades', index, 'grade', 'raw_value'], 'float')} /></Field>
                  <Field label="Scale maximum" htmlFor={`subject-max-${index}`}><input id={`subject-max-${index}`} type="number" step="0.01" {...bind(['academics', 'subject_grades', index, 'grade', 'raw_scale_max'], 'float')} /></Field>
                  <Field label="Scale label" htmlFor={`subject-scale-${index}`}><input id={`subject-scale-${index}`} {...bind(['academics', 'subject_grades', index, 'grade', 'raw_scale_label'])} /></Field>
                </div>
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['academics', 'subject_grades'], index)}>Remove</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['academics', 'subject_grades'], {
              subject: '', grade: { raw_value: null, raw_scale_max: null, raw_scale_label: '', status: 'applicant_confirmed' },
            })}>+ Add subject grade</button>
          </div>
        </Panel>

        <Panel title="AP, IB and A-Level results" hint="Add achieved and predicted curriculum results exactly as reported.">
          <div className="stack stack--tight">
            {curriculumResults.map((item, index) => (
              <div className="grid-3 panel panel--sunken" key={`curriculum-${index}`}>
                <Field label="Framework" htmlFor={`framework-${index}`}>
                  <select id={`framework-${index}`} {...bind(['academics', 'curriculum_results', index, 'framework'])}>
                    {['AP', 'IB', 'A-Level', 'AS-Level', 'other'].map((value) => <option key={value}>{value}</option>)}
                  </select>
                </Field>
                <Field label="Subject" htmlFor={`curriculum-subject-${index}`}><input id={`curriculum-subject-${index}`} {...bind(['academics', 'curriculum_results', index, 'subject'])} /></Field>
                <Field label="Result" htmlFor={`curriculum-result-${index}`}><input id={`curriculum-result-${index}`} {...bind(['academics', 'curriculum_results', index, 'result'])} /></Field>
                <Field label="Year" htmlFor={`curriculum-year-${index}`}><input id={`curriculum-year-${index}`} type="number" {...bind(['academics', 'curriculum_results', index, 'year'], 'number')} /></Field>
                <label className="row row--tight small"><input type="checkbox" checked={Boolean(item.predicted)} onChange={(event) => setProfileDraft((draft) => setIn(draft, ['academics', 'curriculum_results', index, 'predicted'], event.target.checked))} /> Predicted</label>
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['academics', 'curriculum_results'], index)}>Remove</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['academics', 'curriculum_results'], {
              framework: 'AP', subject: '', result: '', year: null, predicted: false,
            })}>+ Add curriculum result</button>
          </div>
        </Panel>
        </div>

        <div className="profile-step-content" hidden={step !== 4}>
        <Panel title="Extracurricular activities" hint="Depth, responsibility and measurable impact matter more than a long list.">
          <div className="stack stack--tight">
            {activities.map((_, index) => (
              <div className="panel panel--sunken" key={`activity-${index}`}>
                <div className="grid-3">
                  <Field label="Activity" htmlFor={`activity-${index}`}><input id={`activity-${index}`} {...bind(['activities', index, 'name'])} /></Field>
                  <Field label="Category" htmlFor={`activity-category-${index}`}><input id={`activity-category-${index}`} {...bind(['activities', index, 'category'])} /></Field>
                  <Field label="Role" htmlFor={`activity-role-${index}`}><input id={`activity-role-${index}`} {...bind(['activities', index, 'role'])} /></Field>
                  <Field label="Responsibility" htmlFor={`activity-level-${index}`}>
                    <select id={`activity-level-${index}`} {...bind(['activities', index, 'responsibility_level'])}>
                      {['participant', 'contributor', 'coordinator', 'leader', 'founder'].map((value) => <option key={value}>{value}</option>)}
                    </select>
                  </Field>
                  <Field label="Months" htmlFor={`activity-months-${index}`}><input id={`activity-months-${index}`} type="number" {...bind(['activities', index, 'duration_months'], 'number')} /></Field>
                  <Field label="Hours / week" htmlFor={`activity-hours-${index}`}><input id={`activity-hours-${index}`} type="number" step="0.5" {...bind(['activities', index, 'hours_per_week'], 'float')} /></Field>
                  <Field label="Weeks / year" htmlFor={`activity-weeks-${index}`}><input id={`activity-weeks-${index}`} type="number" {...bind(['activities', index, 'weeks_per_year'], 'number')} /></Field>
                  <Field label="Measurable outcome" htmlFor={`activity-outcome-${index}`}><textarea id={`activity-outcome-${index}`} {...bind(['activities', index, 'measurable_outcome'])} /></Field>
                  <Field label="Impact on others" htmlFor={`activity-impact-${index}`}><textarea id={`activity-impact-${index}`} {...bind(['activities', index, 'impact_on_others'])} /></Field>
                  <Field label="Evidence links" htmlFor={`activity-links-${index}`} hint="Comma-separated URLs.">
                    <CommaSeparatedInput id={`activity-links-${index}`} {...bindList(['activities', index, 'evidence_links'])} />
                  </Field>
                </div>
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['activities'], index)}>Remove activity</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['activities'], {
              name: '', category: '', role: '', duration_months: null, hours_per_week: null,
              weeks_per_year: null, responsibility_level: 'participant', measurable_outcome: null,
              impact_on_others: null, evidence_links: [],
            })}>+ Add activity</button>
          </div>
        </Panel>

        <Panel title="Achievements" hint="Include level, placement and how recipients were selected.">
          <div className="stack stack--tight">
            {achievements.map((_, index) => (
              <div className="grid-3 panel panel--sunken" key={`achievement-${index}`}>
                <Field label="Achievement" htmlFor={`achievement-${index}`}><input id={`achievement-${index}`} {...bind(['achievements', index, 'name'])} /></Field>
                <Field label="Level" htmlFor={`achievement-level-${index}`}>
                  <select id={`achievement-level-${index}`} {...bind(['achievements', index, 'level'])}>
                    {['school', 'city', 'regional', 'national', 'international'].map((value) => <option key={value}>{value}</option>)}
                  </select>
                </Field>
                <Field label="Year" htmlFor={`achievement-year-${index}`}><input id={`achievement-year-${index}`} type="number" {...bind(['achievements', index, 'year'], 'number')} /></Field>
                <Field label="Placement" htmlFor={`achievement-place-${index}`}><input id={`achievement-place-${index}`} {...bind(['achievements', index, 'placement'])} /></Field>
                <Field label="Selection criterion" htmlFor={`achievement-select-${index}`}><textarea id={`achievement-select-${index}`} {...bind(['achievements', index, 'selection_criterion'])} /></Field>
                <Field label="Evidence links" htmlFor={`achievement-links-${index}`} hint="Comma-separated URLs.">
                  <CommaSeparatedInput id={`achievement-links-${index}`} {...bindList(['achievements', index, 'evidence_links'])} />
                </Field>
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['achievements'], index)}>Remove</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['achievements'], {
              name: '', level: 'school', year: new Date().getFullYear(), placement: null,
              selection_criterion: null, evidence_links: [],
            })}>+ Add achievement</button>
          </div>
        </Panel>
        </div>

        <div className="profile-step-content" hidden={step !== 5}>
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
        {!validation && <Panel title="Ready to review"><p className="muted">Save your profile to check which information is blocking, recommended or optional.</p></Panel>}
        </div>

        <div className="profile-step-actions">
          {step > 1 && <button className="btn" type="button" onClick={() => setStep(step - 1)}>← Back</button>}
          <button
            className="btn"
            disabled={loading || saving}
            aria-busy={saving}
            data-testid="save-profile"
            onClick={() => { void commitProfile(); }}
          >
            {saving ? 'Saving…' : loading ? 'Please wait…' : 'Save profile'}
          </button>
          <SaveFeedback saving={(saving && !receiptConfirmsCurrentDraft) || profileRecovery?.dispatching === true} saved={(saved || receiptConfirmsCurrentDraft) && Boolean(savedProfile)} dirty={dirty} failed={saveFailed && !receiptConfirmsCurrentDraft}
            uncertain={Boolean(profileRecovery && !receiptConfirmsCurrentDraft && profileRecovery.entry && ['pending', 'unknown', 'accepted'].includes(profileRecovery.entry.status))} />
          <button className="btn btn--primary" onClick={() => step < PROFILE_STEPS.length ? setStep(step + 1) : onNext()} data-testid="to-preferences">
            {step < PROFILE_STEPS.length ? 'Continue →' : 'Continue to preferences →'}
          </button>
        </div>
      </div>
      </div>
    </>
  );
}

/**
 * Screen 01 — Applicant profile.
 *
 * The form's job is to make the *cost of each gap* visible. Every missing
 * field is listed with what it will do to the result, so the applicant can
 * decide which blanks are worth filling.
 */

import { useEffect, useRef, useState } from 'react';
import { ApiError, api } from '@/api/client';
import { Chip, Field, Notice, Panel } from '@/components/primitives';
import { castInput, get, setIn, type Path } from '@/lib/immutable';
import { useStore } from '@/lib/store';
import type { TranscriptSuggestion } from '@/types';
import { useTranslation } from '@/lib/useTranslation';
import { profileCopy, translateProfile, type ProfileCopyKey } from '@/lib/profileCopy';
import { profileWizardCopy } from '@/lib/profileWizardCopy';
import { profileValidationCopy } from '@/lib/profileValidationCopy';
import { ExamPicker } from '@/components/ExamPicker';
import { EvidenceLinksField } from '@/components/EvidenceLinksField';

/** "4.82 out of 5", not "[object Object]". */
function describe(value: unknown, separator: string): string {
  if (value && typeof value === 'object') {
    const gpa = value as { raw_value?: unknown; raw_scale_max?: unknown };
    if (gpa.raw_value != null && gpa.raw_scale_max != null) {
      return `${gpa.raw_value} ${separator} ${gpa.raw_scale_max}`;
    }
    return Object.values(value as Record<string, unknown>).filter(Boolean).join(', ');
  }
  return String(value ?? '');
}

const SEVERITY_LABEL = {
  blocking: 'Blocks research',
  high: 'Strong effect on results',
  medium: 'Noticeable effect',
  low: 'Minor effect',
} as const;

const EMPTY_EVIDENCE_LINKS: string[] = [];

export function ProfileScreen({ onNext }: { onNext: () => void }) {
  const { locale } = useTranslation();
  const copy = profileWizardCopy[locale];
  const tr = (key: ProfileCopyKey) => translateProfile(locale, key);
  const validationCopy = profileValidationCopy[locale];
  const {
    profileDraft, setProfileDraft, validation, validationStatus, retryValidation, saveProfile, loading,
    savedProfile, restored, loadDemoProfile, clearProfile, draftRestored, discardDraft,
    activeCaseKey, profileStep: step, setProfileStep: setStep,
  } = useStore();
  const [review, setReview] = useState<{ key: string | null; enabled: boolean } | null>(null);
  if (review !== null && review.key !== activeCaseKey) setReview(null);
  const showAll = review?.key === activeCaseKey && review.enabled;
  const setShowAll = (enabled: boolean) => setReview({ key: activeCaseKey, enabled });
  const sectionRef = useRef<HTMLDivElement>(null);
  const moveStep = (next: number) => {
    setStep(next);
    setShowAll(false);
    sectionRef.current?.focus();
  };
  const [saved, setSaved] = useState(false);
  const updateExam = (updater: (draft: Record<string, unknown>) => Record<string, unknown>) => {
    setProfileDraft(updater);
    setSaved(false);
  };
  const [confirmingReplace, setConfirmingReplace] = useState<'demo' | 'clear' | null>(null);
  const [methods, setMethods] = useState<
    { key: string; description: string; source: string; caveat: string; to_scale: string }[]
  >([]);

  const [conversionError, setConversionError] = useState<string | null>(null);

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

  const [suggestions, setSuggestions] = useState<TranscriptSuggestion[]>([]);
  const [transcriptNote, setTranscriptNote] = useState('');
  const [transcriptBusy, setTranscriptBusy] = useState(false);

  const readTranscript = async (file: File | undefined) => {
    if (!file) return;
    setTranscriptBusy(true);
    setSuggestions([]);
    try {
      const reading = await api.readTranscript(file);
      setSuggestions(reading.suggestions);
      setTranscriptNote(reading.note);
    } catch (e) {
      // The draft is not touched on failure, for the same reason the grade
      // conversion leaves it alone: a refused read must not cost the applicant
      // what they have already typed.
      setTranscriptNote(e instanceof ApiError ? e.message : tr('That file could not be read.'));
    } finally {
      setTranscriptBusy(false);
    }
  };

  /**
   * Apply one suggestion, field by field rather than wholesale.
   *
   * A transcript states a number and a scale; it does not know what the
   * applicant calls their grading system. Writing the whole object in would
   * blank the scale name they had already typed.
   */
  const applySuggestion = (suggestion: TranscriptSuggestion) => {
    const path = suggestion.field.split('.') as Path;
    setProfileDraft((d) => {
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
    const gpa = get(profileDraft, ['academics', 'gpa']) as Record<string, unknown>;
    setConversionError(null);
    try {
      const converted = await api.previewConversion(gpa, key);
      setProfileDraft((d) => setIn(d, ['academics', 'gpa'], converted));
    } catch (e) {
      setConversionError(e instanceof ApiError ? e.message : tr('The conversion could not be applied.'));
    }
  };

  const converted = get(profileDraft, ['academics', 'gpa', 'converted_value']);
  const subjectGrades = (get(profileDraft, ['academics', 'subject_grades']) as Record<string, unknown>[]) ?? [];
  const curriculumResults = (get(profileDraft, ['academics', 'curriculum_results']) as Record<string, unknown>[]) ?? [];
  const otherTests = (get(profileDraft, ['academics', 'other_tests']) as Record<string, unknown>[]) ?? [];
  const activities = (get(profileDraft, ['activities']) as Record<string, unknown>[]) ?? [];
  const achievements = (get(profileDraft, ['achievements']) as Record<string, unknown>[]) ?? [];
  const evidenceCopy = {
    label: tr('Evidence links'),
    hint: tr('Add up to five full HTTP or HTTPS URLs. Format is checked locally; links are not verified.'),
    rowLabel: tr('Evidence link'),
    add: tr('+ Add evidence link'),
    remove: tr('Remove link'),
    invalid: tr('Enter a full HTTP or HTTPS URL.'),
    limit: tr('Five link limit reached.'),
  };

  const append = (path: Path, item: Record<string, unknown>) => {
    const current = (get(profileDraft, path) as Record<string, unknown>[]) ?? [];
    setProfileDraft((draft) => setIn(draft, path, [...current, item]));
  };
  const remove = (path: Path, index: number) => {
    const current = (get(profileDraft, path) as Record<string, unknown>[]) ?? [];
    setProfileDraft((draft) => setIn(draft, path, current.filter((_, itemIndex) => itemIndex !== index)));
  };

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">{tr("Step 01")}</p>
        <h1 className="screen__title">{tr("Who is applying")}</h1>
        <p className="screen__lede">
          {tr('Nothing here is converted or inferred behind your back. Grades keep their original scale, and every blank below is listed with exactly what it costs you in the results.')}
        </p>
      </div>

      <nav className="profile-steps" aria-label={copy.navigation}>
        {copy.steps.map((name, index) => <button type="button" key={name}
          className="profile-steps__item" data-testid={`profile-step-${index}`}
          aria-current={!showAll && step === index ? 'step' : undefined}
          onClick={() => moveStep(index)}><span className="mono">0{index + 1}</span>{name}</button>)}
      </nav>
      <div className="profile-wizard-toolbar">
        <p className="small muted">{copy.hint}</p>
        <button type="button" className="btn btn--sm" data-testid="profile-show-all"
          aria-pressed={showAll} onClick={() => setShowAll(!showAll)}>{showAll ? copy.wizard : copy.all}</button>
      </div>
      <div className="stack stack--loose" ref={sectionRef} tabIndex={-1} aria-label={showAll ? copy.all : `${copy.step} ${step + 1}: ${copy.steps[step]}`}>
        {draftRestored && (
          <Notice kind="warn">
            <div className="stack stack--tight" data-testid="draft-restored">
              <div>
                <strong>{tr('Unsaved changes restored.')}</strong> {tr('This browser still had edits you had not saved. Your saved profile on the server is untouched until you press Save.')}
              </div>
              <div className="row">
                <button className="btn btn--sm" onClick={discardDraft} data-testid="discard-draft">
                  {tr("Discard these edits")}
                </button>
              </div>
            </div>
          </Notice>
        )}

        {restored && savedProfile && (
          <Notice kind="info">
            <div>
              {tr('Loaded saved profile:')} <strong>{String(profileDraft.display_name)}</strong> {tr('Edits here update that profile.')}
            </div>
          </Notice>
        )}

        <div hidden={!showAll && step !== 0}>
        <Panel
          title={tr("Start from")}
          hint={tr("Demo data is never loaded on your behalf. Choose it explicitly, and it is clearly labelled everywhere it appears.")}
        >
          <div className="row">
            <button
              className="btn btn--sm"
              data-testid="clear-profile"
              onClick={() => (savedProfile ? setConfirmingReplace('clear') : clearProfile())}
            >
              {tr("Blank profile")}
            </button>
            <button
              className="btn btn--sm"
              data-testid="load-demo-profile"
              onClick={() => (savedProfile ? setConfirmingReplace('demo') : loadDemoProfile())}
            >
              {tr("Load synthetic demo")}
            </button>
            {String(profileDraft.display_name).includes('synthetic') && (
              <Chip tone="demo">{tr("synthetic demo data")}</Chip>
            )}
          </div>
          {confirmingReplace && (
            <Notice kind="warn">
              <div style={{ flex: 1 }}>
                <strong>{tr('Replace the profile you have saved?')}</strong> {tr('The saved copy is not deleted, but your unsaved edits are lost.')}
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
                    {tr("Replace")}
                  </button>
                  <button className="btn btn--sm" onClick={() => setConfirmingReplace(null)}>
                    {tr("Keep editing")}
                  </button>
                </div>
              </div>
            </Notice>
          )}
        </Panel>
        </div>

        <div hidden={!showAll && step !== 0}>
        <Panel title={tr("Application context")} hint={tr("What you are applying for, and from where.")}>
          <div className="grid-2">
            <Field label={tr("Level")} htmlFor="level">
              <select id="level" {...bind(['context', 'level'])}>
                <option value="foundation">{tr("Foundation")}</option>
                <option value="bachelor">{tr("Bachelor")}</option>
                <option value="master">{tr("Master")}</option>
                <option value="phd">{tr("PhD")}</option>
              </select>
            </Field>
            <Field label={tr("Field of study")} htmlFor="field" hint={tr("Drives which programmes are searched.")}>
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
            <Field label={tr("Intake term")} htmlFor="term">
              <select id="term" {...bind(['context', 'intake_term'])}>
                <option value="fall">{tr("Fall")}</option>
                <option value="spring">{tr("Spring")}</option>
                <option value="summer">{tr("Summer")}</option>
                <option value="winter">{tr("Winter")}</option>
              </select>
            </Field>
            <Field label={tr("Intake year")} htmlFor="year">
              <input id="year" type="number" min={2024} max={2035} {...bind(['context', 'intake_year'], 'number')} />
            </Field>
            <Field label={tr("Citizenship")} htmlFor="citizenship"
                   hint={tr("Decides which scholarships you are eligible for at all.")}>
              <input id="citizenship" {...bind(['context', 'citizenship'])} />
            </Field>
            <Field label={tr("Country of residence")} htmlFor="residence">
              <input id="residence" {...bind(['context', 'country_of_residence'])} />
            </Field>
            <Field label={tr("Country of education")} htmlFor="education-country">
              <input id="education-country" {...bind(['context', 'education_country'])} />
            </Field>
            <Field label={tr("Additional nationality (if any)")} htmlFor="second-citizenship" hint={tr("Leave blank if none.")}>
              <input id="second-citizenship" {...bind(['context', 'second_citizenship'])} />
            </Field>
            <Field label={tr("Education system")} htmlFor="edsys">
              <input id="edsys" {...bind(['context', 'education_system'])} />
            </Field>
            <Field label={tr("Curriculum type")} htmlFor="curriculum-type">
              <select id="curriculum-type" {...bind(['context', 'curriculum_type'])}>
                {['national', 'ib', 'a_level', 'ap', 'us_high_school', 'other'].map((value) => (
                  <option key={value} value={value}>{tr(value as ProfileCopyKey)}</option>
                ))}
              </select>
            </Field>
            <Field label={tr("Finishing school on")} htmlFor="grad">
              <input id="grad" type="date" {...bind(['context', 'graduation_date'])} />
            </Field>
          </div>
        </Panel>
        </div>

        <div hidden={!showAll && step !== 1}>
        <Panel
          title={tr("Read it off your transcript")}
          hint={tr("Optional. The file is read and discarded — it is never saved, and nothing is filled in until you say so.")}
        >
          <div className="stack stack--tight">
            <Field label={tr("Transcript (PDF)")} htmlFor="transcript-file">
              <input
                id="transcript-file"
                type="file"
                accept="application/pdf"
                data-testid="transcript-file"
                onChange={(e) => readTranscript(e.target.files?.[0])}
              />
            </Field>
            {transcriptBusy && <p className="xs muted">{tr("Reading…")}</p>}
            {transcriptNote && (
              <p className="xs muted" data-testid="transcript-note">{transcriptNote}</p>
            )}
            {suggestions.map((suggestion) => (
              <div key={suggestion.field} className="notice" data-testid={`suggestion-${suggestion.field}`}>
                <div style={{ flex: 1 }}>
                  <div className="small"><strong>{suggestion.label}:</strong> {describe(suggestion.value, tr('out of'))}</div>
                  {/* The quote is the point: the applicant checks the number
                      against their own document instead of trusting ours. */}
                  <div className="xs faint">“{suggestion.excerpt}”</div>
                </div>
                <button
                  type="button"
                  className="btn btn--sm"
                  data-testid={`apply-${suggestion.field}`}
                  onClick={() => applySuggestion(suggestion)}
                >
                  {tr('Use this')}
                </button>
              </div>
            ))}
          </div>
        </Panel>
        </div>

        <div hidden={!showAll && step !== 1}>
        <Panel
          title={tr("Grades")}
          hint={tr("Enter the grade exactly as it appears on your transcript. ASHYQ Apply does not convert it silently.")}
        >
          <div className="grid-2">
            <Field label={tr("GPA / average")} htmlFor="gpa">
              <input id="gpa" type="number" step="0.01" {...bind(['academics', 'gpa', 'raw_value'], 'float')} />
            </Field>
            <Field label={tr("Maximum on your scale")} htmlFor="gpamax">
              <input id="gpamax" type="number" step="0.1" {...bind(['academics', 'gpa', 'raw_scale_max'], 'float')} />
            </Field>
            <Field label={tr("Scale name")} htmlFor="gpascale" hint={tr("e.g. 'KZ 5-point', 'US 4.0 unweighted'")}>
              <input id="gpascale" {...bind(['academics', 'gpa', 'raw_scale_label'])} />
            </Field>
            <Field label={tr("Class rank")} htmlFor="rank">
              <input id="rank" type="number" {...bind(['academics', 'class_rank'], 'number')} />
            </Field>
            <Field label={tr("Class size")} htmlFor="class-size">
              <input id="class-size" type="number" {...bind(['academics', 'class_size'], 'number')} />
            </Field>
          </div>

          {methods.length > 0 && (
            <div className="stack stack--tight" style={{ marginTop: 'var(--space-4)' }}>
              <p className="small muted" style={{ marginBottom: 'var(--space-0)' }}>
                {tr('Programmes that publish a different scale cannot be decided without a conversion. You can accept one — the method and its caveat are stored with the number.')}
              </p>
              {converted != null ? (
                <Notice kind="info">
                  <div>
                    <strong>{tr('Converted to')} {String(get(profileDraft, ['academics', 'gpa', 'converted_scale_label']))}: {String(converted)}</strong>
                    <div className="xs" style={{ marginTop: 'var(--space-1)' }}>
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
                      {tr('Convert to')} {m.to_scale}
                    </button>
                  ))}
                </div>
              )}
              {conversionError && (
                <Notice kind="risk">
                  <div data-testid="conversion-error">
                    <strong>{tr('The conversion was not applied.')}</strong> {conversionError} {tr('Your grade is unchanged.')}
                  </div>
                </Notice>
              )}
            </div>
          )}
        </Panel>
        </div>

        <div hidden={!showAll && step !== 2}>
          <ExamPicker key={`english-${savedProfile?.id ?? 'draft'}`} group="english" draft={profileDraft} update={updateExam} showAll={showAll} />
        </div>
        <div hidden={!showAll && step !== 3}>
          <ExamPicker key={`standard-${savedProfile?.id ?? 'draft'}`} group="standard" draft={profileDraft} update={updateExam} showAll={showAll} />
          <Panel title={tr("Other tests and planned retakes")} hint={tr("Optional. Keep achieved and planned results separate.")}>
          <div className="grid-3">
            <Field label={tr("Planned retakes")} htmlFor="planned-retakes" hint={tr("Comma-separated.")}>
              <input id="planned-retakes"
                value={((get(profileDraft, ['academics', 'planned_retakes']) as string[]) ?? []).join(', ')}
                onChange={(event) => setProfileDraft((draft) => setIn(draft, ['academics', 'planned_retakes'], event.target.value.split(',').map((value) => value.trim()).filter(Boolean)))} />
            </Field>
          </div>
          <div className="stack stack--tight" style={{ marginTop: 'var(--space-4)' }}>
            {otherTests.map((_, index) => (
              <div className="grid-3 panel panel--sunken" key={`other-test-${index}`}>
                <Field label={tr("Test name")} htmlFor={`other-test-name-${index}`}><input id={`other-test-name-${index}`} {...bind(['academics', 'other_tests', index, 'name'])} /></Field>
                <Field label={tr("Score")} htmlFor={`other-test-score-${index}`}><input id={`other-test-score-${index}`} type="number" step="0.01" {...bind(['academics', 'other_tests', index, 'score'], 'float')} /></Field>
                <Field label={tr("Maximum")} htmlFor={`other-test-max-${index}`}><input id={`other-test-max-${index}`} type="number" step="0.01" {...bind(['academics', 'other_tests', index, 'max_score'], 'float')} /></Field>
                <Field label={tr("Taken on")} htmlFor={`other-test-date-${index}`}><input id={`other-test-date-${index}`} type="date" {...bind(['academics', 'other_tests', index, 'dates', 'taken_on'])} /></Field>
                <Field label={tr("Planned retake")} htmlFor={`other-test-retake-${index}`}><input id={`other-test-retake-${index}`} type="date" {...bind(['academics', 'other_tests', index, 'dates', 'planned_retake_on'])} /></Field>
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['academics', 'other_tests'], index)}>{tr("Remove")}</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['academics', 'other_tests'], {
              name: '', score: null, max_score: null, dates: { taken_on: null, planned_retake_on: null },
            })}>{tr("+ Add another test")}</button>
          </div>
        </Panel>
        </div>

        <div hidden={!showAll && step !== 1}>
        <Panel title={tr("Subject grades")} hint={tr("Keep the original transcript scale for every subject.")}>
          <div className="stack stack--tight">
            {subjectGrades.map((_, index) => (
              <div className="panel panel--sunken" key={`subject-${index}`}>
                <div className="grid-3">
                  <Field label={tr("Subject")} htmlFor={`subject-${index}`}><input id={`subject-${index}`} {...bind(['academics', 'subject_grades', index, 'subject'])} /></Field>
                  <Field label={tr("Grade")} htmlFor={`subject-grade-${index}`}><input id={`subject-grade-${index}`} type="number" step="0.01" {...bind(['academics', 'subject_grades', index, 'grade', 'raw_value'], 'float')} /></Field>
                  <Field label={tr("Scale maximum")} htmlFor={`subject-max-${index}`}><input id={`subject-max-${index}`} type="number" step="0.01" {...bind(['academics', 'subject_grades', index, 'grade', 'raw_scale_max'], 'float')} /></Field>
                  <Field label={tr("Scale label")} htmlFor={`subject-scale-${index}`}><input id={`subject-scale-${index}`} {...bind(['academics', 'subject_grades', index, 'grade', 'raw_scale_label'])} /></Field>
                </div>
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['academics', 'subject_grades'], index)}>{tr("Remove")}</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['academics', 'subject_grades'], {
              subject: '', grade: { raw_value: null, raw_scale_max: null, raw_scale_label: '', status: 'applicant_confirmed' },
            })}>{tr("+ Add subject grade")}</button>
          </div>
        </Panel>
        </div>

        <div hidden={!showAll && step !== 3}>
        <Panel title={tr("AP, IB and A-Level results")} hint={tr("Add achieved and predicted curriculum results exactly as reported.")}>
          <div className="stack stack--tight">
            {curriculumResults.map((item, index) => (
              <div className="grid-3 panel panel--sunken" key={`curriculum-${index}`}>
                <Field label={tr("Framework")} htmlFor={`framework-${index}`}>
                  <select id={`framework-${index}`} {...bind(['academics', 'curriculum_results', index, 'framework'])}>
                    {['AP', 'IB', 'A-Level', 'AS-Level', 'other'].map((value) => <option key={value} value={value}>{value in profileCopy ? tr(value as ProfileCopyKey) : value}</option>)}
                  </select>
                </Field>
                <Field label={tr("Subject")} htmlFor={`curriculum-subject-${index}`}><input id={`curriculum-subject-${index}`} {...bind(['academics', 'curriculum_results', index, 'subject'])} /></Field>
                <Field label={tr("Result")} htmlFor={`curriculum-result-${index}`}><input id={`curriculum-result-${index}`} {...bind(['academics', 'curriculum_results', index, 'result'])} /></Field>
                <Field label={tr("Year")} htmlFor={`curriculum-year-${index}`}><input id={`curriculum-year-${index}`} type="number" {...bind(['academics', 'curriculum_results', index, 'year'], 'number')} /></Field>
                <label className="row row--tight small"><input type="checkbox" checked={Boolean(item.predicted)} onChange={(event) => setProfileDraft((draft) => setIn(draft, ['academics', 'curriculum_results', index, 'predicted'], event.target.checked))} /> {tr('Predicted')}</label>
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['academics', 'curriculum_results'], index)}>{tr("Remove")}</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['academics', 'curriculum_results'], {
              framework: 'AP', subject: '', result: '', year: null, predicted: false,
            })}>{tr("+ Add curriculum result")}</button>
          </div>
        </Panel>
        </div>

        <div hidden={!showAll && step !== 4}>
        <Panel title={tr("Extracurricular activities")} hint={tr("Depth, responsibility and measurable impact matter more than a long list.")}>
          <div className="stack stack--tight">
            {activities.map((_, index) => (
              <div className="panel panel--sunken" key={`activity-${index}`}>
                <div className="grid-3">
                  <Field label={tr("Activity")} htmlFor={`activity-${index}`}><input id={`activity-${index}`} {...bind(['activities', index, 'name'])} /></Field>
                  <Field label={tr("Category")} htmlFor={`activity-category-${index}`}><input id={`activity-category-${index}`} {...bind(['activities', index, 'category'])} /></Field>
                  <Field label={tr("Role")} htmlFor={`activity-role-${index}`}><input id={`activity-role-${index}`} {...bind(['activities', index, 'role'])} /></Field>
                  <Field label={tr("Responsibility")} htmlFor={`activity-level-${index}`}>
                    <select id={`activity-level-${index}`} {...bind(['activities', index, 'responsibility_level'])}>
                      {['participant', 'contributor', 'coordinator', 'leader', 'founder'].map((value) => <option key={value} value={value}>{value in profileCopy ? tr(value as ProfileCopyKey) : value}</option>)}
                    </select>
                  </Field>
                  <Field label={tr("Months")} htmlFor={`activity-months-${index}`}><input id={`activity-months-${index}`} type="number" {...bind(['activities', index, 'duration_months'], 'number')} /></Field>
                  <Field label={tr("Hours / week")} htmlFor={`activity-hours-${index}`}><input id={`activity-hours-${index}`} type="number" step="0.5" {...bind(['activities', index, 'hours_per_week'], 'float')} /></Field>
                  <Field label={tr("Weeks / year")} htmlFor={`activity-weeks-${index}`}><input id={`activity-weeks-${index}`} type="number" {...bind(['activities', index, 'weeks_per_year'], 'number')} /></Field>
                  <Field label={tr("Measurable outcome")} htmlFor={`activity-outcome-${index}`}><textarea id={`activity-outcome-${index}`} {...bind(['activities', index, 'measurable_outcome'])} /></Field>
                  <Field label={tr("Impact on others")} htmlFor={`activity-impact-${index}`}><textarea id={`activity-impact-${index}`} {...bind(['activities', index, 'impact_on_others'])} /></Field>
                  <EvidenceLinksField
                    idPrefix={`activity-${index}-evidence`}
                    scopeKey={`${activeCaseKey ?? 'local'}:activity:${index}`}
                    value={(get(profileDraft, ['activities', index, 'evidence_links']) as string[]) ?? EMPTY_EVIDENCE_LINKS}
                    onChange={(links) => {
                      setProfileDraft((draft) => setIn(draft, ['activities', index, 'evidence_links'], links));
                      setSaved(false);
                    }}
                    copy={evidenceCopy}
                  />
                </div>
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['activities'], index)}>{tr("Remove activity")}</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['activities'], {
              name: '', category: '', role: '', duration_months: null, hours_per_week: null,
              weeks_per_year: null, responsibility_level: 'participant', measurable_outcome: null,
              impact_on_others: null, evidence_links: [],
            })}>{tr("+ Add activity")}</button>
          </div>
        </Panel>
        </div>

        <div hidden={!showAll && step !== 5}>
        <Panel title={tr("Achievements")} hint={tr("Include level, placement and how recipients were selected.")}>
          <div className="stack stack--tight">
            {achievements.map((_, index) => (
              <div className="grid-3 panel panel--sunken" key={`achievement-${index}`}>
                <Field label={tr("Achievement")} htmlFor={`achievement-${index}`}><input id={`achievement-${index}`} {...bind(['achievements', index, 'name'])} /></Field>
                <Field label={tr("Level")} htmlFor={`achievement-level-${index}`}>
                  <select id={`achievement-level-${index}`} {...bind(['achievements', index, 'level'])}>
                    {['school', 'city', 'regional', 'national', 'international'].map((value) => <option key={value} value={value}>{tr(value === 'national' ? 'National level' : value as ProfileCopyKey)}</option>)}
                  </select>
                </Field>
                <Field label={tr("Year")} htmlFor={`achievement-year-${index}`}><input id={`achievement-year-${index}`} type="number" {...bind(['achievements', index, 'year'], 'number')} /></Field>
                <Field label={tr("Placement")} htmlFor={`achievement-place-${index}`}><input id={`achievement-place-${index}`} {...bind(['achievements', index, 'placement'])} /></Field>
                <Field label={tr("Selection criterion")} htmlFor={`achievement-select-${index}`}><textarea id={`achievement-select-${index}`} {...bind(['achievements', index, 'selection_criterion'])} /></Field>
                <EvidenceLinksField
                  idPrefix={`achievement-${index}-evidence`}
                  scopeKey={`${activeCaseKey ?? 'local'}:achievement:${index}`}
                  value={(get(profileDraft, ['achievements', index, 'evidence_links']) as string[]) ?? EMPTY_EVIDENCE_LINKS}
                  onChange={(links) => {
                    setProfileDraft((draft) => setIn(draft, ['achievements', index, 'evidence_links'], links));
                    setSaved(false);
                  }}
                  copy={evidenceCopy}
                />
                <button className="btn btn--sm btn--danger" type="button" onClick={() => remove(['achievements'], index)}>{tr("Remove")}</button>
              </div>
            ))}
            <button className="btn btn--sm" type="button" onClick={() => append(['achievements'], {
              name: '', level: 'school', year: new Date().getFullYear(), placement: null,
              selection_criterion: null, evidence_links: [],
            })}>{tr("+ Add achievement")}</button>
          </div>
        </Panel>
        </div>

        <div role="status" aria-live="polite" data-testid="profile-validation-status">
          <Notice kind={validationStatus === 'invalid' || (validation && !validation.can_proceed) ? 'risk' : validationStatus === 'error' ? 'warn' : 'info'}>
            {validationStatus === 'error' || validationStatus === 'invalid' ? validationCopy[validationStatus]
              : validation ? (validation.can_proceed ? validationCopy.eligible : `${validationCopy.blocked} ${validation.blocking_count}`)
                : validationCopy.pending}
            {validationStatus === 'error' && <button type="button" className="btn" onClick={retryValidation}>{validationCopy.retry}</button>}
          </Notice>
        </div>

        {validation && (
          <Panel
            title={tr("What is missing, and what it costs you")}
            hint={validation.summary}
          >
            {validation.gaps.length === 0 ? (
              <p className="muted small">{tr("No gaps found by the current server checks.")}</p>
            ) : (
              <div className="stack stack--tight" data-testid="gap-list">
                {validation.gaps.map((g) => (
                  <div key={g.field_path} className={`gap-item gap-item--${g.severity}`}>
                    <Chip tone={g.severity === 'blocking' ? 'risk' : g.severity === 'high' ? 'warn' : 'neutral'}>
                      {tr(SEVERITY_LABEL[g.severity])}
                    </Chip>
                    <div>
                      <div className="gap-item__path">{g.field_path}</div>
                      <p className="small" style={{ margin: 'var(--space-0-5) var(--space-0) var(--space-0)' }}>{g.impact}</p>
                      {g.suggested_action && (
                        <p className="xs muted" style={{ margin: 'var(--space-1) var(--space-0) var(--space-0)' }}>→ {g.suggested_action}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        )}

        <div className="row">
          {!showAll && <>
            <button type="button" className="btn" disabled={step === 0} onClick={() => moveStep(step - 1)}>{copy.back}</button>
            <span className="mono small">{copy.step} {step + 1} / {copy.steps.length}</span>
            {step < copy.steps.length - 1 && <button type="button" className="btn btn--primary" data-testid="profile-next-step" onClick={() => moveStep(step + 1)}>{copy.next} →</button>}
          </>}
          <button
            className="btn"
            disabled={loading}
            data-testid="save-profile"
            onClick={async () => {
              await saveProfile();
              setSaved(true);
            }}
          >
            {loading ? tr('Saving…') : tr('Save profile')}
          </button>
          {saved && <Chip tone="ok">{tr("Saved")}</Chip>}
          <button className={`btn${showAll || step === copy.steps.length - 1 ? ' btn--primary' : ''}`} onClick={onNext} data-testid="to-preferences">
            {tr('Next: preferences & budget →')}
          </button>
        </div>
      </div>
    </>
  );
}

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

  const worstGap = validation?.gaps[0];

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
        {/* The full gap panel is six screens down, after eighty fields. A
            student reads which blanks matter *after* deciding what to fill in,
            which is the wrong way round, so the count and the worst one are
            surfaced here with a jump to the detail. */}
        {worstGap && validation && (
          <Notice kind={validation.gaps.some((g) => g.severity === 'blocking') ? 'warn' : 'info'}>
            <div>
              <strong>
                {validation.gaps.length} {validation.gaps.length === 1 ? 'blank affects' : 'blanks affect'} your results.
              </strong>{' '}
              Most consequential: <em>{worstGap.field_path}</em> —{' '}
              {(SEVERITY_LABEL[worstGap.severity] ?? worstGap.severity).toLowerCase()}.{' '}
              <button
                type="button"
                className="btn btn--link"
                data-testid="jump-to-gaps"
                onClick={() => {
                  // Deliberately not smooth. Both scrollIntoView({behavior:
                  // 'smooth'}) and scrollTo({behavior:'smooth'}) are silently
                  // no-ops in some embedded browsers, which leaves the control
                  // doing nothing at all; an instant jump always works and is
                  // what a reduced-motion reader wants regardless.
                  const target = document.querySelector('[data-testid="gap-list"]');
                  if (!target) return;
                  window.scrollTo({
                    top: target.getBoundingClientRect().top + window.scrollY - 80,
                    behavior: 'auto',
                  });
                }}
              >
                See what each one costs
              </button>
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

        <Panel
          title="Grades"
          hint="Enter the grade exactly as it appears on your transcript. ASHYQ Apply does not convert it silently."
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
              <input id="planned-retakes"
                value={((get(profileDraft, ['academics', 'planned_retakes']) as string[]) ?? []).join(', ')}
                onChange={(event) => setProfileDraft((draft) => setIn(draft, ['academics', 'planned_retakes'], event.target.value.split(',').map((value) => value.trim()).filter(Boolean)))} />
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
                    <input id={`activity-links-${index}`}
                      value={((get(profileDraft, ['activities', index, 'evidence_links']) as string[]) ?? []).join(', ')}
                      onChange={(event) => setProfileDraft((draft) => setIn(draft, ['activities', index, 'evidence_links'], event.target.value.split(',').map((value) => value.trim()).filter(Boolean)))} />
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
                  <input id={`achievement-links-${index}`}
                    value={((get(profileDraft, ['achievements', index, 'evidence_links']) as string[]) ?? []).join(', ')}
                    onChange={(event) => setProfileDraft((draft) => setIn(draft, ['achievements', index, 'evidence_links'], event.target.value.split(',').map((value) => value.trim()).filter(Boolean)))} />
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

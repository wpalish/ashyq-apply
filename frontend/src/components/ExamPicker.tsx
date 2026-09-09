import { useId, useState } from 'react';
import { Field, Panel } from './primitives';
import { castInput, get, setIn, type Path } from '@/lib/immutable';
import { useTranslation } from '@/lib/useTranslation';
import type { Locale } from '@/lib/i18n';

type ExamId = 'ielts' | 'toefl' | 'duolingo' | 'sat' | 'act';
type ScoreField = { key: string; label: string; id: string };
const EXAMS: Record<ExamId, { name: string; fields: ScoreField[] }> = {
  ielts: { name: 'IELTS', fields: ['overall', 'listening', 'reading', 'writing', 'speaking'].map(key => ({ key, label: `IELTS ${key}`, id: `ielts-${key}` })) },
  toefl: { name: 'TOEFL', fields: [
    { key: 'total', label: 'TOEFL total', id: 'toefl' },
    ...['reading', 'listening', 'speaking', 'writing'].map(key => ({ key, label: `TOEFL ${key[0]!.toUpperCase()}${key.slice(1)}`, id: `toefl-${key[0]}` })),
  ] },
  duolingo: { name: 'Duolingo', fields: [{ key: 'score', label: 'Duolingo English Test', id: 'duolingo-score' }] },
  sat: { name: 'SAT', fields: [
    { key: 'total', label: 'SAT total', id: 'sat' }, { key: 'math', label: 'SAT Math', id: 'satm' },
    { key: 'reading_writing', label: 'SAT Reading & Writing', id: 'satr' },
  ] },
  act: { name: 'ACT', fields: [
    { key: 'composite', label: 'ACT composite', id: 'act' },
    ...[['english', 'en'], ['math', 'math'], ['reading', 'read'], ['science', 'sci']].map(([key, id]) => ({ key: key!, label: `ACT ${key![0]!.toUpperCase()}${key!.slice(1)}`, id: `act-${id}` })),
  ] },
};
const GROUPS: Record<'english' | 'standard', ExamId[]> = { english: ['ielts', 'toefl', 'duolingo'], standard: ['sat', 'act'] };
const COPY: Record<Locale, { english: string; standard: string; prompt: string; hint: string; retained: string; all: string; date: string; planned: string }> = {
  ru: { english: 'Английский язык', standard: 'Вступительные тесты', prompt: 'Какие экзамены вы хотите указать?', hint: 'Раскройте нужные блоки. Скрытие не удаляет баллы и не исключает их из подбора.', retained: 'Данные сохранены в профиле. Раскройте блок, чтобы изменить или очистить их.', all: 'Режим обзора: показаны все экзамены.', date: 'Дата сдачи', planned: 'Планируемая пересдача' },
  kk: { english: 'Ағылшын тілі', standard: 'Қабылдау тесттері', prompt: 'Қай емтихандарды көрсеткіңіз келеді?', hint: 'Қажетті блоктарды ашыңыз. Жасыру балдарды жоймайды және іріктеуден алып тастамайды.', retained: 'Деректер профильде қалды. Өзгерту немесе тазалау үшін блокты ашыңыз.', all: 'Шолу режимі: барлық емтихандар көрсетілген.', date: 'Тапсырған күні', planned: 'Жоспарланған қайта тапсыру' },
  en: { english: 'English language', standard: 'Standardised tests', prompt: 'Which exams would you like to enter?', hint: 'Open the blocks you need. Hiding never deletes scores or excludes them from matching.', retained: 'Data remains in your profile. Open the block to edit or clear it.', all: 'Review mode: all exams are shown.', date: 'test date', planned: 'planned retake' },
};
const DUOLINGO_COPY: Record<Locale, { incomplete: string; remove: string; confirm: string }> = {
  ru: { incomplete: 'Для сохранения Duolingo нужен балл. Даты остаются в черновике: введите балл или удалите результат целиком.', remove: 'Удалить результат Duolingo и даты', confirm: 'Удалить балл, шкалу и обе даты Duolingo из черновика? Скрытие блока сохраняет эти данные.' },
  kk: { incomplete: 'Duolingo сақтау үшін балл қажет. Күндер нобайда қалады: балл енгізіңіз немесе нәтижені толық жойыңыз.', remove: 'Duolingo нәтижесі мен күндерін жою', confirm: 'Duolingo балын, шкаласын және екі күнін нобайдан жою керек пе? Блокты жасыру деректерді сақтайды.' },
  en: { incomplete: 'Duolingo needs a score before saving. Dates remain in the draft: enter a score or remove the whole result.', remove: 'Remove Duolingo result and dates', confirm: 'Remove the Duolingo score, scale and both dates from this draft? Hiding the block keeps this data.' },
};

/** Default maxima, test type and provenance are not evidence of taking an exam. */
export function examHasData(draft: Record<string, unknown>, exam: ExamId): boolean {
  return EXAMS[exam].fields.some(({ key }) => {
    const value = get(draft, ['academics', exam, key]);
    return value !== null && value !== undefined && value !== '';
  }) || ['taken_on', 'planned_retake_on'].some(key => Boolean(get(draft, ['academics', exam, 'dates', key])));
}

export function ExamPicker({ group, draft, update, showAll = false }: {
  group: 'english' | 'standard'; draft: Record<string, unknown>;
  update: (updater: (draft: Record<string, unknown>) => Record<string, unknown>) => void;
  showAll?: boolean;
}) {
  const { locale } = useTranslation();
  const copy = COPY[locale];
  const duolingoCopy = DUOLINGO_COPY[locale];
  const id = useId();
  const incompleteDuolingo = Boolean(get(draft, ['academics', 'duolingo'])) && get(draft, ['academics', 'duolingo', 'score']) == null;
  const [choices, setChoices] = useState<Partial<Record<ExamId, boolean>>>({});
  const expanded = (exam: ExamId) => showAll || (choices[exam] ?? examHasData(draft, exam));
  const bind = (exam: ExamId, rest: Path, cast: 'string' | 'number' | 'float' = 'string') => ({
    value: String(get(draft, ['academics', exam, ...rest]) ?? ''),
    onChange: (event: { target: { value: string } }) => {
      // Clearing the last score must not collapse the block under keyboard focus.
      setChoices(current => ({ ...current, [exam]: true }));
      const value = rest[0] === 'dates' && event.target.value === '' ? null : castInput(event.target.value, cast);
      update(current => {
        const base = exam === 'duolingo' && !get(current, ['academics', exam])
          ? setIn(current, ['academics', exam], { name: 'Duolingo English Test', score: null, max_score: 160, dates: { taken_on: null, planned_retake_on: null } }) : current;
        return setIn(base, ['academics', exam, ...rest], value);
      });
    },
  });
  return <Panel title={copy[group]} hint={copy.hint}>
    <p className="small">{copy.prompt}</p>
    <div className="exam-picker" role="group" aria-label={copy.prompt}>
      {GROUPS[group].map(exam => <button type="button" className="btn" key={exam}
        data-testid={`exam-toggle-${exam}`} aria-expanded={expanded(exam)} aria-controls={`${id}-${exam}`}
        disabled={showAll} onClick={() => setChoices(current => ({ ...current, [exam]: !expanded(exam) }))}>
        <span aria-hidden="true">{expanded(exam) ? '−' : '+'}</span> {EXAMS[exam].name}
      </button>)}
    </div>
    {showAll && <p className="small muted">{copy.all}</p>}
    {GROUPS[group].map(exam => <div key={exam}>
      {!expanded(exam) && examHasData(draft, exam) && <p className="small muted" role="status">{EXAMS[exam].name}: {copy.retained}</p>}
      <fieldset className="exam-block" id={`${id}-${exam}`} hidden={!expanded(exam)}>
        <legend>{EXAMS[exam].name}</legend>
        <div className="grid-3">
          {EXAMS[exam].fields.map(field => <Field key={field.key} label={field.label} htmlFor={field.id}>
            <input id={field.id} data-testid={field.id} type="number" inputMode="decimal"
              aria-invalid={exam === 'duolingo' && incompleteDuolingo ? true : undefined}
              aria-describedby={exam === 'duolingo' && incompleteDuolingo ? `${id}-duolingo-error` : undefined}
              step={exam === 'ielts' ? '0.5' : exam === 'duolingo' ? 'any' : '1'}
              min={exam === 'ielts' ? 0 : undefined} max={exam === 'ielts' ? 9 : undefined}
              {...bind(exam, [field.key], exam === 'ielts' || exam === 'duolingo' ? 'float' : 'number')} />
          </Field>)}
          {exam === 'ielts' && <Field label="Test type" htmlFor="ielts-type">
            <select id="ielts-type" {...bind(exam, ['test_type'])}>
              <option value="academic">Academic</option><option value="general_training">General Training</option>
              <option value="ukvi_academic">UKVI Academic</option><option value="one_skill_retake">One Skill Retake</option>
            </select>
          </Field>}
          {exam === 'duolingo' && <Field label="Duolingo maximum" htmlFor="duolingo-max">
            <input id="duolingo-max" type="number" {...bind(exam, ['max_score'], 'float')} />
          </Field>}
          <Field label={`${EXAMS[exam].name} ${copy.date}`} htmlFor={`${exam}-taken`}>
            <input id={`${exam}-taken`} type="date" {...bind(exam, ['dates', 'taken_on'])} />
          </Field>
          <Field label={`${EXAMS[exam].name} ${copy.planned}`} htmlFor={`${exam}-retake`}>
            <input id={`${exam}-retake`} type="date" {...bind(exam, ['dates', 'planned_retake_on'])} />
          </Field>
        </div>
        {exam === 'duolingo' && Boolean(get(draft, ['academics', exam])) && <div className="stack stack--tight">
          {incompleteDuolingo && <div className="notice notice--warn" role="status" id={`${id}-duolingo-error`}>{duolingoCopy.incomplete}</div>}
          <button type="button" className="btn btn--sm" data-testid="remove-duolingo" onClick={() => {
            if (!window.confirm(duolingoCopy.confirm)) return;
            update(current => setIn(current, ['academics', 'duolingo'], null));
            setChoices(current => ({ ...current, duolingo: true }));
          }}>{duolingoCopy.remove}</button>
        </div>}
      </fieldset>
    </div>)}
  </Panel>;
}

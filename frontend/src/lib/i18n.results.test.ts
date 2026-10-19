/**
 * Gap B6: the results screens and the backend's sentences in en, ru and kk.
 *
 * Key coverage first — every results key answers in all three languages with
 * the same parameters — then the rule that makes backend keys safe: whatever
 * cannot be localised is shown in the English the server sent, never as a key,
 * a half-filled template or an invented sentence.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { EN_RESULTS, KK_RESULTS, RU_RESULTS, type ResultsKey } from './i18n.results';
import { setLocale, t, untranslated } from './i18n';
import { localStaleChip, localStaleReason, localize } from './messages';

const KEYS = Object.keys(EN_RESULTS) as ResultsKey[];
const placeholders = (text: string) => new Set(Array.from(text.matchAll(/\{(\w+)\}/g), (m) => m[1]));

afterEach(() => setLocale('en'));

describe('key coverage', () => {
  it('has every results key in English, Russian and Kazakh', () => {
    for (const [name, dictionary] of [['ru', RU_RESULTS], ['kk', KK_RESULTS]] as const) {
      const missing = KEYS.filter((key) => !dictionary[key]?.trim());
      expect(missing, `${name} is missing results keys`).toEqual([]);
      const extra = Object.keys(dictionary).filter((key) => !(key in EN_RESULTS));
      expect(extra, `${name} has keys English does not`).toEqual([]);
    }
  });

  it('leaves no results key falling back to English in either locale', () => {
    for (const locale of ['ru', 'kk'] as const) {
      expect(untranslated(locale).filter((key) => key in EN_RESULTS)).toEqual([]);
    }
  });

  it('gives every translation the same parameters as the English', () => {
    for (const key of KEYS) {
      const wanted = placeholders(EN_RESULTS[key]);
      expect(placeholders(RU_RESULTS[key]), `ru ${key}`).toEqual(wanted);
      expect(placeholders(KK_RESULTS[key]), `kk ${key}`).toEqual(wanted);
    }
  });

  it('does not pass English off as a translation', () => {
    // A sentence copied across unchanged looks translated to the coverage
    // check and reads as English to the applicant.
    for (const key of KEYS) {
      if (EN_RESULTS[key].length < 12) continue;
      expect(RU_RESULTS[key], `ru ${key}`).not.toBe(EN_RESULTS[key]);
      expect(KK_RESULTS[key], `kk ${key}`).not.toBe(EN_RESULTS[key]);
    }
  });

  it('never says probability or chance where Russian or Kazakh would not hedge it', () => {
    // I-rule: the fit is never a probability. The translations may *deny* it
    // (as the English does), but no other string may introduce the word.
    const denies = new Set(['results.fitDisclaimer', 'detail.assessmentNote', 'shortlist.rankedFootnote', 'compare.lede']);
    for (const key of KEYS) {
      if (denies.has(key)) continue;
      expect(RU_RESULTS[key], key).not.toMatch(/вероятност|шанс|%\s*поступ/i);
      expect(KK_RESULTS[key], key).not.toMatch(/ықтималд/i);
    }
  });

  it('answers in the chosen locale through t()', () => {
    setLocale('kk');
    expect(t('detail.tab.costs')).toBe('Шығындар');
    setLocale('ru');
    expect(t('detail.tab.costs')).toBe('Расходы');
    setLocale('en');
    expect(t('detail.tab.costs')).toBe('Costs');
  });
});

describe('a sentence the backend wrote', () => {
  const english = 'No verified data yet for Example University: the bachelor\'s in Computer Science.';
  const ref = { key: 'question.noVerifiedDataInScope', params: { university: 'Example University' } };

  it('is localised from its key and parameters', () => {
    setLocale('ru');
    expect(localize(ref, english)).toBe(
      'Проверенных данных по Example University пока нет: бакалавриат по Computer Science.',
    );
    setLocale('kk');
    expect(localize(ref, english)).toContain('Example University бойынша');
  });

  it('stays the served English for an English reader, even if the template drifted', () => {
    expect(localize(ref, 'Reworded by the server.')).toBe('Reworded by the server.');
  });

  it('stays English with no key, an unknown key, or a missing parameter', () => {
    setLocale('ru');
    expect(localize(null, english)).toBe(english);
    expect(localize({ key: 'question.nothingLikeThis', params: {} }, english)).toBe(english);
    expect(localize({ key: 'question.noVerifiedDataInScope', params: {} }, english)).toBe(english);
  });

  it('translates cost categories inside a parameter', () => {
    setLocale('ru');
    const out = localize(
      { key: 'gap.notItemised', params: { categories: 'housing, meals' } },
      'The cost table does not itemise housing, meals; …',
    );
    expect(out).toContain('жильё, питание');
  });

  it('localises stale reasons inside a sentence only when it knows every one', () => {
    setLocale('kk');
    const known = {
      key: 'why.awardStale',
      params: { reasons: 'deadline 2026-01-15 has passed' },
      parts: { reasons: [{ key: 'stale.deadlinePassed', params: { date: '2026-01-15' } }] },
    };
    expect(localize(known, 'x')).toContain('2026-01-15 мерзімі өтіп кетті');
    const partly = { ...known, parts: { reasons: [null] } };
    expect(localize(partly, 'x')).toContain('(deadline 2026-01-15 has passed)');
  });
});

describe('why a claim is stale', () => {
  const claim = {
    notes: 'Verified knowledge base. Stale, not current: deadline 2026-01-15 has passed; something new.',
    stale_messages: [{ key: 'stale.deadlinePassed', params: { date: '2026-01-15' } }, null],
  };

  it('localises each reason it has a key for and keeps the rest in English', () => {
    setLocale('ru');
    expect(localStaleReason(claim)).toBe('срок 2026-01-15 уже прошёл; something new');
  });

  it('is the backend English for an English reader', () => {
    expect(localStaleReason(claim)).toBe('deadline 2026-01-15 has passed; something new');
  });

  it('labels the age chip in the reader\'s language', () => {
    expect(localStaleChip(12)).toBe('12d old');
    setLocale('kk');
    expect(localStaleChip(12)).toBe('12 күн бұрын');
    expect(localStaleChip(0)).toBe('өзекті емес');
  });
});

/**
 * The i18n groundwork, and the rule that keeps it honest.
 *
 * An untranslated string here is not a bug: the product's own vocabulary —
 * claim, shortlist, funding gap — needs a person who knows the admissions
 * words in Russian and Kazakh, and a machine translation would be
 * indistinguishable from a reviewed one to the applicant acting on it.
 *
 * These tests hold the mechanism to that: English always answers, a locale may
 * be incomplete, and the gaps stay in step with `docs/i18n/GLOSSARY.md`.
 */

import { beforeEach, describe, expect, it } from 'vitest';
import { getLocale, setLocale, subscribe, t, untranslated, LOCALES } from './i18n';

beforeEach(() => {
  window.localStorage.clear();
  setLocale('en');
});

describe('looking a message up', () => {
  it('answers in the chosen locale', () => {
    setLocale('ru');
    expect(t('nav.profile')).toBe('Профиль абитуриента');
    setLocale('kk');
    expect(t('nav.profile')).toBe('Талапкер профилі');
  });

  it('falls back to English rather than showing a key or an invented word', () => {
    // Any key Kazakh does not have yet: English is the correct answer until a
    // person chooses the Kazakh words.
    const gap = untranslated('kk')[0];
    if (gap === undefined) throw new Error('Kazakh has no gap left to fall back on');
    const english = t(gap);
    setLocale('kk');
    expect(t(gap)).toBe(english);
  });

  it('never renders a raw key', () => {
    for (const { id } of LOCALES) {
      setLocale(id);
      for (const key of untranslated('ru')) {
        expect(t(key)).not.toBe(key);
        expect(t(key).trim()).not.toBe('');
      }
    }
  });
});

describe('choosing a language', () => {
  it('remembers the choice and tells the page what it is', () => {
    setLocale('kk');
    expect(window.localStorage.getItem('ashyq.locale')).toBe('kk');
    expect(document.documentElement.lang).toBe('kk');
    expect(getLocale()).toBe('kk');
  });

  it('notifies subscribers, so a screen re-renders when it changes', () => {
    let calls = 0;
    const stop = subscribe(() => { calls += 1; });
    setLocale('ru');
    setLocale('en');
    stop();
    setLocale('kk');
    expect(calls).toBe(2);
  });
});

describe('the gaps are deliberate', () => {
  it('names every screen in the navigation with the provisional glossary words', () => {
    // Navigation used to keep these in English (GLOSSARY.md, Open). Since
    // 2026-10-25 it carries the provisional words the results screens already
    // use ("Provisional — navigation"), so a menu is never half in English.
    const words = {
      ru: { 'nav.shortlist': 'короткий список', 'nav.sources': 'расхождения', 'nav.group.research': 'Исследование' },
      kk: { 'nav.shortlist': 'қысқа тізім', 'nav.sources': 'сәйкессіздік', 'nav.group.research': 'Зерттеу' },
    } as const;
    const nav = ['nav.preferences', 'nav.shortlist', 'nav.funding', 'nav.sources', 'nav.export', 'nav.group.research'] as const;
    for (const locale of ['ru', 'kk'] as const) {
      const gaps = untranslated(locale);
      for (const key of nav) expect(gaps, `${locale} ${key}`).not.toContain(key);
      setLocale(locale);
      for (const [key, word] of Object.entries(words[locale])) {
        expect(t(key as keyof typeof words.ru).toLowerCase()).toContain(word.toLowerCase());
      }
    }
  });

  it('leaves nothing in the community untranslated', () => {
    // The community says post, answer, city, major — ordinary words, none of
    // them in the glossary. There is no excuse for a gap here, and a screen
    // half in English is the one a Kazakh school leaver actually reads most.
    for (const locale of ['ru', 'kk'] as const) {
      const gaps = untranslated(locale).filter(
        (key) => key.startsWith('community.')
          || key.startsWith('discover.')
          || key.startsWith('person.')
          || key.startsWith('leave.'),
      );
      expect(gaps, `${locale} is missing community strings`).toEqual([]);
    }
  });

  it('translates the ordinary interface words in both locales', () => {
    for (const locale of ['ru', 'kk'] as const) {
      const gaps = untranslated(locale);
      for (const key of ['appearance.light', 'appearance.dark', 'topbar.signOut', 'language.label']) {
        expect(gaps).not.toContain(key);
      }
    }
  });
});

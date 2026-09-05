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
    setLocale('kk');
    // "University shortlist" holds a glossary term with no settled Kazakh
    // equivalent. English is the correct answer until a person chooses one.
    expect(t('nav.shortlist')).toBe('University shortlist');
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
  it('leaves the product vocabulary untranslated in both locales', () => {
    // Each of these strings contains a term listed as Open in the glossary.
    const reserved = ['nav.shortlist', 'nav.funding', 'nav.sources', 'nav.export', 'nav.preferences'];
    for (const locale of ['ru', 'kk'] as const) {
      const gaps = untranslated(locale);
      for (const key of reserved) {
        expect(gaps).toContain(key);
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

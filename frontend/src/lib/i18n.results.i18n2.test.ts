/**
 * I18N-2: the results screens' remaining backend sentences — requirement
 * checks, award classifications, the ranking, conflicts and the exchange-rate
 * warning — in en, ru and kk, with the same safe fallback as gap B6: whatever
 * cannot be said whole in the reader's language is the served English.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { setLocale } from './i18n';
import { localRequirement, localize, localizeAll } from './messages';
import type { MessageRef } from '@/types';

afterEach(() => setLocale('en'));

const label = (key: string, params: Record<string, string> = {}): MessageRef => ({ key, params });

describe('a requirement check', () => {
  const english = 'No official minimum for Minimum GPA was found; not treated as a barrier.';
  const ref: MessageRef = {
    key: 'explain.noMinimum',
    params: { label: 'Minimum GPA' },
    parts: { label: [label('req.minGpa')] },
  };

  it('is the served English in English', () => {
    expect(localize(ref, english)).toBe(english);
  });

  it('names the requirement in the reader\'s language inside the sentence', () => {
    setLocale('ru');
    expect(localize(ref, english)).toBe(
      'Официальный минимум для «Минимальный GPA» не найден; это не считается препятствием.',
    );
    setLocale('kk');
    expect(localize(ref, english)).toBe(
      '«Ең төменгі GPA» үшін ресми ең төменгі шек табылмады; бұл кедергі деп есептелмейді.',
    );
  });

  it('keeps an unkeyed requirement label as served, inside a translated sentence', () => {
    setLocale('ru');
    const unknown = { ...ref, params: { label: 'Some new test' }, parts: { label: [null] } };
    expect(localize(unknown, 'x')).toContain('«Some new test»');
  });

  it('says a hard filter by the key its check carries', () => {
    const checks = [{ requirement: 'IELTS overall', requirement_message: label('req.ieltsOverall') }];
    expect(localRequirement('IELTS overall', checks)).toBe('IELTS overall');
    setLocale('kk');
    expect(localRequirement('IELTS overall', checks)).toBe('IELTS, жалпы балл');
    expect(localRequirement('Not on any check', checks)).toBe('Not on any check');
  });
});

describe('an award classification, sentence by sentence', () => {
  const english =
    'Tuition is confirmed as covered, but housing is not covered — this is full tuition, not a full ride. ' +
    'The profile states that a tuition-only award would not be taken up.';
  const refs: MessageRef[] = [
    {
      key: 'class.fullTuition',
      params: { missing: 'housing is not covered' },
      parts: { missing: [label('missing.notCovered', { category: 'housing' })] },
    },
    label('class.noTuitionOnly'),
  ];

  it('is the served English in English', () => {
    expect(localizeAll(refs, english)).toBe(english);
  });

  it('is said whole in Russian and Kazakh, cost categories included', () => {
    setLocale('ru');
    const ru = localizeAll(refs, english);
    expect(ru).toContain('жильё не покрывается');
    expect(ru).toContain('стипендию только на обучение вы не примете');
    setLocale('kk');
    expect(localizeAll(refs, english)).toContain('тұрғын үй өтелмейді');
  });

  it('stays English, whole, when one sentence has no translation', () => {
    setLocale('ru');
    expect(localizeAll([...refs, label('class.nothingLikeThis')], english)).toBe(english);
    expect(localizeAll(null, english)).toBe(english);
  });

  it('says the classification with the chip\'s own label', () => {
    setLocale('ru');
    const ref = label('class.onlyFullRide', { classification: 'FULL_TUITION' });
    expect(localize(ref, 'x')).toContain('«Обучение полностью»');
  });
});

describe('the ranking', () => {
  it('names an axis with the axis label the screen uses', () => {
    setLocale('ru');
    expect(localize(label('rank.noPreference', { axis: 'university size' }), 'x')).toBe(
      'Предпочтение по параметру «Размер университета» не указано.',
    );
    setLocale('kk');
    expect(localize(label('rank.attributeUnknown', { axis: 'climate' }), 'x')).toBe(
      'Бұл университеттің «Климат» көрсеткіші белгісіз.',
    );
  });

  it('says a knock-out with its requirement and its explanation, both keyed', () => {
    const english = 'Minimum GPA: Published minimum 3.5; applicant 3. The published minimum is not met.';
    const ref: MessageRef = {
      key: 'rank.knockout',
      params: { requirement: 'Minimum GPA', explanation: 'Published minimum 3.5; applicant 3. The published minimum is not met.' },
      parts: {
        requirement: [label('req.minGpa')],
        explanation: [label('explain.minimumNotMet', { published: '3.5', applicant: '3' })],
      },
    };
    expect(localize(ref, english)).toBe(english);
    setLocale('ru');
    expect(localize(ref, english)).toBe(
      'Минимальный GPA — Опубликованный минимум 3.5; у вас 3. Опубликованный минимум не достигнут.',
    );
  });

  it('keeps the remaining cost figures as the backend wrote them', () => {
    setLocale('kk');
    const ref = label('rank.withinCeiling', { gap: '5,000', ceiling: '10,000' });
    expect(localize(ref, 'x')).toBe('Жылына 5,000 қалдық көрсетілген 10,000 шегіне сыяды.');
  });
});

describe('a conflict', () => {
  const subject: MessageRef = {
    key: 'conflict.subjectProgramme',
    params: { what: 'the tuition fee', programme: 'Computer Science' },
    parts: { what: [label('conflict.label.tuition')] },
  };

  it('names what the sources disagree on, and keeps the programme as published', () => {
    expect(localize(subject, 'the tuition fee (Computer Science)')).toBe('the tuition fee (Computer Science)');
    setLocale('ru');
    expect(localize(subject, 'x')).toBe('плата за обучение — программа Computer Science');
    setLocale('kk');
    expect(localize(subject, 'x')).toBe('оқу ақысы — Computer Science бағдарламасы');
  });

  it('says why it is a question, with the subject inside', () => {
    setLocale('ru');
    const why: MessageRef = {
      key: 'conflict.why',
      params: { subject: 'the tuition fee (Computer Science)', values: '[2530, 2600]' },
      parts: { subject: [subject] },
    };
    expect(localize(why, 'x')).toBe(
      'Официальные источники расходятся в вопросе «плата за обучение — программа Computer Science»: [2530, 2600]',
    );
  });
});

describe('the exchange-rate warning', () => {
  it('is said with its date and age', () => {
    setLocale('kk');
    const ref = label('currency.staleRates', { date: '2026-01-01', days: '292' });
    expect(localize(ref, 'x')).toContain('2026-01-01 күнгі валюта бағамдарын');
  });
});

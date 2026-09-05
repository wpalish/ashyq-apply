/**
 * Formatting must never turn an absence into a number.
 *
 * A blank cell where a cost should be reads as "nothing to pay". These tests
 * pin the phrases that prevent that.
 */

import { describe, expect, it } from 'vitest';
import {
  DISPLAY_LOCALE,
  NOT_FOUND,
  STATUS_LABEL,
  STATUS_MEANING,
  admissionsFitTone,
  claimStatusTone,
  date,
  dateTime,
  eligibilityTone,
  fundingClassTone,
  fundingFitTone,
  humanize,
  isDemoSource,
  money,
  scorePercent,
  sourceLabel,
} from './format';
import type { Money } from '@/types';

const usd = (amount: number, extra: Partial<Money> = {}): Money => ({
  amount,
  currency: 'USD',
  academic_year: '2026/27',
  is_estimate: false,
  range_low: null,
  range_high: null,
  ...extra,
});

describe('money', () => {
  it('shows the amount, the currency and the academic year', () => {
    expect(money(usd(42500))).toBe('42,500 USD · 2026/27');
  });

  it('says "not found" rather than rendering nothing', () => {
    expect(money(null)).toBe(NOT_FOUND);
    expect(money(undefined)).toBe(NOT_FOUND);
  });

  it('never renders an absent value as zero', () => {
    expect(money(null)).not.toContain('0');
  });

  it('renders a genuine zero as zero', () => {
    expect(money(usd(0))).toBe('0 USD · 2026/27');
  });

  it('shows a range when the cost is published as one', () => {
    expect(money(usd(10000, { range_low: 9000, range_high: 11000 })))
      .toBe('10,000 USD (9,000–11,000) · 2026/27');
  });

  it('marks an estimate as an estimate', () => {
    expect(money(usd(10000, { is_estimate: true }))).toContain('est.');
  });

  it('omits the year when none was published', () => {
    expect(money(usd(10000, { academic_year: null }))).toBe('10,000 USD');
  });
});

describe('dates', () => {
  it('formats an ISO date readably, in the reader own locale', () => {
    // Money and dates now share DISPLAY_LOCALE. Asserting the literal string
    // would pin the test to whichever locale the runner happens to have, so
    // this asserts the parts that must be there in any of them.
    const formatted = date('2027-01-15');
    expect(formatted).toContain('2027');
    expect(formatted).toMatch(/15/);
    expect(formatted).toBe(
      new Date('2027-01-15').toLocaleDateString(DISPLAY_LOCALE, {
        day: '2-digit', month: 'short', year: 'numeric',
      }),
    );
  });

  it('uses one locale for money and dates alike', () => {
    // The defect: money was en-US and dates en-GB, so the same screen mixed
    // two conventions the reader never chose.
    expect(money(usd(1234567))).toContain((1234567).toLocaleString(DISPLAY_LOCALE));
  });

  it('reports a missing date rather than showing a dash', () => {
    expect(date(null)).toBe(NOT_FOUND);
    expect(dateTime(null)).toBe('never');
  });

  it('passes through anything it cannot parse instead of inventing one', () => {
    expect(date('rolling')).toBe('rolling');
  });
});

describe('humanize', () => {
  it('turns a screaming-snake status into a sentence', () => {
    expect(humanize('FULL_RIDE_CONFIRMED')).toBe('Full ride confirmed');
    expect(humanize('needs_official_clarification')).toBe('Needs official clarification');
  });
});

describe('status vocabulary', () => {
  it('gives every eligibility status a tone', () => {
    for (const status of ['MET', 'PENDING', 'GAP', 'NOT_APPLICABLE', 'NEEDS_OFFICIAL_CLARIFICATION'] as const) {
      expect(eligibilityTone[status]).toBeTruthy();
    }
  });

  it('maps the four funding classifications a user acts on to distinct tones', () => {
    expect(fundingClassTone.FULL_RIDE_CONFIRMED).toBe('ok');
    expect(fundingClassTone.NOT_ELIGIBLE).toBe('risk');
    expect(fundingClassTone.UNKNOWN).toBe('neutral');
  });

  it('never gives an unknown state a positive tone', () => {
    expect(fundingFitTone.UNKNOWN).toBe('neutral');
    expect(admissionsFitTone.INSUFFICIENT_DATA).toBe('neutral');
    expect(claimStatusTone.UNVERIFIED).toBe('neutral');
  });

  it('explains every status it shortens', () => {
    for (const key of Object.keys(STATUS_LABEL)) {
      expect(STATUS_MEANING[key], `${key} is shortened but never explained`).toBeTruthy();
    }
  });

  it('keeps each shortened label meaningfully shorter than the full phrase', () => {
    for (const [key, label] of Object.entries(STATUS_LABEL)) {
      expect(label.length).toBeLessThan(humanize(key).length);
    }
  });
});

describe('scorePercent', () => {
  it('scales the total against the achievable maximum', () => {
    expect(scorePercent(4, 8)).toBe(50);
  });

  it('does not divide by zero', () => {
    expect(scorePercent(0, 0)).toBe(0);
  });
});

describe('source labelling', () => {
  it('recognises bundled demo pages', () => {
    expect(isDemoSource(['fixture://u/page.html'])).toBe(true);
    expect(isDemoSource(['https://rug.nl/x'])).toBe(false);
  });

  it('marks a fixture URL as a bundled page rather than a link', () => {
    expect(sourceLabel('fixture://u/page.html')).toContain('bundled demo page');
  });

  it('shortens a real URL to host and path', () => {
    expect(sourceLabel('https://www.rug.nl/education/bachelor?x=1'))
      .toBe('www.rug.nl/education/bachelor');
  });
});

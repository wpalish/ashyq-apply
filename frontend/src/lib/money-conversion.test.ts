import { describe, expect, it } from 'vitest';
import { conversionNote, money } from '@/lib/format';
import type { Money } from '@/types';

const eur: Money = {
  amount: 2530, currency: 'EUR', academic_year: '2026/27',
  is_estimate: false, range_low: null, range_high: null,
};

const converted: Money = {
  ...eur, amount: 2734, currency: 'USD',
  original_amount: 2530, original_currency: 'EUR',
  rate: 1.0806, rate_date: '2026-08-28',
  rate_source: 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml',
};

describe('converted amounts say so', () => {
  it('leaves an unconverted amount without a conversion note', () => {
    expect(conversionNote(eur)).toBeNull();
  });

  /**
   * A student comparing a Dutch fee with a Canadian one sees two numbers in
   * their own currency. Without this, nothing on screen says one of them is
   * the product's arithmetic rather than a figure the university published.
   */
  it('names the original amount, the rate, its date and its source', () => {
    const note = conversionNote(converted);
    expect(note).toContain('2,530 EUR');
    expect(note).toContain('1.0806');
    expect(note).toContain('2026-08-28');
    expect(note).toContain('ecb.europa.eu');
  });

  it('marks the formatted amount as converted', () => {
    expect(money(converted)).toContain('converted');
    expect(money(eur)).not.toContain('converted');
  });
});

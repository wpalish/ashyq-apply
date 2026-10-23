import { afterEach, expect, it, vi } from 'vitest';
import { date, dateTime, localDate, sourceDatePosition } from './format';
afterEach(() => { vi.restoreAllMocks(); });
it.each(['America/New_York', 'Asia/Almaty', 'UTC'])('keeps calendar date under an Intl default zone of %s', zone => {
  const NativeFormatter = Intl.DateTimeFormat;
  vi.spyOn(Intl, 'DateTimeFormat').mockImplementation(function (locales, options) { return new NativeFormatter(locales, { timeZone: zone, ...options }); });
  expect(localDate('2027-01-15', 'en-GB')).toBe('15 Jan 2027'); expect(date('2027-01-15')).toMatch(/15/);
});
it('compares known zones across midnight without using the current UTC day', () => {
  const midnight = new Date('2026-10-14T00:30:00Z');
  expect(sourceDatePosition('2026-10-13', 'America/New_York', midnight)).toBe('same');
  expect(sourceDatePosition('2026-10-13', 'Asia/Almaty', midnight)).toBe('earlier');
  expect(sourceDatePosition('2026-10-14', 'UTC', midnight)).toBe('same');
});
it('keeps unknown zones and missing dates explicitly incomparable', () => {
  const now = new Date('2026-10-14T00:30:00Z');
  expect(sourceDatePosition('2020-01-01', null, now)).toBe('unknown');
  expect(sourceDatePosition('2026-10-13', 'Not/AZone', now)).toBe('unknown'); expect(sourceDatePosition(null, 'UTC', now)).toBe('unknown');
});
it('formats an actual Instant across New York DST and does not invent time for LocalDate', () => {
  const early = dateTime('2026-11-01T05:30:00Z', 'America/New_York'); const late = dateTime('2026-11-01T06:30:00Z', 'America/New_York');
  expect(early).toBe(late); expect(dateTime('2026-11-01')).toBe('2026-11-01');
});
it('never normalizes an invalid leap date into a different calendar day', () => {
  expect(localDate('2027-02-29', 'en-GB')).toBe('2027-02-29'); expect(localDate('2028-02-29', 'en-GB')).toBe('29 Feb 2028');
});

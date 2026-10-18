import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearPublicSearchIntent, readPublicSearchIntent, savePublicSearchIntent } from './publicSearchIntent';
beforeEach(() => sessionStorage.clear());
afterEach(() => vi.useRealTimers());
describe('public search intent boundaries', () => {
  it('keeps preferences in this tab, without putting them in a URL', () => {
    const before = location.href;
    savePublicSearchIntent({ subject: 'Engineering', country: 'Japan', budget: 6000 });
    expect(readPublicSearchIntent()).toEqual({ subject: 'Engineering', country: 'Japan', budget: 6000 });
    expect(location.href).toBe(before);
    expect(localStorage.getItem('unimatch.public-search-intent')).toBeNull();
    clearPublicSearchIntent(); expect(readPublicSearchIntent()).toBeNull();
  });
  it('expires rather than applying an old visitor preference to a later case', () => {
    vi.useFakeTimers(); savePublicSearchIntent({ subject: 'Medicine', country: '', budget: null });
    vi.advanceTimersByTime(3600001); expect(readPublicSearchIntent()).toBeNull();
  });
  it.each([NaN, -1, 1000001])('rejects an invalid budget: %s', budget => {
    savePublicSearchIntent({ subject: 'Design', country: '', budget });
    expect(readPublicSearchIntent()).toBeNull();
  });
  it('tolerates damaged or unavailable storage without preventing sign-in', () => {
    sessionStorage.setItem('unimatch.public-search-intent', '{'); expect(readPublicSearchIntent()).toBeNull();
    vi.spyOn(Storage.prototype, 'getItem').mockImplementationOnce(() => { throw new Error('blocked'); });
    expect(readPublicSearchIntent()).toBeNull();
  });
});

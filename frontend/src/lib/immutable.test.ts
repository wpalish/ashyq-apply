/** Path-based updates must copy, never mutate. */

import { describe, expect, it } from 'vitest';
import { castInput, get, setIn } from './immutable';

describe('get', () => {
  it('reads a nested value', () => {
    expect(get({ a: { b: { c: 42 } } }, ['a', 'b', 'c'])).toBe(42);
  });

  it('returns undefined for a missing branch instead of throwing', () => {
    expect(get({ a: {} }, ['a', 'b', 'c'])).toBeUndefined();
    expect(get(null, ['a'])).toBeUndefined();
  });

  it('reads through arrays', () => {
    expect(get({ xs: [{ n: 1 }, { n: 2 }] }, ['xs', 1, 'n'])).toBe(2);
  });
});

describe('setIn', () => {
  it('does not mutate the original object', () => {
    const original = { a: { b: 1 } };
    const updated = setIn(original, ['a', 'b'], 2);
    expect(original.a.b).toBe(1);
    expect(updated.a.b).toBe(2);
  });

  it('leaves untouched branches referentially identical', () => {
    const original = { a: { b: 1 }, keep: { deep: true } };
    const updated = setIn(original, ['a', 'b'], 2);
    expect(updated.keep).toBe(original.keep);
  });

  it('preserves arrays as arrays', () => {
    const updated = setIn({ xs: [1, 2, 3] }, ['xs', 1], 9);
    expect(Array.isArray(updated.xs)).toBe(true);
    expect(updated.xs).toEqual([1, 9, 3]);
  });

  it('creates a missing branch rather than throwing', () => {
    expect(setIn({}, ['a', 'b'], 1)).toEqual({ a: { b: 1 } });
  });
});

describe('castInput', () => {
  it('keeps strings as strings', () => {
    expect(castInput('hello', 'string')).toBe('hello');
  });

  it('turns an emptied field into null, not zero', () => {
    // A cleared score must read as "not provided", never as a score of nought.
    expect(castInput('', 'number')).toBeNull();
    expect(castInput('', 'float')).toBeNull();
  });

  it('parses integers and floats', () => {
    expect(castInput('42', 'number')).toBe(42);
    expect(castInput('6.5', 'float')).toBe(6.5);
  });

  it('returns null rather than NaN for unparseable input', () => {
    expect(castInput('abc', 'number')).toBeNull();
    expect(castInput('abc', 'float')).toBeNull();
  });
});

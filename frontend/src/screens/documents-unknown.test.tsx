import { describe, expect, it } from 'vitest';
import { allRequirementLevelsUnknown } from '@/screens/DocumentsScreen';

const doc = (level: string) => ({ requirement_level: level }) as never;

describe('saying "not stated" once instead of seven times', () => {
  /**
   * When a university publishes a document list without marking anything
   * required, every row carries the identical grey chip. Seven copies of the
   * same sentence bury the lead times and format limits, which are the part
   * that differs. The fact is worth stating; it is not worth repeating.
   */
  it('is true when nothing in the list states a requirement level', () => {
    expect(allRequirementLevelsUnknown([doc('unknown'), doc('unknown')])).toBe(true);
  });

  it('is false as soon as one item does state one', () => {
    expect(allRequirementLevelsUnknown([doc('unknown'), doc('required')])).toBe(false);
    expect(allRequirementLevelsUnknown([doc('conditional'), doc('unknown')])).toBe(false);
  });

  it('is false for an empty list, so nothing is announced about nothing', () => {
    expect(allRequirementLevelsUnknown([])).toBe(false);
  });
});

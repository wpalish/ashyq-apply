import { describe, expect, it } from 'vitest';
import { orderCaveats } from './caveats';

describe('ordering the caveats about aid', () => {
  it('puts what explains the figures first, then whether the aid can be won', () => {
    const warnings = [
      "'Grant' may not be combined with other awards.",
      "'Grant' requires a departmental nomination, so it cannot be applied for directly.",
      'Cost is published for 2026/27 but the award amount for 2024/25. The figures below are not directly comparable.',
    ];
    expect(orderCaveats(warnings)).toEqual([warnings[2], warnings[1]]);
  });

  it('keeps the original order among equals, and copes with nothing', () => {
    expect(orderCaveats(['a', 'b', 'c'], 3)).toEqual(['a', 'b', 'c']);
    expect(orderCaveats(undefined)).toEqual([]);
  });
});

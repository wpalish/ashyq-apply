import { describe, expect, it, vi } from 'vitest';
import { BUNDLE_BUDGET_KB, bundleBudget, measureBundle, overBudget } from '../bundle-budget';

/** Bytes gzip cannot shrink (a fixed xorshift stream), so the measured size is known. */
function incompressible(bytes: number, seed = 0x9e3779b9): Uint8Array {
  const out = new Uint8Array(bytes);
  let x = seed >>> 0;
  for (let i = 0; i < bytes; i += 1) {
    x ^= x << 13;
    x >>>= 0;
    x ^= x >>> 17;
    x ^= x << 5;
    x >>>= 0;
    out[i] = x & 0xff;
  }
  return out;
}

type Hook = (this: { error: (message: string) => never }, options: unknown, bundle: Record<string, unknown>) => void;

function runPlugin(bundle: Record<string, unknown>) {
  const plugin = bundleBudget();
  const error = vi.fn((message: string) => {
    throw new Error(message);
  });
  const log = vi.spyOn(console, 'log').mockImplementation(() => undefined);
  try {
    (plugin.generateBundle as Hook).call({ error }, {}, bundle);
  } finally {
    log.mockRestore();
  }
  return { plugin, error };
}

describe('the bundle-size budget (PERF-1)', () => {
  it('pins the budgets the release ledger names', () => {
    expect(BUNDLE_BUDGET_KB).toEqual({ jsGzip: 200, cssGzip: 35 });
  });

  it('measures gzip per kind and ignores source maps and other assets', () => {
    const sizes = measureBundle({
      'assets/a.js': incompressible(50_000),
      'assets/b.js': 'const x = 1;'.repeat(10_000),
      'assets/a.css': incompressible(10_000, 7),
      'assets/a.js.map': incompressible(500_000, 3),
      'assets/font.woff': incompressible(500_000, 5),
    });
    expect(sizes.jsGzipKb).toBeGreaterThan(50);
    expect(sizes.jsGzipKb).toBeLessThan(51);
    expect(sizes.cssGzipKb).toBeGreaterThan(10);
    expect(sizes.cssGzipKb).toBeLessThan(10.2);
  });

  it('names each kind that is over its budget', () => {
    expect(overBudget({ jsGzipKb: 169.3, cssGzipKb: 27.5 })).toEqual([]);
    expect(overBudget({ jsGzipKb: 200.01, cssGzipKb: 27.5 })).toEqual(['JS is 200.01 kB gzip, over its 200 kB budget']);
    expect(overBudget({ jsGzipKb: 1, cssGzipKb: 36 })).toEqual(['CSS is 36.00 kB gzip, over its 35 kB budget']);
  });

  it('fails the build when a chunk outgrows the budget, and only in a build', () => {
    const small = { 'assets/index.js': { type: 'chunk', code: 'console.log(1)' } };
    expect(runPlugin(small).error).not.toHaveBeenCalled();
    expect(runPlugin(small).plugin.apply).toBe('build');

    const heavy = {
      'assets/index.js': { type: 'chunk', code: 'export {}' },
      'assets/vendor.js': { type: 'asset', source: incompressible(201_000) },
    };
    expect(() => runPlugin(heavy)).toThrow(/bundle budget \(PERF-1\): JS is 201\.\d\d kB gzip, over its 200 kB budget/);
  });
});

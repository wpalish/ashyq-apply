/**
 * PERF-1: the production bundle's size budget, enforced by `npm run build`.
 *
 * Measured on 2026-10-22 (docs/process/PERF_2026-10-22.md): JS 606.2 kB,
 * 169.3 kB gzip; CSS 97.0 kB, 27.5 kB gzip. The build is deterministic, so
 * there is no CI noise to absorb; the headroom (about 18 % on JS) is for the
 * next few cycles of ordinary growth (catalogue keys, a screen), and a new
 * heavy dependency or an accidental second copy of one fails the build.
 * Raise a budget on purpose, with its number in RELEASE_CHECKLIST gate 3, not
 * to get a build through.
 */

import { gzipSync } from 'node:zlib';
import type { Plugin } from 'vite';

export const BUNDLE_BUDGET_KB = { jsGzip: 200, cssGzip: 35 } as const;

export interface BundleSizes {
  jsGzipKb: number;
  cssGzipKb: number;
}

/** What Vite's report calls "gzip", summed per kind (kB = 1000 bytes, as Vite prints). */
export function measureBundle(files: Record<string, string | Uint8Array>): BundleSizes {
  let js = 0;
  let css = 0;
  for (const [name, content] of Object.entries(files)) {
    if (name.endsWith('.js')) js += gzipSync(content).length;
    else if (name.endsWith('.css')) css += gzipSync(content).length;
  }
  return { jsGzipKb: js / 1000, cssGzipKb: css / 1000 };
}

/** The sentences a build over budget fails with; empty when within it. */
export function overBudget(sizes: BundleSizes, budget: { jsGzip: number; cssGzip: number } = BUNDLE_BUDGET_KB): string[] {
  const over: string[] = [];
  if (sizes.jsGzipKb > budget.jsGzip) over.push(`JS is ${sizes.jsGzipKb.toFixed(2)} kB gzip, over its ${budget.jsGzip} kB budget`);
  if (sizes.cssGzipKb > budget.cssGzip) over.push(`CSS is ${sizes.cssGzipKb.toFixed(2)} kB gzip, over its ${budget.cssGzip} kB budget`);
  return over;
}

/** The Vite plugin: measures the emitted chunks and fails the build over budget. */
export function bundleBudget(budget: { jsGzip: number; cssGzip: number } = BUNDLE_BUDGET_KB): Plugin {
  return {
    name: 'bundle-budget',
    apply: 'build',
    generateBundle(_options, bundle) {
      const files: Record<string, string | Uint8Array> = {};
      for (const [name, output] of Object.entries(bundle)) {
        files[name] = output.type === 'chunk' ? output.code : output.source;
      }
      const sizes = measureBundle(files);
      const over = overBudget(sizes, budget);
      if (over.length > 0) {
        this.error(`bundle budget (PERF-1): ${over.join('; ')}. See frontend/bundle-budget.ts.`);
      }
      console.log(
        `bundle budget (PERF-1): JS ${sizes.jsGzipKb.toFixed(2)} / ${budget.jsGzip} kB gzip, ` +
          `CSS ${sizes.cssGzipKb.toFixed(2)} / ${budget.cssGzip} kB gzip`,
      );
    },
  };
}

// @vitest-environment node
/**
 * The three Playwright configs, held by a test (E2E-CFG-1).
 *
 * `npm run e2e`, `e2e:auth` and `e2e:kb` share ports 5173/8099 and run one at
 * a time. What keeps them honest is a handful of lines in three files: none
 * adopts a server it did not start, each states the backend mode it asserts,
 * and every spec belongs to exactly one suite. Nothing checked those lines
 * before; a `reuseExistingServer: true` pasted from a tutorial, or a new
 * `kb-*.spec.ts` that the demo suite also picks up, passed CI.
 *
 * The configs are read as text, never imported: importing them would pull in
 * `@playwright/test`, which vitest has no business loading.
 */

import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const FRONTEND = fileURLToPath(new URL('..', import.meta.url));
const read = (relative: string) => readFileSync(path.join(FRONTEND, relative), 'utf8');

const CONFIGS = {
  demo: 'playwright.config.ts',
  auth: 'playwright.auth.config.ts',
  kb: 'playwright.kb.config.ts',
} as const;
type Suite = keyof typeof CONFIGS;
const SUITES = Object.keys(CONFIGS) as Suite[];

const text = (suite: Suite) => read(CONFIGS[suite]);

/** The `webServer` array's source, from its key to the end of the file. */
function webServerBlock(source: string): string {
  const at = source.indexOf('webServer:');
  expect(at, 'a webServer entry').toBeGreaterThan(-1);
  return source.slice(at);
}

/** Every string literal inside one `key: [ … ]` array, or the single `key: '…'`. */
function stringsOf(source: string, key: string): string[] {
  const array = new RegExp(`${key}:\\s*\\[([^\\]]*)\\]`).exec(source);
  const single = new RegExp(`${key}:\\s*'([^']*)'`).exec(source);
  if (array) return [...array[1]!.matchAll(/'([^']*)'/g)].map((m) => m[1]!);
  if (single) return [single[1]!];
  return [];
}

/** Playwright-style glob → RegExp, for the shapes these configs use (`**`, `*`). */
function globToRegExp(glob: string): RegExp {
  let out = '';
  for (let i = 0; i < glob.length; i += 1) {
    const c = glob[i]!;
    if (c === '*' && glob[i + 1] === '*' && glob[i + 2] === '/') {
      out += '(?:.*/)?';
      i += 2;
    } else if (c === '*') {
      out += '[^/]*';
    } else {
      out += c.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
    }
  }
  return new RegExp(`^${out}$`);
}

const matchesAny = (file: string, globs: string[]) => globs.some((g) => globToRegExp(g).test(file));

/** Which specs a config runs: testDir ./e2e, narrowed by testMatch, minus testIgnore. */
function claimedSpecs(suite: Suite, specs: string[]): string[] {
  const source = text(suite);
  expect(source, `${CONFIGS[suite]} testDir`).toMatch(/testDir:\s*'\.\/e2e'/);
  const match = stringsOf(source, 'testMatch');
  const ignore = stringsOf(source, 'testIgnore');
  return specs.filter((file) => {
    const rel = `e2e/${file}`;
    if (match.length > 0 && !matchesAny(rel, match)) return false;
    return !matchesAny(rel, ignore);
  });
}

/** `${PORT}` / `${API_PORT}` in a template literal, resolved from the file's own consts. */
function resolvedUrls(source: string): string[] {
  const consts = Object.fromEntries(
    [...source.matchAll(/const (\w+) = (\d+);/g)].map((m) => [m[1]!, m[2]!] as [string, string]),
  );
  return [...webServerBlock(source).matchAll(/url:\s*`([^`]*)`/g)].map((m) =>
    m[1]!.replace(/\$\{(\w+)\}/g, (_, name: string) => consts[name] ?? `<${name}?>`),
  );
}

describe('the three Playwright configs', () => {
  it.each(SUITES)('%s never adopts a server it did not start', (suite) => {
    const source = text(suite);
    const flags = [...source.matchAll(/reuseExistingServer:\s*([^,\s}]+)/g)].map((m) => m[1]);
    // Two servers per config, the API and Vite; both refuse a busy port.
    expect(flags).toEqual(['false', 'false']);
  });

  it.each(SUITES)('%s points its API at 8099 and Vite at 5173 (the proxy hard-codes 8099)', (suite) => {
    expect(resolvedUrls(text(suite))).toEqual(['http://127.0.0.1:8099/api/health', 'http://127.0.0.1:5173']);
  });

  it('every spec runs in exactly one suite', () => {
    const specs = readdirSync(path.join(FRONTEND, 'e2e')).filter((f) => f.endsWith('.spec.ts'));
    expect(specs.length).toBeGreaterThan(0);
    const owners = new Map<string, Suite[]>(specs.map((s) => [s, []]));
    for (const suite of SUITES) for (const spec of claimedSpecs(suite, specs)) owners.get(spec)!.push(suite);
    const wrong = [...owners].filter(([, by]) => by.length !== 1).map(([spec, by]) => `${spec}: [${by.join(', ')}]`);
    expect(wrong).toEqual([]);
  });

  it('claims the auth and kb specs by glob, and the demo suite ignores them by the same glob', () => {
    expect(stringsOf(text('auth'), 'testMatch')).toEqual(['**/auth-journey.spec.ts']);
    expect(stringsOf(text('kb'), 'testMatch')).toEqual(['**/kb-*.spec.ts']);
    expect(stringsOf(text('demo'), 'testMatch')).toEqual([]);
    expect(stringsOf(text('demo'), 'testIgnore')).toEqual(['**/auth-journey.spec.ts', '**/kb-*.spec.ts']);
  });

  it.each(['demo', 'auth'] as const)('%s states the mode it asserts: demo on, knowledge mode kb', (suite) => {
    const block = webServerBlock(text(suite));
    expect(block).toMatch(/UNIMATCH_DEMO_MODE:\s*'true'/);
    expect(block).toMatch(/UNIMATCH_KNOWLEDGE_MODE:\s*'kb'/);
  });

  it('the kb API script states its mode: demo off, knowledge mode kb', () => {
    const script = read('e2e/kb-env/serve-api.sh');
    expect(script).toMatch(/^export UNIMATCH_DEMO_MODE=false$/m);
    expect(script).toMatch(/^export UNIMATCH_KNOWLEDGE_MODE=kb$/m);
  });

  it.each(SUITES)('%s starts its API through a serve-api.sh under e2e/*-env/ (E2E-DB-1)', (suite) => {
    const source = text(suite);
    const api = webServerBlock(source);
    // The first server is the API; its command is the env directory's script, nothing else.
    expect(/command:\s*(`[^`]*`|'[^']*')/.exec(api)?.[1]).toBe('`bash "${SERVE_API}"`');
    const from = /import \{[^}]*\bSERVE_API\b[^}]*\} from '\.\/(e2e\/[\w-]+-env)\/paths';/.exec(source);
    expect(from, `${CONFIGS[suite]} imports SERVE_API from e2e/*-env/paths`).not.toBeNull();
    const envDir = from![1]!;
    expect(read(`${envDir}/paths.ts`)).toMatch(/export const SERVE_API = path\.join\(here, 'serve-api\.sh'\);/);
    const script = read(`${envDir}/serve-api.sh`);
    // The database lives inside the scratch directory the script wipes …
    expect(script).toMatch(/^export UNIMATCH_DATABASE_URL="sqlite:\/\/\/\$SCRATCH\/[\w.-]+\.db"$/m);
    // … and the directory's name is checked before anything is removed.
    const guard = script.search(/^case "\$\(basename -- "\$SCRATCH"\)" in$/m);
    const wipe = script.indexOf('rm -rf -- "$SCRATCH"');
    expect(guard).toBeGreaterThan(-1);
    expect(wipe).toBeGreaterThan(guard);
  });

  it.each([
    ['demo', 'DEMO_SCRATCH_DIR'],
    ['auth', 'AUTH_SCRATCH_DIR'],
  ] as const)('%s hands the script its own scratch directory, never a database URL', (suite, dir) => {
    const api = webServerBlock(text(suite));
    expect(api).toContain(`E2E_SCRATCH_DIR: ${dir}`);
    expect(api).not.toMatch(/UNIMATCH_DATABASE_URL/);
    expect(read('e2e/demo-env/paths.ts')).toMatch(
      new RegExp(`export const ${dir} = path\\.join\\(data, 'e2e-${suite}'\\);`),
    );
  });

  it('npm run typecheck reads all three configs', () => {
    const tsconfig = JSON.parse(read('tsconfig.json')) as { include: string[] };
    for (const file of Object.values(CONFIGS)) expect(tsconfig.include).toContain(file);
  });
});

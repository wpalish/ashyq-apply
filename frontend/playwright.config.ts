import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

/**
 * A hermetic E2E run.
 *
 * This suite used to run against fixed ports with `reuseExistingServer: true`
 * and no database of its own. Every one of those was a way to test something
 * other than the code in front of you:
 *
 *  - `reuseExistingServer` attached the run to whatever was already listening
 *    on 8099. On this machine that was a six-hour-old worker holding model
 *    definitions from before a schema change, which had already buried three
 *    jobs in the dead-letter state.
 *  - No `UNIMATCH_DATABASE_URL` meant `backend/data/unimatch.db`, which had
 *    grown to 61 MB across 86 applicant profiles, 50 runs and 19,831 claims.
 *    Document collection timed out purely because of the accumulated data, and
 *    the suite failed for a reason that had nothing to do with the change
 *    under test.
 *  - Fixed ports meant two runs could never be in flight at once.
 *
 * So: fresh ports, a fresh database and a fresh directory per run, servers
 * never reused, and everything removed afterwards.
 */

/** Ports nothing is listening on, asked of the OS rather than guessed. */
function freePorts(count: number): number[] {
  const script = `
    const net = require('node:net');
    const servers = [];
    (function next() {
      if (servers.length === ${count}) {
        console.log(servers.map((s) => s.address().port).join(' '));
        servers.forEach((s) => s.close());
        return;
      }
      const s = net.createServer();
      s.listen(0, '127.0.0.1', () => { servers.push(s); next(); });
    })();
  `;
  const out = execFileSync(process.execPath, ['-e', script], { encoding: 'utf8' });
  return out.trim().split(/\s+/).map(Number);
}

/**
 * Chosen once per run, then shared with every process through the environment.
 *
 * Playwright evaluates this file again inside each test worker. Allocating
 * ports unconditionally therefore gave the workers a different pair from the
 * one the servers were started on, and every test failed with
 * ERR_CONNECTION_REFUSED against a port nothing was listening on — while the
 * API log cheerfully showed it running on the other one. Workers inherit the
 * parent's environment, so the first evaluation decides and the rest read.
 */
const API_PORT = Number(process.env.ASHYQ_E2E_API_PORT ?? 0) || 0;
const WEB_PORT = Number(process.env.ASHYQ_E2E_WEB_PORT ?? 0) || 0;
const [allocatedApi, allocatedWeb] = API_PORT && WEB_PORT ? [API_PORT, WEB_PORT] : freePorts(2);
process.env.ASHYQ_E2E_API_PORT = String(allocatedApi);
process.env.ASHYQ_E2E_WEB_PORT = String(allocatedWeb);

/**
 * One directory per run, named so a leftover is obvious in `ls /tmp`. The
 * teardown removes it; if a run is killed hard enough to skip teardown, the
 * name says what it was and the OS clears tmp eventually.
 */
const RUN_DIR =
  process.env.ASHYQ_E2E_RUN_DIR ?? fs.mkdtempSync(path.join(os.tmpdir(), 'ashyq-e2e-'));
const DATABASE_URL = `sqlite:///${path.join(RUN_DIR, 'e2e.sqlite3')}`;

process.env.ASHYQ_E2E_RUN_DIR = RUN_DIR;

const serverEnv = {
  ...process.env,
  UNIMATCH_DATABASE_URL: DATABASE_URL,
  // Demo data only: the suite must never reach a real university site.
  UNIMATCH_DEMO_MODE: 'true',
  PORT: String(allocatedApi),
  VITE_DEV_PORT: String(allocatedWeb),
  VITE_API_TARGET: `http://127.0.0.1:${allocatedApi}`,
};

export default defineConfig({
  testDir: './e2e',
  globalTeardown: './e2e/global-teardown.ts',
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${allocatedWeb}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  // Both servers, so `npm run e2e` is self-contained. Without the API the
  // suite fails with a wall of ECONNREFUSED instead of a clear cause.
  webServer: [
    {
      // The API only enqueues; a worker is needed to consume the queue.
      // run.sh supervises both and takes the worker down with the API.
      command: '../backend/run.sh --with-worker',
      url: `http://127.0.0.1:${allocatedApi}/api/health`,
      // Never reuse. A server that is already up is a server this run did not
      // configure, and cannot vouch for.
      reuseExistingServer: false,
      timeout: 90_000,
      stdout: 'ignore',
      env: serverEnv,
    },
    {
      command: 'npm run dev',
      url: `http://127.0.0.1:${allocatedWeb}`,
      reuseExistingServer: false,
      timeout: 90_000,
      env: serverEnv,
    },
  ],
});

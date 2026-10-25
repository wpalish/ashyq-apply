import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'node:fs';

const PORT = 5173;
const API_PORT = 8099;

// The sandbox's preinstalled Chromium, when the installed Playwright's own
// revision is not downloaded (as in playwright.kb.config.ts). CI uses its own.
const LOCAL_CHROMIUM = '/opt/pw-browsers/chromium';
const launchOptions = !process.env.CI && existsSync(LOCAL_CHROMIUM) ? { executablePath: LOCAL_CHROMIUM } : {};

export default defineConfig({
  testDir: './e2e',
  // auth-journey.spec.ts needs a backend with UNIMATCH_AUTH_ENABLED=true, so
  // it runs under playwright.auth.config.ts. Without this exclusion it would
  // be picked up here too and assert a sign-in screen that never appears.
  // kb-journey.spec.ts needs a kb-mode backend (playwright.kb.config.ts).
  testIgnore: ['**/auth-journey.spec.ts', '**/kb-journey.spec.ts', '**/kb-accessibility.spec.ts'],
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    launchOptions,
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
      // Invoked through bash rather than as an executable: on Windows the
      // shebang means nothing to cmd.exe and the suite dies before the first
      // test with an unhelpful "'..' is not recognized".
      command: 'bash ../backend/run.sh --with-worker',
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      // Never adopt a server already on the port, as the auth and kb configs:
      // a stale run, or another worktree's suite on the same ports, would
      // answer with its own code and its own env, and the run would assert
      // against a product it did not start.
      reuseExistingServer: false,
      timeout: 60_000,
      stdout: 'ignore',
      // The mode this suite asserts, stated rather than inherited: a demo
      // server whose knowledge mode is kb (both are the Settings defaults CI
      // runs with). Explicit, so a shell export or a backend/.env cannot turn
      // the local run into a different product (journey.spec.ts, MODE-1).
      env: { UNIMATCH_DEMO_MODE: 'true', UNIMATCH_KNOWLEDGE_MODE: 'kb' },
    },
    {
      command: 'npm run dev',
      url: `http://127.0.0.1:${PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});

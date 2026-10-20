/**
 * The kb-mode E2E run (E2E-KB): the browser journey the two manual KB smokes
 * walked (docs/process/KB_E2E_SMOKE_2026-10-19.md), against the knowledge base
 * as an applicant gets it by default.
 *
 * A config of its own for the same reason as playwright.auth.config.ts:
 * `webServer` is top-level, so a backend in another mode needs another file.
 * e2e/kb-env/serve-api.sh starts the API and the worker with demo mode off,
 * `UNIMATCH_KNOWLEDGE_MODE=kb`, no search provider, no browser tier, a scratch
 * SQLite database migrated by `alembic upgrade head`, and the network guard.
 *
 * Same ports as the other two suites (the vite proxy hard-codes 8099), so it
 * never runs beside them; CI runs the three as sequential steps, and this one
 * refuses to adopt a server it did not start.
 */

import { defineConfig, devices } from '@playwright/test';
import { existsSync } from 'node:fs';
import { KB_SCRATCH_DIR, SERVE_API } from './e2e/kb-env/paths';

const PORT = 5173;
const API_PORT = 8099;

// The sandbox's preinstalled Chromium, when the installed Playwright's own
// revision is not downloaded. CI installs Playwright's browser and uses it.
const LOCAL_CHROMIUM = '/opt/pw-browsers/chromium';
const launchOptions = !process.env.CI && existsSync(LOCAL_CHROMIUM) ? { executablePath: LOCAL_CHROMIUM } : {};

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/kb-journey.spec.ts',
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-kb' }]],
  outputDir: 'test-results-kb',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 }, launchOptions },
    },
  ],
  webServer: [
    {
      command: `bash "${SERVE_API}"`,
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      // A demo-mode backend left running would answer every request and the
      // journey would assert kb copy against demo data. Fail on a busy port.
      reuseExistingServer: false,
      timeout: 90_000,
      stdout: 'ignore',
      env: { E2E_KB_DIR: KB_SCRATCH_DIR },
    },
    {
      command: 'npm run dev',
      url: `http://127.0.0.1:${PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});

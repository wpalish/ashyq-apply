/**
 * The auth-enabled E2E run.
 *
 * `webServer` is a top-level field, not a per-project one, so both servers
 * boot once before any project starts and every project shares them. A second
 * project therefore cannot run against a differently-configured backend —
 * only a second config file can, which is why this exists rather than an
 * extra entry in playwright.config.ts.
 *
 * It deliberately reuses ports 5173 and 8099. The vite dev server hard-codes
 * its port and proxies /api to 8099, and with auth on the API rejects any
 * unsafe request whose Origin is outside UNIMATCH_CORS_ORIGINS — so moving
 * either port would mean parametrising the proxy and the CORS list to gain
 * nothing. The cost is that this suite and `npm run e2e` must never run at
 * the same time; CI runs them as sequential steps.
 */

import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const PORT = 5173;
const API_PORT = 8099;
const here = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/auth-journey.spec.ts',
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-auth' }]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  // One project: an auth flow gains nothing from a second viewport, and the
  // servers it needs are expensive enough to boot once.
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: [
    {
      command: 'bash ../backend/run.sh --with-worker',
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      // The interlock. With `true`, a backend left running from `npm run e2e`
      // or a dev shell would be silently adopted — auth disabled — and every
      // assertion below would pass against the wrong build. Failing loudly on
      // a busy port is the point.
      reuseExistingServer: false,
      timeout: 90_000,
      stdout: 'ignore',
      env: {
        UNIMATCH_AUTH_ENABLED: 'true',
        // Its own database: pointing at the dev one would write real users
        // into it and migrate it under different settings.
        UNIMATCH_DATABASE_URL: `sqlite:///${path.resolve(here, '../backend/data/e2e-auth.db')}`,
        // Production hashes at 2**17, about a second each. This suite pays
        // that four times over plus once at import for the dummy hash, and
        // proves nothing by it. Same value and reasoning as the API tests.
        UNIMATCH_PASSWORD_SCRYPT_LOG2: '14',
        // Two independent limiters guard sign-in — per IP and per email, ten
        // a minute each. A re-run inside a minute would 429 on the defaults.
        UNIMATCH_AUTH_RATE_LIMIT_PER_MINUTE: '60',
      },
    },
    {
      command: 'npm run dev',
      url: `http://127.0.0.1:${PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});

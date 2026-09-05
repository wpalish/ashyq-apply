import { defineConfig, devices } from '@playwright/test';

const PORT = 5173;
const API_PORT = 8099;

export default defineConfig({
  testDir: './e2e',
  // auth-journey.spec.ts needs a backend with UNIMATCH_AUTH_ENABLED=true, so
  // it runs under playwright.auth.config.ts. Without this exclusion it would
  // be picked up here too and assert a sign-in screen that never appears.
  testIgnore: '**/auth-journey.spec.ts',
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
      reuseExistingServer: true,
      timeout: 60_000,
      stdout: 'ignore',
    },
    {
      command: 'npm run dev',
      url: `http://127.0.0.1:${PORT}`,
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});

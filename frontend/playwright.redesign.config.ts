import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', testMatch: 'redesign.spec.ts', timeout: 30_000,
  use: { baseURL: 'http://127.0.0.1:5178', screenshot: 'only-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { ...devices['Pixel 7'], viewport: { width: 390, height: 844 } } },
  ],
  webServer: { command: 'npm run dev -- --port 5178', url: 'http://127.0.0.1:5178', reuseExistingServer: true },
});

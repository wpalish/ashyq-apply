/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  server: {
    // Pin the host: Vite otherwise binds to [::1] only on this machine, and
    // Playwright's 127.0.0.1 base URL then cannot reach it.
    host: '127.0.0.1',
    // Both are overridable so an E2E run can take a pair of ports nobody else
    // is on. Fixed ports meant a second run — or a stale server from an
    // earlier one — silently shared the first run's processes. Defaults are
    // unchanged, so plain `npm run dev` behaves exactly as before.
    port: Number(process.env.VITE_DEV_PORT ?? 5173),
    strictPort: true,
    // The API is same-origin in dev, so no CORS surprises and no API base URL
    // to configure in the client.
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8099',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    // Source maps reconstruct the original source, comments included, for
    // anyone who loads the site. Useful locally, not something to publish, so
    // a production build omits them unless VITE_SOURCEMAP is set explicitly
    // for a debugging deploy.
    sourcemap: process.env.VITE_SOURCEMAP === 'true' || process.env.NODE_ENV !== 'production',
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});

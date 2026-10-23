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
    port: 5173,
    strictPort: true,
    // The API is same-origin in dev, so no CORS surprises and no API base URL
    // to configure in the client.
    proxy: { '/api': { target: 'http://127.0.0.1:8099', changeOrigin: true } },
  },
  build: { outDir: 'dist', sourcemap: true },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});

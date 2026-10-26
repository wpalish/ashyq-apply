/// <reference types="vitest/config" />
import { defineConfig, searchForWorkspaceRoot } from 'vite';
import react from '@vitejs/plugin-react';
import { existsSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { bundleBudget } from './bundle-budget';

// A git worktree links the main checkout's node_modules (scripts/link_worktree_env.sh).
// Vite resolves imports to their realpath, which then lies outside the worktree,
// and refuses to serve static files there (the @fontsource fonts 403). Allow the
// realpath too; in a checkout with a real node_modules it is inside the root already.
const nodeModules = path.resolve(__dirname, 'node_modules');
const nodeModulesReal = existsSync(nodeModules) ? realpathSync(nodeModules) : nodeModules;

export default defineConfig({
  // bundleBudget fails `npm run build` when the gzip JS or CSS outgrows its budget (PERF-1).
  plugins: [react(), bundleBudget()],
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
    // Setting `allow` replaces Vite's default, so the workspace root stays first.
    fs: { allow: [searchForWorkspaceRoot(process.cwd()), nodeModulesReal] },
  },
  build: { outDir: 'dist', sourcemap: true },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});

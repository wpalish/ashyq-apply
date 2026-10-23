import { defineConfig } from 'vitest/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.dirname(fileURLToPath(import.meta.url));
export default defineConfig({
  root,
  cacheDir: path.join(root, '.owned-vite-cache'),
  resolve: { alias: { '@': path.join(root, 'src') } },
  esbuild: { jsx: 'automatic', jsxImportSource: 'react' },
  server: { host: '127.0.0.1', hmr: false },
  test: {
    environment: 'jsdom', globals: true, setupFiles: ['./src/test-setup.ts'],
    include: ['src/screens/LegalScreen.test.tsx', 'src/screens/LegalScreen.privacy.test.tsx'],
    pool: 'forks', maxWorkers: 1, fileParallelism: false, watch: false, api: false,
  },
});

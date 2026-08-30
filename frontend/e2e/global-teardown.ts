import fs from 'node:fs';

/**
 * Remove the run's scratch directory, and say if a server outlived the run.
 *
 * The database, its journals and anything the suite wrote live under one
 * directory created in the config. Leaving it behind is how a "temporary"
 * database becomes a permanent one that later runs quietly share.
 */
export default async function globalTeardown() {
  const dir = process.env.ASHYQ_E2E_RUN_DIR;
  if (dir && fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

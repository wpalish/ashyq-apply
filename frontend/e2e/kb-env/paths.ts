/**
 * Where the kb-mode journey (E2E-KB) keeps its scratch database and the
 * network guard's log. Shared by playwright.kb.config.ts, which hands it to
 * serve-api.sh, and by the spec, which reads the guard's log. Under
 * backend/data, which git ignores, and never backend/data's own database.
 */

import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));

export const KB_SCRATCH_DIR = process.env.E2E_KB_DIR ?? path.resolve(here, '../../../backend/data/e2e-kb');
export const NETGUARD_LOG = path.join(KB_SCRATCH_DIR, 'netguard.log');
export const SERVE_API = path.join(here, 'serve-api.sh');

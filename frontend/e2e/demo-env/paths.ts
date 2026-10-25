/**
 * Where the demo and auth browser suites keep their scratch databases
 * (E2E-DB-1). playwright.config.ts and playwright.auth.config.ts hand one of
 * these to serve-api.sh, which wipes it and points the API's database, cache
 * and exports inside it. Under backend/data, which git ignores, and never
 * backend/data's own database — so a local run starts from what CI starts from.
 */

import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const data = path.resolve(here, '../../../backend/data');

export const DEMO_SCRATCH_DIR = path.join(data, 'e2e-demo');
export const AUTH_SCRATCH_DIR = path.join(data, 'e2e-auth');
export const SERVE_API = path.join(here, 'serve-api.sh');

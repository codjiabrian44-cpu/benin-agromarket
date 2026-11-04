/**
 * Post-build hook that invokes `.venv/bin/python -m src.evaluate.web_budget`
 * to write `docs/tables/web_budget.{csv,md}` after every `astro build`.
 */

import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const PYTHON_BIN = path.join(PROJECT_ROOT, '.venv', 'bin', 'python');

execFileSync(PYTHON_BIN, ['-m', 'src.evaluate.web_budget'], {
  cwd: PROJECT_ROOT,
  stdio: 'inherit',
});

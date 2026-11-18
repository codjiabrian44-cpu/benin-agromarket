/**
 * Standalone budget-report hook (`npm run report:budget`) that invokes
 * `.venv/bin/python -m src.evaluate.web_budget` to write `docs/tables/web_budget.{csv,md}`.
 * Automatically skipped when `.venv` is absent (e.g. Node-only CI or clean clone builds).
 */

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const PYTHON_BIN = path.join(PROJECT_ROOT, '.venv', 'bin', 'python');

if (!fs.existsSync(PYTHON_BIN)) {
  console.log('[Web Budget] .venv not found — skipping Python budget report (Node-only environment).');
  process.exit(0);
}

execFileSync(PYTHON_BIN, ['-m', 'src.evaluate.web_budget'], {
  cwd: PROJECT_ROOT,
  stdio: 'inherit',
});

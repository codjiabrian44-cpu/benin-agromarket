import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { pathToFileURL } from 'node:url';

/**
 * Load Playwright from standard resolution, PLAYWRIGHT_PATH, or local npx cache
 * without adding any package to web/package.json or hardcoding machine paths.
 */
export async function loadPlaywright() {
  try {
    const mod = await import('playwright');
    if (fs.existsSync(mod.chromium.executablePath())) return mod;
  } catch {
    // fallback below
  }
  if (process.env.PLAYWRIGHT_PATH && fs.existsSync(process.env.PLAYWRIGHT_PATH)) {
    return await import(pathToFileURL(process.env.PLAYWRIGHT_PATH).href);
  }
  const npxDir = path.join(os.homedir(), '.npm', '_npx');
  let fallback = null;
  if (fs.existsSync(npxDir)) {
    for (const entry of fs.readdirSync(npxDir)) {
      const candidate = path.join(npxDir, entry, 'node_modules', 'playwright', 'index.mjs');
      if (!fs.existsSync(candidate)) continue;
      const mod = await import(pathToFileURL(candidate).href);
      fallback ??= mod;
      try {
        if (fs.existsSync(mod.chromium.executablePath())) {
          return mod;
        }
      } catch {
        // ignore and keep checking
      }
    }
  }
  if (fallback) return fallback;
  throw new Error('Playwright not found in node_modules, PLAYWRIGHT_PATH, or ~/.npm/_npx');
}

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
};

/**
 * Serve `distDir` mounted under `mountPrefix` (e.g., '/benin-agromarket' or '').
 */
export function startStaticMountServer(distDir, mountPrefix = '/benin-agromarket') {
  const cleanMount = mountPrefix === '/' ? '' : mountPrefix.replace(/\/+$/, '');
  const server = http.createServer((req, res) => {
    const reqUrl = new URL(req.url || '/', 'http://127.0.0.1');
    let pathname = decodeURIComponent(reqUrl.pathname);

    if (cleanMount) {
      if (!pathname.startsWith(cleanMount)) {
        res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('Not found (outside mount prefix)');
        return;
      }
      pathname = pathname.slice(cleanMount.length) || '/';
    }

    const rel = pathname.replace(/^\/+/, '');
    const candidates = [];
    if (!rel) {
      candidates.push(path.join(distDir, 'index.html'));
    } else {
      const direct = path.join(distDir, rel);
      candidates.push(direct);
      candidates.push(path.join(direct, 'index.html'));
    }

    let served = null;
    for (const c of candidates) {
      if (!c.startsWith(distDir)) continue;
      if (fs.existsSync(c) && fs.statSync(c).isFile()) {
        served = c;
        break;
      }
    }

    if (!served) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('404 Not Found');
      return;
    }

    const ext = path.extname(served).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
    fs.createReadStream(served).pipe(res);
  });

  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      const addr = server.address();
      resolve({
        server,
        port: typeof addr === 'object' && addr ? addr.port : 0,
        origin: `http://127.0.0.1:${typeof addr === 'object' && addr ? addr.port : 0}`,
      });
    });
  });
}

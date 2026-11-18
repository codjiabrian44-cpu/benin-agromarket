import assert from 'node:assert/strict';
import path from 'node:path';
import { loadPlaywright, startStaticMountServer } from './playwright-loader.mjs';

const distDir = path.resolve(import.meta.dirname, '..', 'dist');
const rawMount = process.env.BASE_MOUNT ?? '/benin-agromarket';
const BASE_MOUNT = rawMount === '/' ? '' : rawMount.replace(/\/+$/, '');
const MOUNT_DISPLAY = BASE_MOUNT || '/';

const { chromium } = await loadPlaywright();
const { server, origin } = await startStaticMountServer(distDir, BASE_MOUNT);
const browser = await chromium.launch({ headless: true });

try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const failedRequests = [];
  const pageErrors = [];
  const consoleErrors = [];

  page.on('response', (res) => {
    if (res.url().startsWith(origin) && res.status() >= 400) {
      failedRequests.push(`${res.status()} ${res.url()}`);
    }
  });
  page.on('pageerror', (err) => pageErrors.push(String(err)));
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  const seeds = [
    `${origin}${BASE_MOUNT}/`,
    `${origin}${BASE_MOUNT}/404.html`,
    `${origin}${BASE_MOUNT}/en/404/`,
    `${origin}${BASE_MOUNT}/sitemap.xml`,
    `${origin}${BASE_MOUNT}/robots.txt`,
  ];

  const queue = [...seeds];
  const visited = new Set();

  while (queue.length > 0) {
    const url = queue.shift();
    if (!url || visited.has(url)) continue;
    visited.add(url);

    const res = await page.goto(url, { waitUntil: 'networkidle' });
    assert.ok(res, `No response for ${url}`);
    assert.equal(res.status(), 200, `Expected 200 for ${url}, got ${res.status()}`);

    if (url.endsWith('.xml') || url.endsWith('.txt')) {
      continue;
    }

    // Collect every internal <a href> on the page
    const hrefs = await page.$$eval('a[href]', (els) =>
      els.map((a) => a.getAttribute('href') || '').filter(Boolean)
    );

    for (const rawHref of hrefs) {
      if (rawHref.startsWith('#') || rawHref.startsWith('mailto:') || rawHref.startsWith('tel:')) {
        continue;
      }
      const resolved = new URL(rawHref, url);
      if (resolved.origin !== origin) continue;
      if (BASE_MOUNT) {
        assert.ok(
          resolved.pathname.startsWith(`${BASE_MOUNT}/`) || resolved.pathname === BASE_MOUNT,
          `Internal link escaped ${BASE_MOUNT} base path: "${rawHref}" on ${url}`
        );
      }
      resolved.hash = '';
      const nextUrl = resolved.toString();
      if (!visited.has(nextUrl)) {
        queue.push(nextUrl);
      }
    }
  }

  // Exercise client-side JSON fetches and language switch on Explorer & Forecast
  for (const route of [
    `${origin}${BASE_MOUNT}/explorer`,
    `${origin}${BASE_MOUNT}/en/explorer`,
    `${origin}${BASE_MOUNT}/previsions`,
    `${origin}${BASE_MOUNT}/en/forecast`,
  ]) {
    await page.goto(route, { waitUntil: 'networkidle' });
    for (const slug of ['tomatoes', 'yam_white']) {
      await page.click(`button[data-product="${slug}"]`);
      await page.waitForTimeout(200);
    }
    const langLink = page.locator('.lang-switch');
    if ((await langLink.count()) > 0) {
      await langLink.first().click();
      await page.waitForLoadState('networkidle');
    }
  }

  // Check OG image & favicon explicitly
  for (const asset of [`${BASE_MOUNT}/og-image.png`, `${BASE_MOUNT}/favicon.svg`]) {
    const r = await page.request.get(`${origin}${asset}`);
    assert.equal(r.status(), 200, `Expected 200 for ${asset}, got ${r.status()}`);
  }

  assert.equal(failedRequests.length, 0, `404/HTTP errors during crawl:\n${failedRequests.join('\n')}`);
  assert.equal(pageErrors.length, 0, `Page errors:\n${pageErrors.join('\n')}`);
  assert.equal(consoleErrors.length, 0, `Console errors:\n${consoleErrors.join('\n')}`);
  assert.ok(visited.size >= 10, `Expected >= 10 crawled URLs, got ${visited.size}`);

  console.log(
    `[Base Path Crawl Test] PASS: Crawled ${visited.size} internal URLs + client fetches under ${MOUNT_DISPLAY} with zero 404s.`
  );
} finally {
  await browser.close();
  server.close();
}

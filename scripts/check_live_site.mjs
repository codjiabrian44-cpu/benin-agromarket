#!/usr/bin/env node
/**
 * Live site crawler and link/SEO/data-fetch integrity checker for Benin AgroMarket.
 *
 * Usage:
 *   node scripts/check_live_site.mjs <base-url> [--expected-origin <origin>]
 *
 * Example:
 *   node scripts/check_live_site.mjs https://codjiabrian44-cpu.github.io/benin-agromarket/
 */

import assert from 'node:assert/strict';

function parseArgs(argv) {
  const args = argv.slice(2);
  let targetUrl = '';
  let expectedOrigin = '';

  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--expected-origin' && args[i + 1]) {
      expectedOrigin = args[++i];
    } else if (!a.startsWith('--') && !targetUrl) {
      targetUrl = a;
    } else if (a === '-h' || a === '--help') {
      console.log(
        'Usage: node scripts/check_live_site.mjs <url> [--expected-origin <origin>]'
      );
      process.exit(0);
    }
  }

  if (!targetUrl) {
    console.error('Error: missing target URL.');
    console.error('Usage: node scripts/check_live_site.mjs <url> [--expected-origin <origin>]');
    process.exit(2);
  }

  const parsed = new URL(targetUrl);
  const normPath = parsed.pathname.endsWith('/') ? parsed.pathname : `${parsed.pathname}/`;
  const normalizedBaseUrl = `${parsed.origin}${normPath}`;
  const expOrigin = expectedOrigin ? new URL(expectedOrigin).origin : parsed.origin;

  return {
    baseUrl: normalizedBaseUrl,
    targetOrigin: parsed.origin,
    basePath: normPath === '/' ? '' : normPath.replace(/\/+$/, ''),
    expectedOrigin: expOrigin,
  };
}

function unescapeHtmlAttr(str) {
  return str
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

function parseAttrs(tagStr) {
  const attrs = {};
  const attrRe = /([a-zA-Z0-9_:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;
  let m;
  while ((m = attrRe.exec(tagStr)) !== null) {
    attrs[m[1].toLowerCase()] = unescapeHtmlAttr(m[2] ?? m[3] ?? '');
  }
  return attrs;
}

function extractElements(html, tagName) {
  const re = new RegExp(`<${tagName}\\b[^>]*>`, 'gi');
  const out = [];
  let m;
  while ((m = re.exec(html)) !== null) {
    out.push(parseAttrs(m[0]));
  }
  return out;
}

async function fetchOk(url, label) {
  const res = await fetch(url, { redirect: 'follow' });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${label}: ${url}`);
  }
  const finalOrigin = new URL(res.url).origin;
  const reqOrigin = new URL(url).origin;
  if (finalOrigin !== reqOrigin) {
    throw new Error(`Redirected across origins (${reqOrigin} -> ${finalOrigin}) for ${url}`);
  }
  return res;
}

const EXTERNAL_ANCHOR_HOSTS = new Set(['github.com']);

const cfg = parseArgs(process.argv);

function assertExpectedOriginAndBase(
  rawUrl,
  contextLabel,
  { requireBase = true, resolveAgainstUrl = cfg.baseUrl } = {}
) {
  const isExplicitAbs = /^https?:\/\//i.test(rawUrl);
  const expectedBaseForRelative = `${cfg.expectedOrigin}${new URL(resolveAgainstUrl).pathname}`;
  const u = isExplicitAbs ? new URL(rawUrl) : new URL(rawUrl, expectedBaseForRelative);
  assert.equal(
    u.origin,
    cfg.expectedOrigin,
    `${contextLabel} points to unexpected origin "${u.origin}" (expected "${cfg.expectedOrigin}"): ${rawUrl}`
  );
  if (requireBase && cfg.basePath) {
    const okPrefix = u.pathname === cfg.basePath || u.pathname.startsWith(`${cfg.basePath}/`);
    assert.ok(
      okPrefix,
      `${contextLabel} escaped base path "${cfg.basePath}": ${u.pathname} (${rawUrl})`
    );
  }
  return u;
}

function toFetchableUrl(urlObj) {
  if (urlObj.origin === cfg.targetOrigin) return urlObj.toString();
  // When checking a local preview server against --expected-origin, map expectedOrigin back to targetOrigin for HTTP fetch
  if (urlObj.origin === cfg.expectedOrigin) {
    return `${cfg.targetOrigin}${urlObj.pathname}${urlObj.search}`;
  }
  return urlObj.toString();
}

const checkedUrls = new Set();
const htmlQueue = [];

function enqueuePage(urlObj) {
  urlObj.hash = '';
  const fetchUrl = toFetchableUrl(urlObj);
  if (!checkedUrls.has(fetchUrl)) {
    htmlQueue.push(fetchUrl);
  }
}

console.log(`[check_live_site] Checking ${cfg.baseUrl} (expected origin: ${cfg.expectedOrigin})...`);

// 1. Check robots.txt
const robotsUrl = `${cfg.baseUrl}robots.txt`;
const robotsRes = await fetchOk(robotsUrl, 'robots.txt');
const robotsText = await robotsRes.text();
const sitemapMatch = robotsText.match(/^Sitemap:\s*(\S+)$/im);
assert.ok(sitemapMatch, 'robots.txt is missing a Sitemap: directive');
const robotsSitemapUrl = assertExpectedOriginAndBase(sitemapMatch[1].trim(), 'robots.txt Sitemap');

// 2. Check sitemap.xml
const sitemapRes = await fetchOk(toFetchableUrl(robotsSitemapUrl), 'sitemap.xml');
const sitemapXml = await sitemapRes.text();
const locUrls = [...sitemapXml.matchAll(/<loc>([^<]+)<\/loc>/gi)].map((m) =>
  unescapeHtmlAttr(m[1].trim())
);
const xhtmlLinks = [...sitemapXml.matchAll(/<xhtml:link\b[^>]*>/gi)].map((m) => parseAttrs(m[0]));

assert.ok(locUrls.length >= 8, `Expected >= 8 <loc> entries in sitemap.xml, got ${locUrls.length}`);
for (const loc of locUrls) {
  const u = assertExpectedOriginAndBase(loc, 'sitemap.xml <loc>');
  enqueuePage(u);
}
for (const x of xhtmlLinks) {
  assert.ok(x.href, 'sitemap.xml <xhtml:link> missing href');
  const u = assertExpectedOriginAndBase(x.href, `sitemap.xml hreflang=${x.hreflang || '?'}`);
  enqueuePage(u);
}

// 3. Seed entry page & 404 pages
enqueuePage(new URL(cfg.baseUrl));
enqueuePage(new URL(`${cfg.baseUrl}404.html`));
enqueuePage(new URL(`${cfg.baseUrl}en/404/`));

// 4. Verify split JSON data fetches explicitly
const dataFiles = [
  'data/forecasts.json',
  'data/home-summary.json',
  'data/method-tables.json',
  'data/product-maize_white.json',
  'data/product-tomatoes.json',
  'data/product-yam_white.json',
];
const verifiedAssets = new Set();

for (const rel of dataFiles) {
  const dataUrl = `${cfg.baseUrl}${rel}`;
  const res = await fetchOk(dataUrl, `data JSON (${rel})`);
  const json = await res.json();
  assert.ok(json && typeof json === 'object' && Object.keys(json).length > 0, `Empty JSON at ${dataUrl}`);
  verifiedAssets.add(dataUrl);
}

// 5. Crawl every internal HTML page & check links, canonical, hreflang, assets
let pagesChecked = 0;

while (htmlQueue.length > 0) {
  const pageUrl = htmlQueue.shift();
  if (!pageUrl || checkedUrls.has(pageUrl)) continue;
  checkedUrls.add(pageUrl);

  const res = await fetchOk(pageUrl, 'HTML page');
  const ctype = (res.headers.get('content-type') || '').toLowerCase();
  assert.ok(ctype.includes('text/html'), `Expected text/html for ${pageUrl}, got "${ctype}"`);
  const html = await res.text();
  pagesChecked++;

  const is404Page = pageUrl.endsWith('/404.html') || pageUrl.endsWith('/404/');
  const links = extractElements(html, 'link');
  const metas = extractElements(html, 'meta');
  const anchors = extractElements(html, 'a');
  const scripts = extractElements(html, 'script');

  // Check canonical & hreflang links
  if (!is404Page) {
    const canonical = links.find((l) => (l.rel || '').toLowerCase() === 'canonical');
    assert.ok(canonical && canonical.href, `Missing <link rel="canonical"> on ${pageUrl}`);
    const canonicalObj = assertExpectedOriginAndBase(canonical.href, `canonical on ${pageUrl}`);
    const canonicalFetch = toFetchableUrl(canonicalObj);
    if (!verifiedAssets.has(canonicalFetch)) {
      await fetchOk(canonicalFetch, `canonical target (${canonical.href})`);
      verifiedAssets.add(canonicalFetch);
    }

    const alternates = links.filter((l) => (l.rel || '').toLowerCase() === 'alternate' && l.hreflang);
    const langs = new Set(alternates.map((a) => a.hreflang.toLowerCase()));
    for (const reqLang of ['fr', 'en', 'x-default']) {
      assert.ok(langs.has(reqLang), `Missing hreflang="${reqLang}" on ${pageUrl}`);
    }
    for (const alt of alternates) {
      assert.ok(alt.href, `Empty hreflang="${alt.hreflang}" href on ${pageUrl}`);
      const altObj = assertExpectedOriginAndBase(alt.href, `hreflang=${alt.hreflang} on ${pageUrl}`);
      const altFetch = toFetchableUrl(altObj);
      if (!verifiedAssets.has(altFetch)) {
        await fetchOk(altFetch, `hreflang target (${alt.href})`);
        verifiedAssets.add(altFetch);
      }
    }
  }

  // Check og:url and og:image
  for (const prop of ['og:url', 'og:image']) {
    const tag = metas.find((m) => (m.property || '').toLowerCase() === prop);
    assert.ok(tag && tag.content, `Missing <meta property="${prop}"> on ${pageUrl}`);
    const mObj = assertExpectedOriginAndBase(tag.content, `${prop} on ${pageUrl}`);
    if (prop === 'og:image') {
      const mFetch = toFetchableUrl(mObj);
      if (!verifiedAssets.has(mFetch)) {
        await fetchOk(mFetch, `og:image on ${pageUrl}`);
        verifiedAssets.add(mFetch);
      }
    }
  }

  // Check stylesheet, icon, and preload links
  for (const l of links) {
    const rel = (l.rel || '').toLowerCase();
    if (!l.href) continue;
    if (rel === 'stylesheet' || rel === 'icon' || rel === 'preload') {
      const aObj = assertExpectedOriginAndBase(l.href, `link rel=${rel} on ${pageUrl}`);
      const aFetch = toFetchableUrl(aObj);
      if (!verifiedAssets.has(aFetch)) {
        await fetchOk(aFetch, `asset (${rel}) on ${pageUrl}`);
        verifiedAssets.add(aFetch);
      }
    }
  }

  // Check script src assets
  for (const s of scripts) {
    if (!s.src) continue;
    const sObj = assertExpectedOriginAndBase(s.src, `script src on ${pageUrl}`);
    const sFetch = toFetchableUrl(sObj);
    if (!verifiedAssets.has(sFetch)) {
      await fetchOk(sFetch, `script asset on ${pageUrl}`);
      verifiedAssets.add(sFetch);
    }
  }

  // Check every <a> href
  for (const a of anchors) {
    const href = (a.href || '').trim();
    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) {
      continue;
    }
    const isExplicitAbs = /^https?:\/\//i.test(href);
    const baseForResolve = `${cfg.expectedOrigin}${new URL(pageUrl).pathname}`;
    const resolved = isExplicitAbs ? new URL(href) : new URL(href, baseForResolve);

    if (resolved.origin !== cfg.expectedOrigin) {
      const isAllowedExternal =
        resolved.protocol === 'https:' && EXTERNAL_ANCHOR_HOSTS.has(resolved.hostname);
      assert.ok(
        isAllowedExternal,
        `Link on ${pageUrl} points to unexpected origin "${resolved.origin}" (expected "${cfg.expectedOrigin}"): ${href}`
      );
      continue;
    }

    const u = assertExpectedOriginAndBase(resolved.toString(), `internal link "${href}" on ${pageUrl}`);
    enqueuePage(u);
  }
}

console.log(
  `[check_live_site] PASS: Verified ${pagesChecked} HTML pages, ${dataFiles.length} data JSON files, ${verifiedAssets.size} static assets/targets, sitemap (${locUrls.length} locs), canonical & hreflang tags under ${cfg.baseUrl}.`
);

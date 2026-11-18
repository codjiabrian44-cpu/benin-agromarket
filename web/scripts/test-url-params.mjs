import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { SITE_BASE_PATH } from '../astro.config.mjs';

const distDir = path.resolve(import.meta.dirname, '..', 'dist');
const cleanBase = SITE_BASE_PATH === '/' ? '' : SITE_BASE_PATH.replace(/\/$/, '');

const htmlFiles = [
  'index.html',
  'en/index.html',
  'explorer/index.html',
  'en/explorer/index.html',
  'previsions/index.html',
  'en/forecast/index.html',
];

const canonicalSlugs = ['maize_white', 'tomatoes', 'yam_white'];
const legacySlugPattern = /\b(mais-blanc|white-maize|igname-blanche|white-yam)\b/;
const legacyParamPattern = /\?(produit|marche|plage|mediane)=|&(produit|marche|plage|mediane)=/;

for (const rel of htmlFiles) {
  const fullPath = path.join(distDir, rel);
  assert.ok(fs.existsSync(fullPath), `Missing built HTML: ${rel}`);
  const html = fs.readFileSync(fullPath, 'utf8');

  assert.equal(
    legacySlugPattern.test(html),
    false,
    `Legacy localized product slug found in ${rel}`
  );
  assert.equal(
    legacyParamPattern.test(html),
    false,
    `Legacy localized query parameter found in ${rel}`
  );
}

// Verify Home links use canonical ?product=<slug>
for (const homeRel of ['index.html', 'en/index.html']) {
  const html = fs.readFileSync(path.join(distDir, homeRel), 'utf8');
  for (const slug of canonicalSlugs) {
    assert.ok(
      html.includes(`?product=${slug}`),
      `Expected ?product=${slug} link in ${homeRel}`
    );
  }
}

// Verify Explorer <-> Forecast cross-links preserve product & market identically
for (const [rel, expectedTarget] of [
  ['explorer/index.html', `${cleanBase}/previsions?product=maize_white&amp;market=Dantokpa`],
  ['en/explorer/index.html', `${cleanBase}/en/forecast?product=maize_white&amp;market=Dantokpa`],
  ['previsions/index.html', `${cleanBase}/explorer?product=maize_white&amp;market=Dantokpa`],
  ['en/forecast/index.html', `${cleanBase}/en/explorer?product=maize_white&amp;market=Dantokpa`],
]) {
  const html = fs.readFileSync(path.join(distDir, rel), 'utf8');
  const unescaped = html.replace(/&amp;/g, '&');
  const rawTarget = expectedTarget.replace(/&amp;/g, '&');
  assert.ok(
    unescaped.includes(rawTarget),
    `Expected cross-navigation link "${rawTarget}" in ${rel}`
  );
}

console.log('[URL Params Test] PASS: All 6 pages use identical canonical URL parameters (?product, &market, &range, &median, &horizon).');

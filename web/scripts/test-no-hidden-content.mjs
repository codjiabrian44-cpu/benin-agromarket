import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { loadPlaywright, startStaticMountServer } from './playwright-loader.mjs';

const distDir = path.resolve(import.meta.dirname, '..', 'dist');
const BASE_MOUNT = '/benin-agromarket';

const { chromium } = await loadPlaywright();
const { server, origin } = await startStaticMountServer(distDir, BASE_MOUNT);
const browser = await chromium.launch({ headless: true });

async function assertSparklinesAndMapVisible(page, label) {
  const result = await page.evaluate(() => {
    const sparkLines = Array.from(document.querySelectorAll('.stories-section .spark-line'));
    const sparkAreas = Array.from(document.querySelectorAll('.stories-section .spark-area'));
    const sparkDots = Array.from(document.querySelectorAll('.stories-section .dot-anchor'));
    const activeMapPanel = document.querySelector('[data-map-panel="maize_white"]');
    const mapDots = activeMapPanel
      ? Array.from(activeMapPanel.querySelectorAll('.map-market-node'))
      : [];
    const reveals = Array.from(document.querySelectorAll('[data-reveal="fade-up"]'));

    const isVisible = (el) => {
      const style = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      const dashOffset = parseFloat(style.strokeDashoffset || '0') || 0;
      return {
        opacity: parseFloat(style.opacity || '1'),
        display: style.display,
        visibility: style.visibility,
        width: rect.width,
        height: rect.height,
        dashOffset,
      };
    };

    const hiddenSparkLines = sparkLines.filter((el) => {
      const v = isVisible(el);
      return v.opacity < 0.99 || v.visibility === 'hidden' || v.width <= 0 || v.dashOffset > 0;
    }).length;

    const hiddenSparkAreas = sparkAreas.filter((el) => isVisible(el).opacity < 0.99).length;
    const hiddenSparkDots = sparkDots.filter((el) => {
      const v = isVisible(el);
      return v.opacity < 0.99 || v.width <= 0 || v.height <= 0;
    }).length;

    const hiddenMapDots = mapDots.filter((el) => {
      const v = isVisible(el);
      return v.opacity < 0.99 || v.visibility === 'hidden' || v.width <= 0 || v.height <= 0;
    }).length;

    const hiddenReveals = reveals.filter((el) => isVisible(el).opacity < 0.99).length;

    return {
      sparkLinesCount: sparkLines.length,
      sparkDotsCount: sparkDots.length,
      mapDotsCount: mapDots.length,
      revealsCount: reveals.length,
      hiddenSparkLines,
      hiddenSparkAreas,
      hiddenSparkDots,
      hiddenMapDots,
      hiddenReveals,
      scrollY: window.scrollY,
    };
  });

  assert.equal(result.sparkLinesCount, 3, `[${label}] Expected 3 sparklines, got ${result.sparkLinesCount}`);
  assert.equal(result.sparkDotsCount, 3, `[${label}] Expected 3 sparkline anchor dots, got ${result.sparkDotsCount}`);
  assert.ok(result.mapDotsCount >= 40, `[${label}] Expected >= 40 active map dots, got ${result.mapDotsCount}`);
  assert.equal(result.hiddenSparkLines, 0, `[${label}] Hidden sparkline paths: ${result.hiddenSparkLines}`);
  assert.equal(result.hiddenSparkAreas, 0, `[${label}] Hidden sparkline areas: ${result.hiddenSparkAreas}`);
  assert.equal(result.hiddenSparkDots, 0, `[${label}] Hidden sparkline dots: ${result.hiddenSparkDots}`);
  assert.equal(result.hiddenMapDots, 0, `[${label}] Hidden map dots: ${result.hiddenMapDots}`);
  assert.equal(result.hiddenReveals, 0, `[${label}] Hidden reveal blocks: ${result.hiddenReveals}`);
  return result;
}

const tmpShot = path.join(os.tmpdir(), `benin-agromarket-no-hidden-${process.pid}.png`);

try {
  // 1. JavaScript DISABLED
  const noJsCtx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    javaScriptEnabled: false,
  });
  const noJsPage = await noJsCtx.newPage();
  await noJsPage.goto(`${origin}${BASE_MOUNT}/`, { waitUntil: 'load' });
  const noJsStats = await assertSparklinesAndMapVisible(noJsPage, 'JS disabled (FR)');
  await noJsCtx.close();

  // 2. JavaScript ENABLED (without scrolling first) + full-page screenshot
  const jsCtx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    javaScriptEnabled: true,
  });
  const jsPage = await jsCtx.newPage();
  await jsPage.goto(`${origin}${BASE_MOUNT}/`, { waitUntil: 'networkidle' });
  const jsStats = await assertSparklinesAndMapVisible(jsPage, 'JS enabled before scroll (FR)');
  assert.equal(jsStats.scrollY, 0, 'Expected scrollY === 0 before fullPage screenshot');

  const pngBuf = await jsPage.screenshot({ path: tmpShot, fullPage: true });
  assert.ok(pngBuf.length > 20_000, `Expected non-trivial full-page screenshot, got ${pngBuf.length} bytes`);

  // Also check Print emulation keeps everything visible
  await jsPage.emulateMedia({ media: 'print' });
  await assertSparklinesAndMapVisible(jsPage, 'Print media (FR)');
  await jsCtx.close();

  // 3. Reduced motion enabled
  const rmCtx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    reducedMotion: 'reduce',
  });
  const rmPage = await rmCtx.newPage();
  await rmPage.goto(`${origin}${BASE_MOUNT}/en/`, { waitUntil: 'networkidle' });
  await assertSparklinesAndMapVisible(rmPage, 'Reduced motion (EN)');
  await rmCtx.close();

  console.log(
    `[No Hidden Content Test] PASS: JS-disabled (${noJsStats.mapDotsCount} dots, ${noJsStats.sparkLinesCount} sparklines), JS-enabled full-page (${jsStats.mapDotsCount} dots, ${jsStats.sparkLinesCount} sparklines), print, and reduced-motion all visible.`
  );
} finally {
  if (fs.existsSync(tmpShot)) fs.unlinkSync(tmpShot);
  await browser.close();
  server.close();
}

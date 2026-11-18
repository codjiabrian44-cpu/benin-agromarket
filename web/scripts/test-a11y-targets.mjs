import assert from 'node:assert/strict';
import path from 'node:path';
import { loadPlaywright, startStaticMountServer } from './playwright-loader.mjs';

const distDir = path.resolve(import.meta.dirname, '..', 'dist');
const BASE_MOUNT = '/benin-agromarket';

const { chromium } = await loadPlaywright();
const { server, origin } = await startStaticMountServer(distDir, BASE_MOUNT);
const browser = await chromium.launch({ headless: true });

try {
  for (const vp of [
    { name: 'desktop', width: 1440, height: 900 },
    { name: 'mobile', width: 390, height: 844 },
  ]) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await ctx.newPage();

    // 1. Home FR: 3 sparkline tables, South zoom table, and >= 44x44 touch hit areas
    await page.goto(`${origin}${BASE_MOUNT}/`, { waitUntil: 'networkidle' });
    const homeCheck = await page.evaluate(() => {
      const sparkDrawers = Array.from(document.querySelectorAll('.stories-section details.sparkline-drawer'));
      const sparkRows = sparkDrawers.map((d) => d.querySelectorAll('tbody tr').length);
      const southDrawers = Array.from(
        document.querySelectorAll('[data-map-panel="maize_white"] details.south-zoom-drawer')
      );
      const southRows = southDrawers[0]?.querySelectorAll('tbody tr').length ?? 0;

      const smallTargets = [];
      const activePanel = document.querySelector('[data-map-panel="maize_white"]');
      const targets = [
        ...Array.from(document.querySelectorAll('.details-tooltip-trigger')).filter(
          (el) => !el.closest('[hidden]')
        ),
        ...Array.from(document.querySelectorAll('.tooltip-term')).filter(
          (el) => !el.closest('[hidden]')
        ),
        ...Array.from(activePanel?.querySelectorAll('.map-hit-target') ?? []),
      ];

      for (const el of targets) {
        const r = el.getBoundingClientRect();
        if (r.width < 43.9 || r.height < 43.9) {
          smallTargets.push({
            cls: el.getAttribute('class') || el.tagName,
            w: Math.round(r.width * 10) / 10,
            h: Math.round(r.height * 10) / 10,
          });
        }
      }

      return { sparkDrawers: sparkDrawers.length, sparkRows, southRows, smallTargets };
    });

    assert.equal(homeCheck.sparkDrawers, 3, `[${vp.name}] Expected 3 sparkline <details> tables`);
    assert.deepEqual(homeCheck.sparkRows, [36, 36, 36], `[${vp.name}] Expected 36 rows per sparkline table`);
    assert.equal(homeCheck.southRows, 28, `[${vp.name}] Expected 28 southern markets in South zoom table`);
    assert.equal(
      homeCheck.smallTargets.length,
      0,
      `[${vp.name}] Found targets < 44x44: ${JSON.stringify(homeCheck.smallTargets.slice(0, 5))}`
    );

    // 2. Explorer: seasonality <details> table + aria-label updates on client interaction
    await page.goto(`${origin}${BASE_MOUNT}/explorer`, { waitUntil: 'networkidle' });
    const expBefore = await page.evaluate(() => ({
      priceAria: document.getElementById('explorer-price-svg')?.getAttribute('aria-label') || '',
      seasonAria: document.getElementById('explorer-season-svg')?.getAttribute('aria-label') || '',
      seasonRows: document.querySelectorAll('#exp-season-table-body tr').length,
    }));
    assert.equal(expBefore.seasonRows, 12, `[${vp.name}] Expected 12 seasonality rows on Explorer`);

    await page.click('button[data-product="tomatoes"]');
    await page.waitForTimeout(250);
    const expAfter = await page.evaluate(() => ({
      priceAria: document.getElementById('explorer-price-svg')?.getAttribute('aria-label') || '',
      seasonAria: document.getElementById('explorer-season-svg')?.getAttribute('aria-label') || '',
      seasonRows: document.querySelectorAll('#exp-season-table-body tr').length,
    }));
    assert.equal(expAfter.seasonRows, 12, `[${vp.name}] Expected 12 seasonality rows after switch`);
    assert.notEqual(expAfter.priceAria, expBefore.priceAria, `[${vp.name}] Explorer price aria-label should update`);
    assert.notEqual(expAfter.seasonAria, expBefore.seasonAria, `[${vp.name}] Explorer season aria-label should update`);

    // 3. Forecast: aria-label updates on product/horizon switch
    await page.goto(`${origin}${BASE_MOUNT}/previsions`, { waitUntil: 'networkidle' });
    const fcBefore = await page.getAttribute('#fc-chart-svg', 'aria-label');
    await page.click('button[data-horizon="1"]');
    await page.waitForTimeout(100);
    const fcAfterHorizon = await page.getAttribute('#fc-chart-svg', 'aria-label');
    assert.notEqual(fcAfterHorizon, fcBefore, `[${vp.name}] Forecast aria-label should update on horizon switch`);

    await page.click('button[data-product="yam_white"]');
    await page.waitForTimeout(250);
    const fcAfterProd = await page.getAttribute('#fc-chart-svg', 'aria-label');
    assert.notEqual(fcAfterProd, fcAfterHorizon, `[${vp.name}] Forecast aria-label should update on product switch`);

    await ctx.close();
  }

  console.log(
    '[A11y Targets & Alternatives Test] PASS: Sparkline & seasonality tables, dynamic SVG aria-labels, South zoom table, and >= 44x44px hit targets verified on desktop & mobile.'
  );
} finally {
  await browser.close();
  server.close();
}

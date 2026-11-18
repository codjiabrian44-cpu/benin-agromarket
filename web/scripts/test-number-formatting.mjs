import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {
  formatDecimal,
  formatPct,
  formatSignedPct,
  roundHalfAway,
} from '../src/lib/format.mjs';

const webRoot = path.resolve(import.meta.dirname, '..');
const distDir = path.join(webRoot, 'dist');
const homeSummary = JSON.parse(
  fs.readFileSync(path.join(webRoot, 'src', 'data', 'generated', 'home-summary.json'), 'utf8')
);
const methodTables = JSON.parse(
  fs.readFileSync(path.join(webRoot, 'src', 'data', 'generated', 'method-tables.json'), 'utf8')
);

function stripNonVisible(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ');
}

// 1. Verify French pages never have English decimal dots before % or missing space before %
const frPages = ['index.html', 'explorer/index.html', 'previsions/index.html', 'methode/index.html'];
for (const rel of frPages) {
  const html = fs.readFileSync(path.join(distDir, rel), 'utf8');
  const visible = stripNonVisible(html);
  const dotPctMatch = visible.match(/[+-]?\d+\.\d+\s*%/);
  assert.equal(
    dotPctMatch,
    null,
    `Found English decimal percentage "${dotPctMatch?.[0]}" in French page ${rel}`
  );
  const unspacedPctMatch = visible.match(/\d%/);
  assert.equal(
    unspacedPctMatch,
    null,
    `Found unspaced percentage "${unspacedPctMatch?.[0]}" in French page ${rel}`
  );
}

// 2. Verify English pages never have French decimal commas or spaces before %
const enPages = [
  'en/index.html',
  'en/explorer/index.html',
  'en/forecast/index.html',
  'en/method/index.html',
];
for (const rel of enPages) {
  const html = fs.readFileSync(path.join(distDir, rel), 'utf8');
  const visible = stripNonVisible(html);
  const commaPctMatch = visible.match(/\d,\d+\s*%/);
  assert.equal(
    commaPctMatch,
    null,
    `Found French decimal comma percentage "${commaPctMatch?.[0]}" in English page ${rel}`
  );
  const spacedPctMatch = visible.match(/\d\s+%/);
  assert.equal(
    spacedPctMatch,
    null,
    `Found French space-before-percent "${spacedPctMatch?.[0]}" in English page ${rel}`
  );
}

// 3. Verify every product x horizon test metric rounds identically in home-summary, method-tables, and built HTML
const SLUG_TO_COMMODITY = {
  maize_white: 'Maize (white)',
  tomatoes: 'Tomatoes',
  yam_white: 'Yam (white)',
};

const frMethodHtml = stripNonVisible(
  fs.readFileSync(path.join(distDir, 'methode/index.html'), 'utf8')
);
const enMethodHtml = stripNonVisible(
  fs.readFileSync(path.join(distDir, 'en/method/index.html'), 'utf8')
);
const frHomeHtml = stripNonVisible(fs.readFileSync(path.join(distDir, 'index.html'), 'utf8'));
const enHomeHtml = stripNonVisible(fs.readFileSync(path.join(distDir, 'en/index.html'), 'utf8'));
const frForecastHtml = stripNonVisible(
  fs.readFileSync(path.join(distDir, 'previsions/index.html'), 'utf8')
);
const enForecastHtml = stripNonVisible(
  fs.readFileSync(path.join(distDir, 'en/forecast/index.html'), 'utf8')
);

for (const [slug, prod] of Object.entries(homeSummary.products)) {
  const commodity = SLUG_TO_COMMODITY[slug];
  for (const h of [1, 2, 3]) {
    const hKey = `h${h}`;
    const acc = prod.backtest_accuracy.by_horizon_test[hKey];
    const rel = prod.reliability_by_horizon[hKey];
    const tableRow = methodTables.champion_selection.find(
      (r) => r['Product'] === commodity && r['Horizon'] === `h=${h}m`
    );
    assert.ok(tableRow, `Missing champion_selection row for ${commodity} ${hKey}`);

    const expectedMapeFr = formatPct(acc.mape, 'fr', 1);
    const expectedMapeEn = formatPct(acc.mape, 'en', 1);
    const csvMapeNum = parseFloat(String(tableRow['Test MAPE %']).replace('%', ''));
    assert.equal(
      roundHalfAway(acc.mape, 1),
      roundHalfAway(csvMapeNum, 1),
      `MAPE rounding mismatch between home-summary (${acc.mape}) and CSV table (${csvMapeNum}) for ${slug} ${hKey}`
    );
    assert.ok(
      acc.reliability_note_fr.includes(expectedMapeFr) &&
        rel.note_fr.includes(expectedMapeFr),
      `French note for ${slug} ${hKey} must contain ${expectedMapeFr}; got "${acc.reliability_note_fr}"`
    );
    assert.ok(
      acc.reliability_note_en.includes(expectedMapeEn) &&
        rel.note_en.includes(expectedMapeEn),
      `English note for ${slug} ${hKey} must contain ${expectedMapeEn}; got "${acc.reliability_note_en}"`
    );
    assert.ok(
      frMethodHtml.includes(expectedMapeFr) && enMethodHtml.includes(expectedMapeEn),
      `Method page must display ${expectedMapeFr} / ${expectedMapeEn} for ${slug} ${hKey}`
    );
  }

  // Horizon-3 headline on Home & Tomato warning on Forecast must match Method table identically
  const h3Mape = prod.backtest_accuracy.by_horizon_test.h3.mape;
  const h3MapeFr = formatPct(h3Mape, 'fr', 1);
  const h3MapeEn = formatPct(h3Mape, 'en', 1);
  assert.ok(
    frHomeHtml.includes(h3MapeFr) && enHomeHtml.includes(h3MapeEn),
    `Home page must display ${h3MapeFr} / ${h3MapeEn} for ${slug} h3`
  );
  assert.ok(
    frForecastHtml.includes(h3MapeFr) && enForecastHtml.includes(h3MapeEn),
    `Forecast page must display ${h3MapeFr} / ${h3MapeEn} for ${slug} h3`
  );

  // Home Section 2 seasonality spread_pct must be localized in FR and EN
  const spreadNum = prod.seasonality.spread_pct_num;
  assert.ok(
    frHomeHtml.includes(formatSignedPct(spreadNum, 'fr', 1)),
    `French Home page missing localized spread_pct ${formatSignedPct(spreadNum, 'fr', 1)} for ${slug}`
  );
  assert.ok(
    enHomeHtml.includes(formatSignedPct(spreadNum, 'en', 1)),
    `English Home page missing localized spread_pct ${formatSignedPct(spreadNum, 'en', 1)} for ${slug}`
  );
}

// Explicit regression check for Yam h=3 (19.45 -> 19,5 % / 19.5%, never 19,4 % / 19.4%)
for (const text of [frHomeHtml, frForecastHtml, frMethodHtml]) {
  assert.equal(text.includes('19,4 %'), false, 'Found stale 19,4 % rounding on French page');
}
for (const text of [enHomeHtml, enForecastHtml, enMethodHtml]) {
  assert.equal(text.includes('19.4%'), false, 'Found stale 19.4% rounding on English page');
}

// Verify Dantokpa h3 test MAPE on Home matches Forecast page
const dantokpaMaizeH3 = homeSummary.products.maize_white.tier1_markets_map.find(
  (m) => m.market_name === 'Dantokpa'
).h3_test_mape;
assert.ok(frHomeHtml.includes(formatPct(dantokpaMaizeH3, 'fr', 1)));
assert.ok(enHomeHtml.includes(formatPct(dantokpaMaizeH3, 'en', 1)));
assert.ok(frForecastHtml.includes(formatPct(dantokpaMaizeH3, 'fr', 1)));
assert.ok(enForecastHtml.includes(formatPct(dantokpaMaizeH3, 'en', 1)));

console.log('[Number Formatting Test] PASS: Shared rounding and locale formatting verified across all pages.');

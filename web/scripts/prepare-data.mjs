/**
 * Build-time data validator, splitter, and self-hosted font/license bundler.
 *
 * Per `docs/PHASE3_BRIEF.md`:
 * - Validates `web/public/data/forecasts.json` at build time before generating pages.
 * - Splits `forecasts.json` + generated CSV tables in `docs/tables/` into:
 *   1. `web/public/data/home-summary.json` (compact summary for Home `/` and `/en/`, never shipping all 111 full series)
 *   2. `web/public/data/product-maize_white.json` (49 Tier-1 series + monthly Tier-1 median reference)
 *   3. `web/public/data/product-tomatoes.json` (43 Tier-1 series + monthly Tier-1 median reference)
 *   4. `web/public/data/product-yam_white.json` (19 Tier-1 series + monthly Tier-1 median reference)
 *   5. `web/public/data/method-tables.json` (script-generated Phase 1/2 tables for `/methode` and `/en/method`)
 * - Copies self-hosted variable Latin `.woff2` fonts (`Fraunces` and `Instrument Sans`, 65.15 KiB total <= 70 KB budget)
 *   and their SIL Open Font License (`OFL-1.1`) files into `web/public/fonts/`.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, '..');
const PROJECT_ROOT = path.resolve(WEB_ROOT, '..');
const PUBLIC_DATA_DIR = path.join(WEB_ROOT, 'public', 'data');
const PUBLIC_FONTS_DIR = path.join(WEB_ROOT, 'public', 'fonts');
const SRC_GEN_DIR = path.join(WEB_ROOT, 'src', 'data', 'generated');
const TABLES_DIR = path.join(PROJECT_ROOT, 'docs', 'tables');

function parseCsv(csvText) {
  const lines = csvText.replace(/\r\n/g, '\n').trim().split('\n');
  if (lines.length === 0) return [];
  const parseLine = (line) => {
    const out = [];
    let cur = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (ch === '"') {
        if (inQuotes && line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === ',' && !inQuotes) {
        out.push(cur);
        cur = '';
      } else {
        cur += ch;
      }
    }
    out.push(cur);
    return out;
  };
  const headers = parseLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = parseLine(line);
    const row = {};
    headers.forEach((h, idx) => {
      row[h.trim()] = (cells[idx] ?? '').trim();
    });
    return row;
  });
}

function median(values) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((acc, v) => acc + v, 0) / values.length;
}

function round(val, digits = 1) {
  const f = 10 ** digits;
  return Math.round(val * f) / f;
}

function copySelfHostedFontsAndLicenses() {
  fs.mkdirSync(PUBLIC_FONTS_DIR, { recursive: true });
  const frauncesDir = path.join(WEB_ROOT, 'node_modules', '@fontsource-variable', 'fraunces');
  const instrumentDir = path.join(WEB_ROOT, 'node_modules', '@fontsource-variable', 'instrument-sans');

  const assets = [
    {
      src: path.join(frauncesDir, 'files', 'fraunces-latin-wght-normal.woff2'),
      dest: path.join(PUBLIC_FONTS_DIR, 'fraunces-latin-wght-normal.woff2'),
    },
    {
      src: path.join(frauncesDir, 'LICENSE'),
      dest: path.join(PUBLIC_FONTS_DIR, 'FRAUNCES-LICENSE-OFL.txt'),
    },
    {
      src: path.join(instrumentDir, 'files', 'instrument-sans-latin-wght-normal.woff2'),
      dest: path.join(PUBLIC_FONTS_DIR, 'instrument-sans-latin-wght-normal.woff2'),
    },
    {
      src: path.join(instrumentDir, 'LICENSE'),
      dest: path.join(PUBLIC_FONTS_DIR, 'INSTRUMENT-SANS-LICENSE-OFL.txt'),
    },
  ];

  let totalFontBytes = 0;
  for (const item of assets) {
    if (!fs.existsSync(item.src)) {
      throw new Error(`[prepare-data] Missing font/license file: ${item.src}`);
    }
    fs.copyFileSync(item.src, item.dest);
    if (item.dest.endsWith('.woff2')) {
      totalFontBytes += fs.statSync(item.dest).size;
    }
  }
  const totalFontKiB = totalFontBytes / 1024;
  if (totalFontKiB > 70.0) {
    throw new Error(
      `[prepare-data] Font budget exceeded: ${totalFontKiB.toFixed(2)} KiB > 70.0 KiB limit`
    );
  }
  console.log(
    `[prepare-data] Self-hosted variable woff2 fonts + OFL licenses copied (${totalFontBytes} bytes / ${totalFontKiB.toFixed(2)} KiB <= 70 KB budget).`
  );
}

function validateForecastsExport(payload) {
  if (payload.as_of_date !== '2026-09-15' || payload.currency !== 'XOF' || payload.unit !== 'KG') {
    throw new Error('[prepare-data] Invalid top-level metadata in forecasts.json');
  }
  const series = payload.series || [];
  if (series.length !== 111) {
    throw new Error(`[prepare-data] Expected 111 Tier-1 series, found ${series.length}`);
  }
  const marketsCov = payload.markets_coverage || [];
  if (marketsCov.length !== 51) {
    throw new Error(`[prepare-data] Expected 51 active markets in markets_coverage, found ${marketsCov.length}`);
  }
  const expectedCounts = { maize_white: 49, tomatoes: 43, yam_white: 19 };
  for (const [slug, expCount] of Object.entries(expectedCounts)) {
    const actual = series.filter((s) => s.product_slug === slug).length;
    if (actual !== expCount) {
      throw new Error(`[prepare-data] Product ${slug}: expected ${expCount} series, got ${actual}`);
    }
    const prodMeta = payload.products?.[slug];
    if (!prodMeta || !prodMeta.reliability_by_horizon) {
      throw new Error(`[prepare-data] Missing reliability_by_horizon on product ${slug}`);
    }
    for (const hKey of ['h1', 'h2', 'h3']) {
      const rel = prodMeta.reliability_by_horizon[hKey];
      if (!rel || !rel.status || !rel.note_fr || !rel.note_en) {
        throw new Error(`[prepare-data] Missing reliability note on ${slug}/${hKey}`);
      }
    }
  }

  for (const s of series) {
    if (!Array.isArray(s.forecasts) || s.forecasts.length !== 3) {
      throw new Error(`[prepare-data] Series ${s.series_id} does not have 3 forecast horizons`);
    }
    for (const fc of s.forecasts) {
      const vals = [fc.low_90, fc.low_80, fc.point_forecast, fc.high_80, fc.high_90];
      if (vals.some((v) => typeof v !== 'number' || !Number.isFinite(v) || v <= 0)) {
        throw new Error(`[prepare-data] Invalid forecast number in ${s.series_id} h=${fc.horizon_months}`);
      }
      if (
        !(
          fc.low_90 <= fc.low_80 + 1e-6 &&
          fc.low_80 <= fc.point_forecast + 1e-6 &&
          fc.point_forecast <= fc.high_80 + 1e-6 &&
          fc.high_80 <= fc.high_90 + 1e-6
        )
      ) {
        throw new Error(`[prepare-data] Interval ordering violation in ${s.series_id} h=${fc.horizon_months}`);
      }
    }
  }
}

function buildSplitDataFiles() {
  const forecastsPath = path.join(PUBLIC_DATA_DIR, 'forecasts.json');
  if (!fs.existsSync(forecastsPath)) {
    throw new Error(`[prepare-data] Missing ${forecastsPath}`);
  }
  const payload = JSON.parse(fs.readFileSync(forecastsPath, 'utf-8'));
  validateForecastsExport(payload);

  // Load supplementary generated CSV tables from docs/tables/
  const seasRows = parseCsv(
    fs.readFileSync(path.join(TABLES_DIR, 'eda_seasonality_profile.csv'), 'utf-8')
  );
  const edaSumRows = parseCsv(
    fs.readFileSync(path.join(TABLES_DIR, 'eda_summary_by_product.csv'), 'utf-8')
  );
  const champRows = parseCsv(
    fs.readFileSync(path.join(TABLES_DIR, 'phase2_champion_selection.csv'), 'utf-8')
  );
  const rankRows = parseCsv(
    fs.readFileSync(path.join(TABLES_DIR, 'phase2_holdout_rank_comparison.csv'), 'utf-8')
  );
  const weatherRows = parseCsv(
    fs.readFileSync(path.join(TABLES_DIR, 'phase2_weather_ablation.csv'), 'utf-8')
  );
  const calibRows = parseCsv(
    fs.readFileSync(path.join(TABLES_DIR, 'phase2_interval_calibration.csv'), 'utf-8')
  );
  const covMarketRows = parseCsv(
    fs.readFileSync(path.join(TABLES_DIR, 'coverage_by_market.csv'), 'utf-8')
  );

  const monthAbbrevToNum = {
    Jan: 1,
    Feb: 2,
    Mar: 3,
    Apr: 4,
    May: 5,
    Jun: 6,
    Jul: 7,
    Aug: 8,
    Sep: 9,
    Oct: 10,
    Nov: 11,
    Dec: 12,
  };
  const monthCols = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  const parseMonthIndexCell = (cell) => {
    const m = /^([A-Za-z]{3})\s*\(([0-9.]+)\)$/.exec(cell);
    if (!m) return { month_num: 1, index: 100.0 };
    return {
      month_num: monthAbbrevToNum[m[1]] || 1,
      index: parseFloat(m[2]),
    };
  };

  const parseSpreadCell = (cell) => {
    const m = /^([0-9.]+)\s*pts\s*\(([^)]+)\)$/.exec(cell);
    if (!m) return { spread_pts: 0, spread_pct: cell };
    return {
      spread_pts: parseFloat(m[1]),
      spread_pct: m[2],
    };
  };

  const metadata = {
    project: payload.project,
    as_of_date: payload.as_of_date,
    forecast_horizons_months: payload.forecast_horizons_months,
    forecast_target_dates: payload.forecast_target_dates,
    currency: payload.currency,
    unit: payload.unit,
    price_type: 'Retail',
    total_tier1_series: payload.series.length,
    active_markets_count: payload.markets_coverage.length,
    evaluation_protocol: payload.evaluation_protocol,
  };

  const productSlugs = ['maize_white', 'tomatoes', 'yam_white'];
  const homeProducts = {};

  fs.mkdirSync(SRC_GEN_DIR, { recursive: true });

  for (const slug of productSlugs) {
    const prodMeta = payload.products[slug];
    const commodity = prodMeta.commodity;
    const prodSeries = payload.series.filter((s) => s.product_slug === slug);

    // Compute monthly Tier-1 median and mean across all Tier-1 markets for this product
    const byDatePrices = new Map();
    for (const s of prodSeries) {
      for (const pt of s.history) {
        if (pt.date >= '2019-01-15' && typeof pt.price === 'number') {
          if (!byDatePrices.has(pt.date)) byDatePrices.set(pt.date, []);
          byDatePrices.get(pt.date).push(pt.price);
        }
      }
    }
    const sortedDates = [...byDatePrices.keys()].sort();
    const nationalMedianSeries = sortedDates.map((d) => {
      const arr = byDatePrices.get(d);
      return {
        date: d,
        median_price: round(median(arr), 1),
        mean_price: round(mean(arr), 1),
        markets_reporting: arr.length,
      };
    });

    // Latest national snapshot across Tier-1 markets
    const latestMarketPoints = prodSeries.map((s) => {
      const f1 = s.forecasts.find((f) => f.horizon_months === 1);
      const f3 = s.forecasts.find((f) => f.horizon_months === 3);
      return {
        market_id: s.market_id,
        market_name: s.market,
        department: s.admin1,
        commune: s.admin2,
        agro_zone: s.agro_zone,
        latitude: s.latitude,
        longitude: s.longitude,
        observed_months_2019_2026: s.obs_months_2019_2026,
        completeness_pct: s.completeness_2019_2026_pct,
        last_observed_date: s.last_observed_date,
        last_observed_price: s.last_observed_price,
        h1_forecast: f1.point_forecast,
        h1_low_80: f1.low_80,
        h1_high_80: f1.high_80,
        h1_change_pct: f1.change_vs_last_pct,
        h3_forecast: f3.point_forecast,
        h3_low_80: f3.low_80,
        h3_high_80: f3.high_80,
        h3_change_pct: f3.change_vs_last_pct,
        holdout_mae: s.backtest_accuracy?.test_overall?.mae ?? null,
        holdout_mape: s.backtest_accuracy?.test_overall?.mape ?? null,
      };
    });

    const latestPrices = latestMarketPoints.map((m) => m.last_observed_price);
    const natMedLatest = round(median(latestPrices), 1);
    const natMeanLatest = round(mean(latestPrices), 1);
    const sortedByPrice = [...latestMarketPoints].sort(
      (a, b) => a.last_observed_price - b.last_observed_price
    );
    const minMarket = sortedByPrice[0];
    const maxMarket = sortedByPrice[sortedByPrice.length - 1];

    const tier1MarketsMap = latestMarketPoints
      .map((m) => ({
        ...m,
        national_median_price: natMedLatest,
        diff_vs_median_pct: round(((m.last_observed_price - natMedLatest) / natMedLatest) * 100, 1),
      }))
      .sort((a, b) => b.latitude - a.latitude);

    // National seasonality from eda_seasonality_profile.csv
    const natSeasRow = seasRows.find(
      (r) => r['Product'] === commodity && r['Agro-Ecological Zone'] === 'All Tier-1 (National)'
    );
    const zoneSeasRows = seasRows.filter((r) => r['Product'] === commodity);
    const troughParsed = parseMonthIndexCell(natSeasRow?.['Trough Month (Index)'] || '');
    const peakParsed = parseMonthIndexCell(natSeasRow?.['Peak Month (Index)'] || '');
    const spreadParsed = parseSpreadCell(natSeasRow?.['Peak-to-Trough Spread (Index pts / %)'] || '');

    // EDA summary row for Tier-1 Modeling Window
    const edaRow = edaSumRows.find(
      (r) => r['Product'] === commodity && r['Regime / Scope'].startsWith('Tier-1 Modeling Window')
    );

    // Dantokpa series (market_id "2279" or market === "Dantokpa")
    const dantokpaFull = prodSeries.find((s) => s.market_id === '2279' || s.market === 'Dantokpa');
    if (!dantokpaFull) {
      throw new Error(`[prepare-data] Missing Dantokpa series for ${slug}`);
    }
    const dantokpaHistory2019 = dantokpaFull.history.filter((pt) => pt.date >= '2019-01-15');

    homeProducts[slug] = {
      commodity,
      product_slug: slug,
      label_fr: prodMeta.label_fr,
      label_en: prodMeta.label_en,
      tier1_markets_count: prodMeta.tier1_markets_count,
      observed_market_months: parseInt(edaRow?.['Obs'] || '0', 10),
      panel_mean_price: parseFloat(edaRow?.['Mean (XOF/kg)'] || '0'),
      panel_median_price: parseFloat(edaRow?.['Median'] || '0'),
      panel_cv_pct: edaRow?.['CV %'] || '',
      cagr_2019_2026: edaRow?.['CAGR % (6.75 yr)'] || '',
      champions_by_horizon: prodMeta.champions_by_horizon,
      backtest_accuracy: prodMeta.backtest_accuracy,
      reliability_by_horizon: prodMeta.reliability_by_horizon,
      seasonality: {
        trough_month_num: troughParsed.month_num,
        trough_index: troughParsed.index,
        peak_month_num: peakParsed.month_num,
        peak_index: peakParsed.index,
        spread_pts: spreadParsed.spread_pts,
        spread_pct: spreadParsed.spread_pct,
        monthly_indices: monthCols.map((mc, idx) => ({
          month_num: idx + 1,
          index: parseFloat(natSeasRow?.[mc] || '100'),
        })),
      },
      latest_national_stats: {
        as_of_date: payload.as_of_date,
        median_price: natMedLatest,
        mean_price: natMeanLatest,
        min_price: minMarket.last_observed_price,
        min_market_name: minMarket.market_name,
        min_department: minMarket.department,
        max_price: maxMarket.last_observed_price,
        max_market_name: maxMarket.market_name,
        max_department: maxMarket.department,
        max_min_ratio: round(maxMarket.last_observed_price / minMarket.last_observed_price, 2),
        sparkline_36m: nationalMedianSeries.slice(-36),
      },
      dantokpa: {
        market_id: dantokpaFull.market_id,
        market_name: dantokpaFull.market,
        department: dantokpaFull.admin1,
        commune: dantokpaFull.admin2,
        agro_zone: dantokpaFull.agro_zone,
        latitude: dantokpaFull.latitude,
        longitude: dantokpaFull.longitude,
        observed_months_2019_2026: dantokpaFull.obs_months_2019_2026,
        completeness_pct: dantokpaFull.completeness_2019_2026_pct,
        last_observed_date: dantokpaFull.last_observed_date,
        last_observed_price: dantokpaFull.last_observed_price,
        champions_by_horizon: dantokpaFull.model_used,
        reliability_by_horizon: dantokpaFull.reliability_by_horizon,
        backtest_accuracy: dantokpaFull.backtest_accuracy,
        history: dantokpaHistory2019,
        recent_backtest_h1: dantokpaFull.recent_backtest_h1,
        forecasts: dantokpaFull.forecasts,
      },
      tier1_markets_map: tier1MarketsMap,
    };

    // Per-product split file (`web/public/data/product-<slug>.json`)
    const productFilePayload = {
      metadata,
      product: homeProducts[slug],
      seasonality_by_zone: zoneSeasRows.map((zr) => ({
        zone: zr['Agro-Ecological Zone'],
        tier1_markets: parseInt(zr['Tier-1 Markets'], 10),
        obs: parseInt(zr['Obs'], 10),
        trough_raw: zr['Trough Month (Index)'],
        peak_raw: zr['Peak Month (Index)'],
        spread_raw: zr['Peak-to-Trough Spread (Index pts / %)'],
        monthly_indices: monthCols.map((mc, idx) => ({
          month_num: idx + 1,
          index: parseFloat(zr[mc] || '100'),
        })),
      })),
      national_median_series: nationalMedianSeries,
      series: prodSeries,
    };

    const prodOutPath = path.join(PUBLIC_DATA_DIR, `product-${slug}.json`);
    const prodGenPath = path.join(SRC_GEN_DIR, `product-${slug}.json`);
    const prodJsonStr = JSON.stringify(productFilePayload);
    fs.writeFileSync(prodOutPath, prodJsonStr, 'utf-8');
    fs.writeFileSync(prodGenPath, prodJsonStr, 'utf-8');
  }

  // Home summary file (`web/public/data/home-summary.json`)
  const homeSummaryPayload = {
    metadata,
    products: homeProducts,
  };
  const homeSummaryStr = JSON.stringify(homeSummaryPayload);
  fs.writeFileSync(path.join(PUBLIC_DATA_DIR, 'home-summary.json'), homeSummaryStr, 'utf-8');
  fs.writeFileSync(path.join(SRC_GEN_DIR, 'home-summary.json'), homeSummaryStr, 'utf-8');

  // Method & Limits tables file (`web/public/data/method-tables.json`)
  const methodTablesPayload = {
    metadata,
    champion_selection: champRows,
    holdout_rank_comparison: rankRows,
    weather_ablation_pooled: weatherRows.filter((r) => r['Horizon'] === 'All (h=1..3)'),
    weather_ablation_all: weatherRows,
    interval_calibration_champions: calibRows.filter((r) =>
      r['Model / Role'].startsWith('Selected Champion')
    ),
    eda_summary: edaSumRows,
    markets_coverage: payload.markets_coverage,
    coverage_by_market_rows: covMarketRows,
  };
  const methodStr = JSON.stringify(methodTablesPayload);
  fs.writeFileSync(path.join(PUBLIC_DATA_DIR, 'method-tables.json'), methodStr, 'utf-8');
  fs.writeFileSync(path.join(SRC_GEN_DIR, 'method-tables.json'), methodStr, 'utf-8');

  console.log(
    `[prepare-data] Validated forecasts.json & wrote split files: home-summary.json (${(Buffer.byteLength(homeSummaryStr) / 1024).toFixed(1)} KiB), product-maize_white.json, product-tomatoes.json, product-yam_white.json, method-tables.json.`
  );
}

copySelfHostedFontsAndLicenses();
buildSplitDataFiles();

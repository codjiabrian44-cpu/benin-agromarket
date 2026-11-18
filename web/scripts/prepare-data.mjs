/**
 * Build-time data validator, splitter, and self-hosted font/license bundler.
 *
 * Per `docs/PHASE3_BRIEF.md` and `AGENTS.md`:
 * - Validates `web/public/data/forecasts.json` at build time before generating pages.
 * - Ensures all 93 calendar months (`2019-01-15..2026-09-15`) are represented on the monthly
 *   grid with `price: number | null` and `is_observed: boolean` so `d3.line().defined()` breaks
 *   cleanly at every unobserved month (`2020-02`, `2021-07`, etc.).
 * - Ensures plain-language bilingual reliability notes (`note_fr`, `note_en`) free of internal
 *   model identifiers or technical jargon.
 * - Splits `forecasts.json` + generated CSV tables in `docs/tables/` into:
 *   1. `web/public/data/home-summary.json` (compact summary for Home `/` and `/en/`, never shipping all 111 full series)
 *   2. `web/public/data/product-maize_white.json` (49 well-tracked series + monthly median reference)
 *   3. `web/public/data/product-tomatoes.json` (43 well-tracked series + monthly median reference)
 *   4. `web/public/data/product-yam_white.json` (19 well-tracked series + monthly median reference)
 *   5. `web/public/data/method-tables.json` (script-generated Phase 1/2 tables for `/methode` and `/en/method`)
 * - Copies self-hosted variable Latin `.woff2` fonts (`Fraunces` and `Instrument Sans`, 65.15 KiB total <= 70 KB budget)
 *   and their SIL Open Font License (`OFL-1.1`) files into `web/public/fonts/`.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  formatDecimal,
  formatPct,
  formatSignedPct,
  roundHalfAway,
} from '../src/lib/format.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, '..');
const PROJECT_ROOT = path.resolve(WEB_ROOT, '..');
const PUBLIC_DATA_DIR = path.join(WEB_ROOT, 'public', 'data');
const PUBLIC_FONTS_DIR = path.join(WEB_ROOT, 'public', 'fonts');
const SRC_GEN_DIR = path.join(WEB_ROOT, 'src', 'data', 'generated');
const TABLES_DIR = path.join(PROJECT_ROOT, 'docs', 'tables');

const MODEL_LABELS_FR = {
  Naive_LastValue: 'Dernier prix connu (méthode simple)',
  Seasonal_Ratio_Naive: 'Ratio saisonnier (méthode simple)',
  Seasonal_Naive_12m: "Prix du même mois l'an dernier (méthode simple)",
  Ridge_ARX: 'Régression saisonnière régularisée',
  HGBR_NoWeather: 'Arbres de décision sur historique de prix',
  HGBR_WithWeather: 'Arbres de décision (prix et météo)',
  ETS_HoltWinters: 'Lissage exponentiel saisonnier',
  SARIMAX_101_011_12: 'Modèle autorégressif saisonnier',
  SARIMA: 'Modèle autorégressif saisonnier',
};

const MODEL_LABELS_EN = {
  Naive_LastValue: 'Last known price (simple method)',
  Seasonal_Ratio_Naive: 'Seasonal ratio (simple method)',
  Seasonal_Naive_12m: 'Same month last year (simple method)',
  Ridge_ARX: 'Regularized seasonal regression',
  HGBR_NoWeather: 'Decision trees on price history',
  HGBR_WithWeather: 'Decision trees (prices and weather)',
  ETS_HoltWinters: 'Seasonal exponential smoothing',
  SARIMAX_101_011_12: 'Seasonal autoregressive model',
  SARIMA: 'Seasonal autoregressive model',
};

function buildCalendarMonths2019To2026() {
  const dates = [];
  for (let yr = 2019; yr <= 2026; yr++) {
    const maxMo = yr === 2026 ? 9 : 12;
    for (let mo = 1; mo <= maxMo; mo++) {
      const mStr = String(mo).padStart(2, '0');
      dates.push({
        date: `${yr}-${mStr}-15`,
        year_month: `${yr}-${mStr}`,
      });
    }
  }
  return dates;
}

const CALENDAR_93_MONTHS = buildCalendarMonths2019To2026();

function resolveReliabilityStatus(relObj, accObj) {
  const status = relObj.status;
  if (status === 'baseline_retained_intervals_too_narrow' || status === 'intervals_too_narrow') {
    return status;
  }
  const champId = accObj?.model_used;
  const isBaseline =
    relObj.is_baseline_retained ||
    ['Naive_LastValue', 'Seasonal_Naive_12m', 'Seasonal_Ratio_Naive'].includes(champId);
  const skill = relObj.skill_vs_best_baseline_test_pct ?? accObj?.skill_vs_best_baseline_pct ?? 0;
  if (!isBaseline && skill < 0) {
    return 'no_better_than_simple';
  }
  return status;
}

function buildPlainReliabilityNotes(relObj, accObj, horizon, marketsCount) {
  const status = resolveReliabilityStatus(relObj, accObj);
  const champId = accObj.model_used;
  const baseId = relObj.best_validation_baseline || accObj.best_baseline_val;
  const bestTestId = relObj.best_holdout_candidate;
  const bestTestMae = relObj.best_holdout_candidate_mae;
  const mae = accObj.mae;
  const mape = accObj.mape;
  const cov80 = relObj.holdout_coverage_80_pct ?? accObj.coverage_80;
  const skill = relObj.skill_vs_best_baseline_test_pct ?? accObj.skill_vs_best_baseline_pct;
  const nominal80 = 80;

  const maeFr = formatDecimal(mae, 'fr', 1);
  const maeEn = formatDecimal(mae, 'en', 1);
  const mapeFr = formatPct(mape, 'fr', 1);
  const mapeEn = formatPct(mape, 'en', 1);
  const cov80Fr = formatPct(cov80, 'fr', 1);
  const cov80En = formatPct(cov80, 'en', 1);
  const skillFr = formatSignedPct(skill, 'fr', 1);
  const skillEn = formatSignedPct(skill, 'en', 1);
  const bestMaeFr = formatDecimal(bestTestMae, 'fr', 1);
  const bestMaeEn = formatDecimal(bestTestMae, 'en', 1);

  const champFr = MODEL_LABELS_FR[champId] || champId;
  const champEn = MODEL_LABELS_EN[champId] || champId;
  const baseFr = MODEL_LABELS_FR[baseId] || baseId;
  const baseEn = MODEL_LABELS_EN[baseId] || baseId;
  const bestTestFr = MODEL_LABELS_FR[bestTestId] || bestTestId;
  const bestTestEn = MODEL_LABELS_EN[bestTestId] || bestTestId;
  const hFr = horizon === 1 ? '1 mois' : `${horizon} mois`;
  const hEn = horizon === 1 ? '1 month' : `${horizon} months`;
  const scopeFr = `Sur l'ensemble des ${marketsCount} marchés suivis, à ${hFr}`;
  const scopeEn = `Across all ${marketsCount} well-tracked markets, at ${hEn}`;

  if (status === 'baseline_retained_intervals_too_narrow') {
    return {
      note_fr: `${scopeFr} : méthode retenue « ${champFr} » (erreur moyenne de ${maeFr} XOF/kg en test, soit ${mapeFr}), mais la fourchette à ${nominal80} % a contenu ${cov80Fr} des prix observés (cible : ${nominal80} %, fourchette un peu étroite lors des variations rapides).`,
      note_en: `${scopeEn}: selected method '${champEn}' (average test error of ${maeEn} XOF/kg, or ${mapeEn}), while the ${nominal80}% interval contained ${cov80En} of observed prices (target: ${nominal80}%, slightly narrow during rapid price swings).`,
    };
  }
  if (status === 'intervals_too_narrow') {
    return {
      note_fr: `${scopeFr} : méthode retenue « ${champFr} » (erreur moyenne de ${maeFr} XOF/kg en test, soit ${mapeFr}), mais la fourchette à ${nominal80} % a contenu ${cov80Fr} des prix observés (cible : ${nominal80} %).`,
      note_en: `${scopeEn}: selected method '${champEn}' (average test error of ${maeEn} XOF/kg, or ${mapeEn}), while the ${nominal80}% interval contained ${cov80En} of observed prices (target: ${nominal80}%).`,
    };
  }
  if (status === 'no_better_than_simple') {
    return {
      note_fr: `${scopeFr} : méthode retenue « ${champFr} », sélectionnée sur la période d'entraînement, mais pas meilleure que la méthode simple en test (${skillFr}, erreur moyenne de ${maeFr} XOF/kg, soit ${mapeFr} ; devancée par « ${bestTestFr} » à ${bestMaeFr} XOF/kg).`,
      note_en: `${scopeEn}: selected method '${champEn}', chosen on the validation period, but no better than the simple method in testing (${skillEn}, average error ${maeEn} XOF/kg, or ${mapeEn}; trailed '${bestTestEn}' at ${bestMaeEn} XOF/kg).`,
    };
  }
  if (status === 'baseline_retained') {
    if (champId === 'Naive_LastValue') {
      return {
        note_fr: `${scopeFr} : méthode retenue « ${champFr} » — aucune méthode statistique complexe ne fait mieux que le dernier prix connu (erreur moyenne en test : ${maeFr} XOF/kg, soit ${mapeFr} ; la fourchette à ${nominal80} % a contenu ${cov80Fr} des prix observés).`,
        note_en: `${scopeEn}: selected method '${champEn}' — no complex statistical model beats the last known price (average test error: ${maeEn} XOF/kg, or ${mapeEn}; the ${nominal80}% interval contained ${cov80En} of observed prices).`,
      };
    }
    return {
      note_fr: `${scopeFr} : méthode retenue « ${champFr} », choisie car elle égale les modèles complexes (erreur moyenne en test : ${maeFr} XOF/kg, soit ${mapeFr} ; la fourchette à ${nominal80} % a contenu ${cov80Fr} des prix observés).`,
      note_en: `${scopeEn}: selected method '${champEn}', retained because it matches complex models (average test error: ${maeEn} XOF/kg, or ${mapeEn}; the ${nominal80}% interval contained ${cov80En} of observed prices).`,
    };
  }
  if (skill >= 0) {
    return {
      note_fr: `${scopeFr} : méthode retenue « ${champFr} » (erreur moyenne : ${maeFr} XOF/kg, soit ${mapeFr}, gain de ${skillFr} par rapport à « ${baseFr} » ; la fourchette à ${nominal80} % a contenu ${cov80Fr} des prix observés).`,
      note_en: `${scopeEn}: selected method '${champEn}' (average error: ${maeEn} XOF/kg, or ${mapeEn}, ${skillEn} gain over '${baseEn}'; the ${nominal80}% interval contained ${cov80En} of observed prices).`,
    };
  }
  return {
    note_fr: `${scopeFr} : méthode retenue « ${champFr} », sélectionnée sur la période d'entraînement (erreur moyenne de ${maeFr} XOF/kg, soit ${mapeFr} ; la fourchette à ${nominal80} % a contenu ${cov80Fr} des prix observés), bien que devancée sur les 12 mois de test par « ${bestTestFr} » (${bestMaeFr} XOF/kg).`,
    note_en: `${scopeEn}: selected method '${champEn}', chosen on the validation period (average error ${maeEn} XOF/kg, or ${mapeEn}; the ${nominal80}% interval contained ${cov80En} of observed prices), though trailed on the 12 test months by '${bestTestEn}' (${bestMaeEn} XOF/kg).`,
  };
}

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
    throw new Error(`[prepare-data] Expected 111 well-tracked series, found ${series.length}`);
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

function buildFull93MonthCalendarHistory(rawHistory) {
  const obsByDate = new Map();
  for (const pt of rawHistory) {
    if (pt.date >= '2019-01-15' && typeof pt.price === 'number' && Number.isFinite(pt.price)) {
      obsByDate.set(pt.date, pt);
    }
  }
  return CALENDAR_93_MONTHS.map(({ date, year_month }) => {
    const found = obsByDate.get(date);
    if (found) {
      return {
        date,
        year_month,
        price: found.price,
        is_observed: true,
        is_outlier: Boolean(found.is_outlier_level || found.is_outlier_jump || found.is_outlier),
      };
    }
    return {
      date,
      year_month,
      price: null,
      is_observed: false,
      is_outlier: false,
    };
  });
}

function buildSplitDataFiles() {
  const forecastsPath = path.join(PUBLIC_DATA_DIR, 'forecasts.json');
  if (!fs.existsSync(forecastsPath)) {
    throw new Error(`[prepare-data] Missing ${forecastsPath}`);
  }
  const payload = JSON.parse(fs.readFileSync(forecastsPath, 'utf-8'));
  validateForecastsExport(payload);

  // Sanitize plain-language labels and reliability notes inside payload (and persist back to forecasts.json)
  let forecastsUpdated = false;
  if (payload.products?.tomatoes?.label_fr === 'Tomate fraîche') {
    payload.products.tomatoes.label_fr = 'Tomate';
    forecastsUpdated = true;
  }
  for (const slug of ['maize_white', 'tomatoes', 'yam_white']) {
    const prodMeta = payload.products[slug];
    for (const h of [1, 2, 3]) {
      const hKey = `h${h}`;
      const relObj = prodMeta.reliability_by_horizon[hKey];
      const accObj = prodMeta.backtest_accuracy.by_horizon_test[hKey];
      const nextStatus = resolveReliabilityStatus(relObj, accObj);
      const plainNotes = buildPlainReliabilityNotes(relObj, accObj, h, prodMeta.tier1_markets_count);
      if (
        relObj.status !== nextStatus ||
        relObj.note_fr !== plainNotes.note_fr ||
        relObj.note_en !== plainNotes.note_en
      ) {
        relObj.status = nextStatus;
        relObj.note_fr = plainNotes.note_fr;
        relObj.note_en = plainNotes.note_en;
        accObj.reliability = nextStatus;
        accObj.reliability_note_fr = plainNotes.note_fr;
        accObj.reliability_note_en = plainNotes.note_en;
        if (accObj.reliability_detail) {
          accObj.reliability_detail.status = nextStatus;
          accObj.reliability_detail.note_fr = plainNotes.note_fr;
          accObj.reliability_detail.note_en = plainNotes.note_en;
        }
        forecastsUpdated = true;
      }
    }
  }
  for (const s of payload.series) {
    if (s.product_slug === 'tomatoes' && s.label_fr === 'Tomate fraîche') {
      s.label_fr = 'Tomate';
      forecastsUpdated = true;
    }
    const prodRel = payload.products[s.product_slug].reliability_by_horizon;
    s.reliability_by_horizon = prodRel;
    for (const fc of s.forecasts) {
      const relH = prodRel[`h${fc.horizon_months}`];
      if (
        fc.reliability !== relH.status ||
        fc.reliability_note_fr !== relH.note_fr ||
        fc.reliability_note_en !== relH.note_en
      ) {
        fc.reliability = relH.status;
        fc.reliability_note_fr = relH.note_fr;
        fc.reliability_note_en = relH.note_en;
        forecastsUpdated = true;
      }
    }
  }
  for (const mEntry of payload.markets_coverage || []) {
    for (const slug of ['maize_white', 'tomatoes', 'yam_white']) {
      const pCov = mEntry.coverage_by_product?.[slug];
      if (!pCov) continue;
      const obsM = pCov.obs_months_2019_2026 ?? 0;
      const isT1 = Boolean(pCov.is_forecasted);
      const nextFr = isT1
        ? `Marché bien suivi (${obsM}/93 relevés de prix entre 2019 et 2026, seuil d'au moins 80 mois sur 93) : prévisions actives avec fourchettes à 80 % et 90 %.`
        : obsM === 0
          ? 'Aucun relevé depuis 2019 pour ce produit dans ce marché : prévision désactivée conformément à la règle anti-invention de données.'
          : `Suivi partiel (${obsM}/93 relevés de prix entre 2019 et 2026, seuil fixé à 80 mois sur 93) : historique affiché en mode exploration uniquement, sans prévision hasardeuse.`;
      const nextEn = isT1
        ? `Well-tracked market (${obsM}/93 price records between 2019 and 2026, threshold of at least 80 months out of 93): active forecasts with 80% and 90% intervals.`
        : obsM === 0
          ? 'Zero post-2019 price records for this product in this market: forecasting disabled per data integrity rules.'
          : `Partial coverage (${obsM}/93 price records between 2019 and 2026 vs 80/93 threshold): historical series shown for exploration only, no forecast issued.`;
      if (pCov.status_note_fr !== nextFr || pCov.status_note_en !== nextEn) {
        pCov.status_note_fr = nextFr;
        pCov.status_note_en = nextEn;
        forecastsUpdated = true;
      }
    }
  }
  if (forecastsUpdated) {
    fs.writeFileSync(forecastsPath, JSON.stringify(payload, null, 2), 'utf-8');
  }

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
  const rawSummaryRows = parseCsv(
    fs.readFileSync(path.join(TABLES_DIR, 'raw_dataset_summary.csv'), 'utf-8')
  );
  const rawSummaryMap = Object.fromEntries(rawSummaryRows.map((r) => [r['metric'], r['value']]));

  // Compute overlap-weighted mean absolute difference between Yam and Yam (white)
  let yamGapWeightedSum = 0;
  let yamGapOverlapTotal = 0;
  for (const row of rawSummaryRows) {
    if ((row['metric'] || '').startsWith('yam_vs_yam_white_overlap_')) {
      const val = row['value'] || '';
      const ovMatch = val.match(/overlap=(\d+)/);
      const diffMatch = val.match(/mean_abs_diff=([\d.]+)/);
      const ov = ovMatch ? parseInt(ovMatch[1], 10) : 0;
      const diff = diffMatch ? parseFloat(diffMatch[1]) : 0;
      if (ov > 0 && Number.isFinite(diff)) {
        yamGapWeightedSum += ov * diff;
        yamGapOverlapTotal += ov;
      }
    }
  }
  const yamVarietyGapXof =
    yamGapOverlapTotal > 0 ? round(yamGapWeightedSum / yamGapOverlapTotal, 1) : 0;

  const obsCounts = payload.series.map((s) => s.obs_months_2019_2026).filter(Number.isFinite);
  const seriesMinObsMonths = obsCounts.length > 0 ? Math.min(...obsCounts) : 0;
  const seriesMaxObsMonths = obsCounts.length > 0 ? Math.max(...obsCounts) : 0;

  const rawSummary = {
    n_observations: parseInt(rawSummaryMap['wfp_food_prices_ben.csv_data_rows'] || '0', 10),
    first_date: rawSummaryMap['global_min_date'] || '2002-01-15',
    last_date: rawSummaryMap['global_max_date'] || '2026-09-15',
    n_active_markets: parseInt(rawSummaryMap['active_markets_in_prices'] || '0', 10),
    n_departments: parseInt(rawSummaryMap['departments_covered'] || '0', 10),
    yam_variety_gap_xof: yamVarietyGapXof,
    tier1_min_months: 80,
    n_model_months: 93,
    series_min_obs_months: seriesMinObsMonths,
    series_max_obs_months: seriesMaxObsMonths,
    model_window_start: '2019-01-15',
    model_window_end: '2026-09-15',
    validation_start: '2022-01-15',
    validation_end: '2025-09-15',
    test_start: '2025-10-15',
    test_end: '2026-09-15',
    first_forecast_month: payload.forecast_target_dates?.[0] || '2026-10-15',
    last_forecast_month: payload.forecast_target_dates?.[2] || '2026-12-15',
  };

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
    if (!m) return { spread_pts: 0, spread_pct: cell, spread_pct_num: 0 };
    return {
      spread_pts: parseFloat(m[1]),
      spread_pct: m[2],
      spread_pct_num: parseFloat(m[2].replace('%', '')),
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

    // Compute monthly median and mean across all well-tracked markets for this product
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

    // Latest snapshot across well-tracked markets
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
        h3_test_mae: s.backtest_accuracy?.by_horizon_test?.h3?.mae ?? null,
        h3_test_mape: s.backtest_accuracy?.by_horizon_test?.h3?.mape ?? null,
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

    // Seasonality across well-tracked markets from eda_seasonality_profile.csv
    const natSeasRow = seasRows.find(
      (r) => r['Product'] === commodity && r['Agro-Ecological Zone'] === 'All Tier-1 (National)'
    );
    const zoneSeasRows = seasRows.filter((r) => r['Product'] === commodity);
    const troughParsed = parseMonthIndexCell(natSeasRow?.['Trough Month (Index)'] || '');
    const peakParsed = parseMonthIndexCell(natSeasRow?.['Peak Month (Index)'] || '');
    const spreadParsed = parseSpreadCell(natSeasRow?.['Peak-to-Trough Spread (Index pts / %)'] || '');
    const peakToTroughRatio = round(peakParsed.index / troughParsed.index, 2);

    // EDA summary row for Modeling Window
    const edaRow = edaSumRows.find(
      (r) => r['Product'] === commodity && r['Regime / Scope'].startsWith('Tier-1 Modeling Window')
    );

    // Dantokpa series (market_id "2279" or market === "Dantokpa")
    const dantokpaFull = prodSeries.find((s) => s.market_id === '2279' || s.market === 'Dantokpa');
    if (!dantokpaFull) {
      throw new Error(`[prepare-data] Missing Dantokpa series for ${slug}`);
    }
    // Build full 93-month calendar history (2019-01-15..2026-09-15) with explicit nulls on unobserved months
    const dantokpaHistory2019 = buildFull93MonthCalendarHistory(dantokpaFull.history);

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
        peak_to_trough_ratio: peakToTroughRatio,
        spread_pts: spreadParsed.spread_pts,
        spread_pct: spreadParsed.spread_pct,
        spread_pct_num: spreadParsed.spread_pct_num,
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
      series: prodSeries.map((s) => ({
        ...s,
        history_calendar_2019_2026: buildFull93MonthCalendarHistory(s.history),
      })),
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
    raw_summary: rawSummary,
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

  // Build-time consistency check: ensure every product/horizon note matches shared formatter rounding
  for (const slug of productSlugs) {
    const p = homeProducts[slug];
    for (const hKey of ['h1', 'h2', 'h3']) {
      const acc = p.backtest_accuracy.by_horizon_test[hKey];
      const expFr = formatPct(acc.mape, 'fr', 1);
      const expEn = formatPct(acc.mape, 'en', 1);
      if (!acc.reliability_note_fr.includes(expFr) || !acc.reliability_note_en.includes(expEn)) {
        throw new Error(
          `[prepare-data] Rounding consistency failure for ${slug} ${hKey}: expected ${expFr} / ${expEn}`
        );
      }
    }
  }

  console.log(
    `[prepare-data] Validated forecasts.json & wrote split files: home-summary.json (${(Buffer.byteLength(homeSummaryStr) / 1024).toFixed(1)} KiB), product-maize_white.json, product-tomatoes.json, product-yam_white.json, method-tables.json.`
  );
}

copySelfHostedFontsAndLicenses();
buildSplitDataFiles();

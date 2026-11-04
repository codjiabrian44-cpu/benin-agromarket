import homeSummaryRaw from '../data/generated/home-summary.json';
import type { ProductSlug } from '../i18n';

export interface HistoryPoint {
  date: string;
  year_month: string;
  price: number | null;
  is_observed?: boolean;
  is_outlier: boolean;
}

export interface ForecastPoint {
  horizon_months: number;
  target_date: string;
  year_month: string;
  model_used: string;
  point_forecast: number;
  low_80: number;
  high_80: number;
  low_90: number;
  high_90: number;
  change_vs_last_pct: number;
  reliability: string;
  reliability_note_fr: string;
  reliability_note_en: string;
}

export interface ReliabilityInfo {
  status: string;
  is_calibrated_80: boolean;
  is_baseline_retained: boolean;
  did_worse_than_another_candidate_on_holdout: boolean;
  best_holdout_candidate: string;
  best_holdout_candidate_mae: number;
  best_validation_baseline: string;
  skill_vs_best_baseline_test_pct: number;
  holdout_coverage_80_pct: number;
  holdout_coverage_90_pct: number;
  note_fr: string;
  note_en: string;
}

export interface Tier1MarketMapItem {
  market_id: string;
  market_name: string;
  department: string;
  commune: string;
  agro_zone: string;
  latitude: number;
  longitude: number;
  observed_months_2019_2026: number;
  completeness_pct: number;
  last_observed_date: string;
  last_observed_price: number;
  national_median_price: number;
  diff_vs_median_pct: number;
  h1_forecast: number;
  h1_low_80: number;
  h1_high_80: number;
  h1_change_pct: number;
  h3_forecast: number;
  h3_low_80: number;
  h3_high_80: number;
  h3_change_pct: number;
  holdout_mae: number | null;
  holdout_mape: number | null;
}

export interface HomeProductData {
  commodity: string;
  product_slug: ProductSlug;
  label_fr: string;
  label_en: string;
  tier1_markets_count: number;
  observed_market_months: number;
  panel_mean_price: number;
  panel_median_price: number;
  panel_cv_pct: string;
  cagr_2019_2026: string;
  champions_by_horizon: Record<'h1' | 'h2' | 'h3', string>;
  backtest_accuracy: {
    holdout_test_window: string;
    validation_window: string;
    test_overall: {
      n_eval: number;
      mae: number;
      rmse: number;
      mape: number;
      skill_vs_snaive_pct: number;
      coverage_80: number;
      coverage_90: number;
    };
    by_horizon_test: Record<
      'h1' | 'h2' | 'h3',
      {
        horizon_months: number;
        model_used: string;
        best_baseline_val: string;
        n_eval: number;
        mae: number;
        rmse: number;
        mape: number;
        skill_vs_best_baseline_pct: number;
        skill_vs_snaive_pct: number;
        coverage_80: number;
        coverage_90: number;
        mean_width_80: number;
        reliability: string;
        reliability_note_fr: string;
        reliability_note_en: string;
      }
    >;
  };
  reliability_by_horizon: Record<'h1' | 'h2' | 'h3', ReliabilityInfo>;
  seasonality: {
    trough_month_num: number;
    trough_index: number;
    peak_month_num: number;
    peak_index: number;
    peak_to_trough_ratio?: number;
    spread_pts: number;
    spread_pct: string;
    monthly_indices: Array<{ month_num: number; index: number }>;
  };
  latest_national_stats: {
    as_of_date: string;
    median_price: number;
    mean_price: number;
    min_price: number;
    min_market_name: string;
    min_department: string;
    max_price: number;
    max_market_name: string;
    max_department: string;
    max_min_ratio: number;
    sparkline_36m: Array<{ date: string; median_price: number; mean_price: number; markets_reporting: number }>;
  };
  dantokpa: {
    market_id: string;
    market_name: string;
    department: string;
    commune: string;
    agro_zone: string;
    latitude: number;
    longitude: number;
    observed_months_2019_2026: number;
    completeness_pct: number;
    last_observed_date: string;
    last_observed_price: number;
    champions_by_horizon: Record<'h1' | 'h2' | 'h3', string>;
    reliability_by_horizon: Record<'h1' | 'h2' | 'h3', ReliabilityInfo>;
    history: HistoryPoint[];
    forecasts: ForecastPoint[];
  };
  tier1_markets_map: Tier1MarketMapItem[];
}

export interface HomeSummaryPayload {
  metadata: {
    project: string;
    as_of_date: string;
    forecast_horizons_months: number[];
    forecast_target_dates: string[];
    currency: string;
    unit: string;
    price_type: string;
    total_tier1_series: number;
    active_markets_count: number;
  };
  products: Record<ProductSlug, HomeProductData>;
}

/**
 * Load and validate the split Home summary dataset at build time.
 * Fails loudly if any invariant is violated.
 */
export function getValidatedHomeData(): HomeSummaryPayload {
  const data = homeSummaryRaw as unknown as HomeSummaryPayload;
  if (!data?.metadata || data.metadata.as_of_date !== '2026-09-15') {
    throw new Error('[data.ts] Build-time validation failed: invalid metadata in home-summary.json');
  }
  if (data.metadata.total_tier1_series !== 111) {
    throw new Error(`[data.ts] Expected 111 Tier-1 series, got ${data.metadata.total_tier1_series}`);
  }
  const slugs: ProductSlug[] = ['maize_white', 'tomatoes', 'yam_white'];
  for (const slug of slugs) {
    const prod = data.products[slug];
    if (!prod || !prod.dantokpa || !prod.dantokpa.history.length || prod.dantokpa.forecasts.length !== 3) {
      throw new Error(`[data.ts] Build-time validation failed for product ${slug}`);
    }
    for (const fc of prod.dantokpa.forecasts) {
      if (
        !Number.isFinite(fc.point_forecast) ||
        !(fc.low_90 <= fc.low_80 && fc.low_80 <= fc.point_forecast && fc.point_forecast <= fc.high_80 && fc.high_80 <= fc.high_90)
      ) {
        throw new Error(`[data.ts] Interval ordering violation in Dantokpa ${slug} h=${fc.horizon_months}`);
      }
    }
  }
  return data;
}

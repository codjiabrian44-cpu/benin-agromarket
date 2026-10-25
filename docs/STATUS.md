# Project Status — Bénin AgroMarket (`docs/STATUS.md`)

**Date:** 2026-10-25  
**Current Phase:** **Phase 2 Complete** (Phase 1 Review Items Closed + Phase 2 Rolling-Origin Modeling, Evaluation, Model Card & App Forecast Export)  
**Status:** **STOPPED at End of Phase 2** — awaiting owner review and confirmation before starting Phase 3 (Web Application).

Every statistic and table in this report is produced deterministically by [`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py), [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py), [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py), and [`src/evaluate/backtest.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/backtest.py) and saved in [`docs/tables/`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/).

---

## 1. Executive Summary of Completed Work (Phase 1 Fixes + Phase 2 Modeling)

1. **Step 1 — Phase 1 Review Items Closed (`fix: phase 1 review items`):**
   - Updated [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) and regenerated `docs/tables/eda_*.{csv,md}` and `docs/figures/fig1..fig5.svg` so that 100% of numbers inside figure titles, labels, and captions are computed dynamically at runtime from the exact plotted data (`L1`: `Pre-2019 Exploration Only (2007-01..2016-11, 20 mkts)`; `L2`: runtime-computed Tier-1 `2019–2026` outlier counts `11/31`, `237/40`, `17/68` in `fig4_abrupt_changes_and_outliers.svg`; `L3`: dynamic `0..3000 XOF/kg` x-axis and dedicated right gutter for `Tomatoes` in `fig3_market_differences_tier1.svg`).
   - Recorded **Safeguard 1** (banning full-sample diagnostic columns `robust_z` and `is_outlier_*` from model inputs) and **Safeguard 2** (evaluating strictly on `is_observed == 1` ground-truth targets, testing `price_interp_1m_max` solely as a lag-input sensitivity variant on validation) in [`docs/DECISIONS.md`](file:///home/brian/projets-ds/benin-agromarket/docs/DECISIONS.md).
2. **Step 2 — Pre-Registered Protocol & Phase 2 Modeling Pipeline ([`src/models/`](file:///home/brian/projets-ds/benin-agromarket/src/models/), [`src/evaluate/`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/)):**
   - Pre-registered **Decision 7** in [`docs/DECISIONS.md`](file:///home/brian/projets-ds/benin-agromarket/docs/DECISIONS.md) before running any models: expanding window with `36` initial training months (`2019-01..2021-12`, first forecast origin `2021-12-15`), **Validation Split (`2022-01..2025-09`)** for model selection and ablations, and **Final Holdout Test Split (`2025-10..2026-09`, `12` target months per horizon)** evaluated once after freezing champion selection.
   - Implemented [`src/models/features.py`](file:///home/brian/projets-ds/benin-agromarket/src/models/features.py), [`src/models/forecasters.py`](file:///home/brian/projets-ds/benin-agromarket/src/models/forecasters.py), [`src/evaluate/backtest.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/backtest.py), and [`src/evaluate/figures.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/figures.py).
   - Trained and evaluated **8 main candidate models** (`Naive_LastValue`, `Seasonal_Naive_12m`, `Seasonal_Ratio_Naive`, `ETS_HoltWinters`, `SARIMAX_101_011_12`, `Ridge_ARX`, `HGBR_NoWeather`, `HGBR_WithWeather`) plus **2 lag-imputation sensitivity variants** (`Ridge_ARX_Interp1mLags`, `HGBR_NoWeather_Interp1mLags`) across all `111` Tier-1 product-market series (`49` `Maize (white)`, `43` `Tomatoes`, `19` `Yam (white)`) and horizons $h \in \{1, 2, 3\}$ months ahead.
   - Generated all **9 Phase 2 CSV + Markdown tables** in [`docs/tables/`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/):
     1. [`docs/tables/phase2_backtest_by_product_horizon.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_backtest_by_product_horizon.md)
     2. [`docs/tables/phase2_champion_selection.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_champion_selection.md)
     3. [`docs/tables/phase2_weather_ablation.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_weather_ablation.md)
     4. [`docs/tables/phase2_imputation_sensitivity.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_imputation_sensitivity.md)
     5. [`docs/tables/phase2_outlier_sensitivity.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_outlier_sensitivity.md)
     6. [`docs/tables/phase2_interval_calibration.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_interval_calibration.md)
     7. [`docs/tables/phase2_metrics_by_market.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_metrics_by_market.md)
     8. [`docs/tables/phase2_metrics_by_zone_season.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_metrics_by_zone_season.md)
     9. [`docs/tables/phase2_forecast_2026Q4_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_forecast_2026Q4_summary.md)
   - Rendered **4 Phase 2 vector `.svg` figures** in [`docs/figures/`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/) via [`src/evaluate/figures.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/figures.py):
     1. [`docs/figures/fig6_model_comparison_by_horizon.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig6_model_comparison_by_horizon.svg): *Plain-language caption:* Compares forecast error (`MAE` in XOF/kg and `MAPE` %) across all 8 candidate models at 1-, 2-, and 3-month horizons on both the Validation split (`2022-01..2025-09`) and the Final Holdout Test split (`2025-10..2026-09`), highlighting the selected champion for each product and horizon.
     2. [`docs/figures/fig7_rolling_backtest_trajectories.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig7_rolling_backtest_trajectories.svg): *Plain-language caption:* Shows actual observed prices alongside 1-month and 3-month rolling-origin forecasts, `80%`/`90%` prediction intervals, and the `2026-10..2026-12` outlook across six major benchmark markets (`Dantokpa`, `Glazoué`, `Parakou`, `Djougou`, `Nikki`, `Savalou`), with the `2025-09` validation/test split boundary marked explicitly.
     3. [`docs/figures/fig8_market_error_distribution.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig8_market_error_distribution.svg): *Plain-language caption:* Displays Holdout Test accuracy (`MAE` and `MAPE`) and skill vs. `Seasonal_Naive_12m` across individual Tier-1 markets per product, showing where forecasts are tightest (e.g., grain and northern producer hubs) vs. widest (high-volatility southern tomato markets).
     4. [`docs/figures/fig9_interval_calibration_and_ablation.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig9_interval_calibration_and_ablation.svg): *Plain-language caption:* Summarizes empirical `80%` and `90%` prediction interval coverage against nominal targets (Panel 9A), the NASA POWER weather feature ablation impact on `MAE` (Panel 9B), and Holdout Test `MAPE` disaggregated by agro-ecological zone and seasonal regime (Panel 9C).
   - Saved final production models trained through `as_of_date = 2026-09-15` in [`models/champion_*.joblib`](file:///home/brian/projets-ds/benin-agromarket/models/) and [`models/model_registry.json`](file:///home/brian/projets-ds/benin-agromarket/models/model_registry.json), wrote [`docs/MODEL_CARD.md`](file:///home/brian/projets-ds/benin-agromarket/docs/MODEL_CARD.md), and exported [`web/public/data/forecasts.json`](file:///home/brian/projets-ds/benin-agromarket/web/public/data/forecasts.json) (`UTF-8`, `111` Tier-1 forecasted series + coverage status for all `51` active markets).

---

## 2. Phase 2 Modeling & Evaluation Results (`src/evaluate/backtest.py`)

### 2.1 Champion Model Selection (Validation Split) & Frozen Holdout Test Performance
*Source script: [`src/evaluate/backtest.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/backtest.py) → [`docs/tables/phase2_champion_selection.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_champion_selection.md)*

| Product | Horizon | Best Baseline (Val) | Baseline Val MAE | Baseline Val MAPE | Best Statistical/ML (Val) | Stat/ML Val MAE | Stat/ML Val MAPE | Selected Champion | Val Skill vs SNaive12m | Test MAE (XOF/kg) | Test RMSE (XOF/kg) | Test MAPE % | Test Skill vs SNaive12m | Test Skill vs Naive1m | Test 80% PI Cov | Test 90% PI Cov | Selection Rationale (Honesty Clause) |
| :--- | :--- | :--- | ---: | ---: | :--- | ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **`Maize (white)`** | `h=1m` | `Naive_LastValue` | 19.8 | 9.1% | `HGBR_NoWeather` | 20.5 | 9.5% | **`Naive_LastValue`** | `+61.2%` | **9.6** | **15.2** | **6.8%** | `+85.0%` | `+0.0%` | 84.4% | 92.8% | Baseline `Naive_LastValue` retained (Honesty Clause: `HGBR_NoWeather` Val MAE 20.5 vs 19.8 [`-3.9% < +0.5%` threshold]) |
| **`Maize (white)`** | `h=2m` | `Seasonal_Ratio_Naive` | 30.2 | 13.9% | `HGBR_NoWeather` | 30.0 | 14.1% | **`HGBR_NoWeather`** | `+41.5%` | **21.3** | **26.6** | **16.2%** | `+66.6%` | `-42.9%` | 78.2% | 88.7% | `HGBR_NoWeather` beats best baseline (`Seasonal_Ratio_Naive`) on Val MAE (30.0 vs 30.2 XOF/kg, `+0.8%` skill) |
| **`Maize (white)`** | `h=3m` | `Seasonal_Ratio_Naive` | 35.1 | 16.2% | `Ridge_ARX` | 35.3 | 16.7% | **`Seasonal_Ratio_Naive`** | `+32.0%` | **24.6** | **31.0** | **17.5%** | `+61.5%` | `-25.9%` | 78.9% | 88.7% | Baseline `Seasonal_Ratio_Naive` retained (Honesty Clause: `Ridge_ARX` Val MAE 35.3 vs 35.1 [`-0.6% < +0.5%` threshold]) |
| **`Tomatoes`** | `h=1m` | `Seasonal_Ratio_Naive` | 119.7 | 24.3% | `Ridge_ARX` | 111.4 | 21.6% | **`Ridge_ARX`** | `+39.4%` | **109.9** | **241.7** | **18.8%** | `+37.1%` | `+10.1%` | 85.0% | 91.8% | `Ridge_ARX` beats best baseline (`Seasonal_Ratio_Naive`) on Val MAE (111.4 vs 119.7 XOF/kg, `+6.9%` skill) |
| **`Tomatoes`** | `h=2m` | `Seasonal_Ratio_Naive` | 150.1 | 31.0% | `Ridge_ARX` | 143.4 | 28.8% | **`Ridge_ARX`** | `+22.4%` | **146.0** | **300.4** | **26.0%** | `+16.5%` | `+17.7%` | 84.6% | 93.2% | `Ridge_ARX` beats best baseline (`Seasonal_Ratio_Naive`) on Val MAE (143.4 vs 150.1 XOF/kg, `+4.5%` skill) |
| **`Tomatoes`** | `h=3m` | `Seasonal_Ratio_Naive` | 163.7 | 33.8% | `Ridge_ARX` | 150.7 | 30.7% | **`Ridge_ARX`** | `+18.5%` | **161.1** | **339.7** | **29.1%** | `+7.9%` | `+28.7%` | 85.4% | 92.6% | `Ridge_ARX` beats best baseline (`Seasonal_Ratio_Naive`) on Val MAE (150.7 vs 163.7 XOF/kg, `+8.0%` skill) |
| **`Yam (white)`** | `h=1m` | `Naive_LastValue` | 45.6 | 10.5% | `HGBR_NoWeather` | 43.9 | 9.8% | **`HGBR_NoWeather`** | `+51.3%` | **39.9** | **68.2** | **9.2%** | `+58.1%` | `+13.1%` | 79.6% | 90.7% | `HGBR_NoWeather` beats best baseline (`Naive_LastValue`) on Val MAE (43.9 vs 45.6 XOF/kg, `+3.8%` skill) |
| **`Yam (white)`** | `h=2m` | `Seasonal_Ratio_Naive` | 64.7 | 13.8% | `HGBR_NoWeather` | 60.8 | 13.3% | **`HGBR_NoWeather`** | `+31.8%` | **57.0** | **85.9** | **14.2%** | `+40.2%` | `+27.0%` | 78.3% | 86.7% | `HGBR_NoWeather` beats best baseline (`Seasonal_Ratio_Naive`) on Val MAE (60.8 vs 64.7 XOF/kg, `+6.0%` skill) |
| **`Yam (white)`** | `h=3m` | `Seasonal_Ratio_Naive` | 73.2 | 15.6% | `Ridge_ARX` | 73.5 | 16.8% | **`Seasonal_Ratio_Naive`** | `+16.8%` | **74.1** | **104.9** | **19.5%** | `+22.3%` | `+23.9%` | 71.2% | 81.4% | Baseline `Seasonal_Ratio_Naive` retained (Honesty Clause: `Ridge_ARX` Val MAE 73.5 vs 73.2 [`-0.3% < +0.5%` threshold]) |

---

### 2.2 NASA POWER Agroclimatic Feature Ablation (`HGBR_WithWeather` vs `HGBR_NoWeather`)
*Source script: [`src/evaluate/backtest.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/backtest.py) → [`docs/tables/phase2_weather_ablation.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_weather_ablation.md)*

| Product | Split | Horizon | Eval Pairs | `HGBR_NoWeather` MAE | `HGBR_NoWeather` MAPE | `HGBR_WithWeather` MAE | `HGBR_WithWeather` MAPE | Delta MAE (`With - No`) | Weather Skill Gain % | Reference `Ridge_ARX` MAE | Ablation Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| `Maize (white)` | Validation (`2022-01..2025-09`) | All (`h=1..3`) | 6300 | 28.70 | 13.51% | 28.77 | 13.56% | `+0.07` | `-0.25%` | 28.62 | Negligible difference (`-0.25%` MAE — parsimony favors `NoWeather`/`Ridge`) |
| `Maize (white)` | Holdout Test (`2025-10..2026-09`) | All (`h=1..3`) | 1749 | 21.63 | 16.50% | 21.89 | 16.64% | `+0.26` | `-1.20%` | 22.88 | Degrades accuracy (`-1.20%` MAE — calendar seasonality sufficient) |
| `Tomatoes` | Validation (`2022-01..2025-09`) | All (`h=1..3`) | 5502 | 137.13 | 28.25% | 137.09 | 28.20% | `-0.05` | `+0.03%` | 134.86 | Negligible difference (`+0.03%` MAE — parsimony favors `NoWeather`/`Ridge`) |
| `Tomatoes` | Holdout Test (`2025-10..2026-09`) | All (`h=1..3`) | 1539 | 134.71 | 24.81% | 135.62 | 24.77% | `+0.91` | `-0.68%` | 139.01 | Degrades accuracy (`-0.68%` MAE — calendar seasonality sufficient) |
| `Yam (white)` | Validation (`2022-01..2025-09`) | All (`h=1..3`) | 2400 | 59.21 | 13.13% | 59.33 | 13.27% | `+0.12` | `-0.20%` | 60.43 | Negligible difference (`-0.20%` MAE — parsimony favors `NoWeather`/`Ridge`) |
| `Yam (white)` | Holdout Test (`2025-10..2026-09`) | All (`h=1..3`) | 678 | 55.08 | 13.70% | 56.04 | 14.08% | `+0.95` | `-1.73%` | 54.75 | Degrades accuracy (`-1.73%` MAE — calendar seasonality sufficient) |

---

### 2.2b Outlier Evaluation Sensitivity (`All Observed Targets` vs. `Excluding Flagged Outlier Target Months`)
*Source script: [`src/evaluate/backtest.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/backtest.py) → [`docs/tables/phase2_outlier_sensitivity.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_outlier_sensitivity.md)*

| Product | Evaluation Split | Horizon | Model | All Obs Targets (`N`) | Flagged Outlier Targets | Non-Outlier Targets (`N`) | Primary MAE (All Obs) | Primary RMSE | Primary MAPE % | Primary Skill vs SNaive12m | Primary 80% PI Cov | Excl-Outliers MAE | Excl-Outliers RMSE | Excl-Outliers MAPE % | Excl-Outliers Skill vs SNaive12m | Excl-Outliers 80% PI Cov | Delta MAE (`Excl - All`) | Delta MAPE (`Excl - All`) |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Maize (white)` | Validation (`2022-01..2025-09`) | All (`h=1..3`) | Selected Champions (`h=1..3`) | 6300 | 48 | 6252 | 28.16 | 39.47 | 13.08% | `+45.1%` | 75.8% | 27.78 | 38.38 | 12.93% | `+45.0%` | 76.1% | `-0.38` | `-0.14 pp` |
| **`Maize (white)`** | **Holdout Test (`2025-10..2026-09`)** | **All (`h=1..3`)** | **Selected Champions (`h=1..3`)** | **1749** | **6** | **1743** | **18.48** | **25.17** | **13.48%** | **`+71.1%`** | **80.5%** | **18.33** | **24.90** | **13.29%** | **`+71.2%`** | **80.8%** | **`-0.15`** | **`-0.19 pp`** |
| `Tomatoes` | Validation (`2022-01..2025-09`) | All (`h=1..3`) | Selected Champions (`h=1..3`) | 5502 | 329 | 5173 | 134.86 | 237.67 | 26.96% | `+26.9%` | 82.5% | 125.80 | 217.93 | 25.30% | `+29.0%` | 84.5% | `-9.06` | `-1.66 pp` |
| **`Tomatoes`** | **Holdout Test (`2025-10..2026-09`)** | **All (`h=1..3`)** | **Selected Champions (`h=1..3`)** | **1539** | **51** | **1488** | **139.01** | **296.69** | **24.65%** | **`+20.5%`** | **85.0%** | **136.93** | **296.22** | **24.35%** | **`+21.0%`** | **85.6%** | **`-2.08`** | **`-0.29 pp`** |
| `Yam (white)` | Validation (`2022-01..2025-09`) | All (`h=1..3`) | Selected Champions (`h=1..3`) | 2400 | 30 | 2370 | 59.06 | 98.80 | 12.86% | `+33.7%` | 80.9% | 56.60 | 91.30 | 12.32% | `+33.7%` | 81.6% | `-2.46` | `-0.54 pp` |
| **`Yam (white)`** | **Holdout Test (`2025-10..2026-09`)** | **All (`h=1..3`)** | **Selected Champions (`h=1..3`)** | **678** | **42** | **636** | **56.99** | **87.62** | **14.28%** | **`+40.2%`** | **76.4%** | **52.50** | **78.13** | **13.08%** | **`+35.5%`** | **79.6%** | **`-4.50`** | **`-1.20 pp`** |

---

### 2.3 Production 3-Month Ahead Forecasts (`2026-10` to `2026-12`, Origin `as_of_date = 2026-09-15`)
*Source script: [`src/evaluate/backtest.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/backtest.py) → [`docs/tables/phase2_forecast_2026Q4_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_forecast_2026Q4_summary.md)*

| Product | Aggregation / Market | Horizon (Target Date) | Model Used | Last Obs Price (`2026-09`, XOF/kg) | Point Forecast (XOF/kg) | Expected Change % | 80% Prediction Interval | 90% Prediction Interval |
| :--- | :--- | :--- | :--- | ---: | :--- | ---: | :--- | :--- |
| **`Maize (white)`** | **All 49 Tier-1 Markets (Mean)** | `h=1m` (`2026-10-15`) | `Naive_LastValue` | 133.9 | 133.9 (med 133.0) | `+0.0%` | `[116.9, 153.6]` | `[110.7, 162.3]` |
| `Maize (white)` | All 49 Tier-1 Markets (Mean) | `h=2m` (`2026-11-15`) | `HGBR_NoWeather` | 133.9 | 131.7 (med 131.0) | `-1.6%` | `[107.1, 162.4]` | `[100.7, 173.1]` |
| `Maize (white)` | All 49 Tier-1 Markets (Mean) | `h=3m` (`2026-12-15`) | `Seasonal_Ratio_Naive` | 133.9 | 134.3 (med 130.4) | `+0.3%` | `[105.9, 170.8]` | `[98.6, 183.9]` |
| **`Tomatoes`** | **All 43 Tier-1 Markets (Mean)** | `h=1m` (`2026-10-15`) | `Ridge_ARX` | 446.3 | 413.9 (med 386.4) | `-7.3%` | `[299.7, 578.5]` | `[274.1, 636.1]` |
| `Tomatoes` | All 43 Tier-1 Markets (Mean) | `h=2m` (`2026-11-15`) | `Ridge_ARX` | 446.3 | 403.1 (med 389.0) | `-9.7%` | `[263.7, 629.8]` | `[234.1, 725.9]` |
| `Tomatoes` | All 43 Tier-1 Markets (Mean) | `h=3m` (`2026-12-15`) | `Ridge_ARX` | 446.3 | 434.0 (med 415.7) | `-2.8%` | `[276.9, 699.8]` | `[242.2, 839.0]` |
| **`Yam (white)`** | **All 19 Tier-1 Markets (Mean)** | `h=1m` (`2026-10-15`) | `HGBR_NoWeather` | 401.1 | 380.2 (med 366.1) | `-5.2%` | `[331.5, 436.9]` | `[313.1, 463.6]` |
| `Yam (white)` | All 19 Tier-1 Markets (Mean) | `h=2m` (`2026-11-15`) | `HGBR_NoWeather` | 401.1 | 384.6 (med 394.8) | `-4.1%` | `[315.4, 470.6]` | `[294.7, 504.9]` |
| `Yam (white)` | All 19 Tier-1 Markets (Mean) | `h=3m` (`2026-12-15`) | `Seasonal_Ratio_Naive` | 401.1 | 400.1 (med 388.2) | `-0.2%` | `[313.0, 514.0]` | `[288.9, 560.5]` |

---

## 3. Retaining Phase 1 EDA Reference Summary (`src/analysis/eda.py`)

### 3.1 Distributional Summary & Multi-Year Price Trends (`2007–2026`)
*Source script: [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) → [`docs/tables/eda_summary_by_product.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_summary_by_product.md)*

| Product | Regime / Scope | Obs | Markets | Mean (XOF/kg) | SD | CV % | Median | P25 | P75 | IQR | Min | Max | 2019 Mean | Last-12m Mean (2025-10..2026-09) | 2019 Median | Last-12m Median | Ratio (Last-12m / 2019) | CAGR % (6.75 yr) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| **`Maize (white)`** | **Tier-1 Modeling Window (`2019-01..2026-09`, `49` mkts)** | 4162 | 49 | 201.8 | 59.9 | 29.7% | 197.0 | 160.3 | 236.7 | 76.4 | 25.6 | 575.8 | 141.6 | 149.1 | 137.4 | 146.0 | `1.05x` (med `1.06x`) | `+0.8%` (med `+0.9%`) |
| `Maize (white)` | All Active Markets (`2019-01..2026-09`, `50` mkts) | 4239 | 50 | 202.8 | 60.9 | 30.0% | 198.0 | 161.0 | 238.4 | 77.4 | 25.6 | 575.8 | 141.7 | 150.0 | 137.4 | 147.2 | `1.06x` (med `1.07x`) | `+0.8%` (med `+1.0%`) |
| `Maize (white)` | Pre-2019 Exploration Only (`2007-01..2016-11`, `20` mkts) | 629 | 20 | 166.9 | 52.2 | 31.3% | 160.0 | 130.0 | 200.0 | 70.0 | 60.0 | 525.0 | - | - | - | - | - | - |
| **`Tomatoes`** | **Tier-1 Modeling Window (`2019-01..2026-09`, `43` mkts)** | 3664 | 43 | 491.5 | 344.2 | 70.0% | 432.6 | 300.0 | 595.2 | 295.2 | 52.5 | 4250.0 | 305.4 | 577.7 | 293.8 | 475.0 | `1.89x` (med `1.62x`) | `+9.9%` (med `+7.4%`) |
| `Tomatoes` | All Active Markets (`2019-01..2026-09`, `50` mkts) | 4136 | 50 | 485.0 | 335.2 | 69.1% | 430.0 | 296.1 | 591.6 | 295.4 | 52.5 | 4250.0 | 303.5 | 566.8 | 287.5 | 474.2 | `1.87x` (med `1.65x`) | `+9.7%` (med `+7.7%`) |
| **`Yam (white)`** | **Tier-1 Modeling Window (`2019-01..2026-09`, `19` mkts)** | 1603 | 19 | 405.3 | 213.7 | 52.7% | 400.0 | 217.5 | 540.0 | 322.5 | 75.0 | 1500.0 | 285.8 | 418.5 | 261.1 | 400.0 | `1.46x` (med `1.53x`) | `+5.8%` (med `+6.5%`) |
| `Yam (white)` | All Active Markets (`2019-01..2026-09`, `47` mkts) | 2727 | 47 | 412.5 | 288.0 | 69.8% | 375.0 | 220.0 | 519.4 | 299.4 | 63.3 | 2958.2 | 300.7 | 450.3 | 240.5 | 381.5 | `1.50x` (med `1.59x`) | `+6.2%` (med `+7.1%`) |
| `Yam` | Exploration-Only Tier-1 (`2019-01..2026-09`, `17` mkts) | 1427 | 17 | 335.9 | 146.6 | 43.6% | 320.0 | 234.2 | 403.3 | 169.2 | 74.2 | 1400.0 | 250.2 | 351.6 | 215.6 | 325.0 | `1.41x` (med `1.51x`) | `+5.2%` (med `+6.3%`) |
| `Yam` | Exploration-Only All Markets (`2019-01..2026-09`, `49` mkts) | 2721 | 49 | 348.7 | 229.0 | 65.7% | 305.0 | 207.2 | 412.5 | 205.2 | 55.0 | 2766.7 | 250.9 | 378.2 | 212.1 | 310.0 | `1.51x` (med `1.46x`) | `+6.3%` (med `+5.8%`) |
| `Yam` | Exploration-Only Pre-2019 (`2013-01..2018-12`, `4` mkts) | 99 | 4 | 323.6 | 126.8 | 39.2% | 300.0 | 249.5 | 350.0 | 100.5 | 112.0 | 777.2 | - | - | - | - | - | - |

---

## 4. Proposed Plan for Phase 3 (Web Application)

Per `AGENTS.md` (*"At the end of each phase, STOP and write a summary in docs/STATUS.md... Do not start the next phase until the owner replies"*), we stop here and await your review before starting **Phase 3 (Web Application)**:

1. **Data Contract Ready ([`web/public/data/forecasts.json`](file:///home/brian/projets-ds/benin-agromarket/web/public/data/forecasts.json)):**
   - Contains all `111` Tier-1 series with historical observations, `2025-10..2026-09` out-of-sample backtest trajectories, `2026-10..2026-12` (`h=1, 2, 3`) point forecasts and `80%`/`90%` prediction intervals, per-market and per-product accuracy metrics (`MAE`, `RMSE`, `MAPE`, interval coverage), and explicit French + English coverage explanations for all `51` active Benin markets.
2. **Phase 3 UI & Design Plan (`BRIEF.md`):**
   - Build a fast, mobile-first, accessible French/English web application following the editorial/terracotta design brief in `BRIEF.md` with four views:
     1. **Vue d'ensemble (Overview & Benin Map):** Interactive market map by agro-ecological zone, current staple prices (`2026-09`), and 3-month ahead signals.
     2. **Explorateur de Marché (Market & Product Explorer):** Full historical trajectory (`2007–2026` with explicit `2017–2018` hiatus break), seasonal profile by latitude zone, and variety comparison (`Yam (white)` vs `Yam`).
     3. **Prévisions & Intervalles (Forecasts & Decision Tool):** Multi-horizon fan chart (`h=1, 2, 3` with `80%` and `90%` bands), recent out-of-sample backtest overlay, and market-specific accuracy badge.
     4. **Méthode, Modèles & Limites (Method, Models & Honest Limits):** Interactive model comparison table (`Baselines` vs `ETS/SARIMAX/Ridge_ARX` vs `HGBR`), NASA POWER weather ablation results, operational limits, and mandatory `CC BY-IGO 3.0` / NASA / FAOSTAT attributions.

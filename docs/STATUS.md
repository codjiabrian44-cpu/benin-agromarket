# Project Status — Bénin AgroMarket (`docs/STATUS.md`)

**Date:** 2026-10-25  
**Current Phase:** **Phase 1 Complete** (Step 0 Corrections + Phase 1(a) Cleaning & NASA POWER Pipeline + Phase 1(b) Exploratory Data Analysis & Vector Figures)  
**Status:** **STOPPED at End of Phase 1** — awaiting owner review and confirmation before starting Phase 2 (Modeling).

Every statistic and table in this report is produced deterministically by [`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py), [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py), and [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) and saved in [`docs/tables/`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/). All 5 publication-grade vector `.svg` figures are saved in [`docs/figures/`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/).

---

## 1. Executive Summary of Completed Work (Phase 1)

1. **Step 0 — Script-Backed Numbers & Coverage Audit ([`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py)):**
   - Replaced all hand-typed coverage statistics with deterministic script outputs in [`docs/tables/raw_dataset_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/raw_dataset_summary.md), [`docs/tables/coverage_by_commodity.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/coverage_by_commodity.md), [`docs/tables/yearly_observation_density.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/yearly_observation_density.md), [`docs/tables/coverage_by_market.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/coverage_by_market.md), and [`docs/tables/tier1_markets_by_product.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/tier1_markets_by_product.md).
   - Explicitly separated full-history coverage (`2007–2026`, which spans the `2017–2018` reporting hiatus) from the `2019-01..2026-09` (`93`-month) primary modeling window.
2. **Phase 1(a) — Central Config, NASA POWER Ingestion & Cleaning Pipeline ([`src/config.py`](file:///home/brian/projets-ds/benin-agromarket/src/config.py), [`src/ingest/download_nasa_power.py`](file:///home/brian/projets-ds/benin-agromarket/src/ingest/download_nasa_power.py), [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py)):**
   - Downloaded monthly NASA POWER MERRA-2 agroclimatology (`PRECTOTCORR`, `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`) across all **`23` unique `0.5° × 0.625°` grid cells** covering Benin's `51` active markets (`2006-01..2026-09`, `5,727` grid-month rows, `474,338` bytes, `0` missing `-999` values, SHA-256 `1a20724807476b3ca20948e6a595a4503bf80d0ede17943f96634785548714f3`; [`docs/tables/nasa_power_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/nasa_power_summary.md)).
   - Verified `0` duplicate `(commodity, market_id, pricetype, unit, date)` keys and `0` non-positive prices across all `146,501` raw rows; stripped the `18` inactive metadata markets (`data/processed/markets_active.csv`, `51` active markets).
   - Flagged extreme levels (`|robust_z| > 3.5`) and consecutive month-over-month jumps (`|Δ log(price)| > ln(2)`) without deleting a single observation (`data/processed/prices_cleaned_all.csv`, `14,551` rows; [`docs/tables/cleaning_audit_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/cleaning_audit_summary.md)).
   - Built the regular `93`-month Tier-1 modeling panel (`data/processed/modeling_panel_2019_2026.csv`, `10,323` rows) with strictly lagged NASA POWER features (using a strictly pre-2019 `2006–2018` climatology for `precip_anom_z_lag1m`) and zero silent imputation (`is_observed=0, price=""` on unobserved months).
3. **Phase 1(b) — Exploratory Data Analysis & Vector Figures ([`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py)):**
   - Generated 6 EDA tables (`CSV` + `Markdown`) in [`docs/tables/`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/):
     - [`docs/tables/eda_summary_by_product.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_summary_by_product.md)
     - [`docs/tables/eda_seasonality_profile.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_seasonality_profile.md)
     - [`docs/tables/eda_market_differences.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_market_differences.md)
     - [`docs/tables/eda_yam_variety_comparison.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_yam_variety_comparison.md)
     - [`docs/tables/eda_abrupt_changes.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_abrupt_changes.md)
     - [`docs/tables/eda_weather_lag_correlations.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_weather_lag_correlations.md)
   - Rendered 5 vector `.svg` figures in [`docs/figures/`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/):
     - [`docs/figures/fig1_regimes_and_trends_2007_2026.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig1_regimes_and_trends_2007_2026.svg)
     - [`docs/figures/fig2_seasonality_by_zone.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig2_seasonality_by_zone.svg)
     - [`docs/figures/fig3_market_differences_tier1.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig3_market_differences_tier1.svg)
     - [`docs/figures/fig4_abrupt_changes_and_outliers.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig4_abrupt_changes_and_outliers.svg)
     - [`docs/figures/fig5_weather_lag_relationships.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig5_weather_lag_relationships.svg)

---

## 2. Phase 0 Audit & Phase 1(a) Cleaning Summary Tables

### 2.1 Global Coverage by Commodity (`wfp_food_prices_ben.csv`)
*Source script: [`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py) → [`docs/tables/coverage_by_commodity.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/coverage_by_commodity.md)*

| Target / Group | Commodity | Pricetype & Unit | Total Obs (All) | Active Markets (All) | Date Range (All) | Unique / Expected Months (All) | Obs (2019-01..2026-09) | Markets >=60m (2019-26) | Tier-1 Markets >=80/93m (2019-26) |
| :--- | :--- | :--- | ---: | ---: | :--- | ---: | ---: | ---: | :--- |
| **Maize (Primary)** | **`Maize (white)`** | `Retail, KG` | 4868 | 51 | `2007-01-15..2026-09-15` | `208 / 237` | 4239 | `50 / 50` | **`49 / 50`** |
| **Tomato (Primary)** | **`Tomatoes`** | `Retail, KG` | 4136 | 50 | `2019-01-15..2026-09-15` | `90 / 93` | 4136 | `49 / 50` | **`43 / 50`** |
| **Yam (Primary — White/Kokoro)** | **`Yam (white)`** | `Retail, KG` | 2727 | 47 | `2019-01-15..2026-09-15` | `89 / 93` | 2727 | `31 / 47` | **`19 / 47`** |
| Yam (Exploration — Early/Laboko) | `Yam` | `Retail, KG` | 2820 | 49 | `2013-01-15..2026-09-15` | `128 / 165` | 2721 | `28 / 49` | `17 / 49` |

### 2.2 Cleaning & Feature Pipeline Audit Summary
*Source script: [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py) → [`docs/tables/cleaning_audit_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/cleaning_audit_summary.md)*

| Product | Role | Obs (All 2007-2026) | Obs Pre-2019 (Exploration) | Obs 2019-2026 (Modern) | Outliers Flagged (Level \|z\|>3.5) | Outliers Flagged (MoM Jump >=2x) | Total Outliers Flagged (0 Deleted) | Tier-1 Markets (>=80m) | Tier-1 Grid Rows (93m) | Tier-1 Observed Rows | Tier-1 Unobserved Rows (price='') | Isolated 1m Gaps (price_interp_1m_max) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Maize (white)` | `forecast_primary` | 4868 | 629 | 4239 | 32 | 14 | 43 | 49 | 4557 | 4162 | 395 | 75 |
| `Tomatoes` | `forecast_primary` | 4136 | 0 | 4136 | 44 | 288 | 320 | 43 | 3999 | 3664 | 335 | 76 |
| `Yam (white)` | `forecast_primary` | 2727 | 0 | 2727 | 113 | 43 | 150 | 19 | 1767 | 1603 | 164 | 50 |
| `Yam` | `exploration_only` | 2820 | 99 | 2721 | 45 | 67 | 108 | 17 | - | - | - | - |

---

## 3. Phase 1(b) Exploratory Data Analysis Findings (`src/analysis/eda.py`)

### 3.1 Distributional Summary & Multi-Year Price Trends (`2007–2026`)
*Source script: [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) → [`docs/tables/eda_summary_by_product.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_summary_by_product.md) | Visualized in [`docs/figures/fig1_regimes_and_trends_2007_2026.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig1_regimes_and_trends_2007_2026.svg)*

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

**Key Insights ([`docs/figures/fig1_regimes_and_trends_2007_2026.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig1_regimes_and_trends_2007_2026.svg)):**
- **Distinct Volatility Regimes Across Products:** Across `2019–2026` Tier-1 markets, `Maize (white)` is the most stable staple (`Mean = 201.8 XOF/kg`, `Median = 197.0 XOF/kg`, `IQR = 76.4 XOF/kg`, `CV = 29.7%`), followed by `Yam (white)` (`Mean = 405.3 XOF/kg`, `Median = 400.0 XOF/kg`, `IQR = 322.5 XOF/kg`, `CV = 52.7%`), whereas perishable `Tomatoes` exhibits extreme dispersion (`Mean = 491.5 XOF/kg`, `Median = 432.6 XOF/kg`, `IQR = 295.2 XOF/kg`, `CV = 70.0%`).
- **Divergent Secular Trajectories (`2019` vs `2025-10..2026-09`):** While `Tomatoes` (`1.89x` mean, `+9.9%` CAGR) and `Yam (white)` (`1.46x` mean, `1.53x` median, `+5.8%` CAGR) experienced persistent nominal price appreciation between `2019` and the final 12 months (`2025-10..2026-09`), `Maize (white)` experienced a pronounced multi-year surge in `2021–2024` followed by a strong downward correction in `2025–2026` back toward `149.1 XOF/kg` (`1.05x` vs `2019` mean of `141.6 XOF/kg`).
- **Benefit of Tier-1 Filtering for `Yam (white)`:** Restricting `Yam (white)` from all `47` markets (`CV = 69.8%`, max `2,958.2 XOF/kg`) to the `19` Tier-1 markets (`CV = 52.7%`, max `1,500.0 XOF/kg`) removes erratic thin-market spikes where white yam is only sporadically sold.

---

### 3.2 Seasonality by Product & Agro-Ecological Latitude Zone
*Source script: [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) → [`docs/tables/eda_seasonality_profile.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_seasonality_profile.md) | Visualized in [`docs/figures/fig2_seasonality_by_zone.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig2_seasonality_by_zone.svg)*

| Product | Agro-Ecological Zone | Tier-1 Markets | Obs | Trough Month (Index) | Peak Month (Index) | Peak-to-Trough Spread (Index pts / %) | Jan | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov |
| :--- | :--- | ---: | ---: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`Maize (white)`** | **All Tier-1 (National)** | 49 | 4162 | **Nov (`87.1`)** | **May (`108.1`)** | **`21.0 pts (+24.1%)`** | 98.4 | 107.5 | 108.1 | 107.0 | 108.0 | 103.0 | 96.0 | 89.4 | 87.1 |
| `Maize (white)` | South (`<7.5°N`, Bimodal) | 28 | 2367 | Nov (`88.8`) | May (`110.3`) | `21.5 pts (+24.2%)` | 99.7 | 109.4 | 110.3 | 108.6 | 106.1 | 96.8 | 89.6 | 89.4 | 88.8 |
| `Maize (white)` | Center (`7.5°–9.5°N`, Transition) | 7 | 601 | Oct (`86.1`) | Jun (`109.3`) | `23.2 pts (+27.0%)` | 97.4 | 106.9 | 107.8 | 109.3 | 107.8 | 104.8 | 93.2 | 86.1 | 87.5 |
| `Maize (white)` | North (`>=9.5°N`, Unimodal) | 14 | 1194 | Nov (`83.8`) | **Aug (`114.1`)** | **`30.3 pts (+36.1%)`** | 96.5 | 103.9 | 103.8 | 102.5 | 111.7 | 114.1 | 109.9 | 91.1 | 83.8 |
| **`Tomatoes`** | **All Tier-1 (National)** | 43 | 3664 | **Sep (`69.0`)** | **Jun (`140.2`)** | **`71.1 pts (+103.1%)`** | 95.2 | 121.6 | 139.7 | 140.2 | 115.2 | 79.6 | 69.0 | 73.0 | 75.3 |
| `Tomatoes` | South (`<7.5°N`, Bimodal) | 27 | 2278 | Sep (`63.9`) | May (`146.2`) | **`82.4 pts (+129.0%)`** | 98.0 | 127.7 | 146.2 | 144.8 | 111.1 | 70.0 | 63.9 | 71.8 | 72.1 |
| `Tomatoes` | Center (`7.5°–9.5°N`, Transition) | 6 | 526 | Oct (`73.1`) | May (`130.3`) | `57.2 pts (+78.2%)` | 97.1 | 116.2 | 130.3 | 124.3 | 103.5 | 91.0 | 78.6 | 73.1 | 78.5 |
| `Tomatoes` | North (`>=9.5°N`, Unimodal) | 10 | 860 | Oct (`76.0`) | Jun (`137.6`) | `61.5 pts (+80.9%)` | 87.2 | 108.9 | 128.0 | 137.6 | 132.9 | 97.3 | 76.7 | 76.0 | 82.0 |
| **`Yam (white)`** | **All Tier-1 (National)** | 19 | 1603 | **Oct (`85.0`)** | **Jul (`121.9`)** | **`37.0 pts (+43.5%)`** | 91.2 | 103.4 | 109.1 | 112.9 | 121.9 | 116.1 | 92.0 | 85.0 | 86.8 |
| `Yam (white)` | South (`<7.5°N`, Bimodal) | 8 | 675 | Nov (`88.5`) | Jul (`117.3`) | `28.8 pts (+32.6%)` | 91.7 | 102.7 | 108.2 | 110.8 | 117.3 | 114.3 | 94.5 | 88.8 | 88.5 |
| `Yam (white)` | Center (`7.5°–9.5°N`, Transition) | 5 | 420 | Oct (`86.3`) | Jul (`119.7`) | `33.4 pts (+38.8%)` | 91.3 | 106.5 | 108.7 | 109.5 | 119.7 | 114.8 | 90.0 | 86.3 | 87.7 |
| `Yam (white)` | North (`>=9.5°N`, Unimodal) | 6 | 508 | Oct (`78.9`) | Jul (`129.8`) | **`50.9 pts (+64.5%)`** | 90.4 | 101.9 | 110.7 | 118.0 | 129.8 | 119.8 | 90.4 | 78.9 | 84.0 |
| `Yam` (Exploration) | All Tier-1 (National) | 17 | 1427 | Nov (`84.8`) | Aug (`120.7`) | `35.9 pts (+42.4%)` | 90.4 | 104.2 | 107.5 | 114.8 | 118.9 | 120.7 | 90.6 | 84.8 | 84.8 |

**Key Insights ([`docs/figures/fig2_seasonality_by_zone.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig2_seasonality_by_zone.svg)):**
- **Bimodal South vs. Unimodal North Phase Shift in `Maize (white)`:** In Southern Benin (`<7.5°N`, bimodal rainfall), the first maize harvest arrives in July–August, pulling the seasonal index down from **`110.3` in May** to **`96.8` in August** and **`89.6` in September**. In contrast, in Northern Benin (`>=9.5°N`, single rainy season), stocks reach maximum depletion in **July (`111.7`) and August (`114.1`)** before the main October–November harvest (`83.8` in November), yielding a **`+36.1%` peak-to-trough spread** in the North vs **`+24.2%`** in the South.
- **Doubling of `Tomatoes` Prices Every Lean Season:** Fresh tomato prices more than double on average between the main harvest trough in **September (`69.0`)** and the May–June lean-season peak (**`139.7` in May, `140.2` in June**, **`+103.1%`** nationally, and **`+129.0%`** in the South where May reaches `146.2` vs September `63.9`).
- **Pre-Harvest Scarcity Peak in `Yam (white)`:** White yam peaks in **July (`121.9` nationally, `129.8` in the North)** right before the new tuber harvest begins in August–October (**October trough `85.0` nationally, `78.9` in the North**, a **`+64.5%`** seasonal swing in Northern markets).

---

### 3.3 Spatial Market Differences: Producer Hubs vs. Consumer Markets
*Source script: [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) → [`docs/tables/eda_market_differences.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_market_differences.md) | Visualized in [`docs/figures/fig3_market_differences_tier1.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig3_market_differences_tier1.svg)*

- **`Maize (white)` (`49` Tier-1 markets, Max/Min Market Mean Ratio = `1.79x`, Cross-Market CV = `13.2%`):**
  - **Lowest-Cost Producer Markets:** `Cobly` (`149.1 XOF/kg`, `-26.2%` vs Tier-1 mean), `Azovè` (`160.8 XOF/kg`, `-20.4%`), `Tchaourou` (`163.1 XOF/kg`, `-19.2%`), `Kérou` (`163.3 XOF/kg`, `-19.2%`), `Glazoué` (`167.8 XOF/kg`, `-16.9%`), and `Kétou` (`169.8 XOF/kg`, `-15.9%`).
  - **Highest-Cost Consumer/Deficit Markets:** `Dantokpa` (Cotonou, `#49/49` at `267.4 XOF/kg`, median `274.7 XOF/kg`, `+32.4%` above Tier-1 mean), `Sèdjè-Dénou` (`258.5 XOF/kg`, `+28.0%`), and `Hozin` (`244.9 XOF/kg`, `+21.2%`). The structural spatial spread between `Dantokpa` (`267.4 XOF/kg`) and wholesale hub `Glazoué` (`167.8 XOF/kg`) is **`+99.6 XOF/kg` (`+59.4%`)**.
- **`Tomatoes` (`43` Tier-1 markets, Max/Min Market Mean Ratio = `6.33x`, Cross-Market CV = `33.8%`):**
  - **Lowest-Cost Markets:** `Bassila` (`217.7 XOF/kg`, median `200.0 XOF/kg`, `-55.7%`), `Dasso` (`301.9 XOF/kg`, `-38.6%`), `Bembèrèkè` (`339.6 XOF/kg`, `-30.9%`), and `Bohicon` (`373.3 XOF/kg`, `-24.1%`).
  - **Major Urban & Deficit Markets:** `Parakou` (`421.0 XOF/kg`), `Malanville (CBM)` (`429.6 XOF/kg`), `Dantokpa` (`481.3 XOF/kg`), `Ouando` (`493.2 XOF/kg`), `Glazoué` (`495.5 XOF/kg`), `Djougou` (`599.6 XOF/kg`), `Dassa-Zoumè` (`670.6 XOF/kg`), `Covè` (`749.8 XOF/kg`), and `Tatonnoukon` (`1,377.0 XOF/kg`, median `782.5 XOF/kg`).
- **`Yam (white)` (`19` Tier-1 markets, Max/Min Market Mean Ratio = `4.07x`, Cross-Market CV = `39.2%`):**
  - **Lowest-Cost Northern/Central Production Basins:** `Nikki` (`#1/19` at `170.1 XOF/kg`, median `90.0 XOF/kg`, `-58.1%`), `Bembèrèkè` (`186.6 XOF/kg`, `-54.1%`), `Glazoué` (`190.3 XOF/kg`, median `170.0 XOF/kg`, `-53.2%`), `Bassila` (`193.1 XOF/kg`, `-52.5%`), and `Ouesse` (`227.2 XOF/kg`, `-44.1%`).
  - **Highest-Cost Consumer/Retail Markets:** `Comé` (`503.2 XOF/kg`, `+23.9%`), `Dantokpa` (`562.4 XOF/kg`, median `566.8 XOF/kg`, `+38.4%`), `Natitingou` (`582.0 XOF/kg`, `+43.3%`), `Dassa-Zoumè` (`682.7 XOF/kg`, `+68.1%`), and `Savalou` (`692.7 XOF/kg`, `+70.5%`).

---

### 3.4 Quantitative Variety Comparison: `Yam (white)` vs. `Yam` (Exploration-Only)
*Source script: [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) → [`docs/tables/eda_yam_variety_comparison.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_yam_variety_comparison.md)*

| Grouping | Slice / Market | Concurrent Market-Months | `Yam (white)` Mean (Med) XOF/kg | `Yam` Mean (Med) XOF/kg | Mean Signed Spread (`Yam - Yam white`) | Mean Abs Diff `\|Yam - Yam white\|` | Mean Spread % (`Yam` vs `Yam white`) |
| :--- | :--- | ---: | :--- | :--- | ---: | ---: | ---: |
| **Summary** | **All Concurrent Market-Months (`2019–2026`)** | `1,956` | `450.7` (med `408.5`) | `318.4` (med `293.8`) | `-132.3` | `141.3` | `-24.5%` |
| **Summary** | **Both Tier-1 Markets Concurrent (`14` Shared Markets)** | `1,150` | `439.8` (med `427.9`) | `319.6` (med `300.0`) | `-120.2` | `122.6` | `-24.9%` |
| By Market | `Dantokpa` (`YW=88m, Y=92m`) | `88` | `562.4` (med `566.8`) | `358.4` (med `317.2`) | `-204.0` | `207.9` | `-34.2%` |
| By Market | `Glazoué` (`YW=89m, Y=86m`) | `85` | `192.9` (med `170.0`) | `155.4` (med `129.0`) | `-37.5` | `40.8` | `-19.9%` |
| By Market | `Savalou` (`YW=84m, Y=85m`) | `84` | `692.7` (med `650.0`) | `475.0` (med `487.5`) | `-217.7` | `219.7` | `-30.0%` |
| By Market | `Bohicon` (`YW=85m, Y=82m`) | `81` | `456.1` (med `425.0`) | `270.8` (med `256.2`) | `-185.3` | `185.3` | `-39.7%` |
| By Market | `Natitingou` (`YW=84m, Y=80m`) | `74` | `634.6` (med `661.9`) | `398.8` (med `375.2`) | `-235.8` | `238.8` | `-34.6%` |
| By Market | `Ouando` (`YW=82m, Y=83m`) | `78` | `452.6` (med `440.6`) | `296.1` (med `300.0`) | `-156.6` | `156.6` | `-35.4%` |
| Non-Overlapping Hub | `Djougou` (`YW=86m, Y=1m`) | `0` | `338.5` (med `295.0`) | Only `1` obs (`2020-08`) | `-` | `-` | `-` |
| Non-Overlapping Hub | `Nikki` (`YW=85m, Y=1m`) | `0` | `170.1` (med `90.0`) | Only `1` obs (`2020-08`) | `-` | `-` | `-` |

- Across `1,956` concurrent `(market, month)` pairs in `2019–2026`, `Yam (white)` averages **`450.7 XOF/kg`** (median `408.5 XOF/kg`) vs **`318.4 XOF/kg`** (median `293.8 XOF/kg`) for generic `Yam`, a mean absolute difference of **`141.3 XOF/kg`** (`122.6 XOF/kg` across the `1,150` concurrent observations in the `14` shared Tier-1 markets). This confirms Decision 1: merging the two WFP series would introduce severe artificial jumps whenever one variety is unrecorded.

---

### 3.5 Empirical Candidate Shocks & Synchronized Abrupt Price Changes (`2019–2026`)
*Source script: [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) → [`docs/tables/eda_abrupt_changes.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_abrupt_changes.md) & [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py) → [`docs/tables/cleaning_audit_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/cleaning_audit_summary.md) | Visualized in [`docs/figures/fig4_abrupt_changes_and_outliers.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig4_abrupt_changes_and_outliers.svg)*

- **Strict Empirical Reporting (Decision 3):** All candidate shocks and abrupt changes in [`docs/tables/eda_abrupt_changes.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_abrupt_changes.md) (`43` synchronized multi-market surge/drop or jump-cluster months) are identified purely from price data (`>= 25%` of active Tier-1 markets surging `>= +35%` MoM or dropping `<= -30%` MoM, national Tier-1 median shifting `>= 25%` MoM, or `>= 3` markets triggering `is_outlier_jump = 1` in the same month). **No unverified external causes (e.g., border closures, policy changes, or weather shocks) are asserted.**
- **Empirical Highlights from [`docs/tables/eda_abrupt_changes.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_abrupt_changes.md):**
  - **`Tomatoes` (`37` synchronized multi-market surge/drop events; `288` jump outliers `|ΔlnP| > ln2` and `44` level outliers `|z| > 3.5` across `2019–2026`):**
    - Largest synchronized upward surges: **`2020-10`** (`22/42` Tier-1 markets [`52.4%`] surging `>= +35%` MoM; Tier-1 median `+47.6%` to `314 XOF/kg`; `10` jump outliers led by `Covè` `+1204%` and `Kalalé` `+282%`), **`2021-12`** (`16/43` markets [`37.2%`] surging `>= +35%`; median `+33.3%` to `400 XOF/kg`), **`2023-04`** (`15/43` markets [`34.9%`] surging `>= +35%`; median `+25.5%` to `625 XOF/kg`), **`2024-05` & `2024-06`** (`13/43` [`30.2%`] and `11/42` [`26.2%`] markets surging `>= +35%`; Tier-1 median reaching **`680 XOF/kg` (`+27.5%`) in `2024-05`** and **`862 XOF/kg` (`+26.7%`, mean `919 XOF/kg`) in `2024-06`**), and **`2025-04`** (`12/43` markets [`27.9%`]; median `+30.8%` to `675 XOF/kg`).
    - Largest synchronized harvest drops: **`2020-08`** (`28/43` markets [`65.1%`] dropping `<= -30%` MoM; median `-50.7%` to `206 XOF/kg`; `20` jump outliers), **`2021-08`** (`26/43` markets [`60.5%`] dropping `<= -30%`; median `-45.2%` to `346 XOF/kg`; `16` jump outliers), **`2024-08`** (`25/43` markets [`58.1%`] dropping `<= -30%`; median `-32.1%` to `425 XOF/kg`), and **`2025-08`** (`21/42` markets [`50.0%`] dropping `<= -30%`; median `-32.1%` to `374 XOF/kg`).
  - **`Yam (white)` (`6` synchronized multi-market surge/drop events; `43` jump outliers and `113` level outliers):**
    - Notable synchronized shifts include **`2019-09`** (`5/19` markets [`26.3%`] dropping `<= -30%` MoM; median `-20.0%` to `230 XOF/kg`), **`2020-01`** (Tier-1 median surging **`+49.3%` MoM** from `175` to `261 XOF/kg`), and **`2021-09`** (`7/19` markets [`36.8%`] dropping `<= -30%` MoM; median `-17.5%` to `412 XOF/kg`).
  - **`Maize (white)` (`14` market-level jump outliers `|ΔlnP| > ln2` and `32` level outliers `|z| > 3.5` in [`docs/tables/cleaning_audit_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/cleaning_audit_summary.md)):**
    - Unlike perishable tomatoes, `Maize (white)` never had $\ge 25\%$ of Tier-1 markets jumping $\ge +35\%$ in a single month (`0` rows under the $\ge 25\%$ threshold in [`docs/tables/eda_abrupt_changes.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_abrupt_changes.md)), reflecting storable grain buffering; its multi-year surge (`2021–2024`) unfolded through cumulative monthly steps rather than single-month nationwide doublings.

---

### 3.6 Lagged Agroclimatic Correlations (`NASA POWER` vs. Detrended Log Price Anomalies)
*Source script: [`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) → [`docs/tables/eda_weather_lag_correlations.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_weather_lag_correlations.md) | Visualized in [`docs/figures/fig5_weather_lag_relationships.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig5_weather_lag_relationships.svg)*

| Product | Agro-Ecological Zone | `precip_lag3m` (`t-3`) Pearson `r` (Spearman `rho`) | `precip_roll3m_lag1` (`t-3..t-1`) Pearson `r` (`rho`) | `t2m_lag1m` (`t-1`) Pearson `r` (`rho`) | `t2m_max_lag1m` (`t-1`) Pearson `r` (`rho`) | `rh2m_lag1m` (`t-1`) Pearson `r` (`rho`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Maize (white)`** | **All Tier-1 (`4,052` pairs)** | **`-0.243` (`-0.247`)** | `-0.142` (`-0.148`) | **`+0.233` (`+0.300`)** | `+0.147` (`+0.177`) | `+0.007` (`-0.065`) |
| `Maize (white)` | South (`<7.5°N`, `2,292` pairs) | `-0.263` (`-0.275`) | `-0.233` (`-0.229`) | **`+0.400` (`+0.401`)** | `+0.277` (`+0.266`) | `-0.132` (`-0.165`) |
| `Maize (white)` | Center (`7.5°–9.5°N`, `583` pairs) | **`-0.320` (`-0.361`)** | `-0.259` (`-0.258`) | `+0.308` (`+0.330`) | `+0.269` (`+0.280`) | `-0.088` (`-0.120`) |
| `Maize (white)` | North (`>=9.5°N`, `1,177` pairs) | `-0.196` (`-0.168`) | `-0.016` (`+0.000`) | `+0.146` (`+0.180`) | `+0.065` (`+0.066`) | `+0.087` (`+0.101`) |
| **`Tomatoes`** | **All Tier-1 (`3,580` pairs)** | **`-0.384` (`-0.422`)** | **`-0.340` (`-0.357`)** | **`+0.360` (`+0.476`)** | `+0.287` (`+0.359`) | `-0.103` (`-0.267`) |
| `Tomatoes` | South (`<7.5°N`, `2,212` pairs) | `-0.399` (`-0.469`) | `-0.376` (`-0.415`) | **`+0.521` (`+0.543`)** | `+0.375` (`+0.414`) | `-0.258` (`-0.343`) |
| `Tomatoes` | Center (`7.5°–9.5°N`, `516` pairs) | **`-0.470` (`-0.487`)** | **`-0.473` (`-0.471`)** | `+0.286` (`+0.341`) | `+0.357` (`+0.438`) | `-0.221` (`-0.352`) |
| `Tomatoes` | North (`>=9.5°N`, `852` pairs) | `-0.332` (`-0.320`) | `-0.251` (`-0.189`) | `+0.324` (`+0.416`) | `+0.328` (`+0.373`) | `-0.052` (`-0.132`) |
| **`Yam (white)`** | **All Tier-1 (`1,581` pairs)** | **`-0.245` (`-0.246`)** | `-0.092` (`-0.064`) | **`+0.186` (`+0.220`)** | `+0.123` (`+0.126`) | `+0.044` (`+0.019`) |
| `Yam (white)` | Center (`7.5°–9.5°N`, `410` pairs) | `-0.284` (`-0.301`) | `-0.169` (`-0.156`) | `+0.155` (`+0.199`) | `+0.115` (`+0.137`) | `+0.025` (`+0.003`) |
| `Yam (white)` | North (`>=9.5°N`, `503` pairs) | **`-0.311` (`-0.311`)** | `-0.146` (`-0.129`) | **`+0.268` (`+0.368`)** | `+0.212` (`+0.269`) | `+0.051` (`-0.014`) |

**Key Insights ([`docs/figures/fig5_weather_lag_relationships.svg`](file:///home/brian/projets-ds/benin-agromarket/docs/figures/fig5_weather_lag_relationships.svg)):**
- **Strong Negative 3-Month Lagged Rainfall Correlation (`precip_lag3m`):** Across all three crops, rainfall 3 months prior (`t-3`) correlates negatively with detrended seasonal price anomalies (`r = -0.384`, `rho = -0.422` for `Tomatoes`; `r = -0.245` for `Yam (white)`; `r = -0.243` for `Maize (white)`), reflecting the agronomic growth-to-harvest lag (~90 days from vegetative rainfall peak to market harvest arrival).
- **Positive Lagged Temperature Correlation (`t2m_lag1m`):** High temperatures in `t-1` (late dry season / onset of rains) coincide with lean-season scarcity (`r = +0.521`, `rho = +0.543` for `Tomatoes` in the South; `r = +0.400` for `Maize (white)` in the South).
- **Important Modeling Caveat for Phase 2 (`precip_anom_z_lag1m`):** While raw lagged rainfall/temperature capture the agro-climatic seasonal cycle, the deseasonalized rainfall z-score (`precip_anom_z_lag1m`, standardized against `2006–2018` monthly means) has a much smaller linear correlation with monthly price anomalies (`r = +0.092` for `Maize (white)`, `r = +0.047` for `Tomatoes`, `r = +0.011` for `Yam (white)`). Therefore, Phase 2 must rigorously test via ablation whether NASA POWER features add predictive power beyond deterministic calendar seasonality (`month` + agro-ecological zone).

---

## 4. Proposed Plan & Open Questions for Phase 2 (Modeling)

Per `AGENTS.md` (*"At the end of each phase, STOP and write a summary in docs/STATUS.md... Do not start the next phase until the owner replies"* and *"Ask before installing any package"*), we stop here and request your confirmation on the following choices before starting **Phase 2**:

1. **Permission to Install Scientific/ML Packages in `.venv` (`requirements.txt`):**
   - Currently `.venv` contains only the Python 3.12 standard library.
   - May we install standard forecasting dependencies (`numpy`, `scipy`, `pandas`, `scikit-learn`, `statsmodels`, `lightgbm`) into `.venv` and pin exact versions in `requirements.txt`? (Alternatively, we can also implement baselines, Holt-Winters / ETS, Ridge/Linear autoregressive models, and tree ensembles directly or with minimal dependencies if you prefer a lightweight stack.)
2. **Rolling-Origin Evaluation & Forecast Horizons ($h = 1, 2, 3$ months ahead):**
   - We propose evaluating multi-step horizons **$h \in \{1, 2, 3\}$ months ahead** using **expanding-window rolling-origin cross-validation** across two historical backtest folds (e.g., **Fold 1:** `2023-10..2024-09` [`12` origins] and **Fold 2 / Holdout Test:** `2025-10..2026-09` [`12` origins]), reporting **MAE, RMSE, and MAPE per product and per market**, plus **80% and 90% empirical conformal / quantile prediction interval coverage**.
3. **Model Hierarchy & Honest Baseline Comparison:**
   - **Step 1 — Baselines:** (a) `Naive_LastValue` ($\hat{y}_{t+h|t} = y_t$), (b) `Seasonal_Naive_12m` ($\hat{y}_{t+h|t} = y_{t+h-12}$), and (c) `Seasonal_Ratio_Naive` (local level $y_t$ scaled by the market/zone seasonal index ratio from training data).
   - **Step 2 — Classical Time-Series Models:** Per-market / hierarchical **ETS (Holt-Winters additive/multiplicative on $\log P$)** and **SARIMA / Ridge Autoregressive (`ARX(1, 2, 12)` + Fourier seasonality)**.
   - **Step 3 — Gradient Boosting (`LightGBM` / `HistGradientBoostingRegressor`) with Weather Ablation:** Pooled panel model with market fixed effects/quantiles, autoregressive lags, seasonal Fourier features, and an explicit ablation with vs. without lagged NASA POWER features (`precip_lag1m..3m`, `precip_anom_z_lag1m`, `t2m_lag1m`). Any model that fails to beat the baselines will be reported transparently.

# Architectural & Methodological Decisions (`docs/DECISIONS.md`)

**Last updated:** 2026-10-25  
**Phase:** Phase 1 (Complete — Phase 1(a) Cleaning & Phase 1(b) EDA)

Every major scope, data engineering, statistical, and licensing decision for **Bénin AgroMarket** is recorded below with its quantitative justification and supporting script-generated table in [`docs/tables/`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/).

---

## Decision 1 — Product Scope, Market Tiering & Single Central Configuration (`src/config.py`)

### Choice
1. **Primary Forecasting Scope (`role = "forecast_primary"`):**
   - **Maize:** `Maize (white)` (`Retail, KG, XOF, actual`) — **49 Tier-1 markets** ($\ge 80 / 93$ observed months in `2019-01..2026-09`).
   - **Tomato:** `Tomatoes` (`Retail, KG, XOF, actual`) — **43 Tier-1 markets** ($\ge 80 / 93$ observed months in `2019-01..2026-09`).
   - **Yam:** `Yam (white)` (*igname blanche / kokoro*, `Retail, KG, XOF, actual`) — **19 Tier-1 markets** ($\ge 80 / 93$ observed months in `2019-01..2026-09`).
2. **Exploratory Comparison Only (`role = "exploration_only"`):**
   - **Early Yam:** `Yam` (*igname précoce / laboko*, `Retail, KG, XOF, actual`, **17 Tier-1 markets** in `2019–2026`, plus `2013–2018` history in `Dantokpa`, `Abomey`, `Natitingou`, and `Parakou`) is retained in `data/processed/prices_cleaned_all.csv` for exploratory variety-spread analysis and historical visualization, but is never merged with `Yam (white)` and is not part of the primary forecasting panel.
3. **Out of Primary Scope (Configurable via 1-Line Change in [`src/config.py`](file:///home/brian/projets-ds/benin-agromarket/src/config.py)):**
   - `Cassava meal (gari)` and other candidate benchmarks (`Rice (imported)`, `Beans (white)`, `Sorghum (red)`, `Sorghum`, `Onions`) are defined as `ProductConfig` entries with `enabled_in_pipeline=False` in [`src/config.py`](file:///home/brian/projets-ds/benin-agromarket/src/config.py) so that adding a product later requires only flipping `enabled_in_pipeline=True`.

### Why (Interview Defense)
- **Empirical Coverage Audit ([`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py) → [`docs/tables/coverage_by_commodity.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/coverage_by_commodity.md) & [`docs/tables/raw_dataset_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/raw_dataset_summary.md)):**
  - `Yam` and `Yam (white)` are tracked concurrently in the same markets with an average price difference of **`207.9 XOF/kg` in `Dantokpa`** (`88` overlapping months), **`219.7 XOF/kg` in `Savalou`** (`84` overlapping months), and **`238.8 XOF/kg` in `Natitingou`** (`74` overlapping months). Merging or averaging them would create spurious regime jumps whenever one variety is absent in a given month.
  - Furthermore, northern yam production hubs **`Djougou`** (`86 / 93` months of `Yam (white)`) and **`Nikki`** (`85 / 93` months of `Yam (white)`) have only `1` row each of `Yam`. Selecting `Yam (white)` as the primary forecast series preserves major northern/central production hubs (`Glazoué`, `Djougou`, `Nikki`, `Savalou`, `Bembèrèkè`, `Kérou`, `Bassila`) alongside major consumption centers (`Dantokpa`, `Kétou`, `Comé`, `Bohicon`, `Natitingou`, `Abomey`, `Ouando`).
  - Restricting forecasting to **Tier-1 markets ($\ge 80 / 93$ months, i.e., $\ge 86.0\%$ completeness)** prevents modeling on thin series ($< 60$ months) where fresh yam or tomato is seasonally absent for 4–8 months at a time.

### Script-Generated Tier-1 Market Lists by Product
*Source script: [`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py) → [`docs/tables/tier1_markets_by_product.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/tier1_markets_by_product.md)*

- **`Maize (white)` (`49` Tier-1 markets out of `50` active in `2019–2026`; only `Klouékanmè` at `77 / 93` is Tier-2, and `N'Dali` has `0` rows after `2016-02`):**  
  `Glazoué` (`90/93`), `Ouesse` (`90/93`), `Cobly` (`89/93`), `Nikki` (`89/93`), `Kassoua-Allah` (`89/93`), `Ikpenlè` (`89/93`), `Kétou` (`89/93`), `Kpedekpo` (`89/93`), `Djougou` (`88/93`), `Malanville (CBM)` (`87/93`), `Tanguiéta` (`87/93`), `Comé` (`87/93`), `Azowlissè` (`87/93`), `Ouando` (`87/93`), `Bohicon` (`87/93`), `Kérou` (`86/93`), `Bembèrèkè` (`86/93`), `Dassa-Zoumè` (`86/93`), `Dangbo` (`86/93`), `Savalou` (`85/93`), `Bassila` (`85/93`), `Affamè` (`85/93`), `Tatonnoukon` (`85/93`), `Azovè` (`85/93`), `Banikoara` (`84/93`), `Péhunco` (`84/93`), `Ouègbo` (`84/93`), `Zinvié` (`84/93`), `Zè` (`84/93`), `Ahidahomè (Porto-Novo)` (`84/93`), `Hozin` (`84/93`), `Natitingou` (`84/93`), `Parakou` (`84/93`), `Dantokpa` (`84/93`), `Sèdjè-Dénou` (`83/93`), `Sékou` (`83/93`), `Dogbo` (`83/93`), `Pobè` (`83/93`), `Abomey` (`83/93`), `Covè` (`83/93`), `So-Ava` (`82/93`), `Dasso` (`82/93`), `Zogbodomey` (`82/93`), `Sehoue` (`82/93`), `Yoko` (`81/93`), `Kalalé` (`81/93`), `Tchaourou` (`81/93`), `Karimama` (`80/93`), `Sinendé` (`80/93`).
- **`Tomatoes` (`43` Tier-1 markets out of `50` active in `2019–2026`; `6` Tier-2 markets `Péhunco` `79/93`, `So-Ava` `78/93`, `Tchaourou` `78/93`, `Karimama` `76/93`, `Klouékanmè` `76/93`, `Sinendé` `64/93`; `1` Thin market `Nikki` `21/93`):**  
  `Parakou` (`90/93`), `Glazoué` (`90/93`), `Ouesse` (`90/93`), `Kassoua-Allah` (`89/93`), `Dantokpa` (`89/93`), `Ikpenlè` (`89/93`), `Natitingou` (`88/93`), `Djougou` (`88/93`), `Kétou` (`88/93`), `Kpedekpo` (`88/93`), `Malanville (CBM)` (`87/93`), `Ouando` (`87/93`), `Bohicon` (`87/93`), `Kérou` (`86/93`), `Bembèrèkè` (`86/93`), `Dassa-Zoumè` (`86/93`), `Dangbo` (`86/93`), `Cobly` (`86/93`), `Comé` (`86/93`), `Azowlissè` (`86/93`), `Savalou` (`85/93`), `Bassila` (`85/93`), `Tanguiéta` (`85/93`), `Banikoara` (`84/93`), `Ouègbo` (`84/93`), `Zinvié` (`84/93`), `Ahidahomè (Porto-Novo)` (`84/93`), `Hozin` (`84/93`), `Tatonnoukon` (`84/93`), `Azovè` (`84/93`), `Sékou` (`83/93`), `Affamè` (`83/93`), `Pobè` (`83/93`), `Abomey` (`83/93`), `Covè` (`83/93`), `Sèdjè-Dénou` (`82/93`), `Zè` (`82/93`), `Dogbo` (`82/93`), `Dasso` (`82/93`), `Zogbodomey` (`82/93`), `Sehoue` (`82/93`), `Yoko` (`81/93`), `Kalalé` (`81/93`).
- **`Yam (white)` (`19` Tier-1 markets out of `47` active in `2019–2026`):**  
  `Glazoué` (`89/93`), `Dantokpa` (`88/93`), `Kétou` (`88/93`), `Djougou` (`86/93`), `Kérou` (`85/93`), `Bembèrèkè` (`85/93`), `Nikki` (`85/93`), `Comé` (`85/93`), `Bohicon` (`85/93`), `Savalou` (`84/93`), `Bassila` (`84/93`), `Natitingou` (`84/93`), `Azovè` (`84/93`), `Péhunco` (`83/93`), `Dassa-Zoumè` (`82/93`), `Abomey` (`82/93`), `Ouando` (`82/93`), `Dogbo` (`81/93`), `Ouesse` (`81/93`).
- **`Yam` (`17` Tier-1 markets in `2019–2026`, `exploration_only`):**  
  `Dantokpa` (`92/93`), `Abomey` (`87/93`), `Kérou` (`86/93`), `Glazoué` (`86/93`), `Bembèrèkè` (`85/93`), `Savalou` (`85/93`), `Kétou` (`85/93`), `Péhunco` (`84/93`), `Ahidahomè (Porto-Novo)` (`83/93`), `Dangbo` (`83/93`), `Ouando` (`83/93`), `Dogbo` (`82/93`), `Comé` (`82/93`), `Bohicon` (`82/93`), `Ouègbo` (`81/93`), `Azovè` (`81/93`), `Natitingou` (`80/93`).

---

## Decision 2 — Primary Modeling Window (`2019-01` to `2026-09`) & Zero Interpolation Across `2017–2018`

### Choice
- Train and evaluate all forecasting models strictly on the **`2019-01-15` to `2026-09-15` (`93` calendar months / `7.75` years)** panel (`data/processed/modeling_panel_2019_2026.csv`).
- Never interpolate or bridge across the **`2017–2018` nationwide reporting hiatus**.
- Retain `2007–2018` observations in `data/processed/prices_cleaned_all.csv` with `regime = "pre_2019_exploration"` strictly for long-term historical context in the Explorer UI (e.g., `Dantokpa` back to `2007-01` and `Malanville (CBM)` back to `2012-04`), visually separated by a clear hiatus break.

### Why (Interview Defense)
- As shown in [`docs/tables/yearly_observation_density.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/yearly_observation_density.md) (generated by [`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py)), `Maize (white)` has **`0` observations in `2017` and `0` observations in `2018`** across all `51` markets (`Tomatoes` and `Yam (white)` start in `2019-01`). Interpolating 24 consecutive missing months would fabricate two full seasonal cycles of synthetic prices, violating `AGENTS.md` (*"Never invent, simulate or fill data silently"*) and corrupting seasonal lag features.

---

## Decision 3 — Exogenous Weather Ingestion & Strictly Lagged Features (`src/ingest/download_nasa_power.py` & `src/clean/clean_prices.py`)

### Choice
1. Deduplicate the `51` active Benin market coordinates onto NASA POWER's native MERRA-2 `0.5° × 0.625°` grid (**`23` unique grid cells**), downloading monthly agroclimatology (`PRECTOTCORR`, `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`) from `2006-01` to `2026-09` (`5,727` grid-month rows, `0` missing values; [`docs/tables/nasa_power_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/nasa_power_summary.md)).
2. Join **only lagged features available at forecast origin $t-1$**: `precip_lag1m`, `precip_lag2m`, `precip_lag3m`, `precip_roll3m_lag1`, `precip_anom_z_lag1m`, `t2m_lag1m`, `t2m_max_lag1m`, `t2m_min_lag1m`, and `rh2m_lag1m`.
3. Compute the climatological mean and standard deviation for `precip_anom_z_lag1m` strictly over **`2006–2018`** (pre-modeling window).
4. Evaluate weather features via an explicit **Phase 2 ablation study** (comparing models with vs. without NASA POWER features against naive and seasonal naive baselines).

### Why (Interview Defense)
- Including contemporaneous month-$t$ rainfall or temperature when forecasting month-$t$ prices is a textbook form of **future target leakage**, because realized weather during month $t$ is unknown when issuing a forecast prior to month $t$. Similarly, standardizing rainfall anomalies using `2019–2026` sample moments would leak future climate distribution shifts into historical training splits; anchoring the climatology on `2006–2018` guarantees zero look-ahead bias.

---

## Decision 4 — Outlier Flagging (Never Deleting) & Explicit Missing-Month Grid Policy (`src/clean/clean_prices.py`)

### Choice
1. **Outliers Flagged, Never Deleted:**
   - [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py) computes two deterministic outlier indicators per `(commodity, market)` series:
     - `is_outlier_level = 1` when the robust MAD z-score on $\log(\text{price})$ satisfies $|\text{robust\_z}| > 3.5$.
     - `is_outlier_jump = 1` when consecutive calendar months exhibit $|\Delta \log(\text{price})| > \ln(2.0) \approx 0.6931$ (a single-month doubling $\ge +100\%$ or halving $\le -50\%$).
   - Per [`docs/tables/cleaning_audit_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/cleaning_audit_summary.md) (`src/clean/clean_prices.py`), across all `14,551` cleaned rows, this flags `43` rows for `Maize (white)` (`32` level, `14` jump), `320` rows for `Tomatoes` (`44` level, `288` jump — reflecting genuine harvest/lean-season perishability swings), `150` rows for `Yam (white)` (`113` level, `43` jump), and `108` rows for `Yam` (`45` level, `67` jump). **Zero rows are deleted or overwritten.**
2. **Missing Months in `modeling_panel_2019_2026.csv`:**
   - Unobserved market-months in the `93`-month Tier-1 panel (`395 / 4,557` rows for `Maize (white)`, `335 / 3,999` rows for `Tomatoes`, `164 / 1,767` rows for `Yam (white)`) keep `is_observed = 0` and `price = ""` (empty/null).
   - For classical autoregressive baselines in Phase 2 that cannot step over a single missing interior month, an explicit, separate column `price_interp_1m_max` (`is_imputed_1m = 1`) linearly interpolates **only isolated 1-month interior gaps** (`75` rows for `Maize (white)`, `76` for `Tomatoes`, `50` for `Yam (white)`), leaving multi-month gaps (such as `2019-01..2019-06` for markets that joined in July 2019) un-imputed (`is_imputed_1m = 0`) and never used as ground-truth evaluation targets.
3. **Mandatory Anti-Leakage & Target-Integrity Safeguards for Phase 2:**
   - **Safeguard 1 (No Leakage from Full-Sample Diagnostics):** `robust_z` and every `is_outlier_*` column (`is_outlier_level`, `is_outlier_jump`) in `data/processed/` are full-sample diagnostics computed across the entire series and **must never be used as model inputs or filtering rules**. Any outlier handling inside a model must be computed strictly within the causal training window ($\le t$) of each backtest origin.
   - **Safeguard 2 (Strict Ground-Truth Target Integrity):** Only months with `is_observed == 1` are ever forecast targets or evaluation ground truth. The 1-month interpolated column (`price_interp_1m_max` / `is_imputed_1m`) **must never be a forecast target**; it may be used as a lag input only in a clearly labelled sensitivity variant compared against the main model on the validation split.

### Why (Interview Defense)
- In agricultural commodity markets—especially perishable fresh tomatoes and yams in West Africa—a $2\times$ monthly price jump during a border closure, flood, or lean-season shortage is often a **real economic shock**, not a keystroke error. Silently deleting or winsorizing such spikes would artificially depress RMSE/MAE and make prediction intervals dangerously overconfident. Keeping flags explicit lets Phase 1(b) EDA inspect them while Safeguards 1 and 2 guarantee zero look-ahead leakage and zero evaluation on synthetic interpolated targets in Phase 2.

---

## Decision 5 — Open-Data Licensing & Mandatory Attribution Text

### Choice
All datasets used in **Bénin AgroMarket** are openly licensed for public redistribution and adaptation. The web app footer, the Method & Limits page, and `README.md` must display the following exact attributions:

1. **WFP Food Prices & Markets for Benin (HDX) — `CC BY-IGO 3.0`:**
   > *Source des données de prix : Programme Alimentaire Mondial (PAM / WFP VAM) via Humanitarian Data Exchange (HDX), « Benin - Food Prices », alimenté par l'ONASA, la CT-SAGSA (SIM-Agricole), l'INStaD (ex-INSAE) et la FAO (FPMA/GIEWS). Sous licence Creative Commons Attribution for Intergovernmental Organisations 3.0 (CC BY-IGO 3.0).*
2. **NASA POWER Agroclimatology — NASA Open Data (Public Domain):**
   > *Données agroclimatiques (précipitations MERRA-2 `PRECTOTCORR`, température `T2M`, humidité `RH2M`) obtenues auprès du projet NASA Langley Research Center (LaRC) Prediction Of Worldwide Energy Resources (POWER), financé par le programme des sciences appliquées de la Terre de la NASA.*
3. **FAOSTAT Macro Context — `CC BY 4.0`:**
   > *Contexte macroéconomique : Organisation des Nations Unies pour l'alimentation et l'agriculture (FAO), base de données FAOSTAT (Indices des prix à la consommation et Prix à la production — Bénin). Sous licence CC BY 4.0.*

---

## Decision 6 — EDA-Informed Modeling Implications for Phase 2 (`src/analysis/eda.py`)

### Choice
Based on the empirical findings in Phase 1(b) ([`src/analysis/eda.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/eda.py) → [`docs/tables/eda_summary_by_product.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_summary_by_product.md), [`docs/tables/eda_seasonality_profile.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_seasonality_profile.md), [`docs/tables/eda_market_differences.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_market_differences.md), [`docs/tables/eda_abrupt_changes.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_abrupt_changes.md), and [`docs/tables/eda_weather_lag_correlations.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_weather_lag_correlations.md)), Phase 2 modeling will enforce five structural design choices:

1. **Log-Scale / Multiplicative Targets & Local Level Adaptation (`last value` + `seasonal naive` baselines first):**
   - Across `2019–2026` Tier-1 markets ([`docs/tables/eda_summary_by_product.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_summary_by_product.md)), `Tomatoes` mean price rose by **`1.89x`** (`305.4 XOF/kg` in `2019` to `577.7 XOF/kg` in `2025-10..2026-09`, CAGR **`+9.9%`**, CV **`70.0%`**) and `Yam (white)` mean price rose by **`1.46x`** (`285.8 XOF/kg` in `2019` to `418.5 XOF/kg` in `2025-10..2026-09`, CAGR **`+5.8%`**, CV **`52.7%`**), whereas `Maize (white)` (`201.8 XOF/kg` overall mean, CV **`29.7%`**) experienced a mid-panel surge followed by mean reversion (`141.6 XOF/kg` in `2019` vs `149.1 XOF/kg` in `2025-10..2026-09`, **`1.05x`**, CAGR **`+0.8%`**).
   - Because seasonal swings scale multiplicatively with the prevailing local price level, forecasting models will operate on $\log(\text{price})$ or local level-differenced features (`price / rolling_mean_12m`, `lag_1m`, `lag_12m`) rather than assuming a stationary global mean.
2. **Explicit $s = 12$ Seasonal Periodicity & Zone-Specific Seasonal Dynamics:**
   - As quantified in [`docs/tables/eda_seasonality_profile.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_seasonality_profile.md) (`src/analysis/eda.py`), all three primary products exhibit strong 12-month seasonal cycles whose phase and amplitude vary across Benin's three agro-ecological latitude zones:
     - **`Maize (white)`:** National seasonal index troughs in **November (`87.1`)** and peaks in **May (`108.1`)**, a **`21.0` index-point (`+24.1%`)** spread. However, in the unimodal **North (`>= 9.5°N`, `14` Tier-1 markets)**, the lean-season peak shifts to **August (`114.1`)** vs **November (`83.8`)**, a **`30.3` index-point (`+36.1%`)** spread (`+24.2%` in the bimodal South `< 7.5°N`, `+27.0%` in the Center `7.5°–9.5°N`).
     - **`Tomatoes`:** Extreme seasonal amplitude of **`71.1` index points (`+103.1%`)** nationally (trough **September `69.0`** → peak **June `140.2`**), reaching **`82.4` index points (`+129.0%`)** in the bimodal **South (`< 7.5°N`, `27` Tier-1 markets: trough September `63.9` → peak May `146.2`)** vs **`+78.2%`** in the Center (`6` markets) and **`+80.9%`** in the North (`10` markets).
     - **`Yam (white)`:** National seasonal index troughs at main harvest in **October (`85.0`)** and peaks during the pre-harvest lean season in **July (`121.9`)**, a **`37.0` index-point (`+43.5%`)** spread, rising to **`50.9` index points (`+64.5%`)** in the **North (`>= 9.5°N`, `6` Tier-1 markets: October `78.9` → July `129.8`)** vs **`+32.6%`** in the South (`8` markets).
   - Phase 2 baselines must therefore include both **Last-Value (`Naive_1m`, $\hat{y}_{t+h|t} = y_t$)** and **Seasonal Naive (`SeasonalNaive_12m`, $\hat{y}_{t+h|t} = y_{t+h-12}$)** as well as a **Drift/Seasonal-Ratio baseline** that combines the current price level $y_t$ with the market's seasonal index ratio.
3. **Market-Specific Fixed Effects / Spatial Hierarchy (`docs/tables/eda_market_differences.md`):**
   - Persistent structural spatial price spreads exist between surplus production basins and deficit/urban markets ([`docs/tables/eda_market_differences.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_market_differences.md)):
     - **`Maize (white)` (`1.79x` max/min market mean ratio, cross-market CV `13.2%`):** Lowest in rural producer markets **`Cobly` (`149.1 XOF/kg`, `-26.2%` vs Tier-1 mean)**, **`Azovè` (`160.8 XOF/kg`)**, **`Tchaourou` (`163.1 XOF/kg`)**, **`Kérou` (`163.3 XOF/kg`)**, and **`Glazoué` (`167.8 XOF/kg`)**, vs highest in coastal/deficit markets **`Dantokpa` (`267.4 XOF/kg`, `+32.4%`)** and **`Sèdjè-Dénou` (`258.5 XOF/kg`, `+28.0%`)**.
     - **`Tomatoes` (`6.33x` max/min market mean ratio, cross-market CV `33.8%`):** Lowest in **`Bassila` (`217.7 XOF/kg`, `-55.7%`)**, **`Dasso` (`301.9 XOF/kg`)**, and **`Bembèrèkè` (`339.6 XOF/kg`)**, vs **`Dantokpa` (`481.3 XOF/kg`)**, **`Glazoué` (`495.5 XOF/kg`)**, **`Djougou` (`599.6 XOF/kg`)**, **`Covè` (`749.8 XOF/kg`)**, and **`Tatonnoukon` (`1,377.0 XOF/kg`)**.
     - **`Yam (white)` (`4.07x` max/min market mean ratio, cross-market CV `39.2%`):** Lowest in northern/central surplus hubs **`Nikki` (`170.1 XOF/kg`, median `90.0 XOF/kg`, `-58.1%`)**, **`Bembèrèkè` (`186.6 XOF/kg`)**, **`Glazoué` (`190.3 XOF/kg`)**, and **`Bassila` (`193.1 XOF/kg`)**, vs **`Dantokpa` (`562.4 XOF/kg`, `+38.4%`)**, **`Natitingou` (`582.0 XOF/kg`, `+43.3%`)**, **`Dassa-Zoumè` (`682.7 XOF/kg`, `+68.1%`)**, and **`Savalou` (`692.7 XOF/kg`, `+70.5%`)**.
   - Any pooled or cross-market model in Phase 2 must include market-level historical quantiles/target encoding and agro-ecological zone indicators, and **all metrics (`MAE`, `RMSE`, `MAPE`) must be reported per product AND per market**.
4. **Evaluation on Raw Ground Truth (`is_observed == 1`) & Empirical Shock Transparency (`docs/tables/eda_abrupt_changes.md`):**
   - [`docs/tables/eda_abrupt_changes.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_abrupt_changes.md) identifies `43` synchronized multi-market surge/drop or jump-cluster months across `2019–2026` (e.g., `Tomatoes` national Tier-1 median surging `+47.6%` MoM in `2020-10` across `52.4%` of markets, `+27.5%` in `2024-05`, and `+26.7%` in `2024-06` to `862 XOF/kg`, followed by harvest drops of `-50.7%` in `2020-08` and `-45.2%` in `2021-08`; `Yam (white)` median surging `+49.3%` in `2020-01`).
   - All rolling-origin backtests in Phase 2 will evaluate strictly against **unmodified observed prices (`is_observed == 1`, `0` outliers deleted)** so that reported `MAE`, `RMSE`, `MAPE`, and prediction interval coverage honestly reflect real-world volatility.
5. **Lagged Agroclimatic Feature Ablation (`docs/tables/eda_weather_lag_correlations.md`):**
   - Strictly lagged NASA POWER features show statistically meaningful correlations with detrended intra-annual log price anomalies ([`docs/tables/eda_weather_lag_correlations.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_weather_lag_correlations.md)):
     - **`Tomatoes`:** `precip_lag3m` (`r = -0.384`, Spearman `rho = -0.422` nationally; `r = -0.470`, `rho = -0.487` in Center; `r = -0.399`, `rho = -0.469` in South), `precip_roll3m_lag1` (`r = -0.340` nationally; `r = -0.473` in Center), and `t2m_lag1m` (`r = +0.360`, `rho = +0.476` nationally; `r = +0.521`, `rho = +0.543` in South).
     - **`Maize (white)`:** `precip_lag3m` (`r = -0.243`, `rho = -0.247` nationally; `r = -0.320`, `rho = -0.361` in Center) and `t2m_lag1m` (`r = +0.233`, `rho = +0.300` nationally; `r = +0.400`, `rho = +0.401` in South).
     - **`Yam (white)`:** `precip_lag3m` (`r = -0.245`, `rho = -0.246` nationally; `r = -0.311` in North) and `precip_roll3m_lag1` vs MoM log change (`r = -0.246`, `rho = -0.289` nationally; `r = -0.323`, `rho = -0.351` in North).
   - Phase 2 will test whether adding these lagged agroclimatic variables improves out-of-sample forecast accuracy over deterministic calendar seasonality (`month` Fourier terms / seasonal indices) alone; if they do not beat simpler models without weather features, we will report that result honestly per `AGENTS.md`.


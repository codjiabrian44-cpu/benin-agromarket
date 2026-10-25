# Data Documentation — Bénin AgroMarket (`docs/DATA.md`)

**Last updated:** 2026-10-25  
**Phase:** Phase 1(a) (Data Ingestion & Cleaning Pipeline Complete)

All statistics, row counts, coverage metrics, and checksums in this document are produced deterministically by [`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py) and [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py) and saved in [`docs/tables/`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/).

---

## 1. Primary Subnational Market Price Dataset: WFP Food Prices for Benin (HDX)

### 1.1 Overview, Provenance & Checksums
- **Dataset Title:** Benin - Food Prices (`wfp-food-prices-for-benin`)
- **HDX Package ID:** `66c7d54e-0c3b-45e5-9a46-07ea6f195093`
- **Landing Page URL:** https://data.humdata.org/dataset/wfp-food-prices-for-benin
- **CKAN Metadata API URL:** https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-benin
- **Ingestion Script:** [`src/ingest/download_wfp.py`](file:///home/brian/projets-ds/benin-agromarket/src/ingest/download_wfp.py)
- **Download Date:** `2026-10-25`
- **Publisher / Organization:** World Food Programme (WFP — VAM Economic & Market Analysis)
- **Upstream Data Sources (per HDX `dataset_source` field):**  
  `CT, FPMA, Government of Benin, Institut National de la Statistique et de l'Analyse Économique (INSAE) via FAO: GIEWS, ONASA, SAGSA, SIMA - Niger`
- **License:** **CC BY-IGO 3.0** — Creative Commons Attribution for Intergovernmental Organisations (`http://creativecommons.org/licenses/by/3.0/igo/legalcode`).

#### Verified Downloaded Resources in `data/raw/`
*Source script: [`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py) → [`docs/tables/raw_dataset_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/raw_dataset_summary.md)*

| Resource | Local Path | Direct Download URL | Size (Bytes) | Data Rows | SHA-256 Checksum | MD5 Checksum |
| :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| **Food Prices CSV** | `data/raw/wfp_food_prices_ben.csv` | `https://data.humdata.org/dataset/66c7d54e-0c3b-45e5-9a46-07ea6f195093/resource/7da1ea0a-56c7-450a-af2c-d477745fc856/download/wfp_food_prices_ben.csv` | `17,567,844` | `146,501` | `535e584050f851b81f1b7523b0f58c6deb9ba5f6a89cd790413bd03f6cb7f4a7` | `a0be1e7b6de7806941d48240915284bc` |
| **Markets Metadata CSV** | `data/raw/wfp_markets_ben.csv` | `https://data.humdata.org/dataset/66c7d54e-0c3b-45e5-9a46-07ea6f195093/resource/030d5114-a642-4b5b-8915-019c6f1e8d4e/download/wfp_markets_ben.csv` | `3,119` | `69` | `68795328eec4b2e4f5c64ff0e040cf53e9d2d640a91e5a1bfe7d51351fcccf66` | `9cc2d01869dbf763405e40a0d6132b3a` |

### 1.2 Verified Schema & Empirical Distributions
*Source script: [`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py) → [`docs/tables/raw_dataset_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/raw_dataset_summary.md)*

| Column | Type | Empirical Summary in `wfp_food_prices_ben.csv` (`146,501` rows) |
| :--- | :--- | :--- |
| `date` | `string (YYYY-MM-DD)` | Mid-month dates (`YYYY-MM-15`), spanning `2002-01-15` to `2026-09-15` |
| `admin1` | `string` | All `12` Départements of Benin (`Alibori`, `Atakora`, `Atlantique`, `Borgou`, `Collines`, `Couffo`, `Donga`, `Littoral`, `Mono`, `Oueme`, `Plateau`, `Zou`) |
| `admin2` | `string` | Commune name (`0` missing values) |
| `market` | `string` | `51` active markets with price observations (`18` additional entries in `wfp_markets_ben.csv` have `0` price rows) |
| `market_id` | `integer` | Unique WFP numeric identifier for each market |
| `latitude` | `float` | WGS84 decimal degrees (`0` missing values across all `51` active markets) |
| `longitude` | `float` | WGS84 decimal degrees (`0` missing values across all `51` active markets) |
| `category` | `string` | `6` categories: `cereals and tubers` (`67,058`), `vegetables and fruits` (`38,562`), `pulses and nuts` (`23,311`), `oil and fats` (`9,996`), `meat, fish and eggs` (`6,872`), `miscellaneous food` (`702`) |
| `commodity` | `string` | `53` unique commodities (`58` unique `commodity × pricetype × unit` combinations) |
| `commodity_id` | `integer` | Unique WFP commodity identifier |
| `unit` | `string` | `2` standardized units: `KG` (`138,082` rows — all solids/crops) and `L` (`8,419` rows — `Oil (groundnut)` and `Oil (palm)` only) |
| `priceflag` | `string` | `100%` `actual` (`146,501` rows; `0` aggregate or imputed rows) |
| `pricetype` | `string` | `Retail`: `146,174` rows; `Wholesale`: `327` rows (restricted to `Malanville (CBM)` in `2002-01-15..2012-02-15`) |
| `currency` | `string` | `100%` `XOF` (`146,501` rows — West African CFA Franc) |
| `price` | `float` | Nominal price in `XOF` per `unit` (`0` non-positive or non-finite values) |
| `usdprice` | `float` | Nominal price converted to `USD` per `unit` |

### 1.3 Known Issues & Structural Regimes Identified in Audit
*Source script: [`src/analysis/coverage.py`](file:///home/brian/projets-ds/benin-agromarket/src/analysis/coverage.py) → [`docs/tables/yearly_observation_density.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/yearly_observation_density.md) and [`docs/tables/raw_dataset_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/raw_dataset_summary.md)*

1. **Two Distinct Temporal Regimes & the 2017–2018 Reporting Hiatus:**
   - **Pre-2019 Exploration Regime (`2002–2018`):**
     - `2002-01` to `2012-02`: Only `Wholesale` cereal prices (`Maize`, `Millet`, `Rice (imported)`, `Sorghum`, `Wheat`) in `Malanville (CBM)` (`327` rows total).
     - `2007-01` to `2011-12`: Only `1` retail market (`Dantokpa`, Cotonou, `12` obs/year) for `Maize (white)`, `Cassava meal (gari)`, `Rice (imported)`, `Beans (white)`, and `Sorghum`.
     - `2012-04` to `2016-12`: Retail collection added `Malanville (CBM)` in April 2012 (`2` markets, `21` obs in 2012), `Parakou` in 2013 (`3` markets, `24–30` obs in 2013), and expanded to `~20` retail markets in `2014–2016` (`238–245` obs/year in 2015 and `205–212` obs/year in 2016), followed by a **near-total nationwide reporting hiatus in `2017–2018`** (`0` observations in 2017–2018 for `Maize (white)` and `Beans (white)`; only `9` obs in 2017 and `26–30` obs in 2018 across `4` urban markets for `Maize`, `Yam`, `Cassava meal (gari)`, `Rice (imported)`, and `Sorghum`).
   - **Modern Continuous SIM-Bénin Regime (`2019-01-15` to `2026-09-15`, `93` months):**
     - Starting January/July 2019, standardized monthly retail price collection (`pricetype='Retail'`, `unit='KG'`, `priceflag='actual'`) covers **`50` active markets** across all `12` departments (`N'Dali` is the only market among the `51` active markets that ceased reporting in `2016-02` with `0` rows in `2019–2026`).
2. **Commodity Variety Split (`Maize` vs. `Maize (white)` and `Yam` vs. `Yam (white)`):**
   - **Maize:** `Maize (white)` (`4,868` rows, `51` markets, `2007–2026`; `4,239` rows in `2019–2026` across `50` markets, with `49` Tier-1 markets $\ge 80\text{m}$) is the primary series. Generic `Maize` (`145` rows, `4` markets, `2013–2019`) overlaps with `Maize (white)` on `20` months in `Dantokpa` and `15` months in `Parakou` and `Natitingou` (`0` overlap in `Abomey`). `Maize (yellow)` (`1,856` rows, `48` markets) only starts on `2023-04-15` (`42` months).
   - **Yam:** WFP tracks two concurrent fresh retail yam series in `KG`:
     - `Yam (white)` (`2,727` rows, `47` markets, `2019-01-15..2026-09-15`; `19` Tier-1 markets $\ge 80\text{m}$): Staple white yam (*igname blanche / kokoro*).
     - `Yam` (`2,820` rows, `49` markets, `2013-01-15..2026-09-15`; `2,721` rows in `2019–2026`, `17` Tier-1 markets $\ge 80\text{m}$): Early/preferred yam (*igname précoce / laboko*).
     - **Price Spread & Market Split (`docs/tables/raw_dataset_summary.md`):** On concurrent market-months, `Yam` and `Yam (white)` differ by `207.9 XOF/kg` in `Dantokpa` (`88` overlapping months), `219.7 XOF/kg` in `Savalou` (`84` overlapping months), `129.3 XOF/kg` in `Abomey` (`82` overlapping months), `238.8 XOF/kg` in `Natitingou` (`74` overlapping months), `185.3 XOF/kg` in `Bohicon` (`81` overlapping months), and `156.6 XOF/kg` in `Ouando` (`78` overlapping months). Conversely, major northern yam hubs **`Djougou`** (`86 / 93` months of `Yam (white)`) and **`Nikki`** (`85 / 93` months of `Yam (white)`) have only **`1` row each of `Yam`** (`2020-08`).

---

## 2. Exogenous Weather Dataset: NASA POWER Agroclimatology (`nasa_power_benin_markets.csv`)

### 2.1 Overview, Provenance & Checksums
*Source scripts: [`src/ingest/download_nasa_power.py`](file:///home/brian/projets-ds/benin-agromarket/src/ingest/download_nasa_power.py) and [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py) → [`docs/tables/nasa_power_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/nasa_power_summary.md)*

- **Dataset Title:** NASA POWER (Prediction Of Worldwide Energy Resources) — Agroclimatology (`AG`) Monthly Point Data
- **Exact API URL Template Used by [`src/ingest/download_nasa_power.py`](file:///home/brian/projets-ds/benin-agromarket/src/ingest/download_nasa_power.py):**  
  `https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M&community=AG&longitude={grid_lon}&latitude={grid_lat}&start=2006&end=2026&format=JSON`
- **Provider:** NASA Langley Research Center (LaRC)
- **License:** **NASA Open Data Policy (Public Domain / Unrestricted Reuse)** with attribution to the *NASA Langley Research Center (LaRC) POWER Project*.
- **Download Date:** `2026-10-25`

| Resource | Local Path | Size (Bytes) | Data Rows | Grid Cells | Temporal Span | SHA-256 Checksum | MD5 Checksum |
| :--- | :--- | ---: | ---: | ---: | :--- | :--- | :--- |
| **NASA POWER Monthly CSV** | `data/raw/nasa_power_benin_markets.csv` | `474,338` | `5,727` | `23` | `2006-01..2026-09` | `1a20724807476b3ca20948e6a595a4503bf80d0ede17943f96634785548714f3` | `807f94211c4d91a05f153ad949d792c9` |

### 2.2 Parameters & Completeness
*Source script: [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py) → [`docs/tables/nasa_power_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/nasa_power_summary.md)*

- The `51` active Benin markets map onto **`23` unique MERRA-2 `0.5° × 0.625°` grid cells** (`249` months each from `2006-01` to `2026-09`, yielding `23 × 249 = 5,727` grid-month rows).
- **Completeness:** All `5` parameters (`PRECTOTCORR`, `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`) have **`5,727 / 5,727` valid observations (`0` missing `-999` values)**.
- **Leakage Prevention in [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py):** Only strictly lagged features (`precip_lag1m`, `precip_lag2m`, `precip_lag3m`, `precip_roll3m_lag1`, `precip_anom_z_lag1m`, `t2m_lag1m`, `t2m_max_lag1m`, `t2m_min_lag1m`, `rh2m_lag1m`) are joined to price observations, and the climatological baseline ($\mu, \sigma$ per grid cell and calendar month) for `precip_anom_z_lag1m` is computed strictly over **`2006–2018`** (prior to the `2019–2026` modeling window).

---

## 3. Cleaned & Processed Datasets in `data/processed/`

*Source script: [`src/clean/clean_prices.py`](file:///home/brian/projets-ds/benin-agromarket/src/clean/clean_prices.py) → [`docs/tables/cleaning_audit_summary.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/cleaning_audit_summary.md)*

| Processed File | Rows | Description |
| :--- | ---: | :--- |
| `data/processed/markets_active.csv` | `51` | All `51` active Benin markets with WGS84 coordinates, snapped MERRA-2 `(grid_lat, grid_lon)`, `2019–2026` observation counts, and Tier-1 binary flags per product (`18` inactive metadata markets stripped). |
| `data/processed/prices_cleaned_all.csv` | `14,551` | All observed `Retail, KG, XOF, actual` rows across `2007–2026` for the `4` enabled products (`Maize (white)`: `4,868`; `Tomatoes`: `4,136`; `Yam (white)`: `2,727`; `Yam`: `2,820`), annotated with `regime`, market tiers, outlier flags (`0` rows deleted), and lagged NASA POWER features. |
| `data/processed/modeling_panel_2019_2026.csv` | `10,323` | Regular monthly calendar grid (`93` months: `2019-01-15..2026-09-15`) for Tier-1 markets of the `3` `forecast_primary` products (`Maize (white)`: `49 × 93 = 4,557` rows, `4,162` observed; `Tomatoes`: `43 × 93 = 3,999` rows, `3,664` observed; `Yam (white)`: `19 × 93 = 1,767` rows, `1,603` observed). Unobserved months have `is_observed = 0` and `price = ""` (`0` silent imputations). |

---

## 4. Reference & Context Sources Audited

1. **FAOSTAT Producer Prices (`PP`) & Consumer Price Index (`CP`):** https://www.fao.org/faostat/en/#data/PP and https://www.fao.org/faostat/en/#data/CP (`CC BY 4.0`). National macro context.
2. **ONASA / CT-SAGSA (*Bulletin SIM-Agricole*) / DSA / INStaD:** Upstream ground collectors already consolidated into `wfp_food_prices_ben.csv`.
3. **World Bank Real-Time Food Prices (RTFP):** Excluded from training due to machine-learning imputation (`AGENTS.md` rule against silent/synthetic filling).
4. **FEWS NET / SIMA-Niger:** Cross-border shock context for northern Benin (`Malanville (CBM)`).

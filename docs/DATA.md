# Data Documentation — Bénin AgroMarket (`docs/DATA.md`)

**Last updated:** 2026-10-25  
**Phase:** Phase 0 (Data Audit — Completed)

This document inventories every primary and candidate dataset audited for **Bénin AgroMarket** (forecasting staple food prices in Benin: maize, yam, tomato), including exact source URLs, licenses, download dates, verified SHA-256 and MD5 checksums, schemas, coverage statistics, and known limitations.

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
- **License:** **CC BY-IGO** — Creative Commons Attribution for Intergovernmental Organisations 3.0 (`http://creativecommons.org/licenses/by/3.0/igo/legalcode`). Permits free sharing and adaptation for any purpose with appropriate attribution to WFP and upstream national partners.

#### Verified Downloaded Resources in `data/raw/`
| Resource | Local Path | Direct Download URL | Size (Bytes) | Data Rows | SHA-256 Checksum | MD5 Checksum |
| :--- | :--- | :--- | ---: | ---: | :--- | :--- |
| **Food Prices CSV** | `data/raw/wfp_food_prices_ben.csv` | `https://data.humdata.org/dataset/66c7d54e-0c3b-45e5-9a46-07ea6f195093/resource/7da1ea0a-56c7-450a-af2c-d477745fc856/download/wfp_food_prices_ben.csv` | `17,567,844` | `146,501` (+1 header) | `535e584050f851b81f1b7523b0f58c6deb9ba5f6a89cd790413bd03f6cb7f4a7` | `a0be1e7b6de7806941d48240915284bc` |
| **Markets Metadata CSV** | `data/raw/wfp_markets_ben.csv` | `https://data.humdata.org/dataset/66c7d54e-0c3b-45e5-9a46-07ea6f195093/resource/030d5114-a642-4b5b-8915-019c6f1e8d4e/download/wfp_markets_ben.csv` | `3,119` | `69` (+1 header) | `68795328eec4b2e4f5c64ff0e040cf53e9d2d640a91e5a1bfe7d51351fcccf66` | `9cc2d01869dbf763405e40a0d6132b3a` |

### 1.2 Verified Schema & Empirical Distributions
#### `wfp_food_prices_ben.csv` (`146,501` data rows × `16` columns)
| Column | Type | Empirical Summary in `wfp_food_prices_ben.csv` |
| :--- | :--- | :--- |
| `date` | `string (YYYY-MM-DD)` | Mid-month dates (`YYYY-MM-15`), spanning `2002-01-15` to `2026-09-15` |
| `admin1` | `string` | All `12` Départements of Benin (`Alibori`, `Atakora`, `Atlantique`, `Borgou`, `Collines`, `Couffo`, `Donga`, `Littoral`, `Mono`, `Oueme`, `Plateau`, `Zou`) |
| `admin2` | `string` | Commune name (`0` missing values) |
| `market` | `string` | `51` active markets with price observations |
| `market_id` | `integer` | Unique WFP numeric identifier for each market |
| `latitude` | `float` | WGS84 decimal degrees (`0` missing values across all `51` active markets) |
| `longitude` | `float` | WGS84 decimal degrees (`0` missing values across all `51` active markets) |
| `category` | `string` | `6` categories: `cereals and tubers` (`67,058`), `vegetables and fruits` (`38,562`), `pulses and nuts` (`23,311`), `oil and fats` (`9,996`), `meat, fish and eggs` (`6,872`), `miscellaneous food` (`702`) |
| `commodity` | `string` | `53` unique commodities (`58` unique `commodity × pricetype × unit` combinations) |
| `commodity_id` | `integer` | Unique WFP commodity identifier |
| `unit` | `string` | `2` standardized units: `KG` (`138,082` rows — all solids/crops) and `L` (`8,419` rows — `Oil (groundnut)` and `Oil (palm)` only) |
| `priceflag` | `string` | `100%` `actual` (`146,501` rows; `0` aggregate or imputed rows) |
| `pricetype` | `string` | `Retail`: `146,174` rows (`99.78%`); `Wholesale`: `327` rows (`0.22%`, restricted to `Malanville (CBM)` in `2002–2012`) |
| `currency` | `string` | `100%` `XOF` (`146,501` rows — West African CFA Franc) |
| `price` | `float` | Nominal price in `XOF` per `unit` (`KG` or `L`) |
| `usdprice` | `float` | Nominal price converted to `USD` per `unit` |

#### `wfp_markets_ben.csv` (`69` data rows × `7` columns)
- Columns: `market_id, market, countryiso3, admin1, admin2, latitude, longitude`.
- Contains `69` market rows (`51` active markets present in `wfp_food_prices_ben.csv` + `18` registered markets with `0` price records in the dataset).

### 1.3 Known Issues & Structural Regimes Identified in Phase 0 Audit
1. **Two Distinct Temporal Regimes & the 2017–2018 Reporting Hiatus:**
   - **Pre-2019 Regime (`2002–2018`):**
     - `2002-01` to `2012-02`: Only `Wholesale` cereal prices (`Maize`, `Millet`, `Rice (imported)`, `Sorghum`, `Wheat`) in a single cross-border market (`Malanville (CBM)`, `327` rows total).
     - `2007-01` to `2011-12`: Only `1` retail market (`Dantokpa`, Cotonou, `12` obs/year) for `Maize (white)`, `Cassava meal (gari)`, `Rice (imported)`, `Beans (white)`, and `Sorghum`.
     - `2012-04` to `2016-12`: Gradual expansion to `~20` retail markets, followed by a **near-total nationwide reporting hiatus in 2017–2018** (`0` observations in 2017–2018 for `Maize (white)` and `Beans (white)`; only `9` obs in 2017 and `26–30` obs in 2018 across `4` urban markets for `Maize`, `Yam`, `Cassava meal (gari)`, `Rice (imported)`, and `Sorghum`).
   - **Modern Continuous SIM-Bénin Regime (`2019-01-15` to `2026-09-15`, 93 months / 7.75 years):**
     - Starting January/July 2019, standardized monthly retail price collection (`pricetype='Retail'`, `unit='KG'`, `priceflag='actual'`) covers **50 active markets** across all 12 departments with **93.5%–98.9% monthly completeness** (`86–90` observed months out of `93`) for core staples.
2. **Commodity Variety Split (`Maize` vs. `Maize (white)` and `Yam` vs. `Yam (white)`):**
   - **Maize:** `Maize (white)` (`4,868` rows, `51` markets, `2007–2026`) is the primary series. Generic `Maize` (`145` rows, `4` markets, `2013–2019`) overlaps with `Maize (white)` on `20` months in `Dantokpa` and `15` months in `Parakou`/`Natitingou` (while filling 2017–2018 in those 4 markets). `Maize (yellow)` (`1,856` rows, `48` markets) only starts on `2023-04-15` (`42` months).
   - **Yam:** WFP tracks two concurrent fresh retail yam series in `KG`:
     - `Yam` (`2,820` rows, `49` markets, `2013-01-15` to `2026-09-15`): Represents early/preferred yam varieties (*igname précoce / laboko*).
     - `Yam (white)` (`2,727` rows, `47` markets, `2019-01-15` to `2026-09-15`): Represents standard white yam (*igname blanche / kokoro*).
     - **Critical Finding:** In markets where both are recorded on the same date (e.g., `88` overlapping months in `Dantokpa`, `84` in `Savalou`, `82` in `Abomey`), their prices differ by **`129–239 XOF/kg` on average**. Therefore, `Yam` and `Yam (white)` **must never be merged or averaged into a single synthetic series**. Furthermore, major northern yam markets like **Djougou** (`86/93` months) and **Nikki** (`85/93` months) report `Yam (white)` almost exclusively (`1` row of `Yam` in Djougou), whereas **Abomey** (`110` months) and **Dantokpa** (`128` months) have long histories of `Yam` plus full 2019–2026 series of `Yam (white)`.
     - Processed yam is also tracked separately from `2020-04-15`: `Yam (flour)` (*cossette moulue / télibo*, `1,915` rows, `39` markets) and `Yam (dry)` (*cossette d'igname*, `1,591` rows, `36` markets).
3. **18 Inactive Markets in `wfp_markets_ben.csv`:**
   - Out of `69` markets in `wfp_markets_ben.csv`, `18` have `0` rows in `wfp_food_prices_ben.csv` (including a duplicate spelling `Comè` `market_id=1765` whereas active `Comé` is `market_id=2714`, plus 17 rural communes in Alibori, Atakora, Mono, and Zou). Only the `51` active markets (`50` active in `2019–2026`) should be retained in Phase 1.

---

## 2. Exogenous Weather Context: NASA POWER Agroclimatology API

### 2.1 Overview & Provenance
- **Dataset Title:** NASA POWER (Prediction Of Worldwide Energy Resources) — Agroclimatology (`AG`) Daily & Monthly Point Data
- **Base API Endpoints:**
  - Daily: `https://power.larc.nasa.gov/api/temporal/daily/point`
  - Monthly: `https://power.larc.nasa.gov/api/temporal/monthly/point`
- **Provider:** NASA Langley Research Center (LaRC)
- **License:** **NASA Open Data Policy (Public Domain / Unrestricted Reuse)**. Free for academic, open-source, and commercial redistribution without an API key; attribution to *NASA Langley Research Center (LaRC) POWER Project*.
- **Audit Date:** `2026-10-25`

### 2.2 Selected Agroclimatic Parameters
| Parameter | Unit | Description | Relevance to Benin Staple Prices |
| :--- | :--- | :--- | :--- |
| `PRECTOTCORR` | `mm/day` | MERRA-2 bias-corrected total precipitation | Captures onset/cessation of rainy seasons (bimodal in south, unimodal in north), drought shocks, and harvest timing |
| `T2M` | `°C` | Mean air temperature at 2 meters | Crop evapotranspiration stress and post-harvest perishability (critical for tomato & yam storage) |
| `T2M_MAX` | `°C` | Maximum daily air temperature at 2 meters | Heatwave stress during maize flowering/grain filling |
| `T2M_MIN` | `°C` | Minimum daily air temperature at 2 meters | Nighttime temperature anomalies |
| `RH2M` | `%` | Relative humidity at 2 meters | Fungal/rot risk during storage (yam, maize drying) and tomato blight pressure |

### 2.3 Coverage & Known Issues
- **Temporal Coverage:** `1981-01-01` to near-real-time.
- **Spatial Resolution:** `0.5° × 0.625°` (~55 km × 69 km grid cells). All `51` active WFP markets have verified `(latitude, longitude)` coordinates in `wfp_food_prices_ben.csv` (`0` missing).
- **Forecasting Leakage Constraint:** Only **lagged** agroclimatic features (e.g., 1-, 3-, and 6-month rolling rainfall anomalies and temperature stress prior to forecast origin $t$) may be used in forecasting models.

---

## 3. National Macro Context: FAOSTAT Producer Prices (`PP`) & Consumer Price Index (`CP`)

- **Dataset URLs:** https://www.fao.org/faostat/en/#data/PP and https://www.fao.org/faostat/en/#data/CP
- **License:** **CC BY 4.0** (FAO Open Data Licensing Policy).
- **Coverage & Role:** National aggregate (`Benin`, `ISO3=BEN`), annual producer prices (`1991–2024`) and monthly Food/General CPI (`2000–present`). Useful for macro inflation context (`XOF` nominal vs. real price deflation) and national sanity checks; cannot replace subnational market series.

---

## 4. Other Candidate Sources Evaluated (from `BRIEF.md`)

1. **ONASA / CT-SAGSA (*Bulletin SIM-Agricole*) / DSA / INStaD (Benin National Agencies):**
   - Ground collection from ONASA, CT-SAGSA, and INSAE/INStaD is **already ingested upstream** into `wfp_food_prices_ben.csv` (as confirmed by the HDX `dataset_source` field and the 50-market SIM rollout visible in the CSV from January 2019 onward). Standalone national portals publish PDF bulletins without open machine-readable historical CSVs.
2. **World Bank Real-Time Food Prices (RTFP):**
   - Uses machine-learning imputation on top of the WFP feed. Per `AGENTS.md` (*"Never invent, simulate or fill data silently"*), we model strictly on the unimputed `actual` observations in `wfp_food_prices_ben.csv`.
3. **FEWS NET / SIMA-Niger:**
   - Cross-border wholesale series for `Malanville (CBM)` (`SIMA - Niger`) is already included in `wfp_food_prices_ben.csv`. FEWS NET regional reports provide qualitative context for border/trade shocks (e.g., 2019–2020 Nigeria border closure, 2023–2024 Niger corridor closure).

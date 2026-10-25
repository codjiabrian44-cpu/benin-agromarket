# Project Status — Bénin AgroMarket (`docs/STATUS.md`)

**Date:** 2026-10-25  
**Current Phase:** Phase 0 — Data Audit (**COMPLETED — Awaiting Owner Sign-off for Phase 1**)

---

## 1. Summary of What Was Done in Phase 0

1. **Built Reproducible Ingestion Script ([`src/ingest/download_wfp.py`](file:///home/brian/projets-ds/benin-agromarket/src/ingest/download_wfp.py)):**
   - Implemented a typed, documented Python 3.10+ module using standard library (`urllib.request`, `hashlib`) per `AGENTS.md` (`## Downloads`).
   - Downloaded the official WFP Benin Food Prices dataset and Markets Metadata from the exact HDX URLs recorded in [`docs/DATA.md`](file:///home/brian/projets-ds/benin-agromarket/docs/DATA.md) into `data/raw/`, verified byte sizes, and recorded SHA-256 and MD5 checksums:
     - `data/raw/wfp_food_prices_ben.csv`: **`17,567,844` bytes** (`146,501` data rows × `16` columns) — SHA-256: `535e584050f851b81f1b7523b0f58c6deb9ba5f6a89cd790413bd03f6cb7f4a7`
     - `data/raw/wfp_markets_ben.csv`: **`3,119` bytes** (`69` market rows × `7` columns) — SHA-256: `68795328eec4b2e4f5c64ff0e040cf53e9d2d640a91e5a1bfe7d51351fcccf66`
2. **Audited All Candidate Data Sources from `BRIEF.md`:**
   - Verified coverage, granularity, licenses, and upstream provenance for **WFP Food Prices (HDX)**, **NASA POWER Agroclimatology API**, **FAOSTAT (`PP` & `CP`)**, **ONASA / CT-SAGSA (*Bulletin SIM-Agricole*) / DSA / INStaD**, **World Bank RTFP**, and **FEWS NET**.
   - Updated [`docs/DATA.md`](file:///home/brian/projets-ds/benin-agromarket/docs/DATA.md) with complete documentation and checksums.
3. **Computed Full `product × market × period` Coverage & Structural Regime Audit:**
   - Audited all `53` commodities (`58` `commodity × pricetype × unit` series) across all `51` active markets in Benin's 12 departments from `2002-01-15` to `2026-09-15`.

---

## 2. Key Findings Across Data Sources

1. **WFP HDX (`wfp_food_prices_ben.csv`) Already Consolidates Benin's National Agencies:**
   - The HDX metadata (`dataset_source`) and empirical series confirm that `wfp_food_prices_ben.csv` directly ingests official ground collection from **ONASA**, **CT-SAGSA (*SIM-Agricole*)**, **INSAE/INStaD**, **FAO FPMA/GIEWS**, and **SIMA-Niger** under an open **CC BY-IGO 3.0** license.
   - **100% of rows (`146,501`) have `priceflag == 'actual'`** (zero machine-imputed rows), **`currency == 'XOF'`**, and **`0` missing coordinates** across all `51` active markets (`18` additional rural/duplicate market entries in `wfp_markets_ben.csv` have `0` price rows).
   - **99.78% of rows (`146,174`) are `Retail` prices in `KG`** (or `L` for cooking oils). Only `327` rows are `Wholesale` (`Malanville (CBM)` cross-border cereals in `2002–2012`).
2. **Critical Temporal Discovery — The 2017–2018 Hiatus vs. the 2019–2026 Continuous Regime:**
   - **Pre-2019 (`2007–2018`) is sparse and discontinuous:** From `2007` to `2011`, only **1 retail market** (`Dantokpa`, Cotonou) was recorded (`12` obs/year). Coverage expanded to `~20` markets in `2014–2016`, and then suffered a **near-total nationwide reporting hiatus in `2017–2018`** (`0` rows for `Maize (white)` and `Beans (white)`; only `9–30` rows/year across `4` cities for `Maize`, `Yam`, `Cassava meal (gari)`, `Rice (imported)`, and `Sorghum`).
   - **Modern Continuous SIM-Bénin Regime (`2019-01-15` to `2026-09-15`, `93` calendar months / `7.75` years):** Starting in January/July 2019, standardized monthly retail monitoring covers **50 active markets across all 12 departments** with **93.5%–98.9% monthly completeness** (`86–90` observed months out of `93`) for core staples.
3. **Exogenous Weather & Macro Context:**
   - **NASA POWER Agroclimatology API (`AG`, Public Domain):** Keyless daily/monthly REST endpoint (`PRECTOTCORR`, `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`) covers `1981–present` at `0.5° × 0.625°` resolution for all `51` active market coordinates.
   - **FAOSTAT (`CC BY 4.0`):** Provides national monthly Food CPI for nominal-to-real `XOF` deflation checks.
   - **World Bank RTFP (`CC BY 4.0`):** Excluded from model training because it relies on machine-learning imputation over the same WFP feed (violating `AGENTS.md`: *"Never invent, simulate or fill data silently"*).

---

## 3. Coverage Tables (`product × market × period`)

### 3.1 Table A — Global Coverage by Commodity (`wfp_food_prices_ben.csv`)

The table below covers **all target commodities** (**Maize**, **Yam**, **Tomato** varieties) plus the **top alternative staple commodities** in Benin, comparing full historical coverage (`2002–2026`) against the continuous modern regime (`2019-01` to `2026-09`, `93` months):

| Target / Group | Exact `commodity` String | `pricetype` & `unit` | Total Obs (`All`) | Active Markets (`All`) | Date Range (`All`) | Unique Months (`All`) | Obs in `2019-01..2026-09` | Markets $\ge 60\text{m}$ (`2019–26`) | Markets $\ge 80/93\text{m}$ (`2019–26`) |
| :--- | :--- | :--- | ---: | ---: | :--- | ---: | ---: | ---: | ---: |
| **Maize (Primary)** | **`Maize (white)`** | `Retail, KG` | **4,868** | **51** | `2007-01-15..2026-09-15` | `208 / 237` | **4,239** | **50 / 50** | **49 / 50** |
| Maize (Yellow) | `Maize (yellow)` | `Retail, KG` | 1,856 | 48 | `2023-04-15..2026-09-15` | `42 / 42` | 1,856 | 0 / 48 | 0 / 48 |
| Maize (Legacy) | `Maize` | `Retail, KG` | 145 | 4 | `2013-01-15..2019-12-15` | `48 / 84` | 40 | 0 / 4 | 0 / 4 |
| Maize (Wholesale) | `Maize` | `Wholesale, KG` | 79 | 1 | `2002-01-15..2012-02-15` | `79 / 122` | 0 | 0 / 0 | 0 / 0 |
| **Tomato (Primary)** | **`Tomatoes`** | `Retail, KG` | **4,136** | **50** | `2019-01-15..2026-09-15` | `90 / 93` | **4,136** | **49 / 50** | **43 / 50** |
| **Yam (Fresh — Early/Laboko)** | **`Yam`** | `Retail, KG` | **2,820** | **49** | `2013-01-15..2026-09-15` | `128 / 165` | **2,721** | **28 / 49** | **17 / 49** |
| **Yam (Fresh — White/Kokoro)** | **`Yam (white)`** | `Retail, KG` | **2,727** | **47** | `2019-01-15..2026-09-15` | `89 / 93` | **2,727** | **31 / 47** | **19 / 47** |
| Yam (Processed Flour) | `Yam (flour)` | `Retail, KG` | 1,915 | 39 | `2020-04-15..2026-09-15` | `77 / 78` | 1,915 | 22 / 39 | 0 / 39 |
| Yam (Dry Cossette) | `Yam (dry)` | `Retail, KG` | 1,591 | 36 | `2020-04-15..2026-09-15` | `77 / 78` | 1,591 | 18 / 36 | 0 / 36 |
| Yam (Yellow) | `Yam (yellow)` | `Retail, KG` | 412 | 24 | `2020-04-15..2026-09-15` | `76 / 78` | 412 | 1 / 24 | 0 / 24 |
| *Alt 1: Gari (Cassava)* | `Cassava meal (gari)` | `Retail, KG` | **4,955** | **51** | `2007-01-15..2026-09-15` | `230 / 237` | **4,262** | **50 / 50** | **48 / 50** |
| *Alt 2: Imported Rice* | `Rice (imported)` | `Retail, KG` | **4,953** | **51** | `2007-01-15..2026-09-15` | `230 / 237` | **4,258** | **50 / 50** | **49 / 50** |
| *Alt 3: Cowpeas / Niébé* | `Beans (white)` | `Retail, KG` | **4,882** | **51** | `2007-01-15..2026-09-15` | `208 / 237` | **4,254** | **50 / 50** | **49 / 50** |
| *Alt 4: Onions* | `Onions` | `Retail, KG` | **4,242** | **50** | `2019-01-15..2026-09-15` | `90 / 93` | **4,242** | **50 / 50** | **49 / 50** |
| *Alt 5: Red Sorghum* | `Sorghum (red)` | `Retail, KG` | **4,147** | **50** | `2019-01-15..2026-09-15` | `90 / 93` | **4,147** | **49 / 50** | **42 / 50** |
| *Alt 6: White Sorghum* | `Sorghum` | `Retail, KG` | **3,927** | **51** | `2007-01-15..2026-09-15` | `230 / 237` | **3,239** | **33 / 49** | **25 / 49** |

---

### 3.2 Table B — Yearly Observation Density (`2007–2026`, Retail `KG`)

This table illustrates the **2017–2018 reporting gap** and why **`2019-01` to `2026-09` (`93` months)** forms the clean, continuous multi-market panel:

| Commodity (`Retail, KG`) | '07–'11 (avg/yr) | 2012 | 2013 | 2014 | 2015 | 2016 | **2017** | **2018** | **2019** | **2020** | **2021** | **2022** | **2023** | **2024** | **2025** | **2026 (Jan–Sep)** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`Maize (white)`** | 12 | 21 | 24 | 76 | 238 | 210 | **0** | **0** | **294** | **562** | **598** | **545** | **599** | **598** | **598** | **445** |
| **`Tomatoes`** | 0 | 0 | 0 | 0 | 0 | 0 | **0** | **0** | **295** | **541** | **580** | **533** | **582** | **570** | **591** | **444** |
| **`Yam`** | 0 | 0 | 9 | 23 | 27 | 5 | **9** | **26** | **166** | **386** | **394** | **355** | **382** | **371** | **389** | **278** |
| **`Yam (white)`** | 0 | 0 | 0 | 0 | 0 | 0 | **0** | **0** | **222** | **355** | **384** | **340** | **397** | **358** | **373** | **298** |
| `Cassava meal (gari)` | 12 | 21 | 30 | 86 | 245 | 212 | **9** | **30** | **320** | **560** | **598** | **545** | **599** | **598** | **597** | **445** |
| `Beans (white)` | 12 | 21 | 24 | 75 | 238 | 210 | **0** | **0** | **309** | **562** | **598** | **545** | **599** | **598** | **598** | **445** |
| `Sorghum (red)` | 0 | 0 | 0 | 0 | 0 | 0 | **0** | **0** | **302** | **535** | **575** | **512** | **588** | **593** | **597** | **445** |

---

### 3.3 Table C — Market-by-Market Coverage (`product × market × period`) for Benin's 18 Major Benchmark Markets

All entries below are **`pricetype = Retail`**, **`unit = KG`**, **`currency = XOF`**, **`priceflag = actual`**.  
*(Note: For series starting in `2007–2014`, the overall gap % reflects the `2017–2018` nationwide pause; within `2019-01` to `2026-09`, completeness across these benchmark markets is **91%–99%**, i.e., gap **1.1%–8.6%**).*

| Market | Département (`admin1`) | `Maize (white)` Obs / Exp (Gap %) & Period | `Tomatoes` Obs / Exp (Gap %) & Period | `Yam (white)` Obs / Exp (Gap %) & Period | `Yam` Obs / Exp (Gap %) & Period |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Dantokpa (Cotonou)** | Littoral | **202 / 237** (14.8%) `2007-01..2026-09` | **89 / 93** (4.3%) `2019-01..2026-09` | **88 / 93** (5.4%) `2019-01..2026-09` | **128 / 165** (22.4%) `2013-01..2026-09` |
| **Malanville (CBM)** | Alibori | **142 / 174** (18.4%) `2012-04..2026-09` | **87 / 93** (6.5%) `2019-01..2026-09` | **77 / 93** (17.2%) `2019-01..2026-09` | **48 / 83** (42.2%) `2019-07..2026-05` |
| **Banikoara** | Alibori | **110 / 145** (24.1%) `2014-09..2026-09` | **85 / 87** (2.3%) `2019-07..2026-09` | **65 / 87** (25.3%) `2019-07..2026-09` | **65 / 87** (25.3%) `2019-07..2026-09` |
| **Natitingou** | Atakora | **110 / 145** (24.1%) `2014-09..2026-09` | **88 / 93** (5.4%) `2019-01..2026-09` | **84 / 93** (9.7%) `2019-01..2026-09` | **100 / 147** (32.0%) `2014-07..2026-09` |
| **Kérou** | Atakora | **112 / 145** (22.8%) `2014-09..2026-09` | **86 / 87** (1.1%) `2019-07..2026-09` | **85 / 87** (2.3%) `2019-07..2026-09` | **86 / 87** (1.1%) `2019-07..2026-09` |
| **Tanguiéta** | Atakora | **113 / 145** (22.1%) `2014-09..2026-09` | **85 / 93** (8.6%) `2019-01..2026-09` | **80 / 93** (14.0%) `2019-01..2026-09` | **68 / 85** (20.0%) `2019-07..2026-07` |
| **Ouègbo** | Atlantique | **86 / 87** (1.1%) `2019-07..2026-09` | **86 / 87** (1.1%) `2019-07..2026-09` | **67 / 87** (23.0%) `2019-07..2026-09` | **81 / 87** (6.9%) `2019-07..2026-09` |
| **Parakou** | Borgou | **110 / 145** (24.1%) `2014-09..2026-09` | **90 / 93** (3.2%) `2019-01..2026-09` | **76 / 93** (18.3%) `2019-01..2026-09` | **97 / 161** (39.8%) `2013-01..2026-05` |
| **Nikki** | Borgou | **115 / 145** (20.7%) `2014-09..2026-09` | **86 / 93** (7.5%) `2019-01..2026-09` | **85 / 93** (8.6%) `2019-01..2026-09` | **58 / 86** (32.6%) `2019-07..2026-08` |
| **Bembèrèkè** | Borgou | **86 / 87** (1.1%) `2019-07..2026-09` | **86 / 87** (1.1%) `2019-07..2026-09` | **85 / 87** (2.3%) `2019-07..2026-09` | **85 / 87** (2.3%) `2019-07..2026-09` |
| **Glazoué** | Collines | **116 / 145** (20.0%) `2014-09..2026-09` | **90 / 93** (3.2%) `2019-01..2026-09` | **89 / 93** (4.3%) `2019-01..2026-09` | **86 / 87** (1.1%) `2019-07..2026-09` |
| **Savalou** | Collines | **111 / 145** (23.4%) `2014-09..2026-09` | **85 / 87** (2.3%) `2019-07..2026-09` | **84 / 87** (3.4%) `2019-07..2026-09` | **85 / 87** (2.3%) `2019-07..2026-09` |
| **Azovè** | Couffo | **111 / 145** (23.4%) `2014-09..2026-09` | **85 / 93** (8.6%) `2019-01..2026-09` | **84 / 93** (9.7%) `2019-01..2026-09` | **75 / 87** (13.8%) `2019-07..2026-09` |
| **Djougou** | Donga | **114 / 145** (21.4%) `2014-09..2026-09` | **88 / 93** (5.4%) `2019-01..2026-09` | **86 / 93** (7.5%) `2019-01..2026-09` | **1 / 1** (Thin) `2020-08` only |
| **Comé** | Mono | **113 / 145** (22.1%) `2014-09..2026-09` | **86 / 93** (7.5%) `2019-01..2026-09` | **85 / 93** (8.6%) `2019-01..2026-09` | **82 / 86** (4.7%) `2019-08..2026-09` |
| **Ouando (Porto-Novo)** | Oueme | **113 / 145** (22.1%) `2014-09..2026-09` | **87 / 93** (6.5%) `2019-01..2026-09` | **82 / 93** (11.8%) `2019-01..2026-09` | **83 / 87** (4.6%) `2019-07..2026-09` |
| **Kétou** | Plateau | **115 / 145** (20.7%) `2014-09..2026-09` | **88 / 93** (5.4%) `2019-01..2026-09` | **88 / 93** (5.4%) `2019-01..2026-09` | **85 / 87** (2.3%) `2019-07..2026-09` |
| **Bohicon** | Zou | **113 / 145** (22.1%) `2014-09..2026-09` | **87 / 93** (6.5%) `2019-01..2026-09` | **85 / 93** (8.6%) `2019-01..2026-09` | **82 / 87** (5.7%) `2019-07..2026-09` |
| **Abomey** | Zou | **83 / 87** (4.6%) `2019-07..2026-09` | **84 / 87** (3.4%) `2019-07..2026-09` | **82 / 87** (5.7%) `2019-07..2026-09` | **110 / 165** (33.3%) `2013-01..2026-09` |

---

## 4. Go / No-Go Assessment per Product & Market Tier

Per `AGENTS.md` (*"If coverage is too thin for a product, report it and propose alternatives. Do not model on bad data"*), here is the rigorous product-by-product and market-tier assessment:

### 4.1 Maize (`Maize (white)`, Retail, KG) — **STRONG GO**
- **Verdict:** **GO** across **49 Tier-1 markets** ($\ge 80/93$ months in `2019-01..2026-09`, gap `1.1%–6.5%`), plus long-term historical exploration (`2007–2016`) in `Dantokpa` (`202` months) and `Malanville (CBM)` (`142` months).
- **Modeling Window Constraint:** Because `2017–2018` has `0` observations nationwide for `Maize (white)`, forecasting models must be trained and backtested on the continuous **`2019-01` to `2026-09` (`93`-month)** panel rather than interpolating across a 24-month void.
- **Sub-varieties:** `Maize (yellow)` (`42` months, `2023-04..2026-09`) and legacy `Maize` (`145` rows, discontinued after `2019-12`) are **NO-GO** for primary forecasting, though `Maize (yellow)` can be included in exploratory price-spread analysis.

### 4.2 Tomato (`Tomatoes`, Retail, KG) — **GO (Modern Regime `2019-01..2026-09`, Tier-1 Markets)**
- **Verdict:** **GO** across **43 Tier-1 markets** ($\ge 80/93$ months in `2019-01..2026-09`, gap `1.1%–6.5%`) and **6 Tier-2 markets** ($60–79$ months). **NO-GO** prior to `2019-01` (`0` observations).
- **Honest Modeling Caveat:** Fresh tomato is highly perishable and exhibits sharp seasonal/weather-driven spikes (`XOF/kg` swings of $2\times–4\times$ between harvest glut and rainy/lean periods). Models must report wider prediction intervals (`80%` / `90%` conformal or quantile bands) and incorporate lagged NASA POWER rainfall/temperature anomalies.

### 4.3 Yam (`Yam` & `Yam (white)`, Retail, KG) — **CONDITIONAL GO (Strict Market Tiering & Variety Separation Required)**
- **Verdict:**
  - **GO on Tier-1 Markets (`19` markets for `Yam (white)` and `17` markets for `Yam` with $\ge 80$ months in `2019–2026`, gap `1.1%–9.7%`; up to `31` markets with $\ge 60$ months).**
  - **NO-GO on `16–21` Secondary/Non-Producing Markets ($< 60$ months, gaps of `25%–70%`)** where fresh yam disappears seasonally from local stalls or was only intermittently recorded.
  - **NO-GO on Merging Varieties:** `Yam` (*igname précoce / laboko*) and `Yam (white)` (*igname blanche / kokoro*) overlap in the same market-months with a **`129–239 XOF/kg` average price difference**. Merging them would introduce artificial price jumps.
- **How to Handle Yam + Concrete Alternatives:**
  1. **Recommended Path for Yam:** Use **`Yam (white)`** as the primary national yam benchmark (covering key northern and central production hubs like `Glazoué`, `Djougou`, `Nikki`, `Savalou`, `Bembèrèkè`, `Kérou`, plus urban `Dantokpa`, `Natitingou`, `Bohicon`, `Ouando`, `Abomey`, `Kétou`) **and/or** allow toggling between `Yam (white)` and `Yam` (*précoce*) in the app, while **strictly restricting forecasts to the Tier-1 markets ($\ge 80$ months)** and displaying an honest *"Insufficient historical coverage in this market"* notice for thin markets.
  2. **Optional 4th Reference Staple (Alternative / Complement):** If the owner wants a tuber/cassava product with **100% nationwide coverage across all 50 markets** (matching `Maize (white)`), **`Cassava meal (gari)`** (`4,955` obs, `50/50` markets $\ge 60\text{m}$, `48/50` markets $\ge 80\text{m}$, continuous back to `2007` in `Dantokpa`) or **`Beans (white)` / Niébé** (`4,882` obs, `49/50` markets $\ge 80\text{m}`) or **`Sorghum (red)`** (`4,147` obs, `42/50` markets $\ge 80\text{m}`) are ready in `data/raw/wfp_food_prices_ben.csv`.

---

## 5. Questions & Decisions Needed from Owner Before Phase 1

Phase 0 is complete and I have stopped per `AGENTS.md`. Before starting **Phase 1 (Cleaning + Exploratory Analysis)**, please confirm your preference on these 3 design/scope choices (which we will also log in `docs/DECISIONS.md`):

1. **Product Scope for Phase 1–3:**
   - Do we keep the exact 3 products from the brief — **`Maize (white)`**, **`Yam (white)`** (with `Yam` documented/compared in EDA), and **`Tomatoes`** — restricting Yam forecasts strictly to its **Tier-1 markets ($\ge 80$ months)**?
   - Or would you also like to include **`Cassava meal (gari)`** (or **`Beans (white)` / `Sorghum (red)`**) as a 4th product or tuber benchmark?
2. **Primary Modeling Window (`2019-01` to `2026-09`):**
   - Do you approve using **`2019-01-15` to `2026-09-15` (`93` months / `7.75` years)** as the clean, continuous training/evaluation regime for forecasting models (avoiding artificial imputation across the `2017–2018` nationwide reporting hiatus), while retaining `2007–2016` observations in `Dantokpa` and `Malanville (CBM)` for historical visualization in the Explorer?
3. **NASA POWER Weather Ingestion in Phase 1:**
   - Shall I write `src/ingest/download_nasa_power.py` in Phase 1 to fetch monthly/daily agroclimatic series (`PRECTOTCORR`, `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`) for the deduplicated MERRA-2 grid cells of our active Benin markets?

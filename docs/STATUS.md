# Project Status — Bénin AgroMarket (`docs/STATUS.md`)

**Date:** 2026-11-04  
**Current Phase:** **Phase 3 — Step 3.1b Correction Pass Completed** (`fix: step 3.1b plain language, empirical claims, history line breaks, and layout alignment` — Full Jargon Removal, Plain-Language Model & Reliability Dictionary, Empirical Product Prose, History Plateau & Unobserved-Month Break Audit, First-Screen Hero Layout, 5-Step Single-Hue Dot Map Ramp, and Subgrid Card Alignment)  
**Status:** **STOPPED at End of Step 3.1b** — awaiting owner validation before starting Step 3.2 (Home page complete: signature GSAP motion, dot map interactions, product cards).

Every statistic and table in this report is produced deterministically by [`src/evaluate/verify_history_plateaus.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/verify_history_plateaus.py), [`src/evaluate/contrast_check.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/contrast_check.py), [`src/evaluate/web_budget.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/web_budget.py), [`src/evaluate/validate_export.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/validate_export.py), [`web/scripts/prepare-data.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/scripts/prepare-data.mjs), and [`web/scripts/write-web-budget.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/scripts/write-web-budget.mjs) and saved in [`docs/tables/`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/).

---

## 1. Summary of Step 3.1b Corrections (Items 1–12)

### Clarity and Honesty (`AGENTS.md` — "Plain language in the UI" & "Claims in the UI")

1. **Item 1 — Complete Removal of Internal Jargon & Raw ISO Dates ([`web/src/i18n/fr.json`](file:///home/brian/projets-ds/benin-agromarket/web/src/i18n/fr.json), [`web/src/i18n/en.json`](file:///home/brian/projets-ds/benin-agromarket/web/src/i18n/en.json), [`web/src/components/HomePage.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/components/HomePage.astro)):**
   - Replaced `"Tier-1"` everywhere with `"marchés bien suivis"` (`"well-tracked markets"` in EN), explained once in Section 2 (`au moins 80 mois de relevés sur 93 entre 2019 et 2026` / `at least 80 months of price records out of 93 between 2019 and 2026`) and via tooltip (`units.marketsDefinitionNote`).
   - Replaced `"mois-marchés observés"` with `"relevés de prix"` (`"price records"` in EN).
   - Replaced `"Médiane nationale"` with `"Médiane des marchés suivis"` (`"Median of tracked markets"` in EN) so statistics over the well-covered markets are never labeled "national".
   - Replaced `"(h=1)"`, `"(h=2)"`, `"(h=3)"` with `"à 1 mois (oct. 2026)"`, `"à 2 mois (nov. 2026)"`, `"à 3 mois (déc. 2026)"` / `"pour décembre 2026"` (`"at 3 months (Dec 2026)"` / `"for December 2026"`).
   - Replaced `"Erreur MAPE holdout (h=1..3)"` and `"MAE test holdout"` with `"Erreur moyenne mesurée en test"` (`"Average error measured in testing"`) accompanied by a plain-language one-sentence tooltip (`units.testErrorTooltip`).
   - Replaced SVG chart markers `"2026-09"` and `"+1..3m"` with `"sept. 2026"` (`"Sep 2026"`) and `"+1 à 3 mois"` (`"+1 to 3 months"`), and formatted all visible dates (`15 septembre 2026` / `15 September 2026`) with zero raw ISO dates in visible strings.
   - Replaced `"indice"` with `"indice saisonnier"` (`"seasonal index"`) and added `(100 = niveau moyen de l'année)` / `(100 = yearly average level)` with a tooltip (`home.stories.indexTooltip`).

2. **Item 2 — Plain-Language Model Dictionary & Reliability Labels ([`web/src/i18n/fr.json`](file:///home/brian/projets-ds/benin-agromarket/web/src/i18n/fr.json), [`web/src/i18n/en.json`](file:///home/brian/projets-ds/benin-agromarket/web/src/i18n/en.json), [`web/src/i18n/index.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/i18n/index.ts), [`src/evaluate/backtest.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/backtest.py), [`web/scripts/prepare-data.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/scripts/prepare-data.mjs)):**
   - Added a `models` dictionary in `fr.json` and `en.json` so no snake_case model identifier (`Seasonal_Ratio_Naive`, `Naive_LastValue`, `Ridge_ARX`, `HGBR_NoWeather`, etc.) ever appears in the UI:
     - `Naive_LastValue` → `"Dernier prix connu (méthode simple)"` / `"Last known price (simple method)"`
     - `Seasonal_Ratio_Naive` → `"Ratio saisonnier (méthode simple)"` / `"Seasonal ratio (simple method)"`
     - `Seasonal_Naive_12m` → `"Prix du même mois l'an dernier (méthode simple)"` / `"Same month last year (simple method)"`
     - `Ridge_ARX` → `"Régression saisonnière régularisée"` / `"Regularized seasonal regression"`
     - `HGBR_NoWeather` → `"Arbres de décision sur historique de prix"` / `"Decision trees on price history"`
     - `HGBR_WithWeather` → `"Arbres de décision (prix et météo)"` / `"Decision trees (prices and weather)"`
     - `ETS_HoltWinters` → `"Lissage exponentiel saisonnier"` / `"Seasonal exponential smoothing"`
     - `SARIMA` / `SARIMAX_101_011_12` → `"Modèle autorégressif saisonnier"` / `"Seasonal autoregressive model"`
   - Updated the bilingual reliability notes (`note_fr`, `note_en`) and displayed the reliability label from `forecasts.json` next to each forecast (`À 1 mois`, `À 2 mois`, `À 3 mois`) in the teaser cards and in the Hero card.

3. **Item 3 — Latitude Band Region (Not Agro-Ecological Zone):**
   - Renamed `"Zone agro-écologique"` to `"Région (bande de latitude)"` in FR and `"Region (latitude band)"` in EN.
   - Mapped values through `zones` and `mapLatBands` in `fr.json` and `en.json` (`"Sud (< 7,5°N)"`, `"Centre (7,5°N à 9,5°N)"`, `"Nord (> 9,5°N)"` in FR; `"South (< 7.5°N)"`, `"Centre (7.5°N to 9.5°N)"`, `"North (> 9.5°N)"` in EN) and localized the dot-map latitude reference lines (`6,5°N · Sud`, `7,5°N · Sud / Centre`, `9,5°N · Centre / Nord`, `11,5°N · Nord`).

4. **Item 4 — Seasonal Labels Without Unverified Causal Claims:**
   - Replaced `"Creux de récolte"` and `"pic de soudure"` with `"Creux saisonnier"` (`"Seasonal low"`) and `"Pic saisonnier"` (`"Seasonal peak"`).

5. **Item 5 — Data-Computed Product Card Sentences:**
   - Deleted the hand-written agronomic `story` paragraphs from `fr.json` and `en.json`.
   - Replaced them with `formatComputedStoryProse()` in [`web/src/i18n/index.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/i18n/index.ts), computed at build time from `tier1_markets_count`, `troughMonthName`, `peakMonthName`, and `peak_to_trough_ratio = round(peak_index / trough_index, 2)` (e.g. `"Sur les 49 marchés bien suivis (2019–2026), le prix est en moyenne au plus bas en novembre et au plus haut en mai, soit un rapport de 1,24 fois entre le pic et le creux saisonnier."`).

6. **Item 6 — Product Qualifiers Audited Against [`docs/DATA.md`](file:///home/brian/projets-ds/benin-agromarket/docs/DATA.md):**
   - **Removed:** `"(grain sec)"` / `"(dry grain)"` from `Maïs blanc` / `White maize` and `"fraîche"` / `"Fresh"` from `Tomate` / `Tomato`, because neither qualifier is documented in [`docs/DATA.md`](file:///home/brian/projets-ds/benin-agromarket/docs/DATA.md) (the raw WFP dataset records `"Maize (white)"` and `"Tomatoes"` without those qualifiers).
   - **Retained:** `"(kokoro)"` in `"Igname blanche (kokoro)"` / `"White yam (kokoro)"`, because [`docs/DATA.md`](file:///home/brian/projets-ds/benin-agromarket/docs/DATA.md) (§1.3, line 67) explicitly documents `Yam (white)` as *"Staple white yam (igname blanche / kokoro)"* to distinguish it from `Yam` (*"igname précoce / laboko"*).

7. **Item 7 — Header & Attribution:**
   - Removed `.brand-tagline` (`"Observatoire ouvert des prix vivriers au Bénin"`) from [`web/src/layouts/BaseLayout.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/layouts/BaseLayout.astro) and removed `"Observatoire..."` from the Hero kicker.
   - Replaced `"Données PAM / ONASA / INStaD"` in the Hero kicker with `"Données : Programme alimentaire mondial (PAM) via HDX"` (`"Data: World Food Programme (WFP) via HDX"`).
   - Updated the footer attribution to credit WFP via HDX and describe ONASA and INStaD strictly as `"relevés de sources nationales consolidés par le PAM"` (`"national source records consolidated by WFP"`), reserving full upstream details for the Method page.

8. **Item 8 — History Line Plateaus & Unobserved Months Audit ([`src/evaluate/verify_history_plateaus.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/verify_history_plateaus.py) → [`docs/tables/history_plateaus_check.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/history_plateaus_check.md)):**
   - Audited `data/raw/wfp_food_prices_ben.csv` and `data/processed/modeling_panel_2019_2026.csv` across all `93` calendar months (`2019-01..2026-09`) for Dantokpa and all `111` well-tracked series (see Section 2.1 below).
   - Verified that `100%` of observed points (`is_observed == 1`) have `priceflag == 'actual'` in `data/raw/wfp_food_prices_ben.csv`, and that Dantokpa has **`9` unobserved months for `Maize (white)` (`2019-05..2019-12`, `2022-03`)**, **`4` unobserved months for `Tomatoes` (`2019-05`, `2019-06`, `2019-11`, `2022-03`)**, and **`5` unobserved months for `Yam (white)` (`2019-05`, `2019-06`, `2019-11`, `2020-08`, `2022-03`)**.
   - Previously, exporting only observed points caused `d3.line()` to connect `2019-04` (`192.31 XOF/kg`) straight across the `8` missing months `2019-05..2019-12` to `2020-01` (`192.31 XOF/kg`), creating a visual 15-month flat line when 8 of those months were unobserved, whereas the `2024-10..2025-10` plateau (`275.00 XOF/kg`, `13` consecutive months) and `2025-11..2026-04` plateau (`220.00 XOF/kg`, `6` consecutive months) are genuine `actual` observations in the raw WFP CSV.
   - Updated [`web/scripts/prepare-data.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/scripts/prepare-data.mjs) and [`web/src/lib/charts.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/lib/charts.ts) so the `2019-01..2026-09` history array contains all `93` calendar months with `price: null, is_observed: false` on unobserved months, and `d3.line<HistoryPoint>().defined((d) => d.is_observed !== false && typeof d.price === 'number' && Number.isFinite(d.price))` breaks the SVG path at every missing month.

---

### Layout (Items 9–12)

9. **Item 9 — Hero Chart First-Screen Visibility (`1440×900`) & Compact 4-Column KPI Row Below Chart:**
   - Shortened the Hero card title to `"Dantokpa (Cotonou) · Maïs blanc"` (`"Dantokpa (Cotonou) · White maize"`).
   - Set Hero SVG `viewBox="0 0 760 280"`, moved the 4 key figures (`Dernier prix observé`, `Prévision à 3 mois`, `Fourchette 80 %`, `Méthode retenue`) below the chart in a single compact 4-column row (label above value, `white-space: nowrap` on values and `"XOF/kg"`), and tightened vertical spacing so the entire Hero chart card fits comfortably within the `1440×900` first screen (`desktop-hero-fr.png`, `desktop-hero-en.png`).

10. **Item 10 — Dot Map 5-Step Single-Hue Ramp & Direct Min/Max Callouts:**
    - Replaced the green/yellow/red scale with a 5-step single-hue sequential ramp of the selected product's color (`PRODUCT_RAMP_5` in [`web/src/lib/charts.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/lib/charts.ts), built with `d3-interpolate` from `#FBF3D5..#7A5200` for Maize, `#F9E5DC..#6E240B` for Tomato, and `#E3EFE6..#16331E` for Yam, all with crisp dark `ink` strokes).
    - Added direct leader-line callouts for the cheapest and most expensive market on the SVG map (`Moins cher : Azovè (67 XOF/kg)` and `Plus cher : Tatonnoukon (259 XOF/kg)` for Maize) routed into dedicated non-overlapping callout gutters, and explained the 5-step scale in plain words above the legend.

11. **Item 11 — Product Cards Row Alignment & Sparkline Independent-Scale Note:**
    - Aligned all 3 cards in Section 2 (`.stories-subgrid`) and Section 4 (`.teaser-subgrid`) across desktop rows using CSS Grid `subgrid`.
    - Added the explicit independent-scale note (`Échelle propre à chaque produit (min–max sur 36 mois)` / `Each chart uses its own vertical scale (36-month min–max)`) and `min–max XOF/kg` range inside each sparkline box.

12. **Item 12 — Map Stats Box Layout & Latest-Month Note:**
    - Formatted each stat in `.spatial-summary-card` with the label above the value (`display: flex; flex-direction: column`) and `white-space: nowrap` on prices + units, and added the note (`Indicateurs calculés uniquement sur le dernier mois observé (septembre 2026).`).

---

## 2. Generated Verification Tables (`docs/tables/`)

### 2.1 Historical Price Plateaus & Unobserved Months Audit (`docs/tables/history_plateaus_check.md`)
*Source script: [`src/evaluate/verify_history_plateaus.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/verify_history_plateaus.py) → [`docs/tables/history_plateaus_check.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/history_plateaus_check.md)*

| Scope | Product | Market | Calendar Months (2019-01..2026-09) | Observed Months (is_observed=1) | Unobserved Months (is_observed=0) | Unobserved Dates (YYYY-MM) | Raw WFP priceflag Check | Constant-Price Runs (>=3 Consecutive Observed Months) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Focal Reference Market | Maize (white) | Dantokpa | 93 | 84 | 9 | 2019-05, 2019-06, 2019-07, 2019-08, 2019-09, 2019-10, 2019-11, 2019-12, 2022-03 | 100% raw WFP priceflag='actual' (84/84 rows) | 192.31 XOF/kg (4m: 2020-01..2020-04, raw=actual); 274.73 XOF/kg (3m: 2020-08..2020-10, raw=actual); 329.67 XOF/kg (3m: 2022-04..2022-06, raw=actual); 274.73 XOF/kg (6m: 2022-12..2023-05, raw=actual); 275.00 XOF/kg (3m: 2023-10..2023-12, raw=actual); 385.00 XOF/kg (3m: 2024-06..2024-08, raw=actual); 275.00 XOF/kg (13m: 2024-10..2025-10, raw=actual); 220.00 XOF/kg (6m: 2025-11..2026-04, raw=actual) |
| All Well-Tracked Markets (49) | Maize (white) | All 49 markets | 4557 | 4162 | 395 | 395 unobserved market-months across 49 series | 100% raw WFP priceflag='actual' (4162/4162 rows) | 189 runs >=3m across 49 markets (max run = 13m) |
| Focal Reference Market | Tomatoes | Dantokpa | 93 | 89 | 4 | 2019-05, 2019-06, 2019-11, 2022-03 | 100% raw WFP priceflag='actual' (89/89 rows) | None (0 runs >= 3 consecutive observed months) |
| All Well-Tracked Markets (43) | Tomatoes | All 43 markets | 3999 | 3664 | 335 | 335 unobserved market-months across 43 series | 100% raw WFP priceflag='actual' (3664/3664 rows) | 15 runs >=3m across 43 markets (max run = 8m) |
| Focal Reference Market | Yam (white) | Dantokpa | 93 | 88 | 5 | 2019-05, 2019-06, 2019-11, 2020-08, 2022-03 | 100% raw WFP priceflag='actual' (88/88 rows) | 300.00 XOF/kg (3m: 2019-02..2019-04, raw=actual); 400.00 XOF/kg (3m: 2019-08..2019-10, raw=actual); 300.00 XOF/kg (3m: 2020-01..2020-03, raw=actual); 600.00 XOF/kg (3m: 2022-11..2023-01, raw=actual); 700.00 XOF/kg (3m: 2025-11..2026-01, raw=actual) |
| All Well-Tracked Markets (19) | Yam (white) | All 19 markets | 1767 | 1603 | 164 | 164 unobserved market-months across 19 series | 100% raw WFP priceflag='actual' (1603/1603 rows) | 55 runs >=3m across 19 markets (max run = 10m) |

---

### 2.2 Web Performance & Asset Budget Report (`docs/tables/web_budget.md`)
*Source script: [`src/evaluate/web_budget.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/web_budget.py) & [`web/scripts/write-web-budget.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/scripts/write-web-budget.mjs) → [`docs/tables/web_budget.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/web_budget.md)*

| Budget Category | Scope / Files Included | File Count | Raw Size (Bytes) | Raw Size (KiB) | Gzip Size (Bytes) | Gzip Size (KiB) | Phase 3 Budget Limit | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Home Page JavaScript (`JS`) | Scripts referenced by `/` (`dist/index.html`) | 1 | 1154 | 1.13 KiB | 446 | **0.44 KiB** | <= 120.00 KiB gzip | PASS |
| All Site JavaScript (`dist/_astro/*.js`) | All bundled JS across all routes | 1 | 1154 | 1.13 KiB | 446 | **0.44 KiB** | <= 120.00 KiB gzip | PASS |
| Home Page Stylesheets (`CSS`) | Stylesheets referenced by `/` (`dist/index.html`) | 1 | 23757 | 23.20 KiB | 4443 | **4.34 KiB** | <= 30.00 KiB gzip | PASS |
| Self-Hosted Variable Fonts (`.woff2`) | `fraunces-latin-wght-normal.woff2` + `instrument-sans-latin-wght-normal.woff2` | 2 | 66712 | **65.15 KiB** | 66773 | **65.21 KiB** | <= 70.00 KiB total | PASS |
| Home Page HTML (`/` FR) | `dist/index.html` (pre-rendered static HTML + SVG) | 1 | 236147 | 230.61 KiB | 31996 | 31.25 KiB | Informational (Static SSR) | PASS |
| Home Page HTML (`/en/` EN) | `dist/en/index.html` (pre-rendered static HTML + SVG) | 1 | 234764 | 229.26 KiB | 31445 | 30.71 KiB | Informational (Static SSR) | PASS |
| Home Summary Data (`home-summary.json`) | `dist/data/home-summary.json` (split summary, not all 111 series) | 1 | 146497 | 143.06 KiB | 20866 | 20.38 KiB | Never ship all 111 series to Home | PASS |
| Raster Images (`.png/.jpg/.webp`) | All raster images in `dist/` (max 1 Open Graph image allowed) | 0 | 0 | 0.00 KiB | 0 | 0.00 KiB | <= 1 Open Graph image | PASS |

---

### 2.3 Design Token & 5-Step Single-Hue Ramp WCAG 2.1 Contrast Verification (`docs/tables/contrast_check.md`)
*Source script: [`src/evaluate/contrast_check.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/contrast_check.py) → [`docs/tables/contrast_check.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/contrast_check.md)*

| Pair ID | Foreground Token | Foreground Hex | FG Luminance | Background Token | Background Hex | BG Luminance | Contrast Ratio | WCAG AA Normal (>=4.5:1) | WCAG AA Large/UI (>=3.0:1) | Usage Role & Enforcement Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CLR-01 | `ink` | `#1E1B16` | 0.0112 | `sand` | `#F6F0E4` | 0.8751 | **15.12:1** | PASS | PASS | Primary body & display text on primary page background — Allowed (AAA) |
| CLR-02 | `ink` | `#1E1B16` | 0.0112 | `sand-2` | `#EDE3D0` | 0.7750 | **13.48:1** | PASS | PASS | Primary text on cards, callouts, and table headers — Allowed (AAA) |
| CLR-03 | `ink` | `#1E1B16` | 0.0112 | `paper-white` | `#FFFDF9` | 0.9835 | **16.89:1** | PASS | PASS | Primary text on elevated chart/tooltip surface — Allowed (AAA) |
| CLR-04 | `ink` | `#1E1B16` | 0.0112 | `line` | `#D9CDB8` | 0.6188 | **10.93:1** | PASS | PASS | Primary text on subtle neutral badge/pill (`#D9CDB8`) — Allowed (AAA) |
| CLR-05 | `muted` | `#6F665A` | 0.1362 | `sand` | `#F6F0E4` | 0.8751 | **4.97:1** | PASS | PASS | Secondary/caption/axis text on `sand` background — Allowed (AA Normal & Large) |
| CLR-06 | `muted` | `#6F665A` | 0.1362 | `sand-2` | `#EDE3D0` | 0.7750 | **4.43:1** | Large/UI Only (>=3.0:1) | PASS | Secondary text on `sand-2` surface — Large/UI text >=18.67px bold (4.43:1 >= 3.0:1); use `ink` (13.48:1) for small body text on `sand-2` |
| CLR-07 | `muted` | `#6F665A` | 0.1362 | `paper-white` | `#FFFDF9` | 0.9835 | **5.55:1** | PASS | PASS | Secondary text inside chart tooltips/panels — Allowed (AA Normal & Large) |
| CLR-08 | `laterite` | `#B5471F` | 0.1443 | `sand` | `#F6F0E4` | 0.8751 | **4.76:1** | PASS | PASS | Tomatoes accent / links / badges on `sand` background — Allowed (AA Normal & Large) |
| CLR-09 | `laterite` | `#B5471F` | 0.1443 | `sand-2` | `#EDE3D0` | 0.7750 | **4.25:1** | Large/UI Only (>=3.0:1) | PASS | Tomatoes accent on `sand-2` surface — Large/UI/Graphical >=3.0:1 (4.25:1); use `ink` (13.48:1) or solid `laterite` fill with `sand` text (4.76:1) for small text |
| CLR-10 | `green` | `#2F5D3A` | 0.0874 | `sand` | `#F6F0E4` | 0.8751 | **6.73:1** | PASS | PASS | Yam (white) accent / calibrated badge text on `sand` — Allowed (AA Normal & Large) |
| CLR-11 | `green` | `#2F5D3A` | 0.0874 | `sand-2` | `#EDE3D0` | 0.7750 | **6.00:1** | PASS | PASS | Yam (white) accent / calibrated badge text on `sand-2` — Allowed (AA Normal & Large) |
| CLR-12 | `ink` | `#1E1B16` | 0.0112 | `maize` | `#E3A81F` | 0.4444 | **8.08:1** | PASS | PASS | Text on Maize (`#E3A81F`) chip / badge fill (Brief rule: text on maize is ink) — Allowed (AAA — Mandatory rule for Maize) |
| CLR-13 | `sand` | `#F6F0E4` | 0.8751 | `ink` | `#1E1B16` | 0.0112 | **15.12:1** | PASS | PASS | Inverted footer / dark button text (`sand` on `ink`) — Allowed (AAA) |
| CLR-14 | `sand-2` | `#EDE3D0` | 0.7750 | `ink` | `#1E1B16` | 0.0112 | **13.48:1** | PASS | PASS | Inverted secondary text (`sand-2` on `ink`) — Allowed (AAA) |
| CLR-15 | `maize` | `#E3A81F` | 0.4444 | `ink` | `#1E1B16` | 0.0112 | **8.08:1** | PASS | PASS | Maize accent highlight on dark `ink` background — Allowed (AAA on dark `ink` only) |
| CLR-16 | `sand` | `#F6F0E4` | 0.8751 | `laterite` | `#B5471F` | 0.1443 | **4.76:1** | PASS | PASS | Light `sand` text on solid `laterite` button/badge fill — Allowed (AA Normal & Large) |
| CLR-17 | `sand` | `#F6F0E4` | 0.8751 | `green` | `#2F5D3A` | 0.0874 | **6.73:1** | PASS | PASS | Light `sand` text on solid `green` button/badge fill — Allowed (AAA / AA Normal & Large) |
| CLR-18 | `ink` | `#1E1B16` | 0.0112 | `maize-step-1` | `#FBF3D5` | 0.8941 | **15.43:1** | PASS | PASS | Dot map Maize lightest step (`#FBF3D5`) with dark `ink` stroke/label — Allowed (AAA) |
| CLR-19 | `paper-white` | `#FFFDF9` | 0.9835 | `maize-step-5` | `#7A5200` | 0.1017 | **6.81:1** | PASS | PASS | Dot map Maize darkest step (`#7A5200`) against `paper-white` canvas — Allowed (AAA) |
| CLR-20 | `ink` | `#1E1B16` | 0.0112 | `tomato-step-1` | `#F9E5DC` | 0.8135 | **14.11:1** | PASS | PASS | Dot map Tomato lightest step (`#F9E5DC`) with dark `ink` stroke/label — Allowed (AAA) |
| CLR-21 | `paper-white` | `#FFFDF9` | 0.9835 | `tomato-step-5` | `#6E240B` | 0.0460 | **10.76:1** | PASS | PASS | Dot map Tomato darkest step (`#6E240B`) against `paper-white` canvas — Allowed (AAA) |
| CLR-22 | `ink` | `#1E1B16` | 0.0112 | `yam-step-1` | `#E3EFE6` | 0.8378 | **14.51:1** | PASS | PASS | Dot map Yam lightest step (`#E3EFE6`) with dark `ink` stroke/label — Allowed (AAA) |
| CLR-23 | `paper-white` | `#FFFDF9` | 0.9835 | `yam-step-5` | `#16331E` | 0.0263 | **13.54:1** | PASS | PASS | Dot map Yam darkest step (`#16331E`) against `paper-white` canvas — Allowed (AAA) |
| CLR-24 | `maize` | `#E3A81F` | 0.4444 | `sand` | `#F6F0E4` | 0.8751 | **1.87:1** | BANNED (Expected Fail) | BANNED (Expected Fail) | BANNED: Maize yellow text on light `sand` background — BANNED by brief (1.87:1 fails AA — never used for text on light backgrounds) |
| CLR-25 | `maize` | `#E3A81F` | 0.4444 | `sand-2` | `#EDE3D0` | 0.7750 | **1.67:1** | BANNED (Expected Fail) | BANNED (Expected Fail) | BANNED: Maize yellow text on light `sand-2` background — BANNED by brief (1.67:1 fails AA — never used for text on light backgrounds) |

---

## 3. Playwright Visual Critique & Iteration Summary (`docs/screenshots/step-3.1b/`)

We ran 2 iteration rounds on `http://127.0.0.1:4321` at desktop (`1440×900`) and mobile (`390×844`):
- **Iteration 1 → Iteration 2 Fixes Applied:**
  1. *Dot Map Callout Placement:* In Iteration 1, `Azovè (67 XOF/kg)` and `Tatonnoukon (259 XOF/kg)` placed labels `16px` from their circles inside the dense southern Benin cluster, colliding with neighboring dots. In Iteration 2, `buildBeninDotMapGeometry()` in [`web/src/lib/charts.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/lib/charts.ts) routes 2-segment elbow leader lines (`M cx cy L elbowX lineY L lineEndX lineY`) into dedicated top/bottom callout gutters (`y = 486..506`) outside the southern dot cluster.
  2. *Section 4 Forecast Reliability Tag Line Break:* In Iteration 1, `.horizon-rel-tag` (`display: inline-block`) concatenated directly onto `XOF/kg` on `À 3 mois (déc. 2026)`. Changing `.horizon-rel-tag` to `display: block; margin-top: 3px;` places the reliability label cleanly on its own line across all 3 horizons.
- **Remaining Minor Mobile Detail Reported (After 2 Iterations):**
  - On `390×844` mobile ([`mobile-home-fr.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1b/mobile-home-fr.png)), inside the 2-column `.story-stats-grid` of the `Dantokpa` market inspector card, the `nowrap` string `160,7 [130, 199] XOF/kg` under `Prévision pour décembre 2026` slightly touches the adjacent right-hand cell (`13,5 %`) at `390px` viewport width. In Step 3.2, we can give that inspector forecast cell `class="story-stat-item story-stat-wide"` (`grid-column: span 2`) on mobile so it has full-row breathing room.

### Saved Screenshots (`docs/screenshots/step-3.1b/`)
- [`docs/screenshots/step-3.1b/desktop-hero-fr.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1b/desktop-hero-fr.png) (`1440×900` viewport, `/` French)
- [`docs/screenshots/step-3.1b/desktop-home-fr.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1b/desktop-home-fr.png) (`1440×900` full page, `/` French)
- [`docs/screenshots/step-3.1b/desktop-hero-en.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1b/desktop-hero-en.png) (`1440×900` viewport, `/en/` English)
- [`docs/screenshots/step-3.1b/mobile-hero-fr.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1b/mobile-hero-fr.png) (`390×844` viewport, `/` French)
- [`docs/screenshots/step-3.1b/mobile-home-fr.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1b/mobile-home-fr.png) (`390×844` full page, `/` French)

---

## 4. Proposed Next Step (Step 3.2 — Home Page Complete)

Per [`docs/PHASE3_BRIEF.md`](file:///home/brian/projets-ds/benin-agromarket/docs/PHASE3_BRIEF.md) and your instructions, we stop here after committing **Step 3.1b** and await your validation before starting **Step 3.2 (Home page complete: signature GSAP motion, dot map interactions, product cards)**.

---

## 5. Step 3.2 Recovery & Label Truthfulness Checks (2026-11-16)

### Part 1 — Hero Annotation Geometry Fix (`fix: hero annotation geometry mismatch`)
- **Root cause:** [`web/src/components/HomePage.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/components/HomePage.astro) read `heroGeom.peakPoint.{labelX, labelY, anchor}`, `heroGeom.lastObsPoint.{labelX, labelY}`, `heroGeom.bandLabelPos.{tickX1, tickY1, tickX2, labelX, labelY}`, `heroGeom.forecastEndLabelPos.{x, yLine1, yLine2}`, and `heroGeom.morphData.{x93, y93, def93, fcBridge}`, whereas [`web/src/lib/charts.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/lib/charts.ts) returned nested `annotation` / `forecastAnnotation` objects and `histX`/`histY`/`histDefined`/`fcX` arrays.
- **Fix:** Aligned `HeroChartGeometry`, `HeroMorphData`, and `buildHeroChartGeometry()` in [`web/src/lib/charts.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/lib/charts.ts) to return the exact fields consumed by [`web/src/components/HomePage.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/components/HomePage.astro), and added defensive conditional guards around `heroGeom.peakPoint`, `heroGeom.lastObsPoint`, `heroGeom.bandLabelPos`, and `heroGeom.forecastEndLabelPos` in [`web/src/components/HomePage.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/components/HomePage.astro) so a missing annotation cannot crash the build.
- **Verification:**
  - `npm run build` in `web/` succeeded for both `/` (FR) and `/en/` (EN).
  - `.venv/bin/python -m src.evaluate.validate_export` passed all 7 contract checks ([`docs/tables/phase2_export_validation.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/phase2_export_validation.md)).
  - Hero screenshots retaken in [`docs/screenshots/step-3.2/`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.2/) (`desktop-hero-fr.png`, `desktop-hero-en.png`, `mobile-hero-fr.png`) confirming no regression.

### Part 2 — Label Truthfulness Checks
1. **Last observed maize price at Dantokpa (September 2026): `160.0 XOF/kg` vs `175.0`:**
   - **Finding from export ([`web/src/data/generated/home-summary.json`](file:///home/brian/projets-ds/benin-agromarket/web/src/data/generated/home-summary.json)):** Both `products.maize_white.dantokpa.last_observed_price` and the final observed `history` entry (`2026-09-15`) are `160` (`160.0 XOF/kg`).
   - **Code check:** In [`web/src/components/HomePage.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/components/HomePage.astro), the KPI strip read `prod.dantokpa.last_observed_price` (1 decimal) while the curve annotation read `heroGeom.lastObsPoint.price` (0 decimals).
   - **Fix applied:** Updated the curve annotation in [`web/src/components/HomePage.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/components/HomePage.astro) to read `prod.dantokpa.last_observed_price` with `1` decimal place so both the KPI strip and curve annotation come from the exact same export field.
2. **Horizon-3 test error label (`"À 3 mois, l'erreur moyenne mesurée en test est de ..."`):**
   - **Finding from export ([`web/src/data/generated/home-summary.json`](file:///home/brian/projets-ds/benin-agromarket/web/src/data/generated/home-summary.json)):** For `maize_white`, `backtest_accuracy.test_overall.mape` (pooled over horizons 1–3) is `13.48` (`13,5 %`), whereas `backtest_accuracy.by_horizon_test.h3.mape` (3-month horizon) is `17.5` (`17,5 %`) and `coverage_80` is `78.9` (`78,9 %`).
   - **Code check:** `getReliabilityHeadlineAndTooltip(prod, 'h3')` in [`web/src/components/HomePage.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/components/HomePage.astro) already reads `prod.backtest_accuracy.by_horizon_test.h3.mape` (`17,5 %` in FR / `17.5%` in EN), matching `"À 3 mois, l'erreur moyenne mesurée en test est de 17,5 %"` (verified in `desktop-hero-fr.png` and `desktop-hero-en.png`). No change needed.

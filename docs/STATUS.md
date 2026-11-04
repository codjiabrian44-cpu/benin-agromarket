# Project Status — Bénin AgroMarket (`docs/STATUS.md`)

**Date:** 2026-11-04  
**Current Phase:** **Phase 3 — Step 3.1 Completed** (`feat: step 3.1 web foundations and static home page` — Astro 7 Static Project, Design Tokens & Contrast Verification, Self-Hosted Variable Fonts, Bilingual FR/EN i18n, Build-Time Data Splitter & Validator, Static Home Page, and Post-Build Asset Budget Report)  
**Status:** **STOPPED at End of Step 3.1** — awaiting owner validation before starting Step 3.2 (Home page complete: signature GSAP motion, enhanced dot map interactions, product cards).

Every statistic and table in this report is produced deterministically by [`src/evaluate/contrast_check.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/contrast_check.py), [`src/evaluate/web_budget.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/web_budget.py), [`web/scripts/prepare-data.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/scripts/prepare-data.mjs), [`web/scripts/write-web-budget.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/scripts/write-web-budget.mjs), and [`src/evaluate/validate_export.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/validate_export.py) and saved in [`docs/tables/`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/).

---

## 1. Compliance with Step 3.1 Conditions (1–6)

1. **Condition 4 — Node.js Runtime Verification (`>= 22.12.0`):**
   - Verified `node -v` is **`v24.22.1`** (`>= 22.12.0`, Astro 7 requirement) and `npm -v` is **`11.19.1`**.
2. **Condition 1 & 2 — Strict Package Allowlist & 14-Day Publish Age Check (`<= 2026-10-21T10:37:23Z`):**
   - Checked `npm view <pkg> time --json` for all approved packages before installing. Six packages had `latest` versions published within the last 3 days (`2026-11-02..04`), so we selected and pinned the latest version older than 14 days:
     - `astro`: **`7.4.1`** (published `2026-10-19T12:20:32Z`; `7.4.5` from `2026-11-02` skipped as `< 14` days old)
     - `gsap`: **`3.15.0`** (published `2026-04-13T16:33:13Z`; `3.15.1` from `2026-11-04` skipped as `< 14` days old)
     - `d3-scale`: **`4.0.2`** (published `2021-09-24T17:17:00Z`; `4.0.3` from `2026-11-03` skipped as `< 14` days old)
     - `d3-shape`: **`3.2.0`** (published `2022-12-20T18:55:27Z`; `3.2.1` from `2026-11-03` skipped as `< 14` days old)
     - `d3-array`: **`3.2.4`** (published `2023-05-30T16:40:10Z`; `3.2.5` from `2026-11-03` skipped as `< 14` days old)
     - `d3-interpolate`: **`3.0.1`** (published `2021-06-05T03:07:37Z`; `3.0.2` from `2026-11-03` skipped as `< 14` days old)
     - `@fontsource-variable/fraunces`: **`5.3.0`** (published `2026-07-19T22:55:47Z`, license `OFL-1.1`)
     - `@fontsource-variable/instrument-sans`: **`5.3.0`** (published `2026-07-19T22:57:08Z`, license `OFL-1.1`)
     - `devDependencies`: `@types/d3-scale` **`4.0.9`** (`2025-02-05`), `@types/d3-shape` **`3.2.0`** (`2026-08-21`), `@types/d3-array` **`3.2.2`** (`2025-09-12`), `@types/d3-interpolate` **`3.0.4`** (`2023-11-07`).
   - Zero extra packages installed.
3. **Condition 3 — Exact Version Pinning (`--save-exact`), Lockfile & Security Audit (`npm audit`):**
   - Installed with `--save-exact` in [`web/package.json`](file:///home/brian/projets-ds/benin-agromarket/web/package.json) and tracked [`web/package-lock.json`](file:///home/brian/projets-ds/benin-agromarket/web/package-lock.json).
   - Ran `npm audit` in `web/`: **`found 0 vulnerabilities`**.
4. **Condition 5 — Font Size Measurement (`<= 70 KB` Total Budget) & Self-Hosted SIL OFL Licenses:**
   - Measured the Latin variable `wght-normal` `.woff2` subset files from `@fontsource-variable/fraunces` and `@fontsource-variable/instrument-sans` (covering `U+0000-00FF`, `U+0152-0153` [`Œ, œ`], `U+2000-206F`, `U+2212`, etc. for complete French and English typography):
     - `web/public/fonts/fraunces-latin-wght-normal.woff2`: **`36,620` bytes (`35.76 KiB`)**
     - `web/public/fonts/instrument-sans-latin-wght-normal.woff2`: **`30,092` bytes (`29.39 KiB`)**
     - **Combined total:** **`66,712` bytes (`65.15 KiB` <= `70.00 KiB` budget)**.
   - Because `65.15 KiB <= 70.00 KiB`, installing `fonttools` and `brotli` in `.venv` was **not** needed.
   - Copied both SIL Open Font License (`OFL-1.1`) files alongside the self-hosted fonts in `web/public/fonts/` ([`FRAUNCES-LICENSE-OFL.txt`](file:///home/brian/projets-ds/benin-agromarket/web/public/fonts/FRAUNCES-LICENSE-OFL.txt) and [`INSTRUMENT-SANS-LICENSE-OFL.txt`](file:///home/brian/projets-ds/benin-agromarket/web/public/fonts/INSTRUMENT-SANS-LICENSE-OFL.txt)).

---

## 2. Step 3.1 Foundations Built

1. **Build-Time Data Splitter & Validator ([`web/scripts/prepare-data.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/scripts/prepare-data.mjs) & [`web/src/lib/data.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/lib/data.ts)):**
   - Validates `web/public/data/forecasts.json` at build time (`111` Tier-1 series across `49` maize, `43` tomato, and `19` yam markets; `333` forecast points; strict interval ordering `low_90 <= low_80 <= point_forecast <= high_80 <= high_90`; `0` `NaN`/null values; `0` markets with tier `"None"` while having observations).
   - Splits `forecasts.json` (`1,182.9 KiB`) into:
     - `web/public/data/home-summary.json` (`143.99 KiB` raw / `19.92 KiB` gzip — containing only Dantokpa reference series, 36-month national median sparklines, seasonal peak/trough metrics from [`docs/tables/eda_seasonality_summary.csv`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/eda_seasonality_summary.csv), Tier-1 dot-map coordinates/prices, and holdout accuracy/reliability summaries; **never ships all 111 series to the home page**),
     - `web/public/data/product-maize_white.json` (`49` series),
     - `web/public/data/product-tomatoes.json` (`43` series),
     - `web/public/data/product-yam_white.json` (`19` series),
     - `web/public/data/method-tables.json` (structured export of Phase 1/2 evaluation tables for Step 3.4).
2. **Design Tokens & WCAG AA Contrast Verification ([`web/src/styles/global.css`](file:///home/brian/projets-ds/benin-agromarket/web/src/styles/global.css) & [`src/evaluate/contrast_check.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/contrast_check.py) → [`docs/tables/contrast_check.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/contrast_check.md)):**
   - Implemented the exact palette (`ink #1E1B16`, `sand #F6F0E4`, `sand-2 #EDE3D0`, `laterite #B5471F`, `maize #E3A81F`, `green #2F5D3A`, `muted #6F665A`, `line #D9CDB8`), fluid `clamp()` typography scale (`body >= 17px` on mobile, `max-width: 68ch`), and 12-column desktop / 4-column mobile grid.
   - Enforced the brief rule that **Maize yellow (`#E3A81F`) is never used for text on light backgrounds (`1.87:1` on `sand`); text on `maize` is always `ink` (`#1E1B16`, `8.08:1` AAA)**.
3. **Bilingual i18n Skeleton ([`web/src/i18n/fr.json`](file:///home/brian/projets-ds/benin-agromarket/web/src/i18n/fr.json), [`web/src/i18n/en.json`](file:///home/brian/projets-ds/benin-agromarket/web/src/i18n/en.json), [`web/src/i18n/index.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/i18n/index.ts)):**
   - French default at `/` ([`web/src/pages/index.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/pages/index.astro)), English at `/en/` ([`web/src/pages/en/index.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/pages/en/index.astro)).
   - Zero hardcoded UI strings or statistics in components; single `PUBLIC_BASE_PATH` config variable in [`web/astro.config.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/astro.config.mjs).
4. **Layout, D3 SVG Geometry Builders & Static Home Page ([`web/src/layouts/BaseLayout.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/layouts/BaseLayout.astro), [`web/src/lib/charts.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/lib/charts.ts), [`web/src/components/HomePage.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/components/HomePage.astro)):**
   - Custom SVG charts built strictly with `d3-scale`, `d3-shape`, `d3-array`, and `d3-interpolate` (zero external chart libraries):
     - **Section 1 (Hero):** Title, subtitle, CTAs, product chips (`Maïs blanc`, `Tomate`, `Igname blanche`), and Dantokpa reference market history (`2019–2026`) + 3-month dashed forecast (`oct.–déc. 2026`) with `80%` and `90%` bands, reliability badge, bilingual holdout note, model used, `as_of_date`, nominal retail XOF/kg notice, and accessible `<details>` data table.
     - **Section 2 (*"Trois produits, trois histoires"*):** One card per product with a 36-month national median sparkline, seasonal peak and trough months and indices, amplitude, latest national median and Dantokpa prices, all computed from data.
     - **Section 3 (*"Un même kilo, des prix différents"*):** Coordinate-accurate dot map of Tier-1 markets (`latitude`/`longitude`, no base map), colored by latest price relative to the national median, interactive market inspector on hover/tap/focus, and an accessible `<details>` table alternative for all Tier-1 markets.
     - **Section 4 (*"Ce que disent les prévisions"*):** Teaser cards per product with the holdout reliability badge, `h=1..3` forecasts, holdout MAE/MAPE, skill vs best validation baseline, and links to `/previsions` and `/methode`.
     - **Footer:** Exact WFP attribution text from `docs/DECISIONS.md`, data as-of date (`2026-09-15`), GitHub link, and unofficial project notice.

---

## 3. Generated Verification Tables (`docs/tables/`)

### 3.1 Web Performance & Asset Budget Report (`docs/tables/web_budget.md`)
*Source script: [`src/evaluate/web_budget.py`](file:///home/brian/projets-ds/benin-agromarket/src/evaluate/web_budget.py) & [`web/scripts/write-web-budget.mjs`](file:///home/brian/projets-ds/benin-agromarket/web/scripts/write-web-budget.mjs) → [`docs/tables/web_budget.md`](file:///home/brian/projets-ds/benin-agromarket/docs/tables/web_budget.md)*

| Budget Category | Scope / Files Included | File Count | Raw Size (Bytes) | Raw Size (KiB) | Gzip Size (Bytes) | Gzip Size (KiB) | Phase 3 Budget Limit | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Home Page JavaScript (`JS`) | Scripts referenced by `/` (`dist/index.html`) | 1 | 1154 | 1.13 KiB | 446 | **0.44 KiB** | <= 120.00 KiB gzip | PASS |
| All Site JavaScript (`dist/_astro/*.js`) | All bundled JS across all routes | 1 | 1154 | 1.13 KiB | 446 | **0.44 KiB** | <= 120.00 KiB gzip | PASS |
| Home Page Stylesheets (`CSS`) | Stylesheets referenced by `/` (`dist/index.html`) | 1 | 22706 | 22.17 KiB | 4142 | **4.04 KiB** | <= 30.00 KiB gzip | PASS |
| Self-Hosted Variable Fonts (`.woff2`) | `fraunces-latin-wght-normal.woff2` + `instrument-sans-latin-wght-normal.woff2` | 2 | 66712 | **65.15 KiB** | 66773 | **65.21 KiB** | <= 70.00 KiB total | PASS |
| Home Page HTML (`/` FR) | `dist/index.html` (pre-rendered static HTML + SVG) | 1 | 220634 | 215.46 KiB | 30576 | 29.86 KiB | Informational (Static SSR) | PASS |
| Home Page HTML (`/en/` EN) | `dist/en/index.html` (pre-rendered static HTML + SVG) | 1 | 219014 | 213.88 KiB | 30040 | 29.34 KiB | Informational (Static SSR) | PASS |
| Home Summary Data (`home-summary.json`) | `dist/data/home-summary.json` (split summary, not all 111 series) | 1 | 147448 | 143.99 KiB | 20397 | 19.92 KiB | Never ship all 111 series to Home | PASS |
| Raster Images (`.png/.jpg/.webp`) | All raster images in `dist/` (max 1 Open Graph image allowed) | 0 | 0 | 0.00 KiB | 0 | 0.00 KiB | <= 1 Open Graph image | PASS |

---

### 3.2 Design Token WCAG 2.1 Contrast Verification (`docs/tables/contrast_check.md`)
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
| CLR-18 | `maize` | `#E3A81F` | 0.4444 | `sand` | `#F6F0E4` | 0.8751 | **1.87:1** | BANNED (Expected Fail) | BANNED (Expected Fail) | BANNED: Maize yellow text on light `sand` background — BANNED by brief (1.87:1 fails AA — never used for text on light backgrounds) |
| CLR-19 | `maize` | `#E3A81F` | 0.4444 | `sand-2` | `#EDE3D0` | 0.7750 | **1.67:1** | BANNED (Expected Fail) | BANNED (Expected Fail) | BANNED: Maize yellow text on light `sand-2` background — BANNED by brief (1.67:1 fails AA — never used for text on light backgrounds) |

---

## 4. Playwright Visual Critique & Iteration Summary (`docs/screenshots/step-3.1/`)

Per the Quality Gate in [`docs/PHASE3_BRIEF.md`](file:///home/brian/projets-ds/benin-agromarket/docs/PHASE3_BRIEF.md), we inspected desktop (`1440×900`) and mobile (`390×844`) screenshots on `http://127.0.0.1:4321`, critiqued weak points honestly, and resolved them within 2 iterations:

1. **Hero Chart 3-Month Forecast Legibility:**
   - *Iteration 1 issue:* Plotting `3` forecast months (`2026-10..12`) on the exact same linear pixel scale as `93` historical months (`2019-01..2026-09`) compressed the `h=1..3` forecast and its `80%`/`90%` bands into a `22px` sliver at the right edge.
   - *Fix applied in [`web/src/lib/charts.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/lib/charts.ts) & [`web/src/components/HomePage.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/components/HomePage.astro):* Allocated a dedicated `108px` forecast horizon zone (`+1..3m`) to the right of the `2026-09` cut line with a subtle shaded backdrop so the dashed forecast path, `h=1, 2, 3` dots, and `80%`/`90%` uncertainty bands are immediately legible on both desktop and mobile.
2. **Benin Dot Map Latitude Label Gutter:**
   - *Iteration 1 issue:* Latitude reference labels (`6.5°N..11.5°N`) at `x=32` overlapped western market dots (`Djougou`, `Natitingou`, `Comè`).
   - *Fix applied in [`web/src/lib/charts.ts`](file:///home/brian/projets-ds/benin-agromarket/web/src/lib/charts.ts):* Reserved a dedicated left label gutter (`x=12..118`) and mapped Benin longitudes (`0.72°E..3.92°E`) to `x=124..396`, eliminating all label-to-dot collisions.
3. **Mobile Header Height, Horizontal Scrollbar & Sticky Artifact:**
   - *Iteration 1 issue:* On `390×844` mobile, the header stacked inefficiently and `flex-wrap: nowrap` on `.nav-list` caused a `17px` horizontal overflow (`"Méthode & li"` clipped); additionally, `position: sticky` caused Playwright full-page screenshots to duplicate the header mid-scroll.
   - *Fix applied in [`web/src/layouts/BaseLayout.astro`](file:///home/brian/projets-ds/benin-agromarket/web/src/layouts/BaseLayout.astro) & [`web/src/styles/global.css`](file:///home/brian/projets-ds/benin-agromarket/web/src/styles/global.css):* Paired the brand lockup and `English` button on row 1 and placed the 4 navigation links across row 2 (`width: 100%`) with zero horizontal overflow, disabled Astro's dev toolbar (`devToolbar: { enabled: false }`), added [`web/public/favicon.svg`](file:///home/brian/projets-ds/benin-agromarket/web/public/favicon.svg), and added `white-space: nowrap` to `.kpi-delta`.

### Saved Screenshots (`docs/screenshots/step-3.1/`)
- [`docs/screenshots/step-3.1/desktop-hero-fr.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1/desktop-hero-fr.png) (`1440×900` viewport, `/` French)
- [`docs/screenshots/step-3.1/desktop-home-fr.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1/desktop-home-fr.png) (`1440×900` full page, `/` French)
- [`docs/screenshots/step-3.1/desktop-hero-en.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1/desktop-hero-en.png) (`1440×900` viewport, `/en/` English)
- [`docs/screenshots/step-3.1/mobile-hero-fr.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1/mobile-hero-fr.png) (`390×844` viewport, `/` French)
- [`docs/screenshots/step-3.1/mobile-home-fr.png`](file:///home/brian/projets-ds/benin-agromarket/docs/screenshots/step-3.1/mobile-home-fr.png) (`390×844` full page, `/` French)

---

## 5. Proposed Next Step (Step 3.2 — Home Page Complete)

Per [`docs/PHASE3_BRIEF.md`](file:///home/brian/projets-ds/benin-agromarket/docs/PHASE3_BRIEF.md), we stop here for your validation. Once approved, we will proceed to **Step 3.2 (Home page complete)**:
- Signature GSAP hero motion: price line self-drawing (`stroke-dashoffset`, `~1.6 s`), dashed forecast extension and `80%`/`90%` band fade-in, and smooth path/scale morphing (`~600 ms`) when switching product chips (`Maïs blanc`, `Tomate`, `Igname blanche`).
- ScrollTrigger subtle section fade-up (`24px`, `~400 ms`, once, no scroll-jacking, no parallax on mobile) and full `prefers-reduced-motion: reduce` instant-final-state support.
- Enhanced dot map floating tooltip and product card transitions.

# Phase 3 brief: Bénin AgroMarket web app

## Stack decisions
- Astro (static output) + TypeScript. Plain CSS with custom properties. No UI framework, no Tailwind.
- Charts: custom SVG built with D3 modules only (d3-scale, d3-shape, d3-array, d3-interpolate). No chart library.
- Motion: GSAP with ScrollTrigger. Add Flip only if it clearly earns its place. Respect prefers-reduced-motion everywhere.
- Fonts: self-hosted, subset, variable woff2. Display: Fraunces. Text: Instrument Sans. Verify availability and license (SIL OFL) first; if unavailable, propose an open-licensed equivalent pair.
- Data: static JSON in web/public/data. At build time, split forecasts.json into one small file per product plus a tiny summary file for the home page. Never ship all 111 series to the home page.
- i18n: French by default at /, English under /en/. All visible strings in src/i18n/fr.json and en.json. No hardcoded text in components.
- Hosting target: static site (GitHub Pages first). Set the base path through one config variable.
- Packages: install only with my approval, and only astro, gsap, d3-scale, d3-shape, d3-array, d3-interpolate and the font packages. No analytics, no trackers, no third-party scripts, no CDN fonts.

## Design tokens
- Colors: ink #1E1B16, sand #F6F0E4, sand-2 #EDE3D0, laterite #B5471F, maize #E3A81F, green #2F5D3A, muted #6F665A, line #D9CDB8.
- Product colors, used identically everywhere: maize (white) = maize yellow, tomatoes = laterite, yam (white) = green.
- Maize yellow is never used for text on light backgrounds. Text on maize is ink. Check AA contrast for every text/background pair with a script and save the result in docs/tables/contrast_check.md.
- Type: fluid scale with clamp(). Large display sizes with tight leading. Body text at least 17px on mobile. Line length 70 characters at most.
- Layout: 12 columns on desktop, 4 on mobile. Generous whitespace, one idea per screen. Original look: principles from The Pudding, Our World in Data and Reuters Graphics, never their layouts or assets.

## Content rules
- Every number shown comes from the JSON export or a generated table. Never type a statistic in a component. If a figure is missing from the export, add it to the export script in src/ and run the validator.
- Honesty is a feature: every forecast shows its reliability label, its interval, the model used and the as-of date. Use the bilingual reliability notes already present in forecasts.json.
- Prices are nominal XOF/kg, retail. Say so near charts.

## Pages
1. Home (/ and /en/)
   - Hero: title "Les prix du marché, enfin lisibles." Subtitle: "Maïs, tomate, igname : l'historique, les saisons et des prévisions à 3 mois pour les marchés du Bénin, avec leurs limites." Buttons: "Explorer les prix" and "Voir les prévisions". Product chips: Maïs blanc, Tomate, Igname blanche.
   - Hero chart: price history of the selected product at the Dantokpa market, with the 3-month forecast dashed and its 80%/90% bands.
   - Section "Trois produits, trois histoires": one card per product with a sparkline, its seasonal peak and trough months, and its latest price, all computed from data.
   - Section "Un même kilo, des prix différents": dot map of the Tier-1 markets for the selected product, no base map, each dot is a market positioned by latitude and longitude, colored by latest price relative to the median. Hover or tap shows the market and price. Provide an accessible table alternative.
   - Section "Ce que disent les prévisions": a short teaser with the reliability badge and a link to the forecast page.
   - Footer: WFP attribution (exact text in docs/DECISIONS.md), data as-of date, GitHub link, "unofficial project" notice.
2. Explorer (/explorer, /en/explorer): choose product, then market (searchable, grouped by department, Tier-1 markets only). Line chart with range presets (1 year, 3 years, all), tooltip and keyboard-navigable crosshair, seasonality chart by month, optional comparison to the median of Tier-1 markets, and a data table in a details element. Shareable URL through query parameters.
3. Forecast (/previsions, /en/forecast): same selectors. Last 24 months plus the next 3 months with 80%/90% bands. Reliability block, model used, backtest accuracy and gain over the best baseline, "how to read this chart" in 3 short lines, and a clear warning that statistical forecasts can be wrong, especially for tomatoes.
4. Method and limits (/methode, /en/method): data and sources, coverage and the 2017-2018 hiatus, methods and evaluation protocol in plain language, what the models cannot do, accuracy summary table from the generated phase 2 tables, exact attribution text, link to the GitHub repository.
5. 404 page, in the same style.

## Motion
- Signature moment (home hero): the price line draws itself (stroke-dashoffset, about 1.6 s), then the dashed forecast extends and the bands fade in. Switching product morphs the path (about 600 ms).
- Elsewhere: subtle fade-up (24px, about 400 ms, once). No scroll-jacking. No parallax on mobile.
- Page transitions: short fade with a slight slide (about 250 ms).
- Animate only transform, opacity and stroke-dashoffset.
- With prefers-reduced-motion: no animation, final state shown immediately.

## Performance and accessibility budgets
- Home page: JS at most 120 KB gzip, CSS at most 30 KB gzip, fonts at most 70 KB in total, no raster images except one Open Graph image. Target LCP under 2.5 s with Slow 4G throttling and CLS under 0.05.
- After every build, a script writes the gzip sizes of JS, CSS and fonts to docs/tables/web_budget.md.
- Semantic landmarks, skip link, visible focus, touch targets of at least 44px, correct lang attribute per page, charts with text alternatives and data tables, no information conveyed by color alone.

## Quality gate for every step
- Run the dev server on localhost, take desktop (1440x900) and mobile (390x844) screenshots with Playwright, save them in docs/screenshots/<step>/, critique them honestly against this brief and BRIEF.md, and fix the weak points.
- At most 2 iteration rounds per step, then report remaining issues in docs/STATUS.md instead of looping.
- At the end of each step: update docs/STATUS.md, commit, and STOP for my validation.

## Steps
- 3.1 Foundations: Astro project in web/ (keep web/public/data), tokens, fonts, i18n skeleton, layout with navigation and footer, static home page (no animation yet), data loader with build-time validation.
- 3.2 Home page complete: signature motion, dot map, product cards.
- 3.3 Explorer and Forecast pages.
- 3.4 Method and limits page, 404, accessibility and performance pass, polish.

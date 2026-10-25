# Bénin AgroMarket — Brief

## Vision
A fast, beautiful and honest web app that makes staple food prices in Benin (maize, yam, tomato) understandable and forecastable for producers, traders and curious citizens. It is also the flagship data science project of a student portfolio: rigorous and explainable first, beautiful second, impressive third.

## Audience and context
- Primary users: producers and traders in Benin, mostly on mid-range Android phones and unstable mobile connections.
- Secondary: recruiters and the data science community reviewing a portfolio.
- Language: French first, with an English toggle.

## Data (to verify in Phase 0, do not assume)
Candidates:
- WFP food prices for Benin (on HDX): check markets, commodities (maize, yam, tomato), unit, retail vs wholesale, date range, last update.
- FAOSTAT producer prices and consumer price index for Benin: national level, context and sanity checks.
- NASA POWER daily weather (rainfall, temperature) at the coordinates of each market.
- If WFP coverage is thin, other candidates to check (not confirmed to exist or be accessible): price bulletins from Benin's national food security office (ONASA), FEWS NET price data. Report accessibility and license. Never scrape against terms of use.
Phase 0 must answer: which of the 3 products has enough clean history to forecast, and for which markets?

## Deliverables
1. Documented, reproducible data pipeline in src/ with docs/DATA.md.
2. Exploratory analysis: seasonality, trends, market differences, shocks.
3. Forecasting models evaluated honestly against baselines, per product and market.
4. A deployed web app: price explorer and forecasts with uncertainty and plain-language explanations.
5. README (English with French summary), docs/DECISIONS.md, final review.

## Web app scope (keep it focused)
- Home: one striking hero with current prices and one headline insight.
- Explorer: choose a product and a market, see history and seasonality.
- Forecast: next weeks or months with an uncertainty band and a clear caveat.
- Method and limits page: sources, how it works, what the model cannot do.
- No accounts. Prefer a static export of precomputed forecasts if it is enough.

## Design direction
Concept: data journalism meets the market. Editorial typography with large numbers, generous whitespace, one memorable scroll-driven visualization, motion that explains the data and never decorates.
- Palette: earthy and warm (laterite red-orange, maize yellow, deep green, ink) on an off-white or dark base. No default purple-blue gradients.
- Type: one expressive display typeface and one highly legible text typeface. Self-host and subset fonts.
- Signature moment: a scroll-driven line that draws the price history of the selected crop, then extends into a dashed forecast with an uncertainty band.
- Transitions: smooth, meaningful page and product transitions (GSAP, Flip). Smooth scrolling only if it does not hurt mobile performance or accessibility.
- References: the owner will add 3 reference sites here. Until then, follow this direction.

## Performance and accessibility
- Mobile-first. Test at 390x844 and 1440x900.
- Target: fast load on a throttled mobile connection, lean JavaScript, no heavy video, optimized images.
- Respect prefers-reduced-motion, AA contrast, keyboard navigation, text alternatives for charts.

## Definition of done per phase
- Phase 0: docs/DATA.md and docs/STATUS.md with a coverage table (product x market x period) and a go/no-go per product.
- Phase 1: clean dataset and exploratory report with figures.
- Phase 2: model comparison table, saved model, reproducible training script.
- Phase 3: app ready to deploy, desktop and mobile screenshots reviewed in docs/screenshots/.
- Phase 4: reviewer report, complete README, repository ready to publish.

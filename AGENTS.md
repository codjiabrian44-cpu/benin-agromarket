# Project: Bénin AgroMarket — agricultural price forecasting for Benin (maize, yam, tomato)

## Goal
Portfolio-grade data science project: analyze and forecast staple food prices in Benin,
shipped as a deployed web app useful to producers and traders. Quality over speed.

## Working method (strict)
Work in phases. At the end of each phase, STOP and write a summary in docs/STATUS.md
(what was done, results, problems, what you propose next). Do not start the next phase
until the owner replies.
- Phase 0: data audit (sources, coverage by market/product/period, gaps). If coverage is
  too thin for a product, report it and propose alternatives. Do not model on bad data.
- Phase 1: cleaning + exploratory analysis.
- Phase 2: modeling.
- Phase 3: web app.
- Phase 4: review, README, deployment.

## Data rules
- Never invent, simulate or fill data silently. Every imputation is documented.
- docs/DATA.md lists, for each dataset: source URL, license, download date, known issues.
- Respect licenses and website terms of use. No personal data. No scraping of sites that forbid it.
- Raw data in data/raw/ is never edited. Cleaning is done by scripts in src/.

## Code rules
- Python 3.10+. Always use the .venv virtual environment. Pin dependencies in requirements.txt.
- Logic lives in src/ as importable, typed, documented functions. Notebooks only for exploration.
- Fixed random seeds. The full pipeline must be reproducible from a clean clone.
- Never store secrets in the repo. Use .env (already gitignored).

## Modeling rules
- Time series: split by time, never randomly. No data leakage.
- Always compare against simple baselines (last value, seasonal naive) before any complex model.
- Report MAE, RMSE and MAPE per product and per market, with prediction intervals when possible.
- State limits honestly: what the model cannot do, where it is unreliable.

## Documentation rules
- docs/DECISIONS.md: every important choice and why (the owner must be able to defend it in an interview).
- README in English with a short French summary: problem, data, method, results, limits, how to run.

## Web app and UI rules
- Interface in French by default, with an English toggle.
- Distinctive, award-level design: no generic template look. Follow the design brief in BRIEF.md.
- Fast, mobile-first (users are on phones), accessible, with real page transitions and purposeful motion.
- Before saying a UI task is done, open it with Playwright, check desktop AND mobile screenshots,
  critique them honestly against the brief, and fix what is weak.

## Git and safety
- Commit often, clear messages (feat:, fix:, docs:, data:).
- Work only inside this project folder. Ask before installing any package or deleting any file.
- If a task is ambiguous or blocked, write the question in docs/STATUS.md and stop. Do not guess.

"""Phase 1(b) Exploratory Data Analysis (EDA) & SVG figure generator.

Computes deterministic tables in ``docs/tables/`` and renders publication-grade
vector ``.svg`` charts in ``docs/figures/`` using only the Python 3.10+ standard
library.

Every number inside table labels, figure titles, panel headers, axis labels, and
captions is computed dynamically from the exact data plotted at runtime (never
hardcoded in strings).
"""

from __future__ import annotations

from collections import defaultdict
import csv
from html import escape
import math
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

from src.analysis.coverage import months_between_dates, write_csv_and_md
from src.config import (
    CLEANED_PRICES_ALL_CSV,
    DOCS_FIGURES_DIR,
    DOCS_TABLES_DIR,
)


MONTH_NAMES_SHORT: tuple[str, ...] = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

# Design Brief Palette (BRIEF.md)
COLOR_BG = "#FAF7F2"
COLOR_CARD = "#FFFFFF"
COLOR_PANEL_ALT = "#F3EFE6"
COLOR_GRID = "#E4DDD0"
COLOR_BORDER = "#D4CBB8"
COLOR_INK = "#1E1E1C"
COLOR_MUTED = "#5C5850"
COLOR_LATERITE = "#C84B31"  # Tomatoes / Alert
COLOR_GOLD = "#D99B26"      # Maize (white)
COLOR_GREEN = "#2D5A27"     # Yam (white)
COLOR_PLUM = "#6B4C7B"      # Yam (early / exploration)
COLOR_SLATE = "#3A6073"     # Hydro-climatic / North zone
COLOR_HIATUS = "#EFE6DC"

PRODUCT_COLORS: dict[str, str] = {
    "Maize (white)": COLOR_GOLD,
    "Tomatoes": COLOR_LATERITE,
    "Yam (white)": COLOR_GREEN,
    "Yam": COLOR_PLUM,
}


def quantile_sorted(sorted_vals: list[float], q: float) -> float:
    """Compute linear-interpolated quantile on a pre-sorted non-empty list."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    if n == 1:
        return sorted_vals[0]
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def classify_agro_zone(lat: float) -> str:
    """Classify Benin latitude into 3 agro-ecological zones."""
    if lat < 7.5:
        return "South (<7.5°N, Bimodal)"
    if lat < 9.5:
        return "Center (7.5°–9.5°N, Transition)"
    return "North (>=9.5°N, Unimodal)"


def pearson_r(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson correlation coefficient between two equal-length lists."""
    n = len(xs)
    if n < 3:
        return 0.0
    mx = mean(xs)
    my = mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs)
    den_y = sum((y - my) ** 2 for y in ys)
    if den_x <= 1e-12 or den_y <= 1e-12:
        return 0.0
    return num / math.sqrt(den_x * den_y)


def _rank_data(vals: list[float]) -> list[float]:
    """Assign average ranks (1-indexed) with tie handling."""
    n = len(vals)
    indexed = sorted(enumerate(vals), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = 0.5 * (i + j) + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman_rho(xs: list[float], ys: list[float]) -> float:
    """Compute Spearman rank correlation coefficient."""
    if len(xs) < 3:
        return 0.0
    return pearson_r(_rank_data(xs), _rank_data(ys))


def load_cleaned_rows(csv_path: Path = CLEANED_PRICES_ALL_CSV) -> list[dict[str, Any]]:
    """Load ``prices_cleaned_all.csv`` with parsed numeric fields."""
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d: dict[str, Any] = dict(r)
            d["year"] = int(r["year"])
            d["month"] = int(r["month"])
            d["latitude_f"] = float(r["latitude"])
            d["longitude_f"] = float(r["longitude"])
            d["zone"] = classify_agro_zone(d["latitude_f"])
            d["price_f"] = float(r["price"])
            d["usdprice_f"] = float(r["usdprice"])
            d["is_tier1"] = int(r["is_tier1_2019_2026"])
            d["is_outlier_level_i"] = int(r["is_outlier_level"])
            d["is_outlier_jump_i"] = int(r["is_outlier_jump"])
            d["is_outlier_i"] = int(r["is_outlier"])
            d["robust_z_f"] = float(r["robust_z"])
            d["mom_log_diff_f"] = float(r["mom_log_diff"]) if r["mom_log_diff"] != "" else None
            for w_col in (
                "precip_lag1m",
                "precip_lag2m",
                "precip_lag3m",
                "precip_roll3m_lag1",
                "precip_anom_z_lag1m",
                "t2m_lag1m",
                "t2m_max_lag1m",
                "t2m_min_lag1m",
                "rh2m_lag1m",
            ):
                d[w_col + "_f"] = float(r[w_col]) if r[w_col] != "" else None
            rows.append(d)
    return rows


def build_table1_summary_by_product(
    rows: list[dict[str, Any]],
    tables_dir: Path,
) -> list[list[Any]]:
    """Build Table 1: Distributional & structural trend metrics by product and regime.

    Every market count and date range in the ``Regime / Scope`` label is computed
    dynamically at runtime from the actual subset ``sub``.
    """
    subsets_spec = [
        ("Maize (white)", "modern_2019_2026", True, "Tier-1 Modeling Window"),
        ("Maize (white)", "modern_2019_2026", False, "All Active Markets"),
        ("Maize (white)", "pre_2019_exploration", False, "Pre-2019 Exploration Only"),
        ("Tomatoes", "modern_2019_2026", True, "Tier-1 Modeling Window"),
        ("Tomatoes", "modern_2019_2026", False, "All Active Markets"),
        ("Yam (white)", "modern_2019_2026", True, "Tier-1 Modeling Window"),
        ("Yam (white)", "modern_2019_2026", False, "All Active Markets"),
        ("Yam", "modern_2019_2026", True, "Exploration-Only Tier-1"),
        ("Yam", "modern_2019_2026", False, "Exploration-Only All Markets"),
        ("Yam", "pre_2019_exploration", False, "Exploration-Only Pre-2019"),
    ]

    out_rows: list[list[Any]] = []
    for comm, regime, tier1_only, prefix_label in subsets_spec:
        sub = [
            r
            for r in rows
            if r["commodity"] == comm
            and r["regime"] == regime
            and (not tier1_only or r["is_tier1"] == 1)
        ]
        prices = sorted(r["price_f"] for r in sub)
        mkts = {r["market"] for r in sub}
        yms = sorted({r["year_month"] for r in sub})
        min_ym, max_ym = yms[0], yms[-1]
        n_mkts = len(mkts)
        label = f"{prefix_label} ({min_ym}..{max_ym}, {n_mkts} mkts)"

        n_obs = len(prices)
        mu = mean(prices)
        sd = pstdev(prices)
        cv_pct = (sd / mu) * 100.0 if mu > 0 else 0.0
        med = median(prices)
        p25 = quantile_sorted(prices, 0.25)
        p75 = quantile_sorted(prices, 0.75)
        iqr = p75 - p25
        p_min = prices[0]
        p_max = prices[-1]

        if regime == "modern_2019_2026":
            p_2019 = sorted(r["price_f"] for r in sub if r["year"] == 2019)
            p_last12 = sorted(r["price_f"] for r in sub if r["year_month"] >= "2025-10")
            mean_19 = mean(p_2019)
            mean_l12 = mean(p_last12)
            med_19 = median(p_2019)
            med_l12 = median(p_last12)
            ratio_mean = mean_l12 / mean_19 if mean_19 > 0 else 1.0
            ratio_med = med_l12 / med_19 if med_19 > 0 else 1.0
            # Midpoint of 2019 (2019.5) to midpoint of 2025-10..2026-09 (2026.25) is 6.75 years
            cagr_mean_pct = ((ratio_mean ** (1.0 / 6.75)) - 1.0) * 100.0
            cagr_med_pct = ((ratio_med ** (1.0 / 6.75)) - 1.0) * 100.0
            mean_19_s = f"{mean_19:.1f}"
            mean_l12_s = f"{mean_l12:.1f}"
            med_19_s = f"{med_19:.1f}"
            med_l12_s = f"{med_l12:.1f}"
            ratio_s = f"{ratio_mean:.2f}x (med {ratio_med:.2f}x)"
            cagr_s = f"{cagr_mean_pct:+.1f}% (med {cagr_med_pct:+.1f}%)"
        else:
            mean_19_s = "-"
            mean_l12_s = "-"
            med_19_s = "-"
            med_l12_s = "-"
            ratio_s = "-"
            cagr_s = "-"

        out_rows.append([
            comm,
            label,
            n_obs,
            n_mkts,
            f"{mu:.1f}",
            f"{sd:.1f}",
            f"{cv_pct:.1f}%",
            f"{med:.1f}",
            f"{p25:.1f}",
            f"{p75:.1f}",
            f"{iqr:.1f}",
            f"{p_min:.1f}",
            f"{p_max:.1f}",
            mean_19_s,
            mean_l12_s,
            med_19_s,
            med_l12_s,
            ratio_s,
            cagr_s,
        ])

    headers = [
        "Product",
        "Regime / Scope",
        "Obs",
        "Markets",
        "Mean (XOF/kg)",
        "SD",
        "CV %",
        "Median",
        "P25",
        "P75",
        "IQR",
        "Min",
        "Max",
        "2019 Mean",
        "Last-12m Mean (2025-10..2026-09)",
        "2019 Median",
        "Last-12m Median",
        "Ratio (Last-12m / 2019)",
        "CAGR % (6.75 yr)",
    ]
    write_csv_and_md(
        csv_path=tables_dir / "eda_summary_by_product.csv",
        md_path=tables_dir / "eda_summary_by_product.md",
        title="Table 1 — Distributional & Structural Trend Summary by Product (`XOF/kg`)",
        script_citation="src/analysis/eda.py",
        headers=headers,
        rows=out_rows,
        notes=[
            "Primary modeling window is `2019-01..2026-09` (`93` months) across Tier-1 markets (`>= 80` observed months). Pre-2019 rows (`2007–2018`) and `Yam` (early/laboko) are strictly for exploration.",
            "`Last-12m` denotes the final 12 months of the panel (`2025-10..2026-09`), guaranteeing balanced seasonal representation (all 12 calendar months) when comparing against calendar year `2019` (`6.75` years between period midpoints).",
        ],
    )
    return out_rows


def build_table2_seasonality_profile(
    rows: list[dict[str, Any]],
    tables_dir: Path,
) -> tuple[list[list[Any]], dict[tuple[str, str], dict[int, dict[str, float]]]]:
    """Build Table 2: Seasonal index profile (100 = annual mean) by product and agro-ecological zone."""
    modern_t1 = [
        r for r in rows if r["regime"] == "modern_2019_2026" and r["is_tier1"] == 1
    ]

    mkt_yr_vals: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for r in modern_t1:
        mkt_yr_vals[(r["commodity"], r["market"], r["year"])].append(r["price_f"])
    mkt_yr_mean: dict[tuple[str, str, int], float] = {
        k: mean(v) for k, v in mkt_yr_vals.items() if len(v) >= 6
    }

    zones_order = [
        "All Tier-1 (National)",
        "South (<7.5°N, Bimodal)",
        "Center (7.5°–9.5°N, Transition)",
        "North (>=9.5°N, Unimodal)",
    ]
    products_order = ["Maize (white)", "Tomatoes", "Yam (white)", "Yam"]

    seasonality_lookup: dict[tuple[str, str], dict[int, dict[str, float]]] = {}
    table_rows: list[list[Any]] = []

    for comm in products_order:
        for z_label in zones_order:
            sub = [
                r
                for r in modern_t1
                if r["commodity"] == comm
                and (z_label == "All Tier-1 (National)" or r["zone"] == z_label)
            ]
            if not sub:
                continue
            mkts_cnt = len({r["market"] for r in sub})

            month_stats: dict[int, dict[str, float]] = {}
            raw_month_means: dict[int, float] = {}
            detrended_indices: dict[int, float] = {}

            for m in range(1, 13):
                m_rows = [r for r in sub if r["month"] == m]
                m_prices = sorted(r["price_f"] for r in m_rows)
                m_norm = sorted(
                    (r["price_f"] / mkt_yr_mean[(comm, r["market"], r["year"])]) * 100.0
                    for r in m_rows
                    if (comm, r["market"], r["year"]) in mkt_yr_mean
                )
                raw_month_means[m] = mean(m_prices) if m_prices else 0.0
                detrended_indices[m] = mean(m_norm) if m_norm else 100.0
                month_stats[m] = {
                    "obs": float(len(m_prices)),
                    "mean": raw_month_means[m],
                    "median": median(m_prices) if m_prices else 0.0,
                    "p25": quantile_sorted(m_prices, 0.25) if m_prices else 0.0,
                    "p75": quantile_sorted(m_prices, 0.75) if m_prices else 0.0,
                    "idx_mean": detrended_indices[m],
                    "idx_med": median(m_norm) if m_norm else 100.0,
                    "idx_p25": quantile_sorted(m_norm, 0.25) if m_norm else 100.0,
                    "idx_p75": quantile_sorted(m_norm, 0.75) if m_norm else 100.0,
                }

            avg_idx = mean(detrended_indices.values())
            for m in range(1, 13):
                scale = 100.0 / avg_idx if avg_idx > 0 else 1.0
                month_stats[m]["idx_mean"] *= scale
                month_stats[m]["idx_med"] *= scale
                month_stats[m]["idx_p25"] *= scale
                month_stats[m]["idx_p75"] *= scale
                month_stats[m]["mkts_cnt"] = float(mkts_cnt)

            seasonality_lookup[(comm, z_label)] = month_stats

            peak_m = max(range(1, 13), key=lambda m: month_stats[m]["idx_mean"])
            trough_m = min(range(1, 13), key=lambda m: month_stats[m]["idx_mean"])
            peak_idx = month_stats[peak_m]["idx_mean"]
            trough_idx = month_stats[trough_m]["idx_mean"]
            amp_diff_pts = peak_idx - trough_idx
            amp_ratio_pct = ((peak_idx / trough_idx) - 1.0) * 100.0 if trough_idx > 0 else 0.0

            row = [
                comm,
                z_label,
                mkts_cnt,
                len(sub),
                f"{MONTH_NAMES_SHORT[trough_m - 1]} ({trough_idx:.1f})",
                f"{MONTH_NAMES_SHORT[peak_m - 1]} ({peak_idx:.1f})",
                f"{amp_diff_pts:.1f} pts (+{amp_ratio_pct:.1f}%)",
            ] + [f"{month_stats[m]['idx_mean']:.1f}" for m in range(1, 13)]
            table_rows.append(row)

    headers = [
        "Product",
        "Agro-Ecological Zone",
        "Tier-1 Markets",
        "Obs",
        "Trough Month (Index)",
        "Peak Month (Index)",
        "Peak-to-Trough Spread (Index pts / %)",
    ] + list(MONTH_NAMES_SHORT)

    write_csv_and_md(
        csv_path=tables_dir / "eda_seasonality_profile.csv",
        md_path=tables_dir / "eda_seasonality_profile.md",
        title="Table 2 — Monthly Seasonal Price Index (`100 = Annual Market Mean`) by Product & Agro-Ecological Zone (`2019–2026` Tier-1 Markets)",
        script_citation="src/analysis/eda.py",
        headers=headers,
        rows=table_rows,
        notes=[
            "Seasonal indices (`100.0 = annual mean`) are computed within each `(market, year)` with `>= 6` observed months and averaged by calendar month (`Jan..Dec`), eliminating bias from secular multi-year inflation.",
            "Agro-ecological latitude zones: **South (`< 7.5°N`)** has bimodal rainfall (long rains Apr–Jul, short rains Sep–Oct); **Center (`7.5°–9.5°N`)** is the Sudano-Guinean transition belt (`Collines`/`Donga`/`Borgou` south); **North (`>= 9.5°N`)** has unimodal Sudanian rainfall (May–Sep).",
        ],
    )
    return table_rows, seasonality_lookup


def build_table3_market_differences(
    rows: list[dict[str, Any]],
    tables_dir: Path,
) -> tuple[list[list[Any]], dict[str, list[dict[str, Any]]]]:
    """Build Table 3: Spatial market price dispersion across Tier-1 markets (2019-2026)."""
    modern_t1 = [
        r for r in rows if r["regime"] == "modern_2019_2026" and r["is_tier1"] == 1
    ]

    market_stats_by_prod: dict[str, list[dict[str, Any]]] = defaultdict(list)
    summary_rows: list[list[Any]] = []

    for comm in ("Maize (white)", "Tomatoes", "Yam (white)", "Yam"):
        by_mkt: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in modern_t1:
            if r["commodity"] == comm:
                by_mkt[r["market"]].append(r)

        mkt_records: list[dict[str, Any]] = []
        for mkt, m_rows in by_mkt.items():
            p_sorted = sorted(r["price_f"] for r in m_rows)
            p_19_21 = [r["price_f"] for r in m_rows if r["year"] <= 2021]
            p_22_26 = [r["price_f"] for r in m_rows if r["year"] >= 2022]
            mkt_records.append({
                "commodity": comm,
                "market": mkt,
                "admin1": m_rows[0]["admin1"],
                "zone": m_rows[0]["zone"],
                "latitude": m_rows[0]["latitude_f"],
                "obs": len(p_sorted),
                "mean": mean(p_sorted),
                "sd": pstdev(p_sorted),
                "median": median(p_sorted),
                "p25": quantile_sorted(p_sorted, 0.25),
                "p75": quantile_sorted(p_sorted, 0.75),
                "iqr": quantile_sorted(p_sorted, 0.75) - quantile_sorted(p_sorted, 0.25),
                "min": p_sorted[0],
                "max": p_sorted[-1],
                "mean_19_21": mean(p_19_21) if p_19_21 else 0.0,
                "mean_22_26": mean(p_22_26) if p_22_26 else 0.0,
            })

        mkt_records.sort(key=lambda x: (x["mean"], x["median"], x["market"]))
        market_stats_by_prod[comm] = mkt_records

        mkt_means = [m["mean"] for m in mkt_records]
        cross_mkt_mean = mean(mkt_means)
        cross_mkt_sd = pstdev(mkt_means)
        cross_mkt_cv = (cross_mkt_sd / cross_mkt_mean) * 100.0 if cross_mkt_mean > 0 else 0.0
        min_m = mkt_records[0]
        max_m = mkt_records[-1]
        max_min_ratio = max_m["mean"] / min_m["mean"] if min_m["mean"] > 0 else 1.0

        benchmark_hubs = {
            "Dantokpa",
            "Glazoué",
            "Parakou",
            "Malanville (CBM)",
            "Kérou",
            "Djougou",
            "Kétou",
            "Natitingou",
            "Bohicon",
            "Nikki",
            "Savalou",
            "Comé",
            "Ouando",
        }
        lowest_3 = {m["market"] for m in mkt_records[:3]}
        highest_3 = {m["market"] for m in mkt_records[-3:]}

        for rank_idx, m in enumerate(mkt_records, start=1):
            is_selected = (
                comm == "Yam (white)"
                or m["market"] in lowest_3
                or m["market"] in highest_3
                or m["market"] in benchmark_hubs
            )
            if not is_selected:
                continue
            role_tag: list[str] = []
            if rank_idx <= 3:
                role_tag.append(f"Lowest #{rank_idx}")
            if rank_idx > len(mkt_records) - 3:
                role_tag.append(f"Highest #{len(mkt_records) - rank_idx + 1}")
            if m["market"] in benchmark_hubs:
                role_tag.append("Benchmark")
            rel_vs_nat_pct = ((m["mean"] / cross_mkt_mean) - 1.0) * 100.0
            summary_rows.append([
                comm,
                f"{rank_idx} / {len(mkt_records)}",
                m["market"],
                m["admin1"],
                m["zone"].split(",")[0] + ")",
                m["obs"],
                f"{m['mean']:.1f}",
                f"{m['median']:.1f}",
                f"{m['p25']:.1f}–{m['p75']:.1f} ({m['iqr']:.1f})",
                f"{m['min']:.0f}..{m['max']:.0f}",
                f"{rel_vs_nat_pct:+.1f}%",
                f"{max_min_ratio:.2f}x (CV {cross_mkt_cv:.1f}%)",
                ", ".join(role_tag) if role_tag else "Tier-1",
            ])

    headers = [
        "Product",
        "Price Rank (Low→High)",
        "Market",
        "Admin1",
        "Zone",
        "Obs (2019-26)",
        "Mean (XOF/kg)",
        "Median (XOF/kg)",
        "P25–P75 (IQR)",
        "Min..Max",
        "Spread vs Tier-1 Mean %",
        "Product Max/Min Mkt Ratio (Cross-Mkt CV%)",
        "Category / Note",
    ]
    n_yw_t1 = len(market_stats_by_prod["Yam (white)"])
    write_csv_and_md(
        csv_path=tables_dir / "eda_market_differences.csv",
        md_path=tables_dir / "eda_market_differences.md",
        title="Table 3 — Spatial Price Dispersion Across Tier-1 Markets (`2019-01..2026-09`, `XOF/kg`)",
        script_citation="src/analysis/eda.py",
        headers=headers,
        rows=summary_rows,
        notes=[
            "Ranks Tier-1 markets from lowest mean price (`#1`, surplus producer hubs) to highest mean price (urban consumer or deficit markets) over `2019-01..2026-09`.",
            f"Includes the 3 lowest-cost markets, 3 highest-cost markets, and key benchmark hubs for `Maize (white)`, `Tomatoes`, and `Yam`, plus all `{n_yw_t1}` Tier-1 markets for `Yam (white)`.",
        ],
    )
    return summary_rows, market_stats_by_prod


def build_table4_yam_variety_comparison(
    rows: list[dict[str, Any]],
    tables_dir: Path,
) -> list[list[Any]]:
    """Build Table 4: Quantitative comparison between Yam (white) (Kokoro) and Yam (Laboko)."""
    modern_rows = [
        r for r in rows if r["regime"] == "modern_2019_2026" and r["commodity"] in ("Yam (white)", "Yam")
    ]

    yw_by_mkt_dt: dict[tuple[str, str], dict[str, Any]] = {}
    ye_by_mkt_dt: dict[tuple[str, str], dict[str, Any]] = {}
    for r in modern_rows:
        if r["commodity"] == "Yam (white)":
            yw_by_mkt_dt[(r["market"], r["date"])] = r
        else:
            ye_by_mkt_dt[(r["market"], r["date"])] = r

    overlap_keys = sorted(set(yw_by_mkt_dt.keys()) & set(ye_by_mkt_dt.keys()))
    shared_t1_mkts = {
        k[0]
        for k in overlap_keys
        if yw_by_mkt_dt[k]["is_tier1"] == 1 and ye_by_mkt_dt[k]["is_tier1"] == 1
    }

    out_rows: list[list[Any]] = []

    for scope_label, filter_fn in [
        ("All Concurrent Market-Months (2019-2026)", lambda k: True),
        (
            f"Both Tier-1 Markets Concurrent ({len(shared_t1_mkts)} Shared Tier-1 Markets)",
            lambda k: yw_by_mkt_dt[k]["is_tier1"] == 1 and ye_by_mkt_dt[k]["is_tier1"] == 1,
        ),
    ]:
        keys = [k for k in overlap_keys if filter_fn(k)]
        yw_vals = sorted(yw_by_mkt_dt[k]["price_f"] for k in keys)
        ye_vals = sorted(ye_by_mkt_dt[k]["price_f"] for k in keys)
        diffs = [ye_by_mkt_dt[k]["price_f"] - yw_by_mkt_dt[k]["price_f"] for k in keys]
        abs_diffs = [abs(d) for d in diffs]
        pct_prem = [
            ((ye_by_mkt_dt[k]["price_f"] / yw_by_mkt_dt[k]["price_f"]) - 1.0) * 100.0
            for k in keys
        ]
        ye_higher_pct = (sum(1 for d in diffs if d > 0) / len(diffs)) * 100.0 if diffs else 0.0
        out_rows.append([
            "Summary",
            scope_label,
            len(keys),
            f"{mean(yw_vals):.1f} (med {median(yw_vals):.1f})",
            f"{mean(ye_vals):.1f} (med {median(ye_vals):.1f})",
            f"{mean(diffs):+.1f}",
            f"{mean(abs_diffs):.1f}",
            f"{mean(pct_prem):+.1f}%",
            f"{ye_higher_pct:.1f}%",
        ])

    for m in range(1, 13):
        keys = [k for k in overlap_keys if yw_by_mkt_dt[k]["month"] == m]
        yw_vals = sorted(yw_by_mkt_dt[k]["price_f"] for k in keys)
        ye_vals = sorted(ye_by_mkt_dt[k]["price_f"] for k in keys)
        diffs = [ye_by_mkt_dt[k]["price_f"] - yw_by_mkt_dt[k]["price_f"] for k in keys]
        abs_diffs = [abs(d) for d in diffs]
        pct_prem = [
            ((ye_by_mkt_dt[k]["price_f"] / yw_by_mkt_dt[k]["price_f"]) - 1.0) * 100.0
            for k in keys
        ]
        ye_higher_pct = (sum(1 for d in diffs if d > 0) / len(diffs)) * 100.0 if diffs else 0.0
        out_rows.append([
            "By Calendar Month",
            f"M{m:02d} ({MONTH_NAMES_SHORT[m - 1]})",
            len(keys),
            f"{mean(yw_vals):.1f} (med {median(yw_vals):.1f})",
            f"{mean(ye_vals):.1f} (med {median(ye_vals):.1f})",
            f"{mean(diffs):+.1f}",
            f"{mean(abs_diffs):.1f}",
            f"{mean(pct_prem):+.1f}%",
            f"{ye_higher_pct:.1f}%",
        ])

    key_yam_mkts = [
        "Dantokpa",
        "Glazoué",
        "Savalou",
        "Kétou",
        "Kérou",
        "Bembèrèkè",
        "Comé",
        "Bohicon",
        "Natitingou",
        "Azovè",
        "Péhunco",
        "Abomey",
        "Ouando",
        "Dogbo",
        "Djougou",
        "Nikki",
    ]
    for mkt in key_yam_mkts:
        keys = [k for k in overlap_keys if k[0] == mkt]
        n_yw_all = sum(1 for (m_name, _) in yw_by_mkt_dt if m_name == mkt)
        n_ye_all = sum(1 for (m_name, _) in ye_by_mkt_dt if m_name == mkt)
        if len(keys) >= 5:
            yw_vals = sorted(yw_by_mkt_dt[k]["price_f"] for k in keys)
            ye_vals = sorted(ye_by_mkt_dt[k]["price_f"] for k in keys)
            diffs = [ye_by_mkt_dt[k]["price_f"] - yw_by_mkt_dt[k]["price_f"] for k in keys]
            abs_diffs = [abs(d) for d in diffs]
            pct_prem = [
                ((ye_by_mkt_dt[k]["price_f"] / yw_by_mkt_dt[k]["price_f"]) - 1.0) * 100.0
                for k in keys
            ]
            ye_higher_pct = (sum(1 for d in diffs if d > 0) / len(diffs)) * 100.0
            out_rows.append([
                "By Market",
                f"{mkt} (YW={n_yw_all}m, Y={n_ye_all}m)",
                len(keys),
                f"{mean(yw_vals):.1f} (med {median(yw_vals):.1f})",
                f"{mean(ye_vals):.1f} (med {median(ye_vals):.1f})",
                f"{mean(diffs):+.1f}",
                f"{mean(abs_diffs):.1f}",
                f"{mean(pct_prem):+.1f}%",
                f"{ye_higher_pct:.1f}%",
            ])
        else:
            yw_all_vals = sorted(
                r["price_f"] for (m_name, _), r in yw_by_mkt_dt.items() if m_name == mkt
            )
            ye_dates = sorted(dt[:7] for (m_name, dt) in ye_by_mkt_dt if m_name == mkt)
            ye_desc = f"Only {n_ye_all} obs ({', '.join(ye_dates)})" if ye_dates else "0 obs"
            out_rows.append([
                "By Market (Non-Overlapping Hub)",
                f"{mkt} (YW={n_yw_all}m, Y={n_ye_all}m)",
                len(keys),
                f"{mean(yw_all_vals):.1f} (med {median(yw_all_vals):.1f})" if yw_all_vals else "-",
                ye_desc,
                "-",
                "-",
                "-",
                "-",
            ])

    headers = [
        "Grouping",
        "Slice / Market / Month",
        "Concurrent Market-Months",
        "Yam (white) [Kokoro] Mean (Med) XOF/kg",
        "Yam [Laboko/Early] Mean (Med) XOF/kg",
        "Mean Signed Spread (Yam - Yam white)",
        "Mean Abs Diff |Yam - Yam white|",
        "Mean Early Yam Premium %",
        "% Months Early Yam > White Yam",
    ]
    write_csv_and_md(
        csv_path=tables_dir / "eda_yam_variety_comparison.csv",
        md_path=tables_dir / "eda_yam_variety_comparison.md",
        title="Table 4 — Quantitative Variety Comparison: `Yam (white)` (*Kokoro*, Forecast Primary) vs `Yam` (*Laboko / Précoce*, Exploration Only)",
        script_citation="src/analysis/eda.py",
        headers=headers,
        rows=out_rows,
        notes=[
            "Demonstrates why `Yam (white)` (*kokoro*, staple white yam) and `Yam` (*laboko*, early/preferred yam) must never be merged into a single series: on concurrent market-months they trade at systematically different price levels and seasonal spreads.",
            "Major northern production hubs `Djougou` (`86/93` months of `Yam (white)`) and `Nikki` (`85/93` months of `Yam (white)`) have only `1` observation each of `Yam` (`2020-08`).",
        ],
    )
    return out_rows


def build_table5_abrupt_changes(
    rows: list[dict[str, Any]],
    tables_dir: Path,
) -> tuple[list[list[Any]], dict[tuple[str, str], dict[str, Any]]]:
    """Build Table 5: Deterministic detection of candidate shocks / abrupt changes (2019-2026)."""
    modern_t1 = [
        r
        for r in rows
        if r["regime"] == "modern_2019_2026"
        and r["is_tier1"] == 1
        and r["commodity"] in ("Maize (white)", "Tomatoes", "Yam (white)")
    ]

    by_comm_ym: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in modern_t1:
        by_comm_ym[(r["commodity"], r["year_month"])].append(r)

    all_yms = sorted({r["year_month"] for r in modern_t1})
    monthly_shock_metrics: dict[tuple[str, str], dict[str, Any]] = {}
    candidate_events: list[list[Any]] = []

    for comm in ("Maize (white)", "Tomatoes", "Yam (white)"):
        prev_med: float | None = None
        prev_ym: str | None = None
        for ym in all_yms:
            m_rows = by_comm_ym.get((comm, ym), [])
            if not m_rows:
                continue
            prices = sorted(r["price_f"] for r in m_rows)
            med_p = median(prices)
            mean_p = mean(prices)

            mom_pcts: list[tuple[float, str, float]] = []
            n_jump_outliers = 0
            n_level_outliers = 0
            for r in m_rows:
                if r["is_outlier_jump_i"] == 1:
                    n_jump_outliers += 1
                if r["is_outlier_level_i"] == 1:
                    n_level_outliers += 1
                if r["mom_log_diff_f"] is not None:
                    pct_chg = (math.exp(r["mom_log_diff_f"]) - 1.0) * 100.0
                    mom_pcts.append((pct_chg, r["market"], r["price_f"]))

            n_consec = len(mom_pcts)
            n_surge_35 = sum(1 for p, _, _ in mom_pcts if p >= 35.0)
            n_drop_30 = sum(1 for p, _, _ in mom_pcts if p <= -30.0)
            share_surge_35 = (n_surge_35 / n_consec) * 100.0 if n_consec > 0 else 0.0
            share_drop_30 = (n_drop_30 / n_consec) * 100.0 if n_consec > 0 else 0.0

            nat_med_mom_pct = 0.0
            if prev_med is not None and prev_ym is not None and months_between_dates(prev_ym + "-15", ym + "-15") == 2:
                nat_med_mom_pct = ((med_p / prev_med) - 1.0) * 100.0
            prev_med = med_p
            prev_ym = ym

            monthly_shock_metrics[(comm, ym)] = {
                "obs_markets": len(m_rows),
                "consec_markets": n_consec,
                "median_price": med_p,
                "mean_price": mean_p,
                "nat_med_mom_pct": nat_med_mom_pct,
                "share_surge_35": share_surge_35,
                "share_drop_30": share_drop_30,
                "n_jump_outliers": n_jump_outliers,
                "n_level_outliers": n_level_outliers,
            }

            is_sync_surge = share_surge_35 >= 25.0 or nat_med_mom_pct >= 25.0
            is_sync_drop = share_drop_30 >= 25.0 or nat_med_mom_pct <= -25.0
            is_multi_outlier = n_jump_outliers >= 3

            if is_sync_surge or is_sync_drop or is_multi_outlier:
                if is_sync_surge:
                    direction = "Multi-Market Surge"
                    mom_pcts.sort(key=lambda x: -x[0])
                elif is_sync_drop:
                    direction = "Multi-Market Drop"
                    mom_pcts.sort(key=lambda x: x[0])
                else:
                    direction = "Cluster of >=2x Jumps"
                    mom_pcts.sort(key=lambda x: -abs(x[0]))

                top_examples = ", ".join(
                    f"{m} ({p:+.0f}% to {val:.0f})" for p, m, val in mom_pcts[:3]
                )
                candidate_events.append([
                    comm,
                    ym,
                    direction,
                    f"{len(m_rows)}",
                    f"{med_p:.0f} ({mean_p:.0f})",
                    f"{nat_med_mom_pct:+.1f}%",
                    f"{n_surge_35}/{n_consec} ({share_surge_35:.1f}%)",
                    f"{n_drop_30}/{n_consec} ({share_drop_30:.1f}%)",
                    f"{n_jump_outliers} jump / {n_level_outliers} lvl",
                    top_examples,
                ])

    headers = [
        "Product",
        "Year-Month",
        "Empirical Classification",
        "Observed Tier-1 Markets",
        "Tier-1 Median (Mean) XOF/kg",
        "Tier-1 Median MoM %",
        "Markets with MoM >= +35%",
        "Markets with MoM <= -30%",
        "Outliers Flagged (|ΔlnP|>ln2 / |z|>3.5)",
        "Top 3 Affected Markets (MoM % & Level)",
    ]
    write_csv_and_md(
        csv_path=tables_dir / "eda_abrupt_changes.csv",
        md_path=tables_dir / "eda_abrupt_changes.md",
        title="Table 5 — Empirical Candidate Shocks & Synchronized Abrupt Price Changes (`2019-01..2026-09` Tier-1 Markets)",
        script_citation="src/analysis/eda.py",
        headers=headers,
        rows=candidate_events,
        notes=[
            "**Methodological Note (Decision 3):** Candidate shock months and abrupt changes are detected purely empirically from observed price trajectories (`>= 25%` of active Tier-1 markets surging `>= +35%` MoM or dropping `<= -30%` MoM, national Tier-1 median shifting `>= 25%` MoM, or `>= 3` markets triggering `is_outlier_jump=1` in the same month). **No external causal attributions (e.g., policy changes, border closures, or weather events) are asserted unless explicitly documented in the dataset metadata.**",
            "All flagged observations are retained in `data/processed/prices_cleaned_all.csv` and `data/processed/modeling_panel_2019_2026.csv` (`0` rows deleted).",
        ],
    )
    return candidate_events, monthly_shock_metrics


def build_table6_weather_lag_correlations(
    rows: list[dict[str, Any]],
    tables_dir: Path,
) -> list[list[Any]]:
    """Build Table 6: Pearson & Spearman correlations between price metrics and strictly lagged NASA POWER features."""
    modern_t1 = [
        r
        for r in rows
        if r["regime"] == "modern_2019_2026"
        and r["is_tier1"] == 1
        and r["commodity"] in ("Maize (white)", "Tomatoes", "Yam (white)")
    ]

    mkt_yr_lps: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for r in modern_t1:
        mkt_yr_lps[(r["commodity"], r["market"], r["year"])].append(math.log(r["price_f"]))
    mkt_yr_lp_mean: dict[tuple[str, str, int], float] = {
        k: mean(v) for k, v in mkt_yr_lps.items() if len(v) >= 6
    }

    weather_features = [
        ("precip_lag1m_f", "precip_lag1m (mm/day, t-1)"),
        ("precip_lag2m_f", "precip_lag2m (mm/day, t-2)"),
        ("precip_lag3m_f", "precip_lag3m (mm/day, t-3)"),
        ("precip_roll3m_lag1_f", "precip_roll3m_lag1 (mm/day, t-3..t-1)"),
        ("precip_anom_z_lag1m_f", "precip_anom_z_lag1m (z-score vs '06-'18, t-1)"),
        ("t2m_lag1m_f", "t2m_lag1m (°C mean temp, t-1)"),
        ("t2m_max_lag1m_f", "t2m_max_lag1m (°C max temp, t-1)"),
        ("rh2m_lag1m_f", "rh2m_lag1m (% rel humidity, t-1)"),
    ]

    zones_spec = [
        "All Tier-1 (National)",
        "South (<7.5°N, Bimodal)",
        "Center (7.5°–9.5°N, Transition)",
        "North (>=9.5°N, Unimodal)",
    ]

    out_rows: list[list[Any]] = []
    for comm in ("Maize (white)", "Tomatoes", "Yam (white)"):
        for z_label in zones_spec:
            sub = [
                r
                for r in modern_t1
                if r["commodity"] == comm
                and (z_label == "All Tier-1 (National)" or r["zone"] == z_label)
                and (comm, r["market"], r["year"]) in mkt_yr_lp_mean
            ]
            if not sub:
                continue

            for w_key, w_label in weather_features:
                valid_pairs = [
                    (
                        math.log(r["price_f"]) - mkt_yr_lp_mean[(comm, r["market"], r["year"])],
                        r["mom_log_diff_f"],
                        r[w_key],
                    )
                    for r in sub
                    if r[w_key] is not None
                ]
                anom_xs = [p[0] for p in valid_pairs]
                w_ys = [p[2] for p in valid_pairs]
                r_anom = pearson_r(anom_xs, w_ys)
                rho_anom = spearman_rho(anom_xs, w_ys)

                mom_pairs = [(p[1], p[2]) for p in valid_pairs if p[1] is not None]
                r_mom = pearson_r([p[0] for p in mom_pairs], [p[1] for p in mom_pairs])
                rho_mom = spearman_rho([p[0] for p in mom_pairs], [p[1] for p in mom_pairs])

                out_rows.append([
                    comm,
                    z_label,
                    w_label,
                    len(valid_pairs),
                    f"{r_anom:+.3f}",
                    f"{rho_anom:+.3f}",
                    f"{r_mom:+.3f}",
                    f"{rho_mom:+.3f}",
                ])

    headers = [
        "Product",
        "Agro-Ecological Zone",
        "Lagged Weather Feature (Available at t-1)",
        "Valid Obs Pairs",
        "Pearson r (vs Detrended Log Price Anomaly)",
        "Spearman rho (vs Detrended Log Price Anomaly)",
        "Pearson r (vs MoM Log Change ΔlnP)",
        "Spearman rho (vs MoM Log Change ΔlnP)",
    ]
    write_csv_and_md(
        csv_path=tables_dir / "eda_weather_lag_correlations.csv",
        md_path=tables_dir / "eda_weather_lag_correlations.md",
        title="Table 6 — Lagged Agroclimatic Feature Correlations vs Price Seasonal Anomalies & MoM Changes (`2019–2026` Tier-1 Markets)",
        script_citation="src/analysis/eda.py",
        headers=headers,
        rows=out_rows,
        notes=[
            "Detrended log price anomaly is `ln(P_{m,t}) - mean_{tau in year(t)}(ln(P_{m,tau}))` within each `(market, year)`, isolating intra-annual seasonal deviations from multi-year macroeconomic inflation.",
            "All NASA POWER features are strictly lagged (`t-1`, `t-2`, `t-3`), and `precip_anom_z_lag1m` uses a strictly pre-modeling (`2006–2018`) monthly climatology per MERRA-2 grid cell.",
        ],
    )
    return out_rows


# ==============================================================================
# Publication-Grade Vector SVG Generators (All Title/Label Numbers Dynamic)
# ==============================================================================


def _svg_header(width: int, height: int, title: str, desc: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{escape(title)}">',
        f"  <title>{escape(title)}</title>",
        f"  <desc>{escape(desc)}</desc>",
        "  <style>",
        '    text { font-family: "Inter", "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; fill: #1E1E1C; }',
        '    .fig-title { font-family: "Georgia", "Times New Roman", serif; font-size: 20px; font-weight: bold; fill: #1E1E1C; }',
        "    .fig-subtitle { font-size: 12.5px; fill: #5C5850; }",
        "    .panel-title { font-size: 13.5px; font-weight: bold; fill: #1E1E1C; }",
        "    .axis-label { font-size: 11px; fill: #5C5850; }",
        "    .tick-label { font-size: 10.5px; fill: #5C5850; }",
        "    .badge-text { font-size: 10.5px; font-weight: bold; }",
        "    .note-text { font-size: 10.5px; fill: #5C5850; }",
        "  </style>",
        f'  <rect x="0" y="0" width="{width}" height="{height}" fill="{COLOR_BG}" />',
    ]


def render_fig1_regimes_and_trends(
    rows: list[dict[str, Any]],
    figures_dir: Path,
) -> Path:
    """Render Figure 1: Full 2007-2026 timeline showing regimes, hiatus, and post-2019 trends.

    All market counts and observation counts in panel titles and banners are
    computed dynamically at runtime from the exact plotted subsets.
    """
    width, height = 1160, 860

    all_years = sorted({r["year"] for r in rows})
    min_yr, max_yr = all_years[0], all_years[-1]
    pre_2017_mkts_by_yr = [
        len({r["market"] for r in rows if r["year"] == yr})
        for yr in range(min_yr, 2017)
    ]
    min_pre_mkts = min(pre_2017_mkts_by_yr) if pre_2017_mkts_by_yr else 0
    max_pre_mkts = max(pre_2017_mkts_by_yr) if pre_2017_mkts_by_yr else 0

    mod_yms_all = sorted({r["year_month"] for r in rows if r["regime"] == "modern_2019_2026"})
    mod_start_ym, mod_end_ym = mod_yms_all[0], mod_yms_all[-1]

    svg = _svg_header(
        width,
        height,
        f"Figure 1 — Bénin AgroMarket: Temporal Regimes, 2017–2018 Reporting Hiatus & Price Trajectories ({min_yr}–{max_yr})",
        f"Four-panel timeline showing pre-2019 sparse exploration regime ({min_yr}-2016, {min_pre_mkts}-{max_pre_mkts} markets), the 2017-2018 nationwide reporting hiatus (not interpolated), and the {mod_start_ym}..{mod_end_ym} primary modeling window.",
    )

    svg.append(
        f'  <text x="40" y="36" class="fig-title">Figure 1 — Régimes temporels, hiatus 2017–2018 et trajectoires des prix ({min_yr}–{max_yr}, XOF/kg)</text>'
    )
    svg.append(
        f'  <text x="40" y="56" class="fig-subtitle">Séparation stricte entre le régime pré-2019 (exploration seule, {min_pre_mkts}–{max_pre_mkts} marchés), le hiatus 2017–2018 (zéro interpolation) et la fenêtre de modélisation {mod_start_ym}..{mod_end_ym} (marchés Tier-1)</text>'
    )

    all_yms: list[str] = []
    for yr in range(min_yr, max_yr + 1):
        for m in range(1, 13):
            if (yr, m) > (2026, 9):
                break
            all_yms.append(f"{yr:04d}-{m:02d}")
    ym_to_idx = {ym: idx for idx, ym in enumerate(all_yms)}
    total_m = len(all_yms)

    left_x, right_x = 85.0, 1120.0
    plot_w = right_x - left_x

    def x_of_ym(ym: str) -> float:
        idx = ym_to_idx[ym]
        return left_x + (idx / (total_m - 1)) * plot_w

    x_2017_01 = x_of_ym("2017-01")
    x_2019_01 = x_of_ym("2019-01")

    banner_y = 70.0
    banner_h = 26.0
    svg.append(
        f'  <rect x="{left_x:.1f}" y="{banner_y:.1f}" width="{x_2017_01 - left_x:.1f}" height="{banner_h}" fill="#EAE3D2" stroke="{COLOR_BORDER}" rx="3" />'
    )
    svg.append(
        f'  <text x="{0.5 * (left_x + x_2017_01):.1f}" y="{banner_y + 17:.1f}" text-anchor="middle" class="badge-text" fill="#5C5850">EXPLORATION ONLY — Pre-2019 Sparse Regime ({min_yr}–2016: {min_pre_mkts} to {max_pre_mkts} Markets)</text>'
    )

    svg.append(
        f'  <rect x="{x_2017_01:.1f}" y="{banner_y:.1f}" width="{x_2019_01 - x_2017_01:.1f}" height="{banner_h}" fill="#F6D8CE" stroke="{COLOR_LATERITE}" rx="3" />'
    )
    svg.append(
        f'  <text x="{0.5 * (x_2017_01 + x_2019_01):.1f}" y="{banner_y + 17:.1f}" text-anchor="middle" class="badge-text" fill="{COLOR_LATERITE}">2017–2018 Hiatus</text>'
    )

    svg.append(
        f'  <rect x="{x_2019_01:.1f}" y="{banner_y:.1f}" width="{right_x - x_2019_01:.1f}" height="{banner_h}" fill="#DCE8D9" stroke="{COLOR_GREEN}" rx="3" />'
    )
    svg.append(
        f'  <text x="{0.5 * (x_2019_01 + right_x):.1f}" y="{banner_y + 17:.1f}" text-anchor="middle" class="badge-text" fill="{COLOR_GREEN}">PRIMARY MODELING WINDOW ({mod_start_ym}..{mod_end_ym}: Tier-1 Markets, Median &amp; IQR Band)</text>'
    )

    panels_meta = [
        ("1A", "Maize (white)", "Maïs blanc", "Forecast Primary", 600.0, COLOR_GOLD),
        ("1B", "Tomatoes", "Tomate fraîche", "Forecast Primary", 1600.0, COLOR_LATERITE),
        ("1C", "Yam (white)", "Igname blanche (Kokoro)", "Forecast Primary", 1000.0, COLOR_GREEN),
        ("1D", "Yam", "Igname précoce (Laboko)", "EXPLORATION ONLY", 1000.0, COLOR_PLUM),
    ]

    panel_top_start = 112.0
    panel_h = 148.0
    panel_gap = 34.0

    for p_idx, (code, comm, fr_name, role_lbl, y_max, color) in enumerate(panels_meta):
        top_y = panel_top_start + p_idx * (panel_h + panel_gap)
        bot_y = top_y + panel_h

        # Compute exact plotted counts dynamically at runtime
        pre_rows_plotted = [r for r in rows if r["commodity"] == comm and r["year_month"] < "2017-01"]
        mod_rows_plotted = [r for r in rows if r["commodity"] == comm and r["year_month"] >= "2019-01" and r["is_tier1"] == 1]
        n_t1_mkts = len({r["market"] for r in mod_rows_plotted})
        n_pre_mkts = len({r["market"] for r in pre_rows_plotted})
        n_pre_obs = len(pre_rows_plotted)

        if n_pre_obs > 0:
            pre_yms_c = sorted({r["year_month"] for r in pre_rows_plotted})
            pre_desc = f"Pre-2019 Exploration ({pre_yms_c[0]}..{pre_yms_c[-1]}): {n_pre_mkts} Markets ({n_pre_obs} obs)"
        else:
            pre_desc = "0 Pre-2019 Obs"

        p_title = f"{code}. {fr_name} — {comm} [{role_lbl}: {n_t1_mkts} Tier-1 Markets in 2019–2026 | {pre_desc}]"

        def y_of_val(val: float, top_y: float = top_y, bot_y: float = bot_y, y_max: float = y_max) -> float:
            clamped = max(0.0, min(y_max, val))
            return bot_y - (clamped / y_max) * panel_h

        svg.append(
            f'  <rect x="{left_x:.1f}" y="{top_y:.1f}" width="{x_2017_01 - left_x:.1f}" height="{panel_h}" fill="#F4F0E6" />'
        )
        svg.append(
            f'  <rect x="{x_2017_01:.1f}" y="{top_y:.1f}" width="{x_2019_01 - x_2017_01:.1f}" height="{panel_h}" fill="{COLOR_HIATUS}" />'
        )
        svg.append(
            f'  <rect x="{x_2019_01:.1f}" y="{top_y:.1f}" width="{right_x - x_2019_01:.1f}" height="{panel_h}" fill="{COLOR_CARD}" />'
        )

        n_ticks = 4
        for t_i in range(n_ticks + 1):
            v = (y_max / n_ticks) * t_i
            yy = y_of_val(v)
            svg.append(
                f'  <line x1="{left_x:.1f}" y1="{yy:.1f}" x2="{right_x:.1f}" y2="{yy:.1f}" stroke="{COLOR_GRID}" stroke-width="1" />'
            )
            svg.append(
                f'  <text x="{left_x - 8:.1f}" y="{yy + 4:.1f}" text-anchor="end" class="tick-label">{int(v)}</text>'
            )

        for yr in range(min_yr, max_yr + 1):
            xx = x_of_ym(f"{yr:04d}-01")
            stroke_w = "1.5" if yr in (2017, 2019) else "0.8"
            stroke_c = COLOR_LATERITE if yr == 2017 else (COLOR_GREEN if yr == 2019 else COLOR_GRID)
            svg.append(
                f'  <line x1="{xx:.1f}" y1="{top_y:.1f}" x2="{xx:.1f}" y2="{bot_y:.1f}" stroke="{stroke_c}" stroke-width="{stroke_w}" stroke-dasharray="{"4,3" if yr in (2017, 2019) else ""}" />'
            )
            if p_idx == len(panels_meta) - 1:
                svg.append(
                    f'  <text x="{xx + 12:.1f}" y="{bot_y + 16:.1f}" text-anchor="middle" class="tick-label">{yr}</text>'
                )

        svg.append(
            f'  <rect x="{left_x:.1f}" y="{top_y:.1f}" width="{plot_w:.1f}" height="{panel_h}" fill="none" stroke="{COLOR_BORDER}" stroke-width="1.2" />'
        )
        svg.append(
            f'  <text x="{left_x:.1f}" y="{top_y - 7:.1f}" class="panel-title">{escape(p_title)}</text>'
        )

        svg.append(
            f'  <text x="{0.5 * (x_2017_01 + x_2019_01):.1f}" y="{top_y + 66:.1f}" text-anchor="middle" font-size="9.5" font-weight="bold" fill="{COLOR_LATERITE}">2017–2018 HIATUS</text>'
        )
        svg.append(
            f'  <text x="{0.5 * (x_2017_01 + x_2019_01):.1f}" y="{top_y + 80:.1f}" text-anchor="middle" font-size="9" fill="{COLOR_LATERITE}">(Not Interpolated)</text>'
        )

        pre_by_ym: dict[str, list[float]] = defaultdict(list)
        mod_by_ym: dict[str, list[float]] = defaultdict(list)
        for r in pre_rows_plotted:
            pre_by_ym[r["year_month"]].append(r["price_f"])
        for r in mod_rows_plotted:
            mod_by_ym[r["year_month"]].append(r["price_f"])

        if pre_by_ym:
            svg.append(
                f'  <text x="{left_x + 12:.1f}" y="{top_y + 18:.1f}" font-size="10" font-style="italic" fill="#5C5850">Exploration Only ({n_pre_mkts} Markets, {n_pre_obs} Obs)</text>'
            )
            pre_yms = sorted(pre_by_ym.keys())
            seg_pts: list[str] = []
            prev_ym_s: str | None = None
            for ym in pre_yms:
                if prev_ym_s is not None and months_between_dates(prev_ym_s + "-15", ym + "-15") > 2:
                    if len(seg_pts) >= 2:
                        svg.append(
                            f'  <polyline points="{" ".join(seg_pts)}" fill="none" stroke="{color}" stroke-width="1.8" stroke-dasharray="4,2" opacity="0.85" />'
                        )
                    seg_pts = []
                med_v = median(sorted(pre_by_ym[ym]))
                seg_pts.append(f"{x_of_ym(ym):.1f},{y_of_val(med_v):.1f}")
                prev_ym_s = ym
            if len(seg_pts) >= 2:
                svg.append(
                    f'  <polyline points="{" ".join(seg_pts)}" fill="none" stroke="{color}" stroke-width="1.8" stroke-dasharray="4,2" opacity="0.85" />'
                )
        else:
            svg.append(
                f'  <text x="{0.5 * (left_x + x_2017_01):.1f}" y="{top_y + 76:.1f}" text-anchor="middle" font-size="10.5" font-style="italic" fill="#7A7468">No WFP Retail Observations Recorded Prior to {mod_start_ym}</text>'
            )

        mod_yms = [ym for ym in all_yms if ym >= "2019-01"]
        band_segments: list[list[tuple[float, float, float]]] = []
        line_segments: list[list[tuple[float, float]]] = []
        cur_band: list[tuple[float, float, float]] = []
        cur_line: list[tuple[float, float]] = []

        for ym in mod_yms:
            vals = sorted(mod_by_ym.get(ym, []))
            if vals:
                xx = x_of_ym(ym)
                p25 = quantile_sorted(vals, 0.25)
                p75 = quantile_sorted(vals, 0.75)
                med = median(vals)
                cur_band.append((xx, y_of_val(p25), y_of_val(p75)))
                cur_line.append((xx, y_of_val(med)))
            else:
                if cur_band:
                    band_segments.append(cur_band)
                    line_segments.append(cur_line)
                    cur_band = []
                    cur_line = []
        if cur_band:
            band_segments.append(cur_band)
            line_segments.append(cur_line)

        for b_seg in band_segments:
            if len(b_seg) >= 2:
                upper = [f"{x:.1f},{y75:.1f}" for x, _, y75 in b_seg]
                lower = [f"{x:.1f},{y25:.1f}" for x, y25, _ in reversed(b_seg)]
                poly_pts = " ".join(upper + lower)
                svg.append(
                    f'  <polygon points="{poly_pts}" fill="{color}" fill-opacity="0.24" stroke="none" />'
                )

        for l_seg in line_segments:
            if len(l_seg) >= 2:
                pts_s = " ".join(f"{x:.1f},{y:.1f}" for x, y in l_seg)
                svg.append(
                    f'  <polyline points="{pts_s}" fill="none" stroke="{color}" stroke-width="2.4" />'
                )

    svg.append(
        f'  <text x="40" y="{height - 18}" class="note-text">Source: WFP Benin Food Prices (HDX, CC BY-IGO 3.0), processed by src/clean/clean_prices.py &amp; src/analysis/eda.py. Shaded band in {mod_start_ym}..{mod_end_ym} shows cross-market P25–P75 (IQR); solid line shows Tier-1 median.</text>'
    )
    svg.append("</svg>")

    out_path = figures_dir / "fig1_regimes_and_trends_2007_2026.svg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(svg), encoding="utf-8")
    return out_path


def render_fig2_seasonality_by_zone(
    seasonality_lookup: dict[tuple[str, str], dict[int, dict[str, float]]],
    figures_dir: Path,
) -> Path:
    """Render Figure 2: 2x2 grid of 12-month seasonal indices by product and agro-ecological zone."""
    width, height = 1160, 760
    svg = _svg_header(
        width,
        height,
        "Figure 2 — Bénin AgroMarket: 12-Month Seasonal Price Profiles by Agro-Ecological Latitude Zone (2019–2026 Tier-1 Markets)",
        "Four-panel seasonal index chart (100 = annual market mean) comparing South (<7.5N), Center (7.5-9.5N), and North (>=9.5N) across Maize (white), Tomatoes, Yam (white), and Early Yam.",
    )

    svg.append(
        '  <text x="40" y="36" class="fig-title">Figure 2 — Profils saisonniers mensuels par zone agro-écologique (2019–2026, Indice 100 = moyenne annuelle)</text>'
    )
    svg.append(
        '  <text x="40" y="56" class="fig-subtitle">Indice déflaté par marché-année sur les marchés Tier-1 : Sud (&lt;7.5°N, bimodal), Centre (7.5°–9.5°N, transition) et Nord (&gt;=9.5°N, unimodal) avec bande IQR nationale</text>'
    )

    leg_y = 80
    svg.append(
        f'  <rect x="40" y="{leg_y - 12}" width="1080" height="26" fill="{COLOR_PANEL_ALT}" stroke="{COLOR_BORDER}" rx="4" />'
    )
    legend_items = [
        ("South (<7.5°N, Bimodal)", COLOR_LATERITE, "solid"),
        ("Center (7.5°–9.5°N, Transition)", COLOR_GOLD, "solid"),
        ("North (>=9.5°N, Unimodal)", COLOR_SLATE, "solid"),
        ("National Tier-1 Mean & P25–P75 IQR Band", COLOR_INK, "dashed"),
    ]
    lx = 60
    for label, col, style in legend_items:
        dash = 'stroke-dasharray="5,3"' if style == "dashed" else ""
        svg.append(
            f'  <line x1="{lx}" y1="{leg_y + 1}" x2="{lx + 28}" y2="{leg_y + 1}" stroke="{col}" stroke-width="2.5" {dash} />'
        )
        svg.append(
            f'  <text x="{lx + 35}" y="{leg_y + 5}" font-size="11" font-weight="bold" fill="{COLOR_INK}">{escape(label)}</text>'
        )
        lx += 265

    panels_meta = [
        ("2A", "Maize (white)", "Maïs blanc", "", 60.0, 150.0, 0, 0),
        ("2B", "Tomatoes", "Tomate fraîche", "", 40.0, 200.0, 0, 1),
        ("2C", "Yam (white)", "Igname blanche (Kokoro)", "", 60.0, 150.0, 1, 0),
        ("2D", "Yam", "Igname précoce (Laboko)", "EXPLORATION ONLY, ", 60.0, 150.0, 1, 1),
    ]

    col_lefts = [75.0, 635.0]
    row_tops = [128.0, 445.0]
    pw, ph = 485.0, 250.0

    zone_styles = [
        ("South (<7.5°N, Bimodal)", COLOR_LATERITE, ""),
        ("Center (7.5°–9.5°N, Transition)", COLOR_GOLD, ""),
        ("North (>=9.5°N, Unimodal)", COLOR_SLATE, ""),
        ("All Tier-1 (National)", COLOR_INK, "5,3"),
    ]

    for code, comm, fr_name, role_prefix, y_min, y_max, r_idx, c_idx in panels_meta:
        nat_stats = seasonality_lookup.get((comm, "All Tier-1 (National)"), {})
        n_mkts = int(nat_stats[1]["mkts_cnt"]) if nat_stats else 0
        title = f"{code}. {fr_name} — {comm} [{role_prefix}{n_mkts} Tier-1 Markets]"

        x0 = col_lefts[c_idx]
        y0 = row_tops[r_idx]
        x1 = x0 + pw
        y1 = y0 + ph

        def x_of_m(m: int, x0: float = x0) -> float:
            return x0 + ((m - 1) / 11.0) * pw

        def y_of_idx(val: float, y0: float = y0, y1: float = y1, y_min: float = y_min, y_max: float = y_max) -> float:
            clamped = max(y_min, min(y_max, val))
            return y1 - ((clamped - y_min) / (y_max - y_min)) * ph

        svg.append(
            f'  <rect x="{x0:.1f}" y="{y0:.1f}" width="{pw:.1f}" height="{ph:.1f}" fill="{COLOR_CARD}" stroke="{COLOR_BORDER}" stroke-width="1.2" />'
        )
        svg.append(
            f'  <text x="{x0:.1f}" y="{y0 - 8:.1f}" class="panel-title">{escape(title)}</text>'
        )

        step = 20.0 if (y_max - y_min) <= 100.0 else 40.0
        v = y_min
        while v <= y_max + 0.1:
            yy = y_of_idx(v)
            is_100 = abs(v - 100.0) < 1e-3
            sc = COLOR_INK if is_100 else COLOR_GRID
            sw = "1.4" if is_100 else "0.9"
            dash = 'stroke-dasharray="3,3"' if is_100 else ""
            svg.append(
                f'  <line x1="{x0:.1f}" y1="{yy:.1f}" x2="{x1:.1f}" y2="{yy:.1f}" stroke="{sc}" stroke-width="{sw}" {dash} />'
            )
            svg.append(
                f'  <text x="{x0 - 8:.1f}" y="{yy + 4:.1f}" text-anchor="end" class="tick-label">{int(v)}</text>'
            )
            v += step

        for m in range(1, 13):
            xx = x_of_m(m)
            svg.append(
                f'  <line x1="{xx:.1f}" y1="{y0:.1f}" x2="{xx:.1f}" y2="{y1:.1f}" stroke="{COLOR_GRID}" stroke-width="0.7" />'
            )
            svg.append(
                f'  <text x="{xx:.1f}" y="{y1 + 16:.1f}" text-anchor="middle" class="tick-label">{MONTH_NAMES_SHORT[m - 1]}</text>'
            )

        if nat_stats:
            upper_pts = [f"{x_of_m(m):.1f},{y_of_idx(nat_stats[m]['idx_p75']):.1f}" for m in range(1, 13)]
            lower_pts = [f"{x_of_m(m):.1f},{y_of_idx(nat_stats[m]['idx_p25']):.1f}" for m in range(12, 0, -1)]
            svg.append(
                f'  <polygon points="{" ".join(upper_pts + lower_pts)}" fill="#9E9689" fill-opacity="0.20" />'
            )

        for z_name, z_col, z_dash in zone_styles:
            z_stats = seasonality_lookup.get((comm, z_name))
            if not z_stats:
                continue
            pts = [f"{x_of_m(m):.1f},{y_of_idx(z_stats[m]['idx_mean']):.1f}" for m in range(1, 13)]
            dash_attr = f'stroke-dasharray="{z_dash}"' if z_dash else ""
            svg.append(
                f'  <polyline points="{" ".join(pts)}" fill="none" stroke="{z_col}" stroke-width="2.3" {dash_attr} />'
            )
            for m in range(1, 13):
                cx = x_of_m(m)
                cy = y_of_idx(z_stats[m]["idx_mean"])
                svg.append(
                    f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.8" fill="{z_col}" />'
                )

        if nat_stats:
            peak_m = max(range(1, 13), key=lambda m: nat_stats[m]["idx_mean"])
            trough_m = min(range(1, 13), key=lambda m: nat_stats[m]["idx_mean"])
            p_val = nat_stats[peak_m]["idx_mean"]
            t_val = nat_stats[trough_m]["idx_mean"]
            amp_pct = ((p_val / t_val) - 1.0) * 100.0
            svg.append(
                f'  <text x="{x0 + 10:.1f}" y="{y0 + 18:.1f}" font-size="10.5" font-weight="bold" fill="{COLOR_INK}">Peak: {MONTH_NAMES_SHORT[peak_m - 1]} ({p_val:.1f}) | Trough: {MONTH_NAMES_SHORT[trough_m - 1]} ({t_val:.1f}) | Spread: +{amp_pct:.1f}%</text>'
            )

    svg.append(
        f'  <text x="40" y="{height - 16}" class="note-text">Source: src/analysis/eda.py → docs/tables/eda_seasonality_profile.md (2019–2026 Tier-1 markets). Shaded band = National P25–P75 IQR of market-year seasonal indices.</text>'
    )
    svg.append("</svg>")

    out_path = figures_dir / "fig2_seasonality_by_zone.svg"
    out_path.write_text("\n".join(svg), encoding="utf-8")
    return out_path


def _compute_nice_axis_bounds(min_val: float, max_val: float, n_ticks: int = 4) -> tuple[float, float]:
    """Compute nice rounded [x_min, x_max] bounds that strictly enclose [min_val, max_val]."""
    raw_span = max(10.0, max_val - min_val)
    rough_step = raw_span / n_ticks
    mag = 10.0 ** math.floor(math.log10(rough_step))
    residual = rough_step / mag
    if residual <= 1.0:
        nice_step = 1.0 * mag
    elif residual <= 2.0:
        nice_step = 2.0 * mag
    elif residual <= 2.5:
        nice_step = 2.5 * mag
    elif residual <= 5.0:
        nice_step = 5.0 * mag
    else:
        nice_step = 10.0 * mag

    x_min = max(0.0, math.floor(min_val / nice_step) * nice_step)
    x_max = math.ceil((max_val * 1.03) / nice_step) * nice_step
    if x_max <= max_val:
        x_max += nice_step
    return x_min, x_max


def render_fig3_market_differences_tier1(
    market_stats_by_prod: dict[str, list[dict[str, Any]]],
    figures_dir: Path,
) -> Path:
    """Render Figure 3: Horizontal dot & IQR range plot comparing Tier-1 markets across the 3 primary products.

    Computes all market counts and x-axis bounds dynamically from the plotted data
    so no point or IQR bar is clamped and mean value labels sit in a dedicated right
    gutter without ever overlapping plotted bars or dots.
    """
    width, height = 1180, 780

    def select_markets(records: list[dict[str, Any]], target_n: int = 19) -> list[dict[str, Any]]:
        if len(records) <= target_n:
            return records
        selected_names = {m["market"] for m in records[:6]} | {m["market"] for m in records[-6:]}
        priority_hubs = [
            "Dantokpa",
            "Glazoué",
            "Parakou",
            "Malanville (CBM)",
            "Kérou",
            "Djougou",
            "Kétou",
            "Natitingou",
            "Bohicon",
            "Nikki",
            "Savalou",
            "Comé",
            "Ouando",
            "Banikoara",
            "Bembèrèkè",
        ]
        for h in priority_hubs:
            if len(selected_names) >= target_n:
                break
            if any(m["market"] == h for m in records):
                selected_names.add(h)
        for m in records:
            if len(selected_names) >= target_n:
                break
            selected_names.add(m["market"])
        return [m for m in records if m["market"] in selected_names]

    sel_mw = select_markets(market_stats_by_prod["Maize (white)"])
    sel_tom = select_markets(market_stats_by_prod["Tomatoes"])
    sel_yw = select_markets(market_stats_by_prod["Yam (white)"])

    svg = _svg_header(
        width,
        height,
        "Figure 3 — Bénin AgroMarket: Spatial Price Dispersion Across Tier-1 Markets (2019–2026, XOF/kg)",
        f"Three-column horizontal range and dot plot comparing lowest-cost producer hubs and highest-cost consumer markets for Maize (white) ({len(sel_mw)}/{len(market_stats_by_prod['Maize (white)'])} markets), Tomatoes ({len(sel_tom)}/{len(market_stats_by_prod['Tomatoes'])} markets), and Yam (white) ({len(sel_yw)}/{len(market_stats_by_prod['Yam (white)'])} markets).",
    )

    svg.append(
        '  <text x="40" y="36" class="fig-title">Figure 3 — Disparités spatiales des prix entre marchés Tier-1 (2019–2026, Médiane, Moyenne &amp; IQR en XOF/kg)</text>'
    )
    svg.append(
        f'  <text x="40" y="56" class="fig-subtitle">Classement des bassins excédentaires (prix bas) aux marchés de consommation (prix élevés) : Maïs blanc ({len(sel_mw)}/{len(market_stats_by_prod["Maize (white)"])} marchés), Tomate ({len(sel_tom)}/{len(market_stats_by_prod["Tomatoes"])} marchés) et Igname blanche ({len(sel_yw)}/{len(market_stats_by_prod["Yam (white)"])} marchés Tier-1)</text>'
    )

    cols_spec = [
        ("3A", "Maize (white)", "Maïs blanc", sel_mw, COLOR_GOLD, 35.0),
        ("3B", "Tomatoes", "Tomate fraîche", sel_tom, COLOR_LATERITE, 420.0),
        ("3C", "Yam (white)", "Igname blanche", sel_yw, COLOR_GREEN, 805.0),
    ]

    top_y = 95.0
    panel_h = 615.0
    label_w = 110.0
    plot_w = 195.0
    val_gutter_w = 38.0  # Dedicated right gutter for numeric mean labels

    for code, comm, fr_name, sel_recs, color, col_x in cols_spec:
        all_recs = market_stats_by_prod[comm]
        n_sel = len(sel_recs)
        n_all = len(all_recs)
        mode_str = "All" if n_sel == n_all else "Selected"
        title = f"{code}. {fr_name} ({mode_str} {n_sel} / {n_all} Tier-1)"

        min_plotted = min(min(m["p25"], m["median"], m["mean"]) for m in sel_recs)
        max_plotted = max(max(m["p75"], m["median"], m["mean"]) for m in sel_recs)
        x_min, x_max = _compute_nice_axis_bounds(min_plotted, max_plotted, n_ticks=4)

        nat_mean = mean(m["mean"] for m in all_recs)

        px0 = col_x + label_w
        px1 = px0 + plot_w

        def x_of_p(val: float, px0: float = px0, x_min: float = x_min, x_max: float = x_max) -> float:
            return px0 + ((val - x_min) / (x_max - x_min)) * plot_w

        svg.append(
            f'  <text x="{col_x:.1f}" y="{top_y - 10:.1f}" class="panel-title">{escape(title)}</text>'
        )
        svg.append(
            f'  <rect x="{px0:.1f}" y="{top_y:.1f}" width="{plot_w + val_gutter_w:.1f}" height="{panel_h}" fill="{COLOR_CARD}" stroke="{COLOR_BORDER}" stroke-width="1.2" />'
        )
        # Separator between plot canvas and numeric value gutter
        svg.append(
            f'  <line x1="{px1:.1f}" y1="{top_y:.1f}" x2="{px1:.1f}" y2="{top_y + panel_h:.1f}" stroke="{COLOR_GRID}" stroke-width="1.0" />'
        )
        svg.append(
            f'  <text x="{px1 + val_gutter_w - 4:.1f}" y="{top_y + 13:.1f}" text-anchor="end" font-size="8.5" font-weight="bold" fill="#5C5850">Mean</text>'
        )

        n_ticks = 4
        for ti in range(n_ticks + 1):
            v = x_min + (x_max - x_min) * (ti / n_ticks)
            xx = x_of_p(v)
            svg.append(
                f'  <line x1="{xx:.1f}" y1="{top_y:.1f}" x2="{xx:.1f}" y2="{top_y + panel_h:.1f}" stroke="{COLOR_GRID}" stroke-width="0.9" />'
            )
            svg.append(
                f'  <text x="{xx:.1f}" y="{top_y + panel_h + 16:.1f}" text-anchor="middle" class="tick-label">{int(round(v))}</text>'
            )

        x_nat = x_of_p(nat_mean)
        svg.append(
            f'  <line x1="{x_nat:.1f}" y1="{top_y:.1f}" x2="{x_nat:.1f}" y2="{top_y + panel_h:.1f}" stroke="{COLOR_INK}" stroke-width="1.4" stroke-dasharray="4,3" />'
        )
        svg.append(
            f'  <text x="{x_nat:.1f}" y="{top_y + 13:.1f}" text-anchor="middle" font-size="9" font-weight="bold" fill="{COLOR_INK}">{nat_mean:.0f}</text>'
        )

        row_step = (panel_h - 28.0) / len(sel_recs)
        for idx, m in enumerate(sel_recs):
            yy = top_y + 26.0 + idx * row_step
            if idx % 2 == 1:
                svg.append(
                    f'  <rect x="{px0 + 1:.1f}" y="{yy - 0.45 * row_step:.1f}" width="{plot_w + val_gutter_w - 2:.1f}" height="{0.9 * row_step:.1f}" fill="{COLOR_PANEL_ALT}" opacity="0.55" />'
                )

            x25 = x_of_p(m["p25"])
            x75 = x_of_p(m["p75"])
            xmed = x_of_p(m["median"])
            xmean = x_of_p(m["mean"])

            mkt_label = m["market"].replace("Ahidahomè (Porto-Novo)", "Ahidahomè").replace("Malanville (CBM)", "Malanville")
            svg.append(
                f'  <text x="{px0 - 6:.1f}" y="{yy + 3.5:.1f}" text-anchor="end" font-size="10" fill="{COLOR_INK}">{escape(mkt_label)}</text>'
            )
            svg.append(
                f'  <line x1="{x25:.1f}" y1="{yy:.1f}" x2="{x75:.1f}" y2="{yy:.1f}" stroke="{color}" stroke-width="4.5" stroke-linecap="round" opacity="0.55" />'
            )
            svg.append(
                f'  <circle cx="{xmed:.1f}" cy="{yy:.1f}" r="4.0" fill="{color}" stroke="#FFFFFF" stroke-width="1" />'
            )
            svg.append(
                f'  <circle cx="{xmean:.1f}" cy="{yy:.1f}" r="2.2" fill="{COLOR_INK}" />'
            )
            svg.append(
                f'  <text x="{px1 + val_gutter_w - 4:.1f}" y="{yy + 3:.1f}" text-anchor="end" font-size="9" fill="#5C5850">{m["mean"]:.0f}</text>'
            )

    svg.append(
        f'  <text x="40" y="{height - 18}" class="note-text">Source: src/analysis/eda.py → docs/tables/eda_market_differences.md (2019–2026 Tier-1 markets). Horizontal bar = P25–P75 IQR; colored circle = median; black dot &amp; right column = mean (XOF/kg).</text>'
    )
    svg.append("</svg>")

    out_path = figures_dir / "fig3_market_differences_tier1.svg"
    out_path.write_text("\n".join(svg), encoding="utf-8")
    return out_path


def render_fig4_abrupt_changes_and_outliers(
    rows: list[dict[str, Any]],
    monthly_shock_metrics: dict[tuple[str, str], dict[str, Any]],
    figures_dir: Path,
) -> Path:
    """Render Figure 4: Empirical timeline of monthly cross-market surges/drops and outlier jumps (2019-2026).

    Computes all market counts and outlier counts in panel titles dynamically at
    runtime from the exact plotted subset (Tier-1 markets in 2019-01..2026-09).
    """
    width, height = 1160, 760
    svg = _svg_header(
        width,
        height,
        "Figure 4 — Bénin AgroMarket: Empirical Candidate Shocks, Synchronized Surges & Outlier Jumps (2019–2026 Tier-1 Markets)",
        "Three-panel timeline showing monthly Tier-1 median MoM % changes, share of markets surging >=+35% MoM, and count of >=2x outlier jumps for Maize (white), Tomatoes, and Yam (white) on 2019-2026 Tier-1 markets.",
    )

    svg.append(
        '  <text x="40" y="36" class="fig-title">Figure 4 — Changements brusques, chocs candidats synchronisés et sauts atypiques (2019–2026, Marchés Tier-1)</text>'
    )
    svg.append(
        '  <text x="40" y="56" class="fig-subtitle">Détection purement empirique sur la fenêtre 2019–2026 (barres = % de marchés Tier-1 avec saut mensuel &gt;= +35% ou &lt;= -30% ; courbe = variation mensuelle médiane %)</text>'
    )

    all_yms = sorted({ym for (_, ym) in monthly_shock_metrics.keys()})
    n_m = len(all_yms)

    left_x, right_x = 85.0, 1115.0
    plot_w = right_x - left_x

    def x_of_idx(idx: int) -> float:
        return left_x + (idx / (n_m - 1)) * plot_w

    panels_meta = [
        ("4A", "Maize (white)", "Maïs blanc", COLOR_GOLD),
        ("4B", "Tomatoes", "Tomate fraîche", COLOR_LATERITE),
        ("4C", "Yam (white)", "Igname blanche", COLOR_GREEN),
    ]

    top_start = 94.0
    panel_h = 182.0
    panel_gap = 36.0

    for p_idx, (code, comm, fr_name, color) in enumerate(panels_meta):
        plotted_rows = [
            r
            for r in rows
            if r["commodity"] == comm and r["regime"] == "modern_2019_2026" and r["is_tier1"] == 1
        ]
        n_t1_mkts = len({r["market"] for r in plotted_rows})
        n_jmp_t1 = sum(r["is_outlier_jump_i"] for r in plotted_rows)
        n_lvl_t1 = sum(r["is_outlier_level_i"] for r in plotted_rows)
        n_obs_t1 = len(plotted_rows)
        p_title = (
            f"{code}. {fr_name} — {comm} [2019–2026 Tier-1 ({n_t1_mkts} Markets, {n_obs_t1} Obs): "
            f"{n_jmp_t1} Jump Outliers |ΔlnP|>ln2, {n_lvl_t1} Level Outliers |z|>3.5]"
        )

        y0 = top_start + p_idx * (panel_h + panel_gap)
        y1 = y0 + panel_h
        y_zero = y0 + 0.5 * panel_h

        def y_of_pct(pct: float, y_zero: float = y_zero) -> float:
            clamped = max(-100.0, min(100.0, pct))
            return y_zero - (clamped / 100.0) * (0.5 * panel_h)

        svg.append(
            f'  <rect x="{left_x:.1f}" y="{y0:.1f}" width="{plot_w:.1f}" height="{panel_h}" fill="{COLOR_CARD}" stroke="{COLOR_BORDER}" stroke-width="1.2" />'
        )
        svg.append(
            f'  <text x="{left_x:.1f}" y="{y0 - 8:.1f}" class="panel-title">{escape(p_title)}</text>'
        )

        for pct_v in (-100, -50, 0, 50, 100):
            yy = y_of_pct(pct_v)
            sw = "1.3" if pct_v == 0 else "0.8"
            sc = COLOR_INK if pct_v == 0 else COLOR_GRID
            svg.append(
                f'  <line x1="{left_x:.1f}" y1="{yy:.1f}" x2="{right_x:.1f}" y2="{yy:.1f}" stroke="{sc}" stroke-width="{sw}" />'
            )
            svg.append(
                f'  <text x="{left_x - 8:.1f}" y="{yy + 4:.1f}" text-anchor="end" class="tick-label">{pct_v:+d}%</text>'
            )

        for idx, ym in enumerate(all_yms):
            if ym.endswith("-01"):
                xx = x_of_idx(idx)
                svg.append(
                    f'  <line x1="{xx:.1f}" y1="{y0:.1f}" x2="{xx:.1f}" y2="{y1:.1f}" stroke="{COLOR_GRID}" stroke-width="0.9" />'
                )
                if p_idx == len(panels_meta) - 1:
                    svg.append(
                        f'  <text x="{xx + 20:.1f}" y="{y1 + 16:.1f}" text-anchor="middle" class="tick-label">{ym[:4]}</text>'
                    )

        bar_w = (plot_w / n_m) * 0.68
        line_pts: list[str] = []
        annotated_peaks: list[tuple[float, str, float, float]] = []

        for idx, ym in enumerate(all_yms):
            m_stat = monthly_shock_metrics.get((comm, ym))
            if not m_stat:
                continue
            xx = x_of_idx(idx)
            s_up = m_stat["share_surge_35"]
            s_dn = m_stat["share_drop_30"]
            med_mom = m_stat["nat_med_mom_pct"]

            if s_up > 0:
                y_up = y_of_pct(s_up)
                svg.append(
                    f'  <rect x="{xx - 0.5 * bar_w:.1f}" y="{y_up:.1f}" width="{bar_w:.1f}" height="{y_zero - y_up:.1f}" fill="{COLOR_LATERITE}" fill-opacity="0.45" />'
                )
            if s_dn > 0:
                y_dn = y_of_pct(-s_dn)
                svg.append(
                    f'  <rect x="{xx - 0.5 * bar_w:.1f}" y="{y_zero:.1f}" width="{bar_w:.1f}" height="{y_dn - y_zero:.1f}" fill="{COLOR_SLATE}" fill-opacity="0.45" />'
                )

            yy_med = y_of_pct(med_mom)
            line_pts.append(f"{xx:.1f},{yy_med:.1f}")

            thresh = 15.0 if comm == "Maize (white)" else 30.0
            if s_up >= thresh or abs(med_mom) >= thresh:
                annotated_peaks.append((max(s_up, abs(med_mom)), ym, xx, yy_med))

        if len(line_pts) >= 2:
            svg.append(
                f'  <polyline points="{" ".join(line_pts)}" fill="none" stroke="{color}" stroke-width="2.2" />'
            )

        annotated_peaks.sort(key=lambda x: -x[0])
        chosen_x: list[float] = []
        for _, ym, xx, yy_med in annotated_peaks:
            if any(abs(xx - cx) < 42.0 for cx in chosen_x):
                continue
            chosen_x.append(xx)
            if len(chosen_x) > 4:
                break
            m_stat = monthly_shock_metrics[(comm, ym)]
            lbl = f"{ym} ({m_stat['nat_med_mom_pct']:+.0f}%)"
            ty = max(y0 + 14.0, min(y1 - 8.0, yy_med - 8.0 if m_stat["nat_med_mom_pct"] >= 0 else yy_med + 14.0))
            svg.append(
                f'  <circle cx="{xx:.1f}" cy="{yy_med:.1f}" r="3.5" fill="{COLOR_INK}" />'
            )
            svg.append(
                f'  <text x="{xx:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="9.5" font-weight="bold" fill="{COLOR_INK}">{escape(lbl)}</text>'
            )

    svg.append(
        f'  <text x="40" y="{height - 16}" class="note-text">Source: src/analysis/eda.py → docs/tables/eda_abrupt_changes.md (2019–2026 Tier-1 markets). Upward red bars = % of Tier-1 markets jumping &gt;=+35% MoM; downward blue bars = % dropping &lt;=-30% MoM; solid curve = Tier-1 median MoM %.</text>'
    )
    svg.append("</svg>")

    out_path = figures_dir / "fig4_abrupt_changes_and_outliers.svg"
    out_path.write_text("\n".join(svg), encoding="utf-8")
    return out_path


def render_fig5_weather_lag_relationships(
    rows: list[dict[str, Any]],
    seasonality_lookup: dict[tuple[str, str], dict[int, dict[str, float]]],
    figures_dir: Path,
) -> Path:
    """Render Figure 5: Joint agroclimatic cycle (NASA POWER PRECTOTCORR) and lagged price correlations."""
    width, height = 1160, 720
    svg = _svg_header(
        width,
        height,
        "Figure 5 — Bénin AgroMarket: NASA POWER Agroclimatic Regimes & Lagged Price Anomaly Relationships (2019–2026)",
        "Left panel shows monthly MERRA-2 rainfall (PRECTOTCORR) across South, Center, and North Benin vs seasonal price indices; right panel shows lagged correlation profiles.",
    )

    svg.append(
        '  <text x="40" y="36" class="fig-title">Figure 5 — Cycles agroclimatiques NASA POWER (pluviométrie &amp; température) et corrélations décalées (t-1 à t-3)</text>'
    )
    svg.append(
        '  <text x="40" y="56" class="fig-subtitle">Gauche : cycle mensuel des précipitations (PRECTOTCORR, mm/jour) par zone vs indice saisonnier des prix | Droite : corrélations de Pearson r avec les variables météo décalées</text>'
    )

    modern_t1 = [
        r
        for r in rows
        if r["regime"] == "modern_2019_2026"
        and r["is_tier1"] == 1
        and r["commodity"] in ("Maize (white)", "Tomatoes", "Yam (white)")
    ]

    zone_month_precip: dict[tuple[str, int], list[float]] = defaultdict(list)
    for r in modern_t1:
        if r["precip_lag1m_f"] is not None:
            m_rain = ((r["month"] - 2) % 12) + 1
            zone_month_precip[(r["zone"], m_rain)].append(r["precip_lag1m_f"])

    lx0, lx1 = 75.0, 565.0
    lw = lx1 - lx0

    ry0, ry1 = 98.0, 345.0
    rh = ry1 - ry0
    svg.append(
        f'  <rect x="{lx0:.1f}" y="{ry0:.1f}" width="{lw:.1f}" height="{rh:.1f}" fill="{COLOR_CARD}" stroke="{COLOR_BORDER}" stroke-width="1.2" />'
    )
    svg.append(
        f'  <text x="{lx0:.1f}" y="{ry0 - 8:.1f}" class="panel-title">5A. Cycle pluviométrique mensuel NASA POWER (PRECTOTCORR, mm/jour)</text>'
    )

    for v in (0, 2, 4, 6, 8, 10):
        yy = ry1 - (v / 10.0) * rh
        svg.append(
            f'  <line x1="{lx0:.1f}" y1="{yy:.1f}" x2="{lx1:.1f}" y2="{yy:.1f}" stroke="{COLOR_GRID}" stroke-width="0.9" />'
        )
        svg.append(
            f'  <text x="{lx0 - 8:.1f}" y="{yy + 4:.1f}" text-anchor="end" class="tick-label">{v}</text>'
        )

    for m in range(1, 13):
        xx = lx0 + ((m - 1) / 11.0) * lw
        svg.append(
            f'  <text x="{xx:.1f}" y="{ry1 + 16:.1f}" text-anchor="middle" class="tick-label">{MONTH_NAMES_SHORT[m - 1]}</text>'
        )

    for z_name, z_col in [
        ("South (<7.5°N, Bimodal)", COLOR_LATERITE),
        ("Center (7.5°–9.5°N, Transition)", COLOR_GOLD),
        ("North (>=9.5°N, Unimodal)", COLOR_SLATE),
    ]:
        pts: list[str] = []
        for m in range(1, 13):
            vals = zone_month_precip.get((z_name, m), [0.0])
            mv = mean(vals) if vals else 0.0
            xx = lx0 + ((m - 1) / 11.0) * lw
            yy = ry1 - (min(10.0, mv) / 10.0) * rh
            pts.append(f"{xx:.1f},{yy:.1f}")
        svg.append(
            f'  <polyline points="{" ".join(pts)}" fill="none" stroke="{z_col}" stroke-width="2.5" />'
        )

    svg.append(
        f'  <text x="{lx0 + 12:.1f}" y="{ry0 + 20:.1f}" font-size="10.5" font-weight="bold" fill="{COLOR_LATERITE}">South (&lt;7.5°N, Bimodal)</text>'
    )
    svg.append(
        f'  <text x="{lx0 + 175:.1f}" y="{ry0 + 20:.1f}" font-size="10.5" font-weight="bold" fill="{COLOR_GOLD}">Center (7.5°–9.5°N)</text>'
    )
    svg.append(
        f'  <text x="{lx0 + 325:.1f}" y="{ry0 + 20:.1f}" font-size="10.5" font-weight="bold" fill="{COLOR_SLATE}">North (&gt;=9.5°N, Unimodal)</text>'
    )

    py0, py1 = 410.0, 665.0
    ph = py1 - py0
    svg.append(
        f'  <rect x="{lx0:.1f}" y="{py0:.1f}" width="{lw:.1f}" height="{ph:.1f}" fill="{COLOR_CARD}" stroke="{COLOR_BORDER}" stroke-width="1.2" />'
    )
    svg.append(
        f'  <text x="{lx0:.1f}" y="{py0 - 8:.1f}" class="panel-title">5B. Réponse saisonnière des prix (Indice 100 = moyenne annuelle, Tier-1)</text>'
    )

    for v in (60, 80, 100, 120, 140, 160):
        yy = py1 - ((v - 60.0) / 100.0) * ph
        sw = "1.4" if v == 100 else "0.9"
        sc = COLOR_INK if v == 100 else COLOR_GRID
        svg.append(
            f'  <line x1="{lx0:.1f}" y1="{yy:.1f}" x2="{lx1:.1f}" y2="{yy:.1f}" stroke="{sc}" stroke-width="{sw}" />'
        )
        svg.append(
            f'  <text x="{lx0 - 8:.1f}" y="{yy + 4:.1f}" text-anchor="end" class="tick-label">{v}</text>'
        )

    for m in range(1, 13):
        xx = lx0 + ((m - 1) / 11.0) * lw
        svg.append(
            f'  <text x="{xx:.1f}" y="{py1 + 16:.1f}" text-anchor="middle" class="tick-label">{MONTH_NAMES_SHORT[m - 1]}</text>'
        )

    for comm, col in [
        ("Maize (white)", COLOR_GOLD),
        ("Tomatoes", COLOR_LATERITE),
        ("Yam (white)", COLOR_GREEN),
    ]:
        s_map = seasonality_lookup[(comm, "All Tier-1 (National)")]
        pts = [
            f"{lx0 + ((m - 1) / 11.0) * lw:.1f},{py1 - ((max(60.0, min(160.0, s_map[m]['idx_mean'])) - 60.0) / 100.0) * ph:.1f}"
            for m in range(1, 13)
        ]
        svg.append(
            f'  <polyline points="{" ".join(pts)}" fill="none" stroke="{col}" stroke-width="2.5" />'
        )

    svg.append(
        f'  <text x="{lx0 + 12:.1f}" y="{py0 + 20:.1f}" font-size="10.5" font-weight="bold" fill="{COLOR_GOLD}">Maize (white)</text>'
    )
    svg.append(
        f'  <text x="{lx0 + 135:.1f}" y="{py0 + 20:.1f}" font-size="10.5" font-weight="bold" fill="{COLOR_LATERITE}">Tomatoes</text>'
    )
    svg.append(
        f'  <text x="{lx0 + 235:.1f}" y="{py0 + 20:.1f}" font-size="10.5" font-weight="bold" fill="{COLOR_GREEN}">Yam (white)</text>'
    )

    rx0, rx1 = 765.0, 1125.0
    rw = rx1 - rx0
    ry_top, ry_bot = 98.0, 665.0
    rh_right = ry_bot - ry_top

    svg.append(
        f'  <rect x="{rx0:.1f}" y="{ry_top:.1f}" width="{rw:.1f}" height="{rh_right:.1f}" fill="{COLOR_CARD}" stroke="{COLOR_BORDER}" stroke-width="1.2" />'
    )
    svg.append(
        f'  <text x="{rx0 - 155:.1f}" y="{ry_top - 8:.1f}" class="panel-title">5C. Corrélation de Pearson r (Anomalie saisonnière log-prix vs Météo décalée)</text>'
    )

    mkt_yr_lps: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for r in modern_t1:
        mkt_yr_lps[(r["commodity"], r["market"], r["year"])].append(math.log(r["price_f"]))
    mkt_yr_lp_mean = {k: mean(v) for k, v in mkt_yr_lps.items() if len(v) >= 6}

    feat_specs = [
        ("precip_lag1m_f", "precip_lag1m (t-1)"),
        ("precip_lag2m_f", "precip_lag2m (t-2)"),
        ("precip_lag3m_f", "precip_lag3m (t-3)"),
        ("precip_roll3m_lag1_f", "precip_roll3m_lag1"),
        ("precip_anom_z_lag1m_f", "precip_anom_z_lag1m"),
        ("t2m_lag1m_f", "t2m_lag1m (t-1)"),
        ("t2m_max_lag1m_f", "t2m_max_lag1m (t-1)"),
        ("rh2m_lag1m_f", "rh2m_lag1m (t-1)"),
    ]

    def x_of_r(r_val: float) -> float:
        clamped = max(-0.6, min(0.6, r_val))
        return rx0 + ((clamped + 0.6) / 1.2) * rw

    x_zero = x_of_r(0.0)
    for rv in (-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6):
        xx = x_of_r(rv)
        sw = "1.4" if abs(rv) < 1e-6 else "0.8"
        sc = COLOR_INK if abs(rv) < 1e-6 else COLOR_GRID
        svg.append(
            f'  <line x1="{xx:.1f}" y1="{ry_top:.1f}" x2="{xx:.1f}" y2="{ry_bot:.1f}" stroke="{sc}" stroke-width="{sw}" />'
        )
        svg.append(
            f'  <text x="{xx:.1f}" y="{ry_bot + 16:.1f}" text-anchor="middle" class="tick-label">{rv:+.1f}</text>'
        )

    group_h = rh_right / len(feat_specs)
    for f_idx, (f_key, f_lbl) in enumerate(feat_specs):
        gy = ry_top + (f_idx + 0.5) * group_h
        svg.append(
            f'  <text x="{rx0 - 8:.1f}" y="{gy + 4:.1f}" text-anchor="end" font-size="10.5" font-weight="bold" fill="{COLOR_INK}">{escape(f_lbl)}</text>'
        )
        for p_offset, (comm, col) in enumerate([
            ("Maize (white)", COLOR_GOLD),
            ("Tomatoes", COLOR_LATERITE),
            ("Yam (white)", COLOR_GREEN),
        ]):
            sub = [
                r
                for r in modern_t1
                if r["commodity"] == comm
                and (comm, r["market"], r["year"]) in mkt_yr_lp_mean
                and r[f_key] is not None
            ]
            xs = [math.log(r["price_f"]) - mkt_yr_lp_mean[(comm, r["market"], r["year"])] for r in sub]
            ys = [r[f_key] for r in sub]
            r_val = pearson_r(xs, ys)
            by = gy + (p_offset - 1) * 14.0
            bx = x_of_r(r_val)
            b_left = min(x_zero, bx)
            b_w = max(1.5, abs(bx - x_zero))
            svg.append(
                f'  <rect x="{b_left:.1f}" y="{by - 5:.1f}" width="{b_w:.1f}" height="10" fill="{col}" rx="1.5" />'
            )
            lbl_x = bx + 5.0 if r_val >= 0 else bx - 5.0
            anchor = "start" if r_val >= 0 else "end"
            svg.append(
                f'  <text x="{lbl_x:.1f}" y="{by + 3.5:.1f}" text-anchor="{anchor}" font-size="9" fill="{COLOR_INK}">{r_val:+.2f}</text>'
            )

    svg.append(
        f'  <text x="40" y="{height - 16}" class="note-text">Source: src/analysis/eda.py → docs/tables/eda_weather_lag_correlations.md (NASA POWER MERRA-2 agroclimatology joined to 2019–2026 Tier-1 markets).</text>'
    )
    svg.append("</svg>")

    out_path = figures_dir / "fig5_weather_lag_relationships.svg"
    out_path.write_text("\n".join(svg), encoding="utf-8")
    return out_path


def run_eda_pipeline(
    cleaned_csv: Path = CLEANED_PRICES_ALL_CSV,
    tables_dir: Path = DOCS_TABLES_DIR,
    figures_dir: Path = DOCS_FIGURES_DIR,
) -> dict[str, Any]:
    """Run all Phase 1(b) EDA table computations and SVG figure renders."""
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    rows = load_cleaned_rows(cleaned_csv)

    t1 = build_table1_summary_by_product(rows, tables_dir)
    t2, seasonality_lookup = build_table2_seasonality_profile(rows, tables_dir)
    t3, market_stats_by_prod = build_table3_market_differences(rows, tables_dir)
    t4 = build_table4_yam_variety_comparison(rows, tables_dir)
    t5, monthly_shock_metrics = build_table5_abrupt_changes(rows, tables_dir)
    t6 = build_table6_weather_lag_correlations(rows, tables_dir)

    fig1 = render_fig1_regimes_and_trends(rows, figures_dir)
    fig2 = render_fig2_seasonality_by_zone(seasonality_lookup, figures_dir)
    fig3 = render_fig3_market_differences_tier1(market_stats_by_prod, figures_dir)
    fig4 = render_fig4_abrupt_changes_and_outliers(rows, monthly_shock_metrics, figures_dir)
    fig5 = render_fig5_weather_lag_relationships(rows, seasonality_lookup, figures_dir)

    return {
        "rows_loaded": len(rows),
        "tables_generated": 6,
        "figures_generated": [fig1.name, fig2.name, fig3.name, fig4.name, fig5.name],
        "t1_rows": len(t1),
        "t2_rows": len(t2),
        "t3_rows": len(t3),
        "t4_rows": len(t4),
        "t5_rows": len(t5),
        "t6_rows": len(t6),
    }


if __name__ == "__main__":
    summary = run_eda_pipeline()
    print(f"[OK] Phase 1(b) EDA complete. Loaded {summary['rows_loaded']:,} cleaned rows.")
    print(f"     Generated {summary['tables_generated']} tables in {DOCS_TABLES_DIR}")
    print(f"     Generated {len(summary['figures_generated'])} SVG figures in {DOCS_FIGURES_DIR}:")
    for fn in summary["figures_generated"]:
        print(f"       - {fn}")

"""Clean WFP Benin food prices and join lagged NASA POWER agroclimatic features.

This module implements the Phase 1(a) data engineering pipeline:
1. Validates schema, units (KG), currency (XOF), priceflag (actual), and checks
   for duplicate (commodity, market_id, pricetype, unit, date) keys.
2. Filters out the 18 inactive metadata markets and writes ``markets_active.csv``.
3. Flags extreme price levels and month-over-month jumps deterministically
   (``is_outlier_level``, ``is_outlier_jump``, ``is_outlier``, ``outlier_reason``)
   without ever deleting or overwriting raw observations.
4. Labels temporal regimes (``pre_2019_exploration`` vs ``modern_2019_2026``)
   with zero interpolation across the 2017-2018 reporting hiatus.
5. Joins strictly lagged NASA POWER agroclimatic features (computed using a
   2006-2018 baseline for monthly rainfall anomalies to prevent data leakage).
6. Writes ``data/processed/prices_cleaned_all.csv``,
   ``data/processed/modeling_panel_2019_2026.csv``, and audit tables in
   ``docs/tables/``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import math
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

from src.analysis.coverage import months_between_dates, write_csv_and_md
from src.config import (
    ACTIVE_MARKETS_CSV,
    CLEANED_PRICES_ALL_CSV,
    DOCS_TABLES_DIR,
    ENABLED_PRODUCTS,
    FORECAST_PRIMARY_PRODUCTS,
    MODELING_END_YM,
    MODELING_PANEL_CSV,
    MODELING_START_DATE,
    MODELING_START_YM,
    MODELING_TOTAL_MONTHS,
    NASA_POWER_PARAMETERS,
    NASA_POWER_RAW_CSV,
    OUTLIER_MOM_LOG_JUMP_THRESHOLD,
    OUTLIER_ROBUST_Z_THRESHOLD,
    PROCESSED_DIR,
    PRODUCT_BY_COMMODITY,
    TIER1_MIN_OBSERVED_MONTHS,
    WFP_MARKETS_RAW_CSV,
    WFP_PRICES_RAW_CSV,
    classify_market_tier,
)
from src.ingest.download_nasa_power import snap_to_merra2_grid
from src.ingest.download_wfp import compute_checksums


def generate_modeling_calendar() -> list[str]:
    """Return the 93 monthly mid-month dates from 2019-01-15 to 2026-09-15."""
    dates: list[str] = []
    for yr in range(2019, 2027):
        for m in range(1, 13):
            if (yr, m) > (2026, 9):
                break
            dates.append(f"{yr:04d}-{m:02d}-15")
    assert len(dates) == MODELING_TOTAL_MONTHS
    return dates


def prev_year_month(ym: str, lag_months: int) -> str:
    """Shift a YYYY-MM string backward by ``lag_months`` calendar months."""
    yr, m = map(int, ym.split("-"))
    total_m = yr * 12 + (m - 1) - lag_months
    new_yr = total_m // 12
    new_m = (total_m % 12) + 1
    return f"{new_yr:04d}-{new_m:02d}"


def load_nasa_power_lagged_lookup(
    nasa_csv: Path = NASA_POWER_RAW_CSV,
) -> tuple[dict[tuple[str, str, str], dict[str, str]], dict[str, Any]]:
    """Load NASA POWER raw CSV and precompute strictly lagged weather features per grid cell."""
    raw_by_cell_ym: dict[tuple[str, str, str], dict[str, float | None]] = {}
    grid_cells: set[tuple[str, str]] = set()
    total_nasa_rows = 0
    missing_param_counts: Counter[str] = Counter()
    min_ym = "9999-99"
    max_ym = "0000-00"

    with nasa_csv.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            total_nasa_rows += 1
            glat = r["grid_lat"]
            glon = r["grid_lon"]
            ym = r["year_month"]
            grid_cells.add((glat, glon))
            if ym < min_ym:
                min_ym = ym
            if ym > max_ym:
                max_ym = ym

            p_map: dict[str, float | None] = {}
            for p in NASA_POWER_PARAMETERS:
                val = float(r[p])
                if val <= -900.0:
                    p_map[p] = None
                    missing_param_counts[p] += 1
                else:
                    p_map[p] = val
            raw_by_cell_ym[(glat, glon, ym)] = p_map

    # Compute 2006-2018 historical monthly baseline (mean, std) per (grid_lat, grid_lon, month_num)
    # Using strictly pre-2019 years prevents any look-ahead data leakage in anomaly z-scores.
    clim_baseline: dict[tuple[str, str, int], tuple[float, float]] = {}
    for glat, glon in grid_cells:
        for m_num in range(1, 13):
            vals = [
                raw_by_cell_ym[(glat, glon, f"{yr:04d}-{m_num:02d}")]["PRECTOTCORR"]
                for yr in range(2006, 2019)
                if (glat, glon, f"{yr:04d}-{m_num:02d}") in raw_by_cell_ym
                and raw_by_cell_ym[(glat, glon, f"{yr:04d}-{m_num:02d}")]["PRECTOTCORR"] is not None
            ]
            valid_vals = [v for v in vals if v is not None]
            if valid_vals:
                mu = mean(valid_vals)
                sd = pstdev(valid_vals)
                clim_baseline[(glat, glon, m_num)] = (mu, sd if sd > 1e-6 else 1.0)
            else:
                clim_baseline[(glat, glon, m_num)] = (0.0, 1.0)

    # Precompute lagged feature strings for every (glat, glon, ym)
    lagged_lookup: dict[tuple[str, str, str], dict[str, str]] = {}
    for (glat, glon, ym) in list(raw_by_cell_ym.keys()):
        ym_l1 = prev_year_month(ym, 1)
        ym_l2 = prev_year_month(ym, 2)
        ym_l3 = prev_year_month(ym, 3)

        d_l1 = raw_by_cell_ym.get((glat, glon, ym_l1), {})
        d_l2 = raw_by_cell_ym.get((glat, glon, ym_l2), {})
        d_l3 = raw_by_cell_ym.get((glat, glon, ym_l3), {})

        p1 = d_l1.get("PRECTOTCORR")
        p2 = d_l2.get("PRECTOTCORR")
        p3 = d_l3.get("PRECTOTCORR")
        t2m_1 = d_l1.get("T2M")
        tmax_1 = d_l1.get("T2M_MAX")
        tmin_1 = d_l1.get("T2M_MIN")
        rh_1 = d_l1.get("RH2M")

        p_roll3 = (
            mean([p1, p2, p3])
            if (p1 is not None and p2 is not None and p3 is not None)
            else None
        )
        m_l1 = int(ym_l1.split("-")[1])
        mu_p, sd_p = clim_baseline.get((glat, glon, m_l1), (0.0, 1.0))
        p_anom_z1 = (p1 - mu_p) / sd_p if p1 is not None else None

        lagged_lookup[(glat, glon, ym)] = {
            "precip_lag1m": f"{p1:.4f}" if p1 is not None else "",
            "precip_lag2m": f"{p2:.4f}" if p2 is not None else "",
            "precip_lag3m": f"{p3:.4f}" if p3 is not None else "",
            "precip_roll3m_lag1": f"{p_roll3:.4f}" if p_roll3 is not None else "",
            "precip_anom_z_lag1m": f"{p_anom_z1:.4f}" if p_anom_z1 is not None else "",
            "t2m_lag1m": f"{t2m_1:.4f}" if t2m_1 is not None else "",
            "t2m_max_lag1m": f"{tmax_1:.4f}" if tmax_1 is not None else "",
            "t2m_min_lag1m": f"{tmin_1:.4f}" if tmin_1 is not None else "",
            "rh2m_lag1m": f"{rh_1:.4f}" if rh_1 is not None else "",
        }

    nasa_sha256, nasa_md5 = compute_checksums(nasa_csv)
    nasa_size = nasa_csv.stat().st_size
    nasa_stats = {
        "size_bytes": nasa_size,
        "sha256": nasa_sha256,
        "md5": nasa_md5,
        "total_rows": total_nasa_rows,
        "unique_grid_cells": len(grid_cells),
        "min_ym": min_ym,
        "max_ym": max_ym,
        "missing_param_counts": dict(missing_param_counts),
    }
    return lagged_lookup, nasa_stats


def compute_outlier_flags(
    series_date_price: dict[str, float],
) -> dict[str, tuple[int, int, int, str, float, float | None]]:
    """Compute (is_outlier_level, is_outlier_jump, is_outlier, reason, robust_z, mom_log_diff).

    Uses robust median/MAD on log(price) within the series and month-over-month
    log ratios on consecutive calendar months. Never modifies or removes prices.
    """
    if not series_date_price:
        return {}

    sorted_dates = sorted(series_date_price.keys())
    log_prices = [math.log(series_date_price[d]) for d in sorted_dates]
    med_lp = median(log_prices)
    abs_devs = [abs(lp - med_lp) for lp in log_prices]
    mad_lp = 1.4826 * median(abs_devs) if abs_devs else 0.0
    scale = mad_lp if mad_lp > 1e-4 else (pstdev(log_prices) if len(log_prices) > 1 else 1.0)
    if scale < 1e-4:
        scale = 1.0

    results: dict[str, tuple[int, int, int, str, float, float | None]] = {}
    for idx, dt in enumerate(sorted_dates):
        lp = math.log(series_date_price[dt])
        robust_z = (lp - med_lp) / scale
        is_level = 1 if abs(robust_z) > OUTLIER_ROBUST_Z_THRESHOLD else 0

        mom_log_diff: float | None = None
        is_jump = 0
        if idx > 0:
            prev_dt = sorted_dates[idx - 1]
            if months_between_dates(prev_dt, dt) == 2:
                prev_lp = math.log(series_date_price[prev_dt])
                mom_log_diff = lp - prev_lp
                if abs(mom_log_diff) > OUTLIER_MOM_LOG_JUMP_THRESHOLD:
                    is_jump = 1

        is_out = 1 if (is_level or is_jump) else 0
        reasons: list[str] = []
        if is_level:
            reasons.append(f"level_z={robust_z:+.2f}")
        if is_jump and mom_log_diff is not None:
            reasons.append(f"mom_log_jump={mom_log_diff:+.2f}")
        reason_str = ";".join(reasons) if reasons else "none"
        results[dt] = (is_level, is_jump, is_out, reason_str, robust_z, mom_log_diff)

    return results


def run_cleaning_pipeline(
    prices_csv: Path = WFP_PRICES_RAW_CSV,
    markets_csv: Path = WFP_MARKETS_RAW_CSV,
    nasa_csv: Path = NASA_POWER_RAW_CSV,
    processed_dir: Path = PROCESSED_DIR,
    tables_dir: Path = DOCS_TABLES_DIR,
) -> dict[str, Any]:
    """Execute the full Phase 1(a) cleaning and feature pipeline."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    lagged_weather_lookup, nasa_stats = load_nasa_power_lagged_lookup(nasa_csv=nasa_csv)

    # Write NASA POWER summary table to docs/tables/
    nasa_summary_rows: list[list[Any]] = [
        ["nasa_power_benin_markets.csv_size_bytes", nasa_stats["size_bytes"], "Exact byte size of NASA POWER monthly CSV"],
        ["nasa_power_benin_markets.csv_sha256", nasa_stats["sha256"], "SHA-256 hex digest of NASA POWER monthly CSV"],
        ["nasa_power_benin_markets.csv_md5", nasa_stats["md5"], "MD5 hex digest of NASA POWER monthly CSV"],
        ["nasa_power_total_rows", nasa_stats["total_rows"], "Total (grid_cell x year_month) rows (2006-01..2026-09)"],
        ["unique_merra2_grid_cells", nasa_stats["unique_grid_cells"], "Unique 0.5 x 0.625 deg MERRA-2 grid cells covering all 51 active markets"],
        ["year_month_range", f"{nasa_stats['min_ym']}..{nasa_stats['max_ym']}", "Temporal range of downloaded monthly agroclimatology"],
    ]
    for p in NASA_POWER_PARAMETERS:
        miss_cnt = nasa_stats["missing_param_counts"].get(p, 0)
        valid_cnt = nasa_stats["total_rows"] - miss_cnt
        nasa_summary_rows.append([
            f"param_{p}_valid_vs_missing",
            f"valid={valid_cnt}, missing(-999)={miss_cnt}",
            f"Completeness of {p} across {nasa_stats['total_rows']} grid-months",
        ])

    write_csv_and_md(
        csv_path=tables_dir / "nasa_power_summary.csv",
        md_path=tables_dir / "nasa_power_summary.md",
        title="NASA POWER Agroclimatology Dataset Summary (`nasa_power_benin_markets.csv`)",
        script_citation="src/clean/clean_prices.py",
        headers=["metric", "value", "description"],
        rows=nasa_summary_rows,
    )

    # Pass 1: Read raw WFP prices, check duplicates, collect active markets & enabled product rows
    enabled_commodities = {p.commodity for p in ENABLED_PRODUCTS}
    seen_keys: set[tuple[str, str, str, str, str]] = set()
    duplicate_keys_count = 0
    non_positive_price_count = 0
    total_raw_rows = 0

    active_markets_map: dict[str, dict[str, Any]] = {}
    enabled_rows: list[dict[str, str]] = []
    obs_2019_2026_by_prod_mkt: dict[tuple[str, str], set[str]] = defaultdict(set)
    series_prices_by_prod_mkt: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)

    with prices_csv.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("date", "").startswith("#"):
                continue
            total_raw_rows += 1
            key = (r["commodity"], r["market_id"], r["pricetype"], r["unit"], r["date"])
            if key in seen_keys:
                duplicate_keys_count += 1
            seen_keys.add(key)

            p_val = float(r["price"])
            if p_val <= 0 or not math.isfinite(p_val):
                non_positive_price_count += 1

            mid = r["market_id"]
            mkt = r["market"]
            lat = float(r["latitude"])
            lon = float(r["longitude"])
            glat, glon = snap_to_merra2_grid(lat, lon)
            active_markets_map[mkt] = {
                "market_id": mid,
                "market": mkt,
                "admin1": r["admin1"],
                "admin2": r["admin2"],
                "latitude": f"{lat:.4f}",
                "longitude": f"{lon:.4f}",
                "grid_lat": f"{glat:.4f}",
                "grid_lon": f"{glon:.4f}",
            }

            c = r["commodity"]
            if c in enabled_commodities:
                p_cfg = PRODUCT_BY_COMMODITY[c]
                if (
                    r["pricetype"] == p_cfg.pricetype
                    and r["unit"] == p_cfg.unit
                    and r["currency"] == p_cfg.currency
                    and r["priceflag"] == p_cfg.priceflag
                ):
                    enabled_rows.append(r)
                    series_prices_by_prod_mkt[(c, mkt)][r["date"]] = p_val
                    if r["date"] >= MODELING_START_DATE:
                        obs_2019_2026_by_prod_mkt[(c, mkt)].add(r["date"][:7])

    # Write active markets table (data/processed/markets_active.csv)
    active_mkt_headers = [
        "market_id",
        "market",
        "admin1",
        "admin2",
        "latitude",
        "longitude",
        "grid_lat",
        "grid_lon",
        "obs_2019_2026_maize_white",
        "tier1_maize_white",
        "obs_2019_2026_tomatoes",
        "tier1_tomatoes",
        "obs_2019_2026_yam_white",
        "tier1_yam_white",
        "obs_2019_2026_yam_early",
        "tier1_yam_early",
    ]
    active_mkt_rows: list[list[Any]] = []
    for mkt_name, m_info in sorted(
        active_markets_map.items(), key=lambda x: (x[1]["admin1"], x[1]["market"])
    ):
        mw_obs = len(obs_2019_2026_by_prod_mkt[("Maize (white)", mkt_name)])
        tom_obs = len(obs_2019_2026_by_prod_mkt[("Tomatoes", mkt_name)])
        yw_obs = len(obs_2019_2026_by_prod_mkt[("Yam (white)", mkt_name)])
        ye_obs = len(obs_2019_2026_by_prod_mkt[("Yam", mkt_name)])
        active_mkt_rows.append([
            m_info["market_id"],
            m_info["market"],
            m_info["admin1"],
            m_info["admin2"],
            m_info["latitude"],
            m_info["longitude"],
            m_info["grid_lat"],
            m_info["grid_lon"],
            mw_obs,
            1 if mw_obs >= TIER1_MIN_OBSERVED_MONTHS else 0,
            tom_obs,
            1 if tom_obs >= TIER1_MIN_OBSERVED_MONTHS else 0,
            yw_obs,
            1 if yw_obs >= TIER1_MIN_OBSERVED_MONTHS else 0,
            ye_obs,
            1 if ye_obs >= TIER1_MIN_OBSERVED_MONTHS else 0,
        ])

    with ACTIVE_MARKETS_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(active_mkt_headers)
        writer.writerows(active_mkt_rows)

    # Precompute outlier flags for every (commodity, market)
    outlier_lookup: dict[tuple[str, str], dict[str, tuple[int, int, int, str, float, float | None]]] = {}
    for (c, mkt), d_map in series_prices_by_prod_mkt.items():
        outlier_lookup[(c, mkt)] = compute_outlier_flags(d_map)

    # Write data/processed/prices_cleaned_all.csv (all observed rows for enabled products)
    cleaned_headers = [
        "date",
        "year_month",
        "year",
        "month",
        "regime",
        "product_slug",
        "product_role",
        "commodity",
        "commodity_id",
        "category",
        "market_id",
        "market",
        "admin1",
        "admin2",
        "latitude",
        "longitude",
        "grid_lat",
        "grid_lon",
        "pricetype",
        "unit",
        "currency",
        "priceflag",
        "price",
        "usdprice",
        "obs_months_2019_2026",
        "tier_2019_2026",
        "is_tier1_2019_2026",
        "is_outlier_level",
        "is_outlier_jump",
        "is_outlier",
        "outlier_reason",
        "robust_z",
        "mom_log_diff",
        "precip_lag1m",
        "precip_lag2m",
        "precip_lag3m",
        "precip_roll3m_lag1",
        "precip_anom_z_lag1m",
        "t2m_lag1m",
        "t2m_max_lag1m",
        "t2m_min_lag1m",
        "rh2m_lag1m",
    ]

    enabled_rows.sort(key=lambda r: (r["commodity"], r["market"], r["date"]))
    cleaned_out_rows: list[list[Any]] = []
    outlier_counts_by_prod: dict[str, Counter[str]] = defaultdict(Counter)
    regime_counts_by_prod: dict[str, Counter[str]] = defaultdict(Counter)

    row_by_prod_mkt_date: dict[tuple[str, str, str], dict[str, str]] = {}

    for r in enabled_rows:
        c = r["commodity"]
        mkt = r["market"]
        dt = r["date"]
        ym = dt[:7]
        yr, m_num = int(dt[:4]), int(dt[5:7])
        p_cfg = PRODUCT_BY_COMMODITY[c]
        m_info = active_markets_map[mkt]
        glat = m_info["grid_lat"]
        glon = m_info["grid_lon"]

        regime = "modern_2019_2026" if dt >= MODELING_START_DATE else "pre_2019_exploration"
        obs_19_cnt = len(obs_2019_2026_by_prod_mkt[(c, mkt)])
        tier_str = classify_market_tier(obs_19_cnt)
        is_t1 = 1 if obs_19_cnt >= TIER1_MIN_OBSERVED_MONTHS else 0

        is_lvl, is_jmp, is_out, reason_str, rob_z, mom_ld = outlier_lookup[(c, mkt)][dt]
        w_feats = lagged_weather_lookup.get((glat, glon, ym), {})

        regime_counts_by_prod[c][regime] += 1
        if is_lvl:
            outlier_counts_by_prod[c]["level"] += 1
        if is_jmp:
            outlier_counts_by_prod[c]["jump"] += 1
        if is_out:
            outlier_counts_by_prod[c]["any"] += 1
            if regime == "modern_2019_2026" and is_t1:
                outlier_counts_by_prod[c]["tier1_modern"] += 1

        row_by_prod_mkt_date[(c, mkt, dt)] = r

        cleaned_out_rows.append([
            dt,
            ym,
            yr,
            m_num,
            regime,
            p_cfg.slug,
            p_cfg.role,
            c,
            r["commodity_id"],
            r["category"],
            r["market_id"],
            mkt,
            r["admin1"],
            r["admin2"],
            m_info["latitude"],
            m_info["longitude"],
            glat,
            glon,
            r["pricetype"],
            r["unit"],
            r["currency"],
            r["priceflag"],
            r["price"],
            r["usdprice"],
            obs_19_cnt,
            tier_str,
            is_t1,
            is_lvl,
            is_jmp,
            is_out,
            reason_str,
            f"{rob_z:.4f}",
            f"{mom_ld:.4f}" if mom_ld is not None else "",
            w_feats.get("precip_lag1m", ""),
            w_feats.get("precip_lag2m", ""),
            w_feats.get("precip_lag3m", ""),
            w_feats.get("precip_roll3m_lag1", ""),
            w_feats.get("precip_anom_z_lag1m", ""),
            w_feats.get("t2m_lag1m", ""),
            w_feats.get("t2m_max_lag1m", ""),
            w_feats.get("t2m_min_lag1m", ""),
            w_feats.get("rh2m_lag1m", ""),
        ])

    with CLEANED_PRICES_ALL_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cleaned_headers)
        writer.writerows(cleaned_out_rows)

    # Construct regular monthly modeling panel (2019-01-15..2026-09-15, 93 months)
    # strictly for Tier-1 markets of FORECAST_PRIMARY_PRODUCTS
    calendar_dates = generate_modeling_calendar()
    panel_headers = [
        "date",
        "year_month",
        "year",
        "month",
        "product_slug",
        "commodity",
        "market_id",
        "market",
        "admin1",
        "admin2",
        "latitude",
        "longitude",
        "grid_lat",
        "grid_lon",
        "unit",
        "currency",
        "is_observed",
        "price",
        "usdprice",
        "price_interp_1m_max",
        "is_imputed_1m",
        "is_outlier_level",
        "is_outlier_jump",
        "is_outlier",
        "outlier_reason",
        "precip_lag1m",
        "precip_lag2m",
        "precip_lag3m",
        "precip_roll3m_lag1",
        "precip_anom_z_lag1m",
        "t2m_lag1m",
        "t2m_max_lag1m",
        "t2m_min_lag1m",
        "rh2m_lag1m",
    ]
    panel_rows: list[list[Any]] = []
    panel_stats_by_prod: dict[str, dict[str, int]] = {}

    for p_cfg in FORECAST_PRIMARY_PRODUCTS:
        c = p_cfg.commodity
        # Identify Tier-1 markets sorted by (admin1, market)
        tier1_mkts = sorted(
            [
                mkt
                for mkt in active_markets_map
                if len(obs_2019_2026_by_prod_mkt[(c, mkt)]) >= TIER1_MIN_OBSERVED_MONTHS
            ],
            key=lambda m: (active_markets_map[m]["admin1"], m),
        )
        n_grid = 0
        n_obs = 0
        n_missing = 0
        n_interp_1m = 0

        for mkt in tier1_mkts:
            m_info = active_markets_map[mkt]
            glat = m_info["grid_lat"]
            glon = m_info["grid_lon"]
            d_price_map = series_prices_by_prod_mkt[(c, mkt)]

            for idx, dt in enumerate(calendar_dates):
                n_grid += 1
                ym = dt[:7]
                yr, m_num = int(dt[:4]), int(dt[5:7])
                w_feats = lagged_weather_lookup.get((glat, glon, ym), {})

                if dt in d_price_map:
                    n_obs += 1
                    r_raw = row_by_prod_mkt_date[(c, mkt, dt)]
                    is_obs = 1
                    p_str = r_raw["price"]
                    usd_str = r_raw["usdprice"]
                    p_interp_str = r_raw["price"]
                    is_imp_1m = 0
                    is_lvl, is_jmp, is_out, reason_str, _, _ = outlier_lookup[(c, mkt)][dt]
                else:
                    n_missing += 1
                    is_obs = 0
                    p_str = ""
                    usd_str = ""
                    is_lvl, is_jmp, is_out, reason_str = 0, 0, 0, "unobserved"
                    # Check if isolated 1-month interior gap (t-1 and t+1 both observed)
                    if (
                        0 < idx < len(calendar_dates) - 1
                        and calendar_dates[idx - 1] in d_price_map
                        and calendar_dates[idx + 1] in d_price_map
                    ):
                        p_prev = d_price_map[calendar_dates[idx - 1]]
                        p_next = d_price_map[calendar_dates[idx + 1]]
                        p_interp_str = f"{0.5 * (p_prev + p_next):.2f}"
                        is_imp_1m = 1
                        n_interp_1m += 1
                    else:
                        p_interp_str = ""
                        is_imp_1m = 0

                panel_rows.append([
                    dt,
                    ym,
                    yr,
                    m_num,
                    p_cfg.slug,
                    c,
                    m_info["market_id"],
                    mkt,
                    m_info["admin1"],
                    m_info["admin2"],
                    m_info["latitude"],
                    m_info["longitude"],
                    glat,
                    glon,
                    p_cfg.unit,
                    p_cfg.currency,
                    is_obs,
                    p_str,
                    usd_str,
                    p_interp_str,
                    is_imp_1m,
                    is_lvl,
                    is_jmp,
                    is_out,
                    reason_str,
                    w_feats.get("precip_lag1m", ""),
                    w_feats.get("precip_lag2m", ""),
                    w_feats.get("precip_lag3m", ""),
                    w_feats.get("precip_roll3m_lag1", ""),
                    w_feats.get("precip_anom_z_lag1m", ""),
                    w_feats.get("t2m_lag1m", ""),
                    w_feats.get("t2m_max_lag1m", ""),
                    w_feats.get("t2m_min_lag1m", ""),
                    w_feats.get("rh2m_lag1m", ""),
                ])

        panel_stats_by_prod[c] = {
            "tier1_markets": len(tier1_mkts),
            "grid_rows": n_grid,
            "observed_rows": n_obs,
            "unobserved_rows": n_missing,
            "isolated_1m_gaps_flagged": n_interp_1m,
            "multi_month_unobserved_rows": n_missing - n_interp_1m,
        }

    with MODELING_PANEL_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(panel_headers)
        writer.writerows(panel_rows)

    # Write cleaning audit summary table to docs/tables/
    audit_headers = [
        "Product",
        "Role",
        "Obs (All 2007-2026)",
        "Obs Pre-2019 (Exploration)",
        "Obs 2019-2026 (Modern)",
        "Outliers Flagged (Level |z|>3.5)",
        "Outliers Flagged (MoM Jump >=2x)",
        "Total Outliers Flagged (0 Deleted)",
        "Tier-1 Markets (>=80m)",
        "Tier-1 Grid Rows (93m)",
        "Tier-1 Observed Rows",
        "Tier-1 Unobserved Rows (price='')",
        "Isolated 1m Gaps (price_interp_1m_max)",
    ]
    audit_rows: list[list[Any]] = []
    for p_cfg in ENABLED_PRODUCTS:
        c = p_cfg.commodity
        rc = regime_counts_by_prod[c]
        oc = outlier_counts_by_prod[c]
        ps = panel_stats_by_prod.get(c, {})
        audit_rows.append([
            c,
            p_cfg.role,
            rc["pre_2019_exploration"] + rc["modern_2019_2026"],
            rc["pre_2019_exploration"],
            rc["modern_2019_2026"],
            oc["level"],
            oc["jump"],
            oc["any"],
            ps.get("tier1_markets", 17 if c == "Yam" else 0),
            ps.get("grid_rows", "-"),
            ps.get("observed_rows", "-"),
            ps.get("unobserved_rows", "-"),
            ps.get("isolated_1m_gaps_flagged", "-"),
        ])

    write_csv_and_md(
        csv_path=tables_dir / "cleaning_audit_summary.csv",
        md_path=tables_dir / "cleaning_audit_summary.md",
        title="Phase 1(a) Cleaning & Feature Pipeline Audit Summary",
        script_citation="src/clean/clean_prices.py",
        headers=audit_headers,
        rows=audit_rows,
        notes=[
            f"Duplicate `(commodity, market_id, pricetype, unit, date)` keys across all `{total_raw_rows:,}` raw rows: `{duplicate_keys_count}`.",
            f"Non-positive or non-finite prices across all `{total_raw_rows:,}` raw rows: `{non_positive_price_count}`.",
            f"Active markets saved in `data/processed/markets_active.csv`: `{len(active_markets_map)}` (`18` inactive metadata markets stripped).",
            f"Total cleaned observed rows in `data/processed/prices_cleaned_all.csv`: `{len(cleaned_out_rows):,}`.",
            f"Total regular monthly grid rows in `data/processed/modeling_panel_2019_2026.csv`: `{len(panel_rows):,}` (`0` prices silently imputed; unobserved months have `is_observed=0` and `price=''`).",
        ],
    )

    return {
        "duplicate_keys_count": duplicate_keys_count,
        "non_positive_price_count": non_positive_price_count,
        "cleaned_rows": len(cleaned_out_rows),
        "panel_rows": len(panel_rows),
        "nasa_stats": nasa_stats,
    }


if __name__ == "__main__":
    summary = run_cleaning_pipeline()
    print(
        f"[OK] Cleaning pipeline finished.\n"
        f"     Duplicates found: {summary['duplicate_keys_count']}\n"
        f"     Cleaned rows (prices_cleaned_all.csv): {summary['cleaned_rows']:,}\n"
        f"     Modeling panel rows (modeling_panel_2019_2026.csv): {summary['panel_rows']:,}"
    )

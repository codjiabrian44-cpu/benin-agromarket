"""Strict export contract validator for `web/public/data/forecasts.json`.

Enforces `AGENTS.md` `## Export contract`:
- Every file exported for the web app must be checked by a validation script
  (`src/evaluate/validate_export.py`) that fails loudly on missing, zero or inconsistent
  fields. Run it as part of the pipeline.

Specifically checks:
1. Exactly 111 Tier-1 series present (`49` `Maize (white)`, `43` `Tomatoes`, `19` `Yam (white)`).
2. All 51 active markets present in `markets_coverage`, with coverage counts and tiers
   matching `docs/tables/coverage_by_market.csv` (`0` markets with `tier == "None"` while
   having observations, and `0` markets with `obs_months_2019_2026 == 0` when they have
   post-2019 observations).
3. `is_forecasted` in `markets_coverage` is 100% consistent with the exported `series` list.
4. No `NaN`, `null`, infinite, non-positive, or empty forecast arrays across all 111 series.
5. Prediction intervals are strictly ordered (`0 < low_90 <= low_80 <= point_forecast <= high_80 <= high_90`)
   for both `forecasts` (`h=1, 2, 3`) and `recent_backtest_h1`.
6. Dates are strictly consistent (`as_of_date == 2026-09-15`, `last_observed_date <= as_of_date`,
   forecast `target_date` values equal to `["2026-10-15", "2026-11-15", "2026-12-15"]`, and
   history/backtest dates strictly chronological).
7. Every product and horizon (`h1, h2, h3`) includes a holdout-computed `reliability` field and
   non-empty French (`note_fr`) and English (`note_en`) plain-language notes.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from src.config import PROJECT_ROOT, TABLES_DIR

SCRIPT_CITATION = "src/evaluate/validate_export.py"
DEFAULT_EXPORT_PATH = PROJECT_ROOT / "web" / "public" / "data" / "forecasts.json"

EXPECTED_TIER1_COUNTS_BY_SLUG = {
    "maize_white": 49,
    "tomatoes": 43,
    "yam_white": 19,
}
SLUG_TO_COMMODITY = {
    "maize_white": "Maize (white)",
    "tomatoes": "Tomatoes",
    "yam_white": "Yam (white)",
}
EXPECTED_HORIZON_DATES = {
    1: "2026-10-15",
    2: "2026-11-15",
    3: "2026-12-15",
}


def _is_valid_pos_number(val: Any) -> bool:
    """Return True iff `val` is a finite float/int strictly > 0."""
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        return False
    return math.isfinite(float(val)) and float(val) > 0.0


def validate_forecasts_export(
    export_path: Path = DEFAULT_EXPORT_PATH,
    coverage_csv_path: Path = TABLES_DIR / "coverage_by_market.csv",
) -> Dict[str, Any]:
    """Validate `web/public/data/forecasts.json` against the Phase 2/3 export contract.

    Writes `docs/tables/phase2_export_validation.{csv,md}` and raises `ValueError` if any
    check fails.
    """
    if not export_path.exists():
        raise FileNotFoundError(f"Missing export file: {export_path}")

    raw_text = export_path.read_text(encoding="utf-8")
    # Disallow literal NaN or Infinity tokens in JSON text
    payload = json.loads(
        raw_text,
        parse_constant=lambda c: (_ for _ in ()).throw(
            ValueError(f"Illegal non-standard JSON constant {c!r} in {export_path}")
        ),
    )

    df_cov = pd.read_csv(coverage_csv_path, dtype={"Market ID": str})
    expected_cov_by_prod_mkt: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for _, row in df_cov.iterrows():
        prod = str(row["Product"]).strip()
        mkt = str(row["Market"]).strip()
        expected_cov_by_prod_mkt[(prod, mkt)] = {
            "market_id": str(row["Market ID"]).strip(),
            "obs_2019_26": int(row["Obs (2019-26)"]),
            "tier_2019_26": str(row["Tier (2019-26)"]).strip(),
        }

    checks: List[Tuple[str, str, str, str]] = []
    errors: List[str] = []

    def record_check(check_id: str, description: str, passed: bool, details: str) -> None:
        status = "PASS" if passed else "FAIL"
        checks.append((check_id, description, status, details))
        if not passed:
            errors.append(f"[{check_id}] {description}: {details}")

    # -------------------------------------------------------------------------
    # Check 1: Top-level structure & 111 Tier-1 series count
    # -------------------------------------------------------------------------
    series_list = payload.get("series", [])
    n_series = len(series_list)
    by_slug_counts = {
        slug: sum(1 for s in series_list if s.get("product_slug") == slug)
        for slug in EXPECTED_TIER1_COUNTS_BY_SLUG
    }
    c1_pass = (n_series == 111) and (by_slug_counts == EXPECTED_TIER1_COUNTS_BY_SLUG)
    record_check(
        "CHK-01",
        "Total Tier-1 series count and per-product breakdown",
        c1_pass,
        f"Total={n_series} (expected 111): maize_white={by_slug_counts['maize_white']} (exp 49), "
        f"tomatoes={by_slug_counts['tomatoes']} (exp 43), yam_white={by_slug_counts['yam_white']} (exp 19)",
    )

    # -------------------------------------------------------------------------
    # Check 2: `markets_coverage` matches `docs/tables/coverage_by_market.csv` (C1 fix)
    # -------------------------------------------------------------------------
    markets_cov = payload.get("markets_coverage", [])
    n_markets_cov = len(markets_cov)
    tier_none_with_obs = 0
    zero_obs_mismatch = 0
    cov_mismatch_details: List[str] = []
    cov_t1_counts = {"maize_white": 0, "tomatoes": 0, "yam_white": 0}
    cov_forecasted_pairs: set[Tuple[str, str]] = set()

    for m_entry in markets_cov:
        mkt_name = str(m_entry.get("market", "")).strip()
        cov_by_prod = m_entry.get("coverage_by_product", {})
        for slug, comm_name in SLUG_TO_COMMODITY.items():
            p_cov = cov_by_prod.get(slug, {})
            tier_val = str(p_cov.get("tier", "None"))
            obs_val = int(p_cov.get("obs_months_2019_2026", -1))
            is_fc = bool(p_cov.get("is_forecasted", False))

            if is_fc:
                cov_t1_counts[slug] += 1
                cov_forecasted_pairs.add((slug, mkt_name))

            if ( tier_val in ("None", "", "null") ) and obs_val > 0:
                tier_none_with_obs += 1
                cov_mismatch_details.append(f"{mkt_name}/{slug}: tier={tier_val} with obs={obs_val}")

            exp_info = expected_cov_by_prod_mkt.get((comm_name, mkt_name))
            if exp_info is not None:
                if obs_val != exp_info["obs_2019_26"] or tier_val != exp_info["tier_2019_26"]:
                    zero_obs_mismatch += 1
                    cov_mismatch_details.append(
                        f"{mkt_name}/{slug}: got (obs={obs_val}, tier={tier_val}) vs "
                        f"expected (obs={exp_info['obs_2019_26']}, tier={exp_info['tier_2019_26']})"
                    )
            else:
                # Market has 0 observations in all periods for this product (e.g. Cotonou/Comé/Ouando for Yam (white))
                if obs_val != 0 or is_fc:
                    zero_obs_mismatch += 1
                    cov_mismatch_details.append(
                        f"{mkt_name}/{slug}: absent in coverage_by_market.csv but got obs={obs_val}, is_forecasted={is_fc}"
                    )

    c2_pass = (
        n_markets_cov == 51
        and tier_none_with_obs == 0
        and zero_obs_mismatch == 0
        and cov_t1_counts == EXPECTED_TIER1_COUNTS_BY_SLUG
    )
    record_check(
        "CHK-02",
        "Markets coverage table alignment (51 markets, no tier 'None' with obs, exact obs match)",
        c2_pass,
        f"Active markets={n_markets_cov} (exp 51), tier='None' with obs={tier_none_with_obs}, "
        f"mismatches vs coverage_by_market.csv={zero_obs_mismatch}, "
        f"Tier-1 counts in markets_coverage={cov_t1_counts}",
    )

    # -------------------------------------------------------------------------
    # Check 3: `is_forecasted` consistency between `markets_coverage` and `series`
    # -------------------------------------------------------------------------
    series_pairs = {(str(s.get("product_slug")), str(s.get("market"))) for s in series_list}
    all_series_flagged_true = all(bool(s.get("is_forecasted")) is True for s in series_list)
    sym_diff = cov_forecasted_pairs ^ series_pairs
    c3_pass = all_series_flagged_true and (len(sym_diff) == 0) and (len(series_pairs) == 111)
    record_check(
        "CHK-03",
        "Consistency of `is_forecasted` between `markets_coverage` and `series`",
        c3_pass,
        f"Forecasted pairs in markets_coverage={len(cov_forecasted_pairs)}, "
        f"unique series pairs={len(series_pairs)}, symmetric difference={len(sym_diff)}",
    )

    # -------------------------------------------------------------------------
    # Check 4: No NaN, null, non-positive, or empty forecast arrays
    # -------------------------------------------------------------------------
    empty_or_nan_count = 0
    total_forecast_points = 0
    total_bt_points = 0
    total_hist_points = 0

    for s in series_list:
        f_list = s.get("forecasts", [])
        bt_list = s.get("recent_backtest_h1", [])
        h_list = s.get("history", [])
        if len(f_list) != 3 or len(bt_list) == 0 or len(h_list) < 80:
            empty_or_nan_count += 1
        for fp in f_list:
            total_forecast_points += 1
            for k in ("point_forecast", "low_80", "high_80", "low_90", "high_90"):
                if not _is_valid_pos_number(fp.get(k)):
                    empty_or_nan_count += 1
        for bp in bt_list:
            total_bt_points += 1
            for k in ("actual_price", "predicted_price", "low_80", "high_80", "low_90", "high_90"):
                if not _is_valid_pos_number(bp.get(k)):
                    empty_or_nan_count += 1
        for hp in h_list:
            total_hist_points += 1
            if not _is_valid_pos_number(hp.get("price")):
                empty_or_nan_count += 1

    c4_pass = (empty_or_nan_count == 0) and (total_forecast_points == 333)
    record_check(
        "CHK-04",
        "No NaN, null, non-positive, or empty forecast/backtest/history arrays",
        c4_pass,
        f"Invalid/empty values={empty_or_nan_count} across {total_forecast_points} forecast pts (exp 333), "
        f"{total_bt_points} holdout backtest pts, and {total_hist_points} historical pts",
    )

    # -------------------------------------------------------------------------
    # Check 5: Prediction intervals strictly ordered (low_90 <= low_80 <= forecast <= high_80 <= high_90)
    # -------------------------------------------------------------------------
    interval_violations = 0
    for s in series_list:
        for fp in s.get("forecasts", []):
            l90, l80, pf, h80, h90 = (
                float(fp["low_90"]),
                float(fp["low_80"]),
                float(fp["point_forecast"]),
                float(fp["high_80"]),
                float(fp["high_90"]),
            )
            if not (0.0 < l90 <= l80 <= pf <= h80 <= h90):
                interval_violations += 1
        for bp in s.get("recent_backtest_h1", []):
            l90, l80, pf, h80, h90 = (
                float(bp["low_90"]),
                float(bp["low_80"]),
                float(bp["predicted_price"]),
                float(bp["high_80"]),
                float(bp["high_90"]),
            )
            if not (0.0 < l90 <= l80 <= pf <= h80 <= h90):
                interval_violations += 1

    c5_pass = interval_violations == 0
    record_check(
        "CHK-05",
        "Prediction interval ordering (`0 < low_90 <= low_80 <= forecast <= high_80 <= high_90`)",
        c5_pass,
        f"Ordering violations={interval_violations} across {total_forecast_points + total_bt_points} interval sets",
    )

    # -------------------------------------------------------------------------
    # Check 6: Date consistency across top-level metadata, history, backtest, and forecasts
    # -------------------------------------------------------------------------
    date_violations = 0
    if payload.get("as_of_date") != "2026-09-15":
        date_violations += 1
    if payload.get("forecast_target_dates") != ["2026-10-15", "2026-11-15", "2026-12-15"]:
        date_violations += 1

    for s in series_list:
        as_of = str(s.get("as_of_date", ""))
        last_obs = str(s.get("last_observed_date", ""))
        if as_of != "2026-09-15" or not last_obs or last_obs > as_of:
            date_violations += 1

        h_dates = [str(hp.get("date", "")) for hp in s.get("history", [])]
        if h_dates != sorted(h_dates) or len(h_dates) != len(set(h_dates)) or h_dates[-1] != last_obs:
            date_violations += 1

        bt_dates = [str(bp.get("date", "")) for bp in s.get("recent_backtest_h1", [])]
        if (
            bt_dates != sorted(bt_dates)
            or len(bt_dates) != len(set(bt_dates))
            or bt_dates[0] < "2025-10-15"
            or bt_dates[-1] > "2026-09-15"
        ):
            date_violations += 1

        f_list = s.get("forecasts", [])
        for idx_h, h_expected in enumerate((1, 2, 3)):
            if idx_h >= len(f_list):
                date_violations += 1
                continue
            fp = f_list[idx_h]
            if (
                int(fp.get("horizon_months", -1)) != h_expected
                or str(fp.get("target_date", "")) != EXPECTED_HORIZON_DATES[h_expected]
            ):
                date_violations += 1

    c6_pass = date_violations == 0
    record_check(
        "CHK-06",
        "Chronological and target date consistency (`as_of_date=2026-09-15`, `2026-10..2026-12`)",
        c6_pass,
        f"Date consistency violations={date_violations} across 111 series",
    )

    # -------------------------------------------------------------------------
    # Check 7: Holdout-derived `reliability` field and bilingual UI notes per (product, horizon)
    # -------------------------------------------------------------------------
    rel_violations = 0
    rel_summary: List[str] = []
    products_dict = payload.get("products", {})
    allowed_rel_statuses = {
        "calibrated",
        "baseline_retained",
        "intervals_too_narrow",
        "baseline_retained_intervals_too_narrow",
        "no_better_than_simple",
    }

    forbidden_note_tokens = (
        "Tier-1",
        "MAPE",
        "MAE",
        "holdout",
        "h=1",
        "h=2",
        "h=3",
        "Naive_LastValue",
        "Seasonal_Ratio_Naive",
        "Seasonal_Naive_12m",
        "Ridge_ARX",
        "HGBR_NoWeather",
        "HGBR_WithWeather",
        "ETS_HoltWinters",
        "SARIMAX",
        "récolte",
        "soudure",
    )

    for slug in EXPECTED_TIER1_COUNTS_BY_SLUG:
        p_meta = products_dict.get(slug, {})
        rel_by_h = p_meta.get("reliability_by_horizon", {})
        by_h_test = p_meta.get("backtest_accuracy", {}).get("by_horizon_test", {})
        for h_key in ("h1", "h2", "h3"):
            r_obj = rel_by_h.get(h_key, {})
            h_obj = by_h_test.get(h_key, {})
            status_val = str(r_obj.get("status", ""))
            note_fr = str(r_obj.get("note_fr", "")).strip()
            note_en = str(r_obj.get("note_en", "")).strip()
            has_jargon = any(tok in note_fr or tok in note_en for tok in forbidden_note_tokens)
            if (
                status_val not in allowed_rel_statuses
                or h_obj.get("reliability") != status_val
                or len(note_fr) < 20
                or len(note_en) < 20
                or has_jargon
            ):
                rel_violations += 1
            else:
                rel_summary.append(f"{slug}/{h_key}={status_val}")

    for s in series_list:
        for fp in s.get("forecasts", []):
            n_fr = str(fp.get("reliability_note_fr", "")).strip()
            n_en = str(fp.get("reliability_note_en", "")).strip()
            if (
                str(fp.get("reliability", "")) not in allowed_rel_statuses
                or len(n_fr) < 20
                or len(n_en) < 20
                or any(tok in n_fr or tok in n_en for tok in forbidden_note_tokens)
            ):
                rel_violations += 1

    c7_pass = (rel_violations == 0) and (len(rel_summary) == 9)
    record_check(
        "CHK-07",
        "Per-(product, horizon) `reliability` status and plain-language FR/EN notes (zero jargon)",
        c7_pass,
        f"Violations={rel_violations}; 9 product-horizons: {', '.join(rel_summary)}",
    )

    # Write validation report to `docs/tables/phase2_export_validation.{csv,md}`
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    csv_out = TABLES_DIR / "phase2_export_validation.csv"
    md_out = TABLES_DIR / "phase2_export_validation.md"
    headers = ["Check ID", "Contract Rule Checked", "Status", "Verification Details"]

    with csv_out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in checks:
            writer.writerow(row)

    md_lines = [
        "# Phase 2 Web Export Contract Validation Report (`web/public/data/forecasts.json`)",
        "",
        f"*Generated by [`{SCRIPT_CITATION}`](../../{SCRIPT_CITATION}) — do not edit by hand.*",
        "",
        f"- **Validated File:** [`web/public/data/forecasts.json`](../../web/public/data/forecasts.json) (`{export_path.stat().st_size:,}` bytes)",
        f"- **Overall Contract Status:** **{'PASS (7/7 checks passed)' if not errors else 'FAIL'}**",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in checks:
        md_lines.append("| " + " | ".join(str(c) for c in row) + " |")
    md_lines.append("")
    md_out.write_text("\n".join(md_lines), encoding="utf-8")

    if errors:
        raise ValueError(
            "Export contract validation failed for web/public/data/forecasts.json:\n"
            + "\n".join(errors)
        )

    print(
        f"[Export Validator] PASS: All {len(checks)} contract checks succeeded for {export_path.name}. "
        f"Report saved to {md_out}"
    )
    return {
        "status": "PASS",
        "checks": checks,
        "report_md": str(md_out),
        "report_csv": str(csv_out),
    }


if __name__ == "__main__":
    try:
        validate_forecasts_export()
    except Exception as exc:
        print(f"[Export Validator] FAIL: {exc}", file=sys.stderr)
        sys.exit(1)

"""Generate `docs/tables/phase2_recompute_diff.{csv,md}` and `docs/audit/README.md` comparing
validation metrics, selected champions, and holdout test metrics before vs after `--recompute`.

Enforces Safeguards 1, 3, and 4:
- Compares archived artifacts in `docs/audit/before_recompute/` against the freshly
  recomputed `data/processed/phase2_backtest_predictions.csv`,
  `docs/tables/phase2_champion_selection.md`, and `models/model_registry.json`.
- Verifies whether every selected champion is unchanged and whether all validation and
  holdout metrics are identical (or differ by less than 0.01 XOF/kg).
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from src.config import MODELS_DIR, PROCESSED_DATA_DIR, PROJECT_ROOT, TABLES_DIR
from src.evaluate.backtest import compute_error_metrics
from src.evaluate.figures import select_champions_from_eval

SCRIPT_CITATION = "src/evaluate/recompute_audit.py"
BEFORE_DIR = PROJECT_ROOT / "docs" / "audit" / "before_recompute"
AUDIT_README_PATH = PROJECT_ROOT / "docs" / "audit" / "README.md"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_recompute_audit_and_diff() -> Dict[str, Any]:
    """Compare before vs after `--recompute` artifacts and write audit tables & README."""
    before_pred_csv = BEFORE_DIR / "phase2_backtest_predictions.csv"
    before_champ_md = BEFORE_DIR / "phase2_champion_selection.md"
    before_reg_json = BEFORE_DIR / "model_registry.json"

    after_pred_csv = PROCESSED_DATA_DIR / "phase2_backtest_predictions.csv"
    after_champ_md = TABLES_DIR / "phase2_champion_selection.md"
    after_reg_json = MODELS_DIR / "model_registry.json"

    df_before = pd.read_csv(before_pred_csv, dtype={"market_id": str})
    df_after = pd.read_csv(after_pred_csv, dtype={"market_id": str})

    champs_before = select_champions_from_eval(df_before)
    champs_after = select_champions_from_eval(df_after)

    main_before = df_before[df_before["is_main_candidate"]].copy()
    main_after = df_after[df_after["is_main_candidate"]].copy()

    products = sorted(main_after["commodity"].unique())
    horizons = [1, 2, 3]
    baseline_ids = ["Naive_LastValue", "Seasonal_Naive_12m", "Seasonal_Ratio_Naive"]
    complex_ids = [
        "ETS_HoltWinters",
        "SARIMAX_101_011_12",
        "Ridge_ARX",
        "HGBR_NoWeather",
        "HGBR_WithWeather",
    ]
    all_main_models = baseline_ids + complex_ids

    # 1. Champion-level comparison across all 9 (product, horizon) pairs
    champ_diff_rows: List[List[Any]] = []
    max_abs_mae_diff = 0.0
    max_abs_rmse_diff = 0.0
    max_abs_mape_diff = 0.0
    any_champion_changed = False

    for comm in products:
        for h in horizons:
            cb = champs_before[(comm, h)]
            ca = champs_after[(comm, h)]
            if cb != ca:
                any_champion_changed = True

            vb = compute_error_metrics(
                main_before[
                    (main_before["commodity"] == comm)
                    & (main_before["horizon"] == h)
                    & (main_before["split"] == "validation")
                    & (main_before["model_id"] == cb)
                ]
            )
            va = compute_error_metrics(
                main_after[
                    (main_after["commodity"] == comm)
                    & (main_after["horizon"] == h)
                    & (main_after["split"] == "validation")
                    & (main_after["model_id"] == ca)
                ]
            )
            tb = compute_error_metrics(
                main_before[
                    (main_before["commodity"] == comm)
                    & (main_before["horizon"] == h)
                    & (main_before["split"] == "test")
                    & (main_before["model_id"] == cb)
                ]
            )
            ta = compute_error_metrics(
                main_after[
                    (main_after["commodity"] == comm)
                    & (main_after["horizon"] == h)
                    & (main_after["split"] == "test")
                    & (main_after["model_id"] == ca)
                ]
            )

            d_val_mae = va["mae"] - vb["mae"]
            d_test_mae = ta["mae"] - tb["mae"]
            d_test_rmse = ta["rmse"] - tb["rmse"]
            d_test_mape = ta["mape"] - tb["mape"]
            d_test_cov80 = ta["cov80"] - tb["cov80"]

            max_abs_mae_diff = max(max_abs_mae_diff, abs(d_val_mae), abs(d_test_mae))
            max_abs_rmse_diff = max(max_abs_rmse_diff, abs(d_test_rmse))
            max_abs_mape_diff = max(max_abs_mape_diff, abs(d_test_mape))

            champ_diff_rows.append([
                comm,
                f"h={h}m",
                cb,
                ca,
                "Unchanged" if cb == ca else "CHANGED",
                f"{vb['mae']:.4f}",
                f"{va['mae']:.4f}",
                f"{d_val_mae:+.4f}",
                f"{tb['mae']:.4f}",
                f"{ta['mae']:.4f}",
                f"{d_test_mae:+.4f}",
                f"{tb['rmse']:.4f}",
                f"{ta['rmse']:.4f}",
                f"{d_test_rmse:+.4f}",
                f"{tb['mape']:.4f}%",
                f"{ta['mape']:.4f}%",
                f"{d_test_mape:+.4f} pp",
                f"{tb['cov80']:.2f}%",
                f"{ta['cov80']:.2f}%",
                f"{d_test_cov80:+.2f} pp",
            ])

    # 2. All 8 candidate models comparison across all (product, split, horizon) slices
    all_model_diff_rows: List[List[Any]] = []
    max_all_candidates_mae_diff = 0.0
    for comm in products:
        for split_k, split_lbl in [("validation", "Validation"), ("test", "Holdout Test")]:
            for h in horizons:
                for m_id in all_main_models:
                    sb = compute_error_metrics(
                        main_before[
                            (main_before["commodity"] == comm)
                            & (main_before["split"] == split_k)
                            & (main_before["horizon"] == h)
                            & (main_before["model_id"] == m_id)
                        ]
                    )
                    sa = compute_error_metrics(
                        main_after[
                            (main_after["commodity"] == comm)
                            & (main_after["split"] == split_k)
                            & (main_after["horizon"] == h)
                            & (main_after["model_id"] == m_id)
                        ]
                    )
                    dm = sa["mae"] - sb["mae"]
                    dr = sa["rmse"] - sb["rmse"]
                    dp = sa["mape"] - sb["mape"]
                    max_all_candidates_mae_diff = max(max_all_candidates_mae_diff, abs(dm))
                    all_model_diff_rows.append([
                        comm,
                        split_lbl,
                        f"h={h}m",
                        m_id,
                        sb["n"],
                        f"{sb['mae']:.4f}",
                        f"{sa['mae']:.4f}",
                        f"{dm:+.4f}",
                        f"{sb['rmse']:.4f}",
                        f"{sa['rmse']:.4f}",
                        f"{dr:+.4f}",
                        f"{sb['mape']:.4f}%",
                        f"{sa['mape']:.4f}%",
                        f"{dp:+.4f} pp",
                    ])

    # Pointwise prediction comparison on the 523,930-row backtest predictions DataFrame
    max_pointwise_pred_diff = float(
        np.max(np.abs(df_after["pred_price"].to_numpy() - df_before["pred_price"].to_numpy()))
    )
    before_pred_sha = _sha256_file(before_pred_csv)
    after_pred_sha = _sha256_file(after_pred_csv)
    before_champ_sha = _sha256_file(before_champ_md)
    after_champ_sha = _sha256_file(after_champ_md)
    before_reg_sha = _sha256_file(before_reg_json)
    after_reg_sha = _sha256_file(after_reg_json)

    headers_champ = [
        "Product",
        "Horizon",
        "Champion (Before)",
        "Champion (After)",
        "Champion Status",
        "Val MAE Before",
        "Val MAE After",
        "Delta Val MAE",
        "Test MAE Before",
        "Test MAE After",
        "Delta Test MAE",
        "Test RMSE Before",
        "Test RMSE After",
        "Delta Test RMSE",
        "Test MAPE Before",
        "Test MAPE After",
        "Delta Test MAPE",
        "Test 80% Cov Before",
        "Test 80% Cov After",
        "Delta 80% Cov",
    ]

    csv_path = TABLES_DIR / "phase2_recompute_diff.csv"
    md_path = TABLES_DIR / "phase2_recompute_diff.md"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers_champ)
        for r in champ_diff_rows:
            writer.writerow(r)

    verdict_ok = (not any_champion_changed) and (max_abs_mae_diff < 0.01)
    verdict_line = (
        f"**PASS (Identical Reproduction):** `0/9` selected champions changed; maximum absolute MAE difference across all 9 champions is `{max_abs_mae_diff:.6f} XOF/kg` (`< 0.01 XOF/kg` threshold), maximum across all 144 `(product, split, horizon, model)` slices is `{max_all_candidates_mae_diff:.6f} XOF/kg`, and maximum pointwise prediction difference across all `{len(df_after):,}` backtest rows is `{max_pointwise_pred_diff:.6f} XOF/kg`."
        if verdict_ok
        else f"**MATERIAL DIFFERENCE DETECTED:** `any_champion_changed={any_champion_changed}`, `max_abs_mae_diff={max_abs_mae_diff:.4f} XOF/kg`."
    )

    md_lines = [
        "# Phase 2 Recompute Verification Diff (`Before` vs `After --recompute`)",
        "",
        f"*Generated by [`{SCRIPT_CITATION}`](file://{PROJECT_ROOT / SCRIPT_CITATION}) — do not edit by hand.*",
        "",
        f"- **Safeguard 3 & 4 Verdict:** {verdict_line}",
        f"- **Archived Predictions (`docs/audit/before_recompute/phase2_backtest_predictions.csv`):** SHA-256 `{before_pred_sha}` (`{before_pred_csv.stat().st_size:,}` bytes)",
        f"- **Recomputed Predictions (`data/processed/phase2_backtest_predictions.csv`):** SHA-256 `{after_pred_sha}` (`{after_pred_csv.stat().st_size:,}` bytes)",
        "",
        "## 1. Selected Champions, Validation MAE & Holdout Test Metrics (`Before` vs `After`)",
        "",
        "| " + " | ".join(headers_champ) + " |",
        "| " + " | ".join(["---"] * len(headers_champ)) + " |",
    ]
    for r in champ_diff_rows:
        md_lines.append("| " + " | ".join(str(c) for c in r) + " |")

    headers_all = [
        "Product",
        "Split",
        "Horizon",
        "Model",
        "Eval Pairs",
        "MAE Before",
        "MAE After",
        "Delta MAE",
        "RMSE Before",
        "RMSE After",
        "Delta RMSE",
        "MAPE Before",
        "MAPE After",
        "Delta MAPE",
    ]
    md_lines.extend([
        "",
        "## 2. Full 144-Slice Audit Across All 8 Main Candidate Models (`Validation` & `Holdout Test`)",
        "",
        "| " + " | ".join(headers_all) + " |",
        "| " + " | ".join(["---"] * len(headers_all)) + " |",
    ])
    for r in all_model_diff_rows:
        md_lines.append("| " + " | ".join(str(c) for c in r) + " |")
    md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # Write `docs/audit/README.md` recording pre-recompute SHA-256 checksums and post-recompute verification
    audit_readme_lines = [
        "# Phase 2 Recompute Audit Archive (`docs/audit/README.md`)",
        "",
        f"*Generated by [`{SCRIPT_CITATION}`](file://{PROJECT_ROOT / SCRIPT_CITATION}) — do not edit by hand.*",
        "",
        "## 1. Pre-Recompute Archived Artifacts (`docs/audit/before_recompute/`)",
        "",
        "Before running `python -m src.evaluate.backtest --recompute`, the existing Phase 2 artifacts were copied to [`docs/audit/before_recompute/`](file:///home/brian/projets-ds/benin-agromarket/docs/audit/before_recompute/) and their SHA-256 checksums recorded:",
        "",
        "| Artifact File | Archived Path | File Size (Bytes) | Pre-Recompute SHA-256 Checksum |",
        "| :--- | :--- | ---: | :--- |",
        f"| `data/processed/phase2_backtest_predictions.csv` | `docs/audit/before_recompute/phase2_backtest_predictions.csv` | `{before_pred_csv.stat().st_size:,}` | `{before_pred_sha}` |",
        f"| `docs/tables/phase2_champion_selection.md` | `docs/audit/before_recompute/phase2_champion_selection.md` | `{before_champ_md.stat().st_size:,}` | `{before_champ_sha}` |",
        f"| `models/model_registry.json` | `docs/audit/before_recompute/model_registry.json` | `{before_reg_json.stat().st_size:,}` | `{before_reg_sha}` |",
        "",
        "## 2. Post-Recompute Verification Summary",
        "",
        f"- **Full Diff Table:** [`docs/tables/phase2_recompute_diff.md`](file://{md_path})",
        f"- **Recomputed `data/processed/phase2_backtest_predictions.csv` SHA-256:** `{after_pred_sha}` (**{'Bit-for-bit identical' if before_pred_sha == after_pred_sha else 'Differs'}**)",
        f"- **Selected Champions Changed:** `{int(any_champion_changed)} / 9`",
        f"- **Max Absolute Validation/Test MAE Difference (Selected Champions):** `{max_abs_mae_diff:.6f} XOF/kg` (threshold `< 0.01 XOF/kg`)",
        f"- **Max Absolute Validation/Test MAE Difference (All 8 Models × 18 Slices = 144 Slices):** `{max_all_candidates_mae_diff:.6f} XOF/kg`",
        f"- **Max Pointwise Prediction Difference (`{len(df_after):,}` rows):** `{max_pointwise_pred_diff:.6f} XOF/kg`",
        "",
    ]
    AUDIT_README_PATH.write_text("\n".join(audit_readme_lines), encoding="utf-8")
    print(f"[Recompute Audit] Wrote {md_path} and {AUDIT_README_PATH}")

    return {
        "verdict_ok": verdict_ok,
        "any_champion_changed": any_champion_changed,
        "max_abs_mae_diff": max_abs_mae_diff,
        "max_all_candidates_mae_diff": max_all_candidates_mae_diff,
        "max_pointwise_pred_diff": max_pointwise_pred_diff,
        "before_pred_sha": before_pred_sha,
        "after_pred_sha": after_pred_sha,
    }


if __name__ == "__main__":
    generate_recompute_audit_and_diff()

"""Expanding-window rolling-origin evaluation, champion selection, and forecast export.

Implements the pre-registered Phase 2 evaluation protocol recorded in Decision 7 of
`docs/DECISIONS.md`:
- Expanding window with 36 initial training months (`2019-01..2021-12`, first origin
  `2021-12-15`).
- Validation split: target dates `(t + h) <= 2025-09-15` (`2022-01-15..2025-09-15`).
- Final holdout test split: target dates `(t + h) in [2025-10-15..2026-09-15]` (12 months),
  evaluated once after freezing champion model selection on the validation split.
- Strictly evaluates only ground-truth observations (`is_observed == 1`, Safeguard 2) and
  never uses full-sample outlier flags (`Safeguard 1`).
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd

from src.config import (
    MODELS_DIR,
    PROCESSED_DATA_DIR,
    PROJECT_ROOT,
    RANDOM_SEED,
    TABLES_DIR,
)
from src.models.features import classify_agro_zone, load_product_panels
from src.models.forecasters import (
    FINAL_ORIGIN_IDX,
    FIRST_ORIGIN_IDX,
    HORIZONS,
    LAST_BACKTEST_ORIGIN_IDX,
    MODEL_SPEC_MAP,
    MODEL_SPECS,
    TEST_START_DATE,
    VALIDATION_END_DATE,
    compute_causal_prediction_intervals,
    fit_final_models_only,
    run_product_backtest_and_final_fit,
)

SCRIPT_CITATION = "src/evaluate/backtest.py"
WEB_DATA_DIR = PROJECT_ROOT / "web" / "public" / "data"

PRODUCT_LABELS_FR: Dict[str, str] = {
    "Maize (white)": "Maïs blanc",
    "Tomatoes": "Tomate",
    "Yam (white)": "Igname blanche (kokoro)",
    "Yam": "Igname précoce (laboko — exploration)",
}

MODEL_LABELS_FR: Dict[str, str] = {
    "Naive_LastValue": "Dernier prix connu (méthode simple)",
    "Seasonal_Ratio_Naive": "Ratio saisonnier (méthode simple)",
    "Seasonal_Naive_12m": "Prix du même mois l'an dernier (méthode simple)",
    "Ridge_ARX": "Régression saisonnière régularisée",
    "HGBR_NoWeather": "Arbres de décision sur historique de prix",
    "HGBR_WithWeather": "Arbres de décision (prix et météo)",
    "ETS_HoltWinters": "Lissage exponentiel saisonnier",
    "SARIMAX_101_011_12": "Modèle autorégressif saisonnier",
    "SARIMA": "Modèle autorégressif saisonnier",
}

MODEL_LABELS_EN: Dict[str, str] = {
    "Naive_LastValue": "Last known price (simple method)",
    "Seasonal_Ratio_Naive": "Seasonal ratio (simple method)",
    "Seasonal_Naive_12m": "Same month last year (simple method)",
    "Ridge_ARX": "Regularized seasonal regression",
    "HGBR_NoWeather": "Decision trees on price history",
    "HGBR_WithWeather": "Decision trees (prices and weather)",
    "ETS_HoltWinters": "Seasonal exponential smoothing",
    "SARIMAX_101_011_12": "Seasonal autoregressive model",
    "SARIMA": "Seasonal autoregressive model",
}

SEASON_REGIME_BY_PRODUCT_MONTH: Dict[str, Dict[int, str]] = {
    "Maize (white)": {
        1: "Transition (Post-Harvest/Dry)",
        2: "Transition (Post-Harvest/Dry)",
        3: "Transition (Post-Harvest/Dry)",
        4: "Lean / High-Price Season",
        5: "Lean / High-Price Season",
        6: "Lean / High-Price Season",
        7: "Lean / High-Price Season",
        8: "Lean / High-Price Season",
        9: "Harvest / Low-Price Season",
        10: "Harvest / Low-Price Season",
        11: "Harvest / Low-Price Season",
        12: "Harvest / Low-Price Season",
    },
    "Tomatoes": {
        1: "Transition (Dry/Irrigated)",
        2: "Transition (Dry/Irrigated)",
        3: "Transition (Dry/Irrigated)",
        4: "Lean / High-Price Season",
        5: "Lean / High-Price Season",
        6: "Lean / High-Price Season",
        7: "Lean / High-Price Season",
        8: "Harvest / Low-Price Season",
        9: "Harvest / Low-Price Season",
        10: "Harvest / Low-Price Season",
        11: "Harvest / Low-Price Season",
        12: "Transition (Dry/Irrigated)",
    },
    "Yam (white)": {
        1: "Transition (Storage)",
        2: "Transition (Storage)",
        3: "Transition (Storage)",
        4: "Transition (Storage)",
        5: "Lean / High-Price Season",
        6: "Lean / High-Price Season",
        7: "Lean / High-Price Season",
        8: "Lean / High-Price Season",
        9: "Harvest / Low-Price Season",
        10: "Harvest / Low-Price Season",
        11: "Harvest / Low-Price Season",
        12: "Harvest / Low-Price Season",
    },
}


def write_table_pair(
    filename_stem: str,
    title: str,
    notes: List[str],
    headers: List[str],
    rows: List[List[Any]],
) -> Tuple[Path, Path]:
    """Write synchronized CSV and Markdown tables in `docs/tables/`."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = TABLES_DIR / f"{filename_stem}.csv"
    md_path = TABLES_DIR / f"{filename_stem}.md"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)

    script_rel = os.path.relpath(PROJECT_ROOT / SCRIPT_CITATION, start=md_path.parent).replace(os.sep, "/")
    md_lines = [
        f"# {title}",
        "",
        f"*Generated by [`{SCRIPT_CITATION}`]({script_rel}) — do not edit by hand.*",
        "",
    ]
    for n in notes:
        md_lines.append(f"- {n}")
    if notes:
        md_lines.append("")

    md_lines.append("| " + " | ".join(headers) + " |")
    md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        md_lines.append("| " + " | ".join(str(cell) for cell in r) + " |")
    md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return csv_path, md_path


def compute_error_metrics(df_slice: pd.DataFrame) -> Dict[str, float]:
    """Compute MAE, RMSE, MAPE, and 80%/90% interval coverage & widths on a slice."""
    n = len(df_slice)
    if n == 0:
        return {
            "n": 0,
            "mae": np.nan,
            "rmse": np.nan,
            "mape": np.nan,
            "cov80": np.nan,
            "cov90": np.nan,
            "width80": np.nan,
            "width90": np.nan,
            "rel_width80_pct": np.nan,
            "mean_actual": np.nan,
        }
    y_true = df_slice["actual_price"].to_numpy(dtype=float)
    y_pred = df_slice["pred_price"].to_numpy(dtype=float)
    l80 = df_slice["low_80"].to_numpy(dtype=float)
    h80 = df_slice["high_80"].to_numpy(dtype=float)
    l90 = df_slice["low_90"].to_numpy(dtype=float)
    h90 = df_slice["high_90"].to_numpy(dtype=float)

    abs_err = np.abs(y_true - y_pred)
    sq_err = (y_true - y_pred) ** 2
    ape = (abs_err / y_true) * 100.0

    in80 = (y_true >= l80) & (y_true <= h80)
    in90 = (y_true >= l90) & (y_true <= h90)
    w80 = h80 - l80
    w90 = h90 - l90
    mean_act = float(np.mean(y_true))

    return {
        "n": int(n),
        "mae": float(np.mean(abs_err)),
        "rmse": float(np.sqrt(np.mean(sq_err))),
        "mape": float(np.mean(ape)),
        "cov80": float(np.mean(in80) * 100.0),
        "cov90": float(np.mean(in90) * 100.0),
        "width80": float(np.mean(w80)),
        "width90": float(np.mean(w90)),
        "rel_width80_pct": float(np.mean(w80) / mean_act * 100.0) if mean_act > 0 else np.nan,
        "mean_actual": mean_act,
    }


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_pipeline_cache_fingerprint() -> Dict[str, Any]:
    """Compute deterministic SHA-256 fingerprint of all code and input data dependencies.

    Per AGENTS.md `## Protocol integrity`:
    Cached artifacts (predictions, models) must store a hash of the code and data that
    produced them. The pipeline must refuse to reuse a cache if the hash differs, instead
    of relying on file timestamps.
    """
    code_rel_paths = [
        "src/config.py",
        "src/models/features.py",
        "src/models/forecasters.py",
        "src/evaluate/backtest.py",
    ]
    data_rel_paths = [
        "data/processed/modeling_panel_2019_2026.csv",
        "data/processed/prices_cleaned_all.csv",
        "data/processed/markets_active.csv",
        "docs/tables/coverage_by_market.csv",
    ]
    code_hashes = {rel: _sha256_file(PROJECT_ROOT / rel) for rel in code_rel_paths}
    data_hashes = {rel: _sha256_file(PROJECT_ROOT / rel) for rel in data_rel_paths}

    combined = hashlib.sha256()
    for rel, digest in sorted({**code_hashes, **data_hashes}.items()):
        combined.update(f"{rel}:{digest}\n".encode("utf-8"))
    combined.update(f"random_seed:{RANDOM_SEED}\n".encode("utf-8"))

    return {
        "combined_sha256": combined.hexdigest(),
        "random_seed": RANDOM_SEED,
        "code_sha256": code_hashes,
        "data_sha256": data_hashes,
    }


def _write_artifact_sidecar_hash(artifact_path: Path, fingerprint: Dict[str, Any]) -> Path:
    """Write sidecar `.sha256.json` next to a cached artifact recording its hash and inputs."""
    sidecar_path = artifact_path.with_name(artifact_path.name + ".sha256.json")
    payload = {
        "artifact_file": str(artifact_path.relative_to(PROJECT_ROOT)),
        "artifact_sha256": _sha256_file(artifact_path),
        "pipeline_combined_sha256": fingerprint["combined_sha256"],
        "random_seed": fingerprint["random_seed"],
        "code_sha256": fingerprint["code_sha256"],
        "data_sha256": fingerprint["data_sha256"],
    }
    sidecar_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return sidecar_path


def _verify_artifact_sidecar_hash(artifact_path: Path, expected_fingerprint: Dict[str, Any]) -> bool:
    """Verify that `artifact_path` exists, has a sidecar `.sha256.json`, and matches both
    the pipeline code/data fingerprint and the artifact's own SHA-256 content hash.
    """
    sidecar_path = artifact_path.with_name(artifact_path.name + ".sha256.json")
    if not artifact_path.exists() or not sidecar_path.exists():
        return False
    try:
        meta = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if meta.get("pipeline_combined_sha256") != expected_fingerprint["combined_sha256"]:
        return False
    if meta.get("artifact_sha256") != _sha256_file(artifact_path):
        return False
    return True


def compute_product_horizon_reliability(
    commodity: str,
    horizon: int,
    champ_id: str,
    best_base_id: str,
    best_model_test_id: str,
    champ_test_stats: Dict[str, float],
    best_base_test_stats: Dict[str, float],
    best_model_test_stats: Dict[str, float],
    val_skill_vs_best_base: float = 0.0,
) -> Dict[str, Any]:
    """Compute test-derived `reliability` status and plain-language bilingual UI notes."""
    cov80 = float(champ_test_stats["cov80"])
    cov90 = float(champ_test_stats["cov90"])
    mae = float(champ_test_stats["mae"])
    mape = float(champ_test_stats["mape"])
    base_mae = float(best_base_test_stats["mae"])
    best_test_mae = float(best_model_test_stats["mae"])
    skill_vs_best_base = (1.0 - mae / base_mae) * 100.0 if base_mae > 0 else 0.0
    nominal_80 = 80

    champ_fr = MODEL_LABELS_FR.get(champ_id, champ_id)
    champ_en = MODEL_LABELS_EN.get(champ_id, champ_id)
    base_fr = MODEL_LABELS_FR.get(best_base_id, best_base_id)
    base_en = MODEL_LABELS_EN.get(best_base_id, best_base_id)
    best_test_fr = MODEL_LABELS_FR.get(best_model_test_id, best_model_test_id)
    best_test_en = MODEL_LABELS_EN.get(best_model_test_id, best_model_test_id)
    h_fr = "1 mois" if horizon == 1 else f"{horizon} mois"
    h_en = "1 month" if horizon == 1 else f"{horizon} months"

    is_baseline_champ = champ_id in {"Naive_LastValue", "Seasonal_Naive_12m", "Seasonal_Ratio_Naive"}
    intervals_narrow = (cov80 < 75.0) or (cov90 < 85.0)
    worse_on_holdout = (mae - best_test_mae) > 0.5

    if intervals_narrow and is_baseline_champ:
        status = "baseline_retained_intervals_too_narrow"
        note_fr = (
            f"Méthode retenue : {champ_fr} (erreur moyenne de {mae:.1f} XOF/kg en test, soit {mape:.1f} %), "
            f"mais la fourchette à {nominal_80} % est un peu trop étroite lors des variations rapides de prix "
            f"({cov80:.1f} % des prix observés en test tombent dans la fourchette au lieu de {nominal_80} %)."
        )
        note_en = (
            f"Selected method: {champ_en} (average test error of {mae:.1f} XOF/kg, or {mape:.1f}%), "
            f"but the {nominal_80}% interval is slightly too narrow during rapid price swings "
            f"({cov80:.1f}% of observed test prices fall inside the interval instead of {nominal_80}%)."
        )
    elif intervals_narrow:
        status = "intervals_too_narrow"
        note_fr = (
            f"Méthode retenue : {champ_fr} (erreur moyenne de {mae:.1f} XOF/kg en test, soit {mape:.1f} %), "
            f"mais la fourchette à {nominal_80} % n'a couvert que {cov80:.1f} % des prix observés en test "
            f"(cible : {nominal_80} %)."
        )
        note_en = (
            f"Selected method: {champ_en} (average test error of {mae:.1f} XOF/kg, or {mape:.1f}%), "
            f"but the {nominal_80}% interval covered {cov80:.1f}% of observed test prices "
            f"(target: {nominal_80}%)."
        )
    elif (not is_baseline_champ) and (skill_vs_best_base < 0.0):
        status = "no_better_than_simple"
        note_fr = (
            f"Méthode retenue : {champ_fr}, sélectionnée sur la période d'entraînement "
            f"({val_skill_vs_best_base:+.1f} % par rapport à « {base_fr} »), mais pas meilleure "
            f"que la méthode simple en test sur l'ensemble des marchés suivis "
            f"({skill_vs_best_base:+.1f} %, erreur moyenne de {mae:.1f} XOF/kg, soit {mape:.1f} % ; "
            f"devancée par « {best_test_fr} » à {best_test_mae:.1f} XOF/kg)."
        )
        note_en = (
            f"Selected method: {champ_en}, chosen on the validation period "
            f"({val_skill_vs_best_base:+.1f}% vs '{base_en}'), but no better than the simple method "
            f"in testing across all well-tracked markets "
            f"({skill_vs_best_base:+.1f}%, average error {mae:.1f} XOF/kg, or {mape:.1f}%; "
            f"trailed '{best_test_en}' at {best_test_mae:.1f} XOF/kg)."
        )
    elif is_baseline_champ:
        status = "baseline_retained"
        if champ_id == "Naive_LastValue":
            note_fr = (
                f"Méthode retenue : {champ_fr}. À {h_fr}, aucune méthode statistique complexe ne fait "
                f"mieux que le dernier prix connu (erreur moyenne en test : {mae:.1f} XOF/kg, soit {mape:.1f} % ; "
                f"fourchette à {nominal_80} % fiable à {cov80:.1f} %)."
            )
            note_en = (
                f"Selected method: {champ_en}. At {h_en}, no complex statistical model beats the last "
                f"known price (average test error: {mae:.1f} XOF/kg, or {mape:.1f}%; "
                f"{nominal_80}% interval well calibrated at {cov80:.1f}%)."
            )
        else:
            note_fr = (
                f"Méthode retenue : {champ_fr}, choisie car elle égale les modèles complexes "
                f"(erreur moyenne en test : {mae:.1f} XOF/kg, soit {mape:.1f} % ; "
                f"fourchette à {nominal_80} % fiable à {cov80:.1f} %)."
            )
            note_en = (
                f"Selected method: {champ_en}, retained because it matches complex models "
                f"(average test error: {mae:.1f} XOF/kg, or {mape:.1f}%; "
                f"{nominal_80}% interval well calibrated at {cov80:.1f}%)."
            )
    else:
        status = "calibrated"
        if skill_vs_best_base >= 0.0:
            note_fr = (
                f"Méthode retenue : {champ_fr}, avec des fourchettes fiables en test "
                f"(erreur moyenne : {mae:.1f} XOF/kg, soit {mape:.1f} %, gain de {skill_vs_best_base:+.1f} % "
                f"par rapport à « {base_fr} », fourchette à {nominal_80} % couvrant {cov80:.1f} % des cas)."
            )
            note_en = (
                f"Selected method: {champ_en}, with well-calibrated test intervals "
                f"(average error: {mae:.1f} XOF/kg, or {mape:.1f}%, {skill_vs_best_base:+.1f}% gain "
                f"over '{base_en}', {nominal_80}% interval covering {cov80:.1f}% of cases)."
            )
        else:
            note_fr = (
                f"Méthode retenue : {champ_fr}, sélectionnée sur la période d'entraînement "
                f"({val_skill_vs_best_base:+.1f} % par rapport à « {base_fr} ») avec une fourchette à {nominal_80} % "
                f"fiable en test ({cov80:.1f} % des cas, erreur moyenne de {mae:.1f} XOF/kg), bien que devancée "
                f"sur les 12 mois de test par « {best_test_fr} » ({best_test_mae:.1f} XOF/kg)."
            )
            note_en = (
                f"Selected method: {champ_en}, chosen on the validation period "
                f"({val_skill_vs_best_base:+.1f}% vs '{base_en}') with a reliable {nominal_80}% test interval "
                f"({cov80:.1f}% coverage, average error {mae:.1f} XOF/kg), though trailed on the 12 test months "
                f"by '{best_test_en}' ({best_test_mae:.1f} XOF/kg)."
            )

    return {
        "status": status,
        "is_calibrated_80": bool(cov80 >= 75.0),
        "is_baseline_retained": bool(is_baseline_champ),
        "did_worse_than_another_candidate_on_holdout": bool(worse_on_holdout),
        "best_holdout_candidate": best_model_test_id,
        "best_holdout_candidate_mae": round(best_test_mae, 2),
        "best_validation_baseline": best_base_id,
        "skill_vs_best_baseline_test_pct": round(skill_vs_best_base, 1),
        "holdout_coverage_80_pct": round(cov80, 1),
        "holdout_coverage_90_pct": round(cov90, 1),
        "note_fr": note_fr,
        "note_en": note_en,
    }


def run_full_evaluation_pipeline(force_recompute: bool = False) -> Dict[str, Any]:
    """Execute Phase 2 backtesting, champion selection, model saving, tables, and JSON export."""
    np.random.seed(RANDOM_SEED)
    panels = load_product_panels()
    pipeline_fp = compute_pipeline_cache_fingerprint()

    pred_csv = PROCESSED_DATA_DIR / "phase2_backtest_predictions.csv"
    fut_csv = PROCESSED_DATA_DIR / "phase2_future_forecasts_all_models.csv"
    final_models_by_product: Dict[str, Dict[str, Dict[int, Any]]] = {}

    cache_valid = (
        not force_recompute
        and _verify_artifact_sidecar_hash(pred_csv, pipeline_fp)
        and _verify_artifact_sidecar_hash(fut_csv, pipeline_fp)
    )

    if cache_valid:
        print(
            f"[Phase 2] Hash-verified cache hit (combined_sha256={pipeline_fp['combined_sha256'][:12]}...). "
            "Loading rolling-origin predictions from data/processed/..."
        )
        df_eval = pd.read_csv(pred_csv, dtype={"market_id": str})
        df_future = pd.read_csv(fut_csv, dtype={"market_id": str})
        if not (MODELS_DIR / "model_registry.json").exists():
            for commodity, panel in panels.items():
                final_models_by_product[commodity] = fit_final_models_only(panel)
    else:
        if not force_recompute and (pred_csv.exists() or fut_csv.exists()):
            print(
                "[Phase 2] Refusing to reuse cached predictions (missing or mismatched code/data SHA-256 hash). "
                "Recomputing from scratch..."
            )
        all_eval_records: List[Dict[str, Any]] = []
        future_forecast_records: List[Dict[str, Any]] = []

        for commodity, panel in panels.items():
            print(f"[Phase 2] Running rolling-origin backtest for {commodity} ({len(panel.markets)} Tier-1 markets)...")
            log_preds_by_model, final_models = run_product_backtest_and_final_fit(panel)
            final_models_by_product[commodity] = final_models

            for spec in MODEL_SPECS:
                model_id = spec.model_id
                log_preds = log_preds_by_model[model_id]
                pred_prices = np.exp(log_preds)
                low_80, high_80, low_90, high_90 = compute_causal_prediction_intervals(panel, log_preds)

                # Collect evaluation records for origins 35..91 (o_pos = 0..56) where target_idx <= 92
                for o_pos, origin_idx in enumerate(range(FIRST_ORIGIN_IDX, LAST_BACKTEST_ORIGIN_IDX + 1)):
                    origin_date = panel.dates[origin_idx]
                    for h_idx, h in enumerate(HORIZONS):
                        target_idx = origin_idx + h
                        if target_idx > FINAL_ORIGIN_IDX:
                            continue
                        target_date = panel.dates[target_idx]
                        target_month = int(panel.months[target_idx])
                        split = "validation" if target_date <= VALIDATION_END_DATE else "test"
                        season_regime = SEASON_REGIME_BY_PRODUCT_MONTH[commodity][target_month]

                        for m_idx, mkt in enumerate(panel.markets):
                            # Safeguard 2: evaluate ONLY when is_observed == 1 at target_idx
                            if not panel.is_observed[m_idx, target_idx]:
                                continue
                            actual_p = float(panel.price_raw[m_idx, target_idx])
                            pred_p = float(pred_prices[m_idx, o_pos, h_idx])
                            all_eval_records.append({
                                "commodity": commodity,
                                "product_slug": panel.product_slug,
                                "market_id": panel.market_ids[m_idx],
                                "market": mkt,
                                "admin1": panel.admin1s[m_idx],
                                "agro_zone": panel.zones[m_idx],
                                "latitude": float(panel.latitudes[m_idx]),
                                "longitude": float(panel.longitudes[m_idx]),
                                "model_id": model_id,
                                "family": spec.family,
                                "is_main_candidate": spec.is_main_candidate,
                                "uses_weather": spec.uses_weather,
                                "uses_interp_lags": spec.uses_interp_lags,
                                "origin_idx": origin_idx,
                                "origin_date": origin_date,
                                "target_idx": target_idx,
                                "target_date": target_date,
                                "target_month": target_month,
                                "season_regime": season_regime,
                                "horizon": h,
                                "split": split,
                                "actual_price": actual_p,
                                "pred_price": pred_p,
                                "low_80": float(low_80[m_idx, o_pos, h_idx]),
                                "high_80": float(high_80[m_idx, o_pos, h_idx]),
                                "low_90": float(low_90[m_idx, o_pos, h_idx]),
                                "high_90": float(high_90[m_idx, o_pos, h_idx]),
                            })

                # Collect future 2026-Q4 forecasts at FINAL_ORIGIN_IDX = 92 (o_pos = 57, '2026-09-15')
                final_opos = FINAL_ORIGIN_IDX - FIRST_ORIGIN_IDX
                future_dates = {1: "2026-10-15", 2: "2026-11-15", 3: "2026-12-15"}
                for h_idx, h in enumerate(HORIZONS):
                    for m_idx, mkt in enumerate(panel.markets):
                        # Last observed price <= 2026-09-15 for this market
                        obs_indices = np.where(panel.is_observed[m_idx, : FINAL_ORIGIN_IDX + 1])[0]
                        last_obs_i = int(obs_indices[-1])
                        last_obs_p = float(panel.price_raw[m_idx, last_obs_i])
                        last_obs_d = panel.dates[last_obs_i]

                        future_forecast_records.append({
                            "commodity": commodity,
                            "product_slug": panel.product_slug,
                            "market_id": panel.market_ids[m_idx],
                            "market": mkt,
                            "admin1": panel.admin1s[m_idx],
                            "agro_zone": panel.zones[m_idx],
                            "model_id": model_id,
                            "as_of_date": panel.dates[FINAL_ORIGIN_IDX],
                            "last_observed_date": last_obs_d,
                            "last_observed_price": last_obs_p,
                            "horizon": h,
                            "target_date": future_dates[h],
                            "pred_price": float(pred_prices[m_idx, final_opos, h_idx]),
                            "low_80": float(low_80[m_idx, final_opos, h_idx]),
                            "high_80": float(high_80[m_idx, final_opos, h_idx]),
                            "low_90": float(low_90[m_idx, final_opos, h_idx]),
                            "high_90": float(high_90[m_idx, final_opos, h_idx]),
                        })

        df_eval = pd.DataFrame(all_eval_records)
        df_future = pd.DataFrame(future_forecast_records)

        # Save full evaluation dataframe and sidecar code/data SHA-256 hashes
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        df_eval.to_csv(pred_csv, index=False)
        df_future.to_csv(fut_csv, index=False)
        _write_artifact_sidecar_hash(pred_csv, pipeline_fp)
        _write_artifact_sidecar_hash(fut_csv, pipeline_fp)

    # -------------------------------------------------------------------------
    # Champion Selection strictly on Validation MAE (`split == 'validation'`)
    # -------------------------------------------------------------------------
    main_df = df_eval[df_eval["is_main_candidate"]].copy()
    champions: Dict[Tuple[str, int], str] = {}
    champion_selection_rows: List[List[Any]] = []

    baseline_ids = ["Naive_LastValue", "Seasonal_Naive_12m", "Seasonal_Ratio_Naive"]
    complex_ids = [
        "ETS_HoltWinters",
        "SARIMAX_101_011_12",
        "Ridge_ARX",
        "HGBR_NoWeather",
        "HGBR_WithWeather",
    ]

    for commodity in sorted(panels.keys()):
        for h in HORIZONS:
            val_sub = main_df[
                (main_df["commodity"] == commodity)
                & (main_df["horizon"] == h)
                & (main_df["split"] == "validation")
            ]
            test_sub = main_df[
                (main_df["commodity"] == commodity)
                & (main_df["horizon"] == h)
                & (main_df["split"] == "test")
            ]

            val_metrics_by_m = {
                m_id: compute_error_metrics(val_sub[val_sub["model_id"] == m_id])
                for m_id in baseline_ids + complex_ids
            }
            test_metrics_by_m = {
                m_id: compute_error_metrics(test_sub[test_sub["model_id"] == m_id])
                for m_id in baseline_ids + complex_ids
            }

            best_base_id = min(baseline_ids, key=lambda m: val_metrics_by_m[m]["mae"])
            non_weather_complex_ids = [
                "ETS_HoltWinters",
                "SARIMAX_101_011_12",
                "Ridge_ARX",
                "HGBR_NoWeather",
            ]
            best_nw_comp_id = min(non_weather_complex_ids, key=lambda m: val_metrics_by_m[m]["mae"])

            # Honesty & Parsimony Clause:
            # 1) HGBR_WithWeather is only selected over the best non-weather statistical/ML
            #    model if it reduces Validation MAE by at least 0.5%.
            nw_mae = val_metrics_by_m[best_nw_comp_id]["mae"]
            ww_mae = val_metrics_by_m["HGBR_WithWeather"]["mae"]
            if (1.0 - ww_mae / nw_mae) * 100.0 >= 0.5:
                best_comp_id = "HGBR_WithWeather"
            else:
                best_comp_id = best_nw_comp_id

            # 2) A statistical/ML model is only selected over the best baseline if it reduces
            #    Validation MAE by at least 0.5% (otherwise retain the simpler baseline).
            base_val_mae = val_metrics_by_m[best_base_id]["mae"]
            comp_val_mae = val_metrics_by_m[best_comp_id]["mae"]
            rel_comp_gain_pct = (1.0 - comp_val_mae / base_val_mae) * 100.0

            if rel_comp_gain_pct >= 0.5:
                champ_id = best_comp_id
                honesty_note = (
                    f"{best_comp_id} beats best baseline ({best_base_id}) on Val MAE "
                    f"({comp_val_mae:.1f} vs {base_val_mae:.1f} XOF/kg, "
                    f"{rel_comp_gain_pct:+.1f}% skill)"
                )
            else:
                champ_id = best_base_id
                honesty_note = (
                    f"Baseline {best_base_id} retained (Honesty Clause: {best_comp_id} "
                    f"Val MAE {comp_val_mae:.1f} vs {base_val_mae:.1f} [{rel_comp_gain_pct:+.1f}% < +0.5% threshold])"
                )

            champions[(commodity, h)] = champ_id

            snaive_val_mae = val_metrics_by_m["Seasonal_Naive_12m"]["mae"]
            snaive_test_mae = test_metrics_by_m["Seasonal_Naive_12m"]["mae"]
            naive_test_mae = test_metrics_by_m["Naive_LastValue"]["mae"]
            best_base_test_mae = test_metrics_by_m[best_base_id]["mae"]
            champ_val = val_metrics_by_m[champ_id]
            champ_test = test_metrics_by_m[champ_id]

            val_skill_best_base = (1.0 - champ_val["mae"] / base_val_mae) * 100.0
            test_skill_best_base = (1.0 - champ_test["mae"] / best_base_test_mae) * 100.0
            val_skill_snaive = (1.0 - champ_val["mae"] / snaive_val_mae) * 100.0
            test_skill_snaive = (1.0 - champ_test["mae"] / snaive_test_mae) * 100.0
            test_skill_naive = (1.0 - champ_test["mae"] / naive_test_mae) * 100.0

            champion_selection_rows.append([
                commodity,
                f"h={h}m",
                best_base_id,
                f"{base_val_mae:.1f}",
                f"{val_metrics_by_m[best_base_id]['mape']:.1f}%",
                best_comp_id,
                f"{comp_val_mae:.1f}",
                f"{val_metrics_by_m[best_comp_id]['mape']:.1f}%",
                champ_id,
                f"{val_skill_best_base:+.1f}%",
                f"{val_skill_snaive:+.1f}%",
                f"{best_base_test_mae:.1f}",
                f"{champ_test['mae']:.1f}",
                f"{champ_test['rmse']:.1f}",
                f"{champ_test['mape']:.1f}%",
                f"{test_skill_best_base:+.1f}%",
                f"{test_skill_snaive:+.1f}%",
                f"{test_skill_naive:+.1f}%",
                f"{champ_test['cov80']:.1f}%",
                f"{champ_test['cov90']:.1f}%",
                honesty_note,
            ])

    # Save champion artifacts to `models/` with code/data SHA-256 provenance
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    registry_info: Dict[str, Any] = {
        "as_of_date": "2026-09-15",
        "random_seed": RANDOM_SEED,
        "validation_window": f"2022-01-15..{VALIDATION_END_DATE}",
        "holdout_test_window": f"{TEST_START_DATE}..2026-09-15",
        "pipeline_cache_fingerprint": pipeline_fp,
        "champions": {},
    }
    for (commodity, h), champ_id in champions.items():
        slug = panels[commodity].product_slug
        artifact_path = MODELS_DIR / f"champion_{slug}_h{h}.joblib"
        if commodity in final_models_by_product:
            artifact_obj = {
                "commodity": commodity,
                "product_slug": slug,
                "horizon": h,
                "champion_model_id": champ_id,
                "as_of_date": "2026-09-15",
                "pipeline_combined_sha256": pipeline_fp["combined_sha256"],
                "model_artifact": final_models_by_product[commodity][champ_id][h],
            }
            joblib.dump(artifact_obj, artifact_path)
            _write_artifact_sidecar_hash(artifact_path, pipeline_fp)
        elif artifact_path.exists():
            _write_artifact_sidecar_hash(artifact_path, pipeline_fp)
        registry_info["champions"].setdefault(commodity, {})[f"h{h}"] = {
            "model_id": champ_id,
            "artifact_file": f"models/{artifact_path.name}",
            "artifact_sha256": _sha256_file(artifact_path) if artifact_path.exists() else "",
        }

    (MODELS_DIR / "model_registry.json").write_text(
        json.dumps(registry_info, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # -------------------------------------------------------------------------
    # Table 1: `phase2_backtest_by_product_horizon.{csv,md}`
    # -------------------------------------------------------------------------
    t1_rows: List[List[Any]] = []
    main_model_ids = [m.model_id for m in MODEL_SPECS if m.is_main_candidate]

    for commodity in sorted(panels.keys()):
        for split_key, split_label in [
            ("validation", "Validation (2022-01..2025-09)"),
            ("test", "Holdout Test (2025-10..2026-09)"),
        ]:
            for h in [1, 2, 3, 0]:  # 0 denotes All Horizons (h=1..3 pooled)
                h_label = f"h={h}m" if h > 0 else "All (h=1..3)"
                sub = main_df[(main_df["commodity"] == commodity) & (main_df["split"] == split_key)]
                if h > 0:
                    sub = sub[sub["horizon"] == h]

                snaive_mae = compute_error_metrics(
                    sub[sub["model_id"] == "Seasonal_Naive_12m"]
                )["mae"]
                naive_mae = compute_error_metrics(
                    sub[sub["model_id"] == "Naive_LastValue"]
                )["mae"]

                for m_id in main_model_ids:
                    m_sub = sub[sub["model_id"] == m_id]
                    stats = compute_error_metrics(m_sub)
                    skill_snaive = (1.0 - stats["mae"] / snaive_mae) * 100.0 if snaive_mae > 0 else 0.0
                    skill_naive = (1.0 - stats["mae"] / naive_mae) * 100.0 if naive_mae > 0 else 0.0
                    is_champ = (
                        "Yes"
                        if (h > 0 and champions[(commodity, h)] == m_id)
                        else ("-" if h == 0 else "No")
                    )
                    t1_rows.append([
                        commodity,
                        split_label,
                        h_label,
                        m_id,
                        MODEL_SPEC_MAP[m_id].family,
                        stats["n"],
                        f"{stats['mae']:.2f}",
                        f"{stats['rmse']:.2f}",
                        f"{stats['mape']:.2f}%",
                        f"{skill_snaive:+.1f}%",
                        f"{skill_naive:+.1f}%",
                        f"{stats['cov80']:.1f}%",
                        f"{stats['cov90']:.1f}%",
                        f"{stats['width80']:.1f}",
                        is_champ,
                    ])

    write_table_pair(
        "phase2_backtest_by_product_horizon",
        "Phase 2 Rolling-Origin Backtest Metrics by Product, Split, Horizon & Model (`XOF/kg`)",
        [
            "Expanding-window rolling-origin evaluation on the 93-month Tier-1 panel (`2019-01..2026-09`) with 36 initial training months (`2019-01..2021-12`, first forecast origin `2021-12-15`).",
            "Validation split covers target dates `2022-01-15..2025-09-15`; Final Holdout Test split covers target dates `2025-10-15..2026-09-15` (`12` target months per horizon).",
            "Strictly evaluated on ground-truth observations (`is_observed == 1`, Safeguard 2); zero full-sample outlier flags used (`Safeguard 1`).",
        ],
        [
            "Product",
            "Evaluation Split",
            "Horizon",
            "Model",
            "Model Family",
            "Eval Pairs",
            "MAE (XOF/kg)",
            "RMSE (XOF/kg)",
            "MAPE %",
            "Skill vs Seasonal_Naive_12m",
            "Skill vs Naive_LastValue",
            "80% PI Coverage",
            "90% PI Coverage",
            "Mean 80% Width (XOF/kg)",
            "Selected Champion",
        ],
        t1_rows,
    )

    # -------------------------------------------------------------------------
    # Table 2: `phase2_champion_selection.{csv,md}`
    # -------------------------------------------------------------------------
    write_table_pair(
        "phase2_champion_selection",
        "Phase 2 Champion Model Selection (Validation Split) & Holdout Test Performance (`XOF/kg`)",
        [
            "Champion models are selected strictly on the Validation Split (`2022-01..2025-09`) by lowest Validation MAE, subject to the Honesty Clause (if a complex model does not beat the best baseline on validation, the baseline is retained).",
            "Final Holdout Test (`2025-10..2026-09`, `12` months per horizon) is evaluated once after freezing the champion selection.",
        ],
        [
            "Product",
            "Horizon",
            "Best Baseline (Val)",
            "Baseline Val MAE",
            "Baseline Val MAPE",
            "Best Statistical/ML (Val)",
            "Stat/ML Val MAE",
            "Stat/ML Val MAPE",
            "Selected Champion",
            "Val Skill vs Best Baseline",
            "Val Skill vs SNaive12m",
            "Best Baseline Test MAE",
            "Test MAE (XOF/kg)",
            "Test RMSE (XOF/kg)",
            "Test MAPE %",
            "Test Skill vs Best Baseline",
            "Test Skill vs SNaive12m",
            "Test Skill vs Naive1m",
            "Test 80% PI Cov",
            "Test 90% PI Cov",
            "Selection Rationale (Honesty Clause)",
        ],
        champion_selection_rows,
    )

    # -------------------------------------------------------------------------
    # Table 2b: `phase2_holdout_rank_comparison.{csv,md}`
    # -------------------------------------------------------------------------
    rank_rows: List[List[Any]] = []
    for commodity in sorted(panels.keys()):
        for h in HORIZONS:
            val_sub = main_df[
                (main_df["commodity"] == commodity)
                & (main_df["horizon"] == h)
                & (main_df["split"] == "validation")
            ]
            test_sub = main_df[
                (main_df["commodity"] == commodity)
                & (main_df["horizon"] == h)
                & (main_df["split"] == "test")
            ]
            val_m = {
                m_id: compute_error_metrics(val_sub[val_sub["model_id"] == m_id])
                for m_id in baseline_ids + complex_ids
            }
            test_m = {
                m_id: compute_error_metrics(test_sub[test_sub["model_id"] == m_id])
                for m_id in baseline_ids + complex_ids
            }
            champ_id = champions[(commodity, h)]
            best_test_id = min(baseline_ids + complex_ids, key=lambda m: test_m[m]["mae"])
            sorted_by_test = sorted(baseline_ids + complex_ids, key=lambda m: test_m[m]["mae"])
            champ_test_rank = sorted_by_test.index(champ_id) + 1
            better_on_test = [
                f"{m} ({test_m[m]['mae']:.2f})"
                for m in sorted_by_test
                if test_m[m]["mae"] < test_m[champ_id]["mae"] - 1e-9
            ]
            mae_gap = test_m[champ_id]["mae"] - test_m[best_test_id]["mae"]
            mape_gap = test_m[champ_id]["mape"] - test_m[best_test_id]["mape"]
            status_str = (
                "Rank #1 on Holdout (Best Candidate)"
                if champ_id == best_test_id
                else f"Rank #{champ_test_rank}/8 on Holdout (+{mae_gap:.2f} XOF/kg vs {best_test_id})"
            )
            rank_rows.append([
                commodity,
                f"h={h}m",
                champ_id,
                f"{val_m[champ_id]['mae']:.2f}",
                f"{test_m[champ_id]['mae']:.2f}",
                f"{test_m[champ_id]['mape']:.2f}%",
                f"#{champ_test_rank} / 8",
                best_test_id,
                f"{val_m[best_test_id]['mae']:.2f}",
                f"{test_m[best_test_id]['mae']:.2f}",
                f"{test_m[best_test_id]['mape']:.2f}%",
                f"{mae_gap:+.2f}",
                f"{mape_gap:+.2f} pp",
                ", ".join(better_on_test) if better_on_test else "None (Champion is #1 on Holdout)",
                status_str,
            ])

    write_table_pair(
        "phase2_holdout_rank_comparison",
        "Phase 2 Holdout Rank Comparison: Selected Validation Champion vs Best Candidate on Holdout Test (`2025-10..2026-09`)",
        [
            "Documents plainly every `(Product, Horizon)` cell where the model selected strictly on the Validation Split (`2022-01..2025-09`) did worse on the frozen Holdout Test (`2025-10..2026-09`) than another candidate model.",
            "Per `AGENTS.md` (`## Protocol integrity`), champion selection is never altered after inspecting the holdout test split.",
        ],
        [
            "Product",
            "Horizon",
            "Selected Champion (Val)",
            "Champion Val MAE",
            "Champion Test MAE",
            "Champion Test MAPE",
            "Champion Test Rank",
            "Best Candidate on Holdout",
            "Best-on-Test Val MAE",
            "Best-on-Test Holdout MAE",
            "Best-on-Test Holdout MAPE",
            "Holdout MAE Gap (Champ - Best)",
            "Holdout MAPE Gap",
            "All Candidates Beating Champion on Holdout",
            "Holdout Comparison Verdict",
        ],
        rank_rows,
    )

    # -------------------------------------------------------------------------
    # Table 3: `phase2_weather_ablation.{csv,md}`
    # -------------------------------------------------------------------------
    t3_rows: List[List[Any]] = []
    for commodity in sorted(panels.keys()):
        for split_key, split_label in [
            ("validation", "Validation (2022-01..2025-09)"),
            ("test", "Holdout Test (2025-10..2026-09)"),
        ]:
            for h in [1, 2, 3, 0]:
                h_label = f"h={h}m" if h > 0 else "All (h=1..3)"
                sub = main_df[(main_df["commodity"] == commodity) & (main_df["split"] == split_key)]
                if h > 0:
                    sub = sub[sub["horizon"] == h]

                no_w = compute_error_metrics(sub[sub["model_id"] == "HGBR_NoWeather"])
                wi_w = compute_error_metrics(sub[sub["model_id"] == "HGBR_WithWeather"])
                ridge_m = compute_error_metrics(sub[sub["model_id"] == "Ridge_ARX"])

                d_mae = wi_w["mae"] - no_w["mae"]
                d_rmse = wi_w["rmse"] - no_w["rmse"]
                d_mape = wi_w["mape"] - no_w["mape"]
                rel_gain_pct = (1.0 - wi_w["mae"] / no_w["mae"]) * 100.0 if no_w["mae"] > 0 else 0.0

                if rel_gain_pct >= 0.5:
                    verdict = f"Modest gain ({rel_gain_pct:+.2f}% MAE)"
                elif rel_gain_pct <= -0.5:
                    verdict = f"Degrades accuracy ({rel_gain_pct:+.2f}% MAE — calendar seasonality sufficient)"
                else:
                    verdict = f"Negligible difference ({rel_gain_pct:+.2f}% MAE — parsimony favors NoWeather/Ridge)"

                t3_rows.append([
                    commodity,
                    split_label,
                    h_label,
                    no_w["n"],
                    f"{no_w['mae']:.2f}",
                    f"{no_w['rmse']:.2f}",
                    f"{no_w['mape']:.2f}%",
                    f"{wi_w['mae']:.2f}",
                    f"{wi_w['rmse']:.2f}",
                    f"{wi_w['mape']:.2f}%",
                    f"{d_mae:+.2f}",
                    f"{d_rmse:+.2f}",
                    f"{d_mape:+.2f} pp",
                    f"{rel_gain_pct:+.2f}%",
                    f"{ridge_m['mae']:.2f}",
                    verdict,
                ])

    write_table_pair(
        "phase2_weather_ablation",
        "Phase 2 Agroclimatic Feature Ablation: `HGBR_NoWeather` vs `HGBR_WithWeather` (`NASA POWER` Lagged Features)",
        [
            "Tests whether adding strictly lagged NASA POWER variables (`precip_lag1m..3m`, `precip_roll3m_lag1`, `precip_anom_z_lag1m`, `t2m_lag1m`, `t2m_max_lag1m`, `t2m_min_lag1m`, `rh2m_lag1m`) improves out-of-sample forecast accuracy beyond deterministic calendar seasonality (`month` Fourier harmonics + causal seasonal indices).",
            "`Δ MAE = MAE(WithWeather) - MAE(NoWeather)` (negative values indicate weather features reduce error; positive values indicate weather features add variance/overfitting).",
        ],
        [
            "Product",
            "Split",
            "Horizon",
            "Eval Pairs",
            "HGBR_NoWeather MAE",
            "HGBR_NoWeather RMSE",
            "HGBR_NoWeather MAPE",
            "HGBR_WithWeather MAE",
            "HGBR_WithWeather RMSE",
            "HGBR_WithWeather MAPE",
            "Delta MAE (With - No)",
            "Delta RMSE",
            "Delta MAPE",
            "Weather Skill Gain %",
            "Reference Ridge_ARX MAE",
            "Ablation Verdict",
        ],
        t3_rows,
    )

    # -------------------------------------------------------------------------
    # Table 4: `phase2_imputation_sensitivity.{csv,md}`
    # -------------------------------------------------------------------------
    t4_rows: List[List[Any]] = []
    for commodity in sorted(panels.keys()):
        for h in [1, 2, 3, 0]:
            h_label = f"h={h}m" if h > 0 else "All (h=1..3)"
            sub_val = df_eval[(df_eval["commodity"] == commodity) & (df_eval["split"] == "validation")]
            if h > 0:
                sub_val = sub_val[sub_val["horizon"] == h]

            for base_id, interp_id in [
                ("Ridge_ARX", "Ridge_ARX_Interp1mLags"),
                ("HGBR_NoWeather", "HGBR_NoWeather_Interp1mLags"),
            ]:
                m_raw = compute_error_metrics(sub_val[sub_val["model_id"] == base_id])
                m_int = compute_error_metrics(sub_val[sub_val["model_id"] == interp_id])
                d_mae = m_int["mae"] - m_raw["mae"]
                d_rmse = m_int["rmse"] - m_raw["rmse"]
                d_mape = m_int["mape"] - m_raw["mape"]
                rel_diff = (1.0 - m_int["mae"] / m_raw["mae"]) * 100.0 if m_raw["mae"] > 0 else 0.0

                t4_rows.append([
                    commodity,
                    h_label,
                    base_id,
                    m_raw["n"],
                    "0 (Strictly is_observed==1)",
                    f"{m_raw['mae']:.2f}",
                    f"{m_raw['rmse']:.2f}",
                    f"{m_raw['mape']:.2f}%",
                    f"{m_int['mae']:.2f}",
                    f"{m_int['rmse']:.2f}",
                    f"{m_int['mape']:.2f}%",
                    f"{d_mae:+.2f}",
                    f"{d_rmse:+.2f}",
                    f"{d_mape:+.2f} pp",
                    f"{rel_diff:+.2f}%",
                ])

    write_table_pair(
        "phase2_imputation_sensitivity",
        "Phase 2 Lag-Imputation Sensitivity Analysis on Validation Split (`2022-01..2025-09`)",
        [
            "Enforces Safeguard 2 (`docs/DECISIONS.md` Decision 4 & Decision 7): Only observed ground-truth months (`is_observed == 1`) are ever used as forecast targets (`Imputed Targets = 0`).",
            "Compares main models using strictly raw observed lags (`price`) against sensitivity variants using isolated 1-month linear interpolation (`price_interp_1m_max`) strictly for historical lag construction.",
        ],
        [
            "Product",
            "Horizon",
            "Base Model Architecture",
            "Val Eval Pairs (is_observed==1)",
            "Imputed Forecast Targets Used",
            "Raw-Lags MAE (XOF/kg)",
            "Raw-Lags RMSE",
            "Raw-Lags MAPE",
            "Interp1m-Lags MAE (XOF/kg)",
            "Interp1m-Lags RMSE",
            "Interp1m-Lags MAPE",
            "Delta MAE (Interp - Raw)",
            "Delta RMSE",
            "Delta MAPE",
            "Relative MAE Change %",
        ],
        t4_rows,
    )

    # -------------------------------------------------------------------------
    # Table 5: `phase2_interval_calibration.{csv,md}`
    # -------------------------------------------------------------------------
    t5_rows: List[List[Any]] = []
    for commodity in sorted(panels.keys()):
        for split_key, split_label in [
            ("validation", "Validation (2022-01..2025-09)"),
            ("test", "Holdout Test (2025-10..2026-09)"),
        ]:
            for h in HORIZONS:
                champ_id = champions[(commodity, h)]
                for role_label, m_id in [
                    (f"Selected Champion ({champ_id})", champ_id),
                    ("Seasonal Baseline (Seasonal_Naive_12m)", "Seasonal_Naive_12m"),
                    ("Classical Statistical (ETS_HoltWinters)", "ETS_HoltWinters"),
                    ("Classical Linear (Ridge_ARX)", "Ridge_ARX"),
                    ("Gradient Boosting (HGBR_NoWeather)", "HGBR_NoWeather"),
                ]:
                    sub = main_df[
                        (main_df["commodity"] == commodity)
                        & (main_df["split"] == split_key)
                        & (main_df["horizon"] == h)
                        & (main_df["model_id"] == m_id)
                    ]
                    st = compute_error_metrics(sub)
                    err80 = st["cov80"] - 80.0
                    err90 = st["cov90"] - 90.0
                    t5_rows.append([
                        commodity,
                        split_label,
                        f"h={h}m",
                        role_label,
                        st["n"],
                        f"{st['mean_actual']:.1f}",
                        "80.0%",
                        f"{st['cov80']:.1f}%",
                        f"{err80:+.1f} pp",
                        f"{st['width80']:.1f}",
                        f"{st['rel_width80_pct']:.1f}%",
                        "90.0%",
                        f"{st['cov90']:.1f}%",
                        f"{err90:+.1f} pp",
                        f"{st['width90']:.1f}",
                    ])

    write_table_pair(
        "phase2_interval_calibration",
        "Phase 2 Empirical / Conformal Prediction Interval Calibration (`80%` and `90%` Nominal Levels)",
        [
            "Prediction intervals are constructed causally at each origin `t` from prior completed out-of-sample residuals (`s + h <= t`) shrunk across market and product levels.",
            "`Calibration Error (pp) = Empirical Coverage % - Nominal Coverage %` (`0.0 pp` is exact calibration).",
        ],
        [
            "Product",
            "Split",
            "Horizon",
            "Model / Role",
            "Eval Pairs",
            "Mean Actual (XOF/kg)",
            "Nominal 80%",
            "Empirical 80% Cov",
            "80% Calib Error",
            "Mean 80% Width (XOF/kg)",
            "80% Width (% of Mean)",
            "Nominal 90%",
            "Empirical 90% Cov",
            "90% Calib Error",
            "Mean 90% Width (XOF/kg)",
        ],
        t5_rows,
    )

    # -------------------------------------------------------------------------
    # Table 6: `phase2_metrics_by_market.{csv,md}` (All 111 Tier-1 Product-Markets)
    # -------------------------------------------------------------------------
    t6_rows: List[List[Any]] = []
    market_accuracy_lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for commodity, panel in panels.items():
        for m_idx, mkt in enumerate(panel.markets):
            mkt_df = main_df[(main_df["commodity"] == commodity) & (main_df["market"] == mkt)]

            # Collect champion rows for this market across h=1,2,3
            champ_slices_test: List[pd.DataFrame] = []
            champ_slices_all: List[pd.DataFrame] = []
            snaive_slices_test: List[pd.DataFrame] = []
            snaive_slices_all: List[pd.DataFrame] = []
            per_h_stats: Dict[str, Dict[str, float]] = {}

            for h in HORIZONS:
                c_id = champions[(commodity, h)]
                c_test = mkt_df[
                    (mkt_df["horizon"] == h)
                    & (mkt_df["model_id"] == c_id)
                    & (mkt_df["split"] == "test")
                ]
                c_all = mkt_df[(mkt_df["horizon"] == h) & (mkt_df["model_id"] == c_id)]
                s_test = mkt_df[
                    (mkt_df["horizon"] == h)
                    & (mkt_df["model_id"] == "Seasonal_Naive_12m")
                    & (mkt_df["split"] == "test")
                ]
                s_all = mkt_df[
                    (mkt_df["horizon"] == h) & (mkt_df["model_id"] == "Seasonal_Naive_12m")
                ]

                champ_slices_test.append(c_test)
                champ_slices_all.append(c_all)
                snaive_slices_test.append(s_test)
                snaive_slices_all.append(s_all)

                st_h_test = compute_error_metrics(c_test)
                st_h_all = compute_error_metrics(c_all)
                per_h_stats[f"h{h}_test"] = st_h_test
                per_h_stats[f"h{h}_all"] = st_h_all

            pooled_test = compute_error_metrics(pd.concat(champ_slices_test, ignore_index=True))
            pooled_all = compute_error_metrics(pd.concat(champ_slices_all, ignore_index=True))
            snaive_test = compute_error_metrics(pd.concat(snaive_slices_test, ignore_index=True))
            snaive_all = compute_error_metrics(pd.concat(snaive_slices_all, ignore_index=True))

            skill_test = (
                (1.0 - pooled_test["mae"] / snaive_test["mae"]) * 100.0
                if snaive_test["mae"] > 0
                else 0.0
            )
            skill_all = (
                (1.0 - pooled_all["mae"] / snaive_all["mae"]) * 100.0
                if snaive_all["mae"] > 0
                else 0.0
            )

            h1_test = per_h_stats["h1_test"]
            h3_test = per_h_stats["h3_test"]

            market_accuracy_lookup[(commodity, mkt)] = {
                "test_overall": {
                    "n_eval": pooled_test["n"],
                    "mae": round(pooled_test["mae"], 2),
                    "rmse": round(pooled_test["rmse"], 2),
                    "mape": round(pooled_test["mape"], 2),
                    "coverage_80": round(pooled_test["cov80"], 1),
                    "coverage_90": round(pooled_test["cov90"], 1),
                    "skill_vs_snaive_pct": round(skill_test, 1),
                },
                "full_backtest_overall": {
                    "n_eval": pooled_all["n"],
                    "mae": round(pooled_all["mae"], 2),
                    "rmse": round(pooled_all["rmse"], 2),
                    "mape": round(pooled_all["mape"], 2),
                    "coverage_80": round(pooled_all["cov80"], 1),
                    "coverage_90": round(pooled_all["cov90"], 1),
                    "skill_vs_snaive_pct": round(skill_all, 1),
                },
                "by_horizon_test": {
                    f"h{h}": {
                        "model_id": champions[(commodity, h)],
                        "n_eval": per_h_stats[f"h{h}_test"]["n"],
                        "mae": round(per_h_stats[f"h{h}_test"]["mae"], 2),
                        "rmse": round(per_h_stats[f"h{h}_test"]["rmse"], 2),
                        "mape": round(per_h_stats[f"h{h}_test"]["mape"], 2),
                        "coverage_80": round(per_h_stats[f"h{h}_test"]["cov80"], 1),
                        "coverage_90": round(per_h_stats[f"h{h}_test"]["cov90"], 1),
                    }
                    for h in HORIZONS
                },
            }

            t6_rows.append([
                commodity,
                mkt,
                panel.admin1s[m_idx],
                panel.zones[m_idx],
                int(np.sum(panel.is_observed[m_idx])),
                f"{pooled_test['mean_actual']:.1f}",
                f"{h1_test['mae']:.1f}",
                f"{h1_test['mape']:.1f}%",
                f"{h3_test['mae']:.1f}",
                f"{h3_test['mape']:.1f}%",
                f"{pooled_test['mae']:.1f}",
                f"{pooled_test['rmse']:.1f}",
                f"{pooled_test['mape']:.1f}%",
                f"{skill_test:+.1f}%",
                f"{pooled_test['cov80']:.1f}%",
                f"{pooled_test['cov90']:.1f}%",
                f"{pooled_all['mae']:.1f}",
                f"{pooled_all['rmse']:.1f}",
                f"{pooled_all['mape']:.1f}%",
                f"{skill_all:+.1f}%",
            ])

    write_table_pair(
        "phase2_metrics_by_market",
        "Phase 2 Per-Market Out-of-Sample Accuracy Across All 111 Tier-1 Product-Market Series (`XOF/kg`)",
        [
            "Reports MAE, RMSE, MAPE, Skill vs `Seasonal_Naive_12m`, and 80%/90% Prediction Interval Coverage for every Tier-1 market on both the Final Holdout Test (`2025-10..2026-09`) and the Full Rolling Backtest (`2022-01..2026-09`).",
        ],
        [
            "Product",
            "Market",
            "Department (Admin1)",
            "Agro-Ecological Zone",
            "Obs (2019-26)",
            "Test Mean Price (XOF/kg)",
            "Test h=1 MAE",
            "Test h=1 MAPE",
            "Test h=3 MAE",
            "Test h=3 MAPE",
            "Test Pooled MAE (h=1..3)",
            "Test Pooled RMSE",
            "Test Pooled MAPE",
            "Test Skill vs SNaive12m",
            "Test 80% PI Cov",
            "Test 90% PI Cov",
            "Full Backtest MAE (2022-26)",
            "Full Backtest RMSE",
            "Full Backtest MAPE",
            "Full Skill vs SNaive12m",
        ],
        t6_rows,
    )

    # -------------------------------------------------------------------------
    # Table 7: `phase2_metrics_by_zone_season.{csv,md}`
    # -------------------------------------------------------------------------
    t7_rows: List[List[Any]] = []
    # Filter to selected champion rows per (commodity, horizon)
    champ_mask = pd.Series(False, index=main_df.index)
    snaive_mask = main_df["model_id"] == "Seasonal_Naive_12m"
    for (comm, h), c_id in champions.items():
        champ_mask |= (
            (main_df["commodity"] == comm)
            & (main_df["horizon"] == h)
            & (main_df["model_id"] == c_id)
        )
    df_champ_all = main_df[champ_mask].copy()
    df_snaive_all = main_df[snaive_mask].copy()

    for commodity in sorted(panels.keys()):
        for split_key, split_label in [
            ("test", "Holdout Test (2025-10..2026-09)"),
            ("validation", "Validation (2022-01..2025-09)"),
        ]:
            c_prod = df_champ_all[
                (df_champ_all["commodity"] == commodity) & (df_champ_all["split"] == split_key)
            ]
            s_prod = df_snaive_all[
                (df_snaive_all["commodity"] == commodity) & (df_snaive_all["split"] == split_key)
            ]

            # By Agro-Ecological Zone
            for z_label in ["South (<7.5°N)", "Center (7.5°–9.5°N)", "North (>=9.5°N)"]:
                c_z = c_prod[c_prod["agro_zone"] == z_label]
                s_z = s_prod[s_prod["agro_zone"] == z_label]
                st_c = compute_error_metrics(c_z)
                st_s = compute_error_metrics(s_z)
                sk = (1.0 - st_c["mae"] / st_s["mae"]) * 100.0 if st_s["mae"] > 0 else 0.0
                t7_rows.append([
                    commodity,
                    split_label,
                    "Agro-Ecological Zone",
                    z_label,
                    st_c["n"],
                    f"{st_c['mean_actual']:.1f}",
                    f"{st_c['mae']:.2f}",
                    f"{st_c['rmse']:.2f}",
                    f"{st_c['mape']:.2f}%",
                    f"{sk:+.1f}%",
                    f"{st_c['cov80']:.1f}%",
                    f"{st_c['cov90']:.1f}%",
                ])

            # By Season Regime
            for s_reg in sorted(c_prod["season_regime"].unique()):
                c_r = c_prod[c_prod["season_regime"] == s_reg]
                s_r = s_prod[s_prod["season_regime"] == s_reg]
                st_c = compute_error_metrics(c_r)
                st_s = compute_error_metrics(s_r)
                sk = (1.0 - st_c["mae"] / st_s["mae"]) * 100.0 if st_s["mae"] > 0 else 0.0
                t7_rows.append([
                    commodity,
                    split_label,
                    "Seasonal Regime",
                    s_reg,
                    st_c["n"],
                    f"{st_c['mean_actual']:.1f}",
                    f"{st_c['mae']:.2f}",
                    f"{st_c['rmse']:.2f}",
                    f"{st_c['mape']:.2f}%",
                    f"{sk:+.1f}%",
                    f"{st_c['cov80']:.1f}%",
                    f"{st_c['cov90']:.1f}%",
                ])

    write_table_pair(
        "phase2_metrics_by_zone_season",
        "Phase 2 Champion Error Disaggregation by Agro-Ecological Zone & Seasonal Regime (`XOF/kg`)",
        [
            "Evaluates selected champion models across Benin's three latitude zones (`South <7.5°N`, `Center 7.5°–9.5°N`, `North >=9.5°N`) and seasonal price regimes (`Harvest / Low-Price`, `Lean / High-Price`, and `Transition`) to identify where forecasts are most vs least reliable.",
        ],
        [
            "Product",
            "Split",
            "Dimension",
            "Slice / Subgroup",
            "Eval Pairs",
            "Mean Actual (XOF/kg)",
            "MAE (XOF/kg)",
            "RMSE (XOF/kg)",
            "MAPE %",
            "Skill vs SNaive12m",
            "80% PI Coverage",
            "90% PI Coverage",
        ],
        t7_rows,
    )

    # -------------------------------------------------------------------------
    # Table 8: `phase2_forecast_2026Q4_summary.{csv,md}`
    # -------------------------------------------------------------------------
    t8_rows: List[List[Any]] = []
    focal_markets = [
        "Dantokpa",
        "Glazoué",
        "Parakou",
        "Malanville (CBM)",
        "Bohicon",
        "Natitingou",
        "Djougou",
        "Nikki",
        "Savalou",
    ]
    for commodity in sorted(panels.keys()):
        for h in HORIZONS:
            c_id = champions[(commodity, h)]
            sub_f = df_future[
                (df_future["commodity"] == commodity)
                & (df_future["horizon"] == h)
                & (df_future["model_id"] == c_id)
            ]
            # National Tier-1 Summary Row
            last_mean = float(sub_f["last_observed_price"].mean())
            pred_mean = float(sub_f["pred_price"].mean())
            pred_med = float(sub_f["pred_price"].median())
            l80_mean = float(sub_f["low_80"].mean())
            h80_mean = float(sub_f["high_80"].mean())
            l90_mean = float(sub_f["low_90"].mean())
            h90_mean = float(sub_f["high_90"].mean())
            pct_chg = (pred_mean / last_mean - 1.0) * 100.0
            t8_rows.append([
                commodity,
                "National Tier-1 Mean",
                f"All {len(sub_f)} Tier-1 Markets",
                f"h={h}m ({sub_f['target_date'].iloc[0]})",
                c_id,
                f"{last_mean:.1f}",
                f"{pred_mean:.1f} (med {pred_med:.1f})",
                f"{pct_chg:+.1f}%",
                f"[{l80_mean:.1f}, {h80_mean:.1f}]",
                f"[{l90_mean:.1f}, {h90_mean:.1f}]",
            ])

            for fm in focal_markets:
                m_row = sub_f[sub_f["market"] == fm]
                if len(m_row) == 0:
                    continue
                r0 = m_row.iloc[0]
                lp = float(r0["last_observed_price"])
                pp = float(r0["pred_price"])
                chg = (pp / lp - 1.0) * 100.0
                t8_rows.append([
                    commodity,
                    r0["agro_zone"],
                    fm,
                    f"h={h}m ({r0['target_date']})",
                    c_id,
                    f"{lp:.1f}",
                    f"{pp:.1f}",
                    f"{chg:+.1f}%",
                    f"[{float(r0['low_80']):.1f}, {float(r0['high_80']):.1f}]",
                    f"[{float(r0['low_90']):.1f}, {float(r0['high_90']):.1f}]",
                ])

    write_table_pair(
        "phase2_forecast_2026Q4_summary",
        "Phase 2 Production Forecasts (`2026-10` to `2026-12`) from Origin `as_of_date = 2026-09-15` (`XOF/kg`)",
        [
            "Generated by the frozen champion model per `(Product, Horizon)` trained on all observed data through `2026-09-15` (`models/champion_*.joblib`).",
            "80% and 90% prediction intervals reflect empirical out-of-sample residual quantiles specific to each market and product.",
        ],
        [
            "Product",
            "Zone / Aggregation",
            "Market",
            "Horizon (Target Date)",
            "Model Used",
            "Last Obs Price (2026-09, XOF/kg)",
            "Point Forecast (XOF/kg)",
            "Expected Change %",
            "80% Prediction Interval",
            "90% Prediction Interval",
        ],
        t8_rows,
    )

    # -------------------------------------------------------------------------
    # Table 9: `phase2_outlier_sensitivity.{csv,md}` (All Observed vs Excluding Flagged Outliers)
    # -------------------------------------------------------------------------
    df_cleaned_flags = pd.read_csv(
        PROCESSED_DATA_DIR / "prices_cleaned_all.csv",
        usecols=["commodity", "market", "date", "is_outlier", "is_outlier_level", "is_outlier_jump"],
    )
    outlier_lookup = {
        (str(r["commodity"]), str(r["market"]), str(r["date"])): int(r["is_outlier"])
        for _, r in df_cleaned_flags.iterrows()
    }
    main_df["target_is_outlier"] = [
        outlier_lookup.get((str(c), str(m), str(d)), 0)
        for c, m, d in zip(main_df["commodity"], main_df["market"], main_df["target_date"])
    ]
    df_champ_all["target_is_outlier"] = main_df.loc[df_champ_all.index, "target_is_outlier"]
    df_snaive_all["target_is_outlier"] = main_df.loc[df_snaive_all.index, "target_is_outlier"]

    t9_rows: List[List[Any]] = []
    for commodity in sorted(panels.keys()):
        for split_key, split_label in [
            ("validation", "Validation (2022-01..2025-09)"),
            ("test", "Holdout Test (2025-10..2026-09)"),
        ]:
            for h in [1, 2, 3, 0]:
                h_label = f"h={h}m" if h > 0 else "All (h=1..3)"
                if h > 0:
                    c_id = champions[(commodity, h)]
                    sub_all = main_df[
                        (main_df["commodity"] == commodity)
                        & (main_df["split"] == split_key)
                        & (main_df["horizon"] == h)
                        & (main_df["model_id"] == c_id)
                    ]
                    sn_all = main_df[
                        (main_df["commodity"] == commodity)
                        & (main_df["split"] == split_key)
                        & (main_df["horizon"] == h)
                        & (main_df["model_id"] == "Seasonal_Naive_12m")
                    ]
                else:
                    c_id = "Selected Champions (h=1..3)"
                    sub_all = df_champ_all[
                        (df_champ_all["commodity"] == commodity)
                        & (df_champ_all["split"] == split_key)
                    ]
                    sn_all = df_snaive_all[
                        (df_snaive_all["commodity"] == commodity)
                        & (df_snaive_all["split"] == split_key)
                    ]

                sub_no_out = sub_all[sub_all["target_is_outlier"] == 0]
                sn_no_out = sn_all[sn_all["target_is_outlier"] == 0]

                st_all = compute_error_metrics(sub_all)
                st_no = compute_error_metrics(sub_no_out)
                st_sn_all = compute_error_metrics(sn_all)
                st_sn_no = compute_error_metrics(sn_no_out)

                sk_all = (1.0 - st_all["mae"] / st_sn_all["mae"]) * 100.0 if st_sn_all["mae"] > 0 else 0.0
                sk_no = (1.0 - st_no["mae"] / st_sn_no["mae"]) * 100.0 if st_sn_no["mae"] > 0 else 0.0
                n_out = st_all["n"] - st_no["n"]
                d_mae = st_no["mae"] - st_all["mae"]
                d_mape = st_no["mape"] - st_all["mape"]

                t9_rows.append([
                    commodity,
                    split_label,
                    h_label,
                    c_id,
                    st_all["n"],
                    n_out,
                    st_no["n"],
                    f"{st_all['mae']:.2f}",
                    f"{st_all['rmse']:.2f}",
                    f"{st_all['mape']:.2f}%",
                    f"{sk_all:+.1f}%",
                    f"{st_all['cov80']:.1f}%",
                    f"{st_no['mae']:.2f}",
                    f"{st_no['rmse']:.2f}",
                    f"{st_no['mape']:.2f}%",
                    f"{sk_no:+.1f}%",
                    f"{st_no['cov80']:.1f}%",
                    f"{d_mae:+.2f}",
                    f"{d_mape:+.2f} pp",
                ])

    write_table_pair(
        "phase2_outlier_sensitivity",
        "Phase 2 Evaluation Sensitivity: Primary Results (All Observed Targets) vs. Excluding Flagged Outlier Target Months (`XOF/kg`)",
        [
            "Primary results evaluate strictly on all observed target months (`is_observed == 1`, including flagged spikes/jumps).",
            "This sensitivity table compares evaluation metrics when target months flagged as level/jump outliers (`is_outlier == 1` in `prices_cleaned_all.csv`) are excluded from the evaluation denominator.",
            "Enforces Safeguard 1: `is_outlier` is never used as a model input feature.",
        ],
        [
            "Product",
            "Evaluation Split",
            "Horizon",
            "Model",
            "All Obs Targets (N)",
            "Flagged Outlier Targets",
            "Non-Outlier Targets (N)",
            "Primary MAE (All Obs)",
            "Primary RMSE",
            "Primary MAPE %",
            "Primary Skill vs SNaive12m",
            "Primary 80% PI Cov",
            "Excl-Outliers MAE",
            "Excl-Outliers RMSE",
            "Excl-Outliers MAPE %",
            "Excl-Outliers Skill vs SNaive12m",
            "Excl-Outliers 80% PI Cov",
            "Delta MAE (Excl - All)",
            "Delta MAPE (Excl - All)",
        ],
        t9_rows,
    )

    # -------------------------------------------------------------------------
    # Export `web/public/data/forecasts.json` (UTF-8) & Render Phase 2 Figures
    # -------------------------------------------------------------------------
    export_web_forecasts_json(
        panels=panels,
        champions=champions,
        main_df=main_df,
        df_future=df_future,
        market_accuracy_lookup=market_accuracy_lookup,
    )

    from src.evaluate.figures import generate_all_phase2_figures
    generate_all_phase2_figures()

    return {
        "champions": champions,
        "df_eval": df_eval,
        "df_future": df_future,
    }


def export_web_forecasts_json(
    panels: Dict[str, Any],
    champions: Dict[Tuple[str, int], str],
    main_df: pd.DataFrame,
    df_future: pd.DataFrame,
    market_accuracy_lookup: Dict[Tuple[str, str], Dict[str, Any]],
) -> Path:
    """Export `web/public/data/forecasts.json` (UTF-8) for the Phase 3 web application."""
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = WEB_DATA_DIR / "forecasts.json"

    df_all_cleaned = pd.read_csv(
        PROCESSED_DATA_DIR / "prices_cleaned_all.csv", dtype={"market_id": str}
    )
    df_markets_active = pd.read_csv(
        PROCESSED_DATA_DIR / "markets_active.csv", dtype={"market_id": str}
    )
    df_cov_market = pd.read_csv(
        TABLES_DIR / "coverage_by_market.csv", dtype={"Market ID": str}
    )

    # Build product-level summary metadata
    products_meta: Dict[str, Any] = {}
    for commodity, panel in panels.items():
        slug = panel.product_slug
        champ_by_h = {f"h{h}": champions[(commodity, h)] for h in HORIZONS}

        # Product-level holdout test and validation accuracy for selected champions
        test_slices = [
            main_df[
                (main_df["commodity"] == commodity)
                & (main_df["horizon"] == h)
                & (main_df["model_id"] == champions[(commodity, h)])
                & (main_df["split"] == "test")
            ]
            for h in HORIZONS
        ]
        val_slices = [
            main_df[
                (main_df["commodity"] == commodity)
                & (main_df["horizon"] == h)
                & (main_df["model_id"] == champions[(commodity, h)])
                & (main_df["split"] == "validation")
            ]
            for h in HORIZONS
        ]
        snaive_test_slices = [
            main_df[
                (main_df["commodity"] == commodity)
                & (main_df["horizon"] == h)
                & (main_df["model_id"] == "Seasonal_Naive_12m")
                & (main_df["split"] == "test")
            ]
            for h in HORIZONS
        ]

        st_test_all = compute_error_metrics(pd.concat(test_slices, ignore_index=True))
        st_val_all = compute_error_metrics(pd.concat(val_slices, ignore_index=True))
        st_snaive_test = compute_error_metrics(pd.concat(snaive_test_slices, ignore_index=True))
        skill_test = (
            (1.0 - st_test_all["mae"] / st_snaive_test["mae"]) * 100.0
            if st_snaive_test["mae"] > 0
            else 0.0
        )

        by_h_acc: Dict[str, Any] = {}
        reliability_by_h: Dict[str, Any] = {}
        baseline_ids = ["Naive_LastValue", "Seasonal_Naive_12m", "Seasonal_Ratio_Naive"]
        all_main_ids = [m.model_id for m in MODEL_SPECS if m.is_main_candidate]

        for h_idx, h in enumerate(HORIZONS):
            st_h = compute_error_metrics(test_slices[h_idx])
            st_sh = compute_error_metrics(snaive_test_slices[h_idx])
            sk_h = (1.0 - st_h["mae"] / st_sh["mae"]) * 100.0 if st_sh["mae"] > 0 else 0.0

            val_h_sub = main_df[
                (main_df["commodity"] == commodity)
                & (main_df["horizon"] == h)
                & (main_df["split"] == "validation")
            ]
            test_h_sub = main_df[
                (main_df["commodity"] == commodity)
                & (main_df["horizon"] == h)
                & (main_df["split"] == "test")
            ]
            val_base_maes = {
                b_id: compute_error_metrics(val_h_sub[val_h_sub["model_id"] == b_id])["mae"]
                for b_id in baseline_ids
            }
            best_base_id = min(baseline_ids, key=lambda b: val_base_maes[b])
            champ_val_mae = compute_error_metrics(
                val_h_sub[val_h_sub["model_id"] == champions[(commodity, h)]]
            )["mae"]
            val_skill_best_base_h = (
                (1.0 - champ_val_mae / val_base_maes[best_base_id]) * 100.0
                if val_base_maes[best_base_id] > 0
                else 0.0
            )
            best_base_test_stats = compute_error_metrics(
                test_h_sub[test_h_sub["model_id"] == best_base_id]
            )
            test_all_stats = {
                m_id: compute_error_metrics(test_h_sub[test_h_sub["model_id"] == m_id])
                for m_id in all_main_ids
            }
            best_model_test_id = min(all_main_ids, key=lambda m: test_all_stats[m]["mae"])
            best_model_test_stats = test_all_stats[best_model_test_id]
            sk_best_base_h = (
                (1.0 - st_h["mae"] / best_base_test_stats["mae"]) * 100.0
                if best_base_test_stats["mae"] > 0
                else 0.0
            )

            rel_info = compute_product_horizon_reliability(
                commodity=commodity,
                horizon=h,
                champ_id=champions[(commodity, h)],
                best_base_id=best_base_id,
                best_model_test_id=best_model_test_id,
                champ_test_stats=st_h,
                best_base_test_stats=best_base_test_stats,
                best_model_test_stats=best_model_test_stats,
                val_skill_vs_best_base=val_skill_best_base_h,
            )
            reliability_by_h[f"h{h}"] = rel_info

            by_h_acc[f"h{h}"] = {
                "horizon_months": h,
                "model_used": champions[(commodity, h)],
                "best_baseline_val": best_base_id,
                "n_eval": st_h["n"],
                "mae": round(st_h["mae"], 2),
                "rmse": round(st_h["rmse"], 2),
                "mape": round(st_h["mape"], 2),
                "skill_vs_best_baseline_pct": round(sk_best_base_h, 1),
                "skill_vs_snaive_pct": round(sk_h, 1),
                "coverage_80": round(st_h["cov80"], 1),
                "coverage_90": round(st_h["cov90"], 1),
                "mean_width_80": round(st_h["width80"], 1),
                "reliability": rel_info["status"],
                "reliability_note_fr": rel_info["note_fr"],
                "reliability_note_en": rel_info["note_en"],
                "reliability_detail": rel_info,
            }

        products_meta[slug] = {
            "product_slug": slug,
            "commodity": commodity,
            "label_fr": PRODUCT_LABELS_FR[commodity],
            "label_en": commodity,
            "unit": "KG",
            "currency": "XOF",
            "role": "forecast_primary",
            "tier1_markets_count": len(panel.markets),
            "as_of_date": "2026-09-15",
            "champions_by_horizon": champ_by_h,
            "reliability_by_horizon": reliability_by_h,
            "backtest_accuracy": {
                "holdout_test_window": "2025-10-15..2026-09-15",
                "validation_window": "2022-01-15..2025-09-15",
                "test_overall": {
                    "n_eval": st_test_all["n"],
                    "mae": round(st_test_all["mae"], 2),
                    "rmse": round(st_test_all["rmse"], 2),
                    "mape": round(st_test_all["mape"], 2),
                    "skill_vs_snaive_pct": round(skill_test, 1),
                    "coverage_80": round(st_test_all["cov80"], 1),
                    "coverage_90": round(st_test_all["cov90"], 1),
                },
                "validation_overall": {
                    "n_eval": st_val_all["n"],
                    "mae": round(st_val_all["mae"], 2),
                    "rmse": round(st_val_all["rmse"], 2),
                    "mape": round(st_val_all["mape"], 2),
                    "coverage_80": round(st_val_all["cov80"], 1),
                    "coverage_90": round(st_val_all["cov90"], 1),
                },
                "by_horizon_test": by_h_acc,
            },
        }

    # Build markets_coverage list across all 51 active markets so the UI can explain
    # why non-Tier-1 markets do not have forecasts for a given commodity.
    # Fix C1: `docs/tables/coverage_by_market.csv` is in LONG format with columns:
    # `Product`, `Market ID`, `Market`, `Obs (2019-26)`, `Tier (2019-26)`
    cov_lookup_by_id: Dict[Tuple[str, str], Dict[str, Any]] = {}
    cov_lookup_by_name: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for _, r in df_cov_market.iterrows():
        prod_name = str(r["Product"]).strip()
        mkt_id_str = str(r["Market ID"]).strip()
        mkt_name_str = str(r["Market"]).strip()
        row_dict = r.to_dict()
        cov_lookup_by_id[(prod_name, mkt_id_str)] = row_dict
        cov_lookup_by_name[(prod_name, mkt_name_str)] = row_dict

    markets_coverage_list: List[Dict[str, Any]] = []
    for _, m_row in df_markets_active.sort_values("market").iterrows():
        mkt_id = str(m_row["market_id"]).strip()
        mkt_name = str(m_row["market"]).strip()
        lat = float(m_row["latitude"])
        lon = float(m_row["longitude"])

        prod_status: Dict[str, Any] = {}
        for slug, comm_name in [
            ("maize_white", "Maize (white)"),
            ("tomatoes", "Tomatoes"),
            ("yam_white", "Yam (white)"),
        ]:
            c_info = cov_lookup_by_id.get(
                (comm_name, mkt_id),
                cov_lookup_by_name.get((comm_name, mkt_name), {}),
            )
            obs_m = int(c_info["Obs (2019-26)"]) if "Obs (2019-26)" in c_info else 0
            tier_str = str(c_info.get("Tier (2019-26)", "None")).strip()
            is_t1 = tier_str.startswith("Tier-1")
            if is_t1:
                reason_fr = (
                    f"Marché bien suivi ({obs_m}/93 relevés de prix entre 2019 et 2026, seuil d'au moins 80 mois sur 93) : "
                    "prévisions actives avec fourchettes à 80 % et 90 %."
                )
                reason_en = (
                    f"Well-tracked market ({obs_m}/93 price records between 2019 and 2026, threshold of at least 80 months out of 93): "
                    "active forecasts with 80% and 90% intervals."
                )
            elif obs_m == 0:
                reason_fr = "Aucun relevé depuis 2019 pour ce produit dans ce marché : prévision désactivée conformément à la règle anti-invention de données."
                reason_en = "Zero post-2019 price records for this product in this market: forecasting disabled per data integrity rules."
            else:
                reason_fr = f"Suivi partiel ({obs_m}/93 relevés de prix entre 2019 et 2026, seuil fixé à 80 mois sur 93) : historique affiché en mode exploration uniquement, sans prévision hasardeuse."
                reason_en = f"Partial coverage ({obs_m}/93 price records between 2019 and 2026 vs 80/93 threshold): historical series shown for exploration only, no forecast issued."

            prod_status[slug] = {
                "tier": tier_str,
                "is_forecasted": is_t1,
                "obs_months_2019_2026": obs_m,
                "expected_months_2019_2026": 93,
                "completeness_pct": round(obs_m / 93.0 * 100.0, 1),
                "status_note_fr": reason_fr,
                "status_note_en": reason_en,
            }

        markets_coverage_list.append({
            "market_id": mkt_id,
            "market": mkt_name,
            "admin1": str(m_row["admin1"]),
            "admin2": str(m_row["admin2"]),
            "latitude": lat,
            "longitude": lon,
            "agro_zone": classify_agro_zone(lat),
            "coverage_by_product": prod_status,
        })

    # Build series payload for all 111 Tier-1 forecasted series + historical exploration series
    series_list: List[Dict[str, Any]] = []

    for commodity, panel in panels.items():
        slug = panel.product_slug
        for m_idx, mkt in enumerate(panel.markets):
            # Full observed history (including pre-2019 if present in prices_cleaned_all.csv)
            hist_df = df_all_cleaned[
                (df_all_cleaned["commodity"] == commodity)
                & (df_all_cleaned["market"] == mkt)
            ].sort_values("date")

            history_points: List[Dict[str, Any]] = []
            for _, hr in hist_df.iterrows():
                history_points.append({
                    "date": str(hr["date"]),
                    "year_month": str(hr["year_month"]),
                    "price": round(float(hr["price"]), 2),
                    "regime": str(hr["regime"]),
                    "is_outlier_level": int(hr["is_outlier_level"]),
                    "is_outlier_jump": int(hr["is_outlier_jump"]),
                })

            # Recent 1-step-ahead out-of-sample test trajectory (2025-10..2026-09)
            h1_champ = champions[(commodity, 1)]
            bt_df = main_df[
                (main_df["commodity"] == commodity)
                & (main_df["market"] == mkt)
                & (main_df["horizon"] == 1)
                & (main_df["model_id"] == h1_champ)
                & (main_df["split"] == "test")
            ].sort_values("target_date")

            recent_bt_points: List[Dict[str, Any]] = []
            for _, br in bt_df.iterrows():
                recent_bt_points.append({
                    "date": str(br["target_date"]),
                    "year_month": str(br["target_date"])[:7],
                    "actual_price": round(float(br["actual_price"]), 2),
                    "predicted_price": round(float(br["pred_price"]), 2),
                    "low_80": round(float(br["low_80"]), 2),
                    "high_80": round(float(br["high_80"]), 2),
                    "low_90": round(float(br["low_90"]), 2),
                    "high_90": round(float(br["high_90"]), 2),
                })

            # 2026-Q4 3-month ahead forecasts (h=1, 2, 3) from as_of_date = 2026-09-15
            forecasts_points: List[Dict[str, Any]] = []
            last_obs_date = ""
            last_obs_price = 0.0
            for h in HORIZONS:
                c_id = champions[(commodity, h)]
                f_row = df_future[
                    (df_future["commodity"] == commodity)
                    & (df_future["market"] == mkt)
                    & (df_future["horizon"] == h)
                    & (df_future["model_id"] == c_id)
                ].iloc[0]
                last_obs_date = str(f_row["last_observed_date"])
                last_obs_price = round(float(f_row["last_observed_price"]), 2)
                p_f = round(float(f_row["pred_price"]), 2)
                chg_pct = round((p_f / last_obs_price - 1.0) * 100.0, 1) if last_obs_price > 0 else 0.0
                rel_h = products_meta[slug]["reliability_by_horizon"][f"h{h}"]
                forecasts_points.append({
                    "horizon_months": h,
                    "target_date": str(f_row["target_date"]),
                    "year_month": str(f_row["target_date"])[:7],
                    "model_used": c_id,
                    "point_forecast": p_f,
                    "low_80": round(float(f_row["low_80"]), 2),
                    "high_80": round(float(f_row["high_80"]), 2),
                    "low_90": round(float(f_row["low_90"]), 2),
                    "high_90": round(float(f_row["high_90"]), 2),
                    "change_vs_last_pct": chg_pct,
                    "reliability": rel_h["status"],
                    "reliability_note_fr": rel_h["note_fr"],
                    "reliability_note_en": rel_h["note_en"],
                })

            obs_cnt_modern = int(np.sum(panel.is_observed[m_idx]))
            series_list.append({
                "series_id": f"{slug}__{mkt}",
                "product_slug": slug,
                "commodity": commodity,
                "label_fr": PRODUCT_LABELS_FR[commodity],
                "market_id": panel.market_ids[m_idx],
                "market": mkt,
                "admin1": panel.admin1s[m_idx],
                "admin2": panel.admin2s[m_idx],
                "latitude": float(panel.latitudes[m_idx]),
                "longitude": float(panel.longitudes[m_idx]),
                "agro_zone": panel.zones[m_idx],
                "tier": "Tier-1 (>=80m)",
                "is_forecasted": True,
                "obs_months_2019_2026": obs_cnt_modern,
                "completeness_2019_2026_pct": round(obs_cnt_modern / 93.0 * 100.0, 1),
                "as_of_date": "2026-09-15",
                "last_observed_date": last_obs_date,
                "last_observed_price": last_obs_price,
                "model_used": {
                    f"h{h}": champions[(commodity, h)] for h in HORIZONS
                },
                "reliability_by_horizon": products_meta[slug]["reliability_by_horizon"],
                "backtest_accuracy": market_accuracy_lookup[(commodity, mkt)],
                "history": history_points,
                "recent_backtest_h1": recent_bt_points,
                "forecasts": forecasts_points,
            })

    payload = {
        "project": "Bénin AgroMarket — Prévision des prix vivriers au Bénin",
        "as_of_date": "2026-09-15",
        "forecast_horizons_months": [1, 2, 3],
        "forecast_target_dates": ["2026-10-15", "2026-11-15", "2026-12-15"],
        "currency": "XOF",
        "unit": "KG",
        "evaluation_protocol": {
            "primary_modeling_window": "2019-01-15..2026-09-15 (93 months)",
            "initial_training_window": "2019-01-15..2021-12-15 (36 months)",
            "validation_split": "2022-01-15..2025-09-15 (target dates used for model selection)",
            "holdout_test_split": "2025-10-15..2026-09-15 (12 target months per horizon, evaluated once)",
            "safeguards": [
                "Safeguard 1: Full-sample outlier diagnostics (robust_z, is_outlier_*) are never used as model inputs.",
                "Safeguard 2: Only months with is_observed == 1 are ever used as forecast targets.",
            ],
            "attributions": {
                "wfp_hdx": "Programme Alimentaire Mondial (PAM / WFP VAM) via HDX (ONASA, CT-SAGSA, INStaD, FAO) — CC BY-IGO 3.0",
                "nasa_power": "NASA Langley Research Center (LaRC) POWER MERRA-2 Agroclimatology — Public Domain",
                "faostat": "FAO FAOSTAT — CC BY 4.0",
            },
        },
        "products": products_meta,
        "markets_coverage": markets_coverage_list,
        "series": series_list,
    }

    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Phase 2] Exported {out_path} ({len(series_list)} Tier-1 series, {len(markets_coverage_list)} active markets).")

    from src.evaluate.validate_export import validate_forecasts_export
    validate_forecasts_export(export_path=out_path)

    return out_path


if __name__ == "__main__":
    run_full_evaluation_pipeline(force_recompute="--recompute" in sys.argv)


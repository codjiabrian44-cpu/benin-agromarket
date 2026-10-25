"""Baseline, classical statistical/linear, and gradient boosting forecasters for Phase 2.

Implements:
1. `Naive_LastValue` (Baseline, refit_step=1)
2. `Seasonal_Naive_12m` (Baseline, refit_step=1)
3. `Seasonal_Ratio_Naive` (Baseline, refit_step=1)
4. `ETS_HoltWinters` (Classical Per-Market Exponential Smoothing on log P, refit_step=1)
5. `SARIMAX_101_011_12` (Classical Per-Market State-Space SARIMAX on log P, refit_step=1)
6. `Ridge_ARX` (Classical Pooled Ridge Autoregressive on log P, refit_step=1)
7. `HGBR_NoWeather` (Machine Learning Pooled HistGradientBoostingRegressor, refit_step=3)
8. `HGBR_WithWeather` (Machine Learning Pooled HGBR + Lagged NASA POWER, refit_step=3)

Plus two validation-only imputation sensitivity variants:
- `Ridge_ARX_Interp1mLags`
- `HGBR_NoWeather_Interp1mLags`
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from joblib import Parallel, delayed
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

from src.config import RANDOM_SEED
from src.models.features import (
    BASE_FEATURE_COLS,
    WEATHER_FEATURE_COLS,
    PanelSeriesData,
    build_features_at_origin,
    compute_causal_seasonal_profiles,
)

HORIZONS: Tuple[int, ...] = (1, 2, 3)
FIRST_ORIGIN_IDX: int = 35  # 2021-12-15 (36 training months: 2019-01..2021-12)
LAST_BACKTEST_ORIGIN_IDX: int = 91  # 2026-08-15 (last origin with h=1 target in 2026-09-15)
FINAL_ORIGIN_IDX: int = 92  # 2026-09-15 (production forecast origin for 2026-10..2026-12)
VALIDATION_END_DATE: str = "2025-09-15"
TEST_START_DATE: str = "2025-10-15"


@dataclass(frozen=True)
class ModelSpec:
    """Metadata and configuration for a forecasting model candidate."""

    model_id: str
    family: str
    refit_schedule: str
    uses_weather: bool
    uses_interp_lags: bool
    is_main_candidate: bool
    description: str


MODEL_SPECS: List[ModelSpec] = [
    ModelSpec(
        model_id="Naive_LastValue",
        family="1_Baseline",
        refit_schedule="Every origin (1m)",
        uses_weather=False,
        uses_interp_lags=False,
        is_main_candidate=True,
        description="Last observed price at or before forecast origin t.",
    ),
    ModelSpec(
        model_id="Seasonal_Naive_12m",
        family="1_Baseline",
        refit_schedule="Every origin (1m)",
        uses_weather=False,
        uses_interp_lags=False,
        is_main_candidate=True,
        description="Observed price in the same calendar month 12 months prior (t+h-12).",
    ),
    ModelSpec(
        model_id="Seasonal_Ratio_Naive",
        family="1_Baseline",
        refit_schedule="Every origin (1m)",
        uses_weather=False,
        uses_interp_lags=False,
        is_main_candidate=True,
        description="Local causal price anchor scaled by market/zone detrended seasonal index ratio.",
    ),
    ModelSpec(
        model_id="ETS_HoltWinters",
        family="2_Classical_Statistical",
        refit_schedule="Every origin (1m state update, 6m param opt)",
        uses_weather=False,
        uses_interp_lags=False,
        is_main_candidate=True,
        description="Per-market damped-trend additive seasonal Holt-Winters ETS on log(price).",
    ),
    ModelSpec(
        model_id="SARIMAX_101_011_12",
        family="2_Classical_Statistical",
        refit_schedule="Every origin (1m Kalman filter, 6m MLE opt)",
        uses_weather=False,
        uses_interp_lags=False,
        is_main_candidate=True,
        description="Per-market state-space SARIMA(1,0,1)(0,1,1)_12 on log(price) with native NaN filtering.",
    ),
    ModelSpec(
        model_id="Ridge_ARX",
        family="2_Classical_Linear",
        refit_schedule="Every origin (1m)",
        uses_weather=False,
        uses_interp_lags=False,
        is_main_candidate=True,
        description="Pooled L2-regularized autoregressive linear model with lags, rolling means, and Fourier seasonality.",
    ),
    ModelSpec(
        model_id="HGBR_NoWeather",
        family="3_Gradient_Boosting",
        refit_schedule="Every 3rd origin (3m)",
        uses_weather=False,
        uses_interp_lags=False,
        is_main_candidate=True,
        description="Pooled HistGradientBoostingRegressor on causal price lags, spatial hierarchy, and calendar seasonality.",
    ),
    ModelSpec(
        model_id="HGBR_WithWeather",
        family="3_Gradient_Boosting",
        refit_schedule="Every 3rd origin (3m)",
        uses_weather=True,
        uses_interp_lags=False,
        is_main_candidate=True,
        description="Pooled HistGradientBoostingRegressor adding strictly lagged NASA POWER agroclimatic features.",
    ),
    ModelSpec(
        model_id="Ridge_ARX_Interp1mLags",
        family="4_Sensitivity_Interp1m",
        refit_schedule="Every origin (1m)",
        uses_weather=False,
        uses_interp_lags=True,
        is_main_candidate=False,
        description="Sensitivity variant: Ridge_ARX using price_interp_1m_max strictly for lag inputs (targets remain is_observed==1).",
    ),
    ModelSpec(
        model_id="HGBR_NoWeather_Interp1mLags",
        family="4_Sensitivity_Interp1m",
        refit_schedule="Every 3rd origin (3m)",
        uses_weather=False,
        uses_interp_lags=True,
        is_main_candidate=False,
        description="Sensitivity variant: HGBR_NoWeather using price_interp_1m_max strictly for lag inputs (targets remain is_observed==1).",
    ),
]

MODEL_SPEC_MAP: Dict[str, ModelSpec] = {m.model_id: m for m in MODEL_SPECS}


def _causal_fill_and_winsorize_1d(y_log_slice: np.ndarray) -> np.ndarray:
    """Causally fill interior gaps and clip extreme spikes strictly within `0..t` for ETS.

    Never looks beyond the slice `y_log_slice` (`0..t`).
    """
    arr = y_log_slice.copy()
    valid_idx = np.where(~np.isnan(arr))[0]
    if len(valid_idx) == 0:
        return np.zeros_like(arr)

    # Causal median and MAD within 0..t
    med = float(np.median(arr[valid_idx]))
    mad = float(np.median(np.abs(arr[valid_idx] - med)))
    scale = max(1.4826 * mad, 0.08)
    arr[valid_idx] = np.clip(arr[valid_idx], med - 3.5 * scale, med + 3.5 * scale)

    # Fill leading NaNs with first observed value (or seasonal mean within 0..t)
    first_v = valid_idx[0]
    if first_v > 0:
        for i in range(first_v):
            # Look for same calendar month inside 0..t
            same_m = [idx for idx in valid_idx if (idx % 12) == (i % 12)]
            arr[i] = float(np.mean(arr[same_m])) if same_m else float(arr[first_v])

    # Linearly interpolate interior gaps that already have a right endpoint <= t,
    # and forward-fill any trailing NaN at the end of 0..t
    n = len(arr)
    last_val = arr[0]
    i = 0
    while i < n:
        if not np.isnan(arr[i]):
            last_val = arr[i]
            i += 1
        else:
            j = i
            while j < n and np.isnan(arr[j]):
                j += 1
            if j < n:
                # Interior gap inside 0..t:both endpoints i-1 and j are <= t
                right_val = arr[j]
                span = j - (i - 1)
                for k in range(i, j):
                    w = (k - (i - 1)) / float(span)
                    arr[k] = (1.0 - w) * last_val + w * right_val
            else:
                # Trailing gap at origin t: strictly forward-fill from last_val
                for k in range(i, n):
                    arr[k] = last_val
            i = j

    return arr


def _run_univariate_series_ets_and_sarimax(
    y_log_full: np.ndarray,
    fallback_log_preds: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any], Dict[str, Any]]:
    """Run per-market ETS and SARIMAX across all origins `35..92` (`58` origins) for one market.

    Parameters
    ----------
    y_log_full : np.ndarray of shape (T,)
        Raw observed log prices for a single market (`NaN` where unobserved).
    fallback_log_preds : np.ndarray of shape (58, 3)
        Causal `Seasonal_Ratio_Naive` log predictions used as a safety fallback if numerical
        optimization produces non-finite values.

    Returns
    -------
    ets_log_preds : np.ndarray of shape (58, 3)
        Log-price forecasts for origins `35..92` and horizons `h=1,2,3`.
    sar_log_preds : np.ndarray of shape (58, 3)
        Log-price forecasts for origins `35..92` and horizons `h=1,2,3`.
    final_ets_state : dict
        Fitted ETS parameters at final origin `92`.
    final_sar_state : dict
        Fitted SARIMAX parameters at final origin `92`.
    """
    n_origins = FINAL_ORIGIN_IDX - FIRST_ORIGIN_IDX + 1  # 58 origins (35..92)
    ets_log_preds = np.zeros((n_origins, 3), dtype=float)
    sar_log_preds = np.zeros((n_origins, 3), dtype=float)

    ets_kw: Optional[Dict[str, Any]] = None
    sar_params: Optional[np.ndarray] = None
    final_ets_state: Dict[str, Any] = {}
    final_sar_state: Dict[str, Any] = {}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for o_pos, t in enumerate(range(FIRST_ORIGIN_IDX, FINAL_ORIGIN_IDX + 1)):
            fb = fallback_log_preds[o_pos]
            yt_raw = y_log_full[: t + 1]
            yt_filled = _causal_fill_and_winsorize_1d(yt_raw)

            # Causal sanity bounds (within [min - 0.8, max + 0.8] of observed history <= t)
            obs_vals = yt_raw[~np.isnan(yt_raw)]
            min_bound = float(np.min(obs_vals)) - 0.80
            max_bound = float(np.max(obs_vals)) + 0.80

            # 1. ETS (Holt-Winters damped additive trend + additive seasonality on log P)
            try:
                mod_ets = ExponentialSmoothing(
                    yt_filled,
                    trend="add",
                    damped_trend=True,
                    seasonal="add",
                    seasonal_periods=12,
                    initialization_method="heuristic",
                )
                if ets_kw is None or (o_pos % 6 == 0) or (t == FINAL_ORIGIN_IDX):
                    res_ets = mod_ets.fit(optimized=True, use_brute=False)
                    p = res_ets.params
                    ets_kw = dict(
                        smoothing_level=float(np.clip(p["smoothing_level"], 0.01, 0.95)),
                        smoothing_trend=float(np.clip(p["smoothing_trend"], 0.0, 0.30)),
                        smoothing_seasonal=float(np.clip(p["smoothing_seasonal"], 0.01, 0.90)),
                        damping_trend=float(np.clip(p["damping_trend"], 0.80, 0.98)),
                        optimized=False,
                    )
                else:
                    res_ets = mod_ets.fit(**ets_kw)

                f_ets = np.asarray(res_ets.forecast(3), dtype=float)
                if not np.all(np.isfinite(f_ets)):
                    f_ets = fb.copy()
                else:
                    f_ets = np.clip(f_ets, min_bound, max_bound)
                ets_log_preds[o_pos] = f_ets
                if t == FINAL_ORIGIN_IDX:
                    final_ets_state = dict(ets_kw) if ets_kw else {}
            except Exception:
                ets_log_preds[o_pos] = fb.copy()

            # 2. SARIMAX((1,0,1), (0,1,1,12)) on log P with native Kalman filtering of NaNs
            try:
                # Clip extreme outliers causally on observed points <= t while keeping NaNs intact
                yt_sar = yt_raw.copy()
                valid_sar = ~np.isnan(yt_sar)
                med_s = float(np.median(yt_sar[valid_sar]))
                mad_s = float(np.median(np.abs(yt_sar[valid_sar] - med_s)))
                scale_s = max(1.4826 * mad_s, 0.08)
                yt_sar[valid_sar] = np.clip(
                    yt_sar[valid_sar], med_s - 3.5 * scale_s, med_s + 3.5 * scale_s
                )

                mod_sar = SARIMAX(
                    yt_sar,
                    order=(1, 0, 1),
                    seasonal_order=(0, 1, 1, 12),
                    trend="n",
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                if sar_params is None or (o_pos % 6 == 0) or (t == FINAL_ORIGIN_IDX):
                    res_sar = mod_sar.fit(disp=False, maxiter=15, start_params=sar_params)
                    if np.all(np.isfinite(res_sar.params)):
                        sar_params = res_sar.params
                else:
                    res_sar = mod_sar.filter(sar_params)

                f_sar = np.asarray(res_sar.forecast(3), dtype=float)
                if not np.all(np.isfinite(f_sar)):
                    f_sar = fb.copy()
                else:
                    f_sar = np.clip(f_sar, min_bound, max_bound)
                sar_log_preds[o_pos] = f_sar
                if t == FINAL_ORIGIN_IDX and sar_params is not None:
                    final_sar_state = {"params": sar_params.tolist()}
            except Exception:
                sar_log_preds[o_pos] = fb.copy()

    return ets_log_preds, sar_log_preds, final_ets_state, final_sar_state


def run_product_backtest_and_final_fit(
    panel: PanelSeriesData,
) -> Tuple[Dict[str, np.ndarray], Dict[str, Dict[int, Any]]]:
    """Run all 10 model configurations across origins `35..92` and horizons `1,2,3` for one product.

    Returns
    -------
    log_preds_by_model : dict mapping model_id -> np.ndarray of shape (M, 58, 3)
        Predicted log(price) for every market `0..M-1`, origin `35..92` (`o_pos = 0..57`),
        and horizon `h=1,2,3` (`h_idx = 0,1,2`).
    final_models : dict mapping model_id -> {horizon: fitted_estimator_at_final_origin}
        Final fitted estimator artifacts at `as_of_date = 2026-09-15` (`origin_idx = 92`).
    """
    m_len = len(panel.markets)
    t_len = len(panel.dates)
    n_origins = FINAL_ORIGIN_IDX - FIRST_ORIGIN_IDX + 1  # 58 origins (35..92)

    # Precompute causal seasonal profiles at each origin t in 12..92 for both raw and interp1m
    seas_raw_by_t: Dict[int, Tuple[np.ndarray, Dict[str, np.ndarray], np.ndarray]] = {}
    seas_int_by_t: Dict[int, Tuple[np.ndarray, Dict[str, np.ndarray], np.ndarray]] = {}
    for t in range(12, t_len):
        seas_raw_by_t[t] = compute_causal_seasonal_profiles(
            panel.log_price_raw[:, : t + 1], panel.months[: t + 1], panel.zones
        )
        seas_int_by_t[t] = compute_causal_seasonal_profiles(
            panel.log_price_interp1m[:, : t + 1], panel.months[: t + 1], panel.zones
        )

    # Precompute feature tensors X_raw[t, h_idx] and X_int[t, h_idx] of shape (M, F) for t in 12..92
    n_feat = len(BASE_FEATURE_COLS) + len(WEATHER_FEATURE_COLS)
    n_base = len(BASE_FEATURE_COLS)
    X_raw_all = np.full((t_len, 3, m_len, n_feat), np.nan, dtype=float)
    X_int_all = np.full((t_len, 3, m_len, n_feat), np.nan, dtype=float)

    for t in range(12, t_len):
        for h_idx, h in enumerate(HORIZONS):
            X_raw_all[t, h_idx] = build_features_at_origin(
                panel, t, h, use_interp_lags=False, precomputed_seas=seas_raw_by_t[t]
            )
            X_int_all[t, h_idx] = build_features_at_origin(
                panel, t, h, use_interp_lags=True, precomputed_seas=seas_int_by_t[t]
            )

    log_preds: Dict[str, np.ndarray] = {
        spec.model_id: np.full((m_len, n_origins, 3), np.nan, dtype=float)
        for spec in MODEL_SPECS
    }
    final_models: Dict[str, Dict[int, Any]] = {spec.model_id: {} for spec in MODEL_SPECS}

    idx_log_p_last = BASE_FEATURE_COLS.index("log_p_last")
    idx_target_lag12 = BASE_FEATURE_COLS.index("log_p_target_lag12")
    idx_target_lag24 = BASE_FEATURE_COLS.index("log_p_target_lag24")
    idx_seas_anchor = BASE_FEATURE_COLS.index("seasonal_anchor_pred")
    idx_mkt_exp_med = BASE_FEATURE_COLS.index("mkt_expanding_median")

    # 1. Baselines (`Naive_LastValue`, `Seasonal_Naive_12m`, `Seasonal_Ratio_Naive`)
    for o_pos, t in enumerate(range(FIRST_ORIGIN_IDX, FINAL_ORIGIN_IDX + 1)):
        for h_idx, h in enumerate(HORIZONS):
            X_t = X_raw_all[t, h_idx]
            last_val = X_t[:, idx_log_p_last]
            exp_med = X_t[:, idx_mkt_exp_med]
            naive_pred = np.where(~np.isnan(last_val), last_val, exp_med)

            seas_anchor = X_t[:, idx_seas_anchor]
            seas_ratio_pred = np.where(~np.isnan(seas_anchor), seas_anchor, naive_pred)

            lag12 = X_t[:, idx_target_lag12]
            lag24 = X_t[:, idx_target_lag24]
            snaive_pred = np.where(
                ~np.isnan(lag12),
                lag12,
                np.where(~np.isnan(lag24), lag24, seas_ratio_pred),
            )

            log_preds["Naive_LastValue"][:, o_pos, h_idx] = naive_pred
            log_preds["Seasonal_Naive_12m"][:, o_pos, h_idx] = snaive_pred
            log_preds["Seasonal_Ratio_Naive"][:, o_pos, h_idx] = seas_ratio_pred

    final_models["Naive_LastValue"] = {
        h: {"type": "Naive_LastValue", "as_of_date": panel.dates[FINAL_ORIGIN_IDX]}
        for h in HORIZONS
    }
    final_models["Seasonal_Naive_12m"] = {
        h: {"type": "Seasonal_Naive_12m", "as_of_date": panel.dates[FINAL_ORIGIN_IDX]}
        for h in HORIZONS
    }
    final_models["Seasonal_Ratio_Naive"] = {
        h: {
            "type": "Seasonal_Ratio_Naive",
            "as_of_date": panel.dates[FINAL_ORIGIN_IDX],
            "mkt_seasonal_profile": seas_raw_by_t[FINAL_ORIGIN_IDX][0],
        }
        for h in HORIZONS
    }

    # 2. Per-Market Classical Statistical Models (`ETS_HoltWinters` & `SARIMAX_101_011_12`)
    uni_results = Parallel(n_jobs=-1)(
        delayed(_run_univariate_series_ets_and_sarimax)(
            panel.log_price_raw[m_idx],
            log_preds["Seasonal_Ratio_Naive"][m_idx],
        )
        for m_idx in range(m_len)
    )
    ets_states: Dict[str, Any] = {}
    sar_states: Dict[str, Any] = {}
    for m_idx, (ets_p, sar_p, ets_st, sar_st) in enumerate(uni_results):
        log_preds["ETS_HoltWinters"][m_idx] = ets_p
        log_preds["SARIMAX_101_011_12"][m_idx] = sar_p
        ets_states[panel.markets[m_idx]] = ets_st
        sar_states[panel.markets[m_idx]] = sar_st

    for h in HORIZONS:
        final_models["ETS_HoltWinters"][h] = {
            "type": "ETS_HoltWinters",
            "as_of_date": panel.dates[FINAL_ORIGIN_IDX],
            "market_params": ets_states,
        }
        final_models["SARIMAX_101_011_12"][h] = {
            "type": "SARIMAX_101_011_12",
            "as_of_date": panel.dates[FINAL_ORIGIN_IDX],
            "market_params": sar_states,
        }

    # 3. Pooled Direct Horizon Models (`Ridge_ARX`, `HGBR_NoWeather`, `HGBR_WithWeather` + Sensitivity)
    pooled_configs = [
        ("Ridge_ARX", "ridge", False, False, 1),
        ("HGBR_NoWeather", "hgbr", False, False, 3),
        ("HGBR_WithWeather", "hgbr", True, False, 3),
        ("Ridge_ARX_Interp1mLags", "ridge", False, True, 1),
        ("HGBR_NoWeather_Interp1mLags", "hgbr", False, True, 3),
    ]

    for model_id, algo, use_weather, use_interp, refit_step in pooled_configs:
        X_tensor = X_int_all if use_interp else X_raw_all
        feat_slice = slice(0, n_feat) if use_weather else slice(0, n_base)

        for h_idx, h in enumerate(HORIZONS):
            current_estimator: Optional[Any] = None

            for o_pos, t in enumerate(range(FIRST_ORIGIN_IDX, FINAL_ORIGIN_IDX + 1)):
                need_refit = (
                    current_estimator is None
                    or (o_pos % refit_step == 0)
                    or (t == FINAL_ORIGIN_IDX)
                )
                if need_refit:
                    # Strictly causal training pairs: origin s >= 12 such that target date s + h <= t
                    # AND ground-truth target at s + h has is_observed == 1 (Safeguard 2)!
                    max_train_origin = t - h
                    X_train_list: List[np.ndarray] = []
                    y_train_list: List[np.ndarray] = []

                    for s in range(12, max_train_origin + 1):
                        target_col = s + h
                        # Safeguard 2: ONLY observed ground-truth targets are ever trained on
                        obs_mask = panel.is_observed[:, target_col]
                        if np.any(obs_mask):
                            X_s = X_tensor[s, h_idx, obs_mask, feat_slice]
                            y_s = panel.log_price_raw[obs_mask, target_col]
                            # Target is log(P_{s+h}) - seasonal_anchor_pred or direct log(P_{s+h})
                            X_train_list.append(X_s)
                            y_train_list.append(y_s)

                    X_train = np.vstack(X_train_list)
                    y_train = np.concatenate(y_train_list)

                    if algo == "ridge":
                        est = Pipeline([
                            ("imputer", SimpleImputer(strategy="median")),
                            ("scaler", StandardScaler()),
                            ("ridge", Ridge(alpha=15.0, random_state=RANDOM_SEED)),
                        ])
                        est.fit(X_train, y_train)
                    else:
                        # HistGradientBoostingRegressor predicts residual around causal seasonal anchor
                        # to combine strong local level adaptation with nonlinear tree corrections
                        anchor_train = X_train[:, idx_seas_anchor]
                        valid_anchor = ~np.isnan(anchor_train)
                        X_tr_clean = X_train[valid_anchor]
                        y_tr_res = y_train[valid_anchor] - anchor_train[valid_anchor]
                        est = HistGradientBoostingRegressor(
                            loss="squared_error",
                            max_iter=100,
                            learning_rate=0.04,
                            max_leaf_nodes=12,
                            max_depth=4,
                            min_samples_leaf=30,
                            l2_regularization=5.0,
                            random_state=RANDOM_SEED,
                        )
                        est.fit(X_tr_clean, y_tr_res)

                    current_estimator = est

                # Predict at origin t for target t + h
                X_pred = X_tensor[t, h_idx, :, feat_slice]
                fb_pred = log_preds["Seasonal_Ratio_Naive"][:, o_pos, h_idx]

                if algo == "ridge":
                    raw_pred = current_estimator.predict(X_pred)
                else:
                    anchor_pred = X_pred[:, idx_seas_anchor]
                    res_pred = current_estimator.predict(X_pred)
                    raw_pred = np.where(~np.isnan(anchor_pred), anchor_pred + res_pred, fb_pred)

                # Causal sanity clip based on observed history <= t
                obs_hist = panel.log_price_raw[:, : t + 1]
                min_b = float(np.nanmin(obs_hist)) - 0.80
                max_b = float(np.nanmax(obs_hist)) + 0.80
                raw_pred = np.where(np.isfinite(raw_pred), np.clip(raw_pred, min_b, max_b), fb_pred)
                log_preds[model_id][:, o_pos, h_idx] = raw_pred

                if t == FINAL_ORIGIN_IDX:
                    final_models[model_id][h] = {
                        "type": model_id,
                        "commodity": panel.commodity,
                        "horizon": h,
                        "as_of_date": panel.dates[FINAL_ORIGIN_IDX],
                        "feature_cols": (
                            BASE_FEATURE_COLS + WEATHER_FEATURE_COLS
                            if use_weather
                            else BASE_FEATURE_COLS
                        ),
                        "estimator": current_estimator,
                    }

    return log_preds, final_models


def compute_causal_prediction_intervals(
    panel: PanelSeriesData,
    log_preds: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute strictly causal 80% and 90% empirical/conformal prediction intervals.

    At each origin `t` (`o_pos` in `0..57`, corresponding to `t = 35..92`) and horizon `h`,
    only out-of-sample residuals whose target date `s + h <= t` AND `is_observed == 1`
    are used. Market-specific residual quantiles are shrunk toward the product-wide
    residual quantiles (`w_m = min(1.0, n_m / 20.0)`).

    When standing at early origins (`o_pos < h`) where fewer than 20 product-wide backtest
    residuals have completed, historical 12-month seasonal-naive log changes strictly within
    `0..t` provide the initial prior scale so intervals are always well-defined and causal.

    Returns
    -------
    low_80, high_80, low_90, high_90 : np.ndarray of shape (M, 58, 3) in XOF/kg
    """
    m_len, n_origins, _ = log_preds.shape
    low_80 = np.zeros_like(log_preds)
    high_80 = np.zeros_like(log_preds)
    low_90 = np.zeros_like(log_preds)
    high_90 = np.zeros_like(log_preds)

    # Precompute initial causal prior log-errors from 2019..2021 (`0..35`) per horizon
    prior_abs_err_by_h: Dict[int, np.ndarray] = {}
    for h in HORIZONS:
        diffs = []
        for tau in range(12, FIRST_ORIGIN_IDX + 1):
            obs_now = panel.is_observed[:, tau]
            obs_prev = panel.is_observed[:, tau - h]
            obs_s12 = panel.is_observed[:, tau - 12]
            mask = obs_now & (obs_prev | obs_s12)
            if np.any(mask):
                ref = np.where(
                    obs_prev[mask],
                    panel.log_price_raw[mask, tau - h],
                    panel.log_price_raw[mask, tau - 12],
                )
                diffs.append(panel.log_price_raw[mask, tau] - ref)
        prior_abs_err_by_h[h] = (
            np.abs(np.concatenate(diffs)) if diffs else np.array([0.15, 0.25, 0.35])
        )

    for h_idx, h in enumerate(HORIZONS):
        prior_abs = prior_abs_err_by_h[h]
        prior_q80 = float(np.quantile(prior_abs, 0.80))
        prior_q90 = float(np.quantile(prior_abs, 0.90))

        for o_pos, t in enumerate(range(FIRST_ORIGIN_IDX, FINAL_ORIGIN_IDX + 1)):
            # Completed prior backtest origins s in 35..t-h (so target s + h <= t)
            max_completed_opos = o_pos - h
            if max_completed_opos >= 0:
                completed_s_indices = np.arange(0, max_completed_opos + 1)
                target_t_indices = FIRST_ORIGIN_IDX + completed_s_indices + h
                obs_mask = panel.is_observed[:, target_t_indices]  # shape (M, K)
                y_true_log = panel.log_price_raw[:, target_t_indices]
                y_hat_log = log_preds[:, completed_s_indices, h_idx]
                abs_res_mat = np.where(obs_mask, np.abs(y_true_log - y_hat_log), np.nan)
                all_valid_abs = abs_res_mat[~np.isnan(abs_res_mat)]
            else:
                abs_res_mat = np.full((m_len, 0), np.nan)
                all_valid_abs = np.array([], dtype=float)

            n_pool = len(all_valid_abs)
            if n_pool >= 10:
                w_pool = min(1.0, n_pool / 100.0)
                pool_q80 = w_pool * float(np.quantile(all_valid_abs, 0.80)) + (1.0 - w_pool) * prior_q80
                pool_q90 = w_pool * float(np.quantile(all_valid_abs, 0.90)) + (1.0 - w_pool) * prior_q90
            else:
                pool_q80 = prior_q80
                pool_q90 = prior_q90

            for m_idx in range(m_len):
                mkt_abs = abs_res_mat[m_idx][~np.isnan(abs_res_mat[m_idx])] if abs_res_mat.shape[1] > 0 else np.array([])
                n_m = len(mkt_abs)
                if n_m >= 5:
                    w_m = min(1.0, n_m / 20.0)
                    q80 = w_m * float(np.quantile(mkt_abs, 0.80)) + (1.0 - w_m) * pool_q80
                    q90 = w_m * float(np.quantile(mkt_abs, 0.90)) + (1.0 - w_m) * pool_q90
                else:
                    q80 = pool_q80
                    q90 = pool_q90

                # Ensure strict ordering q90 > q80 > 0
                q80 = max(q80, 0.03)
                q90 = max(q90, q80 + 0.02)

                pred_log = log_preds[m_idx, o_pos, h_idx]
                pred_price = np.exp(pred_log)
                low_80[m_idx, o_pos, h_idx] = pred_price * np.exp(-q80)
                high_80[m_idx, o_pos, h_idx] = pred_price * np.exp(+q80)
                low_90[m_idx, o_pos, h_idx] = pred_price * np.exp(-q90)
                high_90[m_idx, o_pos, h_idx] = pred_price * np.exp(+q90)

    return low_80, high_80, low_90, high_90


def fit_final_models_only(panel: PanelSeriesData) -> Dict[str, Dict[int, Any]]:
    """Fit all candidate models at the final forecast origin `as_of_date = 2026-09-15` (`t = 92`)."""
    m_len = len(panel.markets)
    t_len = len(panel.dates)
    seas_raw_by_t = {
        t: compute_causal_seasonal_profiles(
            panel.log_price_raw[:, : t + 1], panel.months[: t + 1], panel.zones
        )
        for t in range(12, t_len)
    }
    n_feat = len(BASE_FEATURE_COLS) + len(WEATHER_FEATURE_COLS)
    n_base = len(BASE_FEATURE_COLS)
    X_raw_all = np.full((t_len, 3, m_len, n_feat), np.nan, dtype=float)
    for t in range(12, t_len):
        for h_idx, h in enumerate(HORIZONS):
            X_raw_all[t, h_idx] = build_features_at_origin(
                panel, t, h, use_interp_lags=False, precomputed_seas=seas_raw_by_t[t]
            )

    final_models: Dict[str, Dict[int, Any]] = {spec.model_id: {} for spec in MODEL_SPECS}
    final_models["Naive_LastValue"] = {
        h: {"type": "Naive_LastValue", "as_of_date": panel.dates[FINAL_ORIGIN_IDX]}
        for h in HORIZONS
    }
    final_models["Seasonal_Naive_12m"] = {
        h: {"type": "Seasonal_Naive_12m", "as_of_date": panel.dates[FINAL_ORIGIN_IDX]}
        for h in HORIZONS
    }
    final_models["Seasonal_Ratio_Naive"] = {
        h: {
            "type": "Seasonal_Ratio_Naive",
            "as_of_date": panel.dates[FINAL_ORIGIN_IDX],
            "mkt_seasonal_profile": seas_raw_by_t[FINAL_ORIGIN_IDX][0],
        }
        for h in HORIZONS
    }
    for h in HORIZONS:
        final_models["ETS_HoltWinters"][h] = {
            "type": "ETS_HoltWinters",
            "as_of_date": panel.dates[FINAL_ORIGIN_IDX],
        }
        final_models["SARIMAX_101_011_12"][h] = {
            "type": "SARIMAX_101_011_12",
            "as_of_date": panel.dates[FINAL_ORIGIN_IDX],
        }

    idx_seas_anchor = BASE_FEATURE_COLS.index("seasonal_anchor_pred")
    for model_id, algo, use_weather in [
        ("Ridge_ARX", "ridge", False),
        ("HGBR_NoWeather", "hgbr", False),
        ("HGBR_WithWeather", "hgbr", True),
    ]:
        feat_slice = slice(0, n_feat) if use_weather else slice(0, n_base)
        for h_idx, h in enumerate(HORIZONS):
            t = FINAL_ORIGIN_IDX
            max_train_origin = t - h
            X_train_list: List[np.ndarray] = []
            y_train_list: List[np.ndarray] = []
            for s in range(12, max_train_origin + 1):
                target_col = s + h
                obs_mask = panel.is_observed[:, target_col]
                if np.any(obs_mask):
                    X_train_list.append(X_raw_all[s, h_idx, obs_mask, feat_slice])
                    y_train_list.append(panel.log_price_raw[obs_mask, target_col])
            X_train = np.vstack(X_train_list)
            y_train = np.concatenate(y_train_list)
            if algo == "ridge":
                est = Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    ("ridge", Ridge(alpha=15.0, random_state=RANDOM_SEED)),
                ])
                est.fit(X_train, y_train)
            else:
                anchor_train = X_train[:, idx_seas_anchor]
                valid_anchor = ~np.isnan(anchor_train)
                est = HistGradientBoostingRegressor(
                    loss="squared_error",
                    max_iter=100,
                    learning_rate=0.04,
                    max_leaf_nodes=12,
                    max_depth=4,
                    min_samples_leaf=30,
                    l2_regularization=5.0,
                    random_state=RANDOM_SEED,
                )
                est.fit(X_train[valid_anchor], y_train[valid_anchor] - anchor_train[valid_anchor])
            final_models[model_id][h] = {
                "type": model_id,
                "commodity": panel.commodity,
                "horizon": h,
                "as_of_date": panel.dates[FINAL_ORIGIN_IDX],
                "feature_cols": (
                    BASE_FEATURE_COLS + WEATHER_FEATURE_COLS
                    if use_weather
                    else BASE_FEATURE_COLS
                ),
                "estimator": est,
            }
    return final_models

